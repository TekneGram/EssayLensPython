from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from app.settings import AppConfig
from app.select_model import (
    get_hardware_info,
    get_models_dir,
    is_model_downloaded,
    load_persisted_model_key,
    persist_model_key,
    recommend_model,
)
from app.select_ocr_model import (
    is_ocr_model_downloaded,
    load_persisted_ocr_key,
    persist_ocr_key,
)
from config.llm_model_spec import LlmModelSpec, MODEL_SPECS
from config.ocr_model_spec import OcrModelSpec, OCR_MODEL_SPECS


@dataclass(frozen=True)
class ModelStatus:
    key: str
    display_name: str
    installed: bool
    recommended: bool
    selected: bool


@dataclass(frozen=True)
class OcrModelStatus:
    key: str
    display_name: str
    installed: bool
    selected: bool


def _base_dir() -> Path:
    return Path(".appdata").resolve()


def _fits_model(spec: LlmModelSpec, total_ram_gb: float, cuda_vram_gb: float | None) -> bool:
    if total_ram_gb < spec.min_ram_gb:
        return False
    if cuda_vram_gb is None:
        return True
    return cuda_vram_gb >= spec.min_vram_gb


def llm_statuses() -> list[ModelStatus]:
    base_dir = _base_dir()
    models_dir = get_models_dir(base_dir)
    models_dir.mkdir(parents=True, exist_ok=True)
    hw = get_hardware_info()
    persisted = load_persisted_model_key(base_dir)

    eligible_specs = [
        spec
        for spec in MODEL_SPECS
        if _fits_model(spec, hw.total_ram_gb, hw.cuda_vram_gb)
    ]
    candidate_specs = eligible_specs if eligible_specs else MODEL_SPECS
    recommended = recommend_model(candidate_specs, hw)

    statuses: list[ModelStatus] = []
    for spec in MODEL_SPECS:
        statuses.append(
            ModelStatus(
                key=spec.key,
                display_name=spec.display_name,
                installed=is_model_downloaded(spec, models_dir),
                recommended=spec.key == recommended.key,
                selected=spec.key == persisted,
            )
        )
    return statuses


def ocr_statuses() -> list[OcrModelStatus]:
    base_dir = _base_dir()
    models_dir = get_models_dir(base_dir)
    models_dir.mkdir(parents=True, exist_ok=True)
    persisted = load_persisted_ocr_key(base_dir)

    statuses: list[OcrModelStatus] = []
    for spec in OCR_MODEL_SPECS:
        statuses.append(
            OcrModelStatus(
                key=spec.key,
                display_name=spec.display_name,
                installed=is_ocr_model_downloaded(spec, models_dir),
                selected=spec.key == persisted,
            )
        )
    return statuses


def _resolve_llm_spec(model_key: str | None) -> LlmModelSpec:
    base_dir = _base_dir()
    persisted = load_persisted_model_key(base_dir)
    hw = get_hardware_info()

    eligible_specs = [
        spec
        for spec in MODEL_SPECS
        if _fits_model(spec, hw.total_ram_gb, hw.cuda_vram_gb)
    ]
    candidate_specs = eligible_specs if eligible_specs else MODEL_SPECS

    if model_key:
        selected = next((spec for spec in MODEL_SPECS if spec.key == model_key), None)
        if selected is None:
            raise ValueError(f"Unknown LLM model key: {model_key}")
        return selected

    if persisted:
        persisted_spec = next((spec for spec in MODEL_SPECS if spec.key == persisted), None)
        if persisted_spec is not None:
            return persisted_spec

    return recommend_model(candidate_specs, hw)


def _resolve_ocr_spec(model_key: str | None) -> OcrModelSpec:
    base_dir = _base_dir()
    persisted = load_persisted_ocr_key(base_dir)

    if model_key:
        selected = next((spec for spec in OCR_MODEL_SPECS if spec.key == model_key), None)
        if selected is None:
            raise ValueError(f"Unknown OCR model key: {model_key}")
        return selected

    if persisted:
        persisted_spec = next((spec for spec in OCR_MODEL_SPECS if spec.key == persisted), None)
        if persisted_spec is not None:
            return persisted_spec

    if not OCR_MODEL_SPECS:
        raise RuntimeError("OCR model specs are empty.")
    return OCR_MODEL_SPECS[0]


def select_llm_and_update_config(app_cfg: AppConfig, model_key: str | None = None) -> AppConfig:
    base_dir = _base_dir()
    models_dir = get_models_dir(base_dir)
    models_dir.mkdir(parents=True, exist_ok=True)

    chosen = _resolve_llm_spec(model_key)
    persist_model_key(base_dir, chosen.key)

    gguf_path = models_dir / chosen.hf_filename
    mmproj_path = models_dir / chosen.mmproj_filename if chosen.mmproj_filename else None
    downloaded = is_model_downloaded(chosen, models_dir)

    new_llm_config = replace(
        app_cfg.llm_config,
        llama_server_model=chosen.key,
        llama_model_key=chosen.key,
        llama_model_display_name=chosen.display_name,
        llama_model_alias=chosen.display_name,
        llama_model_family=chosen.model_family,
        hf_repo_id=chosen.hf_repo_id,
        hf_filename=chosen.hf_filename,
        hf_mmproj_filename=chosen.mmproj_filename,
        llama_gguf_path=gguf_path if downloaded else None,
        llama_mmproj_path=mmproj_path if mmproj_path is not None and mmproj_path.exists() else None,
    )
    new_llm_config.validate(allow_unresolved_model_paths=True)
    return replace(app_cfg, llm_config=new_llm_config)


def select_ocr_and_update_config(app_cfg: AppConfig, model_key: str | None = None) -> AppConfig:
    base_dir = _base_dir()
    models_dir = get_models_dir(base_dir)
    models_dir.mkdir(parents=True, exist_ok=True)

    chosen = _resolve_ocr_spec(model_key)
    persist_ocr_key(base_dir, chosen.key)

    ocr_gguf_path = models_dir / chosen.hf_filename
    ocr_mmproj_path = models_dir / chosen.mmproj_filename
    downloaded = is_ocr_model_downloaded(chosen, models_dir)

    new_ocr_config = replace(
        app_cfg.ocr_config,
        hf_repo_id=chosen.hf_repo_id,
        hf_filename=chosen.hf_filename,
        hf_mmproj_filename=chosen.mmproj_filename,
        ocr_server_model=chosen.backend,
        ocr_model_key=chosen.key,
        ocr_model_display_name=chosen.display_name,
        ocr_model_alias=chosen.display_name,
        ocr_model_family=chosen.model_family,
        ocr_gguf_path=ocr_gguf_path if downloaded else None,
        ocr_mmproj_path=ocr_mmproj_path if downloaded else None,
    )
    new_ocr_config.validate(allow_unresolved_model_paths=True)
    return replace(app_cfg, ocr_config=new_ocr_config)


def get_selected_llm_key() -> str | None:
    return load_persisted_model_key(_base_dir())


def get_selected_ocr_key() -> str | None:
    return load_persisted_ocr_key(_base_dir())
