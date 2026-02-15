from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def print_help() -> None:
    print("Available commands:")
    print("  /help")
    print("  /exit")
    print("  /llm-list")
    print("  /llm-start [model_key]")
    print("  /llm-stop")
    print("  /llm-switch <model_key>")
    print("  /llm-status")
    print("  /ocr-start [model_key]")
    print("  /topic-sentence @path/to/file.docx")
    print("  /metadata @path/to/file.docx")
    print("  /prompt-test @path/to/file.docx")


def print_llm_status(payload: dict[str, Any]) -> None:
    selected = payload.get("selected_llm_key") or "<none>"
    running = "running" if payload.get("running") else "stopped"
    endpoint = payload.get("endpoint") or "<none>"
    print(f"LLM selected: {selected}")
    print(f"LLM runtime: {running}")
    print(f"LLM endpoint: {endpoint}")


def print_model_rows(title: str, rows: list[dict[str, Any]]) -> None:
    print(title)
    for row in rows:
        markers: list[str] = []
        if row.get("selected"):
            markers.append("selected")
        if row.get("recommended"):
            markers.append("recommended")
        if row.get("installed"):
            markers.append("installed")
        marker_str = f" ({', '.join(markers)})" if markers else ""
        print(f"  - {row['key']}: {row['display_name']}{marker_str}")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def print_topic_sentence_result(result: dict[str, Any]) -> None:
    print("Topic sentence analysis complete")
    print(f"File: {result['file']}")
    print(f"Suggested topic sentence: {result['suggested_topic_sentence']}")
    print(f"Feedback: {result['feedback']}")
    print(f"JSON: {result['json_out']}")


def print_metadata_result(result: dict[str, Any]) -> None:
    metadata = result.get("metadata", {})
    print("Metadata extraction complete")
    print(f"File: {result['file']}")
    print(f"Student Name: {metadata.get('student_name', '')}")
    print(f"Student Number: {metadata.get('student_number', '')}")
    print(f"Essay Title: {metadata.get('essay_title', '')}")
    print(f"JSON: {result['json_out']}")


def print_prompt_test_result(result: dict[str, Any]) -> None:
    print("Prompt test complete")
    print(f"File: {result['file']}")
    print(f"Feedback: {result['feedback']}")
    print(f"JSON: {result['json_out']}")
