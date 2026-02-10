from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import json

from app.settings import AppConfig
from config.ocr_model_spec import OCR_MODEL_SPECS, OcrModelSpec

try:
    from huggingface_hub import hf_hub_download  # type: ignore
except ImportError:
    hf_hub_download = None


def _ocr_persist_path(base_dir: Path) -> Path:
    return base_dir / "config" / "ocr_model.json"


def get_models_dir(base_dir: Path) -> Path:
    return base_dir / "models"


def is_ocr_model_downloaded(spec: OcrModelSpec, models_dir: Path) -> bool:
    ocr_gguf_path = models_dir / spec.hf_filename
    ocr_mmproj_path = models_dir / spec.mmproj_filename
    return ocr_gguf_path.exists() and ocr_mmproj_path.exists()


def load_persisted_ocr_key(base_dir: Path) -> str | None:
    persist_path = _ocr_persist_path(base_dir)
    if not persist_path.exists():
        return None
    try:
        payload = json.loads(persist_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    model_key = payload.get("model_key")
    if not isinstance(model_key, str) or not model_key.strip():
        return None
    return model_key


def persist_ocr_key(base_dir: Path, key: str) -> None:
    persist_path = _ocr_persist_path(base_dir)
    persist_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"model_key": key}
    persist_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def resolve_default_ocr_spec(specs: list[OcrModelSpec], persisted_key: str | None) -> OcrModelSpec:
    if not specs:
        raise RuntimeError("OCR_MODEL_SPECS is empty. Add at least one OCR model spec.")

    if persisted_key is not None:
        persisted_spec = next((s for s in specs if s.key == persisted_key), None)
        if persisted_spec is not None:
            return persisted_spec

    return specs[0]


def _ensure_hf_download(repo_id: str, filename: str, revision: str | None, models_dir: Path) -> Path:
    if hf_hub_download is None:
        raise RuntimeError(
            "huggingface_hub is not installed. Install dependencies before bootstrapping models."
        )
    try:
        downloaded = hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            revision=revision,
            local_dir=str(models_dir),
            local_dir_use_symlinks=False,
        )
    except Exception as exc:
        raise RuntimeError(f"Failed to download OCR artifact from Hugging Face: {exc}") from exc

    resolved = Path(downloaded).expanduser().resolve()
    if not resolved.exists() or not resolved.is_file():
        raise RuntimeError(f"Downloaded OCR artifact is invalid: {resolved}")
    return resolved


def select_ocr_model_and_update_config(app_cfg: AppConfig) -> AppConfig:
    base_dir = Path(".appdata").resolve()

    models_dir = get_models_dir(base_dir)
    models_dir.mkdir(parents=True, exist_ok=True)

    persisted_key = load_persisted_ocr_key(base_dir)
    chosen_spec = resolve_default_ocr_spec(OCR_MODEL_SPECS, persisted_key)

    persist_ocr_key(base_dir, chosen_spec.key)

    ocr_gguf_path = models_dir / chosen_spec.hf_filename
    ocr_mmproj_path = models_dir / chosen_spec.mmproj_filename

    if not is_ocr_model_downloaded(chosen_spec, models_dir):
        print("\nOCR setup")
        print("OCR model artifacts are missing. Downloading required OCR files...")

    new_ocr_config = replace(
        app_cfg.ocr_config,
        hf_repo_id=chosen_spec.hf_repo_id,
        hf_filename=chosen_spec.hf_filename,
        hf_mmproj_filename=chosen_spec.mmproj_filename,
        ocr_model_key=chosen_spec.key,
        ocr_model_display_name=chosen_spec.display_name,
        ocr_gguf_path=ocr_gguf_path if ocr_gguf_path.exists() else None,
        ocr_mmproj_path=ocr_mmproj_path if ocr_mmproj_path.exists() else None,
    )
    new_ocr_config.validate(allow_unresolved_model_paths=True)

    resolved_gguf = ocr_gguf_path
    if not ocr_gguf_path.exists():
        resolved_gguf = _ensure_hf_download(
            repo_id=chosen_spec.hf_repo_id,
            filename=chosen_spec.hf_filename,
            revision=app_cfg.ocr_config.hf_revision,
            models_dir=models_dir,
        )

    resolved_mmproj = ocr_mmproj_path
    if not ocr_mmproj_path.exists():
        resolved_mmproj = _ensure_hf_download(
            repo_id=chosen_spec.hf_repo_id,
            filename=chosen_spec.mmproj_filename,
            revision=app_cfg.ocr_config.hf_revision,
            models_dir=models_dir,
        )

    final_ocr_config = replace(
        new_ocr_config,
        ocr_gguf_path=resolved_gguf,
        ocr_mmproj_path=resolved_mmproj,
    )
    final_ocr_config.validate(allow_unresolved_model_paths=False)

    return replace(app_cfg, ocr_config=final_ocr_config)
