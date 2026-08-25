#!/usr/bin/env bash
# =====================================================================
#  ❖ ABRAXAS | REGISTRO DEL LANZADOR DE ESCRITORIO (.DESKTOP)
# =====================================================================

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APPS_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$DIR/abraxas.desktop"
TARGET_FILE="$APPS_DIR/abraxas.desktop"

chmod +x "$DIR/bin/abraxas-gui"

mkdir -p "$APPS_DIR"

# Copiar el archivo .desktop al directorio de aplicaciones del usuario
cp "$DESKTOP_FILE" "$TARGET_FILE"
chmod +x "$TARGET_FILE"

# Actualizar base de datos de escritorio si la herramienta existe
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APPS_DIR"
fi

echo "✅ ABRAXAS se ha registrado exitosamente como aplicación de escritorio."
echo "   Lanzador instalado en: $TARGET_FILE"
echo "   Ya puedes buscar 'ABRAXAS' en el menú de aplicaciones de tu entorno (GNOME, KDE, Rofi, etc.)."

