from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class RunConfig:
    author: str
    single_paragraph_mode: bool = True
    max_llm_corrections: int = 5
    include_edited_text_section_policy: bool = True

    def validate(self) -> None:
        if not isinstance(self.author, str) or not self.author.strip():
            raise ValueError("RunConfig.author must be a non-empty string.")
        
        if not isinstance(self.single_paragraph_mode, bool):
            raise ValueError("RunConfig.single_paragraph_mode must be a boolean.")
        
        # bool is a subclass of int; reject it explicitly.
        if isinstance(self.max_llm_corrections, bool) or not isinstance(self.max_llm_corrections, int):
            raise ValueError("RunConfig.max_llm_corrections must be an integer.")
        
        if not isinstance(self.include_edited_text_section_policy, bool):
            raise ValueError("RunConfig.include_edited_text_section_policy must be a boolean.")
        
        if self.max_llm_corrections < 0:
            raise ValueError("RunConfig.max_llm_corrections must be >= 0.")


    @staticmethod
    def from_strings(
        author: str,
        single_paragraph_mode: bool | str = True,
        max_llm_corrections: str | int = 5,
        include_edited_text_section_policy: bool | str = True
    ) -> "RunConfig":
        def _to_bool(v: bool | str) -> bool:
            if isinstance(v, bool):
                return v
            if isinstance(v, str):
                s = v.strip().lower()
                if s in {"1", "true", "t", "yes", "y", "on"}:
                    return True
                if s in {"0", "false", "f", "no", "n", "off"}:
                    return False
            raise ValueError(f"Expected a boolean or boolean-string, got {v!r}")
        
        cfg = RunConfig(
            author=author,
            single_paragraph_mode=_to_bool(single_paragraph_mode),
            max_llm_corrections=int(max_llm_corrections),
            include_edited_text_section_policy=_to_bool(include_edited_text_section_policy)
        )
        cfg.validate()
        return cfg
