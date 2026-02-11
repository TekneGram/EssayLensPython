from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DiscoveredInputs:
    docx_paths: list[Path] = field(default_factory=list)
    pdf_paths: list[Path] = field(default_factory=list)
    image_paths: list[Path] = field(default_factory=list)
    unsupported_paths: list[Path] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class InputDiscoveryService:
    """
    Discover and classify candidate input documents under the configured
    assessment input root.

    This service is intentionally filesystem-only; it does not load or parse
    document contents.
    """

    input_root: Path
    docx_suffixes: frozenset[str] = frozenset({".docx"})
    pdf_suffixes: frozenset[str] = frozenset({".pdf"})
    image_suffixes: frozenset[str] = frozenset(
        {
            ".png",
            ".jpg",
            ".jpeg",
            ".heic",
            ".heif",
            ".tif",
            ".tiff",
            ".bmp",
            ".webp",
        }
    )

    def discover(self) -> DiscoveredInputs:
        root = self.input_root
        if not root.exists():
            raise FileNotFoundError(f"Input folder not found: {root}")
        if not root.is_dir():
            raise ValueError(f"Input path is not a directory: {root}")

        docx_paths: list[Path] = []
        pdf_paths: list[Path] = []
        image_paths: list[Path] = []
        unsupported_paths: list[Path] = []

        for submission_dir in sorted((p for p in root.iterdir() if p.is_dir()), key=lambda p: p.name):
            for file_path in sorted((p for p in submission_dir.rglob("*") if p.is_file()), key=lambda p: str(p)):
                suffix = file_path.suffix.lower()
                if suffix in self.docx_suffixes:
                    docx_paths.append(file_path)
                elif suffix in self.pdf_suffixes:
                    pdf_paths.append(file_path)
                elif suffix in self.image_suffixes:
                    image_paths.append(file_path)
                else:
                    unsupported_paths.append(file_path)

        return DiscoveredInputs(
            docx_paths=docx_paths,
            pdf_paths=pdf_paths,
            image_paths=image_paths,
            unsupported_paths=unsupported_paths,
        )
