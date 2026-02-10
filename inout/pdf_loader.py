from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from pypdf import PdfReader


@dataclass(frozen=True, slots=True)
class PdfLoader:
    """
    Loads page text from a .pdf file
    """

    strip_whitespace: bool = True
    keep_empty_pages: bool = True

    def load_pages(self, pdf_path: str | Path) -> list[str]:
        """
        Read a .pdf and return a list of page strings in source order.

        Parameters
        ----------
        pdf_path:
            Path (or string path) to a .pdf file.

        Returns
        ----------
        list[str]
            Page texts, optionally stripped and optionally excluding empties
        """
        path = Path(pdf_path)
        self._validate_pdf_path(path)

        reader = PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
        return self._postprocess(pages)

    def iter_pages(self, pdf_path: str | Path) -> Iterable[str]:
        """
        Generator version of `load_pages`. Useful for streaming.
        """
        path = Path(pdf_path)
        self._validate_pdf_path(path)

        reader = PdfReader(str(path))
        for page in reader.pages:
            txt = page.extract_text() or ""
            if self.strip_whitespace:
                txt = txt.strip()
            if not self.keep_empty_pages and not txt:
                continue
            yield txt

    def _postprocess(self, pages: list[str]) -> list[str]:
        if self.strip_whitespace:
            pages = [p.strip() for p in pages]
        if not self.keep_empty_pages:
            pages = [p for p in pages if p]
        return pages

    @staticmethod
    def _validate_pdf_path(path: Path) -> None:
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {path}")
        if not path.is_file():
            raise ValueError(f"PDF path is not a file: {path}")
        if path.suffix.lower() != ".pdf":
            raise ValueError(f"Expected a .pdf file, but got: {path.name}")
