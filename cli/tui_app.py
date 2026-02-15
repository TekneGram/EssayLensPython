from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from cli.file_completion import (
    ActiveAtToken,
    find_active_at_token,
    find_matching_files,
    normalize_selected_path,
    replace_active_at_token,
)
from cli.parser import parse_shell_command
from cli.tui_state import TuiState
from cli.worker_client import WorkerClient, WorkerClientError, WorkerCommandError

try:
    from textual.app import App, ComposeResult
    from textual.containers import Container, Vertical
    from textual.widgets import Footer, Header, Input, RichLog, Static
except Exception:  # pragma: no cover - exercised in runtime environments without textual.
    App = object  # type: ignore[assignment]
    ComposeResult = object  # type: ignore[assignment]
    Container = object  # type: ignore[assignment]
    Vertical = object  # type: ignore[assignment]
    Footer = object  # type: ignore[assignment]
    Header = object  # type: ignore[assignment]
    Input = object  # type: ignore[assignment]
    RichLog = object  # type: ignore[assignment]
    Static = object  # type: ignore[assignment]
    TEXTUAL_AVAILABLE = False
else:
    TEXTUAL_AVAILABLE = True


def _render_status(status: dict[str, Any]) -> str:
    selected = str(status.get("selected_llm_key") or "<none>")
    runtime = "running" if status.get("running") else "stopped"
    endpoint = str(status.get("endpoint") or "<none>")
    return "\n".join(
        [
            "Runtime Status",
            "--------------",
            f"Selected LLM: {selected}",
            f"Runtime: {runtime}",
            f"Endpoint: {endpoint}",
        ]
    )


def _format_model_rows(title: str, rows: list[dict[str, Any]]) -> list[str]:
    lines = [title]
    for row in rows:
        markers: list[str] = []
        if row.get("selected"):
            markers.append("selected")
        if row.get("recommended"):
            markers.append("recommended")
        if row.get("installed"):
            markers.append("installed")
        marker_str = f" ({', '.join(markers)})" if markers else ""
        lines.append(f"  - {row['key']}: {row['display_name']}{marker_str}")
    return lines


def _help_lines() -> list[str]:
    return [
        "Commands:",
        "  /help",
        "  /exit",
        "  /llm-list",
        "  /llm-start [model_key]",
        "  /llm-stop",
        "  /llm-switch <model_key>",
        "  /llm-status",
        "  /ocr-start [model_key]",
        "  /topic-sentence @path/to/file.docx",
        "  /metadata @path/to/file.docx",
        "  /prompt-test @path/to/file.docx",
    ]


if TEXTUAL_AVAILABLE:

    class EssayLensTuiApp(App[None]):
        TITLE = "EssayLens TUI"
        COMPLETION_VIEWPORT_ROWS = 8
        CSS = """
        Screen {
            background: #e6e6e6;
            color: #111111;
        }
        #root {
            layout: vertical;
            height: 100%;
        }
        #main {
            layout: horizontal;
            height: 1fr;
        }
        #left {
            width: 2fr;
            border: round $primary;
            padding: 1;
            background: #f2f2f2;
            color: #111111;
        }
        #right {
            width: 1fr;
            border: round $accent;
            padding: 1;
            background: #f2f2f2;
            color: #111111;
        }
        #cmd {
            dock: bottom;
            margin: 1 0 0 0;
        }
        #completion {
            dock: bottom;
            border: round $secondary;
            padding: 0 1;
            max-height: 8;
            margin: 0;
            display: block;
            overflow-y: scroll;
        }
        #status {
            height: 1fr;
        }
        RichLog {
            background: #f7f7f7;
            color: #111111;
        }
        Input {
            background: #f7f7f7;
            color: #111111;
        }
        """

        BINDINGS = [
            ("ctrl+l", "clear_log", "Clear Log"),
            ("ctrl+c", "quit", "Quit"),
            ("up", "completion_up", "Completion Up"),
            ("down", "completion_down", "Completion Down"),
            ("tab", "completion_apply", "Completion Apply"),
            ("escape", "completion_cancel", "Completion Cancel"),
        ]

        def __init__(self, worker: WorkerClient | None = None) -> None:
            super().__init__()
            self.worker = worker or WorkerClient()
            self.state = TuiState()
            self._completion_task: asyncio.Task[None] | None = None
            self._completion_nonce = 0
            self._busy = False

        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)
            with Container(id="root"):
                with Container(id="main"):
                    with Vertical(id="left"):
                        yield Static("Output", classes="pane-title")
                        yield RichLog(id="log", highlight=False, wrap=True)
                    with Vertical(id="right"):
                        yield Static("Status", classes="pane-title")
                        yield Static(id="status")
                yield Input(placeholder="Type slash command, e.g. /llm-list", id="cmd")
                yield Static(id="completion")
            yield Footer()

        async def on_mount(self) -> None:
            self._log("EssayLens TUI ready. Type /help for commands.")
            try:
                await self.worker.start()
            except Exception as exc:
                self._log(f"Worker failed to start: {exc}")
            await self._refresh_status()
            self._render_completion()
            self.query_one(Input).focus()

        async def on_unmount(self) -> None:
            await self.worker.shutdown()

        def action_clear_log(self) -> None:
            self.query_one(RichLog).clear()
            self._log("Log cleared.")

        def action_completion_up(self) -> None:
            if not self.state.completion_active or not self.state.completion_items:
                return
            self.state.completion_index = (self.state.completion_index - 1) % len(self.state.completion_items)
            self._render_completion()

        def action_completion_down(self) -> None:
            if not self.state.completion_active or not self.state.completion_items:
                return
            self.state.completion_index = (self.state.completion_index + 1) % len(self.state.completion_items)
            self._render_completion()

        def action_completion_apply(self) -> None:
            if not self.state.completion_active or not self.state.completion_items:
                return
            cmd_input = self.query_one(Input)
            current_text = cmd_input.value
            current_cursor = getattr(cmd_input, "cursor_position", len(current_text))

            token = find_active_at_token(current_text, current_cursor)
            if token is None:
                source_matches = (
                    self.state.completion_source_text == current_text
                    and self.state.completion_source_cursor == current_cursor
                )
                if not source_matches:
                    self._log("Error: completion state is stale, please try again.")
                    self._schedule_completion(current_text, current_cursor)
                    return
                token = ActiveAtToken(
                    start=self.state.completion_start,
                    end=self.state.completion_end,
                    query=self.state.completion_query,
                )

            selected_path = self.state.completion_items[self.state.completion_index]
            selected_path = normalize_selected_path(selected_path, root=Path.cwd())
            new_text = replace_active_at_token(current_text, token, selected_path)
            cmd_input.value = new_text
            cmd_input.cursor_position = len(new_text)
            self._log(f"Applied completion: {selected_path}")
            self._clear_completion()

        def action_completion_cancel(self) -> None:
            if not self.state.completion_active:
                return
            self._clear_completion()

        async def on_input_changed(self, event: Input.Changed) -> None:
            cursor = getattr(event.input, "cursor_position", len(event.value or ""))
            self._schedule_completion(event.value or "", cursor)

        async def on_input_submitted(self, event: Input.Submitted) -> None:
            if self.state.completion_active and self.state.completion_items:
                self.action_completion_apply()
                return

            if self._busy:
                self._log("Busy: previous command still running.")
                return

            raw = (event.value or "").strip()
            event.input.value = ""
            self._clear_completion()
            if not raw:
                return
            self.state.command_history.append(raw)
            self._log(f"> {raw}")

            try:
                parsed = parse_shell_command(raw)
            except Exception as exc:
                self.state.last_error = str(exc)
                self._log(f"Error: {exc}")
                return

            if parsed.name == "exit":
                self.exit()
                return

            try:
                self._busy = True
                await self._dispatch(parsed.name, parsed.args)
            except WorkerCommandError as exc:
                self.state.last_error = str(exc)
                if exc.stage:
                    self._log(f"Error at stage {exc.stage}: {exc}")
                else:
                    self._log(f"Error: {exc}")
                if "fds_to_keep" in str(exc):
                    self._log(
                        "Runtime startup failed in worker process; retry one-shot CLI command for verification."
                    )
                if exc.traceback_text:
                    self._log(f"[debug] traceback:\\n{exc.traceback_text}")
            except WorkerClientError as exc:
                self.state.last_error = str(exc)
                self._log(f"Worker transport error: {exc}")
            except Exception as exc:
                self.state.last_error = str(exc)
                self._log(f"Error: {exc}")
            finally:
                self._busy = False
                await self._refresh_status()

        async def _dispatch(self, name: str, args: dict[str, Any]) -> None:
            if name == "help":
                for line in _help_lines():
                    self._log(line)
                return

            if name == "llm-list":
                rows = await self.worker.call("llm-list", {})
                for line in _format_model_rows("LLM models", rows["llm"]):
                    self._log(line)
                for line in _format_model_rows("OCR models", rows["ocr"]):
                    self._log(line)
                self.state.last_result = rows
                return

            if name == "llm-start":
                model_key = args.get("model_key")
                result = await self.worker.call("llm-start", {"model_key": model_key})
                self._log(result["message"])
                self._log(f"Selected LLM: {result['selected_llm_key']}")
                self.state.last_result = result
                return

            if name == "ocr-start":
                model_key = args.get("model_key")
                result = await self.worker.call("ocr-start", {"model_key": model_key})
                self._log(result["message"])
                self._log(f"Selected OCR model: {result['selected_ocr_key']}")
                self.state.last_result = result
                return

            if name == "llm-stop":
                stop_result = await self.worker.call("llm-stop", {})
                stopped = bool(stop_result.get("stopped", False))
                self._log("LLM server stopped." if stopped else "LLM server already stopped.")
                self.state.last_result = {"stopped": stopped}
                return

            if name == "llm-switch":
                model_key = str(args["model_key"])
                result = await self.worker.call("llm-switch", {"model_key": model_key})
                self._log(result["message"])
                self._log(f"Selected LLM: {result['selected_llm_key']}")
                self.state.last_result = result
                return

            if name == "llm-status":
                status = await self.worker.call("llm-status", {})
                for line in _render_status(status).splitlines():
                    self._log(line)
                self.state.last_result = status
                return

            if name == "topic-sentence":
                file_path = str(args["file"])
                max_concurrency = args.get("max_concurrency")
                json_out = args.get("json_out")
                self._log("Starting runtime and running topic sentence analysis...")
                result = await self.worker.call(
                    "topic-sentence",
                    {
                        "file": file_path,
                        "max_concurrency": max_concurrency,
                        "json_out": json_out,
                    },
                )
                self._log("Topic sentence analysis complete.")
                self._log(f"File: {result['file']}")
                self._log(f"Suggested topic sentence: {result['suggested_topic_sentence']}")
                self._log(f"Feedback: {result['feedback']}")
                self._log(f"JSON: {result['json_out']}")
                self.state.last_result = result
                return

            if name == "metadata":
                file_path = str(args["file"])
                json_out = args.get("json_out")
                self._log("Starting runtime and running metadata extraction...")
                result = await self.worker.call(
                    "metadata",
                    {
                        "file": file_path,
                        "json_out": json_out,
                    },
                )
                metadata = result.get("metadata", {})
                self._log("Metadata extraction complete.")
                self._log(f"File: {result['file']}")
                self._log(f"Student Name: {metadata.get('student_name', '')}")
                self._log(f"Student Number: {metadata.get('student_number', '')}")
                self._log(f"Essay Title: {metadata.get('essay_title', '')}")
                self._log(f"JSON: {result['json_out']}")
                self.state.last_result = result
                return

            if name == "prompt-test":
                file_path = str(args["file"])
                max_concurrency = args.get("max_concurrency")
                json_out = args.get("json_out")
                self._log("Starting runtime and running prompt test...")
                result = await self.worker.call(
                    "prompt-test",
                    {
                        "file": file_path,
                        "max_concurrency": max_concurrency,
                        "json_out": json_out,
                    },
                )
                self._log("Prompt test complete.")
                self._log(f"File: {result['file']}")
                self._log(f"Feedback: {result['feedback']}")
                self._log(f"JSON: {result['json_out']}")
                self.state.last_result = result
                return

            raise ValueError(f"Unknown command: {name}")

        async def _refresh_status(self) -> None:
            try:
                status = await self.worker.call("llm-status", {}, retry_once=True, timeout_s=20.0)
            except Exception:
                status = {
                    "selected_llm_key": self.state.status.get("selected_llm_key"),
                    "running": False,
                    "endpoint": None,
                }
            self.state.status = status
            self.query_one("#status", Static).update(_render_status(status))

        def _log(self, line: str) -> None:
            self.query_one(RichLog).write(line)

        def _schedule_completion(self, text: str, cursor: int) -> None:
            token = find_active_at_token(text, cursor)
            if token is None or len(token.query) < 4:
                self._clear_completion()
                return

            self._completion_nonce += 1
            nonce = self._completion_nonce
            if self._completion_task is not None and not self._completion_task.done():
                self._completion_task.cancel()

            async def _run() -> None:
                try:
                    await asyncio.sleep(0.15)
                    items = await asyncio.to_thread(find_matching_files, token.query)
                except asyncio.CancelledError:
                    return

                if nonce != self._completion_nonce:
                    return
                if not items:
                    self._clear_completion()
                    return

                self.state.completion_active = True
                self.state.completion_query = token.query
                self.state.completion_items = items
                self.state.completion_index = 0
                self.state.completion_start = token.start
                self.state.completion_end = token.end
                self.state.completion_source_text = text
                self.state.completion_source_cursor = cursor
                self._render_completion()

            self._completion_task = asyncio.create_task(_run())

        def _clear_completion(self) -> None:
            self.state.completion_active = False
            self.state.completion_query = ""
            self.state.completion_items = []
            self.state.completion_index = 0
            self.state.completion_start = 0
            self.state.completion_end = 0
            self.state.completion_source_text = ""
            self.state.completion_source_cursor = 0
            self._render_completion()

        def _render_completion(self) -> None:
            widget = self.query_one("#completion", Static)
            if not self.state.completion_active or not self.state.completion_items:
                widget.styles.display = "none"
                widget.update("")
                return

            items = self.state.completion_items
            selected = max(0, min(self.state.completion_index, len(items) - 1))
            window = max(1, self.COMPLETION_VIEWPORT_ROWS)

            start = max(0, selected - (window // 2))
            end = min(len(items), start + window)
            start = max(0, end - window)

            lines = []
            if start > 0:
                lines.append("  ...")

            for idx in range(start, end):
                item = items[idx]
                marker = ">" if idx == selected else " "
                lines.append(f"{marker} {item}")

            if end < len(items):
                lines.append("  ...")
            widget.styles.display = "block"
            widget.update("\n".join(lines))


def main() -> int:
    if not TEXTUAL_AVAILABLE:
        print("Error: textual is not installed. Add 'textual' to dependencies and install.")
        return 1
    app = EssayLensTuiApp()
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
