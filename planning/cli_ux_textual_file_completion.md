# To run one-shot tests in the terminal:
python -m cli.tui_app (will load a minimal TUI app)
python -m cli.main shell (run from command line)

# Textual `@file` Recursive Autocomplete Plan

## Summary
Add recursive `@file` autocomplete to `cli/tui_app.py` so that when a
user types a command like `/topic-sentence @...`, the UI shows matching
files under the current working directory and all nested folders.

Autocomplete trigger policy:
1. activate only for `@` token in command input
2. start search once query length after `@` reaches 4 characters
3. update suggestions as user types
4. support keyboard navigation and insertion

## Goals And Success Criteria
- Users get live file suggestions for `@` paths while typing.
- Suggestions search recursively from current working directory.
- Suggestions are responsive and do not block the Textual UI.
- Selecting a suggestion replaces only the active `@...` token.
- Existing command parsing and execution behavior remains unchanged.

## Scope
- In scope:
1. `@token` detection in `Input` text
2. recursive file indexing/search worker
3. suggestion popover/list widget under command input
4. keyboard controls for suggestion navigation and selection
5. ignore rules to reduce noisy/unwanted directories

- Out of scope (first iteration):
1. fuzzy ranking libraries
2. persistent index database
3. symlink-heavy traversal optimizations
4. autocomplete for non-file command arguments

## Cross-Compatibility Requirements
1. No changes to NLP task code.
2. No change to `CliSession` command semantics.
3. Parser behavior stays authoritative at submit time.
4. Feature is additive for TUI only; shell/one-shot CLI unchanged.

## Proposed File/Module Changes
1. `cli/tui_app.py`
   - add autocomplete state hooks
   - add suggestion widget creation and rendering
   - add key handlers for up/down/tab/enter/escape
2. `cli/tui_state.py`
   - add fields:
     - `completion_active: bool`
     - `completion_query: str`
     - `completion_items: list[str]`
     - `completion_index: int`
3. new helper module: `cli/file_completion.py`
   - token extraction helpers
   - recursive search helpers
   - ranking and filtering
4. tests: `tests/test_cli_file_completion.py`
5. tests: extend `tests/test_cli_tui_runtime.py` with completion
   interaction coverage

## UX Rules (Decision-Complete)
1. Trigger condition:
   - current input contains an active `@token` (token being edited)
   - token query length >= 4
2. Suggestion visibility:
   - show list only when matches exist
   - hide list on:
     - query length < 4
     - no active `@token`
     - ESC key
     - command submit
3. Candidate cap:
   - max 20 items shown
4. Insert behavior:
   - TAB or ENTER on suggestion inserts selected path into active token
   - inserted text is quoted if path contains spaces
   - `@` prefix is preserved
5. Navigation keys:
   - UP/DOWN moves highlighted suggestion
   - TAB confirms highlighted suggestion
   - ESC closes suggestions

## Search And Ranking Rules (Decision-Complete)
1. Search root:
   - `Path.cwd()`
2. Traversal:
   - recursive file scan with `Path.rglob("*")` or `os.walk`
   - include files only (no directories in V1)
3. Default ignore directories:
   - `.git`, `venv`, `.venv`, `__pycache__`, `third_party`, `.appdata`
4. Matching strategy (case-insensitive):
   - score 0: filename startswith query
   - score 1: filename contains query
   - score 2: full relative path contains query
   - then alphabetical by relative path
5. Returned path format:
   - relative path from cwd for display and insertion

## Performance Strategy
1. Debounce input-triggered search by 150ms.
2. Execute search in background thread (`asyncio.to_thread`).
3. Cancel stale in-flight searches when newer query arrives.
4. Cache last query results in memory for incremental typing in same
   session.

## Data Flow
1. User types into input widget.
2. `on_input_changed` inspects active token.
3. If completion trigger met, schedule debounced search worker.
4. Worker returns ranked paths.
5. UI updates suggestion list and highlight index.
6. User selects suggestion -> token replacement in input text.
7. Final submitted command still runs through `parse_shell_command`.

## Edge Cases
1. Multiple `@` tokens in one line:
   - autocomplete applies to token currently being edited (nearest token
     covering cursor position).
2. Quoted `@"path with spaces"` partial tokens:
   - parser tolerant at UI layer; final parser still validates on submit.
3. No matches:
   - hide suggestion list silently.
4. Very large repos:
   - capped results + ignored dirs + background worker to prevent UI
     freeze.

## Testing Plan

### Unit Tests (`tests/test_cli_file_completion.py`)
1. Active token extraction from command line.
2. Token replacement logic preserves `@` and spacing.
3. Ranking order correctness (startswith > contains > path contains).
4. Ignore directory filtering.
5. Quoted insertion when path contains spaces.

### TUI Runtime Tests (`tests/test_cli_tui_runtime.py`)
1. Suggestions appear after 4-char query.
2. Suggestions hidden when query drops below threshold.
3. Up/down changes selected index.
4. Tab inserts selected suggestion.
5. Esc closes suggestion list.
6. Submitting command clears suggestions.

### Manual Smoke Tests
1. Start TUI: `python -m cli.tui_app`.
2. Type `/topic-sentence @asse` and verify suggestions appear.
3. Continue typing to narrow results.
4. Select with arrows + tab/enter.
5. Submit command and verify normal execution.

## Acceptance Criteria
1. Autocomplete appears only for `@` token with query length >= 4.
2. Suggestions are recursive from cwd with ignore rules applied.
3. UI remains responsive during search.
4. Suggestion insert produces valid path token for command parser.
5. Existing command execution behavior is unchanged.

## Rollout Plan
1. Add `cli/file_completion.py` helpers and tests.
2. Add completion state to `TuiState`.
3. Implement suggestion UI and keybindings in `cli/tui_app.py`.
4. Add debounce + background search + stale result cancellation.
5. Extend runtime tests and run full CLI/TUI test suite.

## Assumptions And Defaults Chosen
1. Minimum query length is 4 characters.
2. Suggestions include files only in V1.
3. Search root is current working directory.
4. Existing parser remains final source of command validity.
