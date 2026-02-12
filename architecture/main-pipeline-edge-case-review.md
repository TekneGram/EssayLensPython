# Main pipeline edge-case failure review

## Scope
- `main.py` orchestration flow.
- Pipeline stages under `app/pipeline_*.py` that are executed from `main.py`.

## Findings

### 1) Image inputs can poison downstream stages when OCR dependencies are unavailable
**Severity:** High

`PrepPipeline.run_pipeline()` returns early when image inputs exist but OCR process/service dependencies are missing. That early return still includes image triplets in `discovered_inputs`, but no prepared `out_path` DOCX is written for those image files. Downstream stages (for example metadata extraction) assume prepared outputs exist and immediately load from `triplet.out_path`, so a missing output can crash an entire stage run.

- Early return on missing OCR deps: `app/pipeline_prep.py` lines 66-69.
- Downstream load assumption: `app/pipeline_metadata.py` lines 56-59 and 107-109.

**Failure mode:** one image file with unavailable OCR can cause a hard failure before non-image documents finish processing through the rest of the pipeline.

**Recommendation:** either (a) filter image triplets out when OCR is unavailable, or (b) create placeholder outputs and mark them as skipped in per-document results so later stages continue safely.

### 2) Shared intermediate filenames can overwrite data across multiple docs in the same folder
**Severity:** High

Several stages use fixed filenames in `triplet.out_path.parent` (`conc_para.docx`, `ts.docx`, `fb.docx`, `comp_para.docx`) instead of per-document names. If multiple input documents map to the same output directory, later documents overwrite earlier intermediates, and subsequent stages may read mixed or incorrect content.

- `conc_para.docx` write: `app/pipeline_metadata.py` lines 135-139.
- `ts.docx` write: `app/pipeline_fb.py` lines 123-126.
- `fb.docx` write/append and reads: `app/pipeline_fb.py` lines 193-197, `app/pipeline_conclusion.py` lines 101-103, `app/pipeline_summarize_fb.py` lines 142-151.
- `comp_para.docx` write/read: `app/pipeline_content.py` lines 111-116 and 241-249.

**Failure mode:** cross-document contamination and nondeterministic results when processing more than one source file in a shared destination folder.

**Recommendation:** switch intermediates to per-document deterministic names (for example `<stem>.conc_para.docx`) and pass those paths through stage outputs.

### 3) Batch preparation has limited isolation for file-load failures
**Severity:** Medium

Metadata batching builds `text_tasks` with a list comprehension that directly calls `_load_prepared_text()` for each triplet. If any single `document_input_service.load()` call raises (missing/corrupt file), the whole batch raises before results are recorded for surviving documents.

- Batch text preparation: `app/pipeline_metadata.py` lines 56-59.
- Direct load call: `app/pipeline_metadata.py` lines 107-109.

**Failure mode:** one bad prepared file aborts an entire metadata batch instead of producing a per-document error item.

**Recommendation:** wrap per-triplet loads into per-item error capture and only submit valid tasks to the LLM, then merge success/failure per document.

## Notes
- `main.py` currently runs all stages sequentially without top-level stage-level recovery; this is acceptable for fail-fast workflows, but it amplifies the impact of the issues above because one stage exception terminates all remaining stages.
