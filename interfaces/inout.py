from __future__ import annotations

from typing import Protocol
from pathlib import Path

class DocxLoader(Protocol):
    def load_paragraphs(self, docx_path: str | Path) -> list[str]:
        ...


class PdfLoader(Protocol):
    def load_pages(self, pdf_path: str | Path) -> list[str]:
        ...
