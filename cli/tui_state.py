from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TuiState:
    command_history: list[str] = field(default_factory=list)
    status: dict[str, Any] = field(default_factory=dict)
    last_error: str | None = None
    last_result: dict[str, Any] | None = None
    completion_active: bool = False
    completion_query: str = ""
    completion_items: list[str] = field(default_factory=list)
    completion_index: int = 0
    completion_start: int = 0
    completion_end: int = 0
    completion_source_text: str = ""
    completion_source_cursor: int = 0
