from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SustainabilityConfig:
    enabled: bool = True
    carbon_intensity_g_per_kwh: float = 475.0
    sample_interval_s: float = 0.25
    power_backend: str = "powermetrics"
    powermetrics_command: str = "powermetrics"

    @staticmethod
    def from_values(
        enabled: bool | str = True,
        carbon_intensity_g_per_kwh: float | int = 475.0,
        sample_interval_s: float | int = 0.25,
        power_backend: str = "powermetrics",
        powermetrics_command: str = "powermetrics",
    ) -> "SustainabilityConfig":
        def _to_bool(v: bool | str) -> bool:
            if isinstance(v, bool):
                return v
            if isinstance(v, str):
                s = v.strip().lower()
                if s in {"1", "true", "t", "yes", "y", "on"}:
                    return True
                if s in {"0", "false", "f", "no", "n", "off"}:
                    return False
            raise ValueError(f"Expected a boolean or boolean-string, got {v!r}")

        cfg = SustainabilityConfig(
            enabled=_to_bool(enabled),
            carbon_intensity_g_per_kwh=float(carbon_intensity_g_per_kwh),
            sample_interval_s=float(sample_interval_s),
            power_backend=power_backend.strip().lower(),
            powermetrics_command=powermetrics_command.strip(),
        )
        cfg.validate()
        return cfg

    def validate(self) -> None:
        if self.carbon_intensity_g_per_kwh <= 0:
            raise ValueError("SustainabilityConfig.carbon_intensity_g_per_kwh must be > 0.")

        if self.sample_interval_s <= 0:
            raise ValueError("SustainabilityConfig.sample_interval_s must be > 0.")

        if self.power_backend not in {"powermetrics", "none"}:
            raise ValueError("SustainabilityConfig.power_backend must be one of: powermetrics, none.")

        if self.power_backend == "powermetrics" and not self.powermetrics_command:
            raise ValueError(
                "SustainabilityConfig.powermetrics_command must be non-empty when using powermetrics backend."
            )
