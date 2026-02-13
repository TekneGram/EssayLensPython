# Minimal Textual TUI Plan For Existing CliSession

## Summary
Build a minimal Textual-based terminal UI that uses the existing
`cli.runner.CliSession` as the backend command/runtime layer. The TUI
must support the same core operations already available in the shell CLI:

1. LLM/OCR model management
   - `/llm-list`
   - `/llm-start [model_key]`
   - `/llm-stop`
   - `/llm-switch <model_key>`
   - `/llm-status`
   - `/ocr-start [model_key]`
2. Task execution
   - `/topic-sentence @path/to/file.docx`

This is a UI adapter project, not a backend rewrite.

## Goals And Success Criteria
- Users can run model-management commands from an interactive Textual
  interface.
- Users can run `topic-sentence` analysis and view concise output in the
  TUI log pane.
- Existing lazy-start behavior remains unchanged (selection commands do
  not force server start; task command triggers runtime start).
- Existing `CliSession` methods are reused directly.
- The app exits cleanly and unloads warm LLM runtime on quit.

## Scope
- In scope:
1. New `cli/tui_app.py` Textual app entrypoint
2. Command input bar with slash-command parsing
3. Output/log pane for command results and errors
4. Status pane showing selected model + runtime state
5. Basic command history (session-only in memory)
6. Async-safe execution for long-running commands

- Out of scope (first iteration):
1. Full file browser UI
2. Fancy progress streaming/token streaming
3. Mouse-heavy UX and advanced theming
4. Replacing existing `cli.main` shell or one-shot commands

## Cross-Compatibility Requirements (CLI Shell + TUI + Electron)
1. TUI is another adapter layer over `CliSession`; no NLP task code
   duplication.
2. TUI must not modify core runtime behavior used by `cli.main`.
3. TUI and shell must produce equivalent command outcomes.
4. Runtime lifecycle cleanup must remain compatible with Electron shared
   lifecycle principles.

## Proposed File/Module Additions
1. `cli/tui_app.py`
   - Textual app class (`EssayLensTuiApp`)
   - layout composition
   - command dispatch to `CliSession`
2. `cli/tui_state.py`
   - small state container for UI session data:
     - command history
     - current status snapshot
     - last error/last result
3. `tests/test_cli_tui_runtime.py`
   - non-visual tests for command dispatch and lifecycle hooks

## Public Entrypoints
1. `python -m cli.tui_app`
2. Existing entrypoints remain:
   - `python -m cli.main shell`
   - `python -m cli.main <subcommand>`

## UI Layout (Minimal)
1. Header: app title + key hints (`Ctrl+C`, `Ctrl+L`, `:help`)
2. Main area split:
   - Left pane: output log (command results and errors)
   - Right pane: runtime/model status summary
3. Footer input: command line prompt accepting slash commands

## Command Handling Design
1. Reuse existing parser:
   - call `cli.parser.parse_shell_command(raw)`
2. Dispatch command names directly to `CliSession` methods:
   - `llm-list` -> `session.list_models()`
   - `llm-start` -> `session.configure_llm_selection(...)`
   - `ocr-start` -> `session.configure_ocr_selection(...)`
   - `llm-stop` -> `session.stop_llm()`
   - `llm-switch` -> `session.switch_llm(...)`
   - `llm-status` -> `session.status()`
   - `topic-sentence` -> `session.run_topic_sentence(...)`
3. For long-running calls (`topic-sentence`):
   - run in worker thread/task (`Textual` worker API)
   - append completion/error message back to log pane

## Lifecycle And Cleanup
1. App startup:
   - instantiate single `CliSession`
   - render initial status from `session.status()`
2. During runtime:
   - keep warm LLM process behavior as already implemented in `CliSession`
3. App shutdown (`on_unmount` or quit action):
   - call `session.stop_llm()` exactly once
   - swallow cleanup exceptions but log them

## Error Handling
1. Parse errors are displayed in log pane with `Error:` prefix.
2. Runtime exceptions from `CliSession` are displayed as user-facing
   error lines.
3. TUI remains running after command failures.

## Dependencies
- Add `textual` (and implicitly `rich`) to runtime dependencies.
- Keep existing dependencies unchanged otherwise.

## Testing Plan

### Unit/Runtime Tests
1. Command parse + dispatch maps to expected `CliSession` methods.
2. `topic-sentence` is executed through background worker path.
3. `llm-stop` called on app shutdown.
4. Parse error does not crash app loop.

### Manual Smoke Tests
1. `python -m cli.tui_app` launches.
2. `/llm-list` shows model rows.
3. `/llm-start <key>` persists selection and reports status.
4. `/llm-status` updates status pane.
5. `/topic-sentence @Assessment/in/sample.docx` runs and writes JSON.
6. Quit app and verify model process is unloaded.

## Acceptance Criteria
1. TUI runs with `python -m cli.tui_app`.
2. All required commands execute successfully from the TUI command bar.
3. `topic-sentence` runs without freezing the UI.
4. Warm LLM lifecycle behavior matches existing shell semantics.
5. Exiting TUI triggers cleanup of warm LLM runtime.

## Rollout Plan
1. Add `textual` dependency and `cli/tui_app.py` scaffold.
2. Wire command input -> parser -> session dispatch.
3. Add status pane refresh hooks after each command.
4. Add worker execution path for long-running commands.
5. Add tests and run smoke checks.
6. Document TUI usage in CLI docs.

## Assumptions And Defaults Chosen
1. TUI is command-driven first (not button-first) to keep scope minimal.
2. Existing `CliSession` stays source of truth for runtime behavior.
3. TUI output is textual summaries; detailed artifacts remain JSON files.
4. No changes to existing `main.py` pipeline entrypoint.
