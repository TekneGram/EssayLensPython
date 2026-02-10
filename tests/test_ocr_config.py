from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from config.ocr_config import OcrConfig


class OcrConfigTests(unittest.TestCase):
    def test_from_strings_normalizes_optional_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            gguf = root / "model.gguf"
            mmproj = root / "mmproj.gguf"
            gguf.write_text("x", encoding="utf-8")
            mmproj.write_text("x", encoding="utf-8")

            cfg = OcrConfig.from_strings(
                ocr_gguf_path=gguf,
                ocr_mmproj_path=mmproj,
                ocr_server_model="server",
                ocr_model_key="demo",
                ocr_model_display_name="Demo OCR",
                ocr_model_alias="demo-ocr",
                ocr_model_family="ocr/vision",
            )

            self.assertEqual(cfg.ocr_gguf_path, gguf.resolve())
            self.assertEqual(cfg.ocr_mmproj_path, mmproj.resolve())

    def test_validate_allows_unresolved_model_paths_when_enabled(self) -> None:
        cfg = OcrConfig.from_strings(
            ocr_server_model="server",
            ocr_model_key="demo",
            ocr_model_display_name="Demo OCR",
            ocr_model_alias="demo-ocr",
            ocr_model_family="ocr/vision",
        )
        cfg.validate(allow_unresolved_model_paths=True)

    def test_validate_rejects_missing_model_source_when_required(self) -> None:
        cfg = OcrConfig.from_strings(
            ocr_server_model="server",
            ocr_model_key="demo",
            ocr_model_display_name="Demo OCR",
            ocr_model_alias="demo-ocr",
            ocr_model_family="ocr/vision",
        )
        with self.assertRaises(ValueError):
            cfg.validate(allow_unresolved_model_paths=False)

    def test_validate_accepts_hf_source(self) -> None:
        cfg = OcrConfig.from_strings(
            hf_repo_id="repo/demo",
            hf_filename="model.gguf",
            ocr_server_model="server",
            ocr_model_key="demo",
            ocr_model_display_name="Demo OCR",
            ocr_model_alias="demo-ocr",
            ocr_model_family="ocr/vision",
        )
        cfg.validate(allow_unresolved_model_paths=False)

    def test_validate_rejects_missing_local_gguf_path(self) -> None:
        cfg = OcrConfig.from_strings(
            ocr_gguf_path="missing.gguf",
            ocr_server_model="server",
            ocr_model_key="demo",
            ocr_model_display_name="Demo OCR",
            ocr_model_alias="demo-ocr",
            ocr_model_family="ocr/vision",
        )
        with self.assertRaises(ValueError):
            cfg.validate()


if __name__ == "__main__":
    unittest.main()
