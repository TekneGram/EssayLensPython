from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.settings import AppConfig
from app.settings import build_settings
from app.container import build_container


class AppConfigInterfaceTests(unittest.TestCase):
    def test_container_annotation_uses_app_config(self) -> None:
        self.assertEqual(build_container.__annotations__["app_cfg"], AppConfig)

    def test_container_smoke_call(self) -> None:
        cfg = build_settings()
        with patch("app.container.LlmServerProcess.start", return_value=None), patch(
            "app.container.GedBertDetector",
            return_value=MagicMock(),
        ), patch(
            "app.container.DocxOutputService",
            return_value=MagicMock(),
        ), patch(
            "app.container.DocxLoader",
            return_value=MagicMock(),
        ), patch(
            "app.container.PdfLoader",
            return_value=MagicMock(),
        ):
            container = build_container(cfg)
        self.assertIn("project_root", container)
        self.assertIn("server_bin", container)
        self.assertIn("document_input", container)
        self.assertNotIn("loader", container)
        self.assertNotIn("pdf_loader", container)


if __name__ == "__main__":
    unittest.main()
