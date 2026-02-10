from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.select_model import (
    _persist_path,
    get_models_dir,
    is_model_downloaded,
    list_available_for_download,
    list_downloaded_specs,
    load_persisted_model_key,
    persist_model_key,
    select_model_and_update_config,
    HardwareInfo,
)
from app.settings import AppConfig
from config.assessment_paths_config import AssessmentPathsConfig
from config.ged_config import GedConfig
from config.llm_config import LlmConfig
from config.llm_model_spec import LlmModelSpec
from config.llm_request_config import LlmRequestConfig
from config.llm_server_config import LlmServerConfig
from config.ocr_config import OcrConfig
from config.run_config import RunConfig
from config.sustainability_config import SustainabilityConfig


class SelectModelHelpersTests(unittest.TestCase):
    def test_persist_path_and_models_dir(self) -> None:
        base = Path("/tmp/example").resolve()
        self.assertEqual(_persist_path(base), base / "config" / "llm_model.json")
        self.assertEqual(get_models_dir(base), base / "models")

    def test_is_model_downloaded_with_and_without_mmproj(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            models_dir = Path(tmpdir)
            spec_no_mmproj = LlmModelSpec(
                key="a",
                display_name="A",
                hf_repo_id="repo/a",
                hf_filename="a.gguf",
                mmproj_filename=None,
                backend="server",
                model_family="instruct",
                min_ram_gb=1,
                min_vram_gb=0,
                param_size_b=1,
                notes="n",
            )
            spec_with_mmproj = LlmModelSpec(
                key="b",
                display_name="B",
                hf_repo_id="repo/b",
                hf_filename="b.gguf",
                mmproj_filename="b.mmproj.gguf",
                backend="server",
                model_family="instruct",
                min_ram_gb=1,
                min_vram_gb=0,
                param_size_b=1,
                notes="n",
            )

            self.assertFalse(is_model_downloaded(spec_no_mmproj, models_dir))
            (models_dir / "a.gguf").write_text("x", encoding="utf-8")
            self.assertTrue(is_model_downloaded(spec_no_mmproj, models_dir))

            self.assertFalse(is_model_downloaded(spec_with_mmproj, models_dir))
            (models_dir / "b.gguf").write_text("x", encoding="utf-8")
            self.assertFalse(is_model_downloaded(spec_with_mmproj, models_dir))
            (models_dir / "b.mmproj.gguf").write_text("x", encoding="utf-8")
            self.assertTrue(is_model_downloaded(spec_with_mmproj, models_dir))

    def test_list_partition_by_download_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            models_dir = Path(tmpdir)
            spec_a = LlmModelSpec(
                key="a",
                display_name="A",
                hf_repo_id="repo/a",
                hf_filename="a.gguf",
                mmproj_filename=None,
                backend="server",
                model_family="instruct",
                min_ram_gb=1,
                min_vram_gb=0,
                param_size_b=1,
                notes="n",
            )
            spec_b = LlmModelSpec(
                key="b",
                display_name="B",
                hf_repo_id="repo/b",
                hf_filename="b.gguf",
                mmproj_filename=None,
                backend="server",
                model_family="instruct",
                min_ram_gb=1,
                min_vram_gb=0,
                param_size_b=1,
                notes="n",
            )
            (models_dir / "a.gguf").write_text("x", encoding="utf-8")
            specs = [spec_a, spec_b]

            downloaded = list_downloaded_specs(specs, models_dir)
            available = list_available_for_download(specs, models_dir)
            self.assertEqual([s.key for s in downloaded], ["a"])
            self.assertEqual([s.key for s in available], ["b"])

    def test_load_and_persist_model_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            self.assertIsNone(load_persisted_model_key(base_dir))

            persist_model_key(base_dir, "qwen3_4b_instruct_q8")
            self.assertEqual(load_persisted_model_key(base_dir), "qwen3_4b_instruct_q8")

            # Malformed JSON should be handled gracefully.
            _persist_path(base_dir).write_text("{bad json", encoding="utf-8")
            self.assertIsNone(load_persisted_model_key(base_dir))


class SelectModelIntegrationTests(unittest.TestCase):
    def test_select_model_updates_config_and_persists_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            prev_cwd = Path.cwd()
            os.chdir(tmpdir)
            try:
                appdata = Path(".appdata")
                server_bin = appdata / "build" / "llama.cpp" / "bin" / "llama-server"
                server_bin.parent.mkdir(parents=True, exist_ok=True)
                server_bin.write_text("bin", encoding="utf-8")

                app_cfg = AppConfig(
                    assessment_paths=AssessmentPathsConfig.from_strings(
                        input_folder="Assessment/in",
                        output_folder="Assessment/out",
                        explained_folder="Assessment/explained",
                    ),
                    llm_config=LlmConfig.from_strings(
                        llama_server_model="initial",
                        llama_model_key="initial",
                        llama_model_display_name="Initial",
                        llama_model_alias="Initial",
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
                    ged_config=GedConfig.from_strings(
                        model_name="gotutiyan/token-ged-bert-large-cased-bin"
                    ),
                    run_config=RunConfig.from_strings(author="tester"),
                    sustainability_config=SustainabilityConfig.from_values(),
                )

                with patch(
                    "app.select_model.get_hardware_info",
                    return_value=HardwareInfo(
                        total_ram_gb=64.0,
                        cpu_count=8,
                        cuda_vram_gb=16.0,
                        is_mps=False,
                    ),
                ), patch("app.select_model.prompt_initial_action") as mock_initial_prompt, patch(
                    "builtins.input", side_effect=[""]
                ), patch(
                    "builtins.print"
                ):
                    updated = select_model_and_update_config(app_cfg)

                mock_initial_prompt.assert_not_called()
                self.assertNotEqual(updated.llm_config.llama_model_key, "initial")
                self.assertIsNotNone(updated.llm_config.hf_repo_id)
                self.assertIsNotNone(updated.llm_config.hf_filename)
                self.assertIsNone(updated.llm_config.llama_gguf_path)
                self.assertTrue(
                    Path(".appdata/config/llm_model.json").exists(),
                    "Selected key should be persisted in .appdata/config/llm_model.json",
                )
            finally:
                os.chdir(prev_cwd)

    def test_no_installed_models_forces_download_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            prev_cwd = Path.cwd()
            os.chdir(tmpdir)
            try:
                appdata = Path(".appdata")
                server_bin = appdata / "build" / "llama.cpp" / "bin" / "llama-server"
                server_bin.parent.mkdir(parents=True, exist_ok=True)
                server_bin.write_text("bin", encoding="utf-8")

                app_cfg = AppConfig(
                    assessment_paths=AssessmentPathsConfig.from_strings(
                        input_folder="Assessment/in",
                        output_folder="Assessment/out",
                        explained_folder="Assessment/explained",
                    ),
                    llm_config=LlmConfig.from_strings(
                        llama_server_model="initial",
                        llama_model_key="initial",
                        llama_model_display_name="Initial",
                        llama_model_alias="Initial",
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
                    ged_config=GedConfig.from_strings(
                        model_name="gotutiyan/token-ged-bert-large-cased-bin"
                    ),
                    run_config=RunConfig.from_strings(author="tester"),
                    sustainability_config=SustainabilityConfig.from_values(),
                )

                with patch(
                    "app.select_model.get_hardware_info",
                    return_value=HardwareInfo(
                        total_ram_gb=64.0,
                        cpu_count=8,
                        cuda_vram_gb=16.0,
                        is_mps=False,
                    ),
                ), patch("app.select_model.prompt_initial_action") as mock_initial_prompt, patch(
                    "builtins.input", side_effect=[""]
                ), patch(
                    "builtins.print"
                ):
                    updated = select_model_and_update_config(app_cfg)

                mock_initial_prompt.assert_not_called()
                self.assertIsNone(updated.llm_config.llama_gguf_path)
            finally:
                os.chdir(prev_cwd)

    def test_download_action_shows_only_not_downloaded_models(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            prev_cwd = Path.cwd()
            os.chdir(tmpdir)
            try:
                appdata = Path(".appdata")
                server_bin = appdata / "build" / "llama.cpp" / "bin" / "llama-server"
                models_dir = appdata / "models"
                server_bin.parent.mkdir(parents=True, exist_ok=True)
                models_dir.mkdir(parents=True, exist_ok=True)
                server_bin.write_text("bin", encoding="utf-8")
                # Mark first model as downloaded.
                (models_dir / "Qwen3-4B-Instruct-2507-Q8_0.gguf").write_text("x", encoding="utf-8")

                app_cfg = AppConfig(
                    assessment_paths=AssessmentPathsConfig.from_strings(
                        input_folder="Assessment/in",
                        output_folder="Assessment/out",
                        explained_folder="Assessment/explained",
                    ),
                    llm_config=LlmConfig.from_strings(
                        llama_server_model="initial",
                        llama_model_key="initial",
                        llama_model_display_name="Initial",
                        llama_model_alias="Initial",
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
                    ged_config=GedConfig.from_strings(
                        model_name="gotutiyan/token-ged-bert-large-cased-bin"
                    ),
                    run_config=RunConfig.from_strings(author="tester"),
                    sustainability_config=SustainabilityConfig.from_values(),
                )

                captured_specs: dict[str, list[str]] = {}

                def _capture_choice(specs, recommended, persisted_key, hw, label):
                    captured_specs["keys"] = [s.key for s in specs]
                    return specs[0]

                with patch(
                    "app.select_model.get_hardware_info",
                    return_value=HardwareInfo(
                        total_ram_gb=64.0,
                        cpu_count=8,
                        cuda_vram_gb=16.0,
                        is_mps=False,
                    ),
                ), patch("app.select_model.prompt_initial_action", return_value="download"), patch(
                    "app.select_model.prompt_model_choice_from_list",
                    side_effect=_capture_choice,
                ), patch(
                    "builtins.print"
                ):
                    select_model_and_update_config(app_cfg)

                self.assertEqual(captured_specs["keys"], ["qwen3_4b_q8", "qwen3_8b_q8"])
            finally:
                os.chdir(prev_cwd)

    def test_select_action_shows_only_downloaded_models(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            prev_cwd = Path.cwd()
            os.chdir(tmpdir)
            try:
                appdata = Path(".appdata")
                server_bin = appdata / "build" / "llama.cpp" / "bin" / "llama-server"
                models_dir = appdata / "models"
                server_bin.parent.mkdir(parents=True, exist_ok=True)
                models_dir.mkdir(parents=True, exist_ok=True)
                server_bin.write_text("bin", encoding="utf-8")
                # Mark only first model as downloaded.
                (models_dir / "Qwen3-4B-Instruct-2507-Q8_0.gguf").write_text("x", encoding="utf-8")

                app_cfg = AppConfig(
                    assessment_paths=AssessmentPathsConfig.from_strings(
                        input_folder="Assessment/in",
                        output_folder="Assessment/out",
                        explained_folder="Assessment/explained",
                    ),
                    llm_config=LlmConfig.from_strings(
                        llama_server_model="initial",
                        llama_model_key="initial",
                        llama_model_display_name="Initial",
                        llama_model_alias="Initial",
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
                    ged_config=GedConfig.from_strings(
                        model_name="gotutiyan/token-ged-bert-large-cased-bin"
                    ),
                    run_config=RunConfig.from_strings(author="tester"),
                    sustainability_config=SustainabilityConfig.from_values(),
                )

                captured_specs: dict[str, list[str]] = {}

                def _capture_choice(specs, recommended, persisted_key, hw, label):
                    captured_specs["keys"] = [s.key for s in specs]
                    return specs[0]

                with patch(
                    "app.select_model.get_hardware_info",
                    return_value=HardwareInfo(
                        total_ram_gb=64.0,
                        cpu_count=8,
                        cuda_vram_gb=16.0,
                        is_mps=False,
                    ),
                ), patch("app.select_model.prompt_initial_action", return_value="select"), patch(
                    "app.select_model.prompt_model_choice_from_list",
                    side_effect=_capture_choice,
                ), patch(
                    "builtins.print"
                ):
                    select_model_and_update_config(app_cfg)

                self.assertEqual(captured_specs["keys"], ["qwen3_4b_instruct_q8"])
            finally:
                os.chdir(prev_cwd)

    def test_download_action_falls_back_to_installed_if_everything_downloaded(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            prev_cwd = Path.cwd()
            os.chdir(tmpdir)
            try:
                appdata = Path(".appdata")
                server_bin = appdata / "build" / "llama.cpp" / "bin" / "llama-server"
                models_dir = appdata / "models"
                server_bin.parent.mkdir(parents=True, exist_ok=True)
                models_dir.mkdir(parents=True, exist_ok=True)
                server_bin.write_text("bin", encoding="utf-8")
                # Mark all models as downloaded.
                (models_dir / "Qwen3-4B-Instruct-2507-Q8_0.gguf").write_text("x", encoding="utf-8")
                (models_dir / "Qwen3-4B-Q8_0.gguf").write_text("x", encoding="utf-8")
                (models_dir / "Qwen3-8B-Q8_0.gguf").write_text("x", encoding="utf-8")

                app_cfg = AppConfig(
                    assessment_paths=AssessmentPathsConfig.from_strings(
                        input_folder="Assessment/in",
                        output_folder="Assessment/out",
                        explained_folder="Assessment/explained",
                    ),
                    llm_config=LlmConfig.from_strings(
                        llama_server_model="initial",
                        llama_model_key="initial",
                        llama_model_display_name="Initial",
                        llama_model_alias="Initial",
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
                    ged_config=GedConfig.from_strings(
                        model_name="gotutiyan/token-ged-bert-large-cased-bin"
                    ),
                    run_config=RunConfig.from_strings(author="tester"),
                    sustainability_config=SustainabilityConfig.from_values(),
                )

                captured_specs: dict[str, list[str]] = {}

                def _capture_choice(specs, recommended, persisted_key, hw, label):
                    captured_specs["keys"] = [s.key for s in specs]
                    return specs[0]

                with patch(
                    "app.select_model.get_hardware_info",
                    return_value=HardwareInfo(
                        total_ram_gb=64.0,
                        cpu_count=8,
                        cuda_vram_gb=16.0,
                        is_mps=False,
                    ),
                ), patch("app.select_model.prompt_initial_action", return_value="download"), patch(
                    "app.select_model.prompt_model_choice_from_list",
                    side_effect=_capture_choice,
                ), patch(
                    "builtins.print"
                ):
                    select_model_and_update_config(app_cfg)

                self.assertEqual(
                    set(captured_specs["keys"]),
                    {"qwen3_4b_instruct_q8", "qwen3_4b_q8", "qwen3_8b_q8"},
                )
            finally:
                os.chdir(prev_cwd)


if __name__ == "__main__":
    unittest.main()
