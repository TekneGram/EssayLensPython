from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.container import build_container
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
    server_bin = root / "llama-server"
    model_file = root / "model.gguf"
    server_bin.write_text("bin", encoding="utf-8")
    model_file.write_text("gguf", encoding="utf-8")

    return AppConfig(
        assessment_paths=AssessmentPathsConfig.from_strings(
            input_folder=root / "Assessment" / "in",
            output_folder=root / "Assessment" / "out",
            explained_folder=root / "Assessment" / "explained",
        ),
        llm_config=LlmConfig.from_strings(
            llama_gguf_path=model_file,
            llama_server_model="demo",
            llama_model_key="demo",
            llama_model_display_name="Demo",
            llama_model_alias="demo",
            llama_model_family="instruct",
        ),
        ocr_config=OcrConfig.from_strings(
            ocr_server_model="server",
            ocr_model_key="ocr",
            ocr_model_display_name="OCR",
            ocr_model_alias="ocr",
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


class ContainerRuntimeTests(unittest.TestCase):
    def test_build_container_starts_server_and_registers_shutdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = _build_app_cfg(Path(tmpdir))
            fake_server_proc = MagicMock()

            with patch("app.container.DocxLoader"), patch("app.container.PdfLoader"), patch(
                "app.container.DocxOutputService"
            ), patch(
                "app.container.GedBertDetector"
            ), patch("app.container.GedService"), patch(
                "app.container.LlmServerProcess", return_value=fake_server_proc
            ) as server_cls, patch(
                "app.container.OpenAICompatChatClient"
            ) as client_cls, patch(
                "app.container.LlmService"
            ) as service_cls, patch(
                "app.container.ExplainabilityRecorder.new"
            ) as explain_new, patch(
                "app.container.ExplainabilityWriter"
            ), patch(
                "app.container.atexit.register"
            ) as register_mock:
                container = build_container(cfg)

            server_cls.assert_called_once()
            fake_server_proc.start.assert_called_once()
            register_mock.assert_called_once_with(fake_server_proc.stop)
            client_cls.assert_called_once()
            service_cls.assert_called_once()
            explain_new.assert_called_once()
            self.assertIn("llm_service", container)
            self.assertIsNotNone(container["llm_service"])
            self.assertIn("sustainability", container)
            self.assertIn("document_input", container)
            self.assertNotIn("loader", container)
            self.assertNotIn("pdf_loader", container)

    def test_build_container_skips_llm_wiring_when_backend_not_server(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = _build_app_cfg(Path(tmpdir))
            cfg = replace(cfg, llm_server=replace(cfg.llm_server, llama_backend="local"))

            with patch("app.container.DocxLoader"), patch("app.container.PdfLoader"), patch(
                "app.container.DocxOutputService"
            ), patch(
                "app.container.GedBertDetector"
            ), patch("app.container.GedService"), patch(
                "app.container.LlmServerProcess"
            ) as server_cls, patch(
                "app.container.OpenAICompatChatClient"
            ) as client_cls, patch(
                "app.container.LlmService"
            ) as service_cls, patch(
                "app.container.ExplainabilityRecorder.new"
            ), patch(
                "app.container.ExplainabilityWriter"
            ):
                container = build_container(cfg)

            server_cls.assert_not_called()
            client_cls.assert_not_called()
            service_cls.assert_not_called()
            self.assertIsNone(container["server_proc"])
            self.assertIsNone(container["llm_service"])
            self.assertIn("sustainability", container)
            self.assertIn("document_input", container)
            self.assertNotIn("loader", container)
            self.assertNotIn("pdf_loader", container)


if __name__ == "__main__":
    unittest.main()
