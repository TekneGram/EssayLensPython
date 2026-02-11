from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from pathlib import Path
from app.runtime_lifecycle import RuntimeLifecycle
from utils.terminal_ui import type_print, Color