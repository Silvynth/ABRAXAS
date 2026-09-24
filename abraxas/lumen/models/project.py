"""
❖ ABRAXAS 2.0 | Lumen Model: Entidad Project
Representación fuertemente tipada de un repositorio o espacio de trabajo gestionado por Abraxas.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

@dataclass
class Project:
    """Entidad que encapsula el estado completo de un proyecto en desarrollo."""
    path: Path
    name: str = ""
    is_git: bool = False
    current_branch: str = ""
    semver: str = "0.0.0"
    is_dirty: bool = False
    staged_count: int = 0
    unstaged_count: int = 0
    untracked_count: int = 0
    has_venv: bool = False
    venv_path: Optional[Path] = None
    has_docker: bool = False
    preferred_editor: str = "code"
    custom_tags: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.path = Path(self.path).resolve()
        if not self.name:
            self.name = self.path.name

    @property
    def exists(self) -> bool:
        """Indica si el directorio del proyecto existe en el disco."""
        return self.path.is_dir()

    @property
    def total_changes_count(self) -> int:
        """Suma de archivos modificados, en staging o no rastreados."""
        return self.staged_count + self.unstaged_count + self.untracked_count

    @property
    def git_summary(self) -> str:
        """Resumen rápido legible del estado de Git."""
        if not self.is_git:
            return "No Git"
        status = "Clean" if not self.is_dirty else f"{self.total_changes_count} cambios"
        return f"{self.current_branch} [{status}]"

    def __repr__(self) -> str:
        return f"<Project '{self.name}' v{self.semver} ({self.git_summary})>"
