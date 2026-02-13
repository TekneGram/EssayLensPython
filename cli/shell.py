from __future__ import annotations

import signal
from typing import Callable

from cli.output import print_help, print_llm_status, print_topic_sentence_result
from cli.parser import parse_shell_command
from cli.runner import CliSession


class CliShell:
    def __init__(self, session: CliSession | None = None, input_fn: Callable[[str], str] = input) -> None:
        self.session = session or CliSession()
        self._input = input_fn
        self._running = True

    def run(self) -> int:
        self._install_signal_handlers()
        print("EssayLens CLI shell. Type /help for commands.")
        while self._running:
            try:
                line = self._input("> ")
            except EOFError:
                break
            except KeyboardInterrupt:
                print()
                break

            raw = (line or "").strip()
            if not raw:
                continue

            try:
                cmd = parse_shell_command(raw)
                self._dispatch(cmd.name, cmd.args)
            except Exception as exc:
                print(f"Error: {exc}")

        self.session.stop_llm()
        return 0

    def _dispatch(self, name: str, args: dict[str, str | int | None]) -> None:
        if name == "help":
            print_help()
            return
        if name == "exit":
            self._running = False
            return
        if name == "llm-list":
            self.session.print_model_list()
            return
        if name == "llm-start":
            result = self.session.configure_llm_selection(args.get("model_key") if args else None)
            print(result["message"])
            print(f"Selected LLM: {result['selected_llm_key']}")
            return
        if name == "ocr-start":
            result = self.session.configure_ocr_selection(args.get("model_key") if args else None)
            print(result["message"])
            print(f"Selected OCR model: {result['selected_ocr_key']}")
            return
        if name == "llm-stop":
            stopped = self.session.stop_llm()
            print("LLM server stopped." if stopped else "LLM server already stopped.")
            return
        if name == "llm-switch":
            model_key = str(args["model_key"])
            result = self.session.switch_llm(model_key)
            print(result["message"])
            print(f"Selected LLM: {result['selected_llm_key']}")
            return
        if name == "llm-status":
            print_llm_status(self.session.status())
            return
        if name == "topic-sentence":
            result = self.session.run_topic_sentence(
                str(args["file"]),
                max_concurrency=args.get("max_concurrency") if args else None,
                json_out=args.get("json_out") if args else None,
            )
            print_topic_sentence_result(result)
            return

        raise ValueError(f"Unknown command: {name}")

    def _install_signal_handlers(self) -> None:
        def _handler(signum: int, _frame: object) -> None:
            _ = signum
            self._running = False
            self.session.stop_llm()

        signal.signal(signal.SIGINT, _handler)
        signal.signal(signal.SIGTERM, _handler)
