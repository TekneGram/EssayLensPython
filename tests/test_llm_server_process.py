from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from config.llm_config import LlmConfig
from config.llm_server_config import LlmServerConfig
from nlp.llm.llm_server_process import LlmServerProcess


class LlmServerProcessTests(unittest.TestCase):
    def _build_configs(self, tmp: Path) -> tuple[LlmServerConfig, LlmConfig]:
        server_bin = tmp / "llama-server"
        model_file = tmp / "model.gguf"
        server_bin.write_text("bin", encoding="utf-8")
        model_file.write_text("gguf", encoding="utf-8")

        server_cfg = LlmServerConfig.from_strings(
            llama_backend="server",
            llama_server_path=server_bin,
            llama_server_url="http://127.0.0.1:8080/v1/chat/completions",
            llama_n_ctx=4096,
            llama_host="127.0.0.1",
            llama_port=8080,
            llama_n_threads=8,
            llama_n_gpu_layers=99,
            llama_n_batch=512,
            llama_n_parallel=6,
            llama_seed=42,
            llama_rope_freq_base=10000.0,
            llama_rope_freq_scale=1.0,
            llama_use_jinja=True,
            llama_cache_prompt=True,
            llama_flash_attn=True,
        )
        llm_cfg = LlmConfig.from_strings(
            llama_gguf_path=model_file,
            llama_server_model="local",
            llama_model_key="local",
            llama_model_display_name="Local",
            llama_model_alias="local-model",
            llama_model_family="instruct",
        )
        return server_cfg, llm_cfg

    def test_start_builds_parallel_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            server_cfg, llm_cfg = self._build_configs(tmp)
            proc = LlmServerProcess(server_cfg=server_cfg, llm_cfg=llm_cfg)

            fake_proc = MagicMock()
            fake_proc.poll.return_value = None
            ok = MagicMock()
            ok.status_code = 200

            with patch(
                "nlp.llm.llm_server_process.subprocess.check_output",
                return_value="... --flash-attn [on|off|auto] ...",
            ), patch("nlp.llm.llm_server_process.subprocess.Popen", return_value=fake_proc) as popen_mock, patch(
                "nlp.llm.llm_server_process.requests.post",
                return_value=ok,
            ), patch("nlp.llm.llm_server_process.requests.get", return_value=ok):
                proc.start(wait_s=1)

            cmd = popen_mock.call_args[0][0]
            self.assertIn("-m", cmd)
            self.assertIn("-c", cmd)
            self.assertIn("--host", cmd)
            self.assertIn("--port", cmd)
            self.assertIn("-np", cmd)
            self.assertIn("6", cmd)
            self.assertIn("--jinja", cmd)
            self.assertIn("--cache-prompt", cmd)
            self.assertIn("--flash-attn", cmd)
            idx = cmd.index("--flash-attn")
            self.assertEqual(cmd[idx + 1], "on")

    def test_start_omits_optional_flags_when_unset(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            server_bin = tmp / "llama-server"
            model_file = tmp / "model.gguf"
            server_bin.write_text("bin", encoding="utf-8")
            model_file.write_text("gguf", encoding="utf-8")

            server_cfg = LlmServerConfig.from_strings(
                llama_backend="server",
                llama_server_path=server_bin,
                llama_server_url="http://127.0.0.1:8080/v1/chat/completions",
                llama_n_ctx=4096,
                llama_host="127.0.0.1",
                llama_port=8080,
                llama_n_threads=None,
                llama_n_gpu_layers=None,
                llama_n_batch=None,
                llama_n_parallel=None,
                llama_seed=None,
                llama_rope_freq_base=None,
                llama_rope_freq_scale=None,
                llama_use_jinja=False,
                llama_cache_prompt=False,
                llama_flash_attn=False,
            )
            llm_cfg = LlmConfig.from_strings(
                llama_gguf_path=model_file,
                llama_server_model="local",
                llama_model_key="local",
                llama_model_display_name="Local",
                llama_model_alias="local-model",
                llama_model_family="instruct",
            )
            proc = LlmServerProcess(server_cfg=server_cfg, llm_cfg=llm_cfg)

            fake_proc = MagicMock()
            fake_proc.poll.return_value = None
            ok = MagicMock()
            ok.status_code = 200

            with patch(
                "nlp.llm.llm_server_process.subprocess.check_output",
                return_value="... --flash-attn [on|off|auto] ...",
            ), patch("nlp.llm.llm_server_process.subprocess.Popen", return_value=fake_proc) as popen_mock, patch(
                "nlp.llm.llm_server_process.requests.post",
                return_value=ok,
            ), patch("nlp.llm.llm_server_process.requests.get", return_value=ok):
                proc.start(wait_s=1)

            cmd = popen_mock.call_args[0][0]
            self.assertNotIn("-np", cmd)
            self.assertNotIn("-t", cmd)
            self.assertNotIn("-ngl", cmd)
            self.assertNotIn("-b", cmd)
            self.assertNotIn("--seed", cmd)
            self.assertNotIn("--rope-freq-base", cmd)
            self.assertNotIn("--rope-freq-scale", cmd)
            self.assertIn("--no-jinja", cmd)
            self.assertIn("--no-cache-prompt", cmd)
            self.assertIn("--flash-attn", cmd)
            idx = cmd.index("--flash-attn")
            self.assertEqual(cmd[idx + 1], "off")

    def test_start_uses_legacy_flash_attn_flag_when_value_not_supported(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            server_cfg, llm_cfg = self._build_configs(tmp)
            proc = LlmServerProcess(server_cfg=server_cfg, llm_cfg=llm_cfg)

            fake_proc = MagicMock()
            fake_proc.poll.return_value = None
            ok = MagicMock()
            ok.status_code = 200

            with patch(
                "nlp.llm.llm_server_process.subprocess.check_output",
                return_value="legacy help text",
            ), patch("nlp.llm.llm_server_process.subprocess.Popen", return_value=fake_proc) as popen_mock, patch(
                "nlp.llm.llm_server_process.requests.post",
                return_value=ok,
            ), patch("nlp.llm.llm_server_process.requests.get", return_value=ok):
                proc.start(wait_s=1)

            cmd = popen_mock.call_args[0][0]
            self.assertIn("--flash-attn", cmd)
            idx = cmd.index("--flash-attn")
            if idx < len(cmd) - 1:
                self.assertNotIn(cmd[idx + 1], {"on", "off", "auto"})

    def test_start_raises_when_gguf_path_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            server_bin = tmp / "llama-server"
            server_bin.write_text("bin", encoding="utf-8")
            server_cfg = LlmServerConfig.from_strings(
                llama_backend="server",
                llama_server_path=server_bin,
                llama_server_url="http://127.0.0.1:8080/v1/chat/completions",
                llama_n_ctx=4096,
                llama_host="127.0.0.1",
                llama_port=8080,
                llama_n_threads=None,
                llama_n_gpu_layers=None,
                llama_n_batch=None,
                llama_n_parallel=2,
                llama_seed=None,
                llama_rope_freq_base=None,
                llama_rope_freq_scale=None,
                llama_use_jinja=True,
                llama_cache_prompt=True,
                llama_flash_attn=True,
            )
            llm_cfg = LlmConfig.from_strings(
                llama_gguf_path=None,
                llama_server_model="local",
                llama_model_key="local",
                llama_model_display_name="Local",
                llama_model_alias="local-model",
                llama_model_family="instruct",
            )
            proc = LlmServerProcess(server_cfg=server_cfg, llm_cfg=llm_cfg)
            with self.assertRaises(ValueError):
                proc.start(wait_s=0.1)


if __name__ == "__main__":
    unittest.main()
