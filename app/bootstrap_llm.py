from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from app.settings import AppConfig

try:
    from huggingface_hub import hf_hub_download  # type: ignore
except ImportError:
    hf_hub_download = None

def get_app_base_dir() -> Path:
    # Get base directory to store model
    # Base directory is .appdata while in dev mode
    return Path(".appdata").resolve()

def ensure_gguf(app_cfg: AppConfig, model_dir: Path) -> Path:
    # Make the models directory if it's not already created
    model_dir.mkdir(parents=True, exist_ok=True)

    # Get the gguf path from the configuration app_cfg and return the path
    gguf_path = app_cfg.llm_config.llama_gguf_path
    if gguf_path is not None:
        gguf_path = Path(gguf_path).expanduser().resolve()
        if gguf_path.exists() and gguf_path.is_file():
            return gguf_path

    # If it does not exist, raise an error
    if not app_cfg.llm_config.hf_repo_id or not app_cfg.llm_config.hf_filename:
        raise RuntimeError(
            "Missing Hugging Face metadata for GGUF. Set hf_repo_id and hf_filename in llm_config."
        )

    # Download the model from hugging face using details from the app_cfg
    # Make sure the gguf goes into the models folder - normalize if hugging face created nested paths
    if hf_hub_download is None:
        raise RuntimeError(
            "huggingface_hub is not installed. Install dependencies before bootstrapping models."
        )
    try:
        downloaded = hf_hub_download(
            repo_id=app_cfg.llm_config.hf_repo_id,
            filename=app_cfg.llm_config.hf_filename,
            revision=app_cfg.llm_config.hf_revision,
            local_dir=str(model_dir),
            local_dir_use_symlinks=False,
        )
    except Exception as exc:
        raise RuntimeError(f"Failed to download GGUF from Hugging Face: {exc}") from exc

    resolved = Path(downloaded).expanduser().resolve()
    if not resolved.exists() or not resolved.is_file():
        raise RuntimeError(f"Downloaded GGUF file is invalid: {resolved}")
    return resolved

def ensure_mmproj(app_cfg: AppConfig, models_dir: Path) -> Path | None:
    # If no mmproj is identified in app_cfg then return None
    mmproj_filename = app_cfg.llm_config.hf_mmproj_filename
    if not mmproj_filename:
        return None

    existing = app_cfg.llm_config.llama_mmproj_path
    if existing is not None:
        existing = Path(existing).expanduser().resolve()
        if existing.exists() and existing.is_file():
            return existing

    # Same as ensure_gguf - download it if not downloaded and normalize path
    if not app_cfg.llm_config.hf_repo_id:
        raise RuntimeError("Missing hf_repo_id required for mmproj download.")
    if hf_hub_download is None:
        raise RuntimeError(
            "huggingface_hub is not installed. Install dependencies before bootstrapping models."
        )
    try:
        downloaded = hf_hub_download(
            repo_id=app_cfg.llm_config.hf_repo_id,
            filename=mmproj_filename,
            revision=app_cfg.llm_config.hf_revision,
            local_dir=str(models_dir),
            local_dir_use_symlinks=False,
        )
    except Exception as exc:
        raise RuntimeError(f"Failed to download mmproj from Hugging Face: {exc}") from exc
    resolved = Path(downloaded).expanduser().resolve()
    if not resolved.exists() or not resolved.is_file():
        raise RuntimeError(f"Downloaded mmproj file is invalid: {resolved}")
    return resolved

def ensure_llm_server_bin(app_cfg: AppConfig) -> Path:
    # Ensure that the server binary exists and return the path.
    # If it doesn't exist, return an error
    server_bin = app_cfg.llm_server.llama_server_path.expanduser().resolve()
    if not server_bin.exists() or not server_bin.is_file():
        raise RuntimeError(
            f"llama-server binary not found at {server_bin}. Build/install llama-server first."
        )
    return server_bin


def bootstrap_llm(app_cfg: AppConfig) -> AppConfig:

    # Resolve the app's base directory where the data/models are stored (.appdata)
    base_dir = get_app_base_dir()
    models_dir = base_dir / "models"

    # Ensure the model files are available
    gguf_path = ensure_gguf(app_cfg, models_dir)
    mmproj_path = ensure_mmproj(app_cfg, models_dir)

    # Ensure the llm server binary exists
    server_bin = ensure_llm_server_bin(app_cfg)

    # Update the app_cfg with resolved file paths
    new_llm_config = replace(
        app_cfg.llm_config,
        llama_gguf_path=gguf_path,
        llama_mmproj_path=mmproj_path,
    )
    new_llm_server = replace(app_cfg.llm_server, llama_server_path=server_bin)

    # Validate the resolved configuration
    new_llm_config.validate(allow_unresolved_model_paths=False)
    new_llm_server.validate()
    app_cfg.llm_request.validate()

    # Return a new app configuration with updated app_cfg settings
    return replace(app_cfg, llm_config=new_llm_config, llm_server=new_llm_server)
