from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import Mock

from services.document_input_service import DocumentInputService


class DocumentInputServiceRuntimeTests(unittest.TestCase):
    def test_load_routes_docx_to_docx_loader(self) -> None:
        docx_loader = Mock()
        docx_loader.load_paragraphs.return_value = ["one", "two"]
        pdf_loader = Mock()
        service = DocumentInputService(
            docx_loader=docx_loader,
            pdf_loader=pdf_loader,
        )

        result = service.load(Path("/tmp/sample.docx"))

        docx_loader.load_paragraphs.assert_called_once_with(Path("/tmp/sample.docx"))
        pdf_loader.load_pages.assert_not_called()
        self.assertEqual(result.source_kind, "docx")
        self.assertEqual(result.blocks, ["one", "two"])

    def test_load_routes_pdf_to_pdf_loader(self) -> None:
        docx_loader = Mock()
        pdf_loader = Mock()
        pdf_loader.load_pages.return_value = ["page one", "page two"]
        service = DocumentInputService(
            docx_loader=docx_loader,
            pdf_loader=pdf_loader,
        )

        result = service.load(Path("/tmp/sample.pdf"))

        pdf_loader.load_pages.assert_called_once_with(Path("/tmp/sample.pdf"))
        docx_loader.load_paragraphs.assert_not_called()
        self.assertEqual(result.source_kind, "pdf")
        self.assertEqual(result.blocks, ["page one", "page two"])

    def test_load_raises_for_unsupported_extension(self) -> None:
        service = DocumentInputService(docx_loader=Mock(), pdf_loader=Mock())

        with self.assertRaises(ValueError):
            service.load(Path("/tmp/sample.txt"))


if __name__ == "__main__":
    unittest.main()
