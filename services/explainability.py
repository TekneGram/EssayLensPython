from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.run_config import RunConfig
from config.ged_config import GedConfig
from config.llm_config import LlmConfig
from config.ocr_config import OcrConfig


@dataclass
class ExplainabilityRecorder:
    run_id: str
    run_cfg: RunConfig
    ged_cfg: GedConfig
    llm_config: LlmConfig
    ocr_config: OcrConfig
    _lines: list[str] = field(default_factory=list)

    @staticmethod
    def new(
        run_cfg: RunConfig,
        ged_cfg: GedConfig,
        llm_config: LlmConfig,
        ocr_config: OcrConfig,
    ) -> "ExplainabilityRecorder":
        run_id = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return ExplainabilityRecorder(
            run_id=run_id,
            run_cfg=run_cfg,
            ged_cfg=ged_cfg,
            llm_config=llm_config,
            ocr_config=ocr_config,
        )

    def reset(self) -> None:
        self._lines.clear()

    def start_doc(self, docx_path: Path, *, include_edited_text: bool) -> None:
        self._lines.append(f"Explainability Report: {docx_path.name}")
        self._lines.append(f"Generated (UTC): {self.run_id}")
        self._lines.append("")
        self._lines.append("=== RUN CONFIG ===")
        self._lines.append(f"AUTHOR: {self.run_cfg.author}")
        self._lines.append(f"OCR MODEL: {self.ocr_config.ocr_model_display_name}")
        self._lines.append(f"GED_MODEL: {self.ged_cfg.model_name}")
        self._lines.append(f"GED_BATCH_SIZE: {self.ged_cfg.batch_size}")
        self._lines.append(f"LLM MODEL: {self.llm_config.llama_model_display_name}")
        self._lines.append(f"MAX_LLM_CORRECTIONS: {self.run_cfg.max_llm_corrections}")

    def log(self, section: str, message: str) -> None:
        self._lines.append(f"[{section}] {message}")

    def log_kv(self, section: str, data: dict[str, Any]) -> None:
        for key, value in data.items():
            self._lines.append(f"[{section}] {key}: {value}")

    def finish_doc(self) -> list[str]:
        return list(self._lines)
