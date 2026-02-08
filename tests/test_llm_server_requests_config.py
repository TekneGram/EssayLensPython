from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.settings import build_settings
from config.llm_request_config import LlmRequestConfig
from config.llm_server_config import LlmServerConfig


class LlmServerConfigTests(unittest.TestCase):
    def test_from_strings_normalizes_server_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            server_bin = tmp / "llama-server"
            server_bin.write_text("bin", encoding="utf-8")

            cfg = LlmServerConfig.from_strings(
                llama_backend="server",
                llama_server_path=server_bin,
                llama_server_url="http://127.0.0.1:8080",
                llama_n_ctx=4096,
                llama_host="127.0.0.1",
                llama_port=8080,
                llama_n_threads=4,
                llama_n_gpu_layers=99,
                llama_n_batch=512,
                llama_n_parallel=4,
                llama_seed=0,
                llama_rope_freq_base=10000.0,
                llama_rope_freq_scale=1.0,
                llama_use_jinja=True,
                llama_cache_prompt=True,
                llama_flash_attn=True,
            )

            self.assertEqual(cfg.llama_server_path, server_bin.resolve())

    def test_validate_rejects_invalid_port(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            server_bin = tmp / "llama-server"
            server_bin.write_text("bin", encoding="utf-8")

            cfg = LlmServerConfig.from_strings(
                llama_backend="server",
                llama_server_path=server_bin,
                llama_server_url="http://127.0.0.1:8080",
                llama_n_ctx=4096,
                llama_host="127.0.0.1",
                llama_port=0,
                llama_n_threads=4,
                llama_n_gpu_layers=99,
                llama_n_batch=512,
                llama_n_parallel=4,
                llama_seed=0,
                llama_rope_freq_base=10000.0,
                llama_rope_freq_scale=1.0,
                llama_use_jinja=True,
                llama_cache_prompt=True,
                llama_flash_attn=True,
            )

            with self.assertRaises(ValueError):
                cfg.validate()

    def test_validate_rejects_non_positive_ctx(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            server_bin = tmp / "llama-server"
            server_bin.write_text("bin", encoding="utf-8")

            cfg = LlmServerConfig.from_strings(
                llama_backend="server",
                llama_server_path=server_bin,
                llama_server_url="http://127.0.0.1:8080",
                llama_n_ctx=0,
                llama_host="127.0.0.1",
                llama_port=8080,
                llama_n_threads=4,
                llama_n_gpu_layers=99,
                llama_n_batch=512,
                llama_n_parallel=4,
                llama_seed=0,
                llama_rope_freq_base=10000.0,
                llama_rope_freq_scale=1.0,
                llama_use_jinja=True,
                llama_cache_prompt=True,
                llama_flash_attn=True,
            )

            with self.assertRaises(ValueError):
                cfg.validate()

    def test_validate_rejects_invalid_optional_numbers(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            server_bin = tmp / "llama-server"
            server_bin.write_text("bin", encoding="utf-8")

            cfg = LlmServerConfig.from_strings(
                llama_backend="server",
                llama_server_path=server_bin,
                llama_server_url="http://127.0.0.1:8080",
                llama_n_ctx=4096,
                llama_host="127.0.0.1",
                llama_port=8080,
                llama_n_threads=0,
                llama_n_gpu_layers=-1,
                llama_n_batch=0,
                llama_n_parallel=0,
                llama_seed=0,
                llama_rope_freq_base=0.0,
                llama_rope_freq_scale=0.0,
                llama_use_jinja=True,
                llama_cache_prompt=True,
                llama_flash_attn=True,
            )

            with self.assertRaises(ValueError):
                cfg.validate()

    def test_validate_rejects_missing_server_identity_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            server_bin = tmp / "llama-server"
            server_bin.write_text("bin", encoding="utf-8")

            cfg = LlmServerConfig.from_strings(
                llama_backend="server",
                llama_server_path=server_bin,
                llama_server_url="",
                llama_n_ctx=4096,
                llama_host="",
                llama_port=8080,
                llama_n_threads=4,
                llama_n_gpu_layers=99,
                llama_n_batch=512,
                llama_n_parallel=4,
                llama_seed=0,
                llama_rope_freq_base=10000.0,
                llama_rope_freq_scale=1.0,
                llama_use_jinja=True,
                llama_cache_prompt=True,
                llama_flash_attn=True,
            )

            with self.assertRaises(ValueError):
                cfg.validate()

    def test_validate_rejects_non_positive_parallel(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            server_bin = tmp / "llama-server"
            server_bin.write_text("bin", encoding="utf-8")

            cfg = LlmServerConfig.from_strings(
                llama_backend="server",
                llama_server_path=server_bin,
                llama_server_url="http://127.0.0.1:8080",
                llama_n_ctx=4096,
                llama_host="127.0.0.1",
                llama_port=8080,
                llama_n_threads=4,
                llama_n_gpu_layers=99,
                llama_n_batch=512,
                llama_n_parallel=0,
                llama_seed=0,
                llama_rope_freq_base=10000.0,
                llama_rope_freq_scale=1.0,
                llama_use_jinja=True,
                llama_cache_prompt=True,
                llama_flash_attn=True,
            )

            with self.assertRaises(ValueError):
                cfg.validate()

    def test_validate_accepts_positive_parallel(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            server_bin = tmp / "llama-server"
            server_bin.write_text("bin", encoding="utf-8")

            cfg = LlmServerConfig.from_strings(
                llama_backend="server",
                llama_server_path=server_bin,
                llama_server_url="http://127.0.0.1:8080",
                llama_n_ctx=4096,
                llama_host="127.0.0.1",
                llama_port=8080,
                llama_n_threads=4,
                llama_n_gpu_layers=99,
                llama_n_batch=512,
                llama_n_parallel=8,
                llama_seed=0,
                llama_rope_freq_base=10000.0,
                llama_rope_freq_scale=1.0,
                llama_use_jinja=True,
                llama_cache_prompt=True,
                llama_flash_attn=True,
            )
            cfg.validate()


class LlmRequestConfigTests(unittest.TestCase):
    def test_validate_rejects_non_positive_max_tokens(self) -> None:
        cfg = LlmRequestConfig.from_values(
            default_max_tokens=0,
            default_temperature=0.2,
            default_top_p=0.9,
            default_top_k=40,
            default_repeat_penalty=1.1,
            default_seed=None,
            default_stop=None,
            default_response_format=None,
            default_stream=False,
        )
        with self.assertRaises(ValueError):
            cfg.validate()

    def test_validate_rejects_invalid_top_p(self) -> None:
        cfg = LlmRequestConfig.from_values(
            default_max_tokens=256,
            default_temperature=0.2,
            default_top_p=2.0,
            default_top_k=40,
            default_repeat_penalty=1.1,
            default_seed=None,
            default_stop=None,
            default_response_format=None,
            default_stream=False,
        )
        with self.assertRaises(ValueError):
            cfg.validate()

    def test_validate_rejects_invalid_top_k(self) -> None:
        cfg = LlmRequestConfig.from_values(
            default_max_tokens=256,
            default_temperature=0.2,
            default_top_p=0.9,
            default_top_k=0,
            default_repeat_penalty=1.1,
            default_seed=None,
            default_stop=None,
            default_response_format=None,
            default_stream=False,
        )
        with self.assertRaises(ValueError):
            cfg.validate()

    def test_validate_rejects_invalid_stop_tokens(self) -> None:
        cfg = LlmRequestConfig.from_values(
            default_max_tokens=256,
            default_temperature=0.2,
            default_top_p=0.9,
            default_top_k=40,
            default_repeat_penalty=1.1,
            default_seed=None,
            default_stop=["", "  "],
            default_response_format=None,
            default_stream=False,
        )
        with self.assertRaises(ValueError):
            cfg.validate()


class BuildSettingsTests(unittest.TestCase):
    def test_build_settings_populates_all_configs(self) -> None:
        cfg = build_settings()
        self.assertIsNotNone(cfg.assessment_paths)
        self.assertIsNotNone(cfg.llm_config)
        self.assertIsNotNone(cfg.llm_server)
        self.assertIsNotNone(cfg.llm_request)
        self.assertIsNotNone(cfg.ged_config)
        self.assertTrue(cfg.ged_config.model_name.strip())
        self.assertGreater(cfg.ged_config.batch_size, 0)
        self.assertIsNotNone(cfg.run_config)
        self.assertTrue(cfg.run_config.author.strip())


if __name__ == "__main__":
    unittest.main()
