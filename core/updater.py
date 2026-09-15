#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS | APP UPDATER ENGINE (GESTOR DE ACTUALIZACIONES)
# =====================================================================

import os
import sys
import subprocess
from datetime import datetime
from typing import Dict, Any, List
from core.paths import ROOT_DIR


def get_current_repo_info() -> Dict[str, Any]:
    """Obtiene la información actual del repositorio de ABRAXAS."""
    branch = "main"
    remote_url = "Local"
    current_commit = "HEAD"
    is_git = os.path.exists(os.path.join(ROOT_DIR, ".git"))

    if is_git:
        try:
            b_proc = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=ROOT_DIR, capture_output=True, text=True, timeout=3
            )
            if b_proc.returncode == 0 and b_proc.stdout.strip():
                branch = b_proc.stdout.strip()
        except (subprocess.SubprocessError, OSError):
            pass

        try:
            r_proc = subprocess.run(
                ["git", "config", "--get", "remote.origin.url"],
                cwd=ROOT_DIR, capture_output=True, text=True, timeout=3
            )
            if r_proc.returncode == 0 and r_proc.stdout.strip():
                remote_url = r_proc.stdout.strip()
        except (subprocess.SubprocessError, OSError):
            pass

        try:
            c_proc = subprocess.run(
                ["git", "log", "-1", "--pretty=format:%h - %s (%cr)"],
                cwd=ROOT_DIR, capture_output=True, text=True, timeout=3
            )
            if c_proc.returncode == 0 and c_proc.stdout.strip():
                current_commit = c_proc.stdout.strip()
        except (subprocess.SubprocessError, OSError):
            pass

    return {
        "is_git": is_git,
        "branch": branch,
        "remote_url": remote_url,
        "current_commit": current_commit,
        "root_dir": ROOT_DIR
    }


def check_for_app_updates() -> Dict[str, Any]:
    """Consulta al servidor remoto (git fetch) para detectar si existen nuevas actualizaciones."""
    info = get_current_repo_info()
    if not info["is_git"]:
        return {
            "success": False,
            "has_updates": False,
            "pending_count": 0,
            "commits": [],
            "message": "El directorio actual no es un repositorio Git.",
            "info": info
        }

    branch = info["branch"]

    # 1. Fetch remoto
    try:
        fetch_proc = subprocess.run(
            ["git", "fetch", "origin", branch],
            cwd=ROOT_DIR, capture_output=True, text=True, timeout=10
        )
    except (subprocess.SubprocessError, OSError) as e:
        return {
            "success": False,
            "has_updates": False,
            "pending_count": 0,
            "commits": [],
            "message": f"Error al conectar con el servidor remoto: {e}",
            "info": info
        }

    # 2. Comprobar commits pendientes: HEAD..origin/<branch>
    commits = []
    pending_count = 0
    try:
        rev_proc = subprocess.run(
            ["git", "rev-list", "--count", f"HEAD..origin/{branch}"],
            cwd=ROOT_DIR, capture_output=True, text=True, timeout=4
        )
        if rev_proc.returncode == 0 and rev_proc.stdout.strip().isdigit():
            pending_count = int(rev_proc.stdout.strip())
    except (subprocess.SubprocessError, OSError):
        pending_count = 0

    if pending_count > 0:
        try:
            log_proc = subprocess.run(
                ["git", "log", f"HEAD..origin/{branch}", "--pretty=format:%h%x09%s%x09%an%x09%cr"],
                cwd=ROOT_DIR, capture_output=True, text=True, timeout=4
            )
            if log_proc.returncode == 0 and log_proc.stdout.strip():
                for line in log_proc.stdout.splitlines():
                    parts = line.split("\t")
                    if len(parts) >= 4:
                        commits.append({
                            "hash": parts[0],
                            "title": parts[1],
                            "author": parts[2],
                            "time": parts[3]
                        })
        except (subprocess.SubprocessError, OSError):
            pass

    # 3. Comprobar si hay cambios locales no guardados
    is_dirty = False
    try:
        st_proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT_DIR, capture_output=True, text=True, timeout=3
        )
        if st_proc.returncode == 0 and st_proc.stdout.strip():
            is_dirty = True
    except (subprocess.SubprocessError, OSError):
        pass

    return {
        "success": True,
        "has_updates": pending_count > 0,
        "pending_count": pending_count,
        "commits": commits,
        "is_dirty": is_dirty,
        "info": info,
        "message": f"{pending_count} actualización(es) disponible(s)" if pending_count > 0 else "ABRAXAS está al día"
    }


def execute_app_update(stash_dirty: bool = True) -> Dict[str, Any]:
    """Ejecuta la actualización completa de la aplicación mediante Git Pull y sincronización."""
    logs = []
    
    def add_log(msg: str):
        now = datetime.now().strftime("%H:%M:%S")
        logs.append(f"[{now}] {msg}")

    add_log("Iniciando secuencia de actualización de ABRAXAS...")
    info = get_current_repo_info()
    branch = info["branch"]

    # 1. Comprobar estado sucio
    did_stash = False
    try:
        st_proc = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT_DIR, capture_output=True, text=True)
        if st_proc.returncode == 0 and st_proc.stdout.strip():
            if stash_dirty:
                add_log("Cambios locales detectados: Creando resguardo automático (git stash)...")
                stash_proc = subprocess.run(
                    ["git", "stash", "push", "-m", "Auto-stash antes de actualizar ABRAXAS"],
                    cwd=ROOT_DIR, capture_output=True, text=True
                )
                if stash_proc.returncode == 0:
                    did_stash = True
                    add_log("✔ Resguardo local completado.")
    except (subprocess.SubprocessError, OSError) as e:
        add_log(f"⚠ Advertencia durante verificación de cambios locales: {e}")

    # 2. Git Pull
    add_log(f"Descargando y fusionando actualizaciones desde origin/{branch}...")
    try:
        pull_proc = subprocess.run(
            ["git", "pull", "origin", branch],
            cwd=ROOT_DIR, capture_output=True, text=True, timeout=20
        )
        if pull_proc.returncode == 0:
            add_log("✔ Repositorio actualizado exitosamente.")
            add_log(pull_proc.stdout.strip())
        else:
            add_log(f"✖ Error durante git pull: {pull_proc.stderr.strip()}")
            return {
                "success": False,
                "logs": logs,
                "message": "Error al descargar la actualización de Git."
            }
    except (subprocess.SubprocessError, OSError) as e:
        add_log(f"✖ Excepción durante pull: {e}")
        return {
            "success": False,
            "logs": logs,
            "message": str(e)
        }

    # 3. Restaurar Stash si se creó
    if did_stash:
        add_log("Restaurando resguardo de cambios locales (git stash pop)...")
        try:
            subprocess.run(["git", "stash", "pop"], cwd=ROOT_DIR, capture_output=True, text=True)
            add_log("✔ Cambios locales re-aplicados.")
        except (subprocess.SubprocessError, OSError) as e:
            add_log(f"⚠ Aviso al restaurar stash: {e}")

    # 4. Actualizar versión
    new_commit = ""
    try:
        c_proc = subprocess.run(["git", "log", "-1", "--pretty=format:%h - %s"], cwd=ROOT_DIR, capture_output=True, text=True)
        if c_proc.returncode == 0:
            new_commit = c_proc.stdout.strip()
    except (subprocess.SubprocessError, OSError):
        pass

    add_log(f"✔ Actualización finalizada con éxito. Commit activo: {new_commit}")
    add_log("Se recomienda reiniciar la aplicación para aplicar todos los cambios en memoria.")

    return {
        "success": True,
        "logs": logs,
        "new_commit": new_commit,
        "message": "ABRAXAS ha sido actualizado exitosamente."
    }


def restart_abraxas_app():
    """Reinicia la aplicación ABRAXAS en un proceso nuevo y limpio."""
    python_bin = sys.executable
    main_script = os.path.join(ROOT_DIR, "gui", "app_main.py")
    if os.path.exists(main_script):
        subprocess.Popen([python_bin, main_script], cwd=ROOT_DIR)
        sys.exit(0)

