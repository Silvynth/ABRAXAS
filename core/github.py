#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS CORE | GITHUB INTEGRATION & REPO SYNC ENGINE
# =====================================================================

import os
import json
import time
import subprocess
import urllib.request
import urllib.error
from typing import List, Dict, Tuple, Any

_REPO_VISIBILITY_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_REPO_VISIBILITY_TTL: float = 300.0  # 5 minutos

def invalidate_repo_visibility_cache(project_path: str = None):
    """Invalida la caché de visibilidad para un proyecto o para todos."""
    global _REPO_VISIBILITY_CACHE
    if project_path:
        _REPO_VISIBILITY_CACHE.pop(project_path, None)
    else:
        _REPO_VISIBILITY_CACHE.clear()


def check_gh_cli_authenticated() -> Tuple[bool, str]:
    """Verifica si la herramienta oficial de GitHub ('gh') está instalada y autenticada."""
    try:
        proc = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True, timeout=5)
        if proc.returncode == 0:
            for line in proc.stdout.splitlines() + proc.stderr.splitlines():
                if "Logged in to" in line and "account" in line:
                    return True, line.strip()
            return True, "Autenticado en GitHub CLI"
        return False, proc.stderr.strip() or "No autenticado en gh CLI"
    except FileNotFoundError:
        return False, "GitHub CLI ('gh') no está instalado"
    except (subprocess.TimeoutExpired, OSError) as e:
        return False, str(e)

def fetch_repos_gh_cli() -> List[Dict]:
    """Obtiene la lista completa de repositorios del usuario autenticado vía 'gh'."""
    cmd = [
        "gh", "repo", "list", 
        "--limit", "100", 
        "--json", "name,nameWithOwner,description,url,isPrivate,pushedAt,stargazerCount,primaryLanguage,sshUrl"
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    if proc.returncode != 0:
        raise RuntimeError(f"Error de GitHub CLI: {proc.stderr}")
    
    raw_data = json.loads(proc.stdout)
    repos = []
    for item in raw_data:
        lang = item.get("primaryLanguage") or {}
        repos.append({
            "name": item.get("name", ""),
            "full_name": item.get("nameWithOwner", item.get("name", "")),
            "description": item.get("description") or "Sin descripción.",
            "url": item.get("url", ""),
            "ssh_url": item.get("sshUrl", ""),
            "is_private": item.get("isPrivate", False),
            "pushed_at": item.get("pushedAt", "")[:10] if item.get("pushedAt") else "",
            "stars": item.get("stargazerCount", 0),
            "language": lang.get("name", "Varios") if isinstance(lang, dict) else "Varios"
        })
    return repos

def fetch_repos_api(username: str = "", token: str = "") -> List[Dict]:
    """Obtiene repositorios usando la API REST de GitHub."""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Abraxas-Neos-App"
    }

    if token.strip():
        url = "https://api.github.com/user/repos?per_page=100&sort=updated"
        headers["Authorization"] = f"Bearer {token.strip()}"
    elif username.strip():
        url = f"https://api.github.com/users/{username.strip()}/repos?per_page=100&sort=updated"
    else:
        raise ValueError("Debes ingresar un nombre de usuario de GitHub o un Token de acceso.")

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
            repos = []
            for item in raw:
                repos.append({
                    "name": item.get("name", ""),
                    "full_name": item.get("full_name", item.get("name", "")),
                    "description": item.get("description") or "Sin descripción.",
                    "url": item.get("html_url", item.get("clone_url", "")),
                    "clone_url": item.get("clone_url", ""),
                    "ssh_url": item.get("ssh_url", ""),
                    "is_private": item.get("private", False),
                    "pushed_at": item.get("pushed_at", "")[:10] if item.get("pushed_at") else "",
                    "stars": item.get("stargazers_count", 0),
                    "language": item.get("language") or "Varios"
                })
            return repos
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise ValueError(f"No se encontró el usuario o repositorio en GitHub ({username}).")
        elif e.code == 401:
            raise ValueError("Token de acceso de GitHub inválido o expirado.")
        else:
            raise RuntimeError(f"Error HTTP {e.code} de GitHub: {e.reason}")
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as e:
        raise RuntimeError(f"Error al conectar con GitHub: {e}")

def fetch_single_repo_api(owner_repo: str, token: str = "") -> Dict:
    """Obtiene información de un único repositorio (owner/repo) usando la API de GitHub."""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Abraxas-Neos-App"
    }
    if token.strip():
        headers["Authorization"] = f"Bearer {token.strip()}"
    
    clean_target = owner_repo.strip().strip("/")
    url = f"https://api.github.com/repos/{clean_target}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            item = json.loads(resp.read().decode("utf-8"))
            lang = item.get("language") or "Varios"
            return {
                "name": item.get("name", ""),
                "full_name": item.get("full_name", item.get("name", "")),
                "description": item.get("description") or "Sin descripción.",
                "url": item.get("html_url", item.get("clone_url", "")),
                "clone_url": item.get("clone_url", ""),
                "ssh_url": item.get("ssh_url", ""),
                "is_private": item.get("private", False),
                "pushed_at": item.get("pushed_at", "")[:10] if item.get("pushed_at") else "",
                "stars": item.get("stargazers_count", 0),
                "language": lang
            }
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise ValueError(f"No se encontró el repositorio '{owner_repo}' en GitHub.")
        raise RuntimeError(f"Error HTTP {e.code} de GitHub: {e.reason}")
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as e:
        raise RuntimeError(f"Error al conectar con GitHub: {e}")

def parse_git_url_repo_data(url: str) -> Dict:
    """Genera una estructura de repositorio a partir de un enlace arbitrario de Git clone."""
    clean_url = url.strip()
    if clean_url.startswith("git clone "):
        clean_url = clean_url[10:].strip()
    
    # Extraer nombre del repositorio (ej. https://github.com/pallets/flask.git -> flask)
    parts = clean_url.rstrip("/").split("/")
    repo_name = parts[-1] if parts else "repo"
    if repo_name.endswith(".git"):
        repo_name = repo_name[:-4]

    return {
        "name": repo_name,
        "full_name": clean_url,
        "description": f"Repositorio remoto ({clean_url})",
        "url": clean_url,
        "clone_url": clean_url,
        "ssh_url": clean_url if clean_url.startswith("git@") else "",
        "is_private": False,
        "pushed_at": "Reciente",
        "stars": 0,
        "language": "Git"
    }

def clone_repository(repo_target: str, dest_dir: str, full_repo_name: str = "") -> None:
    """Clona un repositorio remoto utilizando GitHub CLI ('gh repo clone') para repositorios privados y públicos."""
    # 1. Si GitHub CLI está autenticado, usar 'gh repo clone' (soporta repos privados sin prompts interactivos)
    is_gh, _ = check_gh_cli_authenticated()
    if is_gh:
        target = full_repo_name if full_repo_name else repo_target
        cmd = ["gh", "repo", "clone", target, dest_dir]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if proc.returncode == 0:
            return
        # Si falló gh, continuar con git clone
        err_msg = proc.stderr.strip() or proc.stdout.strip()
    else:
        err_msg = ""

    # 2. Fallback con git clone estándar evitando bloqueos de terminal (GIT_TERMINAL_PROMPT=0)
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    cmd = ["git", "clone", repo_target, dest_dir]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180, env=env)
    
    if proc.returncode != 0:
        details = proc.stderr.strip() or proc.stdout.strip() or err_msg
        raise RuntimeError(f"Error al clonar repositorio:\n{details}")

def pull_repository(repo_path: str) -> str:
    """Actualiza un repositorio local con 'git pull' evitando bloqueos de terminal."""
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    cmd = ["git", "-C", repo_path, "pull"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60, env=env)
    if proc.returncode != 0:
        raise RuntimeError(f"Error al actualizar repositorio:\n{proc.stderr.strip() or proc.stdout.strip()}")
    return proc.stdout.strip()


def get_repo_visibility(project_path: str, force_refresh: bool = False) -> Dict[str, Any]:
    """Determina si el proyecto tiene remoto en GitHub y consulta si es Público o Privado.
    Utiliza caché en memoria para evitar latencias de red en cada consulta repetida."""
    if not project_path or not os.path.exists(os.path.join(project_path, ".git")):
        return {
            "has_remote": False,
            "is_github": False,
            "visibility": "LOCAL",
            "is_private": True,
            "text": "Sin Git",
            "badge": "⚪ Sin Git"
        }

    now = time.time()
    if not force_refresh and project_path in _REPO_VISIBILITY_CACHE:
        cached_time, cached_val = _REPO_VISIBILITY_CACHE[project_path]
        if (now - cached_time) < _REPO_VISIBILITY_TTL:
            return cached_val

    # 1. Obtener URL remota
    try:
        proc = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=2
        )
        url = proc.stdout.strip() if proc.returncode == 0 else ""
    except Exception:
        url = ""

    if not url:
        res = {
            "has_remote": False,
            "is_github": False,
            "visibility": "LOCAL",
            "is_private": True,
            "text": "Solo Local",
            "badge": "🔒 Solo Local"
        }
        _REPO_VISIBILITY_CACHE[project_path] = (now, res)
        return res

    is_github = "github.com" in url
    if not is_github:
        res = {
            "has_remote": True,
            "is_github": False,
            "visibility": "REMOTE",
            "is_private": None,
            "text": "Remoto Externo",
            "badge": "🌐 Externo"
        }
        _REPO_VISIBILITY_CACHE[project_path] = (now, res)
        return res

    # 2. Consultar visibilidad exacta en GitHub vía gh CLI (con timeout estricto de 3s)
    try:
        gh_proc = subprocess.run(
            ["gh", "repo", "view", "--json", "isPrivate,visibility,nameWithOwner"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=3
        )
        if gh_proc.returncode == 0 and gh_proc.stdout.strip():
            data = json.loads(gh_proc.stdout)
            is_priv = data.get("isPrivate", False)
            vis = "private" if is_priv else "public"
            badge = "🔒 Privado" if is_priv else "🌐 Público"
            res = {
                "has_remote": True,
                "is_github": True,
                "is_private": is_priv,
                "visibility": vis,
                "text": "Privado" if is_priv else "Público",
                "badge": badge,
                "repo_name": data.get("nameWithOwner", "")
            }
            _REPO_VISIBILITY_CACHE[project_path] = (now, res)
            return res
    except Exception:
        pass

    res = {
        "has_remote": True,
        "is_github": True,
        "is_private": None,
        "visibility": "UNKNOWN",
        "text": "GitHub",
        "badge": "🌐 GitHub"
    }
    _REPO_VISIBILITY_CACHE[project_path] = (now, res)
    return res


def change_repo_visibility(project_path: str, target_visibility: str) -> Tuple[bool, str]:
    """Cambia la visibilidad de un repositorio en GitHub ('public' o 'private')."""
    target = target_visibility.lower().strip()
    if target not in ("public", "private"):
        return False, f"Visibilidad inválida: {target}. Debe ser 'public' o 'private'."

    if not project_path or not os.path.exists(os.path.join(project_path, ".git")):
        return False, "El directorio no contiene un repositorio Git válido."

    try:
        cmd = ["gh", "repo", "edit", "--visibility", target, "--accept-visibility-change-consequences"]
        proc = subprocess.run(cmd, cwd=project_path, capture_output=True, text=True, timeout=20)
        if proc.returncode == 0:
            invalidate_repo_visibility_cache(project_path)
            label = "PÚBLICO" if target == "public" else "PRIVADO"
            return True, f"Visibilidad del repositorio cambiada a {label} exitosamente en GitHub."
        err = proc.stderr.strip() or proc.stdout.strip()
        return False, f"Error de GitHub CLI: {err}"
    except Exception as e:
        return False, f"Excepción al cambiar visibilidad: {str(e)}"


def publish_repo_to_github(project_path: str, repo_name: str = "", visibility: str = "private") -> Tuple[bool, str]:
    """Crea un repositorio remoto en GitHub para un proyecto local y lo vincula como origin."""
    if not project_path or not os.path.exists(os.path.join(project_path, ".git")):
        return False, "El directorio no contiene un repositorio Git."

    vis_flag = "--private" if visibility.lower() == "private" else "--public"
    cmd = ["gh", "repo", "create"]
    if repo_name.strip():
        cmd.append(repo_name.strip())
    cmd.extend(["--source=.", vis_flag, "--push"])

    try:
        proc = subprocess.run(cmd, cwd=project_path, capture_output=True, text=True, timeout=30)
        if proc.returncode == 0:
            return True, f"Repositorio publicado exitosamente en GitHub como {visibility.upper()}."
        return False, proc.stderr.strip() or proc.stdout.strip()
    except Exception as e:
        return False, str(e)

