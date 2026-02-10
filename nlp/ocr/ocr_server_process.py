from __future__ import annotations

from dataclasses import dataclass
import subprocess
import time
from typing import TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from config.llm_server_config import LlmServerConfig
    from config.ocr_config import OcrConfig


@dataclass
class OcrServerProcess:
    server_cfg: LlmServerConfig
    ocr_cfg: OcrConfig
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
            self._flash_attn_value_supported = True
        return self._flash_attn_value_supported

    def start(self, wait_s: float = 180.0) -> None:
        if self.is_running():
            return

        if not self.server_cfg.llama_server_path.exists():
            raise FileNotFoundError(f"ocr server not found: {self.server_cfg.llama_server_path}")

        if self.ocr_cfg.ocr_gguf_path is None:
            raise ValueError("ocr_cfg.ocr_gguf_path is required to start the ocr server.")
        if not self.ocr_cfg.ocr_gguf_path.exists():
            raise FileNotFoundError(f"ocr gguf not found: {self.ocr_cfg.ocr_gguf_path}")
        if not self.ocr_cfg.ocr_gguf_path.is_file():
            raise FileNotFoundError(f"ocr gguf is not a file: {self.ocr_cfg.ocr_gguf_path}")

        if self.ocr_cfg.ocr_mmproj_path is None:
            raise ValueError("ocr_cfg.ocr_mmproj_path is required to start the ocr server.")
        if not self.ocr_cfg.ocr_mmproj_path.exists():
            raise FileNotFoundError(f"ocr mmproj not found: {self.ocr_cfg.ocr_mmproj_path}")
        if not self.ocr_cfg.ocr_mmproj_path.is_file():
            raise FileNotFoundError(f"ocr mmproj is not a file: {self.ocr_cfg.ocr_mmproj_path}")

        cmd = [
            str(self.server_cfg.llama_server_path),
            "-m",
            str(self.ocr_cfg.ocr_gguf_path),
            "--mmproj",
            str(self.ocr_cfg.ocr_mmproj_path),
            "--host",
            str(self.server_cfg.llama_host),
            "--port",
            str(self.server_cfg.llama_port),
            "-c",
            str(self.server_cfg.llama_n_ctx),
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

        self._proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        deadline = time.time() + wait_s
        health_url = f"http://{self.server_cfg.llama_host}:{self.server_cfg.llama_port}/health"
        while time.time() < deadline:
            if self._proc.poll() is not None:
                stdout = self._proc.stdout.read() if self._proc.stdout else ""
                stderr = self._proc.stderr.read() if self._proc.stderr else ""
                raise RuntimeError(f"ocr-server exited.\nstdout:\n{stdout}\n\nstderr:\n{stderr}")

            try:
                response = requests.get(health_url, timeout=1)
                if response.status_code == 200:
                    try:
                        data = response.json()
                    except Exception:
                        return
                    if not isinstance(data, dict):
                        return
                    status = data.get("status")
                    if status == "ok":
                        return
                    if status is None:
                        return
                    if status == "loading-model":
                        pass
            except Exception:
                pass

            time.sleep(1.0)

        raise TimeoutError("Timed out waiting for the ocr server to become ready.")

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
