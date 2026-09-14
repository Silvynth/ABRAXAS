#!/usr/bin/env bash
# =====================================================================
#  ❖ ABRAXAS | REGISTRO DEL LANZADOR DE ESCRITORIO (.DESKTOP)
# =====================================================================

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APPS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
BIN_DIR="$HOME/.local/bin"
TARGET_FILE="$APPS_DIR/abraxas.desktop"

chmod +x "$DIR/bin/abraxas-gui"
mkdir -p "$APPS_DIR" "$BIN_DIR"

# Escribir abraxas.desktop dinámicamente con la ruta actual del repositorio
cat > "$TARGET_FILE" << EOF
[Desktop Entry]
Type=Application
Name=ABRAXAS
Comment=NEOS Control Center
Path=$DIR
Exec=$DIR/bin/abraxas-gui
Icon=$DIR/assets/abraxas_icon.svg
Terminal=false
Categories=Development;System;Utility;
StartupNotify=false
EOF
chmod +x "$TARGET_FILE"

# Crear enlace simbólico en ~/.local/bin/abx para acceso rápido desde terminal
ln -sf "$DIR/bin/abraxas-gui" "$BIN_DIR/abx"
chmod +x "$BIN_DIR/abx"

# Actualizar base de datos de escritorio si la herramienta existe
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APPS_DIR" >/dev/null 2>&1 || true
fi

echo "✅ ABRAXAS se ha registrado exitosamente como aplicación de escritorio."
echo "   Lanzador instalado en: $TARGET_FILE"
echo "   Comando rápido creado en: $BIN_DIR/abx"
echo "   Ya puedes buscar 'ABRAXAS' en tu lanzador de aplicaciones o escribir 'abx' en la terminal."

