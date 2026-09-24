"""
❖ ABRAXAS 2.0 | Foundation: SemVer Protocol Engine
Cálculo, parseo e incremento de versiones SemVer siguiendo los estándares tácticos de Abraxas (ALPHA, BETA, GAMMA).
"""

from pathlib import Path
from typing import Optional, Union, Tuple
import re
from abraxas.core.process import run_command

SEMVER_REGEX = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9.-]+))?$")

def parse_semver(version_str: str) -> Tuple[int, int, int, str]:
    """
    Parsea una versión SemVer en una tupla (major, minor, patch, prerelease).
    Si falla, retorna (0, 1, 0, "").
    """
    if not version_str:
        return (0, 1, 0, "")
    
    clean = version_str.strip().lstrip("vV")
    match = SEMVER_REGEX.match(clean)
    if match:
        major, minor, patch, pre = match.groups()
        return (int(major), int(minor), int(patch), pre or "")
    
    parts = clean.split(".")
    try:
        major = int(parts[0]) if len(parts) > 0 else 0
        minor = int(parts[1]) if len(parts) > 1 else 1
        patch = int(parts[2]) if len(parts) > 2 else 0
        return (major, minor, patch, "")
    except (ValueError, IndexError):
        return (0, 1, 0, "")


def bump_semver(current_ver: str, bump_type: str = "patch") -> str:
    """
    Calcula la siguiente versión SemVer según el impacto:
    - ALPHA / MAJOR: Rompimiento de arquitectura o nueva era (X+1.0.0)
    - BETA / MINOR: Nueva funcionalidad o sector táctico (X.Y+1.0)
    - GAMMA / PATCH: Corrección de bugs o refactors internos (X.Y.Z+1)
    """
    major, minor, patch, _ = parse_semver(current_ver)
    b_type = bump_type.upper().strip()

    if b_type in ("ALPHA", "MAJOR"):
        major += 1
        minor = 0
        patch = 0
    elif b_type in ("BETA", "MINOR"):
        minor += 1
        patch = 0
    elif b_type in ("GAMMA", "PATCH"):
        patch += 1

    return f"v{major}.{minor}.{patch}"


def detect_project_semver(project_path: Union[str, Path]) -> str:
    """
    Detecta de forma determinista la versión SemVer actual de un proyecto:
    1. Tag más reciente en Git.
    2. Tags embebidos en los últimos 50 commits [vX.Y.Z].
    3. Archivos VERSION o .version en la raíz.
    4. Fallback por defecto: v0.1.0.
    """
    path = Path(project_path).resolve()
    if not path.is_dir():
        return "v0.1.0"

    # 1. Tag Git más reciente
    res = run_command(["git", "describe", "--tags", "--abbrev=0"], cwd=path)
    if res.success and res.output:
        return f"v{res.output.lstrip('vV')}"

    # 2. Tag en los últimos 50 commits
    log_res = run_command(["git", "log", "--format=%s", "-n", "50"], cwd=path)
    if log_res.success:
        for line in log_res.stdout.splitlines():
            m = re.search(r"\[v?(\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?)\]", line)
            if m:
                return f"v{m.group(1)}"

    # 3. Archivo VERSION o .version
    for fname in ("VERSION", ".version"):
        v_file = path / fname
        if v_file.is_file():
            try:
                content = v_file.read_text(encoding="utf-8").strip().split()
                if content and content[0]:
                    return f"v{content[0].lstrip('vV')}"
            except OSError:
                pass

    return "v0.1.0"
