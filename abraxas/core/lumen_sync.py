#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS | LUMEN SYNC ENGINE (SINCRONIZACIÓN EN TIEMPO REAL)
# =====================================================================

import os
import re
import json
import subprocess
from datetime import datetime
from typing import Dict, List, Any, Union

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

from abraxas.core.github import get_repo_visibility


def get_project_version(project_path: str) -> str:
    """Detecta la versión del proyecto a través de git tags, commits, archivos VERSION o manifests."""
    if not project_path or not os.path.isdir(project_path):
        return "v0.1.0"

    from abraxas.core.git_workflow import get_project_semver
    v = get_project_semver(project_path)
    if v and v != "v0.1.0":
        return v

    # 3. pyproject.toml
    pyproj = os.path.join(project_path, "pyproject.toml")
    if tomllib and os.path.exists(pyproj):
        try:
            with open(pyproj, "rb") as f:
                d = tomllib.load(f)
                v = d.get("project", {}).get("version") or d.get("tool", {}).get("poetry", {}).get("version")
                if v:
                    return f"v{v.lstrip('v')}"
        except (OSError, ValueError):
            pass

    # 4. package.json
    pkg = os.path.join(project_path, "package.json")
    if os.path.exists(pkg):
        try:
            with open(pkg, "r", encoding="utf-8") as f:
                d = json.load(f)
                v = d.get("version")
                if v:
                    return f"v{v.lstrip('v')}"
        except (OSError, json.JSONDecodeError):
            pass

    # 5. config.toml
    cfg = os.path.join(project_path, "config.toml")
    if tomllib and os.path.exists(cfg):
        try:
            with open(cfg, "rb") as f:
                d = tomllib.load(f)
                v = d.get("general", {}).get("version") or d.get("version")
                if v:
                    return f"v{v.lstrip('v')}"
        except (OSError, ValueError):
            pass

    # 6. Cargo.toml (Rust)
    cargo = os.path.join(project_path, "Cargo.toml")
    if os.path.exists(cargo):
        try:
            with open(cargo, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("version") and "=" in line:
                        v = line.split("=")[1].strip().strip('"\'')
                        if v:
                            return f"v{v.lstrip('v')}"
        except OSError:
            pass

    return "v0.1.0"


def get_project_git_info(project_path: str) -> Dict[str, Any]:
    """Obtiene la rama activa y el remoto configurado para el repositorio Git."""
    if not project_path or not os.path.exists(os.path.join(project_path, ".git")):
        return {
            "is_git": False,
            "branch": "(Sin Git)",
            "remote": "Local"
        }

    branch = "main"
    remote = "Local"

    # Rama activa
    try:
        res = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=3
        )
        if res.returncode == 0 and res.stdout.strip():
            branch = res.stdout.strip()
        else:
            # Fallback para detached HEAD
            res_head = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=3
            )
            if res_head.returncode == 0 and res_head.stdout.strip():
                branch = f"HEAD ({res_head.stdout.strip()})"
    except (subprocess.TimeoutExpired, OSError):
        pass

    # Remoto y Visibilidad en GitHub (Público / Privado)
    vis_data = get_repo_visibility(project_path)
    if vis_data.get("has_remote"):
        repo_display = vis_data.get("repo_name")
        if not repo_display:
            try:
                res = subprocess.run(["git", "config", "--get", "remote.origin.url"], cwd=project_path, capture_output=True, text=True, timeout=2)
                repo_display = res.stdout.strip().split("/")[-1].replace(".git", "") if res.returncode == 0 else "origin"
            except Exception:
                repo_display = "origin"
        remote = f"{repo_display}  [{vis_data.get('badge', 'Remoto')}]"
    else:
        remote = "Solo Local  [🔒 Privado en máquina]"

    return {
        "is_git": True,
        "branch": branch,
        "remote": remote,
        "visibility_info": vis_data
    }


def get_project_env_info(project_path: str) -> Dict[str, Any]:
    """Detecta si el proyecto posee un entorno virtual Python y si está realmente activo en la sesión."""
    if not project_path or not os.path.isdir(project_path):
        return {"is_active": False, "text": "Sin Entorno"}

    venv_names = [".venv", "venv", "env", ".env_py"]
    detected_venv = None
    for vname in venv_names:
        cand = os.path.join(project_path, vname)
        if os.path.isdir(cand):
            bin_py = os.path.join(cand, "bin", "python")
            win_py = os.path.join(cand, "Scripts", "python.exe")
            if os.path.exists(bin_py) or os.path.exists(win_py):
                detected_venv = (cand, vname)
                break

    if not detected_venv:
        return {"is_active": False, "text": "Sin Entorno"}

    cand_path, vname = detected_venv
    active_env = os.environ.get("VIRTUAL_ENV", "")
    is_active = False
    if active_env:
        try:
            is_active = os.path.samefile(active_env, cand_path)
        except Exception:
            is_active = os.path.abspath(active_env) == os.path.abspath(cand_path)

    if is_active:
        return {
            "is_active": True,
            "text": f"🟢 Activo ({vname})"
        }
    else:
        return {
            "is_active": False,
            "text": f"⚪ Inactivo ({vname})"
        }


def get_project_docker_info(project_path: str) -> Dict[str, Any]:
    """Verifica contenedores Docker activos relacionados con el proyecto o en el daemon."""
    try:
        proc = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=2
        )
        if proc.returncode == 0:
            containers = [c.strip() for c in proc.stdout.splitlines() if c.strip()]
            p_name = os.path.basename(project_path).lower() if project_path else ""
            matching = [c for c in containers if p_name and p_name in c.lower()]
            if matching:
                return {
                    "count": len(matching),
                    "text": f"{len(matching)} activos ({len(containers)} total)"
                }
            elif containers:
                return {
                    "count": len(containers),
                    "text": f"{len(containers)} activos"
                }
            else:
                return {"count": 0, "text": "0 activos"}
        return {"count": 0, "text": "0 activos"}
    except (subprocess.TimeoutExpired, OSError):
        return {"count": 0, "text": "Inactivo"}


def get_project_git_hud(project_path: str) -> Dict[str, Any]:
    """Extrae el estado numérico del árbol de trabajo de Git (Modificados, Untracked, Deleted)."""
    if not project_path or not os.path.exists(os.path.join(project_path, ".git")):
        return {
            "mod": 0,
            "untracked": 0,
            "deleted": 0,
            "mod_str": "0 modificados",
            "untracked_str": "0 no rastreados",
            "deleted_str": "0"
        }

    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=3
        )
        if proc.returncode != 0:
            return {
                "mod": 0,
                "untracked": 0,
                "deleted": 0,
                "mod_str": "0 modificados",
                "untracked_str": "0 no rastreados",
                "deleted_str": "0"
            }

        mod = 0
        untracked = 0
        deleted = 0
        for line in proc.stdout.splitlines():
            if not line.strip():
                continue
            code = line[:2]
            if "??" in code:
                untracked += 1
            elif "D" in code:
                deleted += 1
            else:
                mod += 1

        mod_str = f"{mod} {'modificado' if mod == 1 else 'modificados'}"
        unt_str = f"{untracked} {'no rastreado' if untracked == 1 else 'no rastreados'}"

        return {
            "mod": mod,
            "untracked": untracked,
            "deleted": deleted,
            "mod_str": mod_str,
            "untracked_str": unt_str,
            "deleted_str": str(deleted)
        }
    except (subprocess.TimeoutExpired, OSError):
        return {
            "mod": 0,
            "untracked": 0,
            "deleted": 0,
            "mod_str": "0 modificados",
            "untracked_str": "0 no rastreados",
            "deleted_str": "0"
        }


def get_project_recent_commits(project_path: str, limit: int = 4) -> List[Dict[str, str]]:
    """Obtiene los últimos N commits reales del repositorio."""
    if not project_path or not os.path.exists(os.path.join(project_path, ".git")):
        return []

    try:
        proc = subprocess.run(
            ["git", "log", f"-n{limit}", "--pretty=format:%cr%x09%s%x09%an%x09%D"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=3
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return []

        commits = []
        palette = ["#38bdf8", "#c084fc", "#fbbf24", "#34d399"]
        for idx, line in enumerate(proc.stdout.splitlines()):
            parts = line.split("\t")
            if len(parts) >= 3:
                time_rel = parts[0].strip()
                title = parts[1].strip()
                author = parts[2].strip()
                branch_ref = parts[3].strip() if len(parts) > 3 and parts[3].strip() else "HEAD"
                
                # Formatear referencia limpia
                if "HEAD -> " in branch_ref:
                    branch_ref = branch_ref.split("HEAD -> ")[-1].split(",")[0].strip()
                elif "tag: " in branch_ref:
                    branch_ref = branch_ref.split("tag: ")[-1].split(",")[0].strip()
                elif "," in branch_ref:
                    branch_ref = branch_ref.split(",")[0].strip()

                commits.append({
                    "time": time_rel,
                    "title": title,
                    "author": author,
                    "branch": branch_ref,
                    "color": palette[idx % len(palette)]
                })
        return commits
    except (subprocess.TimeoutExpired, OSError):
        return []


def get_full_project_sync(folder_data: Union[Dict[str, Any], str]) -> Dict[str, Any]:
    """Genera el diccionario de sincronización completo y en tiempo real para un proyecto."""
    if isinstance(folder_data, str):
        p_path = folder_data
        p_name = os.path.basename(folder_data) or "Proyecto"
    elif isinstance(folder_data, dict):
        p_path = folder_data.get("path", "")
        p_name = folder_data.get("name", os.path.basename(p_path) if p_path else "Proyecto")
    else:
        p_path = ""
        p_name = "Proyecto"

    version = get_project_version(p_path)
    git_info = get_project_git_info(p_path)
    env_info = get_project_env_info(p_path)
    docker_info = get_project_docker_info(p_path)
    git_hud = get_project_git_hud(p_path)
    commits = get_project_recent_commits(p_path, limit=4)

    return {
        "name": p_name,
        "path": p_path,
        "version": version,
        "git_info": git_info,
        "env_info": env_info,
        "docker_info": docker_info,
        "git_hud": git_hud,
        "commits": commits,
        "timestamp": datetime.now().strftime("%H:%M:%S")
    }

