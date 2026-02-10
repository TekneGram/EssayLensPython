from __future__ import annotations

from dataclasses import dataclass
import time

from config.sustainability_config import SustainabilityConfig
from services.power_sampler import PowerSampler, PowerSnapshot


@dataclass(frozen=True, slots=True)
class SustainabilityReport:
    run_label: str | None
    elapsed_s: float
    token_count: int | None
    throughput_tps: float | None
    sample_count: int
    avg_mw: float
    energy_j: float
    co2_g: float
    tree_minutes: float
    lightbulb_minutes: float
    diagnostics: tuple[str, ...] = ()


@dataclass
class Sustainability:
    cfg: SustainabilityConfig
    sampler: PowerSampler

    _started_at: float | None = None
    _stopped: bool = False
    _run_label: str | None = None
    _last_report: SustainabilityReport | None = None

    def start(self, run_label: str | None = None) -> None:
        if self._started_at is not None and not self._stopped:
            return
        self._run_label = run_label
        self._started_at = time.perf_counter()
        self._stopped = False
        self._last_report = None
        if self.cfg.enabled:
            self.sampler.start()

    def finish(self, *, token_count: int | None = None) -> SustainabilityReport:
        if self._stopped and self._last_report is not None:
            return self._last_report

        now = time.perf_counter()
        started_at = self._started_at if self._started_at is not None else now
        elapsed_s = max(0.0, now - started_at)

        snapshot = PowerSnapshot(sample_count=0, avg_mw=0.0, total_mw=0.0)
        if self.cfg.enabled:
            self.sampler.stop()
            snapshot = self.sampler.snapshot()

        energy_j = (snapshot.avg_mw / 1000.0) * elapsed_s
        kwh = energy_j / 3_600_000.0
        co2_g = kwh * self.cfg.carbon_intensity_g_per_kwh
        tree_minutes = co2_g / (21000.0 / 525600.0)
        lightbulb_minutes = (co2_g * 1000.0) / 71.25

        throughput_tps: float | None = None
        if token_count is not None and elapsed_s > 0:
            throughput_tps = token_count / elapsed_s

        report = SustainabilityReport(
            run_label=self._run_label,
            elapsed_s=elapsed_s,
            token_count=token_count,
            throughput_tps=throughput_tps,
            sample_count=snapshot.sample_count,
            avg_mw=snapshot.avg_mw,
            energy_j=energy_j,
            co2_g=co2_g,
            tree_minutes=tree_minutes,
            lightbulb_minutes=lightbulb_minutes,
            diagnostics=getattr(self.sampler, "diagnostics", ()),
        )

        self._stopped = True
        self._last_report = report
        return report

    def summary_text(self, report: SustainabilityReport) -> str:
        label = report.run_label or "run"
        throughput = (
            f", throughput={report.throughput_tps:.2f} tok/s"
            if report.throughput_tps is not None
            else ""
        )
        return (
            f"[sustainability] {label}: elapsed={report.elapsed_s:.2f}s"
            f", power={report.avg_mw:.1f}mW"
            f", energy={report.energy_j:.2f}J"
            f", co2={report.co2_g:.6f}g"
            f", samples={report.sample_count}{throughput}"
        )
