#!/usr/bin/env bash
# =====================================================================
#  ❖ ABRAXAS | INSTALADOR CON ASISTENTE GRÁFICO FLOTANTE (v0.1.0)
# =====================================================================

set -e

C_GOLD='\033[38;2;230;166;200m'
C_GREEN='\033[38;2;143;208;184m'
C_ACCENT='\033[38;2;175;162;216m'
C_AMBER='\033[38;2;217;184;116m'
C_DIM='\033[38;2;200;185;202m'
C_TEXT='\033[38;2;238;231;240m'
RESET='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f "$SCRIPT_DIR/VERSION" ]; then
    VERSION=$(cat "$SCRIPT_DIR/VERSION" | tr -d '[:space:]')
else
    VERSION="0.1.1"
fi

CONFIG_DIR="$SCRIPT_DIR"
SHARE_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/abraxas"
CONFIG_FILE="$SCRIPT_DIR/config.toml"

# Detectar flags de CLI y Preview (Dry-Run)
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

# Crear directorios solo si no estamos en modo simulación
if [[ "$PREVIEW_MODE" == "false" ]]; then
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$SHARE_DIR"
fi

# Detectar si existe entorno gráfico activo
HAS_DISPLAY=false
if [[ -n "$DISPLAY" || -n "$WAYLAND_DISPLAY" ]]; then
    HAS_DISPLAY=true
fi

# Detectar PySide6
HAS_PYSIDE=false
if python3 -c "import PySide6" &>/dev/null; then
    HAS_PYSIDE=true
fi

if [[ "$HAS_DISPLAY" == "true" && "$HAS_PYSIDE" == "true" && "$CLI_MODE" == "false" ]]; then
    echo -e "\n${C_GOLD}=====================================================================${RESET}"
    if [[ "$PREVIEW_MODE" == "true" ]]; then
        echo -e "  ${C_AMBER}❖ LANZANDO ASISTENTE GRÁFICO (MODO VISTA PREVIA / DRY-RUN) ❖${RESET}"
    else
        echo -e "  ${C_GOLD}❖ LANZANDO ASISTENTE GRÁFICO FLOTANTE DE ABRAXAS ❖${RESET}"
    fi
    echo -e "${C_GOLD}=====================================================================${RESET}\n"
    if [[ "$PREVIEW_MODE" == "true" ]]; then
        echo -e "  ${C_AMBER}🧪 Modo simulación activo: no se guardará ningún cambio en el disco.${RESET}\n"
        python3 gui/installer_gui.py --preview
    else
        echo -e "  ${C_DIM}Abriendo ventana emergente interactiva de instalación...${RESET}\n"
        python3 gui/installer_gui.py
    fi
else
    echo -e "\n${C_GOLD}=====================================================================${RESET}"
    if [[ "$PREVIEW_MODE" == "true" ]]; then
        echo -e "  ${C_AMBER}❖ SIMULANDO INSTALACIÓN DE ABRAXAS (v${VERSION}) — MODO TERMINAL (CLI) ❖${RESET}"
    else
        echo -e "  ${C_GOLD}❖ INSTALANDO ABRAXAS (v${VERSION}) — MODO TERMINAL (CLI) ❖${RESET}"
    fi
    echo -e "${C_GOLD}=====================================================================${RESET}\n"

    if [[ "$PREVIEW_MODE" == "true" ]]; then
        echo -e "  ${C_AMBER}🧪 MODO SIMULACIÓN ACTIVO (DRY-RUN) — Ningún archivo será creado o modificado.${RESET}\n"
        python3 core/setup.py --wizard --preview
        echo -e "\n  ${C_GOLD}Ejecutando diagnóstico del sistema en modo lectura...${RESET}"
        python3 core/doctor.py
        echo -e "  ${C_GREEN}✔ Simulación de instalación completada exitosamente.${RESET}\n"
    else
        if [ ! -f "$CONFIG_FILE" ]; then
            echo -e "  ${C_TEXT}¿Deseas personalizar tus rutas y preferencias ahora con el asistente interactivo? [S/n]${RESET}"
            read -r resp
            if [[ -z "$resp" || "$resp" =~ ^[SsYy]$ ]]; then
                python3 core/setup.py --wizard
            else
                cp config.default.toml "$CONFIG_FILE"
                chmod 600 "$CONFIG_FILE"
                echo -e "  ${C_GREEN}✔ Archivo base generado con valores predeterminados en: $CONFIG_FILE${RESET}"
            fi
        else
            echo -e "  ${C_DIM}ℹ Configuración existente preservada en: $CONFIG_FILE${RESET}"
        fi

        # Diagnóstico de integridad del sistema
        echo -e "\n  ${C_GOLD}Ejecutando diagnóstico inicial del sistema...${RESET}"
        python3 core/doctor.py

        echo -e "  ${C_GREEN}✨ Instalación de ABRAXAS v${VERSION} completada exitosamente.${RESET}\n"
    fi
fi
