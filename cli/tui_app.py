from __future__ import annotations

import asyncio
from typing import Any

from cli.parser import parse_shell_command
from cli.runner import CliSession
from cli.tui_state import TuiState

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
    ]


if TEXTUAL_AVAILABLE:

    class EssayLensTuiApp(App[None]):
        TITLE = "EssayLens TUI"
        CSS = """
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
        }
        #right {
            width: 1fr;
            border: round $accent;
            padding: 1;
        }
        #cmd {
            dock: bottom;
            margin: 1 0 0 0;
        }
        #status {
            height: 1fr;
        }
        """

        BINDINGS = [
            ("ctrl+l", "clear_log", "Clear Log"),
            ("ctrl+c", "quit", "Quit"),
        ]

        def __init__(self, session: CliSession | None = None) -> None:
            super().__init__()
            self.session = session or CliSession()
            self.state = TuiState()

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
            yield Footer()

        async def on_mount(self) -> None:
            self._log("EssayLens TUI ready. Type /help for commands.")
            self._refresh_status()
            self.query_one(Input).focus()

        async def on_unmount(self) -> None:
            self.session.stop_llm()

        def action_clear_log(self) -> None:
            self.query_one(RichLog).clear()
            self._log("Log cleared.")

        async def on_input_submitted(self, event: Input.Submitted) -> None:
            raw = (event.value or "").strip()
            event.input.value = ""
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
                await self._dispatch(parsed.name, parsed.args)
            except Exception as exc:
                self.state.last_error = str(exc)
                self._log(f"Error: {exc}")
            finally:
                self._refresh_status()

        async def _dispatch(self, name: str, args: dict[str, Any]) -> None:
            if name == "help":
                for line in _help_lines():
                    self._log(line)
                return

            if name == "llm-list":
                rows = await asyncio.to_thread(self.session.list_models)
                for line in _format_model_rows("LLM models", rows["llm"]):
                    self._log(line)
                for line in _format_model_rows("OCR models", rows["ocr"]):
                    self._log(line)
                self.state.last_result = rows
                return

            if name == "llm-start":
                model_key = args.get("model_key")
                result = await asyncio.to_thread(self.session.configure_llm_selection, model_key)
                self._log(result["message"])
                self._log(f"Selected LLM: {result['selected_llm_key']}")
                self.state.last_result = result
                return

            if name == "ocr-start":
                model_key = args.get("model_key")
                result = await asyncio.to_thread(self.session.configure_ocr_selection, model_key)
                self._log(result["message"])
                self._log(f"Selected OCR model: {result['selected_ocr_key']}")
                self.state.last_result = result
                return

            if name == "llm-stop":
                stopped = await asyncio.to_thread(self.session.stop_llm)
                self._log("LLM server stopped." if stopped else "LLM server already stopped.")
                self.state.last_result = {"stopped": stopped}
                return

            if name == "llm-switch":
                model_key = str(args["model_key"])
                result = await asyncio.to_thread(self.session.switch_llm, model_key)
                self._log(result["message"])
                self._log(f"Selected LLM: {result['selected_llm_key']}")
                self.state.last_result = result
                return

            if name == "llm-status":
                status = await asyncio.to_thread(self.session.status)
                for line in _render_status(status).splitlines():
                    self._log(line)
                self.state.last_result = status
                return

            if name == "topic-sentence":
                file_path = str(args["file"])
                max_concurrency = args.get("max_concurrency")
                json_out = args.get("json_out")
                self._log("Running topic sentence analysis...")
                result = await asyncio.to_thread(
                    self.session.run_topic_sentence,
                    file_path,
                    max_concurrency=max_concurrency,
                    json_out=json_out,
                )
                self._log("Topic sentence analysis complete.")
                self._log(f"File: {result['file']}")
                self._log(f"Suggested topic sentence: {result['suggested_topic_sentence']}")
                self._log(f"Feedback: {result['feedback']}")
                self._log(f"JSON: {result['json_out']}")
                self.state.last_result = result
                return

            raise ValueError(f"Unknown command: {name}")

        def _refresh_status(self) -> None:
            status = self.session.status()
            self.state.status = status
            self.query_one("#status", Static).update(_render_status(status))

        def _log(self, line: str) -> None:
            self.query_one(RichLog).write(line)


def main() -> int:
    if not TEXTUAL_AVAILABLE:
        print("Error: textual is not installed. Add 'textual' to dependencies and install.")
        return 1
    app = EssayLensTuiApp()
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

