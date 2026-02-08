from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
import json
import os

try:
    import psutil  # type: ignore
except ImportError:
    psutil = None

try:
    import torch  # type: ignore
except ImportError:
    torch = None

from app.settings import AppConfig
from config.llm_model_spec import LlmModelSpec, MODEL_SPECS

@dataclass(frozen=True, slots=True)
class HardwareInfo:
    total_ram_gb: float
    cpu_count: int
    cuda_vram_gb: float | None
    is_mps: bool

    @property
    def summary(self) -> str:
        vram = f"{self.cuda_vram_gb:.1f} GB VRAM" if self.cuda_vram_gb is not None else "No CUDA VRAM"
        mps = "MPS available" if self.is_mps else "MPS unavailable"
        return f"RAM: {self.total_ram_gb:.1f} GB | CPU: {self.cpu_count} | {vram} | {mps}"
    
def get_hardware_info() -> HardwareInfo:
    """
    Collect basic hardware stats used to filter and recommend models.
    """
    if psutil is not None:
        total_ram_gb = psutil.virtual_memory().total / (1024 ** 3)
    else:
        try:
            total_ram_gb = (
                os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
            ) / (1024 ** 3)
        except (ValueError, OSError, AttributeError):
            total_ram_gb = 8.0

    cpu_count = os.cpu_count() or 1
    cuda_vram_gb = None
    if torch is not None and torch.cuda.is_available():
        try:
            mem = torch.cuda.get_device_properties(0).total_memory
            cuda_vram_gb = mem / (1024 ** 3)
        except Exception:
            cuda_vram_gb = None
    is_mps = bool(
        torch is not None
        and getattr(torch.backends, "mps", None)
        and torch.backends.mps.is_available()
    )
    return HardwareInfo(
        total_ram_gb=total_ram_gb,
        cpu_count=cpu_count,
        cuda_vram_gb=cuda_vram_gb,
        is_mps=is_mps
    )

def _fits_model(spec: LlmModelSpec, hw: HardwareInfo) -> bool:
    """Return True if the model fits available RAM/VRAM constraints."""
    if hw.total_ram_gb < spec.min_ram_gb:
        return False
    if hw.cuda_vram_gb is None:
        return True
    return hw.cuda_vram_gb >= spec.min_vram_gb

def recommend_model(specs: list[LlmModelSpec], hw: HardwareInfo) -> LlmModelSpec:
    """Pick the largest model that fits the current hardware."""
    # Best quality = largest model that fits
    ranked = sorted(specs, key=lambda s: (s.min_ram_gb, s.min_vram_gb), reverse=True)
    for spec in ranked:
        if _fits_model(spec, hw):
            return spec
    return ranked[-1]

def _persist_path(base_dir: Path) -> Path:
    """
    Return the path used to persist the selected model key
    In dev this is .appdata/config/llm_model.json
    """
    return base_dir / "config" / "llm_model.json"

def get_models_dir(base_dir: Path) -> Path:
    """
    Returns the directory where the models are based
    In dev this is .appdata/models
    """
    return base_dir / "models"

def is_model_downloaded(spec: LlmModelSpec, models_dir: Path) -> bool:
    """
    Check whether the GGUF model file exists locally.
    """
    gguf_path = models_dir / spec.hf_filename
    if not gguf_path.exists():
        return False
    if spec.mmproj_filename:
        mmproj_path = models_dir / spec.mmproj_filename
        return mmproj_path.exists()
    return True

def list_downloaded_specs(specs: list[LlmModelSpec], model_dir: Path) -> list[LlmModelSpec]:
    """
    Return model specs that are already downloaded
    """
    return [spec for spec in specs if is_model_downloaded(spec, model_dir)]

def list_available_for_download(specs: list[LlmModelSpec], models_dir: Path) -> list[LlmModelSpec]:
    """
    Return model specs that are not yet downloaded
    """
    return [spec for spec in specs if not is_model_downloaded(spec, models_dir)]

def load_persisted_model_key(base_dir: Path) -> str | None:
    """
    Load the previously selected model from disk, if present.
    """
    persist_path = _persist_path(base_dir)
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

def persist_model_key(base_dir: Path, key: str) -> None:
    """
    Persist the selected model key to disk
    """
    persist_path = _persist_path(base_dir)
    persist_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"model_key": key}
    persist_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

def _format_spec_line(idx: int, spec: LlmModelSpec, recommended_key: str) -> str:
    """Format a single model entry line for display in selection UI."""
    marker = " (Recommended)" if spec.key == recommended_key else ""
    return (
        f"{idx}. {spec.display_name}{marker} | "
        f"{spec.param_size_b}B | min RAM {spec.min_ram_gb} GB, min VRAM {spec.min_vram_gb} GB"
    )

def prompt_initial_action(has_downloads: bool, has_installed: bool) -> str:
    """
    Prompt user to select an installed model or download a new one.
    """
    print("\nModel setup")
    if has_installed and has_downloads:
        print("1. Select an installed model (Recommended)")
        print("2. Download a new model")
        prompt = "Selection [default: 1]: "
        while True:
            raw = input(prompt).strip()
            if not raw or raw == "1":
                return "select"
            if raw == "2":
                return "download"
            print("Invalid selection. Enter 1 or 2.")

    if has_installed:
        print("1. Select an installed model")
        prompt = "Selection [default: 1]: "
        while True:
            raw = input(prompt).strip()
            if not raw or raw == "1":
                return "select"
            print("Invalid selection. Enter 1.")

    # No installed models: force download flow.
    return "download"

def prompt_model_choice_from_list(
    specs: list[LlmModelSpec],
    recommended: LlmModelSpec,
    persisted_key: str | None,
    hw: HardwareInfo,
    label: str,
) -> LlmModelSpec:
    """Prompt the user to select a model from a list."""
    print(f"\nModel selection - {label}")
    print(hw.summary)
    print("Choose a model (press Enter for default):")
    for i, spec in enumerate(specs, start=1):
        print(_format_spec_line(i, spec, recommended.key))

    default_spec = None
    if persisted_key:
        default_spec = next((s for s in specs if s.key == persisted_key), None)
    if default_spec is None:
        default_spec = next((s for s in specs if s.key == recommended.key), None)
    if default_spec is None:
        default_spec = specs[0]
    prompt = f"Selection [default: {default_spec.display_name}]: "

    while True:
        raw = input(prompt).strip()
        if not raw:
            return default_spec
        if raw.isdigit():
            idx = int(raw)
            if 1 <= idx <= len(specs):
                return specs[idx - 1]
        print("Invalid selection. Enter a number from the list or press Enter for default.")

def select_model_and_update_config(app_cfg: AppConfig) -> AppConfig:
    """
    Interactive model selection
    Returns updated app config with chosen model
    """

    base_dir = Path(".appdata").resolve()

    models_dir = get_models_dir(base_dir)
    models_dir.mkdir(parents=True, exist_ok=True)

    hw = get_hardware_info()

    eligible_specs = [spec for spec in MODEL_SPECS if _fits_model(spec, hw)]
    candidate_specs = eligible_specs if eligible_specs else MODEL_SPECS

    recommended = recommend_model(candidate_specs, hw)

    persisted_key = load_persisted_model_key(base_dir)

    # If persisted choice fits, treat it as the recommended default (overrides the recommendation)
    # otherwise discard the persisted key
    if persisted_key is not None:
        persisted_spec = next((s for s in candidate_specs if s.key == persisted_key), None)
        if persisted_spec is not None:
            recommended = persisted_spec
        else:
            persisted_key = None

    # Identify downloaded model specs
    downloaded_specs = list_downloaded_specs(candidate_specs, models_dir)
    available_for_download = list_available_for_download(candidate_specs, models_dir)

    # If no installed models are available, skip straight to download flow.
    if downloaded_specs:
        action = prompt_initial_action(
            has_downloads=bool(available_for_download),
            has_installed=True,
        )
    else:
        action = "download"

    # Based on user's choice, select from strict list partitions.
    if action == "select":
        if not downloaded_specs:
            action = "download"
        else:
            selectable_specs = downloaded_specs
            label = "Select an installed model"

    if action == "download":
        if available_for_download:
            selectable_specs = available_for_download
            label = "Available models for download (metadata only)"
        elif downloaded_specs:
            print("All eligible models are already downloaded. Showing installed models.")
            selectable_specs = downloaded_specs
            label = "Select an installed model"
        else:
            raise RuntimeError("No eligible models are available to select or download.")

    chosen_spec = prompt_model_choice_from_list(
        specs=selectable_specs,
        recommended=recommended,
        persisted_key=persisted_key,
        hw=hw,
        label=label,
    )

    # Persist the user's choice model key to disk
    persist_model_key(base_dir, chosen_spec.key)

    # Create a new app.llm_config, app.llm_request_config, app.llm_server_config objects by copying the old ones and updating the relevant fields
    gguf_path = models_dir / chosen_spec.hf_filename
    model_is_downloaded = is_model_downloaded(chosen_spec, models_dir)
    mmproj_path = (
        models_dir / chosen_spec.mmproj_filename
        if chosen_spec.mmproj_filename is not None
        else None
    )

    new_llm_config = replace(
        app_cfg.llm_config,
        llama_server_model=chosen_spec.key,
        llama_model_key=chosen_spec.key,
        llama_model_display_name=chosen_spec.display_name,
        llama_model_alias=chosen_spec.display_name,
        llama_model_family=chosen_spec.model_family,
        hf_repo_id=chosen_spec.hf_repo_id,
        hf_filename=chosen_spec.hf_filename,
        hf_mmproj_filename=chosen_spec.mmproj_filename,
        llama_gguf_path=gguf_path if model_is_downloaded else None,
        llama_mmproj_path=mmproj_path if mmproj_path is not None and mmproj_path.exists() else None,
    )
    new_llm_request = replace(app_cfg.llm_request)
    new_llm_server = replace(app_cfg.llm_server)

    # Validate the new app.llm_config, app.llm_request_config, app.llm_server_config objects
    new_llm_config.validate(allow_unresolved_model_paths=True)
    new_llm_request.validate()
    new_llm_server.validate()

    # Now validated, replace the old app.llm_config, app.llm_request_config, app.llm_server_config configs with the new ones and return the updated app_cfg
    return replace(
        app_cfg,
        llm_config=new_llm_config,
        llm_request=new_llm_request,
        llm_server=new_llm_server,
    )
