from __future__ import annotations

from typing import Any, Dict, List, Tuple

from docx_tools.sentence_splitter import split_paragraphs


_HEADER_KEYS = ["student_name", "student_number", "essay_title"]


def split_header_and_body(
    raw_paragraphs: List[str],
    classified: Any,
) -> Tuple[Dict[str, str], List[str]]:
    """
    Use classified metadata to find header sentences within the first 4 and last 3
    sentences. If a match is found (substring match), remove that entire sentence.
    """
    sentences = split_paragraphs(raw_paragraphs)

    candidates: Dict[str, str] = {}
    if isinstance(classified, dict):
        for key in _HEADER_KEYS:
            value = classified.get(key)
            if isinstance(value, str) and value.strip():
                candidates[key] = value.strip()

    n = len(sentences)
    first_idxs = list(range(min(4, n)))
    last_start = max(0, n - 3)
    last_idxs = list(range(last_start, n))
    search_idxs = first_idxs + [i for i in last_idxs if i not in first_idxs]

    matched: Dict[str, str] = {}
    remove_idxs = set()

    for idx in search_idxs:
        sentence = (sentences[idx] or "").strip()
        if not sentence:
            continue
        sentence_lower = sentence.lower()
        for key in _HEADER_KEYS:
            if key in matched:
                continue
            target = candidates.get(key)
            if not target:
                continue
            if target.lower() in sentence_lower:
                matched[key] = target
                remove_idxs.add(idx)

    header = {
        "student_name": matched.get("student_name", ""),
        "student_number": matched.get("student_number", ""),
        "essay_title": matched.get("essay_title", ""),
    }

    body = [s for i, s in enumerate(sentences) if i not in remove_idxs]
    return header, body


def build_edited_text(
    raw_paragraphs: List[str],
    classified: Any,
) -> Tuple[str, Dict[str, str], List[str]]:
    header, body = split_header_and_body(raw_paragraphs, classified)
    edited_text = build_text_from_header_and_body(header, body)
    return edited_text, header, body


def build_text_from_header_and_body(header: Dict[str, str], body_sentences: List[str]) -> str:
    header_lines: List[str] = []
    header_lines.append(f"Name: {header.get('student_name', '')}")
    header_lines.append(f"Number: {header.get('student_number', '')}")
    header_lines.append(f"Title: {header.get('essay_title', '')}")
    body_text = " ".join(s.strip() for s in body_sentences if s and s.strip())
    parts = header_lines + [body_text]
    return "\n\n".join(parts)


def build_paragraphs_from_header_and_body(
    header: Dict[str, str],
    body_sentences: List[str],
) -> List[str]:
    header_lines: List[str] = []
    header_lines.append(f"Name: {header.get('student_name', '')}")
    header_lines.append(f"Number: {header.get('student_number', '')}")
    header_lines.append(f"Title: {header.get('essay_title', '')}")
    body_text = " ".join(s.strip() for s in body_sentences if s and s.strip())
    return header_lines + [body_text]
