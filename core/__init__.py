"""
❖ ABRAXAS CORE ENGINE
Dualistic Operating Environment for Linux
"""

import os
import subprocess
import re

from core.paths import ROOT_DIR as _ROOT_DIR, VERSION_FILE as _VERSION_FILE

def get_git_commit_version():
    """Extrae el tag de versión del mensaje de los últimos commits (ej: [v1.2.0])"""
    try:
        msg = subprocess.check_output(
            ["git", "log", "-n", "30", "--pretty=%B"],
            cwd=_ROOT_DIR,
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
        
        # Busca patrones tipo [v0.1.4] o [v1.2.0] en los commits
        match = re.search(r"\[v?(\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?)\]", msg)
        if match:
            return match.group(1)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return ""

def get_version():
    """Obtiene dinámicamente la versión actual dando prioridad al tag de Git y commits"""
    # 1. Intentar extraer tag de Git
    try:
        tag = subprocess.check_output(
            ["git", "describe", "--tags", "--abbrev=0"],
            cwd=_ROOT_DIR,
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
        if tag:
            return tag.lstrip("vV")
    except (subprocess.SubprocessError, OSError):
        pass

    # 2. Intentar extraer la versión etiquetada en commits recientes de Git [vX.Y.Z]
    git_v = get_git_commit_version()
    if git_v:
        return git_v

    # 3. Leer archivo .version o VERSION
    for vf in [os.path.join(_ROOT_DIR, ".version"), _VERSION_FILE]:
        if os.path.exists(vf):
            try:
                with open(vf, "r", encoding="utf-8") as _f:
                    v = _f.read().strip().split()[0]
                    if v:
                        return v.lstrip("vV")
            except (OSError, ValueError):
                pass

    return "0.5.15"

__version__ = get_version()
__app_name__ = "ABRAXAS"
