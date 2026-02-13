from __future__ import annotations

from dataclasses import dataclass
import shlex


@dataclass(frozen=True)
class ParsedCommand:
    name: str
    args: dict[str, str | int | None]


def parse_shell_command(line: str) -> ParsedCommand:
    raw = (line or "").strip()
    if not raw:
        raise ValueError("Empty command.")
    if not raw.startswith("/"):
        raise ValueError("Shell commands must start with '/'.")

    parts = shlex.split(raw)
    if not parts:
        raise ValueError("Empty command.")

    cmd = parts[0][1:]
    rest = parts[1:]

    if cmd in {"help", "exit", "llm-list", "llm-stop", "llm-status"}:
        if rest:
            raise ValueError(f"/{cmd} does not take arguments.")
        return ParsedCommand(name=cmd, args={})

    if cmd in {"llm-start", "ocr-start"}:
        if len(rest) > 1:
            raise ValueError(f"/{cmd} accepts at most one model key.")
        return ParsedCommand(name=cmd, args={"model_key": rest[0] if rest else None})

    if cmd == "llm-switch":
        if len(rest) != 1:
            raise ValueError("/llm-switch requires exactly one model key.")
        return ParsedCommand(name=cmd, args={"model_key": rest[0]})

    if cmd == "topic-sentence":
        if not rest:
            raise ValueError("/topic-sentence requires a @file argument.")
        file_tokens = [tok for tok in rest if tok.startswith("@")] 
        if len(file_tokens) != 1:
            raise ValueError("/topic-sentence requires exactly one @file argument.")
        if len(rest) != 1:
            raise ValueError("/topic-sentence accepts only one @file argument.")
        raw_path = file_tokens[0][1:]
        if not raw_path:
            raise ValueError("@file argument is empty.")
        return ParsedCommand(name=cmd, args={"file": raw_path, "max_concurrency": None, "json_out": None})

    raise ValueError(f"Unknown command: /{cmd}")
