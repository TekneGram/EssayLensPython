# PDF Loader Integration Plan

## Objective
With app folder structure and architecure in mind, add a `PdfLoader` module in `inout/` that mirrors the design and coding style of `inout/docx_loader.py`, enabling extraction of text per page from `.pdf` files with the same ergonomics and validation discipline.

## Coding Conventions to Match (`inout/docx_loader.py`)
- Use `from __future__ import annotations`.
- Use a frozen, slotted dataclass (`@dataclass(frozen=True, slots=True)`).
- Keep class responsibilities narrow and explicit.
- Provide both list-returning and iterator APIs.
- Use `Path` for path handling and validate early.
- Keep method docstrings concise and structured.
- Keep helper methods private when internal.
- Use explicit, user-actionable error messages.
- Default behavior should be configurable via dataclass fields.

## Implementation Plan
1. Add new file `inout/pdf_loader.py`.
2. Implement `PdfLoader` dataclass with:
   - `strip_whitespace: bool = True`
   - `keep_empty_pages: bool = True`
3. Implement `load_pages(self, pdf_path: str | Path) -> list[str]`:
   - Validate path using `_validate_pdf_path`.
   - Use `PdfReader` to iterate pages in source order.
   - Extract text via `page.extract_text() or ""`.
   - Apply postprocessing via `_postprocess`.
4. Implement `iter_pages(self, pdf_path: str | Path) -> Iterable[str]`:
   - Same validation and extraction path as `load_pages`.
   - Yield page text one page at a time.
   - Respect `strip_whitespace` and `keep_empty_pages` during iteration.
5. Implement `_postprocess(self, pages: list[str]) -> list[str]`:
   - Conditionally strip and filter empty values, matching `DocxLoader` behavior.
6. Implement `_validate_pdf_path(path: Path) -> None`:
   - Raise `FileNotFoundError` when missing.
   - Raise `ValueError` when not a file.
   - Raise `ValueError` when suffix is not `.pdf` (case-insensitive).
7. Add dependency note for `pypdf` (`pip install pypdf`) in relevant docs or setup flow.
8. Add tests mirroring expected `DocxLoader` style:
   - Valid PDF returns ordered list of page text.
   - Iterator yields same content as list API.
   - Missing file raises `FileNotFoundError`.
   - Non-file path raises `ValueError`.
   - Wrong extension raises `ValueError`.
   - Empty-page handling respects `keep_empty_pages`.

## Non-Drift Rules
- Do not change existing `DocxLoader` API or behavior while introducing `PdfLoader`.
- Keep naming and structure parallel to `DocxLoader` (`load_*`, `iter_*`, `_postprocess`, `_validate_*`).
- Keep exception types and message style consistent with existing loaders.
- Keep defaults semantically equivalent: whitespace trimming on, empty units retained.
- Do not introduce unrelated refactors in `inout/` during this change.
- Do not add new runtime dependencies beyond `pypdf` for baseline extraction.
- If OCR is needed, treat it as a separate extension task, not part of baseline loader parity.

## Acceptance Checklist
- [ ] `inout/pdf_loader.py` exists and follows the same style pattern as `inout/docx_loader.py`.
- [ ] `PdfLoader` uses a frozen, slotted dataclass with clear defaults.
- [ ] `load_pages` returns ordered page text and postprocesses output correctly.
- [ ] `iter_pages` yields page text with parity to `load_pages` options.
- [ ] Path validation enforces existence, file type, and `.pdf` extension.
- [ ] Error messages are clear and aligned with existing loader conventions.
- [ ] `pypdf` dependency is documented for install/use.
- [ ] Tests cover success path, iterator parity, and validation failures.
- [ ] No unrelated files or behaviors are modified.

## Risks and Notes
- PDFs with scanned images may produce empty text with `pypdf`; OCR is out of scope for this baseline integration.
- Some PDFs have irregular internal encoding; extraction quality depends on source document structure.
