from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from docx import Document

from inout.docx_loader import DocxLoader


class DocxLoaderRuntimeTests(unittest.TestCase):
    def _make_docx(self, root: Path, name: str, paragraphs: list[str]) -> Path:
        path = root / name
        doc = Document()
        for text in paragraphs:
            doc.add_paragraph(text)
        doc.save(path)
        return path

    def test_validate_docx_path_raises_for_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            missing = Path(tmpdir) / "missing.docx"
            with self.assertRaises(FileNotFoundError):
                DocxLoader._validate_docx_path(missing)

    def test_validate_docx_path_raises_for_non_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            with self.assertRaises(ValueError):
                DocxLoader._validate_docx_path(root)

    def test_validate_docx_path_raises_for_non_docx(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            txt = Path(tmpdir) / "note.txt"
            txt.write_text("x", encoding="utf-8")
            with self.assertRaises(ValueError):
                DocxLoader._validate_docx_path(txt)

    def test_load_paragraphs_with_strip_and_keep_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            path = self._make_docx(root, "sample.docx", ["  one  ", "", " two "])

            loader = DocxLoader(strip_whitespace=True, keep_empty_paragraphs=True)
            self.assertEqual(loader.load_paragraphs(path), ["one", "", "two"])

    def test_load_paragraphs_without_strip_and_drop_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            path = self._make_docx(root, "sample.docx", ["  one  ", "", " two "])

            loader = DocxLoader(strip_whitespace=False, keep_empty_paragraphs=False)
            self.assertEqual(loader.load_paragraphs(path), ["  one  ", " two "])

    def test_iter_paragraphs_matches_load_paragraphs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            path = self._make_docx(root, "sample.docx", ["  one  ", "", " two "])

            loader = DocxLoader(strip_whitespace=True, keep_empty_paragraphs=False)
            loaded = loader.load_paragraphs(path)
            itered = list(loader.iter_paragraphs(path))
            self.assertEqual(itered, loaded)


if __name__ == "__main__":
    unittest.main()
