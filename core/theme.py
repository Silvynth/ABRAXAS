"""
❖ ABRAXAS 2.0 | Foundation: Dynamic Multi-Theme Engine & Universal Link
Enlace universal de temas para todo el ecosistema de Abraxas:
- Cintas Top (HUD Project, Ribbons, Switcher Pills)
- Grafos de Red & Git (Lienzo interactivo, nodos, hash, aristas)
- Terminal Interactiva (Cabecera, visor de logs, prompt, input)
- Barras (Scrollbars tácticas, splitters, barras de filamento de hardware)
- Botones (Primarios, tácticos, toggles, badges, danger)
- Visor de Documentación & README (Fondo negro carbón por defecto; en Claro: fondo blanco con texto negro puro)

Soporta 5 Esquemas Visuales:
1. Oscuro (Haute Horlogerie / Monocromo actual)
2. Claro (Slate puro de alto contraste con texto negro)
3. Lavanda (Violeta noche y púrpuras suaves)
4. Cyberpunk (Asfalto profundo con cian, magenta y amarillo neón)
5. Sistema (Sincronizado dinámicamente con el SO)
"""

import functools
from typing import Optional, Dict, Any, List
from PySide6.QtGui import QColor

# -------------------------------------------------------------
# 1. ESTADO GLOBAL DEL TEMA ACTIVO Y CACHÉ ULTRA-RÁPIDA
# -------------------------------------------------------------
_ACTIVE_THEME: str = "oscuro"
_CURRENT_PALETTE_REF: Optional[Dict[str, Any]] = None
_CURRENT_STORAGE_REF: Optional[List[str]] = None

def get_active_theme_name() -> str:
    """Devuelve el nombre del tema activo actualmente en memoria."""
    global _ACTIVE_THEME
    return _ACTIVE_THEME

def set_active_theme_name(theme_name: str):
    """Establece el nombre del tema activo para el enlace universal y actualiza la caché directa O(1)."""
    global _ACTIVE_THEME, _CURRENT_PALETTE_REF, _CURRENT_STORAGE_REF
    _ACTIVE_THEME = (theme_name or "oscuro").lower().strip()
    _CURRENT_PALETTE_REF = get_theme_palette(_ACTIVE_THEME)
    _CURRENT_STORAGE_REF = _CURRENT_PALETTE_REF.get("STORAGE_PALETTE", OSCURO_PALETTE["STORAGE_PALETTE"])


# -------------------------------------------------------------
# 2. DEFINICIÓN DE PALETAS COMPLETAS
# -------------------------------------------------------------

# 2.1 TEMA OSCURO (El actual: Monocromo Haute Horlogerie)
OSCURO_PALETTE: Dict[str, Any] = {
    "NAME": "oscuro",
    "IS_LIGHT": "false",
    "BG_CANVAS": "#0a0b0e",           # Fondo general profundo
    "BG_SIDEBAR": "#101115",          # Barra lateral sólida
    "BG_SURFACE": "#14161c",          # Tarjetas y contenedores principales
    "BG_SURFACE_HOVER": "#1a1c24",    # Hover sutil en contenedores
    "BG_INPUT": "#0c0d10",            # Entradas de texto y terminal
    "BG_HIGHLIGHT": "rgba(255, 255, 255, 0.04)", # Fondos secundarios

    "BORDER_SUBTLE": "rgba(255, 255, 255, 0.07)",  # Borde por defecto
    "BORDER_MEDIUM": "rgba(255, 255, 255, 0.15)",  # Borde hover / enfocado
    "BORDER_STRONG": "#ffffff",                     # Borde activo

    "TEXT_TITLES": "#ffffff",          # Blanco puro para titulares
    "TEXT_BODY": "#e2e8f0",            # Platino para lectura principal
    "TEXT_MUTED": "#9ca3af",           # Gris medio para subtítulos
    "TEXT_MICRO": "#64748b",           # Titanio oscuro para micro-tags

    "ACCENT_ACTIVE": "#ffffff",
    "ACCENT_PILL": "rgba(255, 255, 255, 0.08)",

    # Cintas Top y Ribbons
    "TOP_BAR_BG": "#14161c",
    "TOP_BAR_TEXT": "#ffffff",
    "TOP_BAR_MUTED": "#94a3b8",
    "TOP_BAR_SEP": "#475569",

    # Terminal Táctica
    "TERMINAL_BG": "#08090b",
    "TERMINAL_HEADER": "#0c0d10",
    "TERMINAL_TEXT": "#e2e8f0",
    "TERMINAL_PROMPT": "#94a3b8",

    # Markdown / Readme (En oscuro: negro carbón con texto platino)
    "MARKDOWN_BG": "#0c0d10",
    "MARKDOWN_TEXT": "#e2e8f0",
    "MARKDOWN_BORDER": "rgba(255, 255, 255, 0.08)",

    # Grafo de Ramas & Commits
    "GRAPH_BG": "transparent",
    "GRAPH_CANVAS_BG": "#08090b",
    "GRAPH_TEXT": "#e2e8f0",
    "GRAPH_TEXT_TITLE": "#ffffff",
    "GRAPH_TEXT_MUTED": "#64748b",
    "GRAPH_HASH": "#cbd5e1",
    "GRAPH_HASH_BG": "rgba(255, 255, 255, 0.06)",
    "GRAPH_HASH_BORDER": "rgba(255, 255, 255, 0.12)",

    # Canales y Carriles del Grafo (Lanes de alta precisión)
    "LANE_COLORS": [
        "#38bdf8",  # Sky Cyan (HEAD / Principal)
        "#818cf8",  # Indigo (Core)
        "#34d399",  # Emerald (Mainline)
        "#fbbf24",  # Amber (Feature Branches)
        "#f43f5e",  # Rose (Bugfix / Stale)
        "#c084fc",  # Purple (Hotfix)
        "#2dd4bf",  # Teal (Experimental)
        "#fb923c",  # Orange (Release)
    ],

    # Barras de Progreso / Filamento
    "PROGRESS_BG": "rgba(255, 255, 255, 0.06)",
    "PROGRESS_START": "#64748b",
    "PROGRESS_END": "#cbd5e1",

    # Almacenamiento Segmentado (Sector 02: Haute Horlogerie Platino / Titanio)
    "STORAGE_PALETTE": [
        "#ffffff",  # Blanco Polar (Elemento Principal / Mayor masa de datos)
        "#d1d5db",  # Platino Claro
        "#9ca3af",  # Titanio / Gris Medio
        "#6b7280",  # Acero Mate
        "#4b5563",  # Grafito Técnico
        "#374151",  # Carbón Medio
        "#282c37",  # Obsidiana Mate
        "#1e222b",  # Carbón Profundo
    ],

    # Botones Primarios
    "BTN_PRIMARY_BG": "#ffffff",
    "BTN_PRIMARY_TEXT": "#0a0b0e",
    "BTN_PRIMARY_HOVER_BG": "#d1d5db",
}

# 2.2 TEMA CLARO (Uno nuevo: Slate de alta legibilidad, fondo README blanco con texto negro)
CLARO_PALETTE: Dict[str, Any] = {
    "NAME": "claro",
    "IS_LIGHT": "true",
    "BG_CANVAS": "#f1f5f9",           # Slate 100 suave
    "BG_SIDEBAR": "#e2e8f0",          # Slate 200 estructural
    "BG_SURFACE": "#ffffff",          # Blanco puro para tarjetas
    "BG_SURFACE_HOVER": "#f8fafc",    # Hover sutil
    "BG_INPUT": "#ffffff",            # Input blanco limpio
    "BG_HIGHLIGHT": "rgba(0, 0, 0, 0.04)",

    "BORDER_SUBTLE": "rgba(0, 0, 0, 0.09)",
    "BORDER_MEDIUM": "rgba(0, 0, 0, 0.18)",
    "BORDER_STRONG": "#0f172a",

    "TEXT_TITLES": "#0f172a",          # Slate 900 casi negro
    "TEXT_BODY": "#334155",            # Slate 700 cuerpo
    "TEXT_MUTED": "#64748b",           # Slate 500 medio
    "TEXT_MICRO": "#94a3b8",           # Slate 400

    "ACCENT_ACTIVE": "#0f172a",
    "ACCENT_PILL": "rgba(0, 0, 0, 0.07)",

    # Cintas Top y Ribbons
    "TOP_BAR_BG": "#ffffff",
    "TOP_BAR_TEXT": "#0f172a",
    "TOP_BAR_MUTED": "#475569",
    "TOP_BAR_SEP": "#cbd5e1",

    # Terminal Táctica (Fondo claro limpio con texto negro)
    "TERMINAL_BG": "#f8fafc",
    "TERMINAL_HEADER": "#f1f5f9",
    "TERMINAL_TEXT": "#0f172a",
    "TERMINAL_PROMPT": "#475569",

    # Markdown / Readme (En claro: fondo blanco puro y TEXTO EN NEGRO)
    "MARKDOWN_BG": "#ffffff",
    "MARKDOWN_TEXT": "#0f172a",
    "MARKDOWN_BORDER": "rgba(0, 0, 0, 0.10)",

    # Grafo de Ramas & Commits (En claro: textos en negro/carbón de alto contraste)
    "GRAPH_BG": "transparent",
    "GRAPH_CANVAS_BG": "#ffffff",
    "GRAPH_TEXT": "#1e293b",
    "GRAPH_TEXT_TITLE": "#0f172a",
    "GRAPH_TEXT_MUTED": "#64748b",
    "GRAPH_HASH": "#0284c7",
    "GRAPH_HASH_BG": "rgba(2, 132, 199, 0.08)",
    "GRAPH_HASH_BORDER": "rgba(2, 132, 199, 0.22)",

    # Canales y Carriles del Grafo (Lanes de alto contraste sobre fondo blanco/claro)
    "LANE_COLORS": [
        "#0284c7",  # Deep Sky Blue
        "#4f46e5",  # Royal Indigo
        "#059669",  # Forest Emerald
        "#d97706",  # Dark Amber
        "#dc2626",  # Crimson Red
        "#7c3aed",  # Deep Violet
        "#0d9488",  # Deep Teal
        "#ea580c",  # Deep Orange
    ],

    # Barras de Progreso / Filamento
    "PROGRESS_BG": "rgba(0, 0, 0, 0.08)",
    "PROGRESS_START": "#94a3b8",
    "PROGRESS_END": "#0f172a",

    # Almacenamiento Segmentado (Sector 02: Alto contraste en fondos claros)
    "STORAGE_PALETTE": [
        "#0f172a",  # Slate 900 (Elemento Principal / Mayor masa)
        "#2563eb",  # Royal Blue
        "#0d9488",  # Deep Teal
        "#475569",  # Slate 600
        "#d97706",  # Dark Amber
        "#7c3aed",  # Deep Violet
        "#dc2626",  # Crimson Red
        "#64748b",  # Slate 500
    ],

    # Botones Primarios
    "BTN_PRIMARY_BG": "#0f172a",
    "BTN_PRIMARY_TEXT": "#ffffff",
    "BTN_PRIMARY_HOVER_BG": "#334155",
}

# 2.3 TEMA LAVANDA (Violeta místico y morados suaves)
LAVANDA_PALETTE: Dict[str, Any] = {
    "NAME": "lavanda",
    "IS_LIGHT": "false",
    "BG_CANVAS": "#0e0c18",           # Noche violeta profunda
    "BG_SIDEBAR": "#151224",          # Barra lateral lavanda noche
    "BG_SURFACE": "#1c1830",          # Tarjetas morado suave profundo
    "BG_SURFACE_HOVER": "#262042",    # Hover morado
    "BG_INPUT": "#120f20",            # Entrada oscura violeta
    "BG_HIGHLIGHT": "rgba(192, 132, 252, 0.07)",

    "BORDER_SUBTLE": "rgba(192, 132, 252, 0.12)",
    "BORDER_MEDIUM": "rgba(192, 132, 252, 0.24)",
    "BORDER_STRONG": "#d8b4fe",

    "TEXT_TITLES": "#f5f3ff",          # Blanco lavanda puro
    "TEXT_BODY": "#e9d5ff",            # Lavanda claro legible
    "TEXT_MUTED": "#c084fc",           # Púrpura medio
    "TEXT_MICRO": "#a855f7",           # Púrpura saturado

    "ACCENT_ACTIVE": "#c084fc",
    "ACCENT_PILL": "rgba(192, 132, 252, 0.14)",

    # Cintas Top y Ribbons
    "TOP_BAR_BG": "#1c1830",
    "TOP_BAR_TEXT": "#f5f3ff",
    "TOP_BAR_MUTED": "#c084fc",
    "TOP_BAR_SEP": "#581c87",

    # Terminal Táctica
    "TERMINAL_BG": "#0a0812",
    "TERMINAL_HEADER": "#131022",
    "TERMINAL_TEXT": "#e9d5ff",
    "TERMINAL_PROMPT": "#c084fc",

    # Markdown / Readme (En lavanda: fondo negro violeta profundo)
    "MARKDOWN_BG": "#0e0c18",
    "MARKDOWN_TEXT": "#e9d5ff",
    "MARKDOWN_BORDER": "rgba(192, 132, 252, 0.15)",

    # Grafo de Ramas & Commits
    "GRAPH_BG": "transparent",
    "GRAPH_CANVAS_BG": "#0a0812",
    "GRAPH_TEXT": "#e9d5ff",
    "GRAPH_TEXT_TITLE": "#f5f3ff",
    "GRAPH_TEXT_MUTED": "#c084fc",
    "GRAPH_HASH": "#d8b4fe",
    "GRAPH_HASH_BG": "rgba(192, 132, 252, 0.08)",
    "GRAPH_HASH_BORDER": "rgba(192, 132, 252, 0.20)",

    # Canales y Carriles del Grafo (Gama Lavanda & Violetas Místicos)
    "LANE_COLORS": [
        "#c084fc",  # Lavanda brillante
        "#a855f7",  # Púrpura eléctrico
        "#e879f9",  # Fucsia suave
        "#818cf8",  # Iris índigo
        "#f472b6",  # Rosa amatista
        "#d8b4fe",  # Lavanda pastel
        "#38bdf8",  # Cian contraste
        "#ec4899",  # Magenta místico
    ],

    # Barras de Progreso / Filamento
    "PROGRESS_BG": "rgba(192, 132, 252, 0.08)",
    "PROGRESS_START": "#7c3aed",
    "PROGRESS_END": "#c084fc",

    # Almacenamiento Segmentado (Sector 02: Gama Lavanda & Violetas Místicos)
    "STORAGE_PALETTE": [
        "#f5f3ff",  # Blanco Lavanda (Elemento Principal / Mayor masa)
        "#c084fc",  # Lavanda Brillante
        "#a855f7",  # Púrpura Eléctrico
        "#818cf8",  # Índigo Iris
        "#e879f9",  # Fucsia Lavanda
        "#7c3aed",  # Violeta Profundo
        "#d8b4fe",  # Lila Pastel
        "#581c87",  # Púrpura Noche
    ],

    # Botones Primarios
    "BTN_PRIMARY_BG": "#c084fc",
    "BTN_PRIMARY_TEXT": "#0e0c18",
    "BTN_PRIMARY_HOVER_BG": "#d8b4fe",
}

# 2.4 TEMA CYBERPUNK (Asfalto profundo con cian, magenta y amarillo neón)
CYBERPUNK_PALETTE: Dict[str, Any] = {
    "NAME": "cyberpunk",
    "IS_LIGHT": "false",
    "BG_CANVAS": "#05060a",           # Asfalto cian profundo
    "BG_SIDEBAR": "#0a0c14",          # Barra lateral carbón frío
    "BG_SURFACE": "#0f121d",          # Superficie con tinte neón
    "BG_SURFACE_HOVER": "#161b2b",    # Hover cian oscuro
    "BG_INPUT": "#080911",            # Terminal oscuro
    "BG_HIGHLIGHT": "rgba(0, 240, 255, 0.06)",

    "BORDER_SUBTLE": "rgba(0, 240, 255, 0.15)",
    "BORDER_MEDIUM": "rgba(255, 0, 85, 0.30)",
    "BORDER_STRONG": "#00f0ff",

    "TEXT_TITLES": "#00f0ff",          # Cian neón eléctrico
    "TEXT_BODY": "#e0f7fa",            # Blanco cian cristalino
    "TEXT_MUTED": "#ff007f",           # Magenta neón
    "TEXT_MICRO": "#ffe600",           # Amarillo neón

    "ACCENT_ACTIVE": "#00f0ff",
    "ACCENT_PILL": "rgba(0, 240, 255, 0.12)",

    # Cintas Top y Ribbons
    "TOP_BAR_BG": "#0f121d",
    "TOP_BAR_TEXT": "#00f0ff",
    "TOP_BAR_MUTED": "#e0f7fa",
    "TOP_BAR_SEP": "#ff007f",

    # Terminal Táctica
    "TERMINAL_BG": "#040508",
    "TERMINAL_HEADER": "#090b14",
    "TERMINAL_TEXT": "#00f0ff",
    "TERMINAL_PROMPT": "#ffe600",

    # Markdown / Readme (En cyberpunk: fondo negro asfalto profundo)
    "MARKDOWN_BG": "#06070c",
    "MARKDOWN_TEXT": "#e0f7fa",
    "MARKDOWN_BORDER": "rgba(0, 240, 255, 0.20)",

    # Grafo de Ramas & Commits
    "GRAPH_BG": "transparent",
    "GRAPH_CANVAS_BG": "#05060a",
    "GRAPH_TEXT": "#e0f7fa",
    "GRAPH_TEXT_TITLE": "#00f0ff",
    "GRAPH_TEXT_MUTED": "#ff007f",
    "GRAPH_HASH": "#ffe600",
    "GRAPH_HASH_BG": "rgba(0, 240, 255, 0.08)",
    "GRAPH_HASH_BORDER": "rgba(0, 240, 255, 0.22)",

    # Canales y Carriles del Grafo (Colores Neón Eléctrico)
    "LANE_COLORS": [
        "#00f0ff",  # Cian Eléctrico
        "#ff007f",  # Magenta Neón
        "#ffe600",  # Amarillo Neón
        "#00ff66",  # Verde Neón
        "#ff5500",  # Naranja Eléctrico
        "#b000ff",  # Púrpura Neón
        "#00e5ff",  # Aqua Brillante
        "#ff003c",  # Rojo Neón
    ],

    # Barras de Progreso / Filamento
    "PROGRESS_BG": "rgba(0, 240, 255, 0.08)",
    "PROGRESS_START": "#ff007f",
    "PROGRESS_END": "#00f0ff",

    # Almacenamiento Segmentado (Sector 02: Gama Neón Alta Tensión)
    "STORAGE_PALETTE": [
        "#00f0ff",  # Cian Eléctrico (Elemento Principal / Mayor masa)
        "#ff007f",  # Magenta Neón
        "#ffe600",  # Amarillo Neón
        "#00ff66",  # Verde Neón
        "#ff5500",  # Naranja Neón
        "#b000ff",  # Púrpura Neón
        "#ffffff",  # Blanco Neón
        "#00e5ff",  # Aqua Brillante
    ],

    # Botones Primarios
    "BTN_PRIMARY_BG": "#00f0ff",
    "BTN_PRIMARY_TEXT": "#05060a",
    "BTN_PRIMARY_HOVER_BG": "#38bdf8",
}

# 2.5 TEMA NORD (Azul Ártico Polar & Nieve Frost) - OSCURO 4
NORD_PALETTE: Dict[str, Any] = {
    "NAME": "nord",
    "IS_LIGHT": "false",
    "BG_CANVAS": "#242933",           # Nord 0 Polar Night
    "BG_SIDEBAR": "#2e3440",          # Noche ártica lateral
    "BG_SURFACE": "#3b4252",          # Nord 1 superficie polar
    "BG_SURFACE_HOVER": "#434c5e",    # Nord 2 hover
    "BG_INPUT": "#2e3440",            # Entrada polar
    "BG_HIGHLIGHT": "rgba(136, 192, 208, 0.08)",

    "BORDER_SUBTLE": "rgba(136, 192, 208, 0.15)",
    "BORDER_MEDIUM": "rgba(136, 192, 208, 0.28)",
    "BORDER_STRONG": "#88c0d0",

    "TEXT_TITLES": "#eceff4",          # Nord 6 Blanco ventisca
    "TEXT_BODY": "#e5e9f0",            # Nord 5 Nieve clara
    "TEXT_MUTED": "#88c0d0",           # Frost Ice Blue
    "TEXT_MICRO": "#81a1c1",           # Frost Blue

    "ACCENT_ACTIVE": "#88c0d0",
    "ACCENT_PILL": "rgba(136, 192, 208, 0.16)",

    # Cintas Top y Ribbons
    "TOP_BAR_BG": "#2e3440",
    "TOP_BAR_TEXT": "#eceff4",
    "TOP_BAR_MUTED": "#88c0d0",
    "TOP_BAR_SEP": "#4c566a",

    # Terminal Táctica
    "TERMINAL_BG": "#1e222a",
    "TERMINAL_HEADER": "#242933",
    "TERMINAL_TEXT": "#e5e9f0",
    "TERMINAL_PROMPT": "#88c0d0",

    # Markdown / Readme
    "MARKDOWN_BG": "#242933",
    "MARKDOWN_TEXT": "#e5e9f0",
    "MARKDOWN_BORDER": "rgba(136, 192, 208, 0.18)",

    # Grafo de Ramas & Commits
    "GRAPH_BG": "transparent",
    "GRAPH_CANVAS_BG": "#242933",
    "GRAPH_TEXT": "#e5e9f0",
    "GRAPH_TEXT_TITLE": "#eceff4",
    "GRAPH_TEXT_MUTED": "#88c0d0",
    "GRAPH_HASH": "#8fbcbb",
    "GRAPH_HASH_BG": "rgba(143, 188, 187, 0.12)",
    "GRAPH_HASH_BORDER": "rgba(143, 188, 187, 0.35)",

    # Canales y Carriles del Grafo (Aurora Borealis & Frost)
    "LANE_COLORS": [
        "#88c0d0",  # Frost Blue
        "#81a1c1",  # Glacial Blue
        "#5e81ac",  # Deep Arctic
        "#a3be8c",  # Aurora Green
        "#ebcb8b",  # Aurora Yellow
        "#d08770",  # Aurora Orange
        "#bf616a",  # Aurora Red
        "#b48ead",  # Aurora Purple
    ],

    # Barras de Progreso / Filamento
    "PROGRESS_BG": "rgba(136, 192, 208, 0.12)",
    "PROGRESS_START": "#81a1c1",
    "PROGRESS_END": "#88c0d0",

    # Almacenamiento Segmentado (Sector 02)
    "STORAGE_PALETTE": [
        "#88c0d0",
        "#81a1c1",
        "#a3be8c",
        "#ebcb8b",
        "#b48ead",
        "#d08770",
        "#5e81ac",
        "#bf616a",
    ],

    # Botones Primarios
    "BTN_PRIMARY_BG": "#88c0d0",
    "BTN_PRIMARY_TEXT": "#242933",
    "BTN_PRIMARY_HOVER_BG": "#8fbcbb",
}

# 2.6 TEMA ESMERALDA (Obsidiana Táctica & Jade Neón) - OSCURO 5
ESMERALDA_PALETTE: Dict[str, Any] = {
    "NAME": "esmeralda",
    "IS_LIGHT": "false",
    "BG_CANVAS": "#090d0b",           # Negro obsidiana profundo
    "BG_SIDEBAR": "#0f1512",          # Obsidiana lateral
    "BG_SURFACE": "#151e19",          # Tarjeta verde bosque oscuro
    "BG_SURFACE_HOVER": "#1c2822",    # Hover jade oscuro
    "BG_INPUT": "#0d1310",            # Entrada táctica
    "BG_HIGHLIGHT": "rgba(16, 185, 129, 0.08)",

    "BORDER_SUBTLE": "rgba(16, 185, 129, 0.15)",
    "BORDER_MEDIUM": "rgba(16, 185, 129, 0.28)",
    "BORDER_STRONG": "#10b981",

    "TEXT_TITLES": "#f0fdf4",          # Verde hielo puro brillante
    "TEXT_BODY": "#d1fae5",            # Verde claro de lectura
    "TEXT_MUTED": "#34d399",           # Jade luminoso
    "TEXT_MICRO": "#059669",           # Esmeralda profundo

    "ACCENT_ACTIVE": "#10b981",
    "ACCENT_PILL": "rgba(16, 185, 129, 0.14)",

    # Cintas Top y Ribbons
    "TOP_BAR_BG": "#151e19",
    "TOP_BAR_TEXT": "#f0fdf4",
    "TOP_BAR_MUTED": "#34d399",
    "TOP_BAR_SEP": "#064e3b",

    # Terminal Táctica
    "TERMINAL_BG": "#060a08",
    "TERMINAL_HEADER": "#0e1612",
    "TERMINAL_TEXT": "#d1fae5",
    "TERMINAL_PROMPT": "#10b981",

    # Markdown / Readme
    "MARKDOWN_BG": "#090d0b",
    "MARKDOWN_TEXT": "#d1fae5",
    "MARKDOWN_BORDER": "rgba(16, 185, 129, 0.16)",

    # Grafo de Ramas & Commits
    "GRAPH_BG": "transparent",
    "GRAPH_CANVAS_BG": "#090d0b",
    "GRAPH_TEXT": "#d1fae5",
    "GRAPH_TEXT_TITLE": "#f0fdf4",
    "GRAPH_TEXT_MUTED": "#34d399",
    "GRAPH_HASH": "#10b981",
    "GRAPH_HASH_BG": "rgba(16, 185, 129, 0.12)",
    "GRAPH_HASH_BORDER": "rgba(16, 185, 129, 0.35)",

    # Canales y Carriles del Grafo
    "LANE_COLORS": [
        "#10b981",  # Esmeralda Neón
        "#06b6d4",  # Cian Laguna
        "#84cc16",  # Lima Táctico
        "#14b8a6",  # Teal Jade
        "#3b82f6",  # Zafiro Táctico
        "#eab308",  # Ámbar
        "#a855f7",  # Amatista
        "#059669",  # Verde Profundo
    ],

    # Barras de Progreso / Filamento
    "PROGRESS_BG": "rgba(16, 185, 129, 0.12)",
    "PROGRESS_START": "#059669",
    "PROGRESS_END": "#10b981",

    # Almacenamiento Segmentado (Sector 02)
    "STORAGE_PALETTE": [
        "#10b981",
        "#06b6d4",
        "#84cc16",
        "#14b8a6",
        "#eab308",
        "#3b82f6",
        "#a855f7",
        "#059669",
    ],

    # Botones Primarios
    "BTN_PRIMARY_BG": "#10b981",
    "BTN_PRIMARY_TEXT": "#060a08",
    "BTN_PRIMARY_HOVER_BG": "#34d399",
}

# 2.7 TEMA PERGAMINO (Sepia Cálido & Marfil Clásico / Cero Fatiga) - CLARO 2
PERGAMINO_PALETTE: Dict[str, Any] = {
    "NAME": "pergamino",
    "IS_LIGHT": "true",
    "BG_CANVAS": "#fbf7ee",           # Papel verjurado marfil cálido
    "BG_SIDEBAR": "#f4ede0",          # Sepia suave lateral
    "BG_SURFACE": "#ffffff",          # Tarjeta papel puro limpio
    "BG_SURFACE_HOVER": "#ece2ce",    # Tono pergamino envejecido
    "BG_INPUT": "#fbf7ee",            # Entrada papel cálido
    "BG_HIGHLIGHT": "rgba(139, 90, 43, 0.08)",

    "BORDER_SUBTLE": "rgba(120, 80, 40, 0.12)",
    "BORDER_MEDIUM": "rgba(120, 80, 40, 0.22)",
    "BORDER_STRONG": "#78350f",

    "TEXT_TITLES": "#292524",          # Carbón café profundo
    "TEXT_BODY": "#44403c",            # Piedra cálida oscura
    "TEXT_MUTED": "#78716c",           # Sepia medio
    "TEXT_MICRO": "#a8a29e",           # Sepia claro

    "ACCENT_ACTIVE": "#b45309",        # Ámbar cálido tostado
    "ACCENT_PILL": "rgba(180, 83, 9, 0.10)",

    # Cintas Top y Ribbons
    "TOP_BAR_BG": "#f4ede0",
    "TOP_BAR_TEXT": "#292524",
    "TOP_BAR_MUTED": "#78716c",
    "TOP_BAR_SEP": "#e7dcc7",

    # Terminal Táctica
    "TERMINAL_BG": "#f7f1e5",
    "TERMINAL_HEADER": "#ece2ce",
    "TERMINAL_TEXT": "#292524",
    "TERMINAL_PROMPT": "#854d0e",

    # Markdown / Readme
    "MARKDOWN_BG": "#ffffff",
    "MARKDOWN_TEXT": "#292524",
    "MARKDOWN_BORDER": "rgba(120, 80, 40, 0.14)",

    # Grafo de Ramas & Commits
    "GRAPH_BG": "transparent",
    "GRAPH_CANVAS_BG": "#fbf7ee",
    "GRAPH_TEXT": "#292524",
    "GRAPH_TEXT_TITLE": "#1c1917",
    "GRAPH_TEXT_MUTED": "#78716c",
    "GRAPH_HASH": "#9a3412",
    "GRAPH_HASH_BG": "rgba(154, 52, 18, 0.08)",
    "GRAPH_HASH_BORDER": "rgba(154, 52, 18, 0.25)",

    # Canales y Carriles del Grafo (Tintas Cálidas & Clásicas)
    "LANE_COLORS": [
        "#9a3412",  # Terracota
        "#b45309",  # Ámbar Tostado
        "#15803d",  # Verde Botella
        "#1d4ed8",  # Azul Marino
        "#7e22ce",  # Púrpura Imperial
        "#0f766e",  # Verde Pino
        "#b91c1c",  # Carmín
        "#4338ca",  # Índigo
    ],

    # Barras de Progreso / Filamento
    "PROGRESS_BG": "rgba(180, 83, 9, 0.10)",
    "PROGRESS_START": "#d97706",
    "PROGRESS_END": "#78350f",

    # Almacenamiento Segmentado (Sector 02)
    "STORAGE_PALETTE": [
        "#78350f",
        "#b45309",
        "#15803d",
        "#1d4ed8",
        "#7e22ce",
        "#0f766e",
        "#b91c1c",
        "#78716c",
    ],

    # Botones Primarios
    "BTN_PRIMARY_BG": "#78350f",
    "BTN_PRIMARY_TEXT": "#ffffff",
    "BTN_PRIMARY_HOVER_BG": "#9a3412",
}

# 2.8 TEMA NIEVE (Titanio Glacial Frost / Ultra Nítido) - CLARO 3
NIEVE_PALETTE: Dict[str, Any] = {
    "NAME": "nieve",
    "IS_LIGHT": "true",
    "BG_CANVAS": "#f4f7fb",           # Glaciar claro con ligero tinte azul ártico
    "BG_SIDEBAR": "#e9eef5",          # Titanio glacial lateral
    "BG_SURFACE": "#ffffff",          # Tarjeta blanca pura
    "BG_SURFACE_HOVER": "#dde5f0",    # Hover hielo suave
    "BG_INPUT": "#f4f7fb",            # Entrada nieve
    "BG_HIGHLIGHT": "rgba(2, 132, 199, 0.08)",

    "BORDER_SUBTLE": "rgba(15, 23, 42, 0.10)",
    "BORDER_MEDIUM": "rgba(15, 23, 42, 0.20)",
    "BORDER_STRONG": "#0284c7",

    "TEXT_TITLES": "#0c4a6e",          # Azul noche hielo profundo
    "TEXT_BODY": "#1e293b",            # Slate 800 lectura nítida
    "TEXT_MUTED": "#475569",           # Slate 600
    "TEXT_MICRO": "#64748b",           # Slate 500

    "ACCENT_ACTIVE": "#0284c7",        # Azul cielo ártico
    "ACCENT_PILL": "rgba(2, 132, 199, 0.12)",

    # Cintas Top y Ribbons
    "TOP_BAR_BG": "#e9eef5",
    "TOP_BAR_TEXT": "#0c4a6e",
    "TOP_BAR_MUTED": "#475569",
    "TOP_BAR_SEP": "#cbd5e1",

    # Terminal Táctica
    "TERMINAL_BG": "#f0f4f9",
    "TERMINAL_HEADER": "#e2e9f3",
    "TERMINAL_TEXT": "#0f172a",
    "TERMINAL_PROMPT": "#0284c7",

    # Markdown / Readme
    "MARKDOWN_BG": "#ffffff",
    "MARKDOWN_TEXT": "#0f172a",
    "MARKDOWN_BORDER": "rgba(2, 132, 199, 0.15)",

    # Grafo de Ramas & Commits
    "GRAPH_BG": "transparent",
    "GRAPH_CANVAS_BG": "#f4f7fb",
    "GRAPH_TEXT": "#1e293b",
    "GRAPH_TEXT_TITLE": "#0c4a6e",
    "GRAPH_TEXT_MUTED": "#475569",
    "GRAPH_HASH": "#0369a1",
    "GRAPH_HASH_BG": "rgba(3, 105, 161, 0.08)",
    "GRAPH_HASH_BORDER": "rgba(3, 105, 161, 0.24)",

    # Canales y Carriles del Grafo
    "LANE_COLORS": [
        "#0284c7",  # Ice Sky
        "#2563eb",  # Arctic Blue
        "#0d9488",  # Glacier Teal
        "#4f46e5",  # Deep Indigo
        "#059669",  # Pine Frost
        "#d97706",  # Ice Gold
        "#dc2626",  # Red Beacon
        "#7c3aed",  # Purple Polar
    ],

    # Barras de Progreso / Filamento
    "PROGRESS_BG": "rgba(2, 132, 199, 0.10)",
    "PROGRESS_START": "#38bdf8",
    "PROGRESS_END": "#0284c7",

    # Almacenamiento Segmentado (Sector 02)
    "STORAGE_PALETTE": [
        "#0284c7",
        "#2563eb",
        "#0d9488",
        "#4f46e5",
        "#059669",
        "#7c3aed",
        "#dc2626",
        "#475569",
    ],

    # Botones Primarios
    "BTN_PRIMARY_BG": "#0284c7",
    "BTN_PRIMARY_TEXT": "#ffffff",
    "BTN_PRIMARY_HOVER_BG": "#0369a1",
}

# 2.9 TEMA SAKURA (Cuarzo & Flor de Cerezo / Refinado y Sereno) - CLARO 4
SAKURA_PALETTE: Dict[str, Any] = {
    "NAME": "sakura",
    "IS_LIGHT": "true",
    "BG_CANVAS": "#fdf7f9",           # Marfil rosado ultra suave
    "BG_SIDEBAR": "#f8ebf0",          # Rosa cuarzo lateral
    "BG_SURFACE": "#ffffff",          # Tarjeta blanca pura
    "BG_SURFACE_HOVER": "#f2dbe4",    # Hover rosa pálido
    "BG_INPUT": "#fdf7f9",            # Entrada cuarzo
    "BG_HIGHLIGHT": "rgba(225, 29, 72, 0.07)",

    "BORDER_SUBTLE": "rgba(225, 29, 72, 0.12)",
    "BORDER_MEDIUM": "rgba(225, 29, 72, 0.22)",
    "BORDER_STRONG": "#be185d",

    "TEXT_TITLES": "#831843",          # Borgoña profundo elegante
    "TEXT_BODY": "#374151",            # Carbón suave neutro
    "TEXT_MUTED": "#9d174d",           # Rosa oscuro apagado
    "TEXT_MICRO": "#be185d",           # Magenta pétalo

    "ACCENT_ACTIVE": "#db2777",        # Rosa cerezo intenso
    "ACCENT_PILL": "rgba(219, 39, 119, 0.12)",

    # Cintas Top y Ribbons
    "TOP_BAR_BG": "#f8ebf0",
    "TOP_BAR_TEXT": "#831843",
    "TOP_BAR_MUTED": "#9d174d",
    "TOP_BAR_SEP": "#fbcfe8",

    # Terminal Táctica
    "TERMINAL_BG": "#fbf0f4",
    "TERMINAL_HEADER": "#f3dce5",
    "TERMINAL_TEXT": "#374151",
    "TERMINAL_PROMPT": "#db2777",

    # Markdown / Readme
    "MARKDOWN_BG": "#ffffff",
    "MARKDOWN_TEXT": "#374151",
    "MARKDOWN_BORDER": "rgba(225, 29, 72, 0.14)",

    # Grafo de Ramas & Commits
    "GRAPH_BG": "transparent",
    "GRAPH_CANVAS_BG": "#fdf7f9",
    "GRAPH_TEXT": "#374151",
    "GRAPH_TEXT_TITLE": "#831843",
    "GRAPH_TEXT_MUTED": "#9d174d",
    "GRAPH_HASH": "#be185d",
    "GRAPH_HASH_BG": "rgba(190, 24, 93, 0.08)",
    "GRAPH_HASH_BORDER": "rgba(190, 24, 93, 0.25)",

    # Canales y Carriles del Grafo
    "LANE_COLORS": [
        "#db2777",  # Rosa Cerezo
        "#9333ea",  # Violeta Suave
        "#0284c7",  # Celeste Primavera
        "#059669",  # Verde Matcha
        "#d97706",  # Durazno Cálido
        "#e11d48",  # Rubí Intenso
        "#4f46e5",  # Azul Hortensia
        "#64748b",  # Grafito Niebla
    ],

    # Barras de Progreso / Filamento
    "PROGRESS_BG": "rgba(219, 39, 119, 0.10)",
    "PROGRESS_START": "#f472b6",
    "PROGRESS_END": "#be185d",

    # Almacenamiento Segmentado (Sector 02)
    "STORAGE_PALETTE": [
        "#be185d",
        "#db2777",
        "#9333ea",
        "#0284c7",
        "#059669",
        "#d97706",
        "#e11d48",
        "#64748b",
    ],

    # Botones Primarios
    "BTN_PRIMARY_BG": "#be185d",
    "BTN_PRIMARY_TEXT": "#ffffff",
    "BTN_PRIMARY_HOVER_BG": "#9d174d",
}

# 2.10 TEMA MENTA (Salvia & Menta Fresca / Concentración Natural) - CLARO 5
MENTA_PALETTE: Dict[str, Any] = {
    "NAME": "menta",
    "IS_LIGHT": "true",
    "BG_CANVAS": "#f3f8f5",           # Menta blanco muy suave
    "BG_SIDEBAR": "#e4f0e9",          # Salvia claro lateral
    "BG_SURFACE": "#ffffff",          # Tarjeta blanca pura
    "BG_SURFACE_HOVER": "#d4e6db",    # Hover verde agua suave
    "BG_INPUT": "#f3f8f5",            # Entrada menta
    "BG_HIGHLIGHT": "rgba(13, 148, 136, 0.08)",

    "BORDER_SUBTLE": "rgba(13, 148, 136, 0.14)",
    "BORDER_MEDIUM": "rgba(13, 148, 136, 0.24)",
    "BORDER_STRONG": "#0d9488",

    "TEXT_TITLES": "#115e59",          # Teal bosque oscuro
    "TEXT_BODY": "#1f2937",            # Gris neutro profundo
    "TEXT_MUTED": "#0f766e",           # Salvia medio
    "TEXT_MICRO": "#14b8a6",           # Menta brillante

    "ACCENT_ACTIVE": "#0d9488",        # Teal menta fresco
    "ACCENT_PILL": "rgba(13, 148, 136, 0.12)",

    # Cintas Top y Ribbons
    "TOP_BAR_BG": "#e4f0e9",
    "TOP_BAR_TEXT": "#115e59",
    "TOP_BAR_MUTED": "#0f766e",
    "TOP_BAR_SEP": "#bbf7d0",

    # Terminal Táctica
    "TERMINAL_BG": "#ecf4ef",
    "TERMINAL_HEADER": "#dbebe1",
    "TERMINAL_TEXT": "#1f2937",
    "TERMINAL_PROMPT": "#0d9488",

    # Markdown / Readme
    "MARKDOWN_BG": "#ffffff",
    "MARKDOWN_TEXT": "#1f2937",
    "MARKDOWN_BORDER": "rgba(13, 148, 136, 0.15)",

    # Grafo de Ramas & Commits
    "GRAPH_BG": "transparent",
    "GRAPH_CANVAS_BG": "#f3f8f5",
    "GRAPH_TEXT": "#1f2937",
    "GRAPH_TEXT_TITLE": "#115e59",
    "GRAPH_TEXT_MUTED": "#0f766e",
    "GRAPH_HASH": "#0f766e",
    "GRAPH_HASH_BG": "rgba(15, 118, 110, 0.08)",
    "GRAPH_HASH_BORDER": "rgba(15, 118, 110, 0.25)",

    # Canales y Carriles del Grafo
    "LANE_COLORS": [
        "#0d9488",  # Menta Jade
        "#16a34a",  # Hoja Viva
        "#0284c7",  # Arroyo Azul
        "#d97706",  # Ámbar Cítrico
        "#7c3aed",  # Lavanda Silvestre
        "#dc2626",  # Baya Silvestre
        "#0891b2",  # Aqua Profundo
        "#4b5563",  # Roca Gris
    ],

    # Barras de Progreso / Filamento
    "PROGRESS_BG": "rgba(13, 148, 136, 0.10)",
    "PROGRESS_START": "#2dd4bf",
    "PROGRESS_END": "#0f766e",

    # Almacenamiento Segmentado (Sector 02)
    "STORAGE_PALETTE": [
        "#0f766e",
        "#0d9488",
        "#16a34a",
        "#0284c7",
        "#d97706",
        "#7c3aed",
        "#dc2626",
        "#4b5563",
    ],

    # Botones Primarios
    "BTN_PRIMARY_BG": "#0d9488",
    "BTN_PRIMARY_TEXT": "#ffffff",
    "BTN_PRIMARY_HOVER_BG": "#0f766e",
}

# Compatibilidad retrospectiva: Proxy dinámico para MONOCHROME_PALETTE que siempre refleja el tema activo
class _DynamicThemePalette(dict):
    """Proxy dinámico ultra-rápido para MONOCHROME_PALETTE con caché de puntero O(1)."""
    def _current(self) -> Dict[str, Any]:
        global _CURRENT_PALETTE_REF
        if _CURRENT_PALETTE_REF is None:
            _CURRENT_PALETTE_REF = get_theme_palette(_ACTIVE_THEME)
        return _CURRENT_PALETTE_REF

    def __getitem__(self, key):
        return self._current().get(key, OSCURO_PALETTE.get(key, ""))

    def get(self, key, default=None):
        return self._current().get(key, default)

    def __contains__(self, key):
        return key in self._current()

    def __iter__(self):
        return iter(self._current())

    def __len__(self):
        return len(self._current())

    def keys(self):
        return self._current().keys()

    def values(self):
        return self._current().values()

    def items(self):
        return self._current().items()

    def __repr__(self):
        return repr(self._current())

MONOCHROME_PALETTE = _DynamicThemePalette()

# Proxy dinámico para STORAGE_PALETTE que siempre refleja el tema activo
class _DynamicStoragePalette(list):
    """Proxy dinámico ultra-rápido para STORAGE_PALETTE con caché de puntero O(1)."""
    def _current(self) -> List[str]:
        global _CURRENT_STORAGE_REF
        if _CURRENT_STORAGE_REF is None:
            _CURRENT_STORAGE_REF = get_theme_storage_palette(_ACTIVE_THEME)
        return _CURRENT_STORAGE_REF

    def __iter__(self):
        return iter(self._current())

    def __getitem__(self, index):
        return self._current()[index]

    def __len__(self):
        return len(self._current())

    def __repr__(self):
        return repr(self._current())

    def __eq__(self, other):
        return self._current() == other

STORAGE_PALETTE = _DynamicStoragePalette()

THEME_PALETTES: Dict[str, Dict[str, Any]] = {
    # 5 Temas Oscuros
    "oscuro": OSCURO_PALETTE,
    "cyberpunk": CYBERPUNK_PALETTE,
    "lavanda": LAVANDA_PALETTE,
    "nord": NORD_PALETTE,
    "esmeralda": ESMERALDA_PALETTE,

    # 5 Temas Claros
    "claro": CLARO_PALETTE,
    "blanco": CLARO_PALETTE,  # Alias directo
    "pergamino": PERGAMINO_PALETTE,
    "nieve": NIEVE_PALETTE,
    "sakura": SAKURA_PALETTE,
    "menta": MENTA_PALETTE,
}

THEMES = THEME_PALETTES

# -------------------------------------------------------------
# 3. HELPERS DE RESOLUCIÓN & ENLACE UNIVERSAL (MEMOIZADOS)
# -------------------------------------------------------------

@functools.lru_cache(maxsize=32)
def get_theme_palette(theme_name: Optional[str] = None) -> Dict[str, Any]:
    """Obtiene el mapa de colores completo del tema indicado o el activo global (Memoizado O(1))."""
    if theme_name in [None, "", "monochrome", "default"]:
        t = (get_active_theme_name() or "oscuro").lower().strip()
    else:
        t = str(theme_name).lower().strip()
    return THEME_PALETTES.get(t, OSCURO_PALETTE)


def is_light_theme(theme_name: Optional[str] = None) -> bool:
    """Indica si el tema especificado o activo es claro."""
    p = get_theme_palette(theme_name)
    return p.get("IS_LIGHT") == "true"


def get_theme_lane_colors(theme_name: Optional[str] = None) -> List[str]:
    """Retorna la lista de colores de carriles/canales para el grafo según el tema."""
    p = get_theme_palette(theme_name)
    return p.get("LANE_COLORS", OSCURO_PALETTE["LANE_COLORS"])


def get_theme_storage_palette(theme_name: Optional[str] = None) -> List[str]:
    """Retorna la paleta de colores para las barras segmentadas de almacenamiento según el tema."""
    p = get_theme_palette(theme_name)
    return p.get("STORAGE_PALETTE", OSCURO_PALETTE["STORAGE_PALETTE"])


@functools.lru_cache(maxsize=16)
def get_graph_colors(theme_name: Optional[str] = None) -> Dict[str, Any]:
    """Devuelve objetos QColor preconfigurados y memoizados para el motor de lienzo del grafo."""
    p = get_theme_palette(theme_name)
    light = is_light_theme(theme_name)
    raw_lanes = p.get("LANE_COLORS", OSCURO_PALETTE["LANE_COLORS"])
    lane_colors = [QColor(c) for c in raw_lanes]

    return {
        "text_title": QColor(p["GRAPH_TEXT_TITLE"]),
        "text_body": QColor(p["GRAPH_TEXT"]),
        "text_muted": QColor(p["GRAPH_TEXT_MUTED"]),
        "hash_color": QColor(p["GRAPH_HASH"]),
        "hash_bg": QColor(p["GRAPH_HASH_BG"]),
        "hash_border": QColor(p["GRAPH_HASH_BORDER"]),
        "accent": QColor(p["ACCENT_ACTIVE"]),
        "lane_colors": lane_colors,
        "is_light": light
    }


# -------------------------------------------------------------
# 4. GENERADOR DE HOJA DE ESTILOS QSS UNIVERSAL (MEMOIZADO)
# -------------------------------------------------------------

def generate_theme_stylesheet(theme_name: str = "oscuro") -> str:
    """Genera u obtiene de caché instantánea la hoja de estilos QSS unificada."""
    t = (theme_name or "oscuro").lower().strip()
    set_active_theme_name(t)
    return _build_theme_stylesheet(t)


@functools.lru_cache(maxsize=16)
def _build_theme_stylesheet(theme_key: str) -> str:
    """Compila y almacena en caché la plantilla QSS para una clave de tema determinada."""
    p = get_theme_palette(theme_key)

    return f"""
/* =====================================================================
   ❖ ABRAXAS 2.0 | UNIVERSAL THEME STYLESHEET: {p["NAME"].upper()}
===================================================================== */

* {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    color: {p["TEXT_BODY"]};
}}

QWidget {{
    background-color: transparent;
    outline: none;
}}

/* Tooltips tácticos */
QToolTip {{
    background-color: {p["BG_SURFACE"]};
    color: {p["TEXT_TITLES"]};
    border: 1px solid {p["BORDER_MEDIUM"]};
    border-radius: 6px;
    padding: 6px 10px;
    font-family: 'Inter', -apple-system, sans-serif;
    font-size: 11px;
    font-weight: 500;
}}

/* Fondo raíz de la ventana */
QWidget#NeosShellWindow, QWidget#content_area {{
    background-color: {p["BG_CANVAS"]};
}}

/* -------------------------------------------------------------
   1. SIDEBAR & NAVEGACIÓN PRINCIPAL
------------------------------------------------------------- */
QFrame.sidebar {{
    background-color: {p["BG_SIDEBAR"]};
    border-right: 1px solid {p["BORDER_SUBTLE"]};
}}

QLabel.brand_title {{
    color: {p["TEXT_TITLES"]};
    font-size: 19px;
    font-weight: 800;
    letter-spacing: 0.5px;
}}

QLabel.brand_subtitle {{
    color: {p["TEXT_MICRO"]};
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}}

QLabel.version_badge {{
    color: {p["TEXT_MUTED"]};
    font-size: 11px;
    font-family: 'JetBrains Mono', monospace;
    background: {p["BG_HIGHLIGHT"]};
    border: 1px solid {p["BORDER_SUBTLE"]};
    border-radius: 6px;
    padding: 4px 8px;
}}

QPushButton.nav_btn {{
    background-color: transparent;
    color: {p["TEXT_MUTED"]};
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 13px;
    font-weight: 600;
    text-align: left;
}}

QPushButton.nav_btn:hover {{
    background-color: {p["BG_HIGHLIGHT"]};
    color: {p["TEXT_TITLES"]};
    border: 1px solid {p["BORDER_SUBTLE"]};
}}

QPushButton.nav_btn:checked {{
    background-color: {p["ACCENT_PILL"]};
    color: {p["TEXT_TITLES"]};
    border: 1px solid {p["BORDER_MEDIUM"]};
    font-weight: 700;
}}

/* -------------------------------------------------------------
   2. CINTAS SUPERIORES (TOP HUDS, RIBBONS, SWITCHER PILLS)
------------------------------------------------------------- */
/* -------------------------------------------------------------
   2. CINTAS SUPERIORES (TOP HUDS, RIBBONS, SWITCHER PILLS)
------------------------------------------------------------- */
QFrame#lumen_project_hud,
QFrame#umbra_status_ribbon,
QFrame#umbra_top_telemetry_hud,
QFrame.top_hud_ribbon,
QFrame.hud_ribbon {{
    background-color: {p["TOP_BAR_BG"]};
    border: 1px solid {p["BORDER_SUBTLE"]};
    border-radius: 10px;
}}

QLabel.hud_tag {{
    color: {p["TOP_BAR_MUTED"]};
    font-weight: 700;
    font-size: 11px;
}}

QLabel.hud_val_title {{
    color: {p["TOP_BAR_TEXT"]};
    font-weight: 800;
    font-size: 12.5px;
}}

QLabel.hud_sub {{
    color: {p["TOP_BAR_MUTED"]};
    font-size: 10px;
}}

QLabel.hud_sep {{
    color: {p["TOP_BAR_SEP"]};
    font-weight: 700;
}}

/* Píldora de Selección de Sectores (Cápsula Táctica) */
QFrame.switcher_pill {{
    background-color: {p["BG_SURFACE"]};
    border: 1px solid {p["BORDER_SUBTLE"]};
    border-radius: 8px;
    padding: 2px;
}}

QPushButton.switcher_pill_btn {{
    background-color: transparent;
    color: {p["TEXT_MUTED"]};
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 4px 14px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
}}

QPushButton.switcher_pill_btn:hover {{
    color: {p["TEXT_TITLES"]};
    background-color: {p["BG_HIGHLIGHT"]};
}}

QPushButton.switcher_pill_btn:checked {{
    background-color: {p["ACCENT_PILL"]};
    color: {p["TEXT_TITLES"]};
    border: 1px solid {p["BORDER_MEDIUM"]};
}}

/* -------------------------------------------------------------
   3. TARJETAS Y CONTENEDORES (SECTOR CARDS)
------------------------------------------------------------- */
QFrame.sector_card, QFrame.surface, QFrame[class="sector_card"] {{
    background-color: {p["BG_SURFACE"]};
    border: 1px solid {p["BORDER_SUBTLE"]};
    border-radius: 10px;
}}

QFrame.sector_card:hover, QFrame.surface:hover, QFrame[class="sector_card"]:hover {{
    border: 1px solid {p["BORDER_MEDIUM"]};
}}

QLabel.sector_micro_tag, QLabel.micro_tag {{
    color: {p["TEXT_MICRO"]};
    font-size: 9.5px;
    font-weight: 700;
    letter-spacing: 1.1px;
    text-transform: uppercase;
    font-family: 'JetBrains Mono', monospace;
}}

QLabel.sector_title, QLabel.section_title, QLabel.page_title {{
    color: {p["TEXT_TITLES"]};
    font-size: 14px;
    font-weight: 800;
    letter-spacing: -0.2px;
}}

QLabel.page_title {{
    font-size: 18px;
}}

QLabel.sector_desc, QLabel.page_subtitle {{
    color: {p["TEXT_MUTED"]};
    font-size: 12px;
    line-height: 1.4;
}}

/* -------------------------------------------------------------
   4. BOTONES TÁCTICOS Y PÍLDORAS
------------------------------------------------------------- */
QPushButton.cyber_btn, QPushButton.browse {{
    background-color: {p["BG_SURFACE"]};
    color: {p["TEXT_BODY"]};
    border: 1px solid {p["BORDER_SUBTLE"]};
    border-radius: 6px;
    padding: 5px 14px;
    min-height: 28px;
    font-size: 11.5px;
    font-weight: 600;
}}

QPushButton.cyber_btn:hover, QPushButton.browse:hover {{
    background-color: {p["BG_SURFACE_HOVER"]};
    color: {p["TEXT_TITLES"]};
    border: 1px solid {p["BORDER_MEDIUM"]};
}}

QPushButton.cyber_btn:pressed, QPushButton.browse:pressed {{
    background-color: {p["ACCENT_PILL"]};
    color: {p["TEXT_TITLES"]};
}}

QPushButton.cyber_btn_primary, QPushButton.primary {{
    background-color: {p["BTN_PRIMARY_BG"]};
    color: {p["BTN_PRIMARY_TEXT"]};
    border: 1px solid {p["BTN_PRIMARY_BG"]};
    border-radius: 6px;
    padding: 5px 16px;
    min-height: 28px;
    font-size: 11.5px;
    font-weight: 700;
}}

QPushButton.cyber_btn_primary:hover, QPushButton.primary:hover {{
    background-color: {p["BTN_PRIMARY_HOVER_BG"]};
    border-color: {p["BTN_PRIMARY_HOVER_BG"]};
    color: {p["BTN_PRIMARY_TEXT"]};
}}

QPushButton.cyber_btn_primary:pressed, QPushButton.primary:pressed {{
    background-color: {p["TEXT_MUTED"]};
    border-color: {p["TEXT_MUTED"]};
}}

QPushButton.cyber_btn_compact {{
    background-color: {p["BG_SURFACE"]};
    color: {p["TEXT_BODY"]};
    border: 1px solid {p["BORDER_SUBTLE"]};
    border-radius: 5px;
    padding: 3px 12px;
    min-height: 24px;
    font-size: 11px;
    font-weight: 600;
}}

QPushButton.cyber_btn_compact:hover {{
    background-color: {p["BG_SURFACE_HOVER"]};
    color: {p["TEXT_TITLES"]};
    border-color: {p["BORDER_MEDIUM"]};
}}

QPushButton.cyber_btn_compact:pressed {{
    background-color: {p["ACCENT_PILL"]};
    color: {p["TEXT_TITLES"]};
}}

QPushButton.cyber_btn_toggle {{
    background-color: {p["BG_SURFACE"]};
    color: {p["TEXT_MUTED"]};
    border: 1px solid {p["BORDER_SUBTLE"]};
    border-radius: 5px;
    padding: 4px 11px;
    min-height: 26px;
    font-size: 10.5px;
    font-weight: 600;
}}

QPushButton.cyber_btn_toggle:hover {{
    background-color: {p["BG_SURFACE_HOVER"]};
    color: {p["TEXT_TITLES"]};
    border-color: {p["BORDER_MEDIUM"]};
}}

QPushButton.cyber_btn_toggle:checked {{
    background-color: {p["ACCENT_PILL"]};
    color: {p["TEXT_TITLES"]};
    border: 1px solid {p["BORDER_STRONG"]};
    font-weight: 800;
}}

QPushButton.cyber_btn_toggle:disabled {{
    background-color: transparent;
    color: {p["TEXT_MUTED"]};
    border: 1px solid {p["BORDER_SUBTLE"]};
}}

QPushButton.cyber_btn_danger {{
    background-color: rgba(239, 68, 68, 0.12);
    color: #ef4444;
    border: 1px solid rgba(239, 68, 68, 0.30);
    border-radius: 6px;
    padding: 6px 14px;
    min-height: 28px;
    font-size: 11px;
    font-weight: 700;
}}

QPushButton.cyber_btn_danger:hover {{
    background-color: rgba(239, 68, 68, 0.25);
    border-color: rgba(239, 68, 68, 0.60);
    color: #ffffff;
}}

QPushButton.cyber_btn_danger:pressed {{
    background-color: #ef4444;
    color: #ffffff;
}}

QPushButton.cyber_btn_danger_compact {{
    background-color: rgba(239, 68, 68, 0.12);
    color: #ef4444;
    border: 1px solid rgba(239, 68, 68, 0.30);
    border-radius: 5px;
    padding: 3px 10px;
    min-height: 24px;
    font-size: 10.5px;
    font-weight: 700;
}}

QPushButton.cyber_btn_danger_compact:hover {{
    background-color: rgba(239, 68, 68, 0.25);
    border-color: rgba(239, 68, 68, 0.60);
    color: #ffffff;
}}

/* -------------------------------------------------------------
   5. LA TERMINAL TÁCTICA
------------------------------------------------------------- */
QFrame#cyber_terminal, QFrame.cyber_terminal_frame {{
    background-color: {p["TERMINAL_BG"]};
    border: 1px solid {p["BORDER_SUBTLE"]};
    border-radius: 10px;
}}

QWidget.terminal_header {{
    background-color: {p["TERMINAL_HEADER"]};
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    border-bottom: 1px solid {p["BORDER_SUBTLE"]};
}}

QLabel.terminal_prompt {{
    color: {p["TERMINAL_PROMPT"]};
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 700;
}}

QTextEdit.cyber_terminal {{
    background-color: {p["TERMINAL_BG"]};
    color: {p["TERMINAL_TEXT"]};
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 11.5px;
    line-height: 1.5;
    border: none;
    padding: 10px 14px;
}}

QWidget.terminal_input_bar {{
    background-color: {p["TERMINAL_HEADER"]};
    border-bottom-left-radius: 10px;
    border-bottom-right-radius: 10px;
    border-top: 1px solid {p["BORDER_SUBTLE"]};
}}

/* -------------------------------------------------------------
   6. VISOR DE DOCUMENTACIÓN & README (FONDO NEGRO SALVO EN CLARO)
------------------------------------------------------------- */
QTextEdit.markdown_viewer {{
    background-color: {p["MARKDOWN_BG"]};
    color: {p["MARKDOWN_TEXT"]};
    border: 1px solid {p["MARKDOWN_BORDER"]};
    border-radius: 8px;
    padding: 14px;
    font-family: 'Inter', -apple-system, sans-serif;
    font-size: 12px;
    line-height: 1.6;
}}

/* -------------------------------------------------------------
   7. BARRAS (SCROLLBARS, SPLITTERS, PROGRESO)
------------------------------------------------------------- */
QScrollBar:vertical, QScrollBar:horizontal {{
    background: transparent;
    width: 7px;
    height: 7px;
    margin: 0;
}}

QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
    background: {p["BORDER_MEDIUM"]};
    border-radius: 3px;
    min-height: 24px;
    min-width: 24px;
}}

QScrollBar::handle:hover {{
    background: {p["BORDER_STRONG"]};
}}

QScrollBar::add-line, QScrollBar::sub-line {{
    width: 0px;
    height: 0px;
}}

QSplitter::handle {{
    background-color: {p["BORDER_SUBTLE"]};
}}

QSplitter::handle:hover {{
    background-color: {p["BORDER_MEDIUM"]};
}}

QProgressBar {{
    background-color: {p["PROGRESS_BG"]};
    border: 1px solid {p["BORDER_SUBTLE"]};
    border-radius: 4px;
    text-align: center;
    color: {p["TEXT_TITLES"]};
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 700;
}}

QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {p["PROGRESS_START"]}, stop:1 {p["PROGRESS_END"]});
    border-radius: 3px;
}}

QProgressBar.filament_bar, QProgressBar[class="filament_bar"] {{
    background-color: {p["PROGRESS_BG"]};
    border: none;
    border-radius: 1px;
    max-height: 4px;
    min-height: 3px;
}}

QProgressBar.filament_bar::chunk, QProgressBar[class="filament_bar"]::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {p["PROGRESS_START"]}, stop:1 {p["PROGRESS_END"]});
    border-radius: 1px;
}}

/* -------------------------------------------------------------
   8. ENTRADAS DE TEXTO & CONTROLES
------------------------------------------------------------- */
QLineEdit, QTextEdit, QComboBox, QDoubleSpinBox {{
    background-color: {p["BG_INPUT"]};
    border: 1px solid {p["BORDER_SUBTLE"]};
    border-radius: 6px;
    color: {p["TEXT_TITLES"]};
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    padding: 6px 10px;
}}

QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QDoubleSpinBox:focus {{
    border-color: {p["BORDER_STRONG"]};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox QAbstractItemView {{
    background-color: {p["BG_SURFACE"]};
    color: {p["TEXT_TITLES"]};
    border: 1px solid {p["BORDER_MEDIUM"]};
    selection-background-color: {p["ACCENT_PILL"]};
    selection-color: {p["TEXT_TITLES"]};
    outline: none;
}}

/* Badges y etiquetas */
QLabel.badge_staged {{
    color: {p["TEXT_TITLES"]};
    background-color: {p["ACCENT_PILL"]};
    border: 1px solid {p["BORDER_MEDIUM"]};
    border-radius: 3px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 8.5px;
    font-weight: 800;
    padding: 2px 6px;
}}

QLabel.badge_pending {{
    color: {p["TEXT_MUTED"]};
    background-color: {p["BG_HIGHLIGHT"]};
    border: 1px solid {p["BORDER_SUBTLE"]};
    border-radius: 3px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 8.5px;
    font-weight: 700;
    padding: 2px 6px;
}}

QLabel.badge_telemetry {{
    color: {p["TEXT_BODY"]};
    background-color: {p["BG_HIGHLIGHT"]};
    border: 1px solid {p["BORDER_SUBTLE"]};
    border-radius: 5px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10.5px;
    font-weight: 600;
    padding: 4px 10px;
}}

/* Filas de workspace y ramas */
QFrame.workspace_file_row, QFrame.branch_item_row, QFrame.env_item_row {{
    background-color: {p["BG_HIGHLIGHT"]};
    border: 1px solid {p["BORDER_SUBTLE"]};
    border-radius: 6px;
}}

QFrame.workspace_file_row:hover, QFrame.branch_item_row:hover, QFrame.env_item_row:hover {{
    background-color: {p["BG_SURFACE_HOVER"]};
    border-color: {p["BORDER_MEDIUM"]};
}}

QFrame.branch_item_row_active, QFrame.env_item_row_active {{
    background-color: {p["ACCENT_PILL"]};
    border: 1px solid {p["BORDER_STRONG"]};
    border-radius: 6px;
}}

/* Radio Buttons & Checkboxes */
QRadioButton {{
    color: {p["TEXT_BODY"]};
    spacing: 8px;
    font-size: 11.5px;
    font-weight: 500;
    background-color: transparent;
}}

QRadioButton:hover {{
    color: {p["TEXT_TITLES"]};
}}

QRadioButton::indicator {{
    width: 15px;
    height: 15px;
    border: 1px solid {p["BORDER_MEDIUM"]};
    border-radius: 8px;
    background-color: {p["BG_SURFACE"]};
}}

QRadioButton::indicator:hover {{
    border-color: {p["TEXT_TITLES"]};
}}

QRadioButton::indicator:checked {{
    background-color: {p["TEXT_TITLES"]};
    border: 4px solid {p["BG_CANVAS"]};
}}

QCheckBox {{
    color: {p["TEXT_BODY"]};
    spacing: 8px;
    font-size: 11.5px;
    background-color: transparent;
}}

QCheckBox:hover {{
    color: {p["TEXT_TITLES"]};
}}

QCheckBox::indicator {{
    width: 15px;
    height: 15px;
    border: 1px solid {p["BORDER_MEDIUM"]};
    border-radius: 3px;
    background-color: {p["BG_SURFACE"]};
}}

QCheckBox::indicator:hover {{
    border-color: {p["TEXT_TITLES"]};
}}

QCheckBox::indicator:checked {{
    background-color: {p["TEXT_TITLES"]};
    border: 3px solid {p["BG_CANVAS"]};
}}

/* -------------------------------------------------------------
   9. GRAFO DE RAMAS & COMMITS
------------------------------------------------------------- */
QGraphicsView.git_graph_view, QGraphicsView#git_graph_view {{
    background-color: {p["GRAPH_CANVAS_BG"]};
    border: 1px solid {p["BORDER_SUBTLE"]};
    border-radius: 8px;
}}

QFrame#CommitHoverCard {{
    background-color: {p["BG_SURFACE"]};
    border: 1px solid {p["BORDER_MEDIUM"]};
    border-radius: 8px;
}}
"""


def generate_monochrome_stylesheet() -> str:
    """Compatibilidad retrospectiva: genera la hoja de estilos monocromática (oscuro)."""
    return generate_theme_stylesheet("oscuro")
