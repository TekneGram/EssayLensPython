# Electron Backend Enablement Plan

## Summary
Prepare this Python project to run reliably as a local backend sidecar
for an Electron desktop app. The plan converts the current interactive
CLI-first runtime into a programmatic service interface, defines
packaging/distribution for Python plus model/runtime dependencies, and
establishes an end-to-end build pipeline for macOS, Windows, and Linux.

The result will be:
1. Electron UI process (Node) launches and supervises a local Python
   backend process.
2. Electron communicates with backend via local HTTP API (primary) or
   stdio protocol (fallback option).
3. Backend exposes task-oriented endpoints (starting with
   topic-sentence analysis and full-run pipeline trigger).
4. Build system emits installable desktop binaries with all required
   runtime artifacts and first-run bootstrap behavior.

## Goals And Success Criteria
- App can be launched by end users without pre-installing Python.
- Backend runs non-interactively (no `input()` prompts, no terminal-only
  control flow).
- Electron can invoke backend actions and receive progress, results, and
  errors through stable interfaces.
- Runtime lifecycle is deterministic: start, health check, graceful
  shutdown, crash recovery.
- Packaging works across target OSes with clear model/binary placement
  strategy.
- First-run flow handles model download/bootstrap and surfaces progress.

## Current-State Constraints (From Existing Codebase)
- `main.py` orchestrates full flow and is terminal-output driven.
- `app/select_model.py` currently contains interactive `input()` model
  selection.
- `build_settings()` defaults to repo-relative folders
  (`Assessment/in`, `Assessment/checked`, `Assessment/explained`).
- `bootstrap_llm()` and OCR setup may download runtime artifacts.
- `LlmServerProcess` and `OcrServerProcess` spawn subprocesses and expose
  readiness via local HTTP health checks.
- Existing services are reusable and already separated well enough for
  API wrapping (`LlmTaskService`, `DocumentInputService`, pipelines).

## Scope
- In scope:
1. Non-interactive backend entrypoint for Electron
2. API contract for backend commands, status, and errors
3. Configuration and path refactor for app-data locations
4. Startup/bootstrap and model-selection strategy for packaged app
5. Packaging/build plan for Python backend plus Electron shell
6. Test and validation strategy for packaged runtime

- Out of scope (first iteration):
1. Cloud-hosted backend mode
2. Multi-user/shared remote service
3. Rewriting NLP task logic itself
4. UI design for Electron frontend screens

## Cross-Plan Compatibility Requirements (Electron + CLI)
1. Electron backend must be a thin interface adapter over shared
   non-interactive application services used by CLI.
2. Electron backend entrypoint remains `app.backend_server`; CLI
   remains `app.cli`; both must avoid direct coupling to each other's
   transport concerns.
3. Any extraction from `main.py` must be placed in shared reusable core
   modules consumed by both plans.
4. Electron default writable paths must remain namespaced under
   app-data roots and not overwrite CLI-specific output locations.
5. Shared config/path resolver must support both packaged Electron mode
   and developer-local CLI mode.
6. Shared subprocess lifecycle controls for `llama-server` and OCR must
   be interface-agnostic and consistent for both entrypoints.
7. Shared result/error schemas should align with CLI reporting format to
   keep behavior consistent across interfaces.

## Public Interfaces To Add/Change
- New Python backend entrypoint:
1. `python -m app.backend_server` (development)
2. packaged executable launched by Electron main process

- HTTP API (v1) endpoints:
1. `GET /health`
2. `GET /runtime/status`
3. `POST /runtime/bootstrap`
4. `POST /analyze/topic-sentence`
5. `POST /pipeline/run`
6. `GET /jobs/{job_id}`
7. `POST /jobs/{job_id}/cancel`

- Event/progress model:
1. polling via `/jobs/{job_id}` in V1 (required)
2. optional SSE/WebSocket in V2 (deferred)

- Request/response schema conventions:
1. JSON request bodies only
2. structured error envelope:
   - `code`
   - `message`
   - `details`

## Architecture Changes Needed

### 1) Backend Service Layer (Non-Interactive)
1. Extract orchestration currently in `main.py` into reusable service
   functions/classes that accept parameters and return structured results.
2. Remove dependency on terminal prompts and animated output in backend
   execution path.
3. Replace `input()` model-selection path with non-interactive policy:
   - use persisted model key if valid
   - fallback to recommended model
   - return explicit error if required artifacts are missing and download
     is disabled

### 2) Job Execution Model
1. Introduce job manager abstraction for long-running tasks.
2. Each request that may take time runs as a background job with:
   - `job_id`
   - `state` (`queued`, `running`, `succeeded`, `failed`, `canceled`)
   - progress fields (`stage`, `completed`, `total`, `message`)
   - `result` or `error`
3. Ensure cancellation hooks stop child processes safely where possible.

### 3) Process Lifecycle And Resource Control
1. Keep `RuntimeLifecycle` semantics, but expose process status through
   API.
2. Ensure backend shuts down `llama-server`/OCR subprocesses on SIGTERM
   from Electron.
3. Add startup lock/guard to prevent duplicate backend instances.
4. Add configurable timeouts for startup, inference, and shutdown.

### 4) Configuration/Paths For Packaged App
1. Stop assuming repo-relative writable folders in packaged mode.
2. Use OS app-data directories for writable state:
   - configs
   - downloaded models
   - outputs
   - logs
3. Distinguish read-only bundled assets vs writable runtime data.
4. Provide config override sources:
   - env vars
   - CLI flags
   - runtime API options

### 5) Logging And Observability
1. Add structured logs (JSON lines preferred) for backend process.
2. Provide log file path via `/runtime/status`.
3. Redact sensitive tokens/paths where appropriate.

## Build And Packaging Plan

### A) Packaging Strategy
1. Package Python backend as standalone binary per OS using PyInstaller
   (recommended baseline).
2. Bundle required Python dependencies into backend artifact.
3. Bundle or provision `llama-server` binaries per platform/arch.
4. Keep large model files out of installer initially; download on first
   run into app-data.

### B) Electron Integration Strategy
1. Electron main process launches backend executable on app start.
2. Pass runtime config via env vars or startup args:
   - backend host/port
   - app-data root
   - log level
3. Main process polls `/health` until ready.
4. Main process handles restart-on-crash policy (bounded retries).
5. Renderer never talks to backend directly without main-process
   mediation unless explicitly allowed by security model.
6. CLI remains independently runnable for developer workflows and must
   not depend on Electron process lifecycle.

### C) Build Outputs
1. `dist/backend/<platform>/backend_server` (Python artifact)
2. `dist/electron/<platform>/EssayLensApp` (desktop app)
3. Installer metadata includes backend artifact and launcher config.

### D) CI/CD Build Matrix
1. macOS (arm64, x64)
2. Windows (x64)
3. Linux (x64)
4. Each job verifies backend boot + health endpoint + one smoke task.

## API Contracts (V1 Decision-Complete)

### `POST /analyze/topic-sentence`
- Request:
1. `file_path` (string, absolute or app-root-relative)
2. `max_concurrency` (optional int)
3. `output_json_path` (optional string)
- Response:
1. `job_id`
2. `status_url`

### `GET /jobs/{job_id}`
- Response:
1. `job_id`
2. `state`
3. `progress`
4. `result` (on success)
5. `error` (on failure)

### `POST /pipeline/run`
- Request:
1. `input_paths` or input folder selector
2. stage toggles (metadata/ged/fb/conclusion/body/content/summarize)
3. run options (single-paragraph mode, limits)
- Response:
1. `job_id`
2. `status_url`

## Security And Safety Defaults
1. Bind backend to `127.0.0.1` only.
2. Randomize port in allowed range unless fixed by config.
3. Generate per-session auth token shared only with Electron main
   process; require token on non-health endpoints.
4. Reject path traversal and enforce allowed root directories for file
   access in packaged mode.

## Testing Plan

### Unit Tests
1. Non-interactive model selection policy
2. Config/path resolution for packaged vs dev mode
3. Job manager transitions and cancellation
4. API schema validation and error envelopes

### Integration Tests
1. Backend startup and `/health`
2. Topic-sentence request end-to-end with sample `.docx`
3. Full pipeline job trigger with staged progress
4. Graceful shutdown tears down subprocesses

### Packaging Smoke Tests
1. Launch packaged app, backend starts, health passes
2. First-run bootstrap downloads required artifacts
3. Subsequent launch reuses cached artifacts
4. Failure injection: missing model, corrupted model, backend crash

## Rollout Plan
1. Phase 1: extract shared non-interactive orchestration/config/path
   core used by both CLI and Electron plans.
2. Phase 2: backend API skeleton + health/status + topic-sentence job.
3. Phase 3: full pipeline job endpoints + progress model.
4. Phase 4: Electron process management integration.
5. Phase 5: packaging and cross-platform build pipeline.
6. Phase 6: installer QA and release hardening.

## Acceptance Criteria
1. Electron can launch backend and receive healthy status within timeout.
2. User can submit topic-sentence analysis via frontend and receive
   structured result.
3. Backend performs full pipeline run via job API without terminal
   interaction.
4. Packaged app works on at least one macOS and one Windows target in
   QA.
5. Logs and errors are actionable for support/debugging.

## Risks And Mitigations
1. Large dependency footprint (`torch`, `spacy`) increases installer size.
   - Mitigation: separate optional model packages; defer heavy downloads
     to first run.
2. Cross-platform subprocess behavior differences.
   - Mitigation: explicit lifecycle tests on each OS.
3. Startup latency from model load.
   - Mitigation: warmup endpoint and UI progress indicators.
4. Path/permissions issues in locked-down environments.
   - Mitigation: strict app-data-only writes and preflight checks.

## Assumptions And Defaults Chosen
1. Transport is local HTTP API (not direct stdio) for easier debugging
   and tooling.
2. First-run model download is allowed and expected.
3. Electron main process owns backend lifecycle.
4. V1 progress is polling-based; SSE/WebSocket deferred.
5. Existing NLP pipeline logic is reused rather than rewritten.
6. CLI and Electron remain in one repo and share core orchestration,
   while each keeps a separate interface adapter layer.
