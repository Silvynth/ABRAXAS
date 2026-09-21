#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS | SEMANTIC VERSION MANAGER & AUTO-BUMPER
# =====================================================================

import os
import sys
import subprocess
import re

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION_FILE = os.path.join(ROOT_DIR, "VERSION")

C_GOLD = '\033[38;2;230;166;200m'
C_GREEN = '\033[38;2;143;208;184m'
C_ACCENT = '\033[38;2;175;162;216m'
C_AMBER = '\033[38;2;217;184;116m'
C_DIM = '\033[38;2;200;185;202m'
C_TEXT = '\033[38;2;238;231;240m'
RESET = '\033[0m'

def get_current_version():
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, "r", encoding="utf-8") as f:
            v = f.read().strip()
            if v:
                return v
    return "0.1.0"

def parse_semver(version_str):
    # Match MAJOR.MINOR.PATCH with optional pre-release tag
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9.-]+))?$", version_str)
    if not match:
        return 0, 1, 0, ""
    major, minor, patch = int(match.group(1)), int(match.group(2)), int(match.group(3))
    tag = match.group(4) or ""
    return major, minor, patch, tag

def detect_bump_type_from_git():
    """Analiza el mensaje del último commit de git para deducir el tipo de cambio"""
    try:
        msg = subprocess.check_output(
            ["git", "log", "-1", "--pretty=%B"], 
            cwd=ROOT_DIR, 
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
    except Exception:
        msg = ""

    # Reglas Conventional Commits:
    # 1. Major
    if "BREAKING CHANGE" in msg or "feat!:" in msg or "fix!:" in msg or "[major]" in msg.lower():
        return "major", msg

    # 2. Minor
    if re.search(r"^(feat|feature)(\(.*\))?:", msg, re.IGNORECASE) or "[minor]" in msg.lower():
        return "minor", msg

    # 3. Patch (Default para fix, refactor, style, docs, chore o texto normal)
    return "patch", msg

def calculate_next_version(current_str, bump_type):
    major, minor, patch, _ = parse_semver(current_str)
    
    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    else:  # patch
        return f"{major}.{minor}.{patch + 1}"

def write_version(new_version):
    with open(VERSION_FILE, "w", encoding="utf-8") as f:
        f.write(f"{new_version}\n")
    dot_v = os.path.join(ROOT_DIR, ".version")
    try:
        with open(dot_v, "w", encoding="utf-8") as f:
            f.write(f"{new_version}\n")
    except OSError:
        pass

def install_git_hook():
    hooks_dir = os.path.join(ROOT_DIR, ".git", "hooks")
    if not os.path.exists(hooks_dir):
        print(f"  {C_AMBER}⚠️ No se encontró el directorio .git/hooks{RESET}")
        return

    pre_push_hook = os.path.join(hooks_dir, "pre-push")
    hook_script = f"""#!/usr/bin/env bash
# ABRAXAS Auto-Version Bump Hook
python3 "{os.path.join(ROOT_DIR, 'scripts', 'bump_version.py')}" --auto-hook
"""
    with open(pre_push_hook, "w", encoding="utf-8") as f:
        f.write(hook_script)
    os.chmod(pre_push_hook, 0o755)
    print(f"  {C_GREEN}✔ Git hook 'pre-push' instalado con éxito en: {pre_push_hook}{RESET}")

def main():
    args = sys.argv[1:]
    curr_v = get_current_version()

    if "--help" in args or "-h" in args:
        print(f"\n{C_GOLD}❖ ABRAXAS | Gestor de Versionado Semántico (SemVer) ❖{RESET}\n")
        print(f"  Uso: python3 scripts/bump_version.py [opciones | major | minor | patch]\n")
        print(f"  Opciones:")
        print(f"    --auto            Detecta automáticamente desde el último commit de Git (Default)")
        print(f"    patch             Incrementa PATCH (ej: 0.1.0 -> 0.1.1)")
        print(f"    minor             Incrementa MINOR (ej: 0.1.0 -> 0.2.0)")
        print(f"    major             Incrementa MAJOR (ej: 0.1.0 -> 1.0.0)")
        print(f"    --set <v>         Establece una versión específica (ej: --set 0.2.0)")
        print(f"    --install-hook    Instala un hook en .git/hooks/pre-push")
        print(f"    --dry-run         Simula el cambio sin escribir en disco")
        print(f"    --current         Muestra la versión actual\n")
        return

    if "--current" in args:
        print(curr_v)
        return

    if "--install-hook" in args:
        install_git_hook()
        return

    is_dry_run = "--dry-run" in args
    is_hook_mode = "--auto-hook" in args

    # Check for --set
    if "--set" in args:
        idx = args.index("--set")
        if idx + 1 < len(args):
            new_v = args[idx + 1]
            if not is_dry_run:
                write_version(new_v)
            print(f"  {C_GREEN}✔ Versión actualizada:{RESET} {curr_v} ➔ {C_GOLD}{new_v}{RESET}")
            return

    # Determine bump type
    bump_type = "patch"
    commit_reason = ""

    for a in args:
        if a.lower() in ["major", "minor", "patch"]:
            bump_type = a.lower()
            commit_reason = "Especificado manualmente por argumento"
            break

    if not commit_reason:
        detected_type, last_commit = detect_bump_type_from_git()
        bump_type = detected_type
        commit_reason = f"Commit: \"{last_commit}\"" if last_commit else "Regla por defecto (Patch)"

    next_v = calculate_next_version(curr_v, bump_type)

    if not is_dry_run:
        write_version(next_v)

    # Display output
    if not is_hook_mode:
        print(f"\n{C_GOLD}====================================================================={RESET}")
        print(f"  {C_GOLD}❖ ABRAXAS | INCREMENTO DE VERSIÓN SEMÁNTICA ❖{RESET}")
        print(f"{C_GOLD}====================================================================={RESET}\n")
        print(f"  • Versión actual:      {C_DIM}{curr_v}{RESET}")
        print(f"  • Tipo de incremento:  {C_ACCENT}{bump_type.upper()}{RESET} ({commit_reason})")
        print(f"  • Nueva versión:       {C_GREEN}{next_v}{RESET}\n")
        if is_dry_run:
            print(f"  {C_AMBER}🧪 [DRY-RUN] No se modificó el archivo VERSION.{RESET}\n")
        else:
            print(f"  {C_GREEN}✔ Archivo VERSION actualizado correctamente.{RESET}\n")

if __name__ == "__main__":
    main()
