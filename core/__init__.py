"""
❖ ABRAXAS CORE ENGINE
Dualistic Operating Environment for Linux
"""

import os
import subprocess
import re

_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_VERSION_FILE = os.path.join(_ROOT_DIR, "VERSION")

def get_git_commit_version():
    """Extrae el tag de versión del mensaje del último commit (ej: [v0.1.4])"""
    try:
        msg = subprocess.check_output(
            ["git", "log", "-1", "--pretty=%B"],
            cwd=_ROOT_DIR,
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
        
        # Busca patrones tipo [v0.1.4] o [v1.0.0] en el mensaje del commit
        match = re.search(r"\[v?(\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?)\]", msg)
        if match:
            return match.group(1)
    except Exception:
        pass
    return ""

def get_version():
    """Obtiene dinámicamente la versión actual dando prioridad al commit de Git"""
    # 1. Intentar extraer la versión etiquetada en el commit actual de Git [vX.Y.Z]
    git_v = get_git_commit_version()
    if git_v:
        return git_v

    # 2. Si no hay tag en el commit, leer el archivo VERSION
    if os.path.exists(_VERSION_FILE):
        try:
            with open(_VERSION_FILE, "r", encoding="utf-8") as _f:
                v = _f.read().strip()
                if v:
                    return v
        except Exception:
            pass

    return "0.1.1"

__version__ = get_version()
__app_name__ = "ABRAXAS"
