# Incremental DOCX Report Builder Plan

## Goal
Build a new incremental DOCX pipeline that preserves tracked-change reporting behavior from `docx_tools/track_changes_editor.py`, while allowing each report section to be appended at different times.

## Required Behavior (Incremental Flow)
1. `original_paragraphs`
- Create a new output `.docx` and append original text content.
- Source text may come from `inout/docx_loader.py`, `inout/pdf_loader.py`, or OCR output.

2. `header_lines` and `edited_text`
- Append header lines and edited text section later in time (separate call).

3. `corrected_text`
- Append corrected section later in time (separate call).
- Render tracked changes between edited and corrected content so Word shows insertions/deletions.

4. `feedback_paragraphs`
- Append feedback after LLM feedback completes (separate call).
- Support skipping feedback or writing feedback to a separate output document.

5. `feedback_summary`
- For each document, collect all currently appended feedback blocks.
- Run collected feedback through an LLM summarization step.
- Support two modes:
  - Option A: append `FEEDBACK SUMMARY` while keeping original feedback.
  - Option B: remove existing feedback blocks and replace them with `FEEDBACK SUMMARY`.

## Design Constraints
- Do not overwrite existing files.
- Create only new files in existing folders (`docx_tools`, `services`).
- Do not reuse helper functions directly from existing utility files.
- Any unused behavior from old files does not need to be recreated.

## New Files To Create
- `docx_tools/incremental_track_changes_editor.py`
- `docx_tools/incremental_header_body_parser.py`
- `docx_tools/incremental_sentence_diff.py`
- `services/incremental_docx_output_service.py`
- `services/incremental_docx_state_store.py`

## Proposed Responsibilities

### `docx_tools/incremental_track_changes_editor.py`
- New class: `IncrementalTrackChangesEditor`
- Functions:
  - `create_or_load_document(output_path)`
  - `enable_track_revisions(doc)`
  - `append_original_section(doc, original_paragraphs)`
  - `append_header_and_edited_section(doc, header_lines, edited_text, include_page_break=True)`
  - `append_corrected_diff_section(doc, edited_text, corrected_text)`
  - `append_feedback_section(doc, feedback_paragraphs, heading="Language Feedback")`
  - `append_feedback_summary_section(doc, feedback_summary, heading="Feedback Summary")`
  - `remove_feedback_sections(doc)` (marker-based removal only)
  - `save(doc, output_path)`
- Tracks revision IDs per append operation and writes `<w:ins>` / `<w:del>` runs for corrected diff.
- Must write explicit feedback boundary markers when appending feedback blocks to support non-brittle future edits.

### `docx_tools/incremental_header_body_parser.py`
- New standalone parsing utilities (not imported from old utility modules):
  - sentence splitting
  - header extraction (`student_name`, `student_number`, `essay_title`)
  - header/body recomposition
- Recreates only needed behavior for this incremental flow.

### `docx_tools/incremental_sentence_diff.py`
- New diff-specific helpers:
  - sentence alignment
  - word-level replacement handling
  - stable whitespace handling for Word XML run output
- Keeps tracked-change logic isolated and testable.

### `services/incremental_docx_state_store.py`
- New disk-backed per-document state manager.
- One sidecar JSON per output report file:
  - Example: `<output_path>.state.json`
- State is loaded/updated/saved for one doc at a time; no global in-memory registry.

## Explicit State Management Plan
- Persistence medium: filesystem JSON sidecar.
- Scope: one sidecar per output `.docx`.
- Memory model: constant-memory per operation (load one doc state, update, save, release).
- Storage model: minimal metadata only, not full text payloads.

### Minimal State Schema (example)
- `version`: integer schema version.
- `sections_written`: list of completed steps (`original`, `header_edited`, `corrected`, `feedback`).
- `feedback_append_count`: integer count of feedback append operations applied to this report.
- `feedback_entries`: optional compact list of feedback append metadata (e.g., `id`, `timestamp`, `target_path`) without storing full feedback text.
- `feedback_summary_present`: boolean indicating whether summary exists in target doc.
- `feedback_summary_hash`: SHA-256 hash of current summary text.
- `feedback_summary_source_count`: number of feedback blocks used to generate latest summary.
- `feedback_summary_updated_at`: ISO timestamp for latest summary generation.
- `edited_text_hash`: SHA-256 of canonical edited text used for corrected diff validation.
- `created_at`: ISO timestamp.
- `updated_at`: ISO timestamp.

### State Rules
- Never store full `original_paragraphs`, full `edited_text`, full `corrected_text`, or full feedback by default.
- Use hashes/flags for integrity checks.
- Only current document state is loaded in memory during each call.
- If sidecar missing, infer “new report” state.
- If sidecar corrupt/unreadable, fail fast with actionable error.
- Optional cleanup policy: remove sidecar after final step, or keep via config.
- Feedback append operations must record stable boundary metadata to allow deterministic remove/replace behavior later.

### Why It Fits Low-Memory / LLM Workloads
- No centralized multi-document state object.
- No accumulation of 100-doc state in memory.
- Per-doc JSON files are tiny and disk-resident.
- KV cache pressure is unaffected unless state files are explicitly injected into prompts.

## Section Dependency and Append Rules
- `original`, `header+edited`, and `feedback` are optional and independently appendable.
- `corrected` has one required dependency: edited baseline must exist.
- Corrected append is allowed only when:
  - `edited_text` is available from prior step or explicit input, and
  - `edited_text_hash` matches expected baseline.
- `feedback` is repeatable: multiple `append_feedback(...)` calls are allowed on the same report at different times.
- Each feedback append must add a new feedback block and increment `feedback_append_count`.
- `feedback` should not be treated as a one-time terminal step.
- `feedback_summary` depends on at least one existing feedback block.
- `feedback_summary` supports two explicit modes:
  - `append_summary`: keep feedback blocks and append a summary section.
  - `replace_with_summary`: remove marked feedback blocks, then append summary.
- Feedback removal/replacement must only use explicit section boundary markers; unmarked free-form deletion is disallowed.
- No hard requirement to include `original`.
- No hard requirement to include `feedback` in the same document.
- Service should support `feedback_target_path` to allow separate feedback document output.

## Track Changes Behavior Guarantee
- Track changes are applied by:
  - enabling `w:trackRevisions` on the target document settings, and
  - emitting `<w:del>` and `<w:ins>` runs from sentence/word diff between edited and corrected text.
- This preserves the same core XML-based mechanism already used in `track_changes_editor.py`, but in incremental append steps.

## Feedback Boundary Marker Requirement
- Every appended feedback block must be wrapped with deterministic start/end markers (XML bookmarks or equivalent structured markers).
- Marker IDs must be unique per feedback block and recorded in sidecar metadata.
- `replace_with_summary` must locate and remove feedback strictly by these markers.
- If required markers are missing/corrupt, the service must fail fast and refuse brittle paragraph-guess deletion.

## Non-Drift Rules
- Keep existing files untouched:
  - `docx_tools/track_changes_editor.py`
  - `docx_tools/header_extractor.py`
  - `docx_tools/sentence_splitter.py`
  - `services/docx_output_service.py`
- New implementation must not import utility functions from old helper files.
- Preserve user-visible section headings and tracked-change semantics.
- Keep all new code in `docx_tools/` and `services/` only.
- Keep API names explicit to incremental purpose (`start_`, `append_`).
- State store must remain disk-backed, per-doc, and metadata-only by default.
- Summary replacement logic must rely on explicit feedback boundary markers, not heuristic text matching.

## Acceptance Checklist
- [ ] New incremental editor class exists and is isolated from old editor.
- [ ] New parser/diff helpers exist in new files, not imported from old utility modules.
- [ ] New service supports independent phase calls over time.
- [ ] Existing output can be loaded and appended, not rebuilt from scratch each time.
- [ ] Corrected section appends only when edited baseline exists.
- [ ] Corrected section shows tracked changes against edited baseline.
- [ ] Feedback can be appended to same document or redirected to a separate document.
- [ ] Feedback summary can be generated from all current feedback blocks.
- [ ] Both summary modes are supported: append-only and replace-with-summary.
- [ ] Replace-with-summary operates only via explicit feedback boundary markers.
- [ ] State persistence is per-doc sidecar JSON and metadata-only by default.
- [ ] No global in-memory multi-doc state store is introduced.
- [ ] Existing legacy files remain unchanged.

## Migration Plan (No Overwrite)
- Keep legacy pipeline active.
- Introduce new service behind a feature flag/config switch.
- Validate with sample DOCX, PDF-derived text, and OCR-derived text.
- After validation, switch callers to incremental service and retire legacy files later.
