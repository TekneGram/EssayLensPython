from __future__ import annotations

import re
from dataclasses import dataclass

from docx_tools.incremental_sentence_diff import split_sentences


@dataclass(frozen=True, slots=True)
class HeaderFields:
    student_name: str | None
    student_number: str | None
    essay_title: str | None


_HEADER_PATTERNS = {
    "student_name": re.compile(r"^\s*(student\s*name|name)\s*:\s*(.+)$", re.IGNORECASE),
    "student_number": re.compile(r"^\s*(student\s*(number|id)|id|number)\s*:\s*(.+)$", re.IGNORECASE),
    "essay_title": re.compile(r"^\s*(essay\s*title|title)\s*:\s*(.+)$", re.IGNORECASE),
}


def extract_header_fields(lines: list[str]) -> HeaderFields:
    student_name: str | None = None
    student_number: str | None = None
    essay_title: str | None = None

    for line in lines:
        text = (line or "").strip()
        if not text:
            continue

        name_match = _HEADER_PATTERNS["student_name"].match(text)
        if name_match:
            student_name = name_match.group(2).strip()
            continue

        number_match = _HEADER_PATTERNS["student_number"].match(text)
        if number_match:
            student_number = number_match.group(3).strip()
            continue

        title_match = _HEADER_PATTERNS["essay_title"].match(text)
        if title_match:
            essay_title = title_match.group(2).strip()

    return HeaderFields(
        student_name=student_name,
        student_number=student_number,
        essay_title=essay_title,
    )


def split_header_and_body(paragraphs: list[str]) -> tuple[list[str], list[str]]:
    header_lines: list[str] = []
    body_lines: list[str] = []
    in_header = True

    for paragraph in paragraphs:
        text = (paragraph or "").rstrip()
        if in_header and text:
            matched = any(pattern.match(text) for pattern in _HEADER_PATTERNS.values())
            if matched:
                header_lines.append(text)
                continue

        if in_header and not text:
            if header_lines:
                in_header = False
            continue

        in_header = False
        body_lines.append(text)

    return header_lines, body_lines


def recompose_header_and_body(header_lines: list[str], body_text: str) -> str:
    parts: list[str] = []
    if header_lines:
        parts.extend([(line or "").strip() for line in header_lines if (line or "").strip()])
    body = (body_text or "").strip()
    if body:
        if parts:
            parts.append("")
        parts.append(body)
    return "\n".join(parts)


__all__ = [
    "HeaderFields",
    "extract_header_fields",
    "recompose_header_and_body",
    "split_header_and_body",
    "split_sentences",
]
