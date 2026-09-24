"""
❖ ABRAXAS 2.0 | Foundation: Pure Monochromatic Theme Engine (Haute Horlogerie)
Diseño de alto contraste y cero distracciones: grises puros, carbón mate, titanio y blanco polar.
"""

from typing import Optional

MONOCHROME_PALETTE = {
    "BG_CANVAS": "#0a0b0e",           # Fondo general profundo
    "BG_SIDEBAR": "#101115",          # Barra lateral sólida
    "BG_SURFACE": "#14161c",          # Tarjetas y contenedores principales
    "BG_SURFACE_HOVER": "#1a1c24",    # Hover sutil en contenedores
    "BG_INPUT": "#0c0d10",            # Entradas de texto y terminal
    "BG_HIGHLIGHT": "rgba(255, 255, 255, 0.04)", # Fondos de celdas secundarias
    
    "BORDER_SUBTLE": "rgba(255, 255, 255, 0.07)",  # Borde por defecto
    "BORDER_MEDIUM": "rgba(255, 255, 255, 0.14)",  # Borde hover / enfocado
    "BORDER_STRONG": "#ffffff",                     # Borde activo / seleccionado
    
    "TEXT_TITLES": "#ffffff",          # Blanco puro para titulares
    "TEXT_BODY": "#e2e8f0",            # Platino para lectura principal
    "TEXT_MUTED": "#9ca3af",           # Gris medio para subtítulos
    "TEXT_MICRO": "#64748b",           # Titanio oscuro para micro-tags (uppercase)
    
    "ACCENT_ACTIVE": "#ffffff",        # Blanco brillante como acento principal
    "ACCENT_PILL": "rgba(255, 255, 255, 0.08)", # Fondo de botones seleccionados
}

def generate_monochrome_stylesheet() -> str:
    """Genera la hoja de estilos QSS puramente monocromática para Abraxas 2.0."""
    p = MONOCHROME_PALETTE
    return f"""
/* =====================================================================
   ❖ ABRAXAS 2.0 | MONOCHROMATIC STYLESHEET (CERO DISTRACCIONES)
===================================================================== */

* {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    color: {p["TEXT_BODY"]};
}}

QWidget {{
    background-color: transparent;
    outline: none;
}}

/* Fondo raíz de la ventana */
QWidget#NeosShellWindow, QWidget#content_area {{
    background-color: {p["BG_CANVAS"]};
}}

/* -------------------------------------------------------------
   1. SIDEBAR
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

/* Botones de navegación en Sidebar */
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
   2. TARJETAS Y CONTENEDORES (SECTOR CARDS)
------------------------------------------------------------- */
QFrame.sector_card {{
    background-color: {p["BG_SURFACE"]};
    border: 1px solid {p["BORDER_SUBTLE"]};
    border-radius: 12px;
}}

QFrame.sector_card:hover {{
    border: 1px solid {p["BORDER_MEDIUM"]};
}}

QLabel.sector_micro_tag {{
    color: {p["TEXT_MICRO"]};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    font-family: 'JetBrains Mono', monospace;
}}

QLabel.sector_title {{
    color: {p["TEXT_TITLES"]};
    font-size: 16px;
    font-weight: 700;
    letter-spacing: -0.2px;
}}

QLabel.sector_desc {{
    color: {p["TEXT_MUTED"]};
    font-size: 12.5px;
    line-height: 1.4;
}}

/* -------------------------------------------------------------
   3. BOTONES TÁCTICOS Y PÍLDORAS
------------------------------------------------------------- */
QPushButton.cyber_btn {{
    background-color: {p["BG_SURFACE"]};
    color: {p["TEXT_TITLES"]};
    border: 1px solid {p["BORDER_SUBTLE"]};
    border-radius: 7px;
    padding: 8px 16px;
    font-size: 12px;
    font-weight: 600;
}}

QPushButton.cyber_btn:hover {{
    background-color: {p["BG_SURFACE_HOVER"]};
    border: 1px solid {p["BORDER_MEDIUM"]};
}}

QPushButton.cyber_btn:pressed {{
    background-color: {p["TEXT_TITLES"]};
    color: {p["BG_CANVAS"]};
}}

QPushButton.cyber_btn_primary {{
    background-color: {p["TEXT_TITLES"]};
    color: {p["BG_CANVAS"]};
    border: 1px solid {p["TEXT_TITLES"]};
    border-radius: 7px;
    padding: 8px 18px;
    font-size: 12px;
    font-weight: 700;
}}

QPushButton.cyber_btn_primary:hover {{
    background-color: #d1d5db;
    border-color: #d1d5db;
}}

/* -------------------------------------------------------------
   4. TERMINAL MONOCROMÁTICA
------------------------------------------------------------- */
QTextEdit.cyber_terminal {{
    background-color: {p["BG_INPUT"]};
    border: 1px solid {p["BORDER_SUBTLE"]};
    border-radius: 8px;
    color: #e5e7eb;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    line-height: 1.5;
    padding: 12px;
}}

/* -------------------------------------------------------------
   5. SCROLLBARS TÁCTICAS
------------------------------------------------------------- */
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: rgba(255, 255, 255, 0.15);
    border-radius: 3px;
    min-height: 24px;
}}

QScrollBar::handle:vertical:hover {{
    background: rgba(255, 255, 255, 0.3);
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
"""
