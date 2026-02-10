from __future__ import annotations

import os
import sys
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

from app.bootstrap_llm import (
    bootstrap_llm,
    ensure_en_core_web_sm,
    ensure_gguf,
    ensure_llm_server_bin,
    ensure_mmproj,
    get_app_base_dir,
)
from app.settings import AppConfig
from config.assessment_paths_config import AssessmentPathsConfig
from config.ged_config import GedConfig
from config.llm_config import LlmConfig
from config.llm_request_config import LlmRequestConfig
from config.llm_server_config import LlmServerConfig
from config.ocr_config import OcrConfig
from config.run_config import RunConfig
from config.sustainability_config import SustainabilityConfig


def _build_app_cfg(root: Path) -> AppConfig:
    server_bin = root / ".appdata" / "build" / "llama.cpp" / "bin" / "llama-server"
    server_bin.parent.mkdir(parents=True, exist_ok=True)
    server_bin.write_text("bin", encoding="utf-8")
    return AppConfig(
        assessment_paths=AssessmentPathsConfig.from_strings(
            input_folder=root / "Assessment" / "in",
            output_folder=root / "Assessment" / "out",
            explained_folder=root / "Assessment" / "explained",
        ),
        llm_config=LlmConfig.from_strings(
            hf_repo_id="repo/demo",
            hf_filename="model.gguf",
            hf_revision=None,
            hf_mmproj_filename=None,
            llama_server_model="demo",
            llama_model_key="demo",
            llama_model_display_name="Demo",
            llama_model_alias="Demo",
            llama_model_family="instruct",
        ),
        llm_server=LlmServerConfig.from_strings(
            llama_backend="server",
            llama_server_path=server_bin,
            llama_server_url="http://127.0.0.1:8080/v1/chat/completions",
            llama_n_ctx=4096,
            llama_host="127.0.0.1",
            llama_port=8080,
            llama_n_threads=None,
            llama_n_gpu_layers=99,
            llama_n_batch=None,
            llama_n_parallel=4,
            llama_seed=None,
            llama_rope_freq_base=None,
            llama_rope_freq_scale=None,
            llama_use_jinja=True,
            llama_cache_prompt=True,
            llama_flash_attn=True,
        ),
        llm_request=LlmRequestConfig.from_values(
            max_tokens=1024,
            temperature=0.2,
            top_p=0.95,
            top_k=40,
            repeat_penalty=1.1,
            seed=None,
            stop=None,
            response_format=None,
            stream=False,
        ),
        ocr_config=OcrConfig.from_strings(
            ocr_server_model="server",
            ocr_model_key="ocr-default",
            ocr_model_display_name="Default OCR",
            ocr_model_alias="Default OCR",
            ocr_model_family="ocr/vision",
        ),
        ged_config=GedConfig.from_strings(model_name="gotutiyan/token-ged-bert-large-cased-bin"),
        run_config=RunConfig.from_strings(author="tester"),
        sustainability_config=SustainabilityConfig.from_values(),
    )


class BootstrapLlmTests(unittest.TestCase):
    def test_ensure_en_core_web_sm_no_download_when_present(self) -> None:
        fake_spacy = SimpleNamespace(
            util=SimpleNamespace(is_package=lambda name: True),
            cli=SimpleNamespace(download=lambda name: None),
        )
        with patch.dict(sys.modules, {"spacy": fake_spacy}):
            ensure_en_core_web_sm()

    def test_ensure_en_core_web_sm_downloads_when_missing(self) -> None:
        calls: list[str] = []
        state = {"present": False}

        def _is_package(_: str) -> bool:
            return state["present"]

        def _download(name: str) -> None:
            calls.append(name)
            state["present"] = True

        fake_spacy = SimpleNamespace(
            util=SimpleNamespace(is_package=_is_package),
            cli=SimpleNamespace(download=_download),
        )
        with patch.dict(sys.modules, {"spacy": fake_spacy}):
            ensure_en_core_web_sm()
        self.assertEqual(calls, ["en_core_web_sm"])

    def test_ensure_en_core_web_sm_raises_when_spacy_missing(self) -> None:
        with patch.dict(sys.modules, {"spacy": None}):
            with self.assertRaises(RuntimeError):
                ensure_en_core_web_sm()

    def test_ensure_en_core_web_sm_raises_on_download_failure(self) -> None:
        def _download(_: str) -> None:
            raise Exception("network error")

        fake_spacy = SimpleNamespace(
            util=SimpleNamespace(is_package=lambda name: False),
            cli=SimpleNamespace(download=_download),
        )
        with patch.dict(sys.modules, {"spacy": fake_spacy}):
            with self.assertRaises(RuntimeError):
                ensure_en_core_web_sm()

    def test_ensure_en_core_web_sm_raises_when_still_missing_after_download(self) -> None:
        fake_spacy = SimpleNamespace(
            util=SimpleNamespace(is_package=lambda name: False),
            cli=SimpleNamespace(download=lambda name: None),
        )
        with patch.dict(sys.modules, {"spacy": fake_spacy}):
            with self.assertRaises(RuntimeError):
                ensure_en_core_web_sm()

    def test_get_app_base_dir_uses_appdata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            prev = Path.cwd()
            os.chdir(tmpdir)
            try:
                self.assertEqual(get_app_base_dir(), Path(".appdata").resolve())
            finally:
                os.chdir(prev)

    def test_ensure_gguf_uses_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            cfg = _build_app_cfg(root)
            gguf = root / ".appdata" / "models" / "model.gguf"
            gguf.parent.mkdir(parents=True, exist_ok=True)
            gguf.write_text("x", encoding="utf-8")
            cfg = AppConfig(
                assessment_paths=cfg.assessment_paths,
                llm_config=LlmConfig.from_strings(
                    hf_repo_id="repo/demo",
                    hf_filename="model.gguf",
                    llama_gguf_path=gguf,
                    llama_server_model="demo",
                    llama_model_key="demo",
                    llama_model_display_name="Demo",
                    llama_model_alias="Demo",
                    llama_model_family="instruct",
                ),
                llm_server=cfg.llm_server,
                llm_request=cfg.llm_request,
                ocr_config=cfg.ocr_config,
                ged_config=cfg.ged_config,
                run_config=cfg.run_config,
                sustainability_config=cfg.sustainability_config,
            )

            with patch("app.bootstrap_llm.hf_hub_download") as mocked:
                resolved = ensure_gguf(cfg, gguf.parent)
            self.assertEqual(resolved, gguf.resolve())
            mocked.assert_not_called()

    def test_ensure_gguf_downloads_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            cfg = _build_app_cfg(root)
            models_dir = root / ".appdata" / "models"

            def _fake_download(**kwargs):
                target = Path(kwargs["local_dir"]) / kwargs["filename"]
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("x", encoding="utf-8")
                return str(target)

            with patch("app.bootstrap_llm.hf_hub_download", side_effect=_fake_download):
                resolved = ensure_gguf(cfg, models_dir)
            self.assertTrue(resolved.exists())
            self.assertEqual(resolved.name, "model.gguf")

    def test_ensure_gguf_raises_when_hf_metadata_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            cfg = _build_app_cfg(root)
            cfg = AppConfig(
                assessment_paths=cfg.assessment_paths,
                llm_config=LlmConfig.from_strings(
                    llama_server_model="demo",
                    llama_model_key="demo",
                    llama_model_display_name="Demo",
                    llama_model_alias="Demo",
                    llama_model_family="instruct",
                ),
                llm_server=cfg.llm_server,
                llm_request=cfg.llm_request,
                ocr_config=cfg.ocr_config,
                ged_config=cfg.ged_config,
                run_config=cfg.run_config,
                sustainability_config=cfg.sustainability_config,
            )
            with self.assertRaises(RuntimeError):
                ensure_gguf(cfg, root / ".appdata" / "models")

    def test_ensure_mmproj_returns_none_when_not_configured(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            cfg = _build_app_cfg(root)
            self.assertIsNone(ensure_mmproj(cfg, root / ".appdata" / "models"))

    def test_ensure_mmproj_downloads_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            cfg = _build_app_cfg(root)
            cfg = AppConfig(
                assessment_paths=cfg.assessment_paths,
                llm_config=LlmConfig.from_strings(
                    hf_repo_id="repo/demo",
                    hf_filename="model.gguf",
                    hf_mmproj_filename="mmproj.gguf",
                    llama_server_model="demo",
                    llama_model_key="demo",
                    llama_model_display_name="Demo",
                    llama_model_alias="Demo",
                    llama_model_family="instruct",
                ),
                llm_server=cfg.llm_server,
                llm_request=cfg.llm_request,
                ocr_config=cfg.ocr_config,
                ged_config=cfg.ged_config,
                run_config=cfg.run_config,
                sustainability_config=cfg.sustainability_config,
            )

            def _fake_download(**kwargs):
                target = Path(kwargs["local_dir"]) / kwargs["filename"]
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("x", encoding="utf-8")
                return str(target)

            with patch("app.bootstrap_llm.hf_hub_download", side_effect=_fake_download):
                resolved = ensure_mmproj(cfg, root / ".appdata" / "models")
            self.assertIsNotNone(resolved)
            self.assertTrue(resolved.exists())

    def test_ensure_llm_server_bin_raises_on_missing_binary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            cfg = _build_app_cfg(root)
            missing_server = root / ".appdata" / "build" / "llama.cpp" / "bin" / "missing-server"
            cfg = AppConfig(
                assessment_paths=cfg.assessment_paths,
                llm_config=cfg.llm_config,
                llm_server=LlmServerConfig.from_strings(
                    llama_backend="server",
                    llama_server_path=missing_server,
                    llama_server_url=cfg.llm_server.llama_server_url,
                    llama_n_ctx=cfg.llm_server.llama_n_ctx,
                    llama_host=cfg.llm_server.llama_host,
                    llama_port=cfg.llm_server.llama_port,
                    llama_n_threads=cfg.llm_server.llama_n_threads,
                    llama_n_gpu_layers=cfg.llm_server.llama_n_gpu_layers,
                    llama_n_batch=cfg.llm_server.llama_n_batch,
                    llama_n_parallel=cfg.llm_server.llama_n_parallel,
                    llama_seed=cfg.llm_server.llama_seed,
                    llama_rope_freq_base=cfg.llm_server.llama_rope_freq_base,
                    llama_rope_freq_scale=cfg.llm_server.llama_rope_freq_scale,
                    llama_use_jinja=cfg.llm_server.llama_use_jinja,
                    llama_cache_prompt=cfg.llm_server.llama_cache_prompt,
                    llama_flash_attn=cfg.llm_server.llama_flash_attn,
                ),
                llm_request=cfg.llm_request,
                ocr_config=cfg.ocr_config,
                ged_config=cfg.ged_config,
                run_config=cfg.run_config,
                sustainability_config=cfg.sustainability_config,
            )
            with self.assertRaises(RuntimeError):
                ensure_llm_server_bin(cfg)

    def test_bootstrap_llm_integration_updates_resolved_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prev = Path.cwd()
            os.chdir(root)
            try:
                cfg = _build_app_cfg(root)
                cfg = AppConfig(
                    assessment_paths=cfg.assessment_paths,
                    llm_config=LlmConfig.from_strings(
                        hf_repo_id="repo/demo",
                        hf_filename="model.gguf",
                        hf_mmproj_filename="mmproj.gguf",
                        llama_server_model="demo",
                        llama_model_key="demo",
                        llama_model_display_name="Demo",
                        llama_model_alias="Demo",
                        llama_model_family="instruct",
                    ),
                    llm_server=cfg.llm_server,
                    llm_request=cfg.llm_request,
                    ocr_config=cfg.ocr_config,
                    ged_config=cfg.ged_config,
                    run_config=cfg.run_config,
                sustainability_config=cfg.sustainability_config,
                )

                def _fake_download(**kwargs):
                    target = Path(kwargs["local_dir"]) / kwargs["filename"]
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text("x", encoding="utf-8")
                    return str(target)

                with patch("app.bootstrap_llm.ensure_en_core_web_sm"):
                    with patch("app.bootstrap_llm.hf_hub_download", side_effect=_fake_download):
                        updated = bootstrap_llm(cfg)

                self.assertIsNotNone(updated.llm_config.llama_gguf_path)
                self.assertTrue(updated.llm_config.llama_gguf_path.exists())
                self.assertIsNotNone(updated.llm_config.llama_mmproj_path)
                self.assertTrue(updated.llm_config.llama_mmproj_path.exists())
            finally:
                os.chdir(prev)

    def test_bootstrap_llm_raises_on_download_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prev = Path.cwd()
            os.chdir(root)
            try:
                cfg = _build_app_cfg(root)
                with patch("app.bootstrap_llm.ensure_en_core_web_sm"):
                    with patch("app.bootstrap_llm.hf_hub_download", side_effect=Exception("network error")):
                        with self.assertRaises(RuntimeError):
                            bootstrap_llm(cfg)
            finally:
                os.chdir(prev)

    def test_bootstrap_llm_calls_ensure_spacy_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            prev = Path.cwd()
            os.chdir(root)
            try:
                cfg = _build_app_cfg(root)

                def _fake_download(**kwargs):
                    target = Path(kwargs["local_dir"]) / kwargs["filename"]
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text("x", encoding="utf-8")
                    return str(target)

                with patch("app.bootstrap_llm.ensure_en_core_web_sm") as ensure_spacy_mock:
                    with patch("app.bootstrap_llm.hf_hub_download", side_effect=_fake_download):
                        bootstrap_llm(cfg)
                ensure_spacy_mock.assert_called_once()
            finally:
                os.chdir(prev)


if __name__ == "__main__":
    unittest.main()
