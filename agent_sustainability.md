# Sustainability Monitoring Integration Plan

## Goal
Introduce a `Sustainability` service that can be started before pipeline execution and finished after execution, returning runtime + power/CO2 metrics for the run.

Target usage:
- `sustainability.start(...)` before heavy processing
- `sustainability.finish(...)` after processing ends to stop monitoring and emit summary metrics

## Design Pattern
Use a **service + strategy provider** pattern:
1. `Sustainability` service owns lifecycle (`start`, `finish`) and report composition.
2. `PowerSampler` strategy abstracts machine-specific power sampling.
3. `PowermetricsPowerSampler` implements macOS power polling.
4. `NullPowerSampler` provides timing-only fallback when power monitoring is disabled/unavailable.

This keeps runtime entrypoints clean and prevents OS-specific logic from leaking into app flow.

## Files To Create
- `config/sustainability_config.py`
- `services/sustainability_service.py`
- `services/power_sampler.py`
- `tests/test_sustainability_service.py`
- `tests/test_sustainability_config.py`

## Files To Update
- `app/settings.py`
- `interfaces/config/app_config.py`
- `app/container.py`

## Config Plan
### `config/sustainability_config.py`
Create immutable config class mirroring current config conventions:
- `@dataclass(frozen=True, slots=True)`
- static constructor: `from_values(...)`
- `validate(self) -> None`

Suggested fields:
- `enabled: bool = True`
- `carbon_intensity_g_per_kwh: float = 475.0`
- `sample_interval_s: float = 0.25`
- `power_backend: str = "powermetrics"`  # allowed: `powermetrics`, `none`
- `powermetrics_command: str = "powermetrics"`

Validation:
- `carbon_intensity_g_per_kwh > 0`
- `sample_interval_s > 0`
- `power_backend` in allowed set
- `powermetrics_command` non-empty when backend is `powermetrics`

## Sampling Strategy Plan
### `services/power_sampler.py`
Define common protocol/base for samplers:
- `start() -> None`
- `stop() -> None`
- `snapshot() -> PowerSnapshot`

Dataclasses:
- `PowerSample(mw: float, ts: float)`
- `PowerSnapshot(sample_count: int, avg_mw: float, total_mw: float)`

Implementations:
1. `PowermetricsPowerSampler`
- Runs a background worker/thread.
- Polls `powermetrics` command at configured interval.
- Parses `Combined Power (CPU + GPU + ANE): X mW`.
- Aggregates totals/samples.
- Handles command errors without crashing the app.

2. `NullPowerSampler`
- No-op start/stop.
- Returns zeroed snapshot.
- Supports timing-only sustainability reporting.

## Service Plan
### `services/sustainability_service.py`
Implement:
- `@dataclass class Sustainability`
  - fields: `cfg: SustainabilityConfig`, `sampler: PowerSampler`
  - internal state: `_started_at`, `_stopped`, `_run_label`

Methods:
- `start(run_label: str | None = None) -> None`
  - idempotent-safe start guard.
  - stores start time.
  - starts sampler when enabled.

- `finish(*, token_count: int | None = None) -> SustainabilityReport`
  - idempotent finish guard.
  - stops sampler.
  - computes elapsed time.
  - computes energy:
    - `joules = (avg_mw / 1000.0) * elapsed_s`
  - computes emissions:
    - `kwh = joules / 3_600_000`
    - `co2_g = kwh * carbon_intensity_g_per_kwh`
  - computes equivalents using `llama_test.py` logic:
    - `tree_minutes = co2_g / (21000 / 525600)`
    - `lightbulb_minutes = (co2_g * 1000) / 71.25`
  - computes throughput using `llama_test.py` benchmark style:
    - `throughput_tps = token_count / elapsed_s` when token_count is provided and elapsed > 0
  - returns immutable `SustainabilityReport`.

- `summary_text(report: SustainabilityReport) -> str`
  - concise one-line printable summary for terminal output.

Dataclass:
- `SustainabilityReport`
  - `run_label: str | None`
  - `elapsed_s: float`
  - `token_count: int | None`
  - `throughput_tps: float | None`
  - `sample_count: int`
  - `avg_mw: float`
  - `energy_j: float`
  - `co2_g: float`
  - `tree_minutes: float`
  - `lightbulb_minutes: float`

## App Wiring Plan
### `app/settings.py`
- Import and build `SustainabilityConfig`.
- Validate it.
- Add `sustainability_config` field to `AppConfig`.
- Return it from `build_settings()`.

### `interfaces/config/app_config.py`
- Add `sustainability_config` to `AppConfigShape` to keep interface aligned.

### `app/container.py`
- Instantiate sampler strategy based on `app_cfg.sustainability_config.power_backend`.
- Build `Sustainability` service and include it in returned deps dict:
  - key: `"sustainability"`

### `main.py`
- Do *not* touch main.py

## Error and Safety Behavior
- Sampling errors should be captured as diagnostics and surfaced in report metadata.
- If `powermetrics` is unavailable, fallback to `NullPowerSampler` and emit timing-only metrics.
- If `token_count` is not provided, set `throughput_tps` to `None` while still returning all energy/emissions/equivalents metrics.

## Non-Drift Rules

1. Keep power parsing isolated to sampler implementation.
2. Keep config validation strict and explicit.
3. Do not modify existing LLM/GED service logic while adding sustainability.
4. Maintain immutable config update/style conventions used in `config/`.
5. Do not modify `main.py` in this sustainability change.

## Acceptance Checklist
- [ ] `Sustainability` service exists with `start()` and `finish()` lifecycle methods.
- [ ] `SustainabilityReport` returns elapsed, power, energy, CO2, tree minutes, and lightbulb minutes metrics.
- [ ] `SustainabilityReport` includes token_count and throughput_tps fields.
- [ ] Power sampling is strategy-based (`powermetrics` and `none` backends).
- [ ] `AppConfig` and `AppConfigShape` include `sustainability_config`.
- [ ] Container exposes `deps["sustainability"]`.
- [ ] `main.py` remains untouched.
- [ ] Fallback mode works when power monitoring is unavailable.
- [ ] Existing pipeline behavior remains unchanged aside from added monitoring output.
