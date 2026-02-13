# CLI Module Plan: Slash Commands with `@file` Targeting

## Summary
Implement a new CLI module that supports:
1. Interactive slash-command mode: `essaylens shell` then `/topic-sentence @Assessment/in/essay.docx`
2. Script-friendly subcommand mode: `essaylens topic-sentence --file Assessment/in/essay.docx`
3. Explicit model-management commands for LLM/OCR setup and runtime control:
   - `/llm-list`, `/llm-start`, `/llm-stop`, `/llm-switch`, `/llm-status`
   - `/ocr-start`

The implementation will reuse existing app wiring (`build_settings`,
`build_container`, `LlmTaskService`) and existing text loaders
(`DocumentInputService`) so analysis logic stays in one place. Default
output will be concise terminal text plus a detailed JSON artifact.

## Goals And Success Criteria
- Users can run topic-sentence analysis for a specific file using either
  slash REPL syntax or standard CLI syntax.
- Users can list/select/download LLMs and OCR models from CLI commands.
- Model selection persists as configuration memory without forcing model
  load at selection time.
- LLM server starts lazily on first LLM-backed task command and stays
  warm for session reuse.
- Users can stop/switch the warm LLM instance explicitly.
- `@file` parsing supports quoted paths and spaces.
- File type support for `.docx` and `.pdf` matches existing
  `DocumentInputService`.
- Analysis result is printed and persisted as JSON in a predictable
  output location.
- Runtime is robust: clear error messages for invalid commands,
  missing files, unsupported types, and service startup failures.

## Scope
- In scope:
1. New CLI package/module for command parsing and execution
2. Slash REPL parser and dispatcher
3. `topic-sentence` command path wired to existing
   `LlmTaskService.analyze_topic_sentence_parallel`
4. LLM/OCR model-management commands and persistence behavior
5. `@file` path parsing/validation
6. JSON output writer for command results
7. Unit tests for parser plus integration-level command tests

- Out of scope (for this iteration):
1. Full parity for every pipeline command
2. Interactive model selection redesign
3. Electron integration

## Cross-Plan Compatibility Requirements (CLI + Electron)
1. CLI must run as a thin interface adapter over shared non-interactive
   application services, not a separate execution stack.
2. CLI entrypoint remains `app.cli`; Electron backend entrypoint remains
   `app.backend_server`; neither should import UI transport logic from
   the other.
3. Any orchestration extracted from `main.py` must be reusable by both
   CLI and Electron backend API to avoid drift in behavior.
4. CLI default output paths must remain namespaced under
   `.../cli/...` and never overwrite Electron-owned output locations.
5. Shared config/path resolution must support both:
   - developer repo-relative paths for local CLI use
   - app-data-root paths for packaged Electron runtime
6. Shared runtime process controls (`llama-server`, OCR server) must use
   common lifecycle primitives so shutdown/startup behavior is
   consistent across interfaces.
7. Error and result payload shapes should align with backend API models
   where practical so frontend and CLI reporting stay consistent.
8. NLP task implementations and existing service-layer logic are reused
   directly; CLI-specific behavior should be limited to command parsing,
   lifecycle policy, and model-management UX.

## Public Interfaces And Commands
- New executable entrypoint:
1. `python -m app.cli` (initial)
2. Optional packaging alias later: `essaylens`

- New command interfaces:
1. `shell` interactive mode
2. `topic-sentence --file <path> [--json-out <path>] [--max-concurrency <n>]`
3. `llm-list`
4. `llm-start [--model-key <key>]`
5. `llm-stop`
6. `llm-switch --model-key <key>`
7. `llm-status`
8. `ocr-start [--model-key <key>]`

- Slash syntax in `shell`:
1. `/topic-sentence @path/to/file.docx`
2. `/topic-sentence @"path with spaces/file.docx"`
3. `/llm-list`
4. `/llm-start` or `/llm-start <model_key>`
5. `/llm-stop`
6. `/llm-switch <model_key>`
7. `/llm-status`
8. `/ocr-start` or `/ocr-start <model_key>`
9. Utility commands: `/help`, `/exit`

## Proposed File/Module Additions
1. `app/cli.py`
   - `main(argv: list[str] | None = None) -> int`
   - top-level argparse/subcommand routing
2. `app/cli_shell.py`
   - REPL loop, slash parsing, dispatch calls
3. `app/cli_parser.py`
   - slash-command grammar parser
   - `@file` token extraction and validation helpers
4. `app/cli_runner.py`
   - command execution layer:
     - load settings
     - run CLI model-management commands
     - lazily build container/start server when LLM task command runs
     - prepare `LlmTaskService`
     - call topic-sentence analysis
5. `app/cli_output.py`
   - print concise user-facing result
   - write JSON artifact
6. `tests/test_cli_parser.py`
7. `tests/test_cli_topic_sentence_runtime.py`
8. `tests/test_cli_shell_runtime.py`
9. shared core modules (from Electron plan) consumed, not duplicated:
   - non-interactive orchestration layer
   - shared config/path resolver
   - shared result/error schema helpers
10. optional CLI session-state module:
   - tracks selected model key, running server state, and warm session

## Data Flow (Topic Sentence Command)
1. Parse command (shell slash line or subcommand args).
2. Resolve file path:
   - strip `@`
   - unquote if quoted
   - resolve relative to current working directory
3. Validate path exists and extension supported (`.docx`, `.pdf`).
4. Load CLI session config memory:
   - selected LLM key from persisted config (`.appdata/config/llm_model.json`)
   - selected OCR key from persisted config (`.appdata/config/ocr_model.json`)
5. If LLM server is not running, build app config and resolve runtime
   artifacts in this exact order:
   - `build_settings()`
   - `select_model_and_update_config(app_cfg)` in CLI-driven mode
     (non-interactive unless explicit CLI selection prompt is invoked)
   - `select_ocr_model_and_update_config(app_cfg)` in CLI-driven mode
   - `bootstrap_llm(app_cfg)` to ensure GGUF/mmproj/server binary exist
6. Build dependencies via `build_container(app_cfg)` if not already
   initialized for this shell session.
7. Start LLM server process (`server_proc.start()`) only when needed for
   the first LLM-backed task command.
8. Load document blocks using `document_input_service.load(path)`.
9. Construct task payload from loaded blocks (single request per target
   file for now).
10. Execute `llm_task_service.analyze_topic_sentence_parallel(...)`.
11. Render concise output to terminal.
12. Persist full JSON output:
   - default path:
     `Assessment/explained/cli/<stem>.topic_sentence.json` unless
     overridden by `--json-out`.
13. Keep server warm in REPL mode; stop in `finally` for one-shot
   subcommand mode.
14. Exit with code:
   - `0` success
   - non-zero for parse/IO/runtime failures

## Startup And Lifecycle Policy (Decision-Complete)
1. Non-interactive model selection is mandatory for CLI flows:
   - no `input()` prompts are allowed in CLI execution paths.
   - persisted model key is used when valid.
   - fallback is hardware-based recommended model if no valid persisted
     key exists.
2. Startup sequence for one-shot subcommands
   (`essaylens topic-sentence --file ...`):
   - run config/model/bootstrap sequence
   - build container
   - start LLM server once
   - run command
   - stop LLM server before process exit
3. Startup sequence for interactive shell (`essaylens shell`):
   - initialize parser and shell loop immediately
   - delay config/bootstrap/server startup until first LLM-backed
     command (lazy start)
   - keep server warm across subsequent LLM commands in the same shell
     session
   - allow explicit model setup before execution with:
     - `/llm-list` to inspect models
     - `/llm-start [model_key]` to persist/select model (and optionally
       download artifacts) without starting server
     - `/ocr-start [model_key]` to persist/select OCR model
     - `/llm-switch <model_key>` to stop warm server, update selection,
       and restart lazily on next task command
     - `/llm-stop` to unload warm model immediately
   - stop server on `/exit`, EOF, SIGINT, and unhandled shell errors
4. Health and readiness:
   - LLM command execution is blocked until `server_proc.start()` health
     check succeeds.
   - startup timeout and error from server startup are surfaced as
     user-facing CLI errors.
5. Failure handling:
   - if startup fails, command exits non-zero and does not continue to
     task execution.
   - if command execution fails after startup, server is still stopped
     via `finally`.
6. Future compatibility requirement:
   - CLI lifecycle hooks must delegate to the same shared runtime
     lifecycle primitives used by the Electron backend plan.

## Model-Management Command Semantics (Decision-Complete)
1. `/llm-list`
   - enumerates installed and downloadable models using existing model
     specs and local model directory checks.
2. `/llm-start [model_key]`
   - if `model_key` provided: set/persist selected LLM key.
   - if omitted: show available choices and prompt in CLI shell.
   - ensures selected model artifacts are available (download if needed
     by current policy).
   - does not start `llama-server`; this command sets selection memory.
3. `/ocr-start [model_key]`
   - same selection/persistence semantics as LLM command but for OCR.
   - does not start LLM server.
4. `/llm-status`
   - reports selected model key, running/stopped state, and current
     server endpoint if running.
5. `/llm-stop`
   - stops running LLM server if active; no-op if already stopped.
6. `/llm-switch <model_key>`
   - persists new model selection key.
   - if LLM server is running: stop current server immediately.
   - new model starts lazily on next LLM-backed task command.

## Command Parsing Rules (Decision-Complete)
- Slash commands must start with `/`.
- Command keyword is first token after `/`.
- `@file` must be present exactly once for `/topic-sentence`.
- File token forms:
1. `@relative/path.docx`
2. `@/absolute/path.docx`
3. `@"relative path/essay 1.docx"`
4. `@"/absolute path/essay 1.docx"`
- If file token missing or malformed: show usage and return parse error.
- Unknown slash command: show list of supported commands.

## Error Handling And UX
- Standardized, short errors:
1. `File not found: ...`
2. `Unsupported file type: ... (supported: .docx, .pdf)`
3. `LLM service unavailable: ...`
4. `Command parse error: ...`
- REPL keeps running after command errors; exits only on `/exit` or EOF.
- Subcommand mode returns non-zero exit code on failure.

## Testing Plan
- Parser unit tests:
1. Parse `/topic-sentence @foo.docx`
2. Parse quoted paths with spaces
3. Reject missing `@file`
4. Reject unknown slash command
5. Reject extra unexpected positional tokens
6. Parse `/llm-list`, `/llm-start`, `/llm-stop`, `/llm-switch`, `/llm-status`
7. Parse `/ocr-start`

- Runner/runtime tests (mocked LLM task service):
1. `.docx` happy path
2. `.pdf` happy path
3. missing file
4. unsupported extension
5. JSON output path override
6. default JSON output location
7. one-shot subcommand starts and stops LLM server exactly once
8. startup failure returns non-zero and does not execute LLM task
9. runtime failure still triggers server stop
10. `/llm-start` persists model without starting server
11. `/llm-switch` stops running server and updates selection memory
12. `/llm-stop` unloads running server and is idempotent

- REPL tests:
1. `/help` output
2. `/exit` terminates loop
3. command error does not terminate loop
4. first LLM command lazy-starts server
5. second LLM command reuses warm server instance
6. shell exit stops running server
7. `/llm-list` returns installed/downloadable model sets
8. `/llm-start` then `/topic-sentence` starts selected model lazily
9. `/llm-switch` applies to next task command without NLP task code changes

- Exit code tests:
1. success returns `0`
2. parse/runtime failure returns non-zero

## Acceptance Criteria
1. `python -m app.cli topic-sentence --file Assessment/in/sample.docx`
   runs and writes JSON artifact.
2. `python -m app.cli shell` accepts
   `/topic-sentence @Assessment/in/sample.docx`.
3. `python -m app.cli shell` supports `/llm-list`, `/llm-start`,
   `/llm-stop`, `/llm-switch`, `/llm-status`, `/ocr-start`.
4. `/llm-start` persists selection without forcing immediate model load.
5. First LLM-backed task command loads server/model lazily and reuses it
   for subsequent LLM commands in the same REPL session.
6. Both modes produce consistent analysis payload shape.
7. Test suite additions pass.

## Rollout Steps
1. Implement/consume shared non-interactive orchestration layer first
   (joint dependency with Electron plan).
2. Add CLI modules and tests as a transport adapter over shared core.
3. Validate local smoke run with one real sample file.
4. Add a short usage section to project docs (`README` or `AGENTS`
   adjacent docs).
5. Optional follow-up: add command aliases for other analysis tasks.

## Assumptions And Defaults Chosen
1. Primary UX style: hybrid (REPL plus subcommands), to preserve
   Codex-like interaction and scriptability.
2. Default output policy: console summary plus JSON artifact file.
3. Initial scope is only `topic-sentence` to establish CLI architecture
   before expanding to other tasks.
4. CLI command path uses existing model persistence/defaults and avoids
   interactive prompts.
5. CLI and Electron will coexist in one repository with shared core
   services and separate interface adapters.
6. CLI startup behavior uses lazy-start warm sessions for REPL and
   start/stop-per-invocation for one-shot subcommands.
7. Existing NLP task modules are reused directly; no duplication of NLP
   task code is allowed in CLI implementation.
