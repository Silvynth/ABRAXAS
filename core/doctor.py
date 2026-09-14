#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS DOCTOR | DIAGNÓSTICO DE SALUD DEL SISTEMA (v0.1.0)
# =====================================================================

import os
import sys
import subprocess
import shutil
import urllib.request
import json

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
from core import __version__

C_GOLD = '\x1b[38;2;230;166;200m'
C_GREEN = '\x1b[38;2;143;208;184m'
C_WARN = '\x1b[38;2;240;138;155m'
C_DIM = '\x1b[38;2;200;185;202m'
C_TEXT = '\x1b[38;2;238;231;240m'
RESET = '\x1b[0m'

def check_item(title, ok, detail_ok, detail_warn):
    badge = f"{C_GREEN}[✔ OK]{RESET}" if ok else f"{C_WARN}[⚠️ ATENCIÓN]{RESET}"
    detail = detail_ok if ok else detail_warn
    print(f"  {badge} {C_TEXT}{title:<32}{RESET} {C_DIM}{detail}{RESET}")
    return ok

def run_doctor():
    title_line = f"❖ ABRAXAS DOCTOR (v{__version__}) — DIAGNÓSTICO DEL SISTEMA"
    print(f"\n  {C_GOLD}╭─────────────────────────────────────────────────────────────────╮{RESET}")
    print(f"  {C_GOLD}│{RESET}  {title_line:<63}{C_GOLD}│{RESET}")
    print(f"  {C_GOLD}╰─────────────────────────────────────────────────────────────────╯{RESET}\n")

    # 1. Python Version
    py_v = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    py_ok = sys.version_info >= (3, 11)
    check_item("Entorno Python", py_ok, f"v{py_v} (Compatible)", f"v{py_v} (Se recomienda 3.11+)")

    # 2. Config TOML
    from core.setup import get_target_config_path
    cfg_file = get_target_config_path()
    template = os.path.join(ROOT_DIR, "config.default.toml")
    cfg_ok = os.path.exists(cfg_file) or os.path.exists(template)
    check_item("Archivo de Configuración", cfg_ok, f"Detectado ({os.path.basename(cfg_file)})", "No se encontró config.toml")

    # 3. Shell Tools
    fzf_ok = shutil.which("fzf") is not None
    check_item("Herramienta TUI (fzf)", fzf_ok, "Instalado en PATH", "No encontrado (paru -S fzf)")

    # 4. Snapper / Btrfs
    snapper_ok = shutil.which("snapper") is not None
    check_item("Motor Btrfs (Snapper)", snapper_ok, "Disponible", "Snapper no instalado")

    # 5. Ollama AI Engine
    ai_ok = False
    ai_msg = "Desconectado"
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(req, timeout=1.2) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            models = [m.get('name') for m in data.get('models', [])]
            ai_ok = True
            ai_msg = f"En línea ({len(models)} modelos detectados)"
    except Exception:
        ai_msg = "Servidor Ollama no activo en :11434"
    check_item("Motor de IA Local (Ollama)", ai_ok, ai_msg, ai_msg)

    print(f"\n  {C_DIM}Diagnóstico completado.{RESET}\n")

if __name__ == "__main__":
    run_doctor()
