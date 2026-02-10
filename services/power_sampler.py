from __future__ import annotations

from dataclasses import dataclass
import re
import subprocess
import threading
import time
from typing import Protocol


@dataclass(frozen=True, slots=True)
class PowerSample:
    mw: float
    ts: float


@dataclass(frozen=True, slots=True)
class PowerSnapshot:
    sample_count: int
    avg_mw: float
    total_mw: float


class PowerSampler(Protocol):
    def start(self) -> None:
        ...

    def stop(self) -> None:
        ...

    def snapshot(self) -> PowerSnapshot:
        ...


class NullPowerSampler:
    def __init__(self) -> None:
        self._diagnostics: list[str] = []

    def start(self) -> None:
        return None

    def stop(self) -> None:
        return None

    def snapshot(self) -> PowerSnapshot:
        return PowerSnapshot(sample_count=0, avg_mw=0.0, total_mw=0.0)

    def add_diagnostic(self, message: str) -> None:
        if len(self._diagnostics) >= 10:
            return
        self._diagnostics.append(message)

    @property
    def diagnostics(self) -> tuple[str, ...]:
        return tuple(self._diagnostics)


class PowermetricsPowerSampler:
    _COMBINED_POWER_RE = re.compile(
        r"Combined Power \(CPU \+ GPU \+ ANE\):\s*([0-9]+(?:\.[0-9]+)?)\s*mW"
    )

    def __init__(self, command: str = "powermetrics", sample_interval_s: float = 0.25) -> None:
        self._command = command
        self._sample_interval_s = sample_interval_s
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._sample_count = 0
        self._total_mw = 0.0
        self._diagnostics: list[str] = []

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="powermetrics-sampler", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._thread is None:
            return
        self._stop_event.set()
        self._thread.join(timeout=max(1.0, self._sample_interval_s * 4.0))

    def snapshot(self) -> PowerSnapshot:
        with self._lock:
            avg_mw = (self._total_mw / self._sample_count) if self._sample_count else 0.0
            return PowerSnapshot(
                sample_count=self._sample_count,
                avg_mw=avg_mw,
                total_mw=self._total_mw,
            )

    @property
    def diagnostics(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(self._diagnostics)

    def _run(self) -> None:
        interval_ms = max(1, int(self._sample_interval_s * 1000))
        while not self._stop_event.is_set():
            sample = self._collect_sample(interval_ms=interval_ms)
            if sample is not None:
                with self._lock:
                    self._sample_count += 1
                    self._total_mw += sample.mw
            self._stop_event.wait(self._sample_interval_s)

    def _collect_sample(self, *, interval_ms: int) -> PowerSample | None:
        try:
            proc = subprocess.run(
                [self._command, "-i", str(interval_ms), "-n", "1", "--samplers", "cpu_power"],
                capture_output=True,
                text=True,
                check=False,
            )
        except Exception as exc:
            self._record_diagnostic(f"powermetrics execution failed: {exc}")
            return None

        if proc.returncode != 0:
            error_text = (proc.stderr or proc.stdout or "").strip()
            self._record_diagnostic(f"powermetrics returned {proc.returncode}: {error_text}")
            return None

        match = self._COMBINED_POWER_RE.search(proc.stdout)
        if not match:
            self._record_diagnostic("powermetrics output did not include combined power sample")
            return None

        return PowerSample(mw=float(match.group(1)), ts=time.perf_counter())

    def _record_diagnostic(self, message: str) -> None:
        with self._lock:
            if len(self._diagnostics) >= 10:
                return
            self._diagnostics.append(message)
