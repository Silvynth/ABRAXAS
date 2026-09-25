#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS DOCTOR | DIAGNÓSTICO DE SALUD DEL SISTEMA (LUMEN & NEOS)
# =====================================================================

import os
import sys
import subprocess
import shutil
import urllib.request
import json

# Asegurar que el directorio raíz del proyecto esté en el path de importación
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from abraxas.core.paths import TEMPLATE_PATH
from abraxas import get_version

C_GOLD = '\x1b[38;2;230;166;200m'
C_GREEN = '\x1b[38;2;143;208;184m'
C_WARN = '\x1b[38;2;240;138;155m'
C_CYAN = '\x1b[38;2;124;206;217m'
C_DIM = '\x1b[38;2;200;185;202m'
C_TEXT = '\x1b[38;2;238;231;240m'
BOLD = '\x1b[1m'
RESET = '\x1b[0m'

def print_section_header(title: str):
    print(f"\n  {C_CYAN}── {BOLD}{title}{RESET} {C_CYAN}─────────────────────────────────────────{RESET}")

def check_item(title: str, ok: bool, detail_ok: str, detail_warn: str, optional: bool = False):
    if ok:
        badge = f"{C_GREEN}[✔ OK]{RESET}"
        detail = detail_ok
    else:
        badge = f"{C_DIM}[○ Opcional]{RESET}" if optional else f"{C_WARN}[⚠️ ATENCIÓN]{RESET}"
        detail = detail_warn
    print(f"  {badge} {C_TEXT}{title:<34}{RESET} {C_DIM}{detail}{RESET}")
    return ok

def run_doctor():
    version = get_version()
    title_line = f"❖ ABRAXAS DOCTOR (v{version}) — DIAGNÓSTICO INTEGRAL"
    print(f"\n  {C_GOLD}╭─────────────────────────────────────────────────────────────────╮{RESET}")
    print(f"  {C_GOLD}│{RESET}  {title_line:<63}{C_GOLD}│{RESET}")
    print(f"  {C_GOLD}╰─────────────────────────────────────────────────────────────────╯{RESET}")

    # =================================================================
    # 1. PLATAFORMA Y ENTORNO BASE
    # =================================================================
    print_section_header("SISTEMA BASE Y ENTORNO GRÁFICO")

    py_v = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    py_ok = sys.version_info >= (3, 10)
    check_item("Intérprete Python", py_ok, f"v{py_v} (Compatible)", f"v{py_v} (Se requiere 3.10+)")

    pyside_ok = False
    pyside_ver = ""
    try:
        import PySide6
        pyside_ok = True
        pyside_ver = getattr(PySide6, "__version__", "Instalado")
    except ImportError:
        pass
    check_item("Librería GUI (PySide6)", pyside_ok, f"v{pyside_ver}", "No instalado (modo CLI únicamente)")

    from abraxas.core.setup import get_target_config_path
    cfg_file = get_target_config_path()
    cfg_ok = os.path.exists(cfg_file) or os.path.exists(TEMPLATE_PATH)
    cfg_label = os.path.basename(cfg_file) if os.path.exists(cfg_file) else "config.default.toml"
    check_item("Archivo de Configuración", cfg_ok, f"Activo ({cfg_label})", "No se encontró config.toml")

    snapper_ok = shutil.which("snapper") is not None
    check_item("Motor Btrfs (Snapper)", snapper_ok, "Disponible para snapshots", "Snapper no instalado", optional=True)

    # =================================================================
    # 2. SECTOR 1: PROTOCOLO GIT & GITHUB
    # =================================================================
    print_section_header("SECTOR 1 : PROTOCOLO GIT & GITHUB")

    git_bin = shutil.which("git")
    git_ok = git_bin is not None
    git_ver = ""
    if git_ok:
        try:
            git_ver = subprocess.check_output(["git", "--version"], text=True).strip().replace("git version ", "")
        except Exception:
            git_ver = "Detectado"
    check_item("Control de Versiones (Git)", git_ok, f"v{git_ver}", "Git no está instalado")

    # Identidad Git
    g_user = ""
    g_email = ""
    try:
        g_user = subprocess.check_output(["git", "config", "--get", "user.name"], text=True, stderr=subprocess.DEVNULL).strip()
        g_email = subprocess.check_output(["git", "config", "--get", "user.email"], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        pass
    id_ok = bool(g_user and g_email)
    id_detail = f"{g_user} <{g_email}>" if id_ok else "Falta configurar user.name o user.email"
    check_item("Identidad Git Global", id_ok, id_detail, id_detail, optional=False)

    gh_bin = shutil.which("gh")
    gh_ok = gh_bin is not None
    gh_status = "No instalado (GitHub CLI)"
    if gh_ok:
        try:
            proc = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True, timeout=2)
            if proc.returncode == 0:
                gh_status = "Instalado y Autenticado"
            else:
                gh_status = "Instalado (Sin autenticar: 'gh auth login')"
        except Exception:
            gh_status = "Instalado en PATH"
    check_item("GitHub CLI (gh)", gh_ok, gh_status, gh_status, optional=True)

    # =================================================================
    # 3. SECTOR 2 : ENTORNOS, DOCKER & PUERTOS
    # =================================================================
    print_section_header("SECTOR 2 : ENTORNOS, DOCKER & RUN")

    from abraxas.core.environments import detect_installed_editors, get_preferred_editor
    editors = detect_installed_editors()
    pref_editor = get_preferred_editor()
    ed_ok = len(editors) > 0
    ed_detail = f"{len(editors)} detectados (Preferido: {pref_editor or editors[0]['name']})" if ed_ok else "No se detectó ningún editor (VS Code, Cursor, Zed...)"
    check_item("Editores de Código", ed_ok, ed_detail, ed_detail, optional=False)

    uv_ok = shutil.which("uv") is not None
    check_item("Acelerador Python (uv)", uv_ok, "Instalado (10x venv ultrarrápido)", "No instalado (usará venv estándar)", optional=True)

    # Docker
    docker_bin = shutil.which("docker")
    docker_ok = docker_bin is not None
    docker_msg = "No instalado"
    if docker_ok:
        try:
            d_proc = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=2)
            if d_proc.returncode == 0:
                docker_msg = "Demonio activo y permisos correctos"
            else:
                docker_msg = "Instalado pero demonio detenido o falta grupo docker"
        except Exception:
            docker_msg = "Instalado en PATH"
    check_item("Plataforma Docker", docker_ok, docker_msg, docker_msg, optional=True)

    # Docker Compose
    compose_ok = False
    compose_msg = "No disponible"
    if docker_ok:
        try:
            c_proc = subprocess.run(["docker", "compose", "version"], capture_output=True, text=True, timeout=2)
            if c_proc.returncode == 0:
                compose_ok = True
                compose_msg = c_proc.stdout.strip().splitlines()[0]
        except Exception:
            pass
    if not compose_ok and shutil.which("docker-compose"):
        compose_ok = True
        compose_msg = "docker-compose (standalone)"
    check_item("Docker Compose", compose_ok, compose_msg, compose_msg, optional=True)

    # Herramienta de puertos (lsof o ss)
    has_lsof = shutil.which("lsof") is not None
    has_ss = shutil.which("ss") is not None
    port_tool_ok = has_lsof or has_ss
    port_tool_msg = f"{'lsof (Primario)' if has_lsof else ''}{' + ss (Fallback)' if has_lsof and has_ss else ('ss (Fallback)' if has_ss else '')}"
    check_item("Auditoría Puertos TCP", port_tool_ok, port_tool_msg, "Ni lsof ni ss encontrados", optional=True)

    # =================================================================
    # 4. SECTOR 3 : HERRAMIENTAS & UTILIDADES IA
    # =================================================================
    print_section_header("SECTOR 3 : HERRAMIENTAS & IA LOCAL")

    from abraxas.core.utilities import check_ollama_status
    ol_stat = check_ollama_status()
    ol_ok = ol_stat.get("online", False)
    models_cnt = len(ol_stat.get("models", []))
    if ol_ok:
        ol_detail = f"En línea (:11434) — {models_cnt} modelos disponibles"
    else:
        ol_detail = "Ollama inactivo o sin conexión (http://localhost:11434)"
    check_item("Motor IA Local (Ollama)", ol_ok, ol_detail, ol_detail, optional=True)

    obsidian_ok = shutil.which("obsidian") is not None
    check_item("Bóveda Obsidian (Markdown)", obsidian_ok, "Instalado en PATH", "No instalado (opcional)", optional=True)

    print(f"\n  {C_GOLD}================================================================={RESET}")
    print(f"  {C_GREEN}✨ Diagnóstico completado. El núcleo de ABRAXAS está operativo.{RESET}\n")

if __name__ == "__main__":
    run_doctor()
