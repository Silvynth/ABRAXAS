#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS | MÓDULO PROYECTOS (CORE)
# =====================================================================

import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from core.setup import read_toml_dict, get_target_config_path

def get_projects_dir(config_path=None):
    """Obtiene la ruta configurada en config.toml para los proyectos."""
    cfg_file = config_path or get_target_config_path()
    cfg = read_toml_dict(cfg_file)
    raw_path = cfg.get("paths", {}).get("projects_dir", "")
    if raw_path:
        return os.path.abspath(os.path.expanduser(raw_path))
    return ""

def list_project_folders(config_path=None):
    """Lista las carpetas que existen dentro del directorio de proyectos de config.toml."""
    base_dir = get_projects_dir(config_path)
    
    if not base_dir or not os.path.isdir(base_dir):
        return base_dir, []

    folders = []
    try:
        for entry in sorted(os.listdir(base_dir)):
            full_path = os.path.join(base_dir, entry)
            if os.path.isdir(full_path) and not entry.startswith("."):
                folders.append({
                    "name": entry,
                    "path": full_path
                })
    except Exception as e:
        print(f"Error al listar carpetas de proyectos en {base_dir}: {e}")

    return base_dir, folders

if __name__ == "__main__":
    path, items = list_project_folders()
    print(f"Directorio de proyectos ({path}):")
    for item in items:
        print(f" - {item['name']} ({item['path']})")

