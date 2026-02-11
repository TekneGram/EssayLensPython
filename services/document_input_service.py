from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from interfaces.inout import DocxLoader, PdfLoader

if TYPE_CHECKING:
    from services.ocr_service import OcrService


@dataclass(frozen=True, slots=True)
class LoadedDocument:
    source_path: Path
    source_kind: Literal["docx", "pdf", "image"]
    blocks: list[str]


@dataclass
class DocumentInputService:
    """
    App-facing input orchestrator.

    Keeps format-specific extraction in inout/* loaders and provides one
    stable entrypoint for the pipeline.
    """

    docx_loader: DocxLoader
    pdf_loader: PdfLoader
    ocr_service: "OcrService | None" = None

    def load(self, path: str | Path) -> LoadedDocument:
        source = Path(path)
        suffix = source.suffix.lower()

        if suffix == ".docx":
            return LoadedDocument(
                source_path=source,
                source_kind="docx",
                blocks=self.docx_loader.load_paragraphs(source),
            )

        if suffix == ".pdf":
            return LoadedDocument(
                source_path=source,
                source_kind="pdf",
                blocks=self.pdf_loader.load_pages(source),
            )

        raise ValueError(f"Unsupported input type: {source.name}")
