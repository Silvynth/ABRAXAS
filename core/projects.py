#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS | MÓDULO PROYECTOS (CORE)
# =====================================================================

import os
import time
import shutil
import subprocess
import stat
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

def check_project_unsaved_changes(project_path: str) -> dict:
    """
    Inspecciona si el proyecto tiene cambios locales sin guardar o commits sin enviar en Git.
    Retorna un diccionario estructurado con:
    - has_unsaved: bool
    - modified_files: list[str]
    - untracked_files: list[str]
    - unpushed_commits: int
    - summary: str
    """
    git_dir = os.path.join(project_path, ".git")
    if not os.path.isdir(git_dir):
        return {
            "has_unsaved": False,
            "modified_files": [],
            "untracked_files": [],
            "unpushed_commits": 0,
            "summary": "Sin repositorio Git"
        }

    modified = []
    untracked = []
    unpushed = 0

    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=5
        )
        if proc.returncode == 0 and proc.stdout.strip():
            for line in proc.stdout.splitlines():
                l = line.strip()
                if not l:
                    continue
                code = l[:2].strip()
                fname = l[2:].strip()
                if code == "??":
                    untracked.append(fname)
                else:
                    modified.append(fname)
    except Exception:
        pass

    try:
        proc_up = subprocess.run(
            ["git", "rev-list", "--count", "@{upstream}..HEAD"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=5
        )
        if proc_up.returncode == 0 and proc_up.stdout.strip():
            unpushed = int(proc_up.stdout.strip())
    except Exception:
        pass

    has_unsaved = bool(modified or untracked or unpushed > 0)
    summary_parts = []
    if modified:
        summary_parts.append(f"{len(modified)} modificados")
    if untracked:
        summary_parts.append(f"{len(untracked)} nuevos")
    if unpushed > 0:
        summary_parts.append(f"{unpushed} sin subir")

    summary = ", ".join(summary_parts) if summary_parts else "Limpio"
    return {
        "has_unsaved": has_unsaved,
        "modified_files": modified,
        "untracked_files": untracked,
        "unpushed_commits": unpushed,
        "summary": summary
    }

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
                unsaved_data = check_project_unsaved_changes(full_path)
                folders.append({
                    "name": entry,
                    "path": full_path,
                    "size_str": get_folder_size_str(full_path),
                    "unsaved": unsaved_data
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

    # Manejador de permisos para archivos de solo lectura en .git u otros
    def _handle_readonly(func, path, exc_info):
        try:
            os.chmod(path, stat.S_IWRITE | stat.S_IWUSR)
            func(path)
        except Exception:
            pass

    # Eliminar árbol completo de la carpeta al 100%
    try:
        shutil.rmtree(abs_target, onexc=lambda fn, p, exc: _handle_readonly(fn, p, exc))
    except TypeError:
        shutil.rmtree(abs_target, onerror=_handle_readonly)

    # Invalidar caché de tamaño
    _FOLDER_SIZE_CACHE.pop(abs_target, None)
    return True

if __name__ == "__main__":
    path, items = list_project_folders()
    print(f"Directorio de proyectos ({path}):")
    for item in items:
        print(f" - {item['name']} ({item['path']}) [{item.get('size_str')}]")
