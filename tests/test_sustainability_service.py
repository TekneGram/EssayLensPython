from __future__ import annotations

import unittest
from unittest.mock import patch

from config.sustainability_config import SustainabilityConfig
from services.power_sampler import PowerSnapshot
from services.sustainability_service import Sustainability


class _FakeSampler:
    def __init__(self, snapshot: PowerSnapshot, diagnostics: tuple[str, ...] = ()) -> None:
        self._snapshot = snapshot
        self.diagnostics = diagnostics
        self.start_calls = 0
        self.stop_calls = 0

    def start(self) -> None:
        self.start_calls += 1

    def stop(self) -> None:
        self.stop_calls += 1

    def snapshot(self) -> PowerSnapshot:
        return self._snapshot


class SustainabilityServiceTests(unittest.TestCase):
    def test_start_and_finish_produces_metrics(self) -> None:
        cfg = SustainabilityConfig.from_values(
            enabled=True,
            carbon_intensity_g_per_kwh=475.0,
            sample_interval_s=0.25,
            power_backend="none",
        )
        sampler = _FakeSampler(
            snapshot=PowerSnapshot(sample_count=2, avg_mw=2500.0, total_mw=5000.0),
            diagnostics=("ok",),
        )
        svc = Sustainability(cfg=cfg, sampler=sampler)

        with patch("services.sustainability_service.time.perf_counter", side_effect=[10.0, 14.0]):
            svc.start(run_label="pipeline")
            report = svc.finish(token_count=20)

        self.assertEqual(sampler.start_calls, 1)
        self.assertEqual(sampler.stop_calls, 1)
        self.assertEqual(report.run_label, "pipeline")
        self.assertEqual(report.elapsed_s, 4.0)
        self.assertEqual(report.sample_count, 2)
        self.assertEqual(report.avg_mw, 2500.0)
        self.assertEqual(report.energy_j, 10.0)
        self.assertEqual(report.throughput_tps, 5.0)
        self.assertAlmostEqual(report.co2_g, (10.0 / 3_600_000.0) * 475.0)
        self.assertEqual(report.diagnostics, ("ok",))

    def test_finish_is_idempotent(self) -> None:
        cfg = SustainabilityConfig.from_values(enabled=True, power_backend="none")
        sampler = _FakeSampler(snapshot=PowerSnapshot(sample_count=1, avg_mw=1000.0, total_mw=1000.0))
        svc = Sustainability(cfg=cfg, sampler=sampler)

        with patch("services.sustainability_service.time.perf_counter", side_effect=[1.0, 2.0]):
            svc.start()
            first = svc.finish(token_count=10)
        second = svc.finish(token_count=999)

        self.assertIs(first, second)
        self.assertEqual(sampler.stop_calls, 1)
        self.assertEqual(first.token_count, 10)

    def test_disabled_config_skips_sampler_lifecycle(self) -> None:
        cfg = SustainabilityConfig.from_values(enabled=False, power_backend="none")
        sampler = _FakeSampler(snapshot=PowerSnapshot(sample_count=9, avg_mw=999.0, total_mw=999.0))
        svc = Sustainability(cfg=cfg, sampler=sampler)

        with patch("services.sustainability_service.time.perf_counter", side_effect=[3.0, 5.0]):
            svc.start()
            report = svc.finish()

        self.assertEqual(sampler.start_calls, 0)
        self.assertEqual(sampler.stop_calls, 0)
        self.assertEqual(report.sample_count, 0)
        self.assertEqual(report.avg_mw, 0.0)
        self.assertIsNone(report.throughput_tps)

    def test_summary_text_contains_expected_fields(self) -> None:
        cfg = SustainabilityConfig.from_values(enabled=True, power_backend="none")
        sampler = _FakeSampler(snapshot=PowerSnapshot(sample_count=0, avg_mw=0.0, total_mw=0.0))
        svc = Sustainability(cfg=cfg, sampler=sampler)

        with patch("services.sustainability_service.time.perf_counter", side_effect=[2.0, 3.0]):
            svc.start(run_label="job")
            report = svc.finish(token_count=7)

        summary = svc.summary_text(report)
        self.assertIn("[sustainability] job:", summary)
        self.assertIn("elapsed=1.00s", summary)
        self.assertIn("throughput=7.00 tok/s", summary)


if __name__ == "__main__":
    unittest.main()
