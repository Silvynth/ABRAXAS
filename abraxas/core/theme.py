"""
❖ ABRAXAS 2.0 | Foundation: Pure Monochromatic Theme Engine (Haute Horlogerie)
Diseño de alto contraste y cero distracciones: grises puros, carbón mate, titanio y blanco polar.
Todas las vistas heredan y consumen estas clases para garantizar coherencia visual absoluta.
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
   ❖ ABRAXAS 2.0 | MONOCHROMATIC STYLESHEET (HAUTE HORLOGERIE)
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
   2. TARJETAS Y CONTENEDORES (SECTOR CARDS)
------------------------------------------------------------- */
QFrame.sector_card {{
    background-color: {p["BG_SURFACE"]};
    border: 1px solid {p["BORDER_SUBTLE"]};
    border-radius: 10px;
}}

QFrame.sector_card:hover {{
    border: 1px solid {p["BORDER_MEDIUM"]};
}}

QLabel.sector_micro_tag {{
    color: {p["TEXT_MICRO"]};
    font-size: 9.5px;
    font-weight: 700;
    letter-spacing: 1.1px;
    text-transform: uppercase;
    font-family: 'JetBrains Mono', monospace;
}}

QLabel.sector_title {{
    color: {p["TEXT_TITLES"]};
    font-size: 14px;
    font-weight: 800;
    letter-spacing: -0.2px;
}}

QLabel.sector_desc {{
    color: {p["TEXT_MUTED"]};
    font-size: 12px;
    line-height: 1.4;
}}

/* -------------------------------------------------------------
   3. BOTONES TÁCTICOS Y PÍLDORAS (CERO TEXTO CORTADO)
------------------------------------------------------------- */
QPushButton.cyber_btn {{
    background-color: {p["BG_SURFACE"]};
    color: {p["TEXT_BODY"]};
    border: 1px solid {p["BORDER_SUBTLE"]};
    border-radius: 6px;
    padding: 5px 14px;
    min-height: 30px;
    font-size: 11.5px;
    font-weight: 600;
}}

QPushButton.cyber_btn:hover {{
    background-color: {p["BG_SURFACE_HOVER"]};
    color: {p["TEXT_TITLES"]};
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
    border-radius: 6px;
    padding: 5px 16px;
    min-height: 30px;
    font-size: 11.5px;
    font-weight: 700;
}}

QPushButton.cyber_btn_primary:hover {{
    background-color: #d1d5db;
    border-color: #d1d5db;
}}

QPushButton.cyber_btn_primary:pressed {{
    background-color: #9ca3af;
}}

/* Botones compactos para barras de herramientas */
QPushButton.cyber_btn_compact {{
    background-color: {p["BG_SURFACE"]};
    color: {p["TEXT_BODY"]};
    border: 1px solid {p["BORDER_SUBTLE"]};
    border-radius: 5px;
    padding: 3px 12px;
    min-height: 26px;
    font-size: 11px;
    font-weight: 600;
}}

QPushButton.cyber_btn_compact:hover {{
    background-color: {p["BG_SURFACE_HOVER"]};
    color: {p["TEXT_TITLES"]};
    border-color: {p["BORDER_MEDIUM"]};
}}

QPushButton.cyber_btn_compact:pressed {{
    background-color: {p["TEXT_TITLES"]};
    color: {p["BG_CANVAS"]};
}}

/* Botones de conmutación / Píldoras selectoras (SemVer, Ligero/Pesado) */
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
    background-color: rgba(255, 255, 255, 0.20);
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.55);
    font-weight: 800;
}}

QPushButton.cyber_btn_toggle:disabled {{
    background-color: transparent;
    color: rgba(255, 255, 255, 0.25);
    border: 1px solid rgba(255, 255, 255, 0.08);
}}

/* Botón en estado de carga animada */
QPushButton.cyber_btn_loading {{
    background-color: {p["BG_SURFACE_HOVER"]};
    color: {p["TEXT_TITLES"]};
    border: 1px solid rgba(255, 255, 255, 0.25);
    border-radius: 6px;
    padding: 5px 14px;
    min-height: 30px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 700;
}}

/* Botones cuadrados para iconos o acciones rápidas */
QPushButton.cyber_btn_icon {{
    background-color: rgba(255, 255, 255, 0.03);
    color: {p["TEXT_MUTED"]};
    border: 1px solid {p["BORDER_SUBTLE"]};
    border-radius: 4px;
    font-size: 11px;
    font-weight: 700;
    min-width: 22px;
    min-height: 22px;
    max-width: 22px;
    max-height: 22px;
    padding: 0;
}}

QPushButton.cyber_btn_icon:hover {{
    background-color: rgba(255, 255, 255, 0.12);
    color: {p["TEXT_TITLES"]};
    border-color: {p["BORDER_MEDIUM"]};
}}

QPushButton.cyber_btn_icon_active {{
    background-color: rgba(255, 255, 255, 0.10);
    color: {p["TEXT_TITLES"]};
    border: 1px solid rgba(255, 255, 255, 0.22);
    border-radius: 4px;
    font-size: 10px;
    font-weight: 800;
    min-width: 22px;
    min-height: 22px;
    max-width: 22px;
    max-height: 22px;
    padding: 0;
}}

QPushButton.cyber_btn_icon_active:hover {{
    background-color: rgba(255, 255, 255, 0.20);
    border-color: #ffffff;
}}

/* -------------------------------------------------------------
   4. BADGES Y ETIQUETAS DE ESTADO MONOCROMÁTICAS
------------------------------------------------------------- */
QLabel.badge_staged {{
    color: #ffffff;
    background-color: rgba(255, 255, 255, 0.12);
    border: 1px solid rgba(255, 255, 255, 0.28);
    border-radius: 3px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 8.5px;
    font-weight: 800;
    padding: 2px 6px;
}}

QLabel.badge_pending {{
    color: #94a3b8;
    background-color: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 3px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 8.5px;
    font-weight: 700;
    padding: 2px 6px;
}}

QLabel.badge_telemetry {{
    color: {p["TEXT_BODY"]};
    background-color: rgba(255, 255, 255, 0.04);
    border: 1px solid {p["BORDER_SUBTLE"]};
    border-radius: 5px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10.5px;
    font-weight: 600;
    padding: 4px 10px;
}}

/* -------------------------------------------------------------
   5. FILAS DE ARCHIVOS DEL WORKSPACE
------------------------------------------------------------- */
QFrame.workspace_file_row {{
    background-color: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 5px;
}}

QFrame.workspace_file_row:hover {{
    background-color: rgba(255, 255, 255, 0.05);
    border-color: rgba(255, 255, 255, 0.12);
}}

QLabel.file_path_label {{
    color: {p["TEXT_BODY"]};
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 600;
}}

/* -------------------------------------------------------------
   6. ENTRADAS DE TEXTO MONOCROMÁTICAS
------------------------------------------------------------- */
QLineEdit.cyber_input, QTextEdit.cyber_input {{
    background-color: {p["BG_INPUT"]};
    border: 1px solid {p["BORDER_SUBTLE"]};
    border-radius: 6px;
    color: {p["TEXT_TITLES"]};
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    padding: 6px 10px;
}}

QLineEdit.cyber_input:focus, QTextEdit.cyber_input:focus {{
    border-color: rgba(255, 255, 255, 0.35);
}}

/* -------------------------------------------------------------
   7. TERMINAL MONOCROMÁTICA
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
   8. SCROLLBARS TÁCTICAS
------------------------------------------------------------- */
QScrollArea.clean_scroll {{
    border: none;
    background: transparent;
}}

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

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

/* -------------------------------------------------------------
   9. GESTOR DE RAMAS (SECTOR 1.2)
------------------------------------------------------------- */
QFrame.branch_item_row {{
    background-color: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 6px;
}}

QFrame.branch_item_row:hover {{
    background-color: rgba(255, 255, 255, 0.05);
    border-color: rgba(255, 255, 255, 0.12);
}}

QFrame.branch_item_row_active {{
    background-color: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.22);
    border-radius: 6px;
}}

QFrame.branch_item_row_selected {{
    background-color: rgba(255, 255, 255, 0.12);
    border: 1px solid rgba(255, 255, 255, 0.35);
    border-radius: 6px;
}}

QPushButton.cyber_btn_danger {{
    background-color: rgba(255, 255, 255, 0.03);
    color: #e2e8f0;
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 6px;
    padding: 6px 14px;
    min-height: 30px;
    font-size: 11px;
    font-weight: 700;
}}

QPushButton.cyber_btn_danger:hover {{
    background-color: rgba(255, 255, 255, 0.10);
    border-color: rgba(255, 255, 255, 0.35);
    color: #ffffff;
}}

QPushButton.cyber_btn_danger:pressed {{
    background-color: #ffffff;
    color: #000000;
}}

QPushButton.cyber_btn_danger_compact {{
    background-color: rgba(255, 255, 255, 0.03);
    color: #e2e8f0;
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 5px;
    padding: 3px 10px;
    min-height: 26px;
    font-size: 10.5px;
    font-weight: 700;
}}

QPushButton.cyber_btn_danger_compact:hover {{
    background-color: rgba(255, 255, 255, 0.12);
    border-color: rgba(255, 255, 255, 0.35);
    color: #ffffff;
}}

/* -------------------------------------------------------------
   10. MODAL DE CONFIRMACIÓN CRÍTICA
------------------------------------------------------------- */
QDialog.cyber_dialog {{
    background-color: {p["BG_CANVAS"]};
    border: 1px solid rgba(255, 255, 255, 0.20);
    border-radius: 10px;
}}

/* -------------------------------------------------------------
   11. PESTAÑAS TÁCTICAS (SECTOR 1.3)
------------------------------------------------------------- */
QTabWidget.cyber_tab_widget::pane {{
    border: 1px solid rgba(255, 255, 255, 0.08);
    background: rgba(255, 255, 255, 0.01);
    border-radius: 6px;
}}

QTabBar::tab {{
    background: rgba(255, 255, 255, 0.03);
    color: #94a3b8;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-bottom: none;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
    padding: 6px 14px;
    margin-right: 4px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10.5px;
    font-weight: 600;
}}

QTabBar::tab:selected {{
    background: rgba(255, 255, 255, 0.10);
    color: #ffffff;
    border-color: rgba(255, 255, 255, 0.25);
    font-weight: 700;
}}

QTabBar::tab:hover:!selected {{
    background: rgba(255, 255, 255, 0.06);
    color: #e2e8f0;
}}

/* -------------------------------------------------------------
   12. BADGES DE VISIBILIDAD & RADAR
------------------------------------------------------------- */
QLabel.badge_public {{
    color: #ffffff;
    background-color: rgba(255, 255, 255, 0.14);
    border: 1px solid rgba(255, 255, 255, 0.35);
    border-radius: 4px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 9.5px;
    font-weight: 800;
    padding: 3px 8px;
}}

QLabel.badge_private {{
    color: #cbd5e1;
    background-color: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.20);
    border-radius: 4px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 9.5px;
    font-weight: 800;
    padding: 3px 8px;
}}

/* -------------------------------------------------------------
   13. FILAS DE TRÁFICO DE COMMITS (AHEAD / BEHIND)
------------------------------------------------------------- */
QFrame.commit_traffic_row {{
    background-color: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 5px;
    padding: 2px 4px;
}}

QFrame.commit_traffic_row:hover {{
    background-color: rgba(255, 255, 255, 0.05);
    border-color: rgba(255, 255, 255, 0.15);
}}

/* -------------------------------------------------------------
   14. CONTROLES DE SELECCIÓN (RADIO BUTTONS & CHECKBOXES)
------------------------------------------------------------- */
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
   15. FILAS DE ENTORNOS, CONTENEDORES Y PUERTOS (SECTOR 2)
------------------------------------------------------------- */
QFrame.env_item_row {{
    background-color: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 6px;
    padding: 4px 8px;
}}

QFrame.env_item_row:hover {{
    background-color: rgba(255, 255, 255, 0.05);
    border-color: rgba(255, 255, 255, 0.12);
}}

QFrame.env_item_row_active {{
    background-color: rgba(255, 255, 255, 0.07);
    border: 1px solid rgba(255, 255, 255, 0.20);
    border-radius: 6px;
    padding: 4px 8px;
}}
"""

