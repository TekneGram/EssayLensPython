from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True, slots=True)
class AssessmentPathsConfig:
    """
    This is where the assessment is stored and edited
    """
    input_folder: Path
    output_folder: Path
    explained_folder: Path

    def list_inputs(self) -> list[Path]:
        return [p for p in self.input_folder.rglob("*") if p.is_file()]

    @staticmethod
    def from_strings(
        input_folder: str | Path,
        output_folder: str | Path,
        explained_folder: str | Path,
    ) -> "AssessmentPathsConfig":
        """
        Convenience constructor
        """
        return AssessmentPathsConfig(
            input_folder=AssessmentPathsConfig._norm(input_folder),
            output_folder=AssessmentPathsConfig._norm(output_folder),
            explained_folder=AssessmentPathsConfig._norm(explained_folder),
        )
    
    def ensure_output_dirs(self) -> None:
        """
        Create output directories if they don't exist.
        """
        self.output_folder.mkdir(parents=True, exist_ok=True)
        self.explained_folder.mkdir(parents=True, exist_ok=True)

    def validate(self) -> None:
        """
       Validate that inputs exist and are directories.
       Raises ValueError with a helpful message if something is wrong
        """
        if not self.input_folder.exists():
            self.input_folder.mkdir(parents=True, exist_ok=True)
            # raise ValueError(f"Input folder does not exist: {self.input_folder}")
        if not self.input_folder.is_dir():
            raise ValueError(f"Input path is not a directory: {self.input_folder}")
        
        # Outputs can be created; but if they exist and aren't dirs, that's an error
        for p, label in [
            (self.output_folder, "output_folder"),
            (self.explained_folder, "explained_folder"),
        ]:
            if p.exists() and not p.is_dir():
                raise ValueError(f"{label} exists but is not a directory: {p}")
            
    @staticmethod
    def _norm(p: str | Path) -> Path:
        """
        Normalize a path: expand ~ and resolve to an absolute path.
        """
        return Path(p).expanduser().resolve()
