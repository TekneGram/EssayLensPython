from __future__ import annotations

import re
from typing import Iterable, List

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


def split_sentences(text: str) -> List[str]:
    s = (text or "").strip()
    if not s:
        return []
    parts = _SENT_SPLIT.split(s)
    return [p.strip() for p in parts if p and p.strip()]


def split_paragraphs(paragraphs: Iterable[str]) -> List[str]:
    sentences: List[str] = []
    for p in paragraphs:
        sentences.extend(split_sentences(p))
    return sentences
