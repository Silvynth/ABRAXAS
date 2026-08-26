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
    """Detecta la versión SemVer del proyecto según los protocolos de Artemis/YoRHa."""
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

        # 2. Ejecutar git commit
        full_title = f"{commit_header} | {title}"
        cmd_commit = ["git", "commit", "-m", full_title, "-m", body]
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
