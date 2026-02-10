from __future__ import annotations

import unittest

from config.sustainability_config import SustainabilityConfig


class SustainabilityConfigTests(unittest.TestCase):
    def test_from_values_defaults(self) -> None:
        cfg = SustainabilityConfig.from_values()
        self.assertTrue(cfg.enabled)
        self.assertEqual(cfg.carbon_intensity_g_per_kwh, 475.0)
        self.assertEqual(cfg.sample_interval_s, 0.25)
        self.assertEqual(cfg.power_backend, "powermetrics")
        self.assertEqual(cfg.powermetrics_command, "powermetrics")

    def test_from_values_parses_boolean_strings(self) -> None:
        cfg = SustainabilityConfig.from_values(enabled="false", power_backend="none")
        self.assertFalse(cfg.enabled)
        self.assertEqual(cfg.power_backend, "none")

    def test_validate_rejects_non_positive_carbon_intensity(self) -> None:
        with self.assertRaises(ValueError):
            SustainabilityConfig.from_values(carbon_intensity_g_per_kwh=0)

    def test_validate_rejects_non_positive_sample_interval(self) -> None:
        with self.assertRaises(ValueError):
            SustainabilityConfig.from_values(sample_interval_s=0)

    def test_validate_rejects_unknown_backend(self) -> None:
        with self.assertRaises(ValueError):
            SustainabilityConfig.from_values(power_backend="watts")

    def test_validate_rejects_empty_powermetrics_command_when_backend_enabled(self) -> None:
        with self.assertRaises(ValueError):
            SustainabilityConfig.from_values(power_backend="powermetrics", powermetrics_command=" ")


if __name__ == "__main__":
    unittest.main()
