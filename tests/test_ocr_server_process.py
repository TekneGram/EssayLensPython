from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from config.llm_server_config import LlmServerConfig
from config.ocr_config import OcrConfig
from nlp.ocr.ocr_server_process import OcrServerProcess


def _build_configs(root: Path) -> tuple[LlmServerConfig, OcrConfig]:
    server_bin = root / "llama-server"
    gguf = root / "ocr.gguf"
    mmproj = root / "ocr-mmproj.gguf"
    server_bin.write_text("bin", encoding="utf-8")
    gguf.write_text("x", encoding="utf-8")
    mmproj.write_text("x", encoding="utf-8")

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
        llama_n_parallel=4,
        llama_seed=42,
        llama_rope_freq_base=10000.0,
        llama_rope_freq_scale=1.0,
        llama_use_jinja=True,
        llama_cache_prompt=True,
        llama_flash_attn=True,
    )
    ocr_cfg = OcrConfig.from_strings(
        ocr_gguf_path=gguf,
        ocr_mmproj_path=mmproj,
        ocr_server_model="server",
        ocr_model_key="ocr",
        ocr_model_display_name="OCR",
        ocr_model_alias="ocr",
        ocr_model_family="ocr/vision",
    )
    return server_cfg, ocr_cfg


class OcrServerProcessTests(unittest.TestCase):
    def test_start_builds_command_and_waits_for_health(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            server_cfg, ocr_cfg = _build_configs(Path(tmpdir))
            proc = OcrServerProcess(server_cfg=server_cfg, ocr_cfg=ocr_cfg)

            fake_proc = MagicMock()
            fake_proc.poll.return_value = None
            ok = MagicMock()
            ok.status_code = 200
            ok.json.return_value = {"status": "ok"}

            with patch(
                "nlp.ocr.ocr_server_process.subprocess.check_output",
                return_value="... --flash-attn [on|off|auto] ...",
            ), patch(
                "nlp.ocr.ocr_server_process.subprocess.Popen",
                return_value=fake_proc,
            ) as popen_mock, patch("nlp.ocr.ocr_server_process.requests.get", return_value=ok):
                proc.start(wait_s=1)

            cmd = popen_mock.call_args[0][0]
            self.assertIn("--mmproj", cmd)
            self.assertIn("-np", cmd)
            self.assertIn("--flash-attn", cmd)
            idx = cmd.index("--flash-attn")
            self.assertEqual(cmd[idx + 1], "on")

    def test_start_raises_when_mmproj_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            server_cfg, ocr_cfg = _build_configs(root)
            missing = root / "missing-mmproj.gguf"
            ocr_cfg = OcrConfig.from_strings(
                ocr_gguf_path=ocr_cfg.ocr_gguf_path,
                ocr_mmproj_path=missing,
                ocr_server_model="server",
                ocr_model_key="ocr",
                ocr_model_display_name="OCR",
                ocr_model_alias="ocr",
                ocr_model_family="ocr/vision",
            )
            proc = OcrServerProcess(server_cfg=server_cfg, ocr_cfg=ocr_cfg)

            with self.assertRaises(FileNotFoundError):
                proc.start(wait_s=0.1)

    def test_start_times_out_when_wait_window_expires(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            server_cfg, ocr_cfg = _build_configs(Path(tmpdir))
            proc = OcrServerProcess(server_cfg=server_cfg, ocr_cfg=ocr_cfg)

            fake_proc = MagicMock()
            fake_proc.poll.return_value = None
            with patch("nlp.ocr.ocr_server_process.subprocess.Popen", return_value=fake_proc):
                with self.assertRaises(TimeoutError):
                    proc.start(wait_s=0)

    def test_stop_kills_when_terminate_wait_times_out(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            server_cfg, ocr_cfg = _build_configs(Path(tmpdir))
            proc = OcrServerProcess(server_cfg=server_cfg, ocr_cfg=ocr_cfg)
            fake_proc = MagicMock()
            fake_proc.poll.return_value = None
            fake_proc.wait.side_effect = subprocess.TimeoutExpired(cmd="x", timeout=5)
            proc._proc = fake_proc

            proc.stop()

            fake_proc.terminate.assert_called_once()
            fake_proc.kill.assert_called_once()
            self.assertIsNone(proc._proc)


if __name__ == "__main__":
    unittest.main()
