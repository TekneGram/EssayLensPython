# OCR Model Download Plan

## Inferred Repository File Structure (Current + Planned OCR Additions)
```text
EssayLensPython/
├── .gitignore
├── AGENTS.md
├── Agent.md
├── agent_docx.md
├── agent_ocr.md
├── agent_ocr_download.md
├── agent_pdf.md
├── agent_rehearsal.md
├── agent_rehearsal_2.md
├── main.py
├── requirements.txt
├── app/
│   ├── bootstrap_llm.py
│   ├── container.py
│   ├── pipeline.py
│   ├── select_model.py
│   └── settings.py
├── architecture/
│   ├── 02-container-flowchart.md
│   ├── 03-components-flowchart.md
│   └── 04-code-flowchart.md
├── config/
│   ├── assessment_paths_config.py
│   ├── ged_config.py
│   ├── llm_config.py
│   ├── llm_model_spec.py
│   ├── llm_request_config.py
│   ├── llm_server_config.py
│   ├── run_config.py
│   ├── ocr_config.py                     # planned/created by OCR plan
│   ├── ocr_model_spec.py                 # planned/created by OCR plan
│   └── ocr_request_config.py             # planned/created by OCR plan
├── docx_tools/
│   ├── header_extractor.py
│   ├── sentence_splitter.py
│   └── track_changes_editor.py
├── gitpractice/
│   ├── goodbye.py
│   └── helloworld.py
├── inout/
│   ├── docx_loader.py
│   └── explainability_writer.py
├── interfaces/
│   └── config/
│       ├── __init__.py
│       └── app_config.py
├── nlp/
│   ├── ged/
│   │   ├── ged_bert.py
│   │   └── ged_types.py
│   ├── llm/
│   │   ├── llm_client.py
│   │   ├── llm_server_process.py
│   │   ├── llm_types.py
│   │   └── tasks/
│   │       ├── test_parallel.py
│   │       ├── test_parallel_2.py
│   │       └── test_sequential.py
│   └── ocr/
│       ├── ocr_client.py                 # planned/created by OCR plan
│       └── ocr_server_process.py         # planned/created by OCR plan
├── services/
│   ├── docx_output_service.py
│   ├── explainability.py
│   ├── ged_service.py
│   ├── llm_service.py
│   └── ocr_service.py                    # planned/created by OCR plan
├── tests/
│   ├── test_app_config_interface.py
│   ├── test_assessment_paths_config.py
│   ├── test_bootstrap_llm.py
│   ├── test_docx_loader_runtime.py
│   ├── test_docx_output_service_runtime.py
│   ├── test_explainability_runtime.py
│   ├── test_ged_bert_runtime.py
│   ├── test_ged_config.py
│   ├── test_ged_types_runtime.py
│   ├── test_llm_client_json_schema.py
│   ├── test_llm_client_response.py
│   ├── test_llm_client_streaming.py
│   ├── test_llm_config.py
│   ├── test_llm_model_spec.py
│   ├── test_llm_server_process.py
│   ├── test_llm_server_requests_config.py
│   ├── test_llm_service_response.py
│   ├── test_run_config.py
│   ├── test_select_model.py
│   └── test_track_changes_editor_runtime.py
└── utils/
    └── terminal_ui.py
```

## Goal
Add a new OCR download/config selection flow that mirrors `app/select_model.py` conventions, but is OCR-specific and does not perform hardware-fit checks.

## Scope
Implement a new selector/downloader script for OCR artifacts that:
1. Uses default OCR model spec(s) from `config/ocr_model_spec.py` (no interactive user selection).
2. Downloads both required OCR files:
   - main GGUF
   - mmproj GGUF
3. Stores both files in the same model storage location used by `app/select_model.py` (`.appdata/models`).
4. Updates `ocr_config` on `app_cfg` and returns updated `AppConfig`, following the same immutable/validated replace pattern used by `select_model_and_update_config`.

No hardware requirement checks are included in this OCR selection flow.

## New File To Add
- `app/select_ocr_model.py`

## Required Existing Inputs (Imports)
- `app.settings.AppConfig`
- `config.ocr_model_spec.OCR_MODEL_SPECS` and `OcrModelSpec`
- `dataclasses.replace`
- `pathlib.Path`
- `json`

Downloader behavior is required in this step, so reuse the same HuggingFace download utility style already used by the app bootstrap path (do not create unrelated download patterns).

## Conventions To Mirror From `app/select_model.py`
- Use pure helper functions with narrow responsibilities.
- Use `Path(".appdata").resolve()` as base dir.
- Reuse model directory convention via helper (`base_dir / "models"`).
- Add persisted selection key file in `.appdata/config/` for OCR key persistence.
- Keep CLI messaging style consistent, but do not prompt for OCR model choice.
- Build new config objects with `replace(...)`.
- Validate updated config objects before returning.
- Return updated `app_cfg` via immutable `replace(app_cfg, ...)`.

## OCR Download/Selection Behavior
1. Determine `base_dir = Path(".appdata").resolve()`.
2. Ensure models dir exists (`.appdata/models`).
3. Load `OCR_MODEL_SPECS`.
4. Skip hardware filtering entirely.
5. Select default OCR spec deterministically (for example first/primary entry in `OCR_MODEL_SPECS`) with no user prompt.
6. Print/log an informational message that OCR download will begin if the models do not exist in `.app/models`.
7. Persist selected/default OCR key in `.appdata/config/ocr_model.json`.
8. Resolve target paths:
   - `ocr_gguf_path = models_dir / chosen_spec.hf_filename`
   - `ocr_mmproj_path = models_dir / chosen_spec.mmproj_filename`
9. If either file is missing, download missing file(s) to `.appdata/models`; if already present, skip download.
10. Build `new_ocr_config = replace(app_cfg.ocr_config, ...)` with selected metadata and resolved local paths.
11. Validate `new_ocr_config` (allow unresolved paths only before download; require resolved after successful download).
12. Return `replace(app_cfg, ocr_config=new_ocr_config)`.

## Suggested Helper Functions In `app/select_ocr_model.py`
- `_ocr_persist_path(base_dir: Path) -> Path`
- `get_models_dir(base_dir: Path) -> Path` (same convention as LLM selector)
- `is_ocr_model_downloaded(spec: OcrModelSpec, models_dir: Path) -> bool`
- `load_persisted_ocr_key(base_dir: Path) -> str | None`
- `persist_ocr_key(base_dir: Path, key: str) -> None`
- `resolve_default_ocr_spec(specs: list[OcrModelSpec], persisted_key: str | None) -> OcrModelSpec`
- `select_ocr_model_and_update_config(app_cfg: AppConfig) -> AppConfig`

## AppConfig / Settings Integration Plan
1. Add `ocr_config` to `AppConfig` dataclass in `app/settings.py`.
2. Build default `ocr_config` in `build_settings()` using `OcrConfig.from_strings(...)`.
3. Validate OCR config in settings flow.
4. Keep LLM config untouched and separate.

## Interface Integration Plan
1. Update `interfaces/config/app_config.py` to reflect the new `ocr_config` field on the application config interface shape.
2. Keep interface typing aligned with `AppConfig` in `app/settings.py`.
3. Ensure interface updates do not introduce LLM/OCR cross-coupling.

## Container Integration Plan
- Extend `app/container.py` wiring to accept/use `app_cfg.ocr_config` independently of LLM config.
- Do not couple OCR model identity with `llm_config`.

## Non-Drift Rules
1. Do not modify `app/select_model.py`; implement OCR flow in a new file.
2. Do not add hardware-fit checks to OCR selector.
3. Use the same `.appdata/models` storage path convention as LLM selector.
4. Do not prompt users to choose OCR model; use deterministic default selection.
5. Keep LLM selection/downloading behavior unchanged.
6. Preserve immutable config update style (`replace(...)` + validation + return new `AppConfig`).
7. Only create/edit files explicitly indicated by this plan and its OCR prerequisite plans.
8. If any additional file must be edited beyond the indicated files, stop and ask for explicit user permission first.

## Acceptance Checklist
- [ ] `app/select_ocr_model.py` exists and mirrors `app/select_model.py` structure/conventions.
- [ ] OCR selector downloads both required files (GGUF + mmproj).
- [ ] Files are stored under `.appdata/models`.
- [ ] If OCR files already exist, download is skipped and config is updated from local files.
- [ ] Selected OCR key is persisted under `.appdata/config/ocr_model.json`.
- [ ] `ocr_config` is updated and validated, then returned in new `AppConfig`.
- [ ] `interfaces/config/app_config.py` is updated to include OCR config interface shape changes.
- [ ] No hardware requirement checks are performed in OCR selector.
- [ ] No user model-selection prompt is used in OCR flow.
- [ ] Existing LLM model selector and LLM config flow remain unchanged.
