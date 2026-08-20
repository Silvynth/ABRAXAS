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

# TrueColor ANSI Palette (Noctalia YoRHa Theme)
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
TEMPLATE_PATH = os.path.join(ROOT_DIR, "config.default.toml")

def get_target_config_path():
    home_dir = os.environ.get("HOME", os.path.expanduser("~"))
    return os.path.join(home_dir, ".config", "abraxas", "config.toml")

def read_toml_dict(filepath):
    """Lector TOML nativo simple para el esquema de Abraxas"""
    if not os.path.exists(filepath):
        return {}
    
    try:
        if sys.version_info >= (3, 11):
            import tomllib
            with open(filepath, "rb") as f:
                return tomllib.load(f)
    except Exception:
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
    """Escritor TOML estructurado nativo"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    lines = [
        "# =====================================================================",
        "#  ❖ ABRAXAS | CONFIGURACIÓN PERSONAL ACTIVA (XDG)",
        "# =====================================================================",
        "",
        "[abraxas]",
        f'schema_version = "{cfg.get("abraxas", {}).get("schema_version", "0.1.0")}"',
        f'app_name = "{cfg.get("abraxas", {}).get("app_name", "ABRAXAS")}"',
        f'theme = "{cfg.get("abraxas", {}).get("theme", "noctalia")}"',
        f'default_interface = "{cfg.get("abraxas", {}).get("default_interface", "tui")}"',
        "",
        "[hardware]",
        f'profile = "{cfg.get("hardware", {}).get("profile", "auto")}"',
        f'detect_gpu = {str(cfg.get("hardware", {}).get("detect_gpu", True)).lower()}',
        f'enable_hardware_accel = {str(cfg.get("hardware", {}).get("enable_hardware_accel", True)).lower()}',
        "",
        "[paths]",
        f'projects_dir = "{cfg.get("paths", {}).get("projects_dir", "~/Proyectos")}"',
        f'vault_dir = "{cfg.get("paths", {}).get("vault_dir", "~/Vault")}"',
        f'snapshots_dir = "{cfg.get("paths", {}).get("snapshots_dir", "/.snapshots")}"',
        f'backup_dir = "{cfg.get("paths", {}).get("backup_dir", "~/.local/share/abraxas/backups")}"',
        "",
        "[ai]",
        f'enabled = {str(cfg.get("ai", {}).get("enabled", True)).lower()}',
        f'provider = "{cfg.get("ai", {}).get("provider", "ollama")}"',
        f'endpoint = "{cfg.get("ai", {}).get("endpoint", "http://localhost:11434")}"',
        f'default_model = "{cfg.get("ai", {}).get("default_model", "qwen2.5-coder:7b")}"',
        f'fallback_model = "{cfg.get("ai", {}).get("fallback_model", "llama3.1:8b")}"',
        f'temperature = {cfg.get("ai", {}).get("temperature", 0.2)}',
        f'system_telemetry = {str(cfg.get("ai", {}).get("system_telemetry", True)).lower()}',
        "",
        "[modules.lumen]",
        f'name = "LUMEN"',
        f'description = "Entorno de Desarrollo, Git Flow y Docker"',
        f'enabled = {str(cfg.get("modules", {}).get("lumen", {}).get("enabled", True)).lower()}',
        f'git_auto_fetch = {str(cfg.get("modules", {}).get("lumen", {}).get("git_auto_fetch", True)).lower()}',
        f'docker_monitor = {str(cfg.get("modules", {}).get("lumen", {}).get("docker_monitor", True)).lower()}',
        "",
        "[modules.umbra]",
        f'name = "UMBRA"',
        f'description = "Control del Sistema, Kernels, Btrfs y Mantenimiento"',
        f'enabled = {str(cfg.get("modules", {}).get("umbra", {}).get("enabled", True)).lower()}',
        f'btrfs_snapshots = {str(cfg.get("modules", {}).get("umbra", {}).get("btrfs_snapshots", True)).lower()}',
        f'snapper_config = "{cfg.get("modules", {}).get("umbra", {}).get("snapper_config", "root")}"',
        f'safe_updates = {str(cfg.get("modules", {}).get("umbra", {}).get("safe_updates", True)).lower()}',
        f'check_arch_news = {str(cfg.get("modules", {}).get("umbra", {}).get("check_arch_news", True)).lower()}',
        "",
        "[modules.nous]",
        f'name = "NOUS"',
        f'description = "Conciencia, Bóveda de Conocimiento y Oráculo"',
        f'enabled = {str(cfg.get("modules", {}).get("nous", {}).get("enabled", True)).lower()}',
        f'oracle_search = {str(cfg.get("modules", {}).get("nous", {}).get("oracle_search", True)).lower()}',
        f'obsidian_sync = {str(cfg.get("modules", {}).get("nous", {}).get("obsidian_sync", True)).lower()}',
        ""
    ]
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    # Proteger permisos a nivel usuario (chmod 600)
    try:
        os.chmod(filepath, 0o600)
    except Exception:
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
    snap_dir = ""
    if is_btrfs:
        snap_dir = prompt_input("Ruta del subvolumen de instantáneas Btrfs (Snapper):", 
                              base_cfg.get("paths", {}).get("snapshots_dir", "/.snapshots"))

    if "paths" not in base_cfg: base_cfg["paths"] = {}
    base_cfg["paths"]["projects_dir"] = proj_dir
    base_cfg["paths"]["vault_dir"] = vault_dir
    base_cfg["paths"]["snapshots_dir"] = snap_dir

    if "modules" not in base_cfg: base_cfg["modules"] = {}
    if "umbra" not in base_cfg["modules"]: base_cfg["modules"]["umbra"] = {}
    base_cfg["modules"]["umbra"]["btrfs_snapshots"] = is_btrfs

    if "nous" not in base_cfg["modules"]: base_cfg["modules"]["nous"] = {}
    base_cfg["modules"]["nous"]["obsidian_sync"] = is_vault
    print("")

    # 2. Hardware Profile
    print(f"  {C_CYAN}⚡ [2/4] PERFIL DE RENDIMIENTO Y HARDWARE:{RESET}")
    print(f"     1) Auto (Recomendado)")
    print(f"     2) Alto Rendimiento (Priorizar GPU / VRAM)")
    print(f"     3) Bajo Consumo (Optimizado para batería)")
    h_choice = prompt_input("Selecciona un perfil (1-3):", "1")
    h_map = {"1": "auto", "2": "high_performance", "3": "low_power"}
    if "hardware" not in base_cfg: base_cfg["hardware"] = {}
    base_cfg["hardware"]["profile"] = h_map.get(h_choice, "auto")
    print("")

    # 3. Inteligencia Artificial (Ollama)
    print(f"  {C_GOLD}🧠 [3/4] CONFIGURACIÓN DE IA LOCAL (OLLAMA):{RESET}")
    ai_choice = prompt_input("¿Deseas habilitar la asistencia con IA Local? (s/n):", "s")
    is_ai = ai_choice.lower().startswith("s") or ai_choice.lower().startswith("y")
    
    selected_model = ""
    if is_ai:
        selected_model = "qwen2.5-coder:7b"
        try:
            req = urllib.request.Request("http://localhost:11434/api/tags")
            with urllib.request.urlopen(req, timeout=1.2) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                models = [m.get('name') for m in data.get('models', [])]
                if models:
                    print(f"     {C_GREEN}✔ Modelos locales detectados:{RESET} {', '.join(models)}")
                    selected_model = models[0]
        except Exception:
            print(f"     {C_DIM}ℹ Ollama no está activo actualmente. Se configurará por defecto.{RESET}")

    if "ai" not in base_cfg: base_cfg["ai"] = {}
    base_cfg["ai"]["enabled"] = is_ai
    base_cfg["ai"]["default_model"] = selected_model
    print("")

    # 4. Tema Visual
    print(f"  {C_ACCENT}🎨 [4/4] TEMA VISUAL:{RESET}")
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
        print(f"     {C_CYAN}[5]{RESET} Activar / Desactivar IA Local (Ollama)")
        print(f"     {C_WARN}[6]{RESET} Restablecer a Valores de Fábrica (config.default.toml)")
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
            curr = cfg.get("ai", {}).get("enabled", True)
            if "ai" not in cfg: cfg["ai"] = {}
            cfg["ai"]["enabled"] = not curr
            write_toml_dict(cfg_target, cfg)
            state_str = "Habilitada" if cfg["ai"]["enabled"] else "Deshabilitada"
            print(f"  {C_GREEN}✔ IA Local {state_str}.{RESET}\n")
        elif choice == "6":
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
