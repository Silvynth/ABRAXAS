"""
❖ ABRAXAS 2.0 | Lumen Model: Modelos de Dominio GitOps
Representación tipada de ramas, commits, diffs, estados de merge y stashes.
"""

from dataclasses import dataclass, field
from typing import Optional

@dataclass(frozen=True)
class GitBranch:
    """Información de una rama local o remota."""
    name: str
    is_current: bool = False
    is_remote: bool = False
    upstream: Optional[str] = None
    ahead: int = 0
    behind: int = 0

    @property
    def display_name(self) -> str:
        prefix = "● " if self.is_current else "  "
        return f"{prefix}{self.name}"


@dataclass(frozen=True)
class GitCommit:
    """Entidad que representa un commit de Git."""
    hash: str
    short_hash: str
    author: str
    date: str
    message: str
    tags: list[str] = field(default_factory=list)

    @property
    def title(self) -> str:
        """Devuelve la primera línea del mensaje de commit."""
        return self.message.split("\n", 1)[0]


@dataclass(frozen=True)
class GitDiffItem:
    """Representa un archivo con cambios en el árbol de trabajo."""
    path: str
    status: str  # 'M', 'A', 'D', 'R', '??'
    staged: bool = False
    old_path: Optional[str] = None

    @property
    def status_label(self) -> str:
        mapping = {
            "M": "Modificado",
            "A": "Agregado",
            "D": "Eliminado",
            "R": "Renombrado",
            "??": "No rastreado"
        }
        return mapping.get(self.status, self.status)


@dataclass(frozen=True)
class GitMergeStatus:
    """Estado de evaluación previa a una fusión entre ramas."""
    target_branch: str
    source_branch: str
    can_merge: bool
    has_conflicts: bool
    conflict_files: list[str] = field(default_factory=list)
    ahead_commits: int = 0
    behind_commits: int = 0


@dataclass(frozen=True)
class GitStashItem:
    """Entrada en el stash de Git."""
    index: int
    name: str
    branch: str
    message: str


@dataclass(frozen=True)
class GitSyncStatus:
    """Estado de sincronización respecto al remoto (origin)."""
    ahead: int = 0
    behind: int = 0
    has_upstream: bool = False
    upstream_branch: str = ""

    @property
    def is_in_sync(self) -> bool:
        return self.has_upstream and self.ahead == 0 and self.behind == 0
