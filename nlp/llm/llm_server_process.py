from __future__ import annotations
from dataclasses import dataclass
import subprocess
import time
from typing import TYPE_CHECKING

try:
    import requests  # type: ignore
except ImportError:
    class _RequestsFallback:
        @staticmethod
        def post(*args, **kwargs):
            raise RuntimeError("requests is not installed.")

        @staticmethod
        def get(*args, **kwargs):
            raise RuntimeError("requests is not installed.")

    requests = _RequestsFallback()

if TYPE_CHECKING:
    from config.llm_server_config import LlmServerConfig
    from config.llm_config import LlmConfig

@dataclass
class LlmServerProcess:
    server_cfg: LlmServerConfig
    llm_cfg: LlmConfig
    _proc: subprocess.Popen | None = None
    _flash_attn_value_supported: bool | None = None

    def is_running(self) -> bool:
        return self._proc is not None and (self._proc.poll() is None)

    def _supports_flash_attn_value(self) -> bool:
        if self._flash_attn_value_supported is not None:
            return self._flash_attn_value_supported
        try:
            help_text = subprocess.check_output(
                [str(self.server_cfg.llama_server_path), "-h"],
                stderr=subprocess.STDOUT,
                text=True,
            )
            self._flash_attn_value_supported = "--flash-attn [on|off|auto]" in help_text
        except Exception:
            # Default to modern behavior when probing fails.
            self._flash_attn_value_supported = True
        return self._flash_attn_value_supported
    
    def start(self, wait_s: float = 180.0) -> None:
        if self.is_running():
            return
        
        if not self.server_cfg.llama_server_path.exists():
            raise FileNotFoundError(f"llm server not found: {self.server_cfg.llama_server_path}")

        if self.llm_cfg.llama_gguf_path is None:
            raise ValueError("llm_cfg.llama_gguf_path is required to start the llm server.")

        if not self.llm_cfg.llama_gguf_path.exists():
            raise FileNotFoundError(f"llm gguf not found: {self.llm_cfg.llama_gguf_path}")

        cmd = [
            str(self.server_cfg.llama_server_path),
            "-m", str(self.llm_cfg.llama_gguf_path),
            "--host", str(self.server_cfg.llama_host),
            "--port", str(self.server_cfg.llama_port),
            "-c", str(self.server_cfg.llama_n_ctx),
        ]
        if self.server_cfg.llama_n_threads is not None:
            cmd.extend(["-t", str(self.server_cfg.llama_n_threads)])
        if self.server_cfg.llama_n_gpu_layers is not None:
            cmd.extend(["-ngl", str(self.server_cfg.llama_n_gpu_layers)])
        if self.server_cfg.llama_n_batch is not None:
            cmd.extend(["-b", str(self.server_cfg.llama_n_batch)])
        if self.server_cfg.llama_n_parallel is not None:
            cmd.extend(["-np", str(self.server_cfg.llama_n_parallel)])
        if self.server_cfg.llama_seed is not None:
            cmd.extend(["--seed", str(self.server_cfg.llama_seed)])
        if self.server_cfg.llama_rope_freq_base is not None:
            cmd.extend(["--rope-freq-base", str(self.server_cfg.llama_rope_freq_base)])
        if self.server_cfg.llama_rope_freq_scale is not None:
            cmd.extend(["--rope-freq-scale", str(self.server_cfg.llama_rope_freq_scale)])
        cmd.append("--jinja" if self.server_cfg.llama_use_jinja else "--no-jinja")
        cmd.append("--cache-prompt" if self.server_cfg.llama_cache_prompt else "--no-cache-prompt")
        if self._supports_flash_attn_value():
            cmd.extend(["--flash-attn", "on" if self.server_cfg.llama_flash_attn else "off"])
        elif self.server_cfg.llama_flash_attn:
            cmd.append("--flash-attn")

        # Start server (persistent model load)
        self._proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Wait until Openai-compatible chat endpoint responds (model loaded)
        deadline = time.time() + wait_s
        url = f"http://{self.server_cfg.llama_host}:{self.server_cfg.llama_port}/health"
        models_url = f"http://{self.server_cfg.llama_host}:{self.server_cfg.llama_port}/v1/models"
        chat_url = f"http://{self.server_cfg.llama_host}:{self.server_cfg.llama_port}/v1/chat/completions"
        chat_payload = {
            "model": self.llm_cfg.llama_model_alias,
            "temperature": 0.0,
            "max_tokens": 1,
            "messages": [
                {"role": "system", "content": "You are a readiness probe."},
                {"role": "user", "content": "ping"}
            ],
        }
        while time.time() < deadline:
            if self._proc.poll() is not None:
                out, err = self._proc.communicate(timeout=1)
                raise RuntimeError(
                    "llm-server exited during startup.\n"
                    f"stdout:\n{out}\n\nstderr:\n{err}"
                )

            # Try chat first; it only succeeds after model loads
            try:
                r = requests.post(chat_url, json=chat_payload, timeout=1)
                if r.status_code == 200:
                    return
            except Exception:
                pass

            # Fallback: health/models can be up before the model is ready
            try:
                r = requests.get(url, timeout=1)
                if r.status_code == 200:
                    pass
            except Exception:
                pass

            try:
                r = requests.get(models_url, timeout=1)
                if r.status_code == 200:
                    pass
            except Exception:
                pass

            time.sleep(0.25)
        raise TimeoutError("Timed out waiting for the llm server to become ready.")
    
        

    def stop(self) -> None:
        if not self.is_running():
            return
        assert self._proc is not None
        self._proc.terminate()
        try:
            self._proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._proc.kill()
        self._proc = None
        
        
