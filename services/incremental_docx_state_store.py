from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class StateStoreError(RuntimeError):
    pass


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def text_hash(text: str) -> str:
    return hashlib.sha256((text or "").strip().encode("utf-8")).hexdigest()


def _new_state() -> dict[str, Any]:
    now = _utc_now_iso()
    return {
        "version": 1,
        "sections_written": [],
        "feedback_append_count": 0,
        "feedback_entries": [],
        "feedback_summary_present": False,
        "feedback_summary_hash": None,
        "feedback_summary_source_count": 0,
        "feedback_summary_updated_at": None,
        "edited_text_hash": None,
        "created_at": now,
        "updated_at": now,
    }


@dataclass
class IncrementalDocxStateStore:
    output_path: Path

    def __post_init__(self) -> None:
        self.output_path = Path(self.output_path)

    @property
    def sidecar_path(self) -> Path:
        return self.output_path.with_suffix(f"{self.output_path.suffix}.state.json")

    def load(self) -> dict[str, Any]:
        if not self.sidecar_path.exists():
            return _new_state()

        try:
            payload = json.loads(self.sidecar_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise StateStoreError(
                f"Failed to read state sidecar {self.sidecar_path}: {exc}"
            ) from exc

        self._validate(payload)
        return payload

    def save(self, state: dict[str, Any]) -> None:
        self._validate(state)
        state["updated_at"] = _utc_now_iso()
        self.sidecar_path.parent.mkdir(parents=True, exist_ok=True)
        self.sidecar_path.write_text(
            json.dumps(state, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def ensure_section(self, state: dict[str, Any], section: str) -> None:
        sections = state.setdefault("sections_written", [])
        if section not in sections:
            sections.append(section)

    def record_edited_hash(self, state: dict[str, Any], edited_text: str) -> None:
        state["edited_text_hash"] = text_hash(edited_text)

    def validate_edited_hash(self, state: dict[str, Any], edited_text: str) -> None:
        expected = state.get("edited_text_hash")
        actual = text_hash(edited_text)
        if not expected:
            raise StateStoreError("Missing edited_text_hash in state; append header+edited first.")
        if expected != actual:
            raise StateStoreError("Edited text baseline hash mismatch for corrected diff append.")

    def add_feedback_entry(
        self,
        state: dict[str, Any],
        *,
        feedback_id: str,
        marker_start: str,
        marker_end: str,
        target_path: str,
    ) -> None:
        entries = state.setdefault("feedback_entries", [])
        entries.append(
            {
                "id": feedback_id,
                "marker_start": marker_start,
                "marker_end": marker_end,
                "target_path": target_path,
                "timestamp": _utc_now_iso(),
            }
        )
        state["feedback_append_count"] = int(state.get("feedback_append_count", 0)) + 1

    def record_feedback_summary(
        self,
        state: dict[str, Any],
        *,
        summary_text: str,
        source_count: int,
    ) -> None:
        state["feedback_summary_present"] = True
        state["feedback_summary_hash"] = text_hash(summary_text)
        state["feedback_summary_source_count"] = source_count
        state["feedback_summary_updated_at"] = _utc_now_iso()

    def _validate(self, state: dict[str, Any]) -> None:
        required = {
            "version": int,
            "sections_written": list,
            "feedback_append_count": int,
            "feedback_entries": list,
            "feedback_summary_present": bool,
            "feedback_summary_source_count": int,
            "created_at": str,
            "updated_at": str,
        }
        for key, expected_type in required.items():
            if key not in state:
                raise StateStoreError(f"Invalid state sidecar: missing '{key}'.")
            if not isinstance(state[key], expected_type):
                raise StateStoreError(
                    f"Invalid state sidecar: field '{key}' must be {expected_type.__name__}."
                )
