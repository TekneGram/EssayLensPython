from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ExplainabilityWriter:
    output_dir: Path

    def write(self, docx_path: Path, lines: list[str]) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        out_path = self.output_dir / f"{docx_path.stem}.txt"
        out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return out_path
