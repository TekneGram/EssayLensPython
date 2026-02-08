# Import services


# Standard utilities
from pathlib import Path
import atexit
from app.settings import AppConfig

def _resolve_path(p: str | Path, project_root: Path) -> Path:
    """
    Resolve a path string to an absolute path
    - Expands ~
    - If relative, resolve it against the project root.
    """
    pp = Path(p).expanduser()
    return pp if pp.is_absolute() else (project_root / pp).resolve()

def build_container(app_cfg: AppConfig):
    """
    Dependency container builder
    Responsibility
    - Takes a fully loaded config object
    - Constructs all the shared services exactly once
    - Wires dependencies together
    - Returns a dictionary of ready-to-use services
    """

    # Determine the project root (used for resolving relative paths)
    project_root = Path(__file__).resolve().parents[1]
    print(project_root)
    

    # ----- LLM Wiring (server mode) -----
    server_proc = None
    server_bin: Path | None = None
    if app_cfg.llm_server.llama_backend == "server":
        server_bin = _resolve_path(
            app_cfg.llm_server.llama_server_path,
            project_root
        )

    def _cleanup() -> None:
        # Placeholder for future server process cleanup.
        if server_proc is not None:
            return

    atexit.register(_cleanup)
    return {
        "project_root": project_root,
        "server_bin": server_bin,
        "server_proc": server_proc,
    }
