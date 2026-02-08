from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
import json
import os
import psutil
import torch

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
    total_ram_gb = psutil.virtual_memory().total / (1024 ** 3)
    cpu_count = os.cpu_count() or 1
    cuda_vram_gb = None
    if torch.cuda.is_available():
        try:
            mem = torch.cuda.get_device_properties(0).total_memory
            cuda_vram_gb = mem / (1024 ** 3)
        except Exception:
            cuda_vram_gb = None
    is_mps = bool(getattr(torch.backends, "mps", None)) and torch.backends.mps.is_available()
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
    #to do

def get_models_dir(base_dir: Path) -> Path:
    """
    Returns the directory where the models are based
    In dev this is .appdata/models
    """
    #to do

def is_model_downloaded(sepc: LlmModelSpec, models_dir: Path) -> bool:
    """
    Check whether the GGUF model file exists locally.
    """
    # To do

def list_downloaded_specs(specs: list[LlmModelSpec], model_dir: Path) -> list[LlmModelSpec]:
    """
    Return model specs that are already downloaded
    """
    # todo

def list_available_for_download(specs: list[LlmModelSpec], models_dir: Path) -> list[LlmModelSpec]:
    """
    Return model specs that are not yet downloaded
    """
    # todo

def load_persisted_model_key(base_dir: Path) -> str | None:
    """
    Load the previously selected model from disk, if present.
    """
    #todo

def persist_model_key(base_dir: Path, key: str) -> None:
    """
    Persist the selected model key to disk
    """
    # todo

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
    if has_downloads:
        label = "Select an installed model (Recommended)" if has_installed else "Select a model (Recommended)"
        print(f"1. {label}")
        print("2. Download a new model")
        prompt = "Selection [default: 1]: "
        while True:
            raw = input(prompt).strip()
            if not raw or raw == "1":
                return "select"
            if raw == "2":
                return "download"
            print("Invalid selection. Enter 1 or 2.")
    else:
        label = "Select an installed model" if has_installed else "Select a model"
        print(f"1. {label}")
        prompt = "Selection [default: 1]: "
        while True:
            raw = input(prompt).strip()
            if not raw or raw == "1":
                return "select"
            print("Invalid selection. Enter 1.")

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

def select_model_and_update_config(app_cfg):
    """
    Interactive model selection
    Returns updated app config with chosen model
    """

    # Establish the base directory
    # todo

    # Derive directory where models are stored from the base directory
    # todo

    # Retrieve all the hardware information (RAM, CPU, VRAM, MPS)
    # todo

    # Filter models in MODEL_SPECS
    # todo

    # Recommend model based on hardware constraints
    # todo

    # Load a previously persisted model key from disk it it exists
    # todo

    # If persisted choice fits, treat it as the recommended default (overrides the recommendation)
    # otherwise discard the persisted key

    # Identify downloaded model specs
    # todo

    # Prompt user to either select an installed model or to download a new model
    # todo

    # Based on user's choice, the appropriate model list is selected
    # User is prompted to choose a model from the list
    # todo

    # Persist the user's choice model key to disk
    # todo

    # Create a new app.llm_config, app.llm_request_config, app.llm_server_config objects by copying the old ones and updating the relevant fields
    # todo

    # Validate the new app.llm_config, app.llm_request_config, app.llm_server_config objects
    # todo

    # Now validated, replace the old app.llm_config, app.llm_request_config, app.llm_server_config configs with the new ones and return the updated app_cfg
    # todo
