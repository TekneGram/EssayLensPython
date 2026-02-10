from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from inout.pdf_loader import PdfLoader


class PdfLoaderRuntimeTests(unittest.TestCase):
    def _make_pdf_placeholder(self, root: Path, name: str = "sample.pdf") -> Path:
        path = root / name
        path.write_bytes(b"%PDF-1.4\n%placeholder\n")
        return path

    def _mock_reader_with_pages(self, texts: list[str | None]) -> Mock:
        pages = []
        for text in texts:
            page = Mock()
            page.extract_text.return_value = text
            pages.append(page)

        reader = Mock()
        reader.pages = pages
        return reader

    def test_validate_pdf_path_raises_for_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            missing = Path(tmpdir) / "missing.pdf"
            with self.assertRaises(FileNotFoundError):
                PdfLoader._validate_pdf_path(missing)

    def test_validate_pdf_path_raises_for_non_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            with self.assertRaises(ValueError):
                PdfLoader._validate_pdf_path(root)

    def test_validate_pdf_path_raises_for_non_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            txt = Path(tmpdir) / "note.txt"
            txt.write_text("x", encoding="utf-8")
            with self.assertRaises(ValueError):
                PdfLoader._validate_pdf_path(txt)

    @patch("inout.pdf_loader.PdfReader")
    def test_load_pages_with_strip_and_keep_empty(self, mock_reader_cls: Mock) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            path = self._make_pdf_placeholder(root)

            mock_reader_cls.return_value = self._mock_reader_with_pages(
                ["  one  ", None, " two "]
            )

            loader = PdfLoader(strip_whitespace=True, keep_empty_pages=True)
            self.assertEqual(loader.load_pages(path), ["one", "", "two"])

    @patch("inout.pdf_loader.PdfReader")
    def test_load_pages_without_strip_and_drop_empty(self, mock_reader_cls: Mock) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            path = self._make_pdf_placeholder(root)

            mock_reader_cls.return_value = self._mock_reader_with_pages(
                ["  one  ", None, " two "]
            )

            loader = PdfLoader(strip_whitespace=False, keep_empty_pages=False)
            self.assertEqual(loader.load_pages(path), ["  one  ", " two "])

    @patch("inout.pdf_loader.PdfReader")
    def test_iter_pages_matches_load_pages(self, mock_reader_cls: Mock) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            path = self._make_pdf_placeholder(root)

            mock_reader_cls.return_value = self._mock_reader_with_pages(
                ["  one  ", None, " two "]
            )

            loader = PdfLoader(strip_whitespace=True, keep_empty_pages=False)
            loaded = loader.load_pages(path)
            itered = list(loader.iter_pages(path))
            self.assertEqual(itered, loaded)


if __name__ == "__main__":
    unittest.main()
