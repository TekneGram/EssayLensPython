from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from typing import Sequence

_SENTENCE_ENDINGS = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True, slots=True)
class WordDiffOp:
    tag: str
    original_text: str
    edited_text: str


def split_sentences(text: str) -> list[str]:
    normalized = (text or "").strip()
    if not normalized:
        return []
    return [segment.strip() for segment in _SENTENCE_ENDINGS.split(normalized) if segment.strip()]


def _tokens_with_trailing_space(text: str) -> list[str]:
    return re.findall(r"\S+\s*", text or "")


def _join_tokens(tokens: Sequence[str]) -> str:
    return "".join(tokens)


def diff_words(original: str, edited: str) -> list[WordDiffOp]:
    original_tokens = _tokens_with_trailing_space(original)
    edited_tokens = _tokens_with_trailing_space(edited)

    matcher = difflib.SequenceMatcher(None, original_tokens, edited_tokens)
    ops: list[WordDiffOp] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        ops.append(
            WordDiffOp(
                tag=tag,
                original_text=_join_tokens(original_tokens[i1:i2]),
                edited_text=_join_tokens(edited_tokens[j1:j2]),
            )
        )
    return ops


def align_sentences(original_text: str, edited_text: str) -> list[tuple[str, str | None, str | None]]:
    original_sentences = split_sentences(original_text)
    edited_sentences = split_sentences(edited_text)

    matcher = difflib.SequenceMatcher(None, original_sentences, edited_sentences)
    aligned: list[tuple[str, str | None, str | None]] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for idx in range(i2 - i1):
                sentence = original_sentences[i1 + idx]
                aligned.append(("equal", sentence, sentence))
            continue

        if tag == "delete":
            for sentence in original_sentences[i1:i2]:
                aligned.append(("delete", sentence, None))
            continue

        if tag == "insert":
            for sentence in edited_sentences[j1:j2]:
                aligned.append(("insert", None, sentence))
            continue

        pair_count = min(i2 - i1, j2 - j1)
        for idx in range(pair_count):
            aligned.append(("replace", original_sentences[i1 + idx], edited_sentences[j1 + idx]))

        for sentence in original_sentences[i1 + pair_count:i2]:
            aligned.append(("delete", sentence, None))

        for sentence in edited_sentences[j1 + pair_count:j2]:
            aligned.append(("insert", None, sentence))

    return aligned
