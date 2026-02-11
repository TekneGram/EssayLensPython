from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ExplainabilityWriter:
    output_dir: Path

    def write(self, docx_path: Path, lines: list[str]) -> Path:
        # Legacy method: this derives the txt filename from the docx stem and may be phased out.
        self.output_dir.mkdir(parents=True, exist_ok=True)
        out_path = self.output_dir / f"{docx_path.stem}.txt"
        out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return out_path

    def write_to_path(self, explained_path: Path, lines: list[str]) -> Path:
        explained_path.parent.mkdir(parents=True, exist_ok=True)
        explained_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return explained_path
