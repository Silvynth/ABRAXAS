#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS CORE | GIT WORKFLOW & IA COMMIT ENGINE (PROTOCOLO ARTEMIS)
# =====================================================================

import os
import re
import subprocess
from typing import Tuple, Dict, Any

from core.engine import AbraxasConfig
from core.ai import get_configured_model, get_model_skill, generate_with_model


def get_project_semver(project_path: str) -> str:
    """Detecta la versión SemVer del proyecto según los protocolos de ABRAXAS."""
    if not project_path or not os.path.isdir(project_path):
        return "v0.1.0"

    # 1. Archivo .version o VERSION en la raíz de git
    for fname in [".version", "VERSION"]:
        fpath = os.path.join(project_path, fname)
        if os.path.isfile(fpath):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    ver = f.read().strip().split()[0]
                    if ver:
                        return f"v{ver.lstrip('vV')}"
            except Exception:
                pass

    # 2. Tag más reciente en Git
    try:
        tag = subprocess.check_output(
            ["git", "describe", "--tags", "--abbrev=0"],
            cwd=project_path,
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
        if tag:
            return f"v{tag.lstrip('vV')}"
    except Exception:
        pass

    # 3. Tag en el historial de commits [vX.Y.Z]
    try:
        log_out = subprocess.check_output(
            ["git", "log", "--format=%s", "-n", "30"],
            cwd=project_path,
            stderr=subprocess.DEVNULL,
            text=True
        )
        match = re.search(r"\[v?(\d+\.\d+\.\d+)\]", log_out)
        if match:
            return f"v{match.group(1)}"
    except Exception:
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
    except Exception:
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
            match = re.search(r"(?:HEX|SIL|HEN|AGY):(\d{4})", line)
            if match:
                num = int(match.group(1))
                return f"{num + 1:04d}"
    except Exception:
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
    except Exception:
        return ""


def generate_ia_commit_proposal(
    project_path: str, 
    model_type: str, 
    impact_type: str, 
    target_ver: str, 
    config_path: str = None
) -> Dict[str, Any]:
    """Genera la propuesta de commit estructurada usando Ollama y las directivas de Artemis."""
    diff = get_git_staged_diff(project_path)
    if not diff.strip():
        raise RuntimeError("El área de preparación (stage) está vacía. Ejecuta 'Add' primero.")

    model_name = get_configured_model(model_type, config_path)
    system_prompt = get_model_skill(model_type, config_path)
    
    id_prefix = "HEX" if model_type == "light" else "HEN"
    next_id = get_next_commit_seq(project_path)

    # Inyección de directiva de contexto de impacto (Protocolo Artemis)
    context_hint = ""
    if impact_type == "GAMMA":
        context_hint = f"\n[CLASIFICACIÓN DE IMPACTO: GAMMA (Patch / Corrección puntual / {target_ver})]. El operador ha clasificado este cambio como un parche o corrección menor. Tu título y descripción deben ser concisos y enfocarse directamente en el fix o ajuste técnico puntual sin sobredimensionar el cambio."
    elif impact_type == "BETA":
        context_hint = f"\n[CLASIFICACIÓN DE IMPACTO: BETA (Minor / Nuevo Módulo o Funcionalidad / {target_ver})]. El operador ha clasificado este cambio como una nueva funcionalidad o módulo. Tu título y descripción deben destacar las nuevas capacidades y el componente funcional creado."
    elif impact_type == "ALPHA":
        context_hint = f"\n[CLASIFICACIÓN DE IMPACTO: ALPHA (Major / Gran Cambio Estructural / {target_ver})]. El operador ha clasificado este cambio como una evolución o reestructuración mayor de arquitectura. Tu título y descripción deben reflejar la escala global de los cambios."

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

    # Quitar cualquier prefijo residual tipo HEX:0024 | o [v0.4.5] que el modelo haya añadido
    title = re.sub(r"^(?:HEX|SIL|HEN|AGY):\d{4}(?:\s*\[v?[0-9.]+\])?\s*\|\s*", "", title, flags=re.IGNORECASE).strip()
    if not title:
        title = "Actualización de componentes del sistema"

    # Failsafe de longitud: máximo 8 palabras y 50 caracteres
    words = title.split()
    if len(words) > 8:
        title = " ".join(words[:8]) + "..."
    if len(title) > 50:
        title = title[:47] + "..."

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
    if target_ver and impact_type != "OMIT":
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
    except Exception:
        pass
    try:
        email = subprocess.check_output(["git", "config", "user.email"], cwd=project_path, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
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
        except Exception:
            pass

    if not name or not email:
        try:
            from core.setup import detect_git_identity
            det_n, det_e = detect_git_identity()
            if not name:
                name = det_n
            if not email:
                email = det_e
        except Exception:
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
        # 1. Si hay cambio de versión, actualizar archivo .version
        if impact_type != "OMIT" and target_ver:
            v_file = os.path.join(project_path, ".version")
            with open(v_file, "w", encoding="utf-8") as f:
                f.write(f"{target_ver.lstrip('vV')}\n")
            subprocess.run(["git", "add", ".version"], cwd=project_path, check=False)

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

        # 3. Crear Git Tag
        if impact_type != "OMIT" and target_ver:
            cmd_tag = ["git", "tag", "-a", target_ver, "-m", f"Release {target_ver}: {full_title}"]
            tag_proc = subprocess.run(cmd_tag, cwd=project_path, capture_output=True, text=True, timeout=10)
            if tag_proc.returncode != 0:
                # Fallback sin -a si falla
                subprocess.run(["git", "tag", target_ver], cwd=project_path, check=False)

        return True, proc.stdout.strip()
    except Exception as e:
        return False, str(e)


# =====================================================================
# PROTOCOLO ARTEMIS: GESTIÓN Y MATRIZ TÁCTICA DE RAMAS
# =====================================================================

def get_git_branches_matrix(project_path: str) -> Dict[str, Any]:
    """
    Obtiene y clasifica la matriz completa de ramas (locales y remotas) según el Protocolo Artemis.
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
    except Exception:
        current_branch = ""

    fmt = "%(refname)|%(refname:short)|%(upstream:track)|%(upstream:short)|%(authorname)|%(authordate:relative)"
    try:
        raw_output = subprocess.check_output(
            ["git", "for-each-ref", f"--format={fmt}", "refs/heads/", "refs/remotes/"],
            cwd=project_path, stderr=subprocess.DEVNULL, text=True
        )
    except Exception:
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
    except Exception:
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
    except Exception as e:
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
    except Exception as e:
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
    except Exception as e:
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
    except Exception as e:
        return False, str(e)


