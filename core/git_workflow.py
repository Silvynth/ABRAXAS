#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS CORE | GIT WORKFLOW & IA COMMIT ENGINE
# =====================================================================

import os
import re
import time
import shutil
import subprocess
from datetime import datetime
from typing import Tuple, Dict, Any, List, Optional, Set

from core.engine import AbraxasConfig
from core.ai import get_configured_model, get_model_skill, generate_with_model


def get_project_semver(project_path: str) -> str:
    """Detecta la versión SemVer del proyecto según los protocolos de ABRAXAS."""
    if not project_path or not os.path.isdir(project_path):
        return "v0.1.0"

    # 1. Tag más reciente en Git
    try:
        tag = subprocess.check_output(
            ["git", "describe", "--tags", "--abbrev=0"],
            cwd=project_path,
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
        if tag:
            return f"v{tag.lstrip('vV')}"
    except (subprocess.SubprocessError, OSError, ValueError, IndexError):
        pass

    # 2. Tag en el historial de commits recientes [vX.Y.Z]
    try:
        log_out = subprocess.check_output(
            ["git", "log", "--format=%s", "-n", "50"],
            cwd=project_path,
            stderr=subprocess.DEVNULL,
            text=True
        )
        for line in log_out.splitlines():
            match = re.search(r"\[v?(\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?)\]", line)
            if match:
                return f"v{match.group(1)}"
    except (subprocess.SubprocessError, OSError):
        pass

    # 3. Archivo .version o VERSION en la raíz de git
    for fname in [".version", "VERSION"]:
        fpath = os.path.join(project_path, fname)
        if os.path.isfile(fpath):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    ver = f.read().strip().split()[0]
                    if ver:
                        return f"v{ver.lstrip('vV')}"
            except (OSError, ValueError, IndexError):
                pass

    return "v0.1.0"


def bump_semver(current_ver: str, bump_type: str) -> str:
    """Calcula la siguiente versión SemVer según el tipo de impacto (GAMMA, BETA, ALPHA)."""
    raw = current_ver.lstrip("vV")
    parts = raw.split(".")
    try:
        major = int(parts[0]) if len(parts) > 0 else 0
        minor = int(parts[1]) if len(parts) > 1 else 1
        patch = int(parts[2]) if len(parts) > 2 else 0
    except (ValueError, IndexError):
        major, minor, patch = 0, 1, 0

    bump = bump_type.upper()
    if bump in ("ALPHA", "MAJOR"):
        major += 1
        minor = 0
        patch = 0
    elif bump in ("BETA", "MINOR"):
        minor += 1
        patch = 0
    elif bump in ("GAMMA", "PATCH"):
        patch += 1

    return f"v{major}.{minor}.{patch}"


def clean_commit_title(title: str, fallback: str = "Actualización de componentes del sistema") -> str:
    """Limpia prefijos residuales (HEX, SIL, HEN, AGY, MAN, ANI) y normaliza la longitud del título."""
    cleaned = re.sub(r"^(?:HEX|SIL|HEN|AGY|MAN|ANI):\d{4}(?:\s*\[v?[0-9.]+\])?\s*\|\s*", "", title, flags=re.IGNORECASE).strip()
    if not cleaned:
        cleaned = fallback
    words = cleaned.split()
    if len(words) > 8:
        cleaned = " ".join(words[:8]) + "..."
    if len(cleaned) > 50:
        cleaned = cleaned[:47] + "..."
    return cleaned


def get_next_commit_seq(project_path: str) -> str:
    """Calcula el siguiente identificador correlativo de commit de 4 dígitos (0001, 0024, etc.)."""
    try:
        log_out = subprocess.check_output(
            ["git", "log", "--format=%s", "-n", "50"],
            cwd=project_path,
            stderr=subprocess.DEVNULL,
            text=True
        )
        for line in log_out.splitlines():
            match = re.search(r"(?:HEX|SIL|HEN|AGY|MAN|ANI):(\d{4})", line)
            if match:
                num = int(match.group(1))
                return f"{num + 1:04d}"
    except (subprocess.SubprocessError, OSError, ValueError, IndexError):
        pass
    return "0001"


def get_git_staged_diff(project_path: str, max_chars: int = 12000) -> str:
    """Obtiene el diff de los cambios en staging ('git diff --cached')."""
    try:
        diff = subprocess.check_output(
            ["git", "diff", "--cached"],
            cwd=project_path,
            stderr=subprocess.DEVNULL,
            text=True
        )
        if not diff.strip():
            diff = subprocess.check_output(
                ["git", "diff", "HEAD"],
                cwd=project_path,
                stderr=subprocess.DEVNULL,
                text=True
            )
        return diff[:max_chars]
    except (subprocess.SubprocessError, OSError, ValueError, IndexError):
        return ""


def generate_ia_commit_proposal(
    project_path: str, 
    model_type: str, 
    impact_type: str, 
    target_ver: str, 
    config_path: str = None
) -> Dict[str, Any]:
    """Genera la propuesta de commit estructurada usando Ollama y las directivas de Abraxas."""
    diff = get_git_staged_diff(project_path)
    if not diff.strip():
        raise RuntimeError("El área de preparación (stage) está vacía. Ejecuta 'Add' primero.")

    model_name = get_configured_model(model_type, config_path)
    system_prompt = get_model_skill(model_type, config_path)
    
    id_prefix = "HEX" if model_type == "light" else "HEN"
    next_id = get_next_commit_seq(project_path)

    # Inyección de directiva de contexto de impacto
    context_hint = ""
    if impact_type == "GAMMA":
        context_hint = f"\n[CLASIFICACIÓN DE IMPACTO: GAMMA (Patch / Corrección puntual / {target_ver})]. El operador ha clasificado este cambio como un parche o corrección menor. Tu título y descripción deben ser concisos y enfocarse directamente en el fix o ajuste técnico puntual sin sobredimensionar el cambio."
    elif impact_type == "BETA":
        context_hint = f"\n[CLASIFICACIÓN DE IMPACTO: BETA (Minor / Nuevo Módulo o Funcionalidad / {target_ver})]. El operador ha clasificado este cambio como una nueva funcionalidad o módulo. Tu título y descripción deben destacar las nuevas capacidades y el componente funcional creado."
    elif impact_type == "ALPHA":
        context_hint = f"\n[CLASIFICACIÓN DE IMPACTO: ALPHA (Major / Gran Cambio Estructural / {target_ver})]. El operador ha clasificado este cambio como una evolución o reestructuración mayor de arquitectura. Tu título y descripción deben reflejar la escala global de los cambios."
    elif impact_type == "OMIT":
        context_hint = f"\n[CLASIFICACIÓN DE IMPACTO: CONTINUACIÓN DE VERSIÓN ({target_ver})]. El operador continúa el ciclo de desarrollo en la versión actual sin incrementar el número de versión. Tu título y descripción deben ser concisos y enfocarse en las modificaciones y ajustes técnicos puntuales realizados."

    user_prompt = f"""Analiza el siguiente git diff y genera la propuesta de commit estructurada:

Diff:
{diff}
{context_hint}
"""

    raw_response = generate_with_model(
        prompt=user_prompt,
        model_name=model_name,
        system_prompt=system_prompt,
        config_path=config_path
    )

    # Limpieza de markdown
    clean_msg = re.sub(r"[*#`_-]", "", raw_response)

    # Extracción de Título
    title = ""
    match_title = re.search(r"(?:t[ií]tulo|title):\s*(.+)", clean_msg, re.IGNORECASE)
    if match_title:
        title = match_title.group(1).strip()
    else:
        # Failsafe: buscar la primera línea con contenido relevante
        for line in clean_msg.splitlines():
            line_str = line.strip()
            if line_str and not re.search(r"(parece|realizado|aqu[ií]|cambios|commits|propuesta|saludos|hola)", line_str, re.IGNORECASE):
                title = line_str
                break
        if not title:
            title = clean_msg.splitlines()[0].strip() if clean_msg.splitlines() else "Actualización de componentes del sistema"

    # Quitar cualquier prefijo residual tipo HEX/MAN y normalizar longitud
    title = clean_commit_title(title, fallback="Actualización de componentes del sistema")

    # Extracción de Cuerpo
    body = ""
    match_body = re.search(r"(?:cuerpo|body):\s*(.+)", clean_msg, re.IGNORECASE | re.DOTALL)
    if match_body:
        body = " ".join(match_body.group(1).split()).strip()
    else:
        # Failsafe: todas las líneas excepto la primera
        lines = [l.strip() for l in clean_msg.splitlines() if l.strip()]
        if len(lines) > 1:
            body = " ".join(lines[1:]).strip()
        else:
            body = "Se han realizado modificaciones y optimizaciones técnicas en el código del repositorio."

    commit_header = f"{id_prefix}:{next_id}"
    if target_ver:
        commit_header = f"{id_prefix}:{next_id} [{target_ver}]"

    return {
        "id_prefix": id_prefix,
        "next_id": next_id,
        "commit_header": commit_header,
        "title": title,
        "body": body,
        "impact_type": impact_type,
        "target_ver": target_ver,
        "model_name": model_name,
        "model_type": model_type,
        "full_commit_title": f"{commit_header} | {title}"
    }


def get_git_identity(project_path: str = None) -> Tuple[str, str]:
    """Obtiene user.name y user.email buscando en:
    1. Git config del repositorio o global
    2. config.toml [git] de Abraxas
    3. Auto-detección desde GitHub CLI (gh)
    """
    name = ""
    email = ""
    try:
        name = subprocess.check_output(["git", "config", "user.name"], cwd=project_path, text=True, stderr=subprocess.DEVNULL).strip()
    except (subprocess.SubprocessError, OSError, ValueError, IndexError):
        pass
    try:
        email = subprocess.check_output(["git", "config", "user.email"], cwd=project_path, text=True, stderr=subprocess.DEVNULL).strip()
    except (subprocess.SubprocessError, OSError, ValueError, IndexError):
        pass

    if not name or not email:
        try:
            from core.setup import read_toml_dict, get_target_config_path
            cfg = read_toml_dict(get_target_config_path())
            git_sec = cfg.get("git", {})
            if not name:
                name = git_sec.get("user_name", "")
            if not email:
                email = git_sec.get("user_email", "")
        except (ValueError, IndexError):
            pass

    if not name or not email:
        try:
            from core.setup import detect_git_identity
            det_n, det_e = detect_git_identity()
            if not name:
                name = det_n
            if not email:
                email = det_e
        except (ValueError, IndexError):
            pass

    return name, email


def execute_commit_and_tag(
    project_path: str,
    commit_header: str,
    title: str,
    body: str,
    impact_type: str,
    target_ver: str
) -> Tuple[bool, str]:
    """Confirma el commit en Git y crea el tag correspondiente si aplica."""
    try:
        # 1. Asegurar la persistencia de la versión en los archivos .version y VERSION
        if target_ver:
            clean_ver = target_ver.lstrip("vV")
            for vf_name in [".version", "VERSION"]:
                vf_path = os.path.join(project_path, vf_name)
                try:
                    with open(vf_path, "w", encoding="utf-8") as f:
                        f.write(f"{clean_ver}\n")
                    subprocess.run(["git", "add", vf_name], cwd=project_path, check=False)
                except OSError:
                    pass

        # 2. Ejecutar git commit con identidad garantizada
        full_title = f"{commit_header} | {title}"
        cmd_commit = ["git"]
        git_name, git_email = get_git_identity(project_path)
        if git_name:
            cmd_commit.extend(["-c", f"user.name={git_name}"])
        if git_email:
            cmd_commit.extend(["-c", f"user.email={git_email}"])
        cmd_commit.extend(["commit", "-m", full_title, "-m", body])
        proc = subprocess.run(cmd_commit, cwd=project_path, capture_output=True, text=True, timeout=20)
        if proc.returncode != 0:
            return False, f"Error al ejecutar git commit:\n{proc.stderr}"

        # 3. Crear Git Tag únicamente cuando hay incremento de versión explícito (no en OMIT/continuación)
        if impact_type != "OMIT" and target_ver:
            cmd_tag = ["git", "tag", "-a", target_ver, "-m", f"Release {target_ver}: {full_title}"]
            tag_proc = subprocess.run(cmd_tag, cwd=project_path, capture_output=True, text=True, timeout=10)
            if tag_proc.returncode != 0:
                # Fallback sin -a si falla
                subprocess.run(["git", "tag", target_ver], cwd=project_path, check=False)

        return True, proc.stdout.strip()
    except (subprocess.SubprocessError, OSError, ValueError, IndexError) as e:
        return False, str(e)


# =====================================================================
# GESTIÓN Y MATRIZ TÁCTICA DE RAMAS
# =====================================================================

def get_git_branches_matrix(project_path: str) -> Dict[str, Any]:
    """
    Obtiene y clasifica la matriz completa de ramas (locales y remotas).
    Categorías:
      - Stale/Gone: Remota eliminada en origen (#f87171)
      - Local (Mía): Creada por el usuario actual (#fde047)
      - Local: Rama local de otro usuario o genérica (#f3f4f6)
      - Remota de otros: Rama remota no creada por el usuario (#4ade80)
      - Remota (Mía): Rama remota creada por el usuario actual (#60a5fa)
    """
    if not project_path or not os.path.isdir(project_path):
        return {"current_branch": "", "current_user": "", "branches": [], "undeployed": []}

    current_user, _ = get_git_identity(project_path)
    if not current_user:
        current_user = "silvynth"

    try:
        current_branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=project_path, stderr=subprocess.DEVNULL, text=True
        ).strip()
    except (subprocess.SubprocessError, OSError, ValueError, IndexError):
        current_branch = ""

    fmt = "%(refname)|%(refname:short)|%(upstream:track)|%(upstream:short)|%(authorname)|%(authordate:relative)"
    try:
        raw_output = subprocess.check_output(
            ["git", "for-each-ref", f"--format={fmt}", "refs/heads/", "refs/remotes/"],
            cwd=project_path, stderr=subprocess.DEVNULL, text=True
        )
    except (subprocess.SubprocessError, OSError):
        raw_output = ""

    branches = []
    curr_user_lower = current_user.lower().strip()

    for line in raw_output.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("|")
        if len(parts) < 6:
            continue

        refname, shortname, track, upstream, author, date = (
            parts[0].strip(), parts[1].strip(), parts[2].strip(),
            parts[3].strip(), parts[4].strip(), parts[5].strip()
        )

        if refname.endswith("/HEAD"):
            continue

        is_active = (shortname == current_branch)
        is_mine = (author.lower().strip() == curr_user_lower)
        is_remote = refname.startswith("refs/remotes/")

        if refname.startswith("refs/heads/") and "gone" in track.lower():
            color = "#f87171"
            category = "stale"
            status_label = "Stale/Gone"
        elif refname.startswith("refs/heads/"):
            if is_mine:
                color = "#fde047"
                category = "local_mine"
                status_label = "Activa (Mía)" if is_active else "Local (Mía)"
            else:
                color = "#f3f4f6"
                category = "local_other"
                status_label = "Activa" if is_active else "Local"
        elif is_remote:
            if not is_mine:
                color = "#4ade80"
                category = "remote_other"
                status_label = f"Remota ({author})" if author else "Remota"
            else:
                color = "#60a5fa"
                category = "remote_mine"
                status_label = "Remota (Mía)"
        else:
            color = "#9ca3af"
            category = "other"
            status_label = "Desconocido"

        branches.append({
            "refname": refname,
            "name": shortname,
            "is_active": is_active,
            "is_remote": is_remote,
            "track": track,
            "upstream": upstream,
            "author": author,
            "date": date,
            "category": category,
            "status_label": status_label,
            "color": color
        })

    # Detectar ramas locales sin upstream
    undeployed = []
    try:
        out_b = subprocess.check_output(
            ["git", "branch", "--format=%(refname:short)|%(upstream:short)"],
            cwd=project_path, stderr=subprocess.DEVNULL, text=True
        )
        for b_line in out_b.splitlines():
            b_line = b_line.strip()
            if not b_line:
                continue
            b_parts = b_line.split("|")
            b_name = b_parts[0].strip()
            b_up = b_parts[1].strip() if len(b_parts) > 1 else ""
            if b_name and not b_up:
                undeployed.append(b_name)
    except (subprocess.SubprocessError, OSError, ValueError, IndexError):
        pass

    return {
        "current_branch": current_branch,
        "current_user": current_user,
        "branches": branches,
        "undeployed": undeployed
    }


def execute_git_checkout(project_path: str, branch_name: str) -> Tuple[bool, str]:
    """Realiza checkout a una rama local o remota."""
    try:
        target = branch_name
        if target.startswith("origin/"):
            target = target[len("origin/"):]

        proc = subprocess.run(
            ["git", "checkout", target],
            cwd=project_path, capture_output=True, text=True, timeout=15
        )
        if proc.returncode == 0:
            out = proc.stdout.strip() or proc.stderr.strip()
            return True, out or f"Cambiado a rama '{target}'."
        else:
            return False, proc.stderr.strip() or proc.stdout.strip()
    except (subprocess.SubprocessError, OSError, ValueError, IndexError) as e:
        return False, str(e)


def execute_git_create_branch(project_path: str, new_branch_name: str) -> Tuple[bool, str]:
    """Crea una nueva rama táctica y conmuta a ella (git checkout -b <name>)."""
    clean_name = new_branch_name.strip()
    if not clean_name:
        return False, "El nombre de la nueva rama no puede estar vacío."

    if any(c in clean_name for c in [" ", "~", "^", ":", "?", "*", "[", "\\"]):
        return False, "El nombre de rama contiene caracteres no permitidos por Git."

    try:
        proc = subprocess.run(
            ["git", "checkout", "-b", clean_name],
            cwd=project_path, capture_output=True, text=True, timeout=15
        )
        if proc.returncode == 0:
            out = proc.stdout.strip() or proc.stderr.strip()
            return True, out or f"Rama '{clean_name}' creada y activada."
        else:
            return False, proc.stderr.strip() or proc.stdout.strip()
    except (subprocess.SubprocessError, OSError, ValueError, IndexError) as e:
        return False, str(e)


def execute_git_delete_branch(project_path: str, branch_name: str, force: bool = False) -> Tuple[bool, str]:
    """Elimina una rama local de forma segura (-d) o forzada (-D)."""
    clean_name = branch_name.strip()
    if not clean_name:
        return False, "No se especificó ninguna rama para eliminar."

    flag = "-D" if force else "-d"
    try:
        proc = subprocess.run(
            ["git", "branch", flag, clean_name],
            cwd=project_path, capture_output=True, text=True, timeout=15
        )
        if proc.returncode == 0:
            out = proc.stdout.strip() or proc.stderr.strip()
            return True, out or f"Rama '{clean_name}' eliminada correctamente."
        else:
            return False, proc.stderr.strip() or proc.stdout.strip()
    except (subprocess.SubprocessError, OSError, ValueError, IndexError) as e:
        return False, str(e)


def execute_git_deploy_branch(project_path: str, branch_name: str, remote: str = "origin") -> Tuple[bool, str]:
    """Despliega una rama local al remoto estableciendo tracking (git push -u <remote> <branch>)."""
    clean_name = branch_name.strip()
    if not clean_name:
        return False, "No se especificó la rama a desplegar."

    try:
        proc = subprocess.run(
            ["git", "push", "-u", remote, clean_name],
            cwd=project_path, capture_output=True, text=True, timeout=30
        )
        if proc.returncode == 0:
            out = proc.stdout.strip() or proc.stderr.strip()
            return True, out or f"Rama '{clean_name}' desplegada con éxito en {remote}."
        else:
            return False, proc.stderr.strip() or proc.stdout.strip()
    except (subprocess.SubprocessError, OSError, ValueError, IndexError) as e:
        return False, str(e)


# =====================================================================
# PROTOCOLO DE FUSIÓN TÁCTICA DE RAMAS (GIT MERGE)
# =====================================================================

def get_git_merge_status(project_path: str) -> Dict[str, Any]:
    """
    Detecta el estado de fusión actual del repositorio:
    - is_merge_active: Si hay un merge en proceso (.git/MERGE_HEAD)
    - has_conflicts: Si hay conflictos no resueltos
    - conflicts: Lista de rutas de archivos en conflicto
    - incoming_branch: Nombre de la rama que se está fusionando
    - current_branch: Rama activa (HEAD)
    - current_author: Autor actual
    """
    if not project_path or not os.path.isdir(project_path):
        return {
            "is_merge_active": False,
            "has_conflicts": False,
            "conflicts": [],
            "incoming_branch": "",
            "current_branch": "",
            "current_author": ""
        }

    current_user, _ = get_git_identity(project_path)
    if not current_user:
        current_user = "silvynth"

    try:
        current_branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=project_path, stderr=subprocess.DEVNULL, text=True
        ).strip()
    except (subprocess.SubprocessError, OSError, ValueError, IndexError):
        current_branch = ""

    is_merge_active = False
    incoming_branch = ""
    try:
        git_dir = subprocess.check_output(
            ["git", "rev-parse", "--git-dir"],
            cwd=project_path, stderr=subprocess.DEVNULL, text=True
        ).strip()
        if not os.path.isabs(git_dir):
            git_dir = os.path.join(project_path, git_dir)

        merge_head_path = os.path.join(git_dir, "MERGE_HEAD")
        if os.path.isfile(merge_head_path):
            is_merge_active = True
            merge_msg_path = os.path.join(git_dir, "MERGE_MSG")
            if os.path.isfile(merge_msg_path):
                with open(merge_msg_path, "r", encoding="utf-8", errors="replace") as f:
                    first_line = f.readline().strip()
                    m = re.search(r"Merge branch ['\"]([^'\"]+)['\"]", first_line)
                    if m:
                        incoming_branch = m.group(1)
                    else:
                        incoming_branch = first_line
    except (subprocess.SubprocessError, OSError, ValueError, IndexError):
        pass

    conflicts = []
    has_conflicts = False
    if is_merge_active:
        try:
            out_u = subprocess.check_output(
                ["git", "diff", "--name-only", "--diff-filter=U"],
                cwd=project_path, stderr=subprocess.DEVNULL, text=True
            ).strip()
            if out_u:
                conflicts = [line.strip() for line in out_u.splitlines() if line.strip()]
                has_conflicts = len(conflicts) > 0
        except (subprocess.SubprocessError, OSError, ValueError, IndexError):
            pass

    return {
        "is_merge_active": is_merge_active,
        "has_conflicts": has_conflicts,
        "conflicts": conflicts,
        "incoming_branch": incoming_branch,
        "current_branch": current_branch,
        "current_author": current_user
    }


def get_mergeable_branches(project_path: str) -> List[Dict[str, Any]]:
    """
    Obtiene la lista de todas las ramas disponibles para fusionar en la rama activa HEAD,
    calculando para cada una el desfase de commits (ahead/behind), autor, fecha y último commit.
    """
    if not project_path or not os.path.isdir(project_path):
        return []

    try:
        current_branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=project_path, stderr=subprocess.DEVNULL, text=True
        ).strip()
    except (subprocess.SubprocessError, OSError, ValueError, IndexError):
        current_branch = ""

    branches_raw = []
    try:
        out = subprocess.check_output(
            ["git", "branch", "-a", "--format=%(refname:short)"],
            cwd=project_path, stderr=subprocess.DEVNULL, text=True
        )
        seen = set()
        for line in out.splitlines():
            b = line.strip()
            if b.startswith("remotes/"):
                b = b[len("remotes/"):]
            if not b or b == "origin/HEAD" or b == "HEAD" or b == current_branch:
                continue
            if b in seen:
                continue
            seen.add(b)
            branches_raw.append(b)
    except (subprocess.SubprocessError, OSError, ValueError, IndexError):
        return []

    results = []
    for b in branches_raw:
        ahead, behind = 0, 0
        try:
            cnt_out = subprocess.check_output(
                ["git", "rev-list", "--left-right", "--count", f"HEAD...{b}"],
                cwd=project_path, stderr=subprocess.DEVNULL, text=True
            ).strip()
            if cnt_out:
                parts = cnt_out.split()
                if len(parts) >= 2:
                    ahead = int(parts[0])
                    behind = int(parts[1])
        except (subprocess.SubprocessError, OSError, ValueError, IndexError):
            pass

        subject = ""
        author = ""
        date = ""
        hash_short = ""
        try:
            log_out = subprocess.check_output(
                ["git", "log", "-1", "--format=%h|%an|%ar|%s", b],
                cwd=project_path, stderr=subprocess.DEVNULL, text=True
            ).strip()
            if log_out:
                lparts = log_out.split("|", 3)
                hash_short = lparts[0] if len(lparts) > 0 else ""
                author = lparts[1] if len(lparts) > 1 else ""
                date = lparts[2] if len(lparts) > 2 else ""
                subject = lparts[3] if len(lparts) > 3 else ""
        except (subprocess.SubprocessError, OSError, ValueError, IndexError):
            pass

        results.append({
            "name": b,
            "is_remote": b.startswith("origin/"),
            "ahead": ahead,
            "behind": behind,
            "last_commit_hash": hash_short,
            "last_commit_author": author,
            "last_commit_date": date,
            "last_commit_subject": subject
        })

    results.sort(key=lambda x: (0 if x["behind"] > 0 else 1, -x["behind"], x["name"]))
    return results


def get_merge_diff_and_commits(project_path: str, source_branch: str = None, target_branch: str = None) -> Dict[str, Any]:
    """
    Obtiene el diff y resumen de commits que serán o están siendo integrados.
    - Si se especifican source_branch y target_branch: analiza target_branch..source_branch.
    - Si solo se especifica source_branch: analiza HEAD..source_branch.
    - Si no se especifica ninguno: analiza el merge activo (HEAD..MERGE_HEAD).
    """
    if not project_path or not os.path.isdir(project_path):
        return {"commits": [], "diff_summary": "", "files_changed": []}

    if target_branch and source_branch:
        range_spec = f"{target_branch}..{source_branch}"
    elif source_branch:
        range_spec = f"HEAD..{source_branch}"
    else:
        range_spec = "HEAD..MERGE_HEAD"

    commits = []
    try:
        c_out = subprocess.check_output(
            ["git", "log", range_spec, "--oneline", "-n", "15"],
            cwd=project_path, stderr=subprocess.DEVNULL, text=True
        ).strip()
        if c_out:
            commits = [line.strip() for line in c_out.splitlines() if line.strip()]
    except (subprocess.SubprocessError, OSError, ValueError, IndexError):
        pass

    files_changed = []
    try:
        f_out = subprocess.check_output(
            ["git", "diff", "--name-only", range_spec],
            cwd=project_path, stderr=subprocess.DEVNULL, text=True
        ).strip()
        if f_out:
            files_changed = [line.strip() for line in f_out.splitlines() if line.strip()]
    except (subprocess.SubprocessError, OSError, ValueError, IndexError):
        pass

    diff_summary = ""
    try:
        d_out = subprocess.check_output(
            ["git", "diff", range_spec],
            cwd=project_path, stderr=subprocess.DEVNULL, text=True
        )
        diff_summary = d_out[:6000]
    except (subprocess.SubprocessError, OSError):
        pass

    if not diff_summary:
        try:
            d_cached = subprocess.check_output(
                ["git", "diff", "--cached"],
                cwd=project_path, stderr=subprocess.DEVNULL, text=True
            )
            diff_summary = d_cached[:6000]
        except (subprocess.SubprocessError, OSError):
            pass

    return {
        "commits": commits,
        "files_changed": files_changed,
        "diff_summary": diff_summary
    }


def generate_ia_merge_proposal(
    project_path: str, 
    source_branch: str, 
    model_type: str = "light", 
    config_path: str = None,
    target_branch: str = None
) -> Dict[str, Any]:
    """
    Analiza con IA los commits y diferencias de la fusión para proponer
    un mensaje estructurado y descriptivo.
    """
    data = get_merge_diff_and_commits(project_path, source_branch, target_branch)
    commits_text = "\n".join(data["commits"]) if data["commits"] else "Commits integrados en la rama."
    diff_text = data["diff_summary"] if data["diff_summary"] else "Sin diferencias de texto disponibles."

    model_name = get_configured_model(model_type, config_path)

    id_prefix = "HEX" if model_type == "light" else "HEN"
    next_id = get_next_commit_seq(project_path)

    if model_type == "heavy":
        system_prompt = (
            "Eres un sensor de análisis de integración táctica de ABRAXAS (Motor Avanzado). "
            "Tu tarea es analizar a fondo los datos de la fusión (commits y archivos modificados) "
            "y generar un mensaje de commit de merge detallado y estructurado en español.\n"
            "Formato de respuesta obligatorio:\n"
            "Título: Fusión de [Rama Origen] en [Rama Destino]\n"
            "Cuerpo: [Un párrafo descriptivo y exhaustivo en español que desglose los cambios clave "
            "integrados por la fusión, los archivos principales modificados y el impacto técnico. "
            "Máximo 4 líneas. No incluyas bloques de código.]"
        )
    else:
        system_prompt = (
            "Eres un sensor de análisis de integración táctica de ABRAXAS. "
            "Tu tarea es analizar los datos de la fusión (commits y archivos modificados) "
            "y generar un mensaje de commit de merge conciso y estructurado en español.\n"
            "Formato de respuesta obligatorio:\n"
            "Título: Fusión de [Rama Origen] en [Rama Destino]\n"
            "Cuerpo: [Un párrafo corto y descriptivo en español que explique el propósito de la fusión "
            "y qué principales características o correcciones aporta a la rama destino. "
            "Máximo 3 líneas. No incluyas bloques de código.]"
        )

    branch_display = f"{source_branch} en {target_branch}" if target_branch else (source_branch if source_branch else "rama externa")
    user_prompt = f"""Fusión de la rama '{source_branch}' en la rama destino '{target_branch or 'activa'}'.

Commits integrados:
{commits_text}

Diferencias de código:
{diff_text}
"""

    raw_response = generate_with_model(
        prompt=user_prompt,
        model_name=model_name,
        system_prompt=system_prompt,
        config_path=config_path
    )

    clean_msg = re.sub(r"[*#`_-]", "", raw_response)

    title = ""
    match_title = re.search(r"(?:t[ií]tulo|title):\s*(.+)", clean_msg, re.IGNORECASE)
    if match_title:
        title = match_title.group(1).strip()
    else:
        for line in clean_msg.splitlines():
            line_str = line.strip()
            if line_str and not re.search(r"(parece|realizado|aqu[ií]|cambios|commits|propuesta|saludos|hola)", line_str, re.IGNORECASE):
                title = line_str
                break
        if not title:
            title = f"Fusión de {branch_display}"

    title = clean_commit_title(title, fallback=f"Fusión de {branch_display}")

    body = ""
    match_body = re.search(r"(?:cuerpo|body):\s*(.+)", clean_msg, re.IGNORECASE | re.DOTALL)
    if match_body:
        body = " ".join(match_body.group(1).split()).strip()
    else:
        lines = [l.strip() for l in clean_msg.splitlines() if l.strip()]
        if len(lines) > 1:
            body = " ".join(lines[1:]).strip()
        else:
            body = f"Integración y fusión táctica de la rama '{branch_display}' en la rama activa."

    commit_header = f"{id_prefix}:{next_id}"
    full_title = f"{commit_header} | {title}"

    return {
        "id_prefix": id_prefix,
        "next_id": next_id,
        "commit_header": commit_header,
        "title": title,
        "body": body,
        "full_commit_title": full_title,
        "model_name": model_name,
        "model_type": model_type
    }


def execute_git_merge(
    project_path: str,
    source_branch: str,
    no_ff: bool = False,
    commit_title: str = None,
    commit_body: str = None
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Ejecuta git merge <source_branch> con opciones (--no-ff, mensaje personalizado con identidad).
    Detecta automáticamente si se suscitaron conflictos.
    """
    clean_branch = source_branch.strip()
    if not clean_branch:
        return False, "No se especificó la rama a fusionar.", {}

    cmd = ["git"]
    git_name, git_email = get_git_identity(project_path)
    if git_name:
        cmd.extend(["-c", f"user.name={git_name}"])
    if git_email:
        cmd.extend(["-c", f"user.email={git_email}"])

    cmd.append("merge")
    if no_ff:
        cmd.append("--no-ff")

    if commit_title:
        cmd.extend(["-m", commit_title])
        if commit_body:
            cmd.extend(["-m", commit_body])

    cmd.append(clean_branch)

    try:
        proc = subprocess.run(cmd, cwd=project_path, capture_output=True, text=True, timeout=30)
        output = proc.stdout.strip() or proc.stderr.strip()
        status = get_git_merge_status(project_path)
        if proc.returncode == 0:
            return True, output or f"Rama '{clean_branch}' fusionada exitosamente.", status
        else:
            return False, output or f"Conflicto o error al fusionar '{clean_branch}'.", status
    except (subprocess.SubprocessError, OSError, ValueError, IndexError) as e:
        return False, str(e), get_git_merge_status(project_path)


def execute_git_merge_into(
    project_path: str,
    target_branch: str,
    source_branch: str,
    no_ff: bool = False,
    commit_title: str = None,
    commit_body: str = None
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Realiza checkout a la rama destino (target_branch) e integra la rama origen (source_branch) dentro de ella.
    Permite el flujo inverso ('Integrar mi rama en destino') con resolución segura de conmutación.
    """
    clean_target = target_branch.strip()
    clean_source = source_branch.strip()
    if not clean_target or not clean_source:
        return False, "Ramas de origen o destino no válidas.", {}

    local_target = clean_target.replace("origin/", "").strip()

    # 1. Conmutar a la rama destino
    try:
        chk = subprocess.run(["git", "checkout", local_target], cwd=project_path, capture_output=True, text=True, timeout=20)
        if chk.returncode != 0 and clean_target != local_target:
            chk = subprocess.run(["git", "checkout", clean_target], cwd=project_path, capture_output=True, text=True, timeout=20)

        if chk.returncode != 0:
            err = chk.stderr.strip() or chk.stdout.strip()
            return False, f"Fallo al cambiar a la rama destino '{clean_target}': {err}", get_git_merge_status(project_path)
    except (subprocess.SubprocessError, OSError, ValueError, IndexError) as e:
        return False, f"Error al ejecutar checkout a rama destino: {str(e)}", get_git_merge_status(project_path)

    # 2. Ejecutar la fusión de source_branch dentro de target_branch
    return execute_git_merge(
        project_path=project_path,
        source_branch=clean_source,
        no_ff=no_ff,
        commit_title=commit_title,
        commit_body=commit_body
    )


def execute_git_merge_abort(project_path: str) -> Tuple[bool, str]:
    """Ejecuta git merge --abort para cancelar de forma segura la fusión activa."""
    try:
        proc = subprocess.run(
            ["git", "merge", "--abort"],
            cwd=project_path, capture_output=True, text=True, timeout=15
        )
        if proc.returncode == 0:
            return True, proc.stdout.strip() or "Fusión abortada de forma segura. El árbol de trabajo fue restaurado."
        else:
            return False, proc.stderr.strip() or proc.stdout.strip()
    except (subprocess.SubprocessError, OSError, ValueError, IndexError) as e:
        return False, str(e)


def execute_git_resolve_conflicts(project_path: str, strategy: str = "ours") -> Tuple[bool, str]:
    """
    Resuelve todos los archivos en conflicto usando la estrategia indicada ('ours' o 'theirs')
    y los agrega automáticamente al staging (git add).
    """
    flag = "--ours" if strategy.lower() == "ours" else "--theirs"
    try:
        out_u = subprocess.check_output(
            ["git", "diff", "--name-only", "--diff-filter=U"],
            cwd=project_path, stderr=subprocess.DEVNULL, text=True
        ).strip()
        conflicts = [l.strip() for l in out_u.splitlines() if l.strip()]
        if not conflicts:
            return True, "No se detectaron archivos con conflictos pendientes."

        details = []
        for file in conflicts:
            subprocess.run(["git", "checkout", flag, file], cwd=project_path, check=False)
            subprocess.run(["git", "add", file], cwd=project_path, check=False)
            details.append(f"✔ Resuelto ({strategy}): {file}")

        return True, "\n".join(details)
    except (subprocess.SubprocessError, OSError, ValueError, IndexError) as e:
        return False, str(e)


def execute_git_complete_merge(project_path: str, commit_title: str, commit_body: str = "") -> Tuple[bool, str]:
    """Finaliza y confirma la fusión activa registrando el commit de merge."""
    cmd = ["git"]
    git_name, git_email = get_git_identity(project_path)
    if git_name:
        cmd.extend(["-c", f"user.name={git_name}"])
    if git_email:
        cmd.extend(["-c", f"user.email={git_email}"])

    cmd.extend(["commit", "-m", commit_title])
    if commit_body:
        cmd.extend(["-m", commit_body])

    try:
        proc = subprocess.run(cmd, cwd=project_path, capture_output=True, text=True, timeout=20)
        if proc.returncode == 0:
            return True, proc.stdout.strip() or "Commit de fusión registrado exitosamente."
        else:
            return False, proc.stderr.strip() or proc.stdout.strip()
    except (subprocess.SubprocessError, OSError, ValueError, IndexError) as e:
        return False, str(e)


# =====================================================================
# PROTOCOLO DE ESTADO Y SINCRONIZACIÓN (STATUS, FETCH, PULL & STASH)
# =====================================================================

def get_git_sync_deep_status(project_path: str) -> Dict[str, Any]:
    """
    Inspección exhaustiva y táctica del estado del repositorio:
    - Rama activa y remoto configurado.
    - Estado de sincronización respecto a upstream (Ahead, Behind, Divergido, Al día).
    - Commits entrantes (incoming) y salientes (outgoing) con hash, autor, tiempo y mensaje.
    - Archivos afectados que se modificarían al hacer pull.
    - Árbol de trabajo con métricas de líneas añadidas/eliminadas (+/-) por archivo.
    - Archivos en staging vs unstaged vs untracked vs conflictos.
    - Registro de stashes activos.
    - Diagnóstico de seguridad pre-pull (Fast-Forward posible, Autostash necesario, archivos con riesgo de colisión).
    - Marca de tiempo del último fetch.
    """
    default_res: Dict[str, Any] = {
        "branch": "",
        "remote": "",
        "remote_url": "",
        "upstream": "",
        "has_remote": False,
        "has_upstream": False,
        "ahead": 0,
        "behind": 0,
        "is_synced": True,
        "diverged": False,
        "ahead_commits": [],
        "behind_commits": [],
        "incoming_files_stat": "",
        "incoming_files_names": [],
        "is_clean": True,
        "staged_files": [],
        "unstaged_files": [],
        "untracked_files": [],
        "conflict_files": [],
        "total_staged": 0,
        "total_unstaged": 0,
        "total_untracked": 0,
        "total_conflicts": 0,
        "total_lines_added": 0,
        "total_lines_deleted": 0,
        "stash_count": 0,
        "stashes": [],
        "last_fetch_str": "Sin registro de fetch",
        "can_fast_forward": False,
        "will_need_autostash": False,
        "collision_files": [],
        "recommended_action": "Al día"
    }

    if not project_path or not os.path.isdir(project_path):
        return default_res

    # 1. Rama activa
    branch = ""
    try:
        b_res = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=project_path, capture_output=True, text=True, timeout=4
        )
        if b_res.returncode == 0 and b_res.stdout.strip():
            branch = b_res.stdout.strip()
        else:
            h_res = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=project_path, capture_output=True, text=True, timeout=4
            )
            branch = h_res.stdout.strip() or "HEAD"
    except (subprocess.SubprocessError, OSError, ValueError, IndexError):
        branch = "HEAD"
    default_res["branch"] = branch

    # 2. Remoto y URL
    remote_name = ""
    remote_url = ""
    try:
        r_list = subprocess.check_output(
            ["git", "remote"],
            cwd=project_path, stderr=subprocess.DEVNULL, text=True
        ).splitlines()
        if r_list:
            remote_name = "origin" if "origin" in r_list else r_list[0].strip()
            url_res = subprocess.run(
                ["git", "config", "--get", f"remote.{remote_name}.url"],
                cwd=project_path, capture_output=True, text=True, timeout=4
            )
            if url_res.returncode == 0:
                remote_url = url_res.stdout.strip()
    except (subprocess.SubprocessError, OSError, ValueError, IndexError):
        pass
    default_res["remote"] = remote_name
    default_res["remote_url"] = remote_url
    default_res["has_remote"] = bool(remote_name)

    # 3. Upstream tracking branch
    upstream = ""
    try:
        u_res = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
            cwd=project_path, capture_output=True, text=True, timeout=4
        )
        if u_res.returncode == 0 and u_res.stdout.strip():
            upstream = u_res.stdout.strip()
    except (subprocess.SubprocessError, OSError, ValueError, IndexError):
        pass
    default_res["upstream"] = upstream
    default_res["has_upstream"] = bool(upstream)

    # 4. Ahead / Behind y Commits
    ahead = 0
    behind = 0
    ahead_commits: List[Dict[str, str]] = []
    behind_commits: List[Dict[str, str]] = []
    incoming_stat = ""
    incoming_names: List[str] = []

    if upstream:
        try:
            rev_out = subprocess.check_output(
                ["git", "rev-list", "--left-right", "--count", f"HEAD...{upstream}"],
                cwd=project_path, stderr=subprocess.DEVNULL, text=True
            ).strip().split()
            if len(rev_out) >= 2:
                ahead = int(rev_out[0])
                behind = int(rev_out[1])
        except (subprocess.SubprocessError, OSError, ValueError, IndexError):
            pass

        # Commits salientes (Ahead)
        if ahead > 0:
            try:
                ah_log = subprocess.check_output(
                    ["git", "log", f"{upstream}..HEAD", "--pretty=format:%h%x09%an%x09%cr%x09%s", "-n", "20"],
                    cwd=project_path, stderr=subprocess.DEVNULL, text=True
                ).strip()
                for line in ah_log.splitlines():
                    p = line.split("\t")
                    if len(p) >= 4:
                        ahead_commits.append({
                            "hash": p[0], "author": p[1], "time": p[2], "subject": p[3]
                        })
            except (subprocess.SubprocessError, OSError, ValueError, IndexError):
                pass

        # Commits entrantes (Behind)
        if behind > 0:
            try:
                bh_log = subprocess.check_output(
                    ["git", "log", f"HEAD..{upstream}", "--pretty=format:%h%x09%an%x09%cr%x09%s", "-n", "20"],
                    cwd=project_path, stderr=subprocess.DEVNULL, text=True
                ).strip()
                for line in bh_log.splitlines():
                    p = line.split("\t")
                    if len(p) >= 4:
                        behind_commits.append({
                            "hash": p[0], "author": p[1], "time": p[2], "subject": p[3]
                        })

                # Stat de archivos entrantes
                stat_out = subprocess.check_output(
                    ["git", "diff", "--stat", f"HEAD...{upstream}"],
                    cwd=project_path, stderr=subprocess.DEVNULL, text=True
                ).strip()
                incoming_stat = stat_out

                names_out = subprocess.check_output(
                    ["git", "diff", "--name-only", f"HEAD...{upstream}"],
                    cwd=project_path, stderr=subprocess.DEVNULL, text=True
                ).strip()
                incoming_names = [n.strip() for n in names_out.splitlines() if n.strip()]
            except (subprocess.SubprocessError, OSError, ValueError, IndexError):
                pass

    default_res["ahead"] = ahead
    default_res["behind"] = behind
    default_res["ahead_commits"] = ahead_commits
    default_res["behind_commits"] = behind_commits
    default_res["incoming_files_stat"] = incoming_stat
    default_res["incoming_files_names"] = incoming_names
    default_res["is_synced"] = (ahead == 0 and behind == 0 and bool(upstream))
    default_res["diverged"] = (ahead > 0 and behind > 0)

    # 5. Árbol de trabajo profundo (Status con numstat)
    unstaged_lines: Dict[str, Tuple[int, int]] = {}
    staged_lines: Dict[str, Tuple[int, int]] = {}
    tot_adds = 0
    tot_dels = 0

    try:
        num_u = subprocess.check_output(
            ["git", "diff", "--numstat"],
            cwd=project_path, stderr=subprocess.DEVNULL, text=True
        ).strip().splitlines()
        for l in num_u:
            pts = l.split("\t")
            if len(pts) >= 3:
                a = int(pts[0]) if pts[0].isdigit() else 0
                d = int(pts[1]) if pts[1].isdigit() else 0
                unstaged_lines[pts[2].strip()] = (a, d)
                tot_adds += a
                tot_dels += d
    except (subprocess.SubprocessError, OSError, ValueError, IndexError):
        pass

    try:
        num_s = subprocess.check_output(
            ["git", "diff", "--cached", "--numstat"],
            cwd=project_path, stderr=subprocess.DEVNULL, text=True
        ).strip().splitlines()
        for l in num_s:
            pts = l.split("\t")
            if len(pts) >= 3:
                a = int(pts[0]) if pts[0].isdigit() else 0
                d = int(pts[1]) if pts[1].isdigit() else 0
                staged_lines[pts[2].strip()] = (a, d)
                tot_adds += a
                tot_dels += d
    except (subprocess.SubprocessError, OSError, ValueError, IndexError):
        pass

    staged_files: List[Dict[str, Any]] = []
    unstaged_files: List[Dict[str, Any]] = []
    untracked_files: List[str] = []
    conflict_files: List[str] = []

    try:
        porc = subprocess.check_output(
            ["git", "status", "--porcelain=v1", "-uall"],
            cwd=project_path, stderr=subprocess.DEVNULL, text=True
        ).splitlines()
        for line in porc:
            if len(line) < 4:
                continue
            x = line[0]
            y = line[1]
            fpath = line[3:].strip()
            if " -> " in fpath:
                fpath = fpath.split(" -> ")[-1].strip()

            # Conflictos
            if x in "U" or y in "U" or (x == "A" and y == "A") or (x == "D" and y == "D"):
                conflict_files.append(fpath)
                continue

            # Untracked
            if x == "?" and y == "?":
                untracked_files.append(fpath)
                continue

            # Staged (X != ' ' and X != '?')
            if x != " " and x != "?":
                s_code = "M" if x == "M" else ("A" if x == "A" else ("D" if x == "D" else x))
                a, d = staged_lines.get(fpath, (0, 0))
                staged_files.append({
                    "path": fpath,
                    "status": s_code,
                    "adds": a,
                    "dels": d
                })

            # Unstaged (Y != ' ' and Y != '?')
            if y != " " and y != "?":
                u_code = "M" if y == "M" else ("D" if y == "D" else y)
                a, d = unstaged_lines.get(fpath, (0, 0))
                unstaged_files.append({
                    "path": fpath,
                    "status": u_code,
                    "adds": a,
                    "dels": d
                })
    except (subprocess.SubprocessError, OSError, ValueError, IndexError):
        pass

    default_res["staged_files"] = staged_files
    default_res["unstaged_files"] = unstaged_files
    default_res["untracked_files"] = untracked_files
    default_res["conflict_files"] = conflict_files
    default_res["total_staged"] = len(staged_files)
    default_res["total_unstaged"] = len(unstaged_files)
    default_res["total_untracked"] = len(untracked_files)
    default_res["total_conflicts"] = len(conflict_files)
    default_res["total_lines_added"] = tot_adds
    default_res["total_lines_deleted"] = tot_dels
    default_res["is_clean"] = (
        len(staged_files) == 0 and len(unstaged_files) == 0 and 
        len(untracked_files) == 0 and len(conflict_files) == 0
    )

    # 6. Detector de Stashes
    stashes: List[Dict[str, str]] = []
    try:
        s_out = subprocess.check_output(
            ["git", "stash", "list", "--pretty=format:%gd%x09%cr%x09%gs"],
            cwd=project_path, stderr=subprocess.DEVNULL, text=True
        ).strip()
        if s_out:
            for s_line in s_out.splitlines():
                pts = s_line.split("\t")
                if len(pts) >= 3:
                    stashes.append({
                        "id": pts[0],
                        "time": pts[1],
                        "message": pts[2]
                    })
                elif len(pts) == 1:
                    stashes.append({
                        "id": pts[0],
                        "time": "",
                        "message": pts[0]
                    })
    except (subprocess.SubprocessError, OSError, ValueError, IndexError):
        pass
    default_res["stashes"] = stashes
    default_res["stash_count"] = len(stashes)

    # 7. Timestamp último fetch (.git/FETCH_HEAD)
    last_fetch_str = "Sin registro de fetch"
    try:
        git_dir = subprocess.check_output(
            ["git", "rev-parse", "--git-dir"],
            cwd=project_path, stderr=subprocess.DEVNULL, text=True
        ).strip()
        if not os.path.isabs(git_dir):
            git_dir = os.path.join(project_path, git_dir)
        fhead_path = os.path.join(git_dir, "FETCH_HEAD")
        if os.path.exists(fhead_path):
            mtime = os.path.getmtime(fhead_path)
            diff_s = int(time.time() - mtime)
            dt = datetime.fromtimestamp(mtime)
            if diff_s < 60:
                last_fetch_str = f"Hace {diff_s}s ({dt.strftime('%H:%M:%S')})"
            elif diff_s < 3600:
                last_fetch_str = f"Hace {diff_s // 60} min ({dt.strftime('%H:%M')})"
            elif diff_s < 86400:
                last_fetch_str = f"Hace {diff_s // 3600} h ({dt.strftime('%H:%M')})"
            else:
                last_fetch_str = dt.strftime("%Y-%m-%d %H:%M")
    except (subprocess.SubprocessError, OSError, ValueError, IndexError):
        pass
    default_res["last_fetch_str"] = last_fetch_str

    # 8. Diagnóstico de Salud Pre-Pull
    can_ff = (ahead == 0 and behind > 0)
    has_local_changes = (len(staged_files) > 0 or len(unstaged_files) > 0)
    will_autostash = (has_local_changes and behind > 0)

    # Detección de colisiones potenciales
    local_modified_paths = set(
        [f["path"] for f in staged_files] + [f["path"] for f in unstaged_files]
    )
    collision_files = list(local_modified_paths.intersection(set(incoming_names)))

    default_res["can_fast_forward"] = can_ff
    default_res["will_need_autostash"] = will_autostash
    default_res["collision_files"] = collision_files

    if not default_res["has_remote"]:
        default_res["recommended_action"] = "Configurar remoto origin"
    elif not default_res["has_upstream"]:
        default_res["recommended_action"] = f"Desplegar a {remote_name} (git push -u)"
    elif default_res["diverged"]:
        default_res["recommended_action"] = "Divergencia: Rebase + Autostash recomendado"
    elif behind > 0:
        if collision_files:
            default_res["recommended_action"] = f"Atención: {len(collision_files)} archivo(s) con posible colisión"
        elif will_autostash:
            default_res["recommended_action"] = "Pull Seguro (Rebase + Autostash)"
        else:
            default_res["recommended_action"] = "Pull directo disponible (Fast-Forward)"
    elif ahead > 0:
        default_res["recommended_action"] = f"Push pendiente (+{ahead} commits)"
    else:
        default_res["recommended_action"] = "Al día con el remoto"

    return default_res


def execute_git_fetch(project_path: str, remote: str = "", prune: bool = True) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Ejecuta git fetch (--all o remoto específico) con poda (--prune) opcional.
    Devuelve: (éxito, mensaje/log crudo, telemetría estructurada de cambios)
    """
    if not project_path or not os.path.isdir(project_path):
        return False, "Ruta de proyecto inválida.", {}

    cmd = ["git", "fetch"]
    if remote:
        cmd.append(remote)
    else:
        cmd.append("--all")

    if prune:
        cmd.append("--prune")

    try:
        proc = subprocess.run(cmd, cwd=project_path, capture_output=True, text=True, timeout=45)
        raw_output = (proc.stdout.strip() + "\n" + proc.stderr.strip()).strip()
        if proc.returncode == 0:
            status_after = get_git_sync_deep_status(project_path)
            summary_msg = "Metadatos remotos descargados correctamente."
            if status_after.get("behind", 0) > 0:
                summary_msg = f"Fetch completado: Hay {status_after['behind']} nuevo(s) commit(s) pendientes de incorporar."
            elif status_after.get("is_synced"):
                summary_msg = "Fetch completado: El repositorio está al día con el remoto."
            return True, raw_output or summary_msg, status_after
        else:
            return False, raw_output or "Fallo al ejecutar git fetch.", {}
    except subprocess.TimeoutExpired:
        return False, "La operación de git fetch excedió el tiempo límite (timeout de 45s). Verifica tu conexión de red.", {}
    except (subprocess.SubprocessError, OSError, ValueError, IndexError) as e:
        return False, str(e), {}


def execute_git_pull(project_path: str, strategy: str = "rebase", autostash: bool = True) -> Tuple[bool, str]:
    """
    Ejecuta git pull aplicando la estrategia táctica elegida:
    - 'rebase': git pull --rebase (--autostash si autostash=True)
    - 'merge': git pull --no-rebase
    - 'ff-only': git pull --ff-only
    """
    if not project_path or not os.path.isdir(project_path):
        return False, "Ruta de proyecto inválida."

    cmd = ["git", "pull"]
    if strategy == "rebase":
        cmd.append("--rebase")
        if autostash:
            cmd.append("--autostash")
    elif strategy == "ff-only":
        cmd.append("--ff-only")
    else:
        cmd.append("--no-rebase")

    try:
        proc = subprocess.run(cmd, cwd=project_path, capture_output=True, text=True, timeout=60)
        combined = (proc.stdout.strip() + "\n" + proc.stderr.strip()).strip()
        if proc.returncode == 0:
            if "Already up to date" in combined or "Ya está actualizado" in combined:
                msg = "El repositorio ya se encontraba completamente al día con el remoto."
            elif "Fast-forward" in combined:
                msg = f"Sincronización Fast-Forward completada exitosamente:\n{combined}"
            elif "Applied autostash" in combined:
                msg = f"Pull Rebase completado exitosamente (con cambios locales preservados y re-aplicados vía autostash):\n{combined}"
            else:
                msg = combined or "Pull completado correctamente."
            return True, msg
        else:
            return False, combined or "Fallo al ejecutar git pull."
    except subprocess.TimeoutExpired:
        return False, "Tiempo de espera agotado durante git pull (timeout de 60s). Verifica tu conexión a internet o credenciales."
    except (subprocess.SubprocessError, OSError, ValueError, IndexError) as e:
        return False, str(e)


def execute_git_stage_path(project_path: str, file_path: str) -> Tuple[bool, str]:
    """Agrega un archivo o directorio específico al área de preparación (git add)."""
    try:
        proc = subprocess.run(["git", "add", "--", file_path], cwd=project_path, capture_output=True, text=True, timeout=10)
        if proc.returncode == 0:
            return True, f"'{file_path}' agregado a staging correctamente."
        return False, proc.stderr.strip() or "Error al agregar archivo a staging."
    except (subprocess.SubprocessError, OSError, ValueError, IndexError) as e:
        return False, str(e)


def execute_git_unstage_path(project_path: str, file_path: str) -> Tuple[bool, str]:
    """Quita un archivo del staging sin descartar sus cambios en el disco (git restore --staged)."""
    try:
        proc = subprocess.run(["git", "restore", "--staged", "--", file_path], cwd=project_path, capture_output=True, text=True, timeout=10)
        if proc.returncode == 0:
            return True, f"'{file_path}' retirado de staging."
        proc2 = subprocess.run(["git", "reset", "HEAD", "--", file_path], cwd=project_path, capture_output=True, text=True, timeout=10)
        if proc2.returncode == 0:
            return True, f"'{file_path}' retirado de staging."
        return False, proc.stderr.strip() or proc2.stderr.strip()
    except (subprocess.SubprocessError, OSError, ValueError, IndexError) as e:
        return False, str(e)


def execute_git_discard_path(project_path: str, file_path: str) -> Tuple[bool, str]:
    """Descarta modificaciones en un archivo rastreado o elimina un archivo no rastreado."""
    full_path = os.path.join(project_path, file_path) if not os.path.isabs(file_path) else file_path
    try:
        proc_chk = subprocess.run(["git", "status", "--porcelain", "--", file_path], cwd=project_path, capture_output=True, text=True, timeout=5)
        out = proc_chk.stdout.strip()
        if out.startswith("??"):
            if os.path.isfile(full_path):
                os.remove(full_path)
                return True, f"Archivo no rastreado '{file_path}' eliminado."
            elif os.path.isdir(full_path):
                shutil.rmtree(full_path)
                return True, f"Directorio no rastreado '{file_path}' eliminado."

        proc = subprocess.run(["git", "restore", "--", file_path], cwd=project_path, capture_output=True, text=True, timeout=10)
        if proc.returncode == 0:
            return True, f"Cambios en '{file_path}' descartados."
        proc2 = subprocess.run(["git", "checkout", "--", file_path], cwd=project_path, capture_output=True, text=True, timeout=10)
        if proc2.returncode == 0:
            return True, f"Cambios en '{file_path}' descartados."
        return False, proc.stderr.strip() or proc2.stderr.strip()
    except (subprocess.SubprocessError, OSError, ValueError, IndexError) as e:
        return False, str(e)


def execute_git_stash_pop(project_path: str) -> Tuple[bool, str]:
    """Aplica y extrae el stash más reciente (git stash pop)."""
    try:
        proc = subprocess.run(["git", "stash", "pop"], cwd=project_path, capture_output=True, text=True, timeout=15)
        if proc.returncode == 0:
            return True, proc.stdout.strip() or "Stash restaurado exitosamente."
        return False, proc.stderr.strip() or proc.stdout.strip()
    except (subprocess.SubprocessError, OSError, ValueError, IndexError) as e:
        return False, str(e)


def execute_git_stash_save(project_path: str, message: str = "") -> Tuple[bool, str]:
    """Guarda los cambios locales actuales en un nuevo stash."""
    cmd = ["git", "stash", "push", "--include-untracked"]
    if message.strip():
        cmd.extend(["-m", message.strip()])
    try:
        proc = subprocess.run(cmd, cwd=project_path, capture_output=True, text=True, timeout=15)
        if proc.returncode == 0:
            return True, proc.stdout.strip() or "Cambios guardados en stash correctamente."
        return False, proc.stderr.strip() or proc.stdout.strip()
    except (subprocess.SubprocessError, OSError, ValueError, IndexError) as e:
        return False, str(e)


def execute_git_init(project_path: str, initial_branch: str = "main", create_gitignore: bool = True) -> Tuple[bool, str]:
    """Inicializa un nuevo repositorio Git en la ruta especificada."""
    if not project_path or not os.path.isdir(project_path):
        return False, "La ruta del proyecto no existe o no es un directorio válido."

    git_dir = os.path.join(project_path, ".git")
    if os.path.exists(git_dir):
        return False, "El proyecto ya contiene un repositorio Git inicializado (.git)."

    try:
        # Intentar git init -b <initial_branch>
        res = subprocess.run(["git", "init", "-b", initial_branch], cwd=project_path, capture_output=True, text=True, timeout=10)
        if res.returncode != 0:
            # Fallback en caso de git anterior a 2.28
            res = subprocess.run(["git", "init"], cwd=project_path, capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                subprocess.run(["git", "checkout", "-b", initial_branch], cwd=project_path, capture_output=True, text=True, timeout=5)

        if res.returncode != 0:
            return False, f"Error al ejecutar git init: {res.stderr.strip()}"

        # Crear plantilla de .gitignore si se solicita y no existe
        gitignore_path = os.path.join(project_path, ".gitignore")
        if create_gitignore and not os.path.exists(gitignore_path):
            with open(gitignore_path, "w", encoding="utf-8") as f:
                f.write(
                    "# Entornos y dependencias\n"
                    "__pycache__/\n"
                    "*.py[cod]\n"
                    ".venv/\n"
                    "venv/\n"
                    "node_modules/\n"
                    ".env\n"
                    "*.log\n"
                    ".DS_Store\n"
                    ".idea/\n"
                    ".vscode/\n"
                )

        return True, f"Repositorio Git inicializado con éxito en rama '{initial_branch}'."
    except Exception as e:
        return False, f"Excepción durante git init: {str(e)}"
