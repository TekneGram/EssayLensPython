from __future__ import annotations

import argparse
from typing import Sequence

from cli.output import print_llm_status, print_topic_sentence_result
from cli.runner import CliSession
from cli.shell import CliShell


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="essaylens")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("shell")
    sub.add_parser("llm-list")

    llm_start = sub.add_parser("llm-start")
    llm_start.add_argument("--model-key", default=None)

    ocr_start = sub.add_parser("ocr-start")
    ocr_start.add_argument("--model-key", default=None)

    llm_switch = sub.add_parser("llm-switch")
    llm_switch.add_argument("--model-key", required=True)

    sub.add_parser("llm-stop")
    sub.add_parser("llm-status")

    topic = sub.add_parser("topic-sentence")
    topic.add_argument("--file", required=True)
    topic.add_argument("--json-out", default=None)
    topic.add_argument("--max-concurrency", type=int, default=None)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command == "shell":
        return CliShell().run()

    session = CliSession()

    try:
        if args.command == "llm-list":
            session.print_model_list()
            return 0
        if args.command == "llm-start":
            result = session.configure_llm_selection(args.model_key)
            print(result["message"])
            print(f"Selected LLM: {result['selected_llm_key']}")
            return 0
        if args.command == "ocr-start":
            result = session.configure_ocr_selection(args.model_key)
            print(result["message"])
            print(f"Selected OCR model: {result['selected_ocr_key']}")
            return 0
        if args.command == "llm-switch":
            result = session.switch_llm(args.model_key)
            print(result["message"])
            print(f"Selected LLM: {result['selected_llm_key']}")
            return 0
        if args.command == "llm-stop":
            stopped = session.stop_llm()
            print("LLM server stopped." if stopped else "LLM server already stopped.")
            return 0
        if args.command == "llm-status":
            print_llm_status(session.status())
            return 0
        if args.command == "topic-sentence":
            result = session.run_topic_sentence(
                args.file,
                max_concurrency=args.max_concurrency,
                json_out=args.json_out,
            )
            print_topic_sentence_result(result)
            return 0

        parser.error(f"Unknown command: {args.command}")
        return 2
    except Exception as exc:
        print(f"Error: {exc}")
        return 1
    finally:
        if args.command != "shell":
            session.stop_llm()


if __name__ == "__main__":
    raise SystemExit(main())
