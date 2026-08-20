#!/usr/bin/env bash
# =====================================================================
#  ❖ ABRAXAS | INSTALADOR Y ASISTENTE INICIAL (v0.1.0)
# =====================================================================

set -e

C_GOLD='\033[38;2;230;166;200m'
C_GREEN='\033[38;2;143;208;184m'
C_DIM='\033[38;2;200;185;202m'
RESET='\033[0m'

echo -e "\n${C_GOLD}=====================================================================${RESET}"
echo -e "  ${C_GOLD}❖ INSTALANDO ABRAXAS (v0.1.0) — PLATAFORMA DUALISTA ❖${RESET}"
echo -e "${C_GOLD}=====================================================================${RESET}\n"

CONFIG_DIR="$HOME/.config/abraxas"
SHARE_DIR="$HOME/.local/share/abraxas"

mkdir -p "$CONFIG_DIR"
mkdir -p "$SHARE_DIR"

# Copiar plantilla de configuración si no existe
if [ ! -f "$CONFIG_DIR/config.toml" ]; then
    cp config.default.toml "$CONFIG_DIR/config.toml"
    chmod 600 "$CONFIG_DIR/config.toml"
    echo -e "  ${C_GREEN}✔ Archivo de configuración generado en: $CONFIG_DIR/config.toml${RESET}"
else
    echo -e "  ${C_DIM}ℹ Configuración existente preservada en: $CONFIG_DIR/config.toml${RESET}"
fi

# Ejecutar doctor de verificación
echo -e "\n  ${C_GOLD}Ejecutando diagnóstico inicial del sistema...${RESET}"
python3 core/doctor.py

echo -e "  ${C_GREEN}✨ Instalación de ABRAXAS v0.1.0 completada exitosamente.${RESET}\n"
