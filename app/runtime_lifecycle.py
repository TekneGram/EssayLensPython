from __future__ import annotations

import atexit
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class RuntimeLifecycle:
    """
    Process-lifecycle safety helper.

    Register long-lived process wrappers once so they are stopped on interpreter
    exit as a fallback. Normal stage code should still use try/finally stop().
    """

    _registered_ids: set[int] = field(default_factory=set)

    def register_process(self, proc: Any) -> None:
        if proc is None:
            return

        key = id(proc)
        if key in self._registered_ids:
            return

        def _shutdown() -> None:
            self._safe_stop(proc)

        atexit.register(_shutdown)
        self._registered_ids.add(key)

    @staticmethod
    def _safe_stop(proc: Any) -> None:
        stop: Callable[[], None] | None = getattr(proc, "stop", None)
        is_running: Callable[[], bool] | None = getattr(proc, "is_running", None)
        if not callable(stop):
            return
        try:
            if callable(is_running) and not is_running():
                return
            stop()
        except Exception:
            # Exit handlers must not crash shutdown flow.
            return
