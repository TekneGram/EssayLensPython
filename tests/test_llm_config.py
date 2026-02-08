from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from config.llm_config import LlmConfig


class LlmConfigTests(unittest.TestCase):
    def test_from_strings_normalizes_optional_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            gguf_file = tmp / "model.gguf"
            mmproj_file = tmp / "mmproj.gguf"
            gguf_file.write_text("gguf", encoding="utf-8")
            mmproj_file.write_text("mmproj", encoding="utf-8")

            cfg = LlmConfig.from_strings(
                llama_gguf_path=gguf_file,
                llama_mmproj_path=mmproj_file,
                llama_server_model="llama",
                llama_model_key="default",
                llama_model_display_name="Default Model",
                llama_model_alias="default",
                llama_model_family="llama",
            )

            self.assertEqual(cfg.llama_gguf_path, gguf_file.resolve())
            self.assertEqual(cfg.llama_mmproj_path, mmproj_file.resolve())

    def test_from_strings_empty_paths_become_none(self) -> None:
        cfg = LlmConfig.from_strings(
            llama_gguf_path="",
            llama_mmproj_path="",
            llama_server_model="llama",
            llama_model_key="default",
            llama_model_display_name="Default Model",
            llama_model_alias="default",
            llama_model_family="llama",
        )
        self.assertIsNone(cfg.llama_gguf_path)
        self.assertIsNone(cfg.llama_mmproj_path)

    def test_validate_passes_for_local_path_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            gguf_file = Path(tmpdir) / "model.gguf"
            gguf_file.write_text("gguf", encoding="utf-8")
            cfg = LlmConfig.from_strings(
                llama_gguf_path=gguf_file,
                llama_server_model="llama",
                llama_model_key="default",
                llama_model_display_name="Default Model",
                llama_model_alias="default",
                llama_model_family="llama",
            )
            cfg.validate()

    def test_validate_passes_for_hf_source(self) -> None:
        cfg = LlmConfig.from_strings(
            hf_repo_id="meta-llama/Meta-Llama-3-8B-Instruct-GGUF",
            hf_filename="model.gguf",
            llama_server_model="llama",
            llama_model_key="default",
            llama_model_display_name="Default Model",
            llama_model_alias="default",
            llama_model_family="llama",
        )
        cfg.validate()

    def test_validate_fails_without_any_source(self) -> None:
        cfg = LlmConfig.from_strings(
            llama_server_model="llama",
            llama_model_key="default",
            llama_model_display_name="Default Model",
            llama_model_alias="default",
            llama_model_family="llama",
        )
        with self.assertRaises(ValueError):
            cfg.validate()

    def test_validate_allows_bootstrap_without_source(self) -> None:
        cfg = LlmConfig.from_strings(
            llama_server_model="llama",
            llama_model_key="default",
            llama_model_display_name="Default Model",
            llama_model_alias="default",
            llama_model_family="llama",
        )
        cfg.validate(allow_unresolved_model_paths=True)

    def test_validate_fails_for_empty_identity_fields(self) -> None:
        cfg = LlmConfig.from_strings(
            hf_repo_id="meta-llama/Meta-Llama-3-8B-Instruct-GGUF",
            hf_filename="model.gguf",
            llama_server_model="",
            llama_model_key="",
            llama_model_display_name="",
            llama_model_alias="",
            llama_model_family="",
        )
        with self.assertRaises(ValueError):
            cfg.validate()

    def test_validate_fails_for_missing_local_path(self) -> None:
        cfg = LlmConfig.from_strings(
            llama_gguf_path="does/not/exist.gguf",
            llama_server_model="llama",
            llama_model_key="default",
            llama_model_display_name="Default Model",
            llama_model_alias="default",
            llama_model_family="llama",
        )
        with self.assertRaises(ValueError):
            cfg.validate()

    def test_validate_fails_for_non_file_mmproj_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mmproj_dir = Path(tmpdir) / "mmproj_dir"
            mmproj_dir.mkdir()
            cfg = LlmConfig.from_strings(
                hf_repo_id="meta-llama/Meta-Llama-3-8B-Instruct-GGUF",
                hf_filename="model.gguf",
                llama_mmproj_path=mmproj_dir,
                llama_server_model="llama",
                llama_model_key="default",
                llama_model_display_name="Default Model",
                llama_model_alias="default",
                llama_model_family="llama",
            )
            with self.assertRaises(ValueError):
                cfg.validate()


if __name__ == "__main__":
    unittest.main()
