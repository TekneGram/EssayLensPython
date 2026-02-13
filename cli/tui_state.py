from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TuiState:
    command_history: list[str] = field(default_factory=list)
    status: dict[str, Any] = field(default_factory=dict)
    last_error: str | None = None
    last_result: dict[str, Any] | None = None

