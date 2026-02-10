from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from config.llm_config import LlmConfig
from config.llm_server_config import LlmServerConfig
from nlp.llm.llm_server_process import LlmServerProcess


def _build_configs(root: Path) -> tuple[LlmServerConfig, LlmConfig]:
    server_bin = root / "llama-server"
    gguf = root / "model.gguf"
    mmproj = root / "mmproj.gguf"
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
    llm_cfg = LlmConfig.from_strings(
        llama_gguf_path=gguf,
        llama_mmproj_path=mmproj,
        llama_server_model="server",
        llama_model_key="demo",
        llama_model_display_name="Demo",
        llama_model_alias="demo",
        llama_model_family="instruct",
    )
    return server_cfg, llm_cfg


class LlmServerProcessAdditionalTests(unittest.TestCase):
    def test_start_raises_when_mmproj_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            server_cfg, llm_cfg = _build_configs(root)
            missing = root / "missing.mmproj.gguf"
            llm_cfg = LlmConfig.from_strings(
                llama_gguf_path=llm_cfg.llama_gguf_path,
                llama_mmproj_path=missing,
                llama_server_model="server",
                llama_model_key="demo",
                llama_model_display_name="Demo",
                llama_model_alias="demo",
                llama_model_family="instruct",
            )
            proc = LlmServerProcess(server_cfg=server_cfg, llm_cfg=llm_cfg)

            with self.assertRaises(FileNotFoundError):
                proc.start(wait_s=0.1)

    def test_start_raises_when_mmproj_not_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            server_cfg, llm_cfg = _build_configs(root)
            mmproj_dir = root / "mmproj_dir"
            mmproj_dir.mkdir()
            llm_cfg = LlmConfig.from_strings(
                llama_gguf_path=llm_cfg.llama_gguf_path,
                llama_mmproj_path=mmproj_dir,
                llama_server_model="server",
                llama_model_key="demo",
                llama_model_display_name="Demo",
                llama_model_alias="demo",
                llama_model_family="instruct",
            )
            proc = LlmServerProcess(server_cfg=server_cfg, llm_cfg=llm_cfg)

            with self.assertRaises(FileNotFoundError):
                proc.start(wait_s=0.1)

    def test_start_raises_when_process_exits_during_wait(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            server_cfg, llm_cfg = _build_configs(Path(tmpdir))
            proc = LlmServerProcess(server_cfg=server_cfg, llm_cfg=llm_cfg)

            fake_proc = MagicMock()
            fake_proc.poll.return_value = 1
            fake_proc.stdout.read.return_value = "startup error"

            with patch("nlp.llm.llm_server_process.subprocess.Popen", return_value=fake_proc):
                with self.assertRaises(RuntimeError):
                    proc.start(wait_s=1)

    def test_start_times_out_when_wait_window_expires(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            server_cfg, llm_cfg = _build_configs(Path(tmpdir))
            proc = LlmServerProcess(server_cfg=server_cfg, llm_cfg=llm_cfg)
            fake_proc = MagicMock()
            fake_proc.poll.return_value = None

            with patch("nlp.llm.llm_server_process.subprocess.Popen", return_value=fake_proc):
                with self.assertRaises(TimeoutError):
                    proc.start(wait_s=0)

    def test_stop_kills_when_wait_times_out(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            server_cfg, llm_cfg = _build_configs(Path(tmpdir))
            proc = LlmServerProcess(server_cfg=server_cfg, llm_cfg=llm_cfg)
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
