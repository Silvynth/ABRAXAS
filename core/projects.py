#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS | MÓDULO PROYECTOS (CORE)
# =====================================================================

import os
import time
from core.setup import read_toml_dict, get_target_config_path

_FOLDER_SIZE_CACHE = {}  # folder_path: (mtime, timestamp, result_str)
_PRUNE_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", 
    ".cache", ".next", ".nuxt", "target", "dist", "build", 
    ".idea", ".vscode"
}

def get_projects_dir(config_path=None):
    """Obtiene la ruta configurada en config.toml para los proyectos."""
    cfg_file = config_path or get_target_config_path()
    cfg = read_toml_dict(cfg_file)
    raw_path = cfg.get("paths", {}).get("projects_dir", "")
    if raw_path:
        return os.path.abspath(os.path.expanduser(raw_path))
    return ""

def get_folder_size_str(folder_path: str, force_refresh: bool = False) -> str:
    """Calcula el tamaño total en disco de una carpeta de forma optimizada podando directorios pesados y cacheando."""
    if not folder_path or not os.path.isdir(folder_path):
        return "Tamaño no disponible"

    now = time.time()
    try:
        current_mtime = os.path.getmtime(folder_path)
    except OSError:
        current_mtime = 0

    if not force_refresh and folder_path in _FOLDER_SIZE_CACHE:
        cached_mtime, cached_time, cached_str = _FOLDER_SIZE_CACHE[folder_path]
        if cached_mtime == current_mtime and (now - cached_time < 300.0):
            return cached_str

    total_size = 0
    file_count = 0
    try:
        for dirpath, dirnames, filenames in os.walk(folder_path):
            # Podar directorios de dependencias y artefactos masivos para acelerar el escaneo en 99%
            dirnames[:] = [d for d in dirnames if d not in _PRUNE_DIRS]
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    if not os.path.islink(fp) and os.path.exists(fp):
                        total_size += os.path.getsize(fp)
                        file_count += 1
                except OSError:
                    continue
        
        # Formatear tamaño
        result = ""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if total_size < 1024.0:
                result = f"{total_size:.1f} {unit} ({file_count} archivos)"
                break
            total_size /= 1024.0
        else:
            result = f"{total_size:.1f} PB ({file_count} archivos)"

        _FOLDER_SIZE_CACHE[folder_path] = (current_mtime, now, result)
        return result
    except (PermissionError, OSError):
        return "Tamaño no disponible"

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
                    "path": full_path,
                    "size_str": get_folder_size_str(full_path)
                })
    except Exception as e:
        print(f"Error al listar carpetas de proyectos en {base_dir}: {e}")

    return base_dir, folders

def purge_project_folder(project_path: str, config_path=None) -> bool:
    """Elimina de forma segura y permanente una carpeta de proyecto dentro del directorio de config.toml."""
    base_dir = get_projects_dir(config_path)
    
    if not base_dir or not os.path.isdir(base_dir):
        raise ValueError(f"Directorio base no configurado o no existe: {base_dir}")

    abs_target = os.path.abspath(project_path)
    abs_base = os.path.abspath(base_dir)

    # Verificaciones estrictas de seguridad
    if abs_target == abs_base:
        raise PermissionError("No está permitido eliminar el directorio raíz de proyectos.")
    
    if not abs_target.startswith(abs_base + os.sep):
        raise PermissionError(f"La carpeta '{abs_target}' no reside dentro del directorio autorizado de proyectos ({abs_base}).")

    if not os.path.exists(abs_target):
        raise FileNotFoundError(f"La carpeta '{abs_target}' no existe.")

    if not os.path.isdir(abs_target):
        raise ValueError(f"'{abs_target}' no es un directorio.")

    # Eliminar árbol completo de la carpeta
    shutil.rmtree(abs_target)
    return True

if __name__ == "__main__":
    path, items = list_project_folders()
    print(f"Directorio de proyectos ({path}):")
    for item in items:
        print(f" - {item['name']} ({item['path']}) [{item.get('size_str')}]")
