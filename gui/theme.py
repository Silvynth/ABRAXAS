#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS | DYNAMIC THEME SYSTEM (COLOR PALETTES & QSS)
# =====================================================================

import os
import json

def get_system_theme_palette():
    """Detecta y genera la paleta de colores activa del sistema / Noctalia."""
    noctalia_file = os.path.expanduser("~/.config/noctalia/colors.json")
    if os.path.exists(noctalia_file):
        try:
            with open(noctalia_file, "r", encoding="utf-8") as f:
                c = json.load(f)
                return {
                    "name": "Sincronizado con Sistema (Noctalia Dinámico)",
                    "BG_MAIN": c.get("mSurface", "#0d0e12"),
                    "BG_SIDEBAR": c.get("mSurfaceVariant", "#12131a"),
                    "BG_SURFACE": c.get("mSurfaceContainer", "#15161c"),
                    "BG_SURFACE_HOVER": c.get("mSurfaceContainerHigh", "#1c1d24"),
                    "BG_INPUT": c.get("mSurfaceContainerLowest", "#0f1015"),
                    "BORDER_BASE": c.get("mOutline", "#22242e"),
                    "BORDER_FOCUS": c.get("mPrimary", "#6366f1"),
                    "TEXT_PRIMARY": c.get("mOnSurface", "#f3f4f6"),
                    "TEXT_SECONDARY": c.get("mOnSurfaceVariant", "#9ca3af"),
                    "TEXT_MUTED": c.get("mOutlineVariant", "#6b7280"),
                    "ACCENT": c.get("mPrimary", "#6366f1"),
                    "ACCENT_HOVER": c.get("mSecondary", "#4f46e5"),
                    "ACCENT_LIGHT": c.get("mPrimaryContainer", "#e0e7ff"),
                    "CYAN": c.get("mTertiary", "#06b6d4"),
                    "SUCCESS": "#10b981",
                    "WARNING": c.get("mError", "#f59e0b")
                }
        except Exception:
            pass
    return None

THEMES = {
    "system_sync": {
        "name": "🔄 Sincronizar con Sistema (Auto / Noctalia)",
        "BG_MAIN": "#0d0e12",
        "BG_SIDEBAR": "#12131a",
        "BG_SURFACE": "#15161c",
        "BG_SURFACE_HOVER": "#1c1d24",
        "BG_INPUT": "#0f1015",
        "BORDER_BASE": "#22242e",
        "BORDER_FOCUS": "#6366f1",
        "TEXT_PRIMARY": "#f3f4f6",
        "TEXT_SECONDARY": "#9ca3af",
        "TEXT_MUTED": "#6b7280",
        "ACCENT": "#6366f1",
        "ACCENT_HOVER": "#4f46e5",
        "ACCENT_LIGHT": "#e0e7ff",
        "CYAN": "#06b6d4",
        "SUCCESS": "#10b981",
        "WARNING": "#f59e0b"
    },
    "noctalia": {
        "name": "Noctalia Minimal (Violeta / Índigo)",
        "BG_MAIN": "#0d0e12",
        "BG_SIDEBAR": "#12131a",
        "BG_SURFACE": "#15161c",
        "BG_SURFACE_HOVER": "#1c1d24",
        "BG_INPUT": "#0f1015",
        "BORDER_BASE": "#22242e",
        "BORDER_FOCUS": "#6366f1",
        "TEXT_PRIMARY": "#f3f4f6",
        "TEXT_SECONDARY": "#9ca3af",
        "TEXT_MUTED": "#6b7280",
        "ACCENT": "#6366f1",
        "ACCENT_HOVER": "#4f46e5",
        "ACCENT_LIGHT": "#e0e7ff",
        "CYAN": "#06b6d4",
        "SUCCESS": "#10b981",
        "WARNING": "#f59e0b"
    },
    "dark_cyberpunk": {
        "name": "Dark Cyberpunk (Cian Neón / Esmeralda)",
        "BG_MAIN": "#080c10",
        "BG_SIDEBAR": "#0d131a",
        "BG_SURFACE": "#101822",
        "BG_SURFACE_HOVER": "#182433",
        "BG_INPUT": "#0a0f16",
        "BORDER_BASE": "#1e2e3d",
        "BORDER_FOCUS": "#00f2fe",
        "TEXT_PRIMARY": "#e0f7fa",
        "TEXT_SECONDARY": "#80deea",
        "TEXT_MUTED": "#4ba3b5",
        "ACCENT": "#00f2fe",
        "ACCENT_HOVER": "#00c4cc",
        "ACCENT_LIGHT": "#e0f7fa",
        "CYAN": "#00f2fe",
        "SUCCESS": "#00e676",
        "WARNING": "#ffb300"
    },
    "monochrome": {
        "name": "Monocromo Puro (Gris Neutro & Acero)",
        "BG_MAIN": "#111111",
        "BG_SIDEBAR": "#181818",
        "BG_SURFACE": "#1f1f1f",
        "BG_SURFACE_HOVER": "#2a2a2a",
        "BG_INPUT": "#141414",
        "BORDER_BASE": "#333333",
        "BORDER_FOCUS": "#e5e5e5",
        "TEXT_PRIMARY": "#ffffff",
        "TEXT_SECONDARY": "#b3b3b3",
        "TEXT_MUTED": "#737373",
        "ACCENT": "#e5e5e5",
        "ACCENT_HOVER": "#cccccc",
        "ACCENT_LIGHT": "#ffffff",
        "CYAN": "#d4d4d4",
        "SUCCESS": "#a3e635",
        "WARNING": "#facc15"
    }
}

def generate_stylesheet(theme_key="noctalia"):
    if theme_key == "system_sync":
        t = get_system_theme_palette() or THEMES["noctalia"]
    else:
        t = THEMES.get(theme_key, THEMES["noctalia"])
        
    return f"""
QWidget {{
    background-color: {t["BG_MAIN"]};
    color: {t["TEXT_PRIMARY"]};
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    font-size: 13px;
}}

QLabel {{
    background-color: transparent;
}}

/* Sidebar Frame */
QFrame.sidebar {{
    background-color: {t["BG_SIDEBAR"]};
    border-right: 1px solid {t["BORDER_BASE"]};
}}

/* Nav Buttons */
QPushButton.nav_btn {{
    background-color: transparent;
    border: none;
    border-radius: 8px;
    color: {t["TEXT_SECONDARY"]};
    padding: 10px 14px;
    font-size: 13px;
    font-weight: 600;
    text-align: left;
}}

QPushButton.nav_btn:hover {{
    background-color: rgba(99, 102, 241, 0.12);
    color: {t["ACCENT_LIGHT"]};
}}

QPushButton.nav_btn:checked {{
    background-color: {t["ACCENT"]};
    color: {t["BG_MAIN"] if theme_key == "monochrome" else "#ffffff"};
    font-weight: 700;
}}

/* Surface Card */
QFrame.surface {{
    background-color: {t["BG_SURFACE"]};
    border: 1px solid {t["BORDER_BASE"]};
    border-radius: 10px;
    padding: 16px;
}}

QLabel.page_title {{
    color: {t["TEXT_PRIMARY"]};
    font-size: 22px;
    font-weight: 700;
    letter-spacing: -0.5px;
}}

QLabel.page_subtitle {{
    color: {t["TEXT_SECONDARY"]};
    font-size: 13px;
}}

QLabel.brand_title {{
    font-size: 20px;
    font-weight: 800;
    color: {t["TEXT_PRIMARY"]};
    letter-spacing: 1px;
}}

QLabel.brand_subtitle {{
    font-size: 11px;
    color: {t["TEXT_MUTED"]};
    font-weight: 500;
}}

QLabel.section_title {{
    font-size: 14px;
    font-weight: 700;
    color: {t["ACCENT"]};
}}

QLabel.status_ok {{
    color: {t["SUCCESS"]};
    font-weight: 600;
    font-size: 12px;
}}

QLabel.card_desc {{
    color: {t["TEXT_SECONDARY"]};
    font-size: 14px;
    line-height: 1.5;
}}

QLabel.version_badge {{
    background-color: #1e1f29;
    color: {t["CYAN"]};
    border: 1px solid rgba(6, 182, 212, 0.3);
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}}

/* Unified Project List Container & Rows */
QFrame.project_list_card {{
    background-color: {t["BG_SURFACE"]};
    border: 1px solid {t["BORDER_BASE"]};
    border-radius: 10px;
    padding: 0px;
}}

QFrame.project_row {{
    background-color: transparent;
    border-bottom: 1px solid {t["BORDER_BASE"]};
    border-left: 3px solid transparent;
    padding: 10px 14px;
}}

QFrame.project_row:hover {{
    background-color: rgba(99, 102, 241, 0.08);
}}

QFrame.project_row[selected="true"] {{
    background-color: rgba(99, 102, 241, 0.18);
    border-left: 3px solid {t["ACCENT"]};
}}

QFrame.project_row_last {{
    border-bottom: none;
}}

QLabel.project_name {{
    color: {t["TEXT_PRIMARY"]};
    font-size: 14px;
    font-weight: 700;
}}

QLabel.project_path {{
    color: {t["TEXT_MUTED"]};
    font-size: 12px;
    font-family: monospace;
}}

QLabel.badge_dir {{
    background-color: rgba(99, 102, 241, 0.12);
    color: {t["ACCENT_LIGHT"]};
    border: 1px solid rgba(99, 102, 241, 0.25);
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}}

QLabel.count_badge {{
    background-color: {t["BG_INPUT"]};
    color: {t["CYAN"]};
    border: 1px solid {t["BORDER_BASE"]};
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 600;
}}

/* Elegant Minimal Scrollbars */
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0px;
}}
QScrollBar::handle:vertical {{
    background: {t["BORDER_BASE"]};
    min-height: 20px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical:hover {{
    background: {t["ACCENT"]};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 6px;
    margin: 0px;
}}
QScrollBar::handle:horizontal {{
    background: {t["BORDER_BASE"]};
    min-width: 20px;
    border-radius: 3px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {t["ACCENT"]};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* Tree View */
QTreeView {{
    background-color: {t["BG_INPUT"]};
    border: 1px solid {t["BORDER_BASE"]};
    border-radius: 8px;
    padding: 6px;
    color: {t["TEXT_PRIMARY"]};
    outline: 0px;
    font-size: 13px;
}}

QTreeView::item {{
    padding: 4px 6px;
    border-radius: 4px;
}}

QTreeView::item:hover {{
    background-color: rgba(99, 102, 241, 0.15);
    color: {t["ACCENT_LIGHT"]};
}}

QTreeView::item:selected {{
    background-color: rgba(99, 102, 241, 0.35);
    color: #ffffff;
}}

QHeaderView::section {{
    background-color: {t["BG_SURFACE"]};
    color: {t["TEXT_SECONDARY"]};
    padding: 6px 8px;
    border: none;
    border-bottom: 1px solid {t["BORDER_BASE"]};
    font-weight: 600;
    font-size: 11px;
}}

/* Splitter */
QSplitter::handle {{
    background-color: {t["BORDER_BASE"]};
    height: 4px;
    margin: 4px 0px;
    border-radius: 2px;
}}

QSplitter::handle:hover {{
    background-color: {t["ACCENT"]};
}}

/* Input Fields */
QLineEdit {{
    background-color: {t["BG_INPUT"]};
    border: 1px solid {t["BORDER_BASE"]};
    border-radius: 7px;
    padding: 8px 12px;
    color: {t["TEXT_PRIMARY"]};
    font-size: 13px;
    selection-background-color: {t["ACCENT"]};
}}

QLineEdit:focus {{
    border: 1px solid {t["BORDER_FOCUS"]};
}}

/* Buttons */
QPushButton {{
    background-color: {t["BG_SURFACE"]};
    border: 1px solid {t["BORDER_BASE"]};
    border-radius: 7px;
    color: {t["TEXT_PRIMARY"]};
    padding: 8px 16px;
    font-weight: 600;
    font-size: 13px;
}}

QPushButton:hover {{
    background-color: {t["BG_SURFACE_HOVER"]};
    border-color: {t["BORDER_FOCUS"]};
    color: {t["TEXT_PRIMARY"]};
}}

QPushButton.primary {{
    background-color: {t["ACCENT"]};
    color: {t["BG_MAIN"] if theme_key == "monochrome" else "#ffffff"};
    border: none;
    border-radius: 7px;
    padding: 9px 20px;
    font-weight: 600;
    font-size: 13px;
}}

QPushButton.primary:hover {{
    background-color: {t["ACCENT_HOVER"]};
}}

QPushButton.browse {{
    background-color: {t["BG_SURFACE"]};
    border: 1px solid {t["BORDER_BASE"]};
    border-radius: 7px;
    padding: 8px 14px;
    font-size: 12px;
    font-weight: 500;
}}

QPushButton.browse:hover {{
    border-color: {t["BORDER_FOCUS"]};
    color: {t["ACCENT_LIGHT"]};
}}

/* Action Mode Buttons (Verde, Amarillo, Morado, Rojo) */
QPushButton.btn_mode_green {{
    background-color: rgba(16, 185, 129, 0.12);
    color: #10b981;
    border: 1px solid rgba(16, 185, 129, 0.35);
    border-radius: 7px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 600;
}}

QPushButton.btn_mode_green:hover {{
    background-color: rgba(16, 185, 129, 0.22);
    border-color: #10b981;
    color: #34d399;
}}

QPushButton.btn_mode_green:checked {{
    background-color: #10b981;
    color: #ffffff;
    border-color: #10b981;
    font-weight: 700;
}}

QPushButton.btn_mode_yellow {{
    background-color: rgba(245, 158, 11, 0.12);
    color: #f59e0b;
    border: 1px solid rgba(245, 158, 11, 0.35);
    border-radius: 7px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 600;
}}

QPushButton.btn_mode_yellow:hover {{
    background-color: rgba(245, 158, 11, 0.22);
    border-color: #f59e0b;
    color: #fbbf24;
}}

QPushButton.btn_mode_yellow:checked {{
    background-color: #f59e0b;
    color: #0d0e12;
    border-color: #f59e0b;
    font-weight: 700;
}}

QPushButton.btn_mode_purple {{
    background-color: rgba(168, 85, 247, 0.12);
    color: #c084fc;
    border: 1px solid rgba(168, 85, 247, 0.35);
    border-radius: 7px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 600;
}}

QPushButton.btn_mode_purple:hover {{
    background-color: rgba(168, 85, 247, 0.22);
    border-color: #a855f7;
    color: #e9d5ff;
}}

QPushButton.btn_mode_purple:checked {{
    background-color: #a855f7;
    color: #ffffff;
    border-color: #a855f7;
    font-weight: 700;
}}

QPushButton.btn_mode_red {{
    background-color: rgba(239, 68, 68, 0.12);
    color: #f87171;
    border: 1px solid rgba(239, 68, 68, 0.35);
    border-radius: 7px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 600;
}}

QPushButton.btn_mode_red:hover {{
    background-color: rgba(239, 68, 68, 0.22);
    border-color: #ef4444;
    color: #fca5a5;
}}

QPushButton.btn_mode_red:checked {{
    background-color: #ef4444;
    color: #ffffff;
    border-color: #ef4444;
    font-weight: 700;
}}

/* CheckBoxes */
QCheckBox {{
    color: {t["TEXT_PRIMARY"]};
    spacing: 10px;
    font-size: 13px;
    font-weight: 500;
    background-color: transparent;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 1px solid {t["BORDER_BASE"]};
    border-radius: 5px;
    background-color: {t["BG_INPUT"]};
}}

QCheckBox::indicator:hover {{
    border-color: {t["BORDER_FOCUS"]};
}}

QCheckBox::indicator:checked {{
    background-color: {t["ACCENT"]};
    border-color: {t["ACCENT"]};
    image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='3.5' stroke-linecap='round' stroke-linejoin='round'><polyline points='20 6 9 17 4 12'></polyline></svg>");
}}

/* Combo Dropdown */
QComboBox {{
    background-color: {t["BG_INPUT"]};
    border: 1px solid {t["BORDER_BASE"]};
    border-radius: 8px;
    padding: 8px 14px;
    color: {t["TEXT_PRIMARY"]};
    font-size: 13px;
    font-weight: 500;
}}

QComboBox:hover {{
    border-color: {t["BORDER_FOCUS"]};
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 30px;
    border: none;
}}

QComboBox::down-arrow {{
    image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%236366f1' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'><polyline points='6 9 12 15 18 9'></polyline></svg>");
    width: 12px;
    height: 12px;
}}

QComboBox QAbstractItemView {{
    background-color: {t["BG_SURFACE"]};
    border: 1px solid {t["BORDER_BASE"]};
    border-radius: 8px;
    color: {t["TEXT_PRIMARY"]};
    selection-background-color: rgba(99, 102, 241, 0.25);
    selection-color: #ffffff;
    outline: 0px;
    padding: 4px;
}}

QComboBox QAbstractItemView::item {{
    min-height: 28px;
    padding: 6px 10px;
    color: {t["TEXT_PRIMARY"]};
    border-radius: 4px;
    background-color: transparent;
}}

QComboBox QAbstractItemView::item:hover {{
    background-color: rgba(99, 102, 241, 0.20);
    color: {t["ACCENT_LIGHT"]};
}}

QComboBox QAbstractItemView::item:selected {{
    background-color: rgba(99, 102, 241, 0.30);
    color: #ffffff;
}}
"""

