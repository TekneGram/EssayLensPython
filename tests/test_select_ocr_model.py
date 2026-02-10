from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.select_ocr_model import (
    _ensure_hf_download,
    _ocr_persist_path,
    load_persisted_ocr_key,
    resolve_default_ocr_spec,
    select_ocr_model_and_update_config,
)
from app.settings import AppConfig
from config.assessment_paths_config import AssessmentPathsConfig
from config.ged_config import GedConfig
from config.llm_config import LlmConfig
from config.llm_request_config import LlmRequestConfig
from config.llm_server_config import LlmServerConfig
from config.ocr_config import OcrConfig
from config.ocr_model_spec import OcrModelSpec
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
            llama_server_model="demo",
            llama_model_key="demo",
            llama_model_display_name="Demo",
            llama_model_alias="demo",
            llama_model_family="instruct",
        ),
        ocr_config=OcrConfig.from_strings(
            hf_repo_id=None,
            hf_filename=None,
            hf_revision="main",
            hf_mmproj_filename=None,
            ocr_server_model="server",
            ocr_model_key="default_ocr",
            ocr_model_display_name="Default OCR",
            ocr_model_alias="default-ocr",
            ocr_model_family="ocr/vision",
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
            llama_n_parallel=3,
            llama_seed=None,
            llama_rope_freq_base=None,
            llama_rope_freq_scale=None,
            llama_use_jinja=True,
            llama_cache_prompt=True,
            llama_flash_attn=True,
        ),
        llm_request=LlmRequestConfig.from_values(
            max_tokens=256,
            temperature=0.2,
            top_p=0.9,
            top_k=40,
            repeat_penalty=1.1,
            seed=None,
            stop=None,
            response_format=None,
            stream=False,
        ),
        ged_config=GedConfig.from_strings(model_name="ged-model"),
        run_config=RunConfig.from_strings(author="tester"),
        sustainability_config=SustainabilityConfig.from_values(),
    )


class SelectOcrModelTests(unittest.TestCase):
    def test_resolve_default_ocr_spec_raises_when_empty(self) -> None:
        with self.assertRaises(RuntimeError):
            resolve_default_ocr_spec([], persisted_key=None)

    def test_load_persisted_ocr_key_handles_bad_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            persist_path = _ocr_persist_path(base_dir)
            persist_path.parent.mkdir(parents=True, exist_ok=True)
            persist_path.write_text("{bad json", encoding="utf-8")
            self.assertIsNone(load_persisted_ocr_key(base_dir))

    def test_select_ocr_model_skips_download_when_artifacts_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            prev_cwd = Path.cwd()
            os.chdir(tmpdir)
            try:
                root = Path(tmpdir)
                cfg = _build_app_cfg(root)
                spec = OcrModelSpec(
                    key="ocr-a",
                    display_name="OCR A",
                    hf_repo_id="repo/ocr-a",
                    hf_filename="ocr-a.gguf",
                    mmproj_filename="ocr-a-mmproj.gguf",
                    backend="server",
                    model_family="ocr/vision",
                    min_ram_gb=4,
                    min_vram_gb=4,
                    param_size_b=1,
                    notes="n",
                )
                models_dir = Path(".appdata/models")
                models_dir.mkdir(parents=True, exist_ok=True)
                (models_dir / spec.hf_filename).write_text("x", encoding="utf-8")
                (models_dir / spec.mmproj_filename).write_text("x", encoding="utf-8")

                with patch("app.select_ocr_model.OCR_MODEL_SPECS", [spec]), patch(
                    "app.select_ocr_model._ensure_hf_download"
                ) as download_mock, patch(
                    "builtins.print"
                ):
                    updated = select_ocr_model_and_update_config(cfg)

                download_mock.assert_not_called()
                self.assertEqual(updated.ocr_config.ocr_model_key, "ocr-a")
                self.assertTrue(updated.ocr_config.ocr_gguf_path.exists())
                self.assertTrue(updated.ocr_config.ocr_mmproj_path.exists())
            finally:
                os.chdir(prev_cwd)

    def test_select_ocr_model_downloads_missing_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            prev_cwd = Path.cwd()
            os.chdir(tmpdir)
            try:
                root = Path(tmpdir)
                cfg = _build_app_cfg(root)
                spec = OcrModelSpec(
                    key="ocr-b",
                    display_name="OCR B",
                    hf_repo_id="repo/ocr-b",
                    hf_filename="ocr-b.gguf",
                    mmproj_filename="ocr-b-mmproj.gguf",
                    backend="server",
                    model_family="ocr/vision",
                    min_ram_gb=4,
                    min_vram_gb=4,
                    param_size_b=1,
                    notes="n",
                )

                def _fake_download(*, repo_id: str, filename: str, revision: str | None, models_dir: Path) -> Path:
                    _ = (repo_id, revision)
                    target = models_dir / filename
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text("x", encoding="utf-8")
                    return target.resolve()

                with patch("app.select_ocr_model.OCR_MODEL_SPECS", [spec]), patch(
                    "app.select_ocr_model._ensure_hf_download",
                    side_effect=_fake_download,
                ) as download_mock, patch(
                    "builtins.print"
                ):
                    updated = select_ocr_model_and_update_config(cfg)

                self.assertEqual(download_mock.call_count, 2)
                self.assertTrue(updated.ocr_config.ocr_gguf_path.exists())
                self.assertTrue(updated.ocr_config.ocr_mmproj_path.exists())
            finally:
                os.chdir(prev_cwd)

    def test_select_ocr_model_uses_persisted_key_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            prev_cwd = Path.cwd()
            os.chdir(tmpdir)
            try:
                root = Path(tmpdir)
                cfg = _build_app_cfg(root)

                spec_a = OcrModelSpec(
                    key="ocr-a",
                    display_name="OCR A",
                    hf_repo_id="repo/ocr-a",
                    hf_filename="ocr-a.gguf",
                    mmproj_filename="ocr-a-mmproj.gguf",
                    backend="server",
                    model_family="ocr/vision",
                    min_ram_gb=4,
                    min_vram_gb=4,
                    param_size_b=1,
                    notes="n",
                )
                spec_b = OcrModelSpec(
                    key="ocr-b",
                    display_name="OCR B",
                    hf_repo_id="repo/ocr-b",
                    hf_filename="ocr-b.gguf",
                    mmproj_filename="ocr-b-mmproj.gguf",
                    backend="server",
                    model_family="ocr/vision",
                    min_ram_gb=4,
                    min_vram_gb=4,
                    param_size_b=1,
                    notes="n",
                )

                persist_path = Path(".appdata/config/ocr_model.json")
                persist_path.parent.mkdir(parents=True, exist_ok=True)
                persist_path.write_text('{"model_key":"ocr-b"}', encoding="utf-8")

                def _fake_download(*, repo_id: str, filename: str, revision: str | None, models_dir: Path) -> Path:
                    _ = (repo_id, revision)
                    target = models_dir / filename
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text("x", encoding="utf-8")
                    return target.resolve()

                with patch("app.select_ocr_model.OCR_MODEL_SPECS", [spec_a, spec_b]), patch(
                    "app.select_ocr_model._ensure_hf_download",
                    side_effect=_fake_download,
                ), patch(
                    "builtins.print"
                ):
                    updated = select_ocr_model_and_update_config(cfg)

                self.assertEqual(updated.ocr_config.ocr_model_key, "ocr-b")
            finally:
                os.chdir(prev_cwd)

    def test_ensure_hf_download_raises_when_dependency_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.select_ocr_model.hf_hub_download", None):
                with self.assertRaises(RuntimeError):
                    _ensure_hf_download(
                        repo_id="repo/demo",
                        filename="x.gguf",
                        revision=None,
                        models_dir=Path(tmpdir),
                    )


if __name__ == "__main__":
    unittest.main()
