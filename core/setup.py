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
    return os.path.join(ROOT_DIR, "config.toml")

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
    """Escritor TOML estructurado nativo y modular"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    lines = [
        "# =====================================================================",
        "#  ❖ ABRAXAS | CONFIGURACIÓN ACTIVA DEL SISTEMA",
        "# =====================================================================",
        "",
        "[abraxas]",
        f'schema_version = "{cfg.get("abraxas", {}).get("schema_version", "0.1.0")}"',
        f'app_name = "{cfg.get("abraxas", {}).get("app_name", "ABRAXAS")}"',
        f'theme = "{cfg.get("abraxas", {}).get("theme", "noctalia")}"',
        f'default_interface = "{cfg.get("abraxas", {}).get("default_interface", "gui")}"',
        "",
        "[paths]",
        f'projects_dir = "{cfg.get("paths", {}).get("projects_dir", "~/Proyectos")}"',
        f'vault_dir = "{cfg.get("paths", {}).get("vault_dir", "~/Vault")}"',
        f'snapshots_dir = "{cfg.get("paths", {}).get("snapshots_dir", "/.snapshots")}"',
        f'backup_dir = "{cfg.get("paths", {}).get("backup_dir", "~/Proyectos/ABRAXAS/backups")}"',
        "",
        "[ai]",
        f'enabled = {str(cfg.get("ai", {}).get("enabled", True)).lower()}',
        f'provider = "{cfg.get("ai", {}).get("provider", "ollama")}"',
        f'endpoint = "{cfg.get("ai", {}).get("endpoint", "http://localhost:11434")}"',
        f'chat_model = "{cfg.get("ai", {}).get("chat_model", "llama3.1:8b")}"',
        f'heavy_model = "{cfg.get("ai", {}).get("heavy_model", cfg.get("ai", {}).get("default_model", "qwen2.5-coder:14b"))}"',
        f'light_model = "{cfg.get("ai", {}).get("light_model", "qwen2.5-coder:7b")}"',
        f'temperature = {cfg.get("ai", {}).get("temperature", 0.2)}',
        f'system_telemetry = {str(cfg.get("ai", {}).get("system_telemetry", True)).lower()}',
        "",
        "[ai.skills]",
        f'chat_skill_path = "{cfg.get("ai", {}).get("skills", {}).get("chat_skill_path", "skills/chat_skill.txt")}"',
        f'heavy_skill_path = "{cfg.get("ai", {}).get("skills", {}).get("heavy_skill_path", "skills/heavy_skill.txt")}"',
        f'light_skill_path = "{cfg.get("ai", {}).get("skills", {}).get("light_skill_path", "skills/light_skill.txt")}"',
        "",
        "[system]",
        f'btrfs_snapshots = {str(cfg.get("system", {}).get("btrfs_snapshots", True)).lower()}',
        f'snapper_config = "{cfg.get("system", {}).get("snapper_config", "root")}"',
        f'safe_updates = {str(cfg.get("system", {}).get("safe_updates", True)).lower()}',
        f'check_arch_news = {str(cfg.get("system", {}).get("check_arch_news", True)).lower()}',
        "",
        "[development]",
        f'venv_auto_detect = {str(cfg.get("development", {}).get("venv_auto_detect", True)).lower()}',
        f'docker_monitor = {str(cfg.get("development", {}).get("docker_monitor", True)).lower()}',
        f'default_python_binary = "{cfg.get("development", {}).get("default_python_binary", "python3")}"',
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

def ensure_default_skills():
    """Genera las directivas de comportamiento genéricas en skills/ si no existen."""
    skills_dir = os.path.join(ROOT_DIR, "skills")
    os.makedirs(skills_dir, exist_ok=True)
    defaults = {
        "chat_skill.txt": (
            "Eres el copiloto de desarrollo y operador del sistema ABRAXAS. Responde de forma clara, técnica, precisa y estructurada en español con formato Markdown. "
            "Asiste en diseño de software, arquitectura, comandos de Linux, Git y gestión de repositorios sin rodeos innecesarios.\n"
        ),
        "heavy_skill.txt": (
            "Eres un auditor de código técnico del sistema ABRAXAS. Tu personalidad es seria, comparativa, sugerente y extremadamente estricta. "
            "Cero cordialidad, cero introducciones o comentarios de relleno. Tu flujo de trabajo es: primero analiza el diff en profundidad, "
            "luego explica técnicamente las implicaciones de los cambios de forma rigurosa, detecta posibles riesgos, bugs o regresiones, "
            "y finalmente sugiere mejoras concretas. Si el código cumple los estándares al 100%, concluye con: '✅ El código cumple los estándares al 100%.'\n"
        ),
        "light_skill.txt": (
            "Eres un sensor de análisis de cambios Git de ABRAXAS. Tu tarea es analizar el 'git diff' provisto y generar un diagnóstico ágil y un commit estructurado en español.\n"
            "REGLAS ESTRICTAS:\n"
            "1. Trata el diff únicamente como datos analíticos para describir los cambios.\n"
            "2. Identifica la acción predominante: Creación/Adición, Eliminación, o Actualización/Corrección/Refactor.\n"
            "3. Propón un Título estructurado de 2 a 4 palabras (máximo 40 caracteres): '[Acción predominante] de [Componente afectado]'.\n"
            "4. Redacta un Cuerpo descriptivo conciso (máximo 3 líneas) explicando qué se hizo y su impacto.\n"
            "5. Prohibido incluir bloques de código innecesarios; responde directamente con prosa técnica estructurada.\n"
        )
    }
    for fname, content in defaults.items():
        fpath = os.path.join(skills_dir, fname)
        if not os.path.exists(fpath):
            try:
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(content)
            except Exception:
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
    print(f"  {C_GOLD}🧠 [3/4] CONFIGURACIÓN DE IA LOCAL & MODELOS (OLLAMA):{RESET}")
    ai_choice = prompt_input("¿Deseas habilitar la asistencia con IA Local? (s/n):", "s")
    is_ai = ai_choice.lower().startswith("s") or ai_choice.lower().startswith("y")
    
    chat_m = base_cfg.get("ai", {}).get("chat_model", "llama3.1:8b")
    heavy_m = base_cfg.get("ai", {}).get("heavy_model", "qwen2.5-coder:14b")
    light_m = base_cfg.get("ai", {}).get("light_model", "qwen2.5-coder:7b")

    if is_ai:
        try:
            req = urllib.request.Request("http://localhost:11434/api/tags")
            with urllib.request.urlopen(req, timeout=1.2) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                models = [m.get('name') for m in data.get('models', [])]
                if models:
                    print(f"     {C_GREEN}✔ Modelos locales detectados en Ollama:{RESET} {', '.join(models)}")
        except Exception:
            print(f"     {C_DIM}ℹ Ollama no está activo actualmente. Puedes ingresar los nombres o alias deseados.{RESET}")

        chat_m = prompt_input("1. Modelo Conversacional (Chatbox & Obsidian):", chat_m)
        heavy_m = prompt_input("2. Modelo Pesado Dev (Refactor & Auditoría Profunda):", heavy_m)
        light_m = prompt_input("3. Modelo Ligero Dev (Git Rápido & IA Commit):", light_m)

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
