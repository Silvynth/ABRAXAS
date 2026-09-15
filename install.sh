#!/usr/bin/env bash
# =====================================================================
#  ❖ ABRAXAS | INSTALADOR CON ASISTENTE GRÁFICO & BOOTSTRAP TRANSPARENTE
# =====================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# TrueColor ANSI Palette (Noctalia Theme)
C_GOLD='\033[38;2;230;166;200m'
C_GREEN='\033[38;2;143;208;184m'
C_ACCENT='\033[38;2;175;162;216m'
C_AMBER='\033[38;2;217;184;116m'
C_DIM='\033[38;2;200;185;202m'
C_TEXT='\033[38;2;238;231;240m'
C_WARN='\033[38;2;240;138;155m'
C_CYAN='\033[38;2;124;206;217m'
BOLD='\033[1m'
RESET='\033[0m'

if [ -f "$SCRIPT_DIR/VERSION" ]; then
    VERSION=$(tr -d '[:space:]' < "$SCRIPT_DIR/VERSION")
else
    VERSION="1.1.2"
fi

CONFIG_DIR="$SCRIPT_DIR"
SHARE_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/abraxas"
CONFIG_FILE="$SCRIPT_DIR/config.toml"

# Flags de CLI y Preview (Dry-Run)
CLI_MODE=false
PREVIEW_MODE=false

for arg in "$@"; do
    if [[ "$arg" == "--cli" || "$arg" == "-c" || "$arg" == "--no-gui" ]]; then
        CLI_MODE=true
    fi
    if [[ "$arg" == "--preview" || "$arg" == "--dry-run" || "$arg" == "-p" || "$arg" == "--simulated" ]]; then
        PREVIEW_MODE=true
    fi
done

if [[ "$PREVIEW_MODE" == "false" ]]; then
    mkdir -p "$CONFIG_DIR" "$SHARE_DIR"
fi

# Pausa estándar entre componentes (2 segundos para lectura y transición limpia)
step_pause() {
    if [[ "$PREVIEW_MODE" == "false" ]]; then
        sleep 2
    fi
}

# Detectar gestor de paquetes disponible (Prioridad a sudo para instalaciones administrativas explícitas)
PKG_INSTALL_CMD=""
if command -v pacman >/dev/null 2>&1; then
    PKG_INSTALL_CMD="sudo pacman -S --needed"
elif command -v paru >/dev/null 2>&1; then
    PKG_INSTALL_CMD="paru -S --needed"
elif command -v yay >/dev/null 2>&1; then
    PKG_INSTALL_CMD="yay -S --needed"
elif command -v apt-get >/dev/null 2>&1; then
    PKG_INSTALL_CMD="sudo apt-get install -y"
elif command -v dnf >/dev/null 2>&1; then
    PKG_INSTALL_CMD="sudo dnf install -y"
fi

# Función para renderizar tarjetas en cuadradito (ANSI Box Cards)
print_box_card() {
    local title="$1"
    local status="$2"
    local desc="$3"
    local role="$4"
    local alt="$5"
    local note="$6"

    echo -e "\n${C_ACCENT}╭──────────────────────────────────────────────────────────────────────────────╮${RESET}"
    echo -e "${C_ACCENT}│${RESET}  ${BOLD}${title}${RESET}  ${status}"
    echo -e "${C_ACCENT}├──────────────────────────────────────────────────────────────────────────────┤${RESET}"
    echo -e "${C_ACCENT}│${RESET}  ${C_GOLD}• Qué es:${RESET} ${C_TEXT}${desc}${RESET}"
    echo -e "${C_ACCENT}│${RESET}  ${C_CYAN}• Para qué sirve en ABRAXAS:${RESET} ${C_TEXT}${role}${RESET}"
    echo -e "${C_ACCENT}│${RESET}  ${C_DIM}• Si decides no instalarlo:${RESET} ${C_TEXT}${alt}${RESET}"
    if [ -n "$note" ]; then
        echo -e "${C_ACCENT}│${RESET}  ${C_AMBER}• Nota:${RESET} ${C_TEXT}${note}${RESET}"
    fi
    echo -e "${C_ACCENT}╰──────────────────────────────────────────────────────────────────────────────╯${RESET}"
}

# Banner Principal
echo -e "\n${C_GOLD}=====================================================================${RESET}"
if [[ "$PREVIEW_MODE" == "true" ]]; then
    echo -e "  ${C_AMBER}❖ INSTALADOR DE ABRAXAS (v${VERSION}) — MODO VISTA PREVIA / DRY-RUN ❖${RESET}"
else
    echo -e "  ${C_GOLD}❖ INSTALADOR DE ABRAXAS (v${VERSION}) — BOOTSTRAP TRANSPARENTE ❖${RESET}"
fi
echo -e "${C_GOLD}=====================================================================${RESET}"
echo -e "  ${C_DIM}Todas las dependencias son opcionales. Tú decides qué instalar.${RESET}"
echo -e "  ${C_AMBER}🔒 Las instalaciones del sistema requieren permisos de administrador (sudo).${RESET}"

# =====================================================================
# 1. PYSIDE6 (Entorno Gráfico)
# =====================================================================
HAS_DISPLAY=false
if [[ -n "$DISPLAY" || -n "$WAYLAND_DISPLAY" ]]; then
    HAS_DISPLAY=true
fi

HAS_PYSIDE=false
if python3 -c "import PySide6" &>/dev/null; then
    HAS_PYSIDE=true
fi

if [[ "$HAS_PYSIDE" == "true" ]]; then
    print_box_card \
        "🎨 PySide6 (Librería Gráfica Qt)" \
        "${C_GREEN}[✔ Instalado]${RESET}" \
        "Bindings oficiales de Qt para Python." \
        "Permite abrir la interfaz gráfica y ventanas flotantes de ABRAXAS." \
        "ABRAXAS funcionará únicamente en modo Terminal (CLI)."
else
    print_box_card \
        "🎨 PySide6 (Librería Gráfica Qt)" \
        "${C_WARN}[○ No instalado]${RESET}" \
        "Bindings oficiales de Qt para Python." \
        "Permite abrir la interfaz gráfica y ventanas flotantes de ABRAXAS." \
        "ABRAXAS funcionará únicamente en modo Terminal (CLI)." \
        "🔒 Requiere permisos de administrador (sudo) para instalar con pacman/paru."

    if [[ "$HAS_DISPLAY" == "true" && "$CLI_MODE" == "false" && "$PREVIEW_MODE" == "false" ]]; then
        echo -en "  ${C_GOLD}¿Deseas instalar PySide6 con permisos de administrador (sudo)? [S/n] >> ${RESET}"
        read -r resp_py
        if [[ -z "$resp_py" || "$resp_py" =~ ^[SsYy]$ ]]; then
            if [ -n "$PKG_INSTALL_CMD" ]; then
                echo -e "  ${C_CYAN}Instalando paquete 'pyside6' con permisos de administrador...${RESET}"
                $PKG_INSTALL_CMD pyside6 || true
                if python3 -c "import PySide6" &>/dev/null; then
                    HAS_PYSIDE=true
                    echo -e "  ${C_GREEN}✔ PySide6 instalado exitosamente.${RESET}"
                fi
            else
                echo -e "  ${C_WARN}⚠️ No se detectó un gestor de paquetes automático. Instala 'pyside6' manualmente con sudo.${RESET}"
            fi
        fi
    fi
fi
step_pause

# =====================================================================
# 2. GITHUB CLI (gh)
# =====================================================================
HAS_GH=false
if command -v gh >/dev/null 2>&1; then
    HAS_GH=true
    print_box_card \
        "🐙 GitHub CLI (gh)" \
        "${C_GREEN}[✔ Instalado]${RESET}" \
        "Herramienta oficial de línea de comandos de GitHub." \
        "Permite a Lumen listar, clonar y sincronizar automáticamente tus repositorios." \
        "Deberás clonar tus repositorios manualmente por URL o SSH."
else
    print_box_card \
        "🐙 GitHub CLI (gh)" \
        "${C_WARN}[○ No instalado]${RESET}" \
        "Herramienta oficial de línea de comandos de GitHub." \
        "Permite a Lumen listar, clonar y sincronizar automáticamente tus repositorios." \
        "Deberás clonar tus repositorios manualmente por URL o SSH." \
        "🔒 Requiere permisos de administrador (sudo). Podrás autenticarte luego con 'gh auth login'."

    if [[ "$PREVIEW_MODE" == "false" ]]; then
        echo -en "  ${C_GOLD}¿Deseas instalar GitHub CLI con permisos de administrador (sudo)? [s/N] >> ${RESET}"
        read -r resp_gh
        if [[ "$resp_gh" =~ ^[SsYy]$ ]]; then
            if [ -n "$PKG_INSTALL_CMD" ]; then
                echo -e "  ${C_CYAN}Instalando paquete 'github-cli' con permisos de administrador...${RESET}"
                $PKG_INSTALL_CMD github-cli || true
            fi
        fi
    fi
fi
step_pause

# =====================================================================
# 2.1 IDENTIDAD GIT (user.name & user.email)
# =====================================================================
GIT_USER=$(git config --get user.name 2>/dev/null || echo "")
GIT_EMAIL=$(git config --get user.email 2>/dev/null || echo "")

if [ -z "$GIT_USER" ] || [ -z "$GIT_EMAIL" ]; then
    if command -v gh >/dev/null 2>&1; then
        GH_USER_DETECT=$(gh api user --jq '.name // .login' 2>/dev/null || echo "")
        GH_EMAIL_DETECT=$(gh api user --jq '.email' 2>/dev/null || echo "")
        if [ "$GH_EMAIL_DETECT" == "null" ] || [ -z "$GH_EMAIL_DETECT" ]; then
            GH_EMAIL_DETECT=$(gh api user/emails --jq '.[0].email' 2>/dev/null || echo "")
        fi
        [ -z "$GIT_USER" ] && [ "$GH_USER_DETECT" != "null" ] && GIT_USER="$GH_USER_DETECT"
        [ -z "$GIT_EMAIL" ] && [ "$GH_EMAIL_DETECT" != "null" ] && GIT_EMAIL="$GH_EMAIL_DETECT"
    fi
fi

if [ -n "$GIT_USER" ] && [ -n "$GIT_EMAIL" ]; then
    print_box_card \
        "🐙 Identidad Git (Control de Versiones)" \
        "${C_GREEN}[✔ Configurado]${RESET}" \
        "Identidad de autoría para commits y releases en Git." \
        "Firma commits automáticamente en LUMEN ($GIT_USER <$GIT_EMAIL>)." \
        "Puedes modificarla más tarde en la pestaña CONFIG de ABRAXAS."
else
    print_box_card \
        "🐙 Identidad Git (Control de Versiones)" \
        "${C_WARN}[○ Incompleto]${RESET}" \
        "Identidad de autoría para commits y releases en Git." \
        "Firma commits automáticamente en LUMEN evitando el bloqueo de commit." \
        "Los commits fallarán si Git no conoce tu nombre y correo." \
        "Se solicitará configurar tu nombre y correo en el asistente."

    if [[ "$PREVIEW_MODE" == "false" && "$CLI_MODE" == "true" ]]; then
        echo -en "  ${C_GOLD}Ingresa tu nombre de usuario para Git [${GIT_USER}]: ${RESET}"
        read -r input_guser
        [ -n "$input_guser" ] && GIT_USER="$input_guser"

        echo -en "  ${C_GOLD}Ingresa tu correo para Git [${GIT_EMAIL}]: ${RESET}"
        read -r input_gemail
        [ -n "$input_gemail" ] && GIT_EMAIL="$input_gemail"

        if [ -n "$GIT_USER" ]; then
            git config --global user.name "$GIT_USER"
        fi
        if [ -n "$GIT_EMAIL" ]; then
            git config --global user.email "$GIT_EMAIL"
        fi
        echo -e "  ${C_GREEN}✔ Identidad Git guardada en ~/.gitconfig global ($GIT_USER <$GIT_EMAIL>).${RESET}"
    fi
fi
step_pause

# =====================================================================
# 3. OBSIDIAN (Segundo Cerebro)
# =====================================================================
HAS_OBSIDIAN=false
if command -v obsidian >/dev/null 2>&1; then
    HAS_OBSIDIAN=true
    print_box_card \
        "📓 Obsidian (Segundo Cerebro)" \
        "${C_GREEN}[✔ Instalado]${RESET}" \
        "Aplicación de gestión de conocimiento y notas en Markdown." \
        "Permite al módulo NOUS abrir y editar tus fichas técnicas y notas de proyectos." \
        "Tus notas se crearán igual en formato Markdown plano (.md) para leer con cualquier editor."
else
    print_box_card \
        "📓 Obsidian (Segundo Cerebro)" \
        "${C_WARN}[○ No instalado]${RESET}" \
        "Aplicación de gestión de conocimiento y notas en Markdown." \
        "Permite al módulo NOUS abrir y editar tus fichas técnicas y notas de proyectos." \
        "Tus notas se crearán igual en formato Markdown plano (.md) para leer con cualquier editor." \
        "🔒 Requiere permisos de administrador (sudo) para instalar."

    if [[ "$PREVIEW_MODE" == "false" ]]; then
        echo -en "  ${C_GOLD}¿Deseas instalar Obsidian con permisos de administrador (sudo)? [s/N] >> ${RESET}"
        read -r resp_obs
        if [[ "$resp_obs" =~ ^[SsYy]$ ]]; then
            if [ -n "$PKG_INSTALL_CMD" ]; then
                echo -e "  ${C_CYAN}Instalando paquete 'obsidian' con permisos de administrador...${RESET}"
                $PKG_INSTALL_CMD obsidian || true
            fi
        fi
    fi
fi
step_pause

# =====================================================================
# 4. DOCKER (Contenedores y Puertos)
# =====================================================================
HAS_DOCKER=false
if command -v docker >/dev/null 2>&1; then
    HAS_DOCKER=true
    print_box_card \
        "🐳 Docker (Plataforma de Contenedores)" \
        "${C_GREEN}[✔ Instalado]${RESET}" \
        "Plataforma de contenedores para desarrollo de software." \
        "Permite a Lumen monitorear contenedores activos y mapeos de puertos de tus proyectos." \
        "El panel de monitoreo de Docker permanecerá desactivado en la app."
else
    print_box_card \
        "🐳 Docker (Plataforma de Contenedores)" \
        "${C_WARN}[○ No instalado]${RESET}" \
        "Plataforma de contenedores para desarrollo de software." \
        "Permite a Lumen monitorear contenedores activos y mapeos de puertos de tus proyectos." \
        "El panel de monitoreo de Docker permanecerá desactivado en la app." \
        "🔒 Requiere permisos de administrador (sudo) para instalar paquetes y habilitar el servicio."

    if [[ "$PREVIEW_MODE" == "false" ]]; then
        echo -en "  ${C_GOLD}¿Deseas instalar Docker con permisos de administrador (sudo)? [s/N] >> ${RESET}"
        read -r resp_doc
        if [[ "$resp_doc" =~ ^[SsYy]$ ]]; then
            if [ -n "$PKG_INSTALL_CMD" ]; then
                echo -e "  ${C_CYAN}Instalando paquete 'docker' con permisos de administrador...${RESET}"
                $PKG_INSTALL_CMD docker || true
                if command -v docker >/dev/null 2>&1; then
                    HAS_DOCKER=true
                fi
            fi
        fi
    fi
fi

# Verificación de Servicio y Permisos de Docker
if [[ "$HAS_DOCKER" == "true" && "$PREVIEW_MODE" == "false" ]]; then
    if ! systemctl is-active docker >/dev/null 2>&1; then
        echo -en "\n  ${C_AMBER}El daemon de Docker está detenido. ¿Deseas habilitarlo e iniciarlo (sudo systemctl enable --now docker)? [s/N] >> ${RESET}"
        read -r resp_ds
        if [[ "$resp_ds" =~ ^[SsYy]$ ]]; then
            sudo systemctl enable --now docker || true
        fi
    fi

    if ! groups "$USER" 2>/dev/null | grep -qw "docker"; then
        echo -en "  ${C_AMBER}Tu usuario ($USER) no está en el grupo docker. ¿Deseas agregarte (sudo usermod -aG docker $USER)? [s/N] >> ${RESET}"
        read -r resp_dg
        if [[ "$resp_dg" =~ ^[SsYy]$ ]]; then
            sudo usermod -aG docker "$USER" || true
            echo -e "  ${C_GREEN}✔ Usuario agregado al grupo docker (se aplicará al reiniciar sesión).${RESET}"
        fi
    fi
fi
step_pause

# =====================================================================
# 5. OLLAMA (Motor de IA Local) & DIAGNÓSTICO DE HARDWARE
# =====================================================================
# Telemetría ligera de hardware en vivo
VRAM_MB=0
GPU_NAME="Gráficos Integrados / Sin GPU Dedicada"
if command -v nvidia-smi >/dev/null 2>&1; then
    VRAM_DETECT=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | head -n 1 | tr -d '[:space:]')
    if [ -n "$VRAM_DETECT" ]; then
        VRAM_MB=$VRAM_DETECT
        GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -n 1 | sed 's/^[ \t]*//')
    fi
fi

RAM_TOTAL=$(free -h 2>/dev/null | awk '/^Mem:/ {print $2}')
CPU_CORES=$(nproc 2>/dev/null || echo "4")

if [ "$VRAM_MB" -ge 14000 ]; then
    HW_TIER="Entusiasta (${VRAM_MB} MiB VRAM)"
    HW_ADVICE="Apto para modelos pesados (14B a 32B)."
elif [ "$VRAM_MB" -ge 7000 ]; then
    HW_TIER="Gama Media-Alta (${VRAM_MB} MiB VRAM)"
    HW_ADVICE="Óptimo para modelos 7B u 8B (~5 GB VRAM). Deja margen para el sistema y juegos."
elif [ "$VRAM_MB" -ge 4000 ]; then
    HW_TIER="Gama de Entrada (${VRAM_MB} MiB VRAM)"
    HW_ADVICE="Apto para modelos compactos (1.5B a 3B). No se recomiendan modelos de 7B o mayores."
else
    HW_TIER="Bajo Consumo / Sin GPU Dedicada (< 4 GB VRAM)"
    HW_ADVICE="No se recomienda instalar modelos locales pesados. Es mejor usar una API en la nube."
fi

# Recuadro de Diagnóstico de Hardware
echo -e "\n${C_ACCENT}╭──────────────────────────────────────────────────────────────────────────────╮${RESET}"
echo -e "${C_ACCENT}│${RESET}  ${BOLD}⚡ DIAGNÓSTICO DE HARDWARE PARA INTELIGENCIA ARTIFICIAL${RESET}"
echo -e "${C_ACCENT}├──────────────────────────────────────────────────────────────────────────────┤${RESET}"
echo -e "${C_ACCENT}│${RESET}  ${C_GOLD}• Tarjeta Gráfica:${RESET}   ${C_TEXT}${GPU_NAME}${RESET}"
echo -e "${C_ACCENT}│${RESET}  ${C_CYAN}• Memoria RAM:${RESET}       ${C_TEXT}${RAM_TOTAL} RAM | ${CPU_CORES} núcleos lógicos${RESET}"
echo -e "${C_ACCENT}│${RESET}  ${C_AMBER}• Perfil Sugerido:${RESET}   ${C_TEXT}${HW_TIER}${RESET}"
echo -e "${C_ACCENT}│${RESET}  ${C_DIM}• Recomendación:${RESET}     ${C_TEXT}${HW_ADVICE}${RESET}"
echo -e "${C_ACCENT}│${RESET}"
echo -e "${C_ACCENT}│${RESET}  ${C_GOLD}💡 AVISO IMPORTANTE:${RESET}"
echo -e "${C_ACCENT}│${RESET}     Gran parte de las funciones de ABRAXAS usan modelos de IA."
echo -e "${C_ACCENT}│${RESET}     • Si tienes hardware compatible, puedes instalar Ollama para IA local privada."
echo -e "${C_ACCENT}│${RESET}     • Si tu hardware es ajustado, ${BOLD}NO se recomienda${RESET} instalar modelos locales:"
echo -e "${C_ACCENT}│${RESET}       es preferible usar una API externa en la nube (ej. Gemini / OpenAI)"
echo -e "${C_ACCENT}│${RESET}       para disfrutar de todas las funciones sin ralentizar tu equipo."
echo -e "${C_ACCENT}╰──────────────────────────────────────────────────────────────────────────────╯${RESET}"

HAS_OLLAMA=false
if command -v ollama >/dev/null 2>&1; then
    HAS_OLLAMA=true
    print_box_card \
        "🧠 Ollama (Motor de IA Local)" \
        "${C_GREEN}[✔ Instalado]${RESET}" \
        "Servidor de modelos de lenguaje para ejecutar IA 100% en local y privada." \
        "Potencia el chat local, commits automáticos y análisis de código en ABRAXAS." \
        "Puedes conectar una API en la nube (Gemini/OpenAI) o usar ABRAXAS sin IA." \
        "Instalación 100% opcional, incluso si tienes hardware compatible."
else
    print_box_card \
        "🧠 Ollama (Motor de IA Local)" \
        "${C_WARN}[○ No instalado]${RESET}" \
        "Servidor de modelos de lenguaje para ejecutar IA 100% en local y privada." \
        "Potencia el chat local, commits automáticos y análisis de código en ABRAXAS." \
        "Puedes conectar una API en la nube (Gemini/OpenAI) o usar ABRAXAS sin IA." \
        "🔒 Requiere permisos de administrador (sudo) para instalar el binario y servicio."

    if [[ "$PREVIEW_MODE" == "false" ]]; then
        echo -en "  ${C_GOLD}¿Deseas instalar Ollama con permisos de administrador (sudo)? [s/N] >> ${RESET}"
        read -r resp_ol
        if [[ "$resp_ol" =~ ^[SsYy]$ ]]; then
            if [ -n "$PKG_INSTALL_CMD" ]; then
                echo -e "  ${C_CYAN}Instalando paquete 'ollama' con permisos de administrador...${RESET}"
                $PKG_INSTALL_CMD ollama || true
                if command -v ollama >/dev/null 2>&1; then
                    HAS_OLLAMA=true
                fi
            fi
        fi
    fi
fi

# Servicio Ollama & Explicación de Roles
if [[ "$HAS_OLLAMA" == "true" && "$PREVIEW_MODE" == "false" ]]; then
    if ! systemctl is-active ollama >/dev/null 2>&1; then
        echo -en "\n  ${C_AMBER}El servicio de Ollama está inactivo. ¿Deseas habilitarlo e iniciarlo (sudo systemctl enable --now ollama)? [s/N] >> ${RESET}"
        read -r resp_os
        if [[ "$resp_os" =~ ^[SsYy]$ ]]; then
            sudo systemctl enable --now ollama || true
            echo -e "  ${C_GREEN}✔ Servicio Ollama iniciado exitosamente en http://localhost:11434${RESET}"
        fi
    fi

    echo -e "\n${C_ACCENT}╭──────────────────────────────────────────────────────────────────────────────╮${RESET}"
    echo -e "${C_ACCENT}│${RESET}  ${BOLD}💡 ASIGNACIÓN DE MODELOS EN ABRAXAS (POST-INSTALACIÓN)${RESET}"
    echo -e "${C_ACCENT}├──────────────────────────────────────────────────────────────────────────────┤${RESET}"
    echo -e "${C_ACCENT}│${RESET}  ${C_TEXT}ABRAXAS cuenta con 3 roles de asistencia de IA:${RESET}"
    echo -e "${C_ACCENT}│${RESET}  ${C_GOLD}1. Conversacional:${RESET} ${C_TEXT}Chat general y consultas sobre tu Bóveda.${RESET}"
    echo -e "${C_ACCENT}│${RESET}  ${C_CYAN}2. Dev Rápido:${RESET}     ${C_TEXT}Commits inteligentes y operaciones ágiles de Git.${RESET}"
    echo -e "${C_ACCENT}│${RESET}  ${C_AMBER}3. Dev Pesado:${RESET}    ${C_TEXT}Auditoría profunda de código y refactorings complejos.${RESET}"
    echo -e "${C_ACCENT}│${RESET}"
    echo -e "${C_ACCENT}│${RESET}  ${C_TEXT}• ¿Cómo descargarlos?${RESET}"
    echo -e "${C_ACCENT}│${RESET}    ${C_DIM}No es obligatorio descargar 3 modelos gigantes. Con ${BOLD}UN SOLO modelo versátil${RESET}"
    echo -e "${C_ACCENT}│${RESET}    ${C_DIM}(ej: llama3.1:8b o qwen2.5-coder:7b) puedes cubrir los 3 roles.${RESET}"
    echo -e "${C_ACCENT}│${RESET}  ${C_TEXT}• Descarga manual en terminal:${RESET} ${C_GREEN}ollama pull <modelo>${RESET}"
    echo -e "${C_ACCENT}│${RESET}  ${C_TEXT}• Asignación visual:${RESET}          ${C_CYAN}Pestaña CONFIGURACIÓN dentro de ABRAXAS.${RESET}"
    echo -e "${C_ACCENT}╰──────────────────────────────────────────────────────────────────────────────╯${RESET}"
fi
step_pause

# =====================================================================
# 6. LANZAMIENTO DEL ASISTENTE (GUI o CLI)
# =====================================================================
if [[ "$HAS_DISPLAY" == "true" && "$HAS_PYSIDE" == "true" && "$CLI_MODE" == "false" ]]; then
    echo -e "\n${C_GOLD}=====================================================================${RESET}"
    if [[ "$PREVIEW_MODE" == "true" ]]; then
        echo -e "  ${C_AMBER}❖ LANZANDO ASISTENTE GRÁFICO FLOTANTE (MODO SIMULACIÓN) ❖${RESET}"
    else
        echo -e "  ${C_GOLD}❖ LANZANDO ASISTENTE GRÁFICO FLOTANTE DE ABRAXAS ❖${RESET}"
    fi
    echo -e "${C_GOLD}=====================================================================${RESET}\n"
    if [[ "$PREVIEW_MODE" == "true" ]]; then
        python3 gui/installer_gui.py --preview
    else
        echo -e "  ${C_DIM}Abriendo ventana interactiva de configuración...${RESET}\n"
        python3 gui/installer_gui.py
    fi
else
    echo -e "\n${C_GOLD}=====================================================================${RESET}"
    if [[ "$PREVIEW_MODE" == "true" ]]; then
        echo -e "  ${C_AMBER}❖ SIMULANDO INSTALACIÓN DE ABRAXAS (v${VERSION}) — MODO TERMINAL (CLI) ❖${RESET}"
    else
        echo -e "  ${C_GOLD}❖ CONFIGURACIÓN DE ABRAXAS (v${VERSION}) — MODO TERMINAL (CLI) ❖${RESET}"
    fi
    echo -e "${C_GOLD}=====================================================================${RESET}\n"

    if [[ "$PREVIEW_MODE" == "true" ]]; then
        echo -e "  ${C_AMBER}🧪 MODO SIMULACIÓN ACTIVO (DRY-RUN) — Ningún archivo será modificado.${RESET}\n"
        python3 core/setup.py --wizard --preview
        echo -e "\n  ${C_GOLD}Ejecutando diagnóstico del sistema en modo lectura...${RESET}"
        python3 core/doctor.py
        echo -e "  ${C_GREEN}✔ Simulación de instalación completada exitosamente.${RESET}\n"
    else
        if [ ! -f "$CONFIG_FILE" ]; then
            echo -e "  ${C_TEXT}¿Deseas personalizar tus rutas y preferencias ahora con el asistente interactivo? [S/n]${RESET}"
            read -r resp_wiz
            if [[ -z "$resp_wiz" || "$resp_wiz" =~ ^[SsYy]$ ]]; then
                python3 core/setup.py --wizard
            else
                cp config.default.toml "$CONFIG_FILE"
                chmod 600 "$CONFIG_FILE"
                echo -e "  ${C_GREEN}✔ Archivo base generado con valores predeterminados en: $CONFIG_FILE${RESET}"
            fi
        else
            echo -e "  ${C_DIM}ℹ Configuración existente preservada en: $CONFIG_FILE${RESET}"
        fi

        # Registro del lanzador de escritorio y comando abx
        if [ -f "$SCRIPT_DIR/scripts/install_desktop_launcher.sh" ]; then
            bash "$SCRIPT_DIR/scripts/install_desktop_launcher.sh" >/dev/null 2>&1 || true
        fi

        # Diagnóstico de integridad del sistema
        echo -e "\n  ${C_GOLD}Ejecutando diagnóstico inicial del sistema...${RESET}"
        python3 core/doctor.py

        echo -e "  ${C_GREEN}✨ Instalación de ABRAXAS v${VERSION} completada exitosamente.${RESET}"
        echo -e "     ${C_CYAN}Inicia tu entorno ejecutando: ${BOLD}abx${RESET}\n"
    fi
fi
