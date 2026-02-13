from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


DEFAULT_IGNORE_DIRS = {".git", "venv", ".venv", "__pycache__", "third_party", ".appdata"}


@dataclass(frozen=True)
class ActiveAtToken:
    start: int
    end: int
    query: str


def find_active_at_token(text: str, cursor_pos: int) -> ActiveAtToken | None:
    value = text or ""
    if not value:
        return None

    cursor = max(0, min(cursor_pos, len(value)))
    if cursor == 0:
        return None

    start = cursor - 1
    while start >= 0 and not value[start].isspace():
        start -= 1
    start += 1

    end = cursor
    while end < len(value) and not value[end].isspace():
        end += 1

    token = value[start:end]
    if not token.startswith("@"):
        return None

    raw = value[start:cursor][1:]
    if raw.startswith('"'):
        raw = raw[1:]
    if raw.endswith('"'):
        raw = raw[:-1]

    return ActiveAtToken(start=start, end=end, query=raw)


def replace_active_at_token(text: str, token: ActiveAtToken, selected_path: str) -> str:
    needs_quotes = " " in selected_path
    replacement = f'@"{selected_path}"' if needs_quotes else f"@{selected_path}"
    return f"{text[:token.start]}{replacement}{text[token.end:]}"


def find_matching_files(
    query: str,
    *,
    root: Path | None = None,
    min_chars: int = 4,
    max_results: int = 20,
    ignore_dirs: set[str] | None = None,
) -> list[str]:
    search_query = (query or "").strip().lower()
    if len(search_query) < min_chars:
        return []

    base = (root or Path.cwd()).resolve()
    ignored = set(ignore_dirs or DEFAULT_IGNORE_DIRS)
    ranked: list[tuple[int, str]] = []

    for dirpath, dirnames, filenames in os.walk(base, topdown=True):
        dirnames[:] = [d for d in dirnames if d not in ignored and not d.startswith(".")]
        current_dir = Path(dirpath)
        for filename in filenames:
            rel = str((current_dir / filename).relative_to(base))
            abs_path = str((current_dir / filename).resolve())
            filename_lower = filename.lower()
            rel_lower = rel.lower()
            abs_lower = abs_path.lower()

            if filename_lower.startswith(search_query):
                score = 0
            elif search_query in filename_lower:
                score = 1
            elif search_query in rel_lower or search_query in abs_lower:
                score = 2
            else:
                continue
            ranked.append((score, abs_path))

    ranked.sort(key=lambda item: (item[0], item[1]))
    return [path for _, path in ranked[:max_results]]
