# CLI Module Plan: Slash Commands with `@file` Targeting

## Summary
Implement a new CLI module that supports:
1. Interactive slash-command mode: `essaylens shell` then `/topic-sentence @Assessment/in/essay.docx`
2. Script-friendly subcommand mode: `essaylens topic-sentence --file Assessment/in/essay.docx`

The implementation will reuse existing app wiring (`build_settings`,
`build_container`, `LlmTaskService`) and existing text loaders
(`DocumentInputService`) so analysis logic stays in one place. Default
output will be concise terminal text plus a detailed JSON artifact.

## Goals And Success Criteria
- Users can run topic-sentence analysis for a specific file using either
  slash REPL syntax or standard CLI syntax.
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
4. `@file` path parsing/validation
5. JSON output writer for command results
6. Unit tests for parser plus integration-level command tests

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

## Public Interfaces And Commands
- New executable entrypoint:
1. `python -m app.cli` (initial)
2. Optional packaging alias later: `essaylens`

- New command interfaces:
1. `shell` interactive mode
2. `topic-sentence --file <path> [--json-out <path>] [--max-concurrency <n>]`

- Slash syntax in `shell`:
1. `/topic-sentence @path/to/file.docx`
2. `/topic-sentence @"path with spaces/file.docx"`
3. Utility commands: `/help`, `/exit`

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
     - build container
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

## Data Flow (Topic Sentence Command)
1. Parse command (shell slash line or subcommand args).
2. Resolve file path:
   - strip `@`
   - unquote if quoted
   - resolve relative to current working directory
3. Validate path exists and extension supported (`.docx`, `.pdf`).
4. Build app config via `build_settings()`.
5. Reuse non-interactive model defaults:
   - keep persisted model/OCR behavior
   - avoid prompt-driven selection in CLI path
6. Build dependencies via `build_container(app_cfg)`.
7. Load document blocks using `document_input_service.load(path)`.
8. Construct task payload from loaded blocks (single request per target
   file for now).
9. Execute `llm_task_service.analyze_topic_sentence_parallel(...)`.
10. Render concise output to terminal.
11. Persist full JSON output:
   - default path:
     `Assessment/explained/cli/<stem>.topic_sentence.json` unless
     overridden by `--json-out`.
12. Exit with code:
   - `0` success
   - non-zero for parse/IO/runtime failures

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

- Runner/runtime tests (mocked LLM task service):
1. `.docx` happy path
2. `.pdf` happy path
3. missing file
4. unsupported extension
5. JSON output path override
6. default JSON output location

- REPL tests:
1. `/help` output
2. `/exit` terminates loop
3. command error does not terminate loop

- Exit code tests:
1. success returns `0`
2. parse/runtime failure returns non-zero

## Acceptance Criteria
1. `python -m app.cli topic-sentence --file Assessment/in/sample.docx`
   runs and writes JSON artifact.
2. `python -m app.cli shell` accepts
   `/topic-sentence @Assessment/in/sample.docx`.
3. Both modes produce consistent analysis payload shape.
4. Test suite additions pass.

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
