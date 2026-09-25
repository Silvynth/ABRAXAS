#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS CORE | SECTOR 3: UTILIDADES, GITIGNORE, DOCS & IA
# =====================================================================

import os
import re
import json
import subprocess
import urllib.request
import urllib.error
from typing import List, Dict, Tuple, Optional
from abraxas.core.ai import generate_with_model, audit_git_diff, get_configured_model
from abraxas.core.engine import AbraxasConfig


# =====================================================================
# 1. GESTIÓN DE .GITIGNORE Y ARCHIVOS DE ENTORNO (.ENV)
# =====================================================================

GITIGNORE_PRESETS = {
    "python": [
        "__pycache__/", "*.py[cod]", "*$py.class",
        ".venv/", "venv/", "env/", "ENV/",
        "build/", "dist/", "*.egg-info/",
        ".pytest_cache/", ".mypy_cache/", ".ruff_cache/",
        ".coverage", "htmlcov/", ".env"
    ],
    "node": [
        "node_modules/", "npm-debug.log*", "yarn-debug.log*",
        "yarn-error.log*", ".pnpm-debug.log*", "dist/", "build/",
        ".next/", ".nuxt/", "out/", ".cache/",
        ".env", ".env.local", "coverage/"
    ],
    "ide": [
        ".vscode/", ".idea/", "*.swp", "*.swo", "*~",
        ".DS_Store", "Thumbs.db", "*.log", "tmp/", "*.bak"
    ],
    "security": [
        ".env", ".env.local", ".env.*.local",
        "*.pem", "*.key", "*.crt", "secrets/", "credentials.json",
        "id_rsa", "id_ed25519"
    ]
}


def inspect_gitignore_and_env(project_path: str) -> Dict:
    """
    Inspecciona el estado de .gitignore y archivos de entorno (.env) en el proyecto.
    """
    gitignore_path = os.path.join(project_path, ".gitignore")
    env_path = os.path.join(project_path, ".env")
    example_path = os.path.join(project_path, ".env.example")

    has_gitignore = os.path.exists(gitignore_path)
    rules = []
    env_is_ignored = False

    if has_gitignore:
        try:
            with open(gitignore_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped and not stripped.startswith("#"):
                        rules.append(stripped)
                        if stripped in (".env", ".env*", "*.env"):
                            env_is_ignored = True
        except OSError:
            pass

    has_env = os.path.exists(env_path)
    has_example = os.path.exists(example_path)

    env_vars_count = 0
    if has_env:
        try:
            with open(env_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line_s = line.strip()
                    if line_s and not line_s.startswith("#") and "=" in line_s:
                        env_vars_count += 1
        except OSError:
            pass

    return {
        "has_gitignore": has_gitignore,
        "gitignore_path": gitignore_path,
        "rules_count": len(rules),
        "rules": rules,
        "has_env": has_env,
        "env_path": env_path,
        "env_vars_count": env_vars_count,
        "env_is_ignored": env_is_ignored,
        "has_example": has_example,
        "has_env_example": has_example,
        "example_path": example_path
    }


def apply_gitignore_preset(project_path: str, preset_type: str) -> Tuple[bool, str, int]:
    """
    Aplica una plantilla predefinida a .gitignore sin duplicar reglas existentes.
    """
    if not project_path or not os.path.exists(project_path):
        return False, "Ruta de proyecto no válida.", 0

    gitignore_path = os.path.join(project_path, ".gitignore")
    existing_rules = set()

    if os.path.exists(gitignore_path):
        try:
            with open(gitignore_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    r = line.strip()
                    if r:
                        existing_rules.add(r)
        except OSError as e:
            return False, f"Error al leer .gitignore: {e}", 0

    target_rules = []
    if preset_type == "all":
        for p_rules in GITIGNORE_PRESETS.values():
            for r in p_rules:
                if r not in target_rules:
                    target_rules.append(r)
    elif preset_type in GITIGNORE_PRESETS:
        target_rules = GITIGNORE_PRESETS[preset_type]
    else:
        return False, f"Preset '{preset_type}' no reconocido.", 0

    to_add = [r for r in target_rules if r not in existing_rules]
    if not to_add:
        return True, f"Todas las reglas del preset '{preset_type}' ya estaban presentes.", 0

    try:
        mode = "a" if os.path.exists(gitignore_path) else "w"
        with open(gitignore_path, mode, encoding="utf-8") as f:
            if mode == "a":
                f.write(f"\n# --- Preset aplicado: {preset_type.upper()} ---\n")
            else:
                f.write(f"# Archivo .gitignore generado por ABRAXAS (Preset: {preset_type.upper()})\n")
            for r in to_add:
                f.write(f"{r}\n")
        return True, f"Se agregaron {len(to_add)} regla(s) a .gitignore.", len(to_add)
    except OSError as e:
        return False, f"Error al escribir en .gitignore: {e}", 0


def add_custom_gitignore_rule(project_path: str, rule: str) -> Tuple[bool, str]:
    """Agrega una regla personalizada a .gitignore si no existe."""
    clean_rule = rule.strip()
    if not clean_rule:
        return False, "Regla vacía."
    gitignore_path = os.path.join(project_path, ".gitignore")
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = [l.strip() for l in f if l.strip()]
            if clean_rule in lines:
                return True, f"La regla '{clean_rule}' ya existe en .gitignore."
    try:
        with open(gitignore_path, "a", encoding="utf-8") as f:
            f.write(f"\n{clean_rule}\n")
        return True, f"Regla '{clean_rule}' añadida exitosamente."
    except OSError as e:
        return False, f"Error al guardar regla: {e}"


def create_base_env_file(project_path: str) -> Tuple[bool, str]:
    """Crea un archivo .env inicial seguro y asegura su exclusión en .gitignore."""
    env_path = os.path.join(project_path, ".env")
    if os.path.exists(env_path):
        return False, "El archivo .env ya existe en el proyecto."

    # Asegurar .env en .gitignore
    add_custom_gitignore_rule(project_path, ".env")
    add_custom_gitignore_rule(project_path, ".env.*.local")

    content = (
        "# =====================================================================\n"
        "#  ❖ ABRAXAS | ARCHIVO DE CONFIGURACIÓN LOCAL (.ENV)\n"
        "#  ⚠️ ADVERTENCIA: NUNCA SUBIR ESTE ARCHIVO AL REPOSITORIO GIT\n"
        "# =====================================================================\n\n"
        "APP_ENV=development\n"
        "DEBUG=true\n"
        "PORT=8000\n"
        "SECRET_KEY=your_secure_random_key_here\n"
    )
    try:
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True, "Archivo .env creado y blindado en .gitignore."
    except OSError as e:
        return False, f"Error al crear .env: {e}"


def generate_env_example_file(project_path: str) -> Tuple[bool, str]:
    """Genera .env.example anonimizando los valores del .env actual."""
    env_path = os.path.join(project_path, ".env")
    example_path = os.path.join(project_path, ".env.example")
    if not os.path.exists(env_path):
        return False, "No existe un archivo .env para generar la plantilla."

    example_lines = [
        "# =====================================================================\n",
        "#  ❖ ABRAXAS | PLANTILLA DE ENTORNO (.ENV.EXAMPLE)\n",
        "#  ✅ SEGURO PARA PUBLICAR EN GITHUB / REPOSITORIOS PÚBLICOS\n",
        "# =====================================================================\n\n"
    ]
    try:
        with open(env_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line_s = line.strip()
                if not line_s or line_s.startswith("#"):
                    example_lines.append(line)
                elif "=" in line_s:
                    var_name = line_s.split("=", 1)[0].strip()
                    example_lines.append(f"{var_name}=your_{var_name.lower()}_here\n")
                else:
                    example_lines.append(line)

        with open(example_path, "w", encoding="utf-8") as f:
            f.writelines(example_lines)
        return True, "Plantilla .env.example generada correctamente."
    except OSError as e:
        return False, f"Error al generar .env.example: {e}"


# =====================================================================
# 2. LECTOR DE DOCUMENTACIÓN & MARKDOWN
# =====================================================================

DOC_IGNORED_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__",
    ".pytest_cache", ".idea", ".vscode", "dist", "build", ".next", ".cache"
}

def scan_project_documentation(project_path: str) -> List[Dict]:
    """
    Rastrea recursivamente archivos Markdown, READMEs, CHANGELOGs y licencias en el proyecto.
    """
    docs = []
    if not project_path or not os.path.exists(project_path):
        return docs

    doc_pattern = re.compile(r"^(readme.*|changelog.*|contributing.*|license.*|.*\.md$)", re.IGNORECASE)

    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in DOC_IGNORED_DIRS and not d.startswith(".")]
        for file in files:
            if doc_pattern.match(file):
                abs_p = os.path.join(root, file)
                rel_p = os.path.relpath(abs_p, project_path)
                try:
                    size = os.path.getsize(abs_p)
                except OSError:
                    size = 0
                docs.append({
                    "name": file,
                    "relative": rel_p,
                    "rel_path": rel_p,
                    "path": abs_p,
                    "size": size,
                    "size_kb": round(size / 1024, 1),
                    "is_readme": "readme" in file.lower()
                })

    docs.sort(key=lambda x: (not x["is_readme"], x["relative"].lower()))
    return docs


def read_markdown_file(file_path: str) -> str:
    """Lee el contenido en texto plano de un archivo de documentación."""
    if not file_path or not os.path.exists(file_path):
        return ""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception as e:
        return f"Error al leer archivo: {e}"


def generate_ai_changelog(project_path: str, count: int = 15) -> Tuple[bool, str]:
    """Genera una propuesta de CHANGELOG.md usando el historial reciente de commits con IA."""
    try:
        log_out = subprocess.check_output(
            ["git", "log", f"-n {count}", "--pretty=format:%h - %s (%an, %ar)"],
            cwd=project_path,
            stderr=subprocess.DEVNULL,
            text=True
        )
    except Exception as e:
        return False, f"Error al obtener historial git: {e}"

    if not log_out.strip():
        return False, "No hay historial de commits suficiente."

    prompt = (
        f"A partir del siguiente historial de commits de Git, redacta un CHANGELOG.md profesional en Markdown:\n\n"
        f"{log_out}\n\n"
        f"Instrucciones estrictas:\n"
        f"- Agrupa por secciones: '🚀 Nuevas Características', '🐛 Correcciones de Errores', '🛠️ Mejoras y Refactor'.\n"
        f"- Redacta en español formal y conciso.\n"
        f"- No inventes cambios que no figuren en los commits."
    )
    system_prompt = "Eres un documentador técnico de software del sistema ABRAXAS. Produce salidas limpias en Markdown."
    try:
        res = generate_with_model(prompt, model_type="chat", system_prompt=system_prompt)
        return True, res
    except Exception as e:
        return False, f"Error al contactar IA de Ollama: {e}"


# =====================================================================
# 3. UTILIDADES IA & AUDITORÍA DE HISTORIAL
# =====================================================================

def check_ollama_status(config_path: str = None) -> Dict:
    """Verifica el estado del servicio local Ollama y sus modelos instalados."""
    cfg = AbraxasConfig(config_path)
    endpoint = cfg.get("ai.endpoint", "http://localhost:11434").rstrip("/")
    light_cfg = cfg.get("ai.light_model", "qwen2.5-coder:7b")
    heavy_cfg = cfg.get("ai.heavy_model", "qwen2.5-coder:14b")

    try:
        req = urllib.request.Request(f"{endpoint}/api/tags")
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = [m.get("name", "") for m in data.get("models", [])]
            return {
                "running": True,
                "online": True,
                "endpoint": endpoint,
                "models": models,
                "models_count": len(models),
                "light_model": light_cfg,
                "heavy_model": heavy_cfg
            }
    except Exception as e:
        return {
            "running": False,
            "online": False,
            "endpoint": endpoint,
            "models": [],
            "models_count": 0,
            "error": str(e),
            "light_model": light_cfg,
            "heavy_model": heavy_cfg
        }


def execute_history_ai_audit(project_path: str, commit_count: int = 5, model_choice: str = "light") -> Tuple[bool, str]:
    """Ejecuta una auditoría de código con IA sobre los últimos N commits acumulados."""
    try:
        diff_out = subprocess.check_output(
            ["git", "diff", f"HEAD~{commit_count}"],
            cwd=project_path,
            stderr=subprocess.DEVNULL,
            text=True
        )
    except Exception as e:
        # Fallback a git diff de cambios actuales o HEAD~1 si no hay tantos commits
        try:
            diff_out = subprocess.check_output(
                ["git", "diff", "HEAD~1"],
                cwd=project_path,
                stderr=subprocess.DEVNULL,
                text=True
            )
        except Exception:
            return False, f"No se pudo extraer el diff de los últimos commits: {e}"

    if not diff_out.strip():
        return False, "No hay diferencias en los últimos commits para auditar."

    try:
        audit_res = audit_git_diff(diff_out[:12000], model_type=model_choice)
        return True, audit_res
    except Exception as e:
        return False, f"Error al ejecutar auditoría IA: {e}"
