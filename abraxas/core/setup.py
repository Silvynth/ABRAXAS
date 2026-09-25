#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS | CONFIGURATION MANAGER & INTERACTIVE SETUP WIZARD (CRUD)
# =====================================================================

import os
import sys
import shutil
import urllib.request
import json
import re
import subprocess

# TrueColor ANSI Palette (Noctalia Theme)
C_GOLD = '\x1b[38;2;230;166;200m'
C_PRIMARY = '\x1b[38;2;230;166;200m'
C_TEXT = '\x1b[38;2;238;231;240m'
C_WHITE = '\x1b[38;2;238;231;240m'
C_DIM = '\x1b[38;2;200;185;202m'
C_DARK = '\x1b[38;2;77;70;92m'
C_ACCENT = '\x1b[38;2;175;162;216m'
C_CYAN = '\x1b[38;2;124;206;217m'
C_GREEN = '\x1b[38;2;143;208;184m'
C_YELLOW = '\x1b[38;2;217;184;116m'
C_WARN = '\x1b[38;2;240;138;155m'
BOLD = '\x1b[1m'
RESET = '\x1b[0m'

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from abraxas.core.paths import ROOT_DIR, TEMPLATE_PATH, SKILLS_DIR

def get_target_config_path():
    user_cfg = os.path.expanduser("~/.config/abraxas/config.toml")
    repo_cfg = os.path.join(ROOT_DIR, "config.toml")
    if os.path.exists(user_cfg):
        return user_cfg
    return repo_cfg

def detect_git_identity():
    """Detecta nombre y correo desde git config o gh CLI."""
    name = ""
    email = ""
    try:
        name = subprocess.check_output(["git", "config", "--get", "user.name"], text=True, stderr=subprocess.DEVNULL).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    try:
        email = subprocess.check_output(["git", "config", "--get", "user.email"], text=True, stderr=subprocess.DEVNULL).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    if not name or not email:
        try:
            gh_user = subprocess.check_output(["gh", "api", "user"], text=True, stderr=subprocess.DEVNULL)
            data = json.loads(gh_user)
            if not name:
                name = data.get("name") or data.get("login") or ""
            if not email:
                email = data.get("email") or ""
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            pass

    if not email:
        try:
            gh_emails = subprocess.check_output(["gh", "api", "user/emails"], text=True, stderr=subprocess.DEVNULL)
            emails_data = json.loads(gh_emails)
            if isinstance(emails_data, list) and len(emails_data) > 0:
                primary = next((e.get("email") for e in emails_data if e.get("primary")), None)
                email = primary or emails_data[0].get("email", "")
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            pass

    return name, email

def sync_global_gitconfig(name: str, email: str):
    """Sincroniza el nombre y correo con git config --global."""
    if name:
        try:
            subprocess.run(["git", "config", "--global", "user.name", name], check=False)
        except (subprocess.CalledProcessError, OSError):
            pass
    if email:
        try:
            subprocess.run(["git", "config", "--global", "user.email", email], check=False)
        except (subprocess.CalledProcessError, OSError):
            pass

def read_toml_dict(filepath):
    """Lector TOML nativo simple para el esquema de Abraxas"""
    if not os.path.exists(filepath):
        return {}
    
    try:
        if sys.version_info >= (3, 11):
            import tomllib
            with open(filepath, "rb") as f:
                return tomllib.load(f)
    except (ImportError, OSError):
        pass

    # Parser fallback básico línea por línea
    data = {}
    current_section = data
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            l = line.strip()
            if not l or l.startswith("#"):
                continue
            if l.startswith("[") and l.endswith("]"):
                sec_name = l[1:-1]
                parts = sec_name.split(".")
                curr = data
                for p in parts:
                    if p not in curr:
                        curr[p] = {}
                    curr = curr[p]
                current_section = curr
            elif "=" in l:
                k, v = l.split("=", 1)
                k = k.strip()
                v = v.split("#")[0].strip()
                if v.startswith('"') and v.endswith('"'):
                    val = v[1:-1]
                elif v.lower() == "true":
                    val = True
                elif v.lower() == "false":
                    val = False
                elif v.isdigit():
                    val = int(v)
                else:
                    try:
                        val = float(v)
                    except ValueError:
                        val = v
                current_section[k] = val
    return data

def write_toml_dict(filepath, cfg):
    """Escritor TOML estructurado nativo y modular"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    lines = [
        "# =====================================================================",
        "#  ❖ ABRAXAS | CONFIGURACIÓN ACTIVA DEL SISTEMA",
        "# =====================================================================",
        "",
        "[abraxas]",
        f'schema_version = "{cfg.get("abraxas", {}).get("schema_version", "0.1.0")}"',
        f'theme = "{cfg.get("abraxas", {}).get("theme", "dark_cyberpunk")}"',
        "",
        "[paths]",
        f'projects_dir = "{cfg.get("paths", {}).get("projects_dir", "")}"',
        f'vault_dir = "{cfg.get("paths", {}).get("vault_dir", "")}"',
        "",
        "[git]",
        f'user_name = "{cfg.get("git", {}).get("user_name", "")}"',
        f'user_email = "{cfg.get("git", {}).get("user_email", "")}"',
        f'auto_sync_global = {str(cfg.get("git", {}).get("auto_sync_global", True)).lower()}',
        "",
        "[ai]",
        f'enabled = {str(cfg.get("ai", {}).get("enabled", False)).lower()}',
        f'provider = "{cfg.get("ai", {}).get("provider", "ollama")}"',
        f'endpoint = "{cfg.get("ai", {}).get("endpoint", "http://localhost:11434")}"',
        f'chat_model = "{cfg.get("ai", {}).get("chat_model", "")}"',
        f'heavy_model = "{cfg.get("ai", {}).get("heavy_model", "")}"',
        f'light_model = "{cfg.get("ai", {}).get("light_model", "")}"',
        f'temperature = {cfg.get("ai", {}).get("temperature", 0.2)}',
        "",
        "[ai.skills]",
        f'chat_skill_path = "{cfg.get("ai", {}).get("skills", {}).get("chat_skill_path", "skills/chat_skill.txt")}"',
        f'heavy_skill_path = "{cfg.get("ai", {}).get("skills", {}).get("heavy_skill_path", "skills/heavy_skill.txt")}"',
        f'light_skill_path = "{cfg.get("ai", {}).get("skills", {}).get("light_skill_path", "skills/light_skill.txt")}"',
        "",
        "[system]",
        f'btrfs_snapshots = {str(cfg.get("system", {}).get("btrfs_snapshots", False)).lower()}',
        f'snapper_config = "{cfg.get("system", {}).get("snapper_config", "root")}"',
        ""
    ]
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    # Proteger permisos a nivel usuario (chmod 600)
    try:
        os.chmod(filepath, 0o600)
    except OSError:
        pass

def prompt_input(label, default_val):
    print(f"  {C_TEXT}{label}{RESET}")
    print(f"  {C_DIM}Valor actual/defecto: [{default_val}]{RESET}")
    try:
        val = input(f"  {C_GOLD}>> {RESET}").strip()
        return val if val else default_val
    except (EOFError, KeyboardInterrupt):
        print(f"{default_val}")
        return default_val

def ensure_default_skills():
    """Genera archivos de directivas de comportamiento (vacíos por defecto) en skills/ si no existen."""
    skills_dir = SKILLS_DIR
    os.makedirs(skills_dir, exist_ok=True)
    for fname in ["chat_skill.txt", "heavy_skill.txt", "light_skill.txt"]:
        fpath = os.path.join(skills_dir, fname)
        if not os.path.exists(fpath):
            try:
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write("")
            except OSError:
                pass

def run_interactive_wizard(is_preview=False):
    cfg_target = get_target_config_path()
    
    # Cargar base desde plantilla o config existente
    base_cfg = read_toml_dict(cfg_target)
    if not base_cfg:
        base_cfg = read_toml_dict(TEMPLATE_PATH)

    print(f"\n  {C_GOLD}╭─────────────────────────────────────────────────────────────────╮{RESET}")
    if is_preview:
        print(f"  {C_GOLD}│{RESET}  {BOLD}❖ ABRAXAS | ASISTENTE INTERACTIVO [MODO SIMULACIÓN / PREVIEW] ❖{RESET} {C_GOLD}│{RESET}")
    else:
        print(f"  {C_GOLD}│{RESET}  {BOLD}❖ ABRAXAS | ASISTENTE INTERACTIVO DE CONFIGURACIÓN ❖{RESET}           {C_GOLD}│{RESET}")
    print(f"  {C_GOLD}╰─────────────────────────────────────────────────────────────────╯{RESET}\n")
    if is_preview:
        print(f"  {C_YELLOW}🧪 Modo Vista Previa activo: Puedes responder las preguntas sin que se guarde ningún cambio.{RESET}\n")
    else:
        print(f"  {C_DIM}Personaliza tus rutas y preferencias. Presiona Enter para mantener el defecto.{RESET}\n")

    # 1. Rutas
    print(f"  {C_ACCENT}📁 [1/4] RUTAS DE TRABAJO DEL USUARIO:{RESET}")
    proj_dir = prompt_input("Directorio raíz para tus Proyectos y Repositorios Git (LUMEN):", 
                            base_cfg.get("paths", {}).get("projects_dir", "~/Proyectos"))
    
    use_vault = prompt_input("¿Deseas integrar una Bóveda de Notas / Obsidian (NOUS)? (s/n):", "s")
    is_vault = use_vault.lower().startswith("s") or use_vault.lower().startswith("y")
    vault_dir = ""
    if is_vault:
        vault_dir = prompt_input("Directorio para tu Bóveda de Notas / Obsidian:", 
                               base_cfg.get("paths", {}).get("vault_dir", "~/Vault"))
                           
    use_btrfs = prompt_input("¿Tu disco raíz usa Btrfs y deseas activar Snapshots automáticos (UMBRA)? (s/n):", "s")
    is_btrfs = use_btrfs.lower().startswith("s") or use_btrfs.lower().startswith("y")
    snapper_cfg = base_cfg.get("system", {}).get("snapper_config", "root")
    if is_btrfs:
        snapper_cfg = prompt_input("Configuración/Perfil de Snapper:", snapper_cfg)

    if "paths" not in base_cfg: base_cfg["paths"] = {}
    base_cfg["paths"]["projects_dir"] = proj_dir
    base_cfg["paths"]["vault_dir"] = vault_dir

    if "system" not in base_cfg: base_cfg["system"] = {}
    base_cfg["system"]["btrfs_snapshots"] = is_btrfs
    base_cfg["system"]["snapper_config"] = snapper_cfg
    print("")

    # 2. Identidad Git & GitHub
    print(f"  {C_CYAN}🐙 [2/5] IDENTIDAD GIT Y CONTROL DE VERSIONES:{RESET}")
    def_name, def_email = detect_git_identity()
    if not def_name:
        def_name = base_cfg.get("git", {}).get("user_name", "")
    if not def_email:
        def_email = base_cfg.get("git", {}).get("user_email", "")
    
    git_name = prompt_input("Nombre de usuario para commits de Git (user.name):", def_name)
    git_email = prompt_input("Correo electrónico para commits de Git (user.email):", def_email)
    
    sync_choice = prompt_input("¿Sincronizar automáticamente con ~/.gitconfig global? (s/n):", "s")
    is_sync = sync_choice.lower().startswith("s") or sync_choice.lower().startswith("y")
    
    if "git" not in base_cfg: base_cfg["git"] = {}
    base_cfg["git"]["user_name"] = git_name
    base_cfg["git"]["user_email"] = git_email
    base_cfg["git"]["auto_sync_global"] = is_sync
    
    if not is_preview and is_sync and (git_name or git_email):
        sync_global_gitconfig(git_name, git_email)
    print("")

    # 3. Editor Preferido (LUMEN Sector 2)
    print(f"  {C_CYAN}💻 [3/6] EDITOR DE CÓDIGO PREFERIDO (LUMEN):{RESET}")
    from abraxas.core.environments import detect_installed_editors, get_preferred_editor, set_preferred_editor
    eds = detect_installed_editors()
    current_pref = get_preferred_editor()
    if eds:
        print("     Editores detectados en el sistema:")
        for idx, ed in enumerate(eds, 1):
            is_def = " (Actual)" if ed['id'] == current_pref else ""
            print(f"       {idx}) {ed['icon']} {ed['name']}{is_def}")
        print(f"       {len(eds)+1}) Otro / Comando personalizado")
        ed_choice = prompt_input(f"Selecciona un editor (1-{len(eds)+1}) [1]:", "1")
        try:
            ch_idx = int(ed_choice) - 1
            if 0 <= ch_idx < len(eds):
                chosen_ed = eds[ch_idx]['id']
            else:
                chosen_ed = prompt_input("Comando de tu editor:", "code")
        except ValueError:
            chosen_ed = prompt_input("Comando de tu editor:", "code")
    else:
        chosen_ed = prompt_input("Comando de tu editor preferido (ej. code, cursor, nvim):", "code")

    if "environments" not in base_cfg: base_cfg["environments"] = {}
    base_cfg["environments"]["preferred_editor"] = chosen_ed
    if not is_preview:
        set_preferred_editor(chosen_ed)
    print(f"  {C_GREEN}✔ Editor preferido fijado en: {chosen_ed}{RESET}\n")

    # 4. Hardware Profile
    print(f"  {C_CYAN}⚡ [4/6] PERFIL DE RENDIMIENTO Y HARDWARE:{RESET}")
    print(f"     1) Auto (Recomendado)")
    print(f"     2) Alto Rendimiento (Priorizar GPU / VRAM)")
    print(f"     3) Bajo Consumo (Optimizado para batería)")
    h_choice = prompt_input("Selecciona un perfil (1-3):", "1")
    h_map = {"1": "auto", "2": "high_performance", "3": "low_power"}
    if "hardware" not in base_cfg: base_cfg["hardware"] = {}
    base_cfg["hardware"]["profile"] = h_map.get(h_choice, "auto")
    print("")

    # 5. Inteligencia Artificial (Ollama)
    print(f"  {C_GOLD}🧠 [5/6] CONFIGURACIÓN DE IA LOCAL & MODELOS (OLLAMA):{RESET}")
    ai_choice = prompt_input("¿Deseas habilitar la asistencia con IA Local? (s/n):", "s")
    is_ai = ai_choice.lower().startswith("s") or ai_choice.lower().startswith("y")
    
    chat_m = base_cfg.get("ai", {}).get("chat_model", "")
    heavy_m = base_cfg.get("ai", {}).get("heavy_model", "")
    light_m = base_cfg.get("ai", {}).get("light_model", "")

    if is_ai:
        models = []
        try:
            req = urllib.request.Request("http://localhost:11434/api/tags")
            with urllib.request.urlopen(req, timeout=1.2) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                models = [m.get('name') for m in data.get('models', [])]
        except (urllib.error.URLError, json.JSONDecodeError, OSError):
            pass

        if models:
            print(f"     {C_DIM}Modelos detectados en Ollama local:{RESET} {C_TEXT}{', '.join(models)}{RESET}")
            def_model = models[0]
            chat_m = prompt_input(f"Modelo para Asistente/Chat [{def_model}]:", def_model)
            heavy_m = prompt_input(f"Modelo Pesado (Auditoría/Refactor) [{def_model}]:", def_model)
            light_m = prompt_input(f"Modelo Ligero (Commits/Quick) [{def_model}]:", def_model)
        else:
            chat_m = prompt_input("Modelo para Asistente/Chat [llama3.1:8b]:", "llama3.1:8b")
            heavy_m = prompt_input("Modelo Pesado (Auditoría/Refactor) [deepseek-coder:6.7b]:", "deepseek-coder:6.7b")
            light_m = prompt_input("Modelo Ligero (Commits/Quick) [qwen2.5-coder:7b]:", "qwen2.5-coder:7b")

    if "ai" not in base_cfg: base_cfg["ai"] = {}
    base_cfg["ai"]["enabled"] = is_ai
    base_cfg["ai"]["chat_model"] = chat_m
    base_cfg["ai"]["heavy_model"] = heavy_m
    base_cfg["ai"]["light_model"] = light_m

    if "skills" not in base_cfg["ai"]: base_cfg["ai"]["skills"] = {}
    base_cfg["ai"]["skills"]["chat_skill_path"] = "skills/chat_skill.txt"
    base_cfg["ai"]["skills"]["heavy_skill_path"] = "skills/heavy_skill.txt"
    base_cfg["ai"]["skills"]["light_skill_path"] = "skills/light_skill.txt"

    if not is_preview:
        ensure_default_skills()
        print(f"     {C_GREEN}✔ Directivas genéricas de Skills inicializadas en 'skills/'.{RESET}")
    print("")

    # 6. Tema Visual
    print(f"  {C_ACCENT}🎨 [6/6] TEMA VISUAL:{RESET}")
    print(f"     1) Noctalia (Sincronizado con el sistema Wayland/Hyprland)")
    print(f"     2) Dark Cyberpunk")
    print(f"     3) Monocromo Minimalista")
    t_choice = prompt_input("Selecciona tema (1-3):", "1")
    t_map = {"1": "noctalia", "2": "dark_cyberpunk", "3": "monochrome"}
    if "abraxas" not in base_cfg: base_cfg["abraxas"] = {}
    base_cfg["abraxas"]["theme"] = t_map.get(t_choice, "noctalia")
    print("")

    if is_preview:
        print(f"  {C_YELLOW}🧪 [MODO SIMULACIÓN] Simulación completada con éxito.{RESET}")
        print(f"  {C_DIM}No se ha modificado ningún archivo en: {cfg_target}{RESET}\n")
    else:
        # Guardar cambios
        write_toml_dict(cfg_target, base_cfg)
        print(f"  {C_GREEN}✅ ¡Configuración guardada satisfactoriamente en:{RESET}")
        print(f"     {C_TEXT}{cfg_target}{RESET} {C_DIM}(Permisos: 600 - Protegido){RESET}\n")

def show_config():
    cfg_target = get_target_config_path()
    if not os.path.exists(cfg_target):
        cfg_target = TEMPLATE_PATH
    print(f"\n  {C_GOLD}❖ CONFIGURACIÓN ACTUAL DE ABRAXAS: {cfg_target} ❖{RESET}\n")
    with open(cfg_target, "r", encoding="utf-8") as f:
        for line in f:
            print(f"  {C_TEXT}{line.rstrip()}{RESET}")
    print("")

def run_crud_menu():
    while True:
        cfg_target = get_target_config_path()
        print(f"\n  {C_GOLD}╭─────────────────────────────────────────────────────────────────╮{RESET}")
        print(f"  {C_GOLD}│{RESET}  {BOLD}❖ ABRAXAS | GESTOR DE CONFIGURACIÓN & RUTAS (CRUD) ❖{RESET}           {C_GOLD}│{RESET}")
        print(f"  {C_GOLD}╰─────────────────────────────────────────────────────────────────╯{RESET}\n")
        print(f"     {C_GREEN}[1]{RESET} Asistente de Configuración Rápida (Wizard)")
        print(f"     {C_ACCENT}[2]{RESET} Ver Configuración Actual (config.toml)")
        print(f"     {C_YELLOW}[3]{RESET} Modificar Ruta de Proyectos")
        print(f"     {C_YELLOW}[4]{RESET} Modificar Ruta de Bóveda / Obsidian")
        print(f"     {C_CYAN}[5]{RESET} Modificar Identidad Git (user.name / user.email)")
        print(f"     {C_CYAN}[6]{RESET} Activar / Desactivar IA Local (Ollama)")
        print(f"     {C_WARN}[7]{RESET} Restablecer a Valores de Fábrica (config.default.toml)")
        print(f"     {C_DIM}[0] Salir{RESET}\n")
        
        choice = input(f"  {C_GOLD}Selecciona una opción >> {RESET}").strip()
        
        if choice == "1":
            run_interactive_wizard()
        elif choice == "2":
            show_config()
        elif choice == "3":
            cfg = read_toml_dict(cfg_target) or read_toml_dict(TEMPLATE_PATH)
            new_p = prompt_input("Nueva ruta para Proyectos:", cfg.get("paths", {}).get("projects_dir", "~/Proyectos"))
            if "paths" not in cfg: cfg["paths"] = {}
            cfg["paths"]["projects_dir"] = new_p
            write_toml_dict(cfg_target, cfg)
            print(f"  {C_GREEN}✔ Ruta de proyectos actualizada.{RESET}\n")
        elif choice == "4":
            cfg = read_toml_dict(cfg_target) or read_toml_dict(TEMPLATE_PATH)
            new_v = prompt_input("Nueva ruta para Bóveda Obsidian:", cfg.get("paths", {}).get("vault_dir", "~/Vault"))
            if "paths" not in cfg: cfg["paths"] = {}
            cfg["paths"]["vault_dir"] = new_v
            write_toml_dict(cfg_target, cfg)
            print(f"  {C_GREEN}✔ Ruta de bóveda actualizada.{RESET}\n")
        elif choice == "5":
            cfg = read_toml_dict(cfg_target) or read_toml_dict(TEMPLATE_PATH)
            curr_name = cfg.get("git", {}).get("user_name", "")
            curr_email = cfg.get("git", {}).get("user_email", "")
            if not curr_name or not curr_email:
                dn, de = detect_git_identity()
                if not curr_name: curr_name = dn
                if not curr_email: curr_email = de
            new_name = prompt_input("Nombre de usuario Git (user.name):", curr_name)
            new_email = prompt_input("Correo electrónico Git (user.email):", curr_email)
            if "git" not in cfg: cfg["git"] = {}
            cfg["git"]["user_name"] = new_name
            cfg["git"]["user_email"] = new_email
            write_toml_dict(cfg_target, cfg)
            sync_global_gitconfig(new_name, new_email)
            print(f"  {C_GREEN}✔ Identidad Git actualizada ({new_name} <{new_email}>).{RESET}\n")
        elif choice == "6":
            cfg = read_toml_dict(cfg_target) or read_toml_dict(TEMPLATE_PATH)
            curr = cfg.get("ai", {}).get("enabled", True)
            if "ai" not in cfg: cfg["ai"] = {}
            cfg["ai"]["enabled"] = not curr
            write_toml_dict(cfg_target, cfg)
            state_str = "Habilitada" if cfg["ai"]["enabled"] else "Deshabilitada"
            print(f"  {C_GREEN}✔ IA Local {state_str}.{RESET}\n")
        elif choice == "7":
            confirm = input(f"  {C_WARN}¿Confirmas sobrescribir con la plantilla por defecto? (s/N) >> {RESET}").strip()
            if confirm.lower().startswith("s") or confirm.lower().startswith("y"):
                shutil.copyfile(TEMPLATE_PATH, cfg_target)
                os.chmod(cfg_target, 0o600)
                print(f"  {C_GREEN}✔ Configuración restablecida de fábrica.{RESET}\n")
        elif choice in ["0", "q", "exit"]:
            break

if __name__ == "__main__":
    is_preview = any(arg in sys.argv for arg in ["--preview", "--dry-run", "-p", "--simulated"])
    if "--wizard" in sys.argv or "-w" in sys.argv:
        run_interactive_wizard(is_preview=is_preview)
    elif "--show" in sys.argv or "-s" in sys.argv:
        show_config()
    elif is_preview:
        run_interactive_wizard(is_preview=True)
    else:
        run_crud_menu()
