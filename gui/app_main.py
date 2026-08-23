#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS | NEOS CONTROL CENTER (PySide6 Main GUI)
# =====================================================================

import sys
import os

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QLineEdit, QFileDialog, QStackedWidget, 
    QRadioButton, QCheckBox, QFrame, QScrollArea,
    QComboBox, QStyledItemDelegate
)
from PySide6.QtCore import Qt

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from core.setup import write_toml_dict, read_toml_dict, get_target_config_path
from core import get_version

import json

# =====================================================================
#  DYNAMIC THEME SYSTEM (COLOR PALETTES)
# =====================================================================
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

class NeosMainApp(QWidget):
    def __init__(self):
        super().__init__()
        self.app_version = get_version()
        self.setWindowTitle(f"ABRAXAS | NEOS Control Center (v{self.app_version})")
        self.setMinimumSize(940, 640)

        self.config_target = get_target_config_path()
        self.cfg = read_toml_dict(self.config_target)

        # Apply initial active theme
        initial_theme = self.cfg.get("abraxas", {}).get("theme", "noctalia")
        self.setStyleSheet(generate_stylesheet(initial_theme))

        self.init_ui()
        self.center_window()

    def center_window(self):
        qr = self.frameGeometry()
        cp = self.screen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def init_ui(self):
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # -------------------------------------------------------------
        # 1. SIDEBAR (NEOS MAIN MENU)
        # -------------------------------------------------------------
        sidebar = QFrame()
        sidebar.setProperty("class", "sidebar")
        sidebar.setFixedWidth(220)
        
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(16, 20, 16, 20)
        sb_layout.setSpacing(8)

        # Brand header
        lbl_brand = QLabel("❖ NEOS")
        lbl_brand.setProperty("class", "brand_title")
        
        lbl_subbrand = QLabel("ABRAXAS Control Center")
        lbl_subbrand.setProperty("class", "brand_subtitle")
        
        sb_layout.addWidget(lbl_brand)
        sb_layout.addWidget(lbl_subbrand)
        sb_layout.addSpacing(16)

        # 5 Main Menu Nav Buttons
        self.nav_buttons = []
        menu_items = [
            ("⚙  UMBRA", "Núcleo Operador & Kernel"),
            ("💻  LUMEN", "Motor Dev & IA Local"),
            ("📁  PROYECTOS", "Explorador de Repositorios"),
            ("🔄  ACTUALIZACIÓN", "Gestor de Paquetes"),
            ("🛠  CONFIG", "Ajustes de Sistema")
        ]

        for idx, (title, sub) in enumerate(menu_items):
            btn = QPushButton(title)
            btn.setProperty("class", "nav_btn")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(sub)
            btn.clicked.connect(lambda _, i=idx: self.switch_tab(i))
            self.nav_buttons.append(btn)
            sb_layout.addWidget(btn)

        sb_layout.addStretch()

        # Footer Badge
        lbl_ver = QLabel(f"v{self.app_version}")
        lbl_ver.setProperty("class", "version_badge")
        sb_layout.addWidget(lbl_ver)

        root_layout.addWidget(sidebar)

        # -------------------------------------------------------------
        # 2. MAIN CONTENT STACK
        # -------------------------------------------------------------
        content_area = QWidget()
        c_layout = QVBoxLayout(content_area)
        c_layout.setContentsMargins(28, 24, 28, 24)
        c_layout.setSpacing(16)

        self.stacked = QStackedWidget()

        # Page 0: UMBRA
        self.page_umbra = self.create_placeholder_page(
            "⚙ UMBRA", 
            "Núcleo Operador & Kernel", 
            "Mantenimiento del sistema, estado de Kernels y respaldos atómicos Btrfs (Snapshots)."
        )
        
        # Page 1: LUMEN
        self.page_lumen = self.create_placeholder_page(
            "💻 LUMEN", 
            "Motor Dev & IA Local", 
            "Gestión de flujos de desarrollo, Docker, entornos virtuales y asistencia de IA Ollama local."
        )

        # Page 2: PROYECTOS
        self.page_proyectos = self.create_placeholder_page(
            "📁 PROYECTOS", 
            "Explorador de Repositorios", 
            "Organizador e inspector visual de proyectos Git en tu espacio de trabajo."
        )

        # Page 3: ACTUALIZACIÓN
        self.page_actualizacion = self.create_placeholder_page(
            "🔄 ACTUALIZACIÓN", 
            "Centro de Actualizaciones", 
            "Semáforo de riesgo de paquetes pendientes e instalación segura de actualizaciones."
        )

        # Page 4: CONFIG
        self.page_config = self.create_config_page()

        self.stacked.addWidget(self.page_umbra)
        self.stacked.addWidget(self.page_lumen)
        self.stacked.addWidget(self.page_proyectos)
        self.stacked.addWidget(self.page_actualizacion)
        self.stacked.addWidget(self.page_config)

        c_layout.addWidget(self.stacked)
        root_layout.addWidget(content_area)

        # Select first tab by default
        self.switch_tab(0)

    def switch_tab(self, index):
        self.stacked.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

    def create_config_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # Header Title
        lbl_t = QLabel("🛠 CONFIG")
        lbl_t.setProperty("class", "page_title")
        lbl_sub = QLabel(f"Gestor de Configuración Activa ({self.config_target})")
        lbl_sub.setProperty("class", "page_subtitle")
        layout.addWidget(lbl_t)
        layout.addWidget(lbl_sub)

        # Scroll Area for all config sections
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        scroll_widget = QWidget()
        s_layout = QVBoxLayout(scroll_widget)
        s_layout.setContentsMargins(0, 0, 10, 0)
        s_layout.setSpacing(14)

        # -------------------------------------------------------------
        # Section 1: Rutas de Trabajo ([paths])
        # -------------------------------------------------------------
        card_paths = QFrame()
        card_paths.setProperty("class", "surface")
        l_paths = QVBoxLayout(card_paths)
        l_paths.setSpacing(10)

        lbl_sec1 = QLabel("📁 Rutas del Sistema ([paths])")
        lbl_sec1.setProperty("class", "section_title")
        l_paths.addWidget(lbl_sec1)

        # Projects Dir
        l_paths.addWidget(QLabel("Directorio raíz de proyectos:"))
        r_proj = QHBoxLayout()
        self.txt_cfg_proj = QLineEdit(self.cfg.get("paths", {}).get("projects_dir", "~/Proyectos"))
        btn_proj = QPushButton("Examinar")
        btn_proj.setProperty("class", "browse")
        btn_proj.clicked.connect(lambda: self.browse_folder(self.txt_cfg_proj))
        r_proj.addWidget(self.txt_cfg_proj)
        r_proj.addWidget(btn_proj)
        l_paths.addLayout(r_proj)

        # Vault Dir
        l_paths.addWidget(QLabel("Bóveda de notas / Obsidian:"))
        r_vault = QHBoxLayout()
        self.txt_cfg_vault = QLineEdit(self.cfg.get("paths", {}).get("vault_dir", "~/Vault"))
        btn_vault = QPushButton("Examinar")
        btn_vault.setProperty("class", "browse")
        btn_vault.clicked.connect(lambda: self.browse_folder(self.txt_cfg_vault))
        r_vault.addWidget(self.txt_cfg_vault)
        r_vault.addWidget(btn_vault)
        l_paths.addLayout(r_vault)

        # Snapshots Dir
        l_paths.addWidget(QLabel("Subvolumen de instantáneas Btrfs / Snapper:"))
        self.txt_cfg_snap = QLineEdit(self.cfg.get("paths", {}).get("snapshots_dir", "/.snapshots"))
        l_paths.addWidget(self.txt_cfg_snap)

        s_layout.addWidget(card_paths)

        # -------------------------------------------------------------
        # Section 2: Motor de Inteligencia Artificial ([ai])
        # -------------------------------------------------------------
        card_ai = QFrame()
        card_ai.setProperty("class", "surface")
        l_ai = QVBoxLayout(card_ai)
        l_ai.setSpacing(10)

        lbl_sec2 = QLabel("🧠 Motor de Asistencia IA Local ([ai])")
        lbl_sec2.setProperty("class", "section_title")
        l_ai.addWidget(lbl_sec2)

        self.chk_cfg_ai = QCheckBox("Habilitar Invocación de IA en ABRAXAS (bajo demanda)")
        self.chk_cfg_ai.setChecked(self.cfg.get("ai", {}).get("enabled", True))
        l_ai.addWidget(self.chk_cfg_ai)

        row_ai1 = QHBoxLayout()
        row_ai1.addWidget(QLabel("Proveedor / Motor:"))
        self.cmb_cfg_provider = QComboBox()
        self.cmb_cfg_provider.setItemDelegate(QStyledItemDelegate())
        self.cmb_cfg_provider.addItems(["ollama", "openai-compatible"])
        row_ai1.addWidget(self.cmb_cfg_provider, 1)
        l_ai.addLayout(row_ai1)

        # 1. Conversational Model (Obsidian Chatbox / Notas)
        row_ai_chat = QHBoxLayout()
        row_ai_chat.addWidget(QLabel("Modelo Conversacional (Chatbox & Obsidian):"))
        self.cmb_cfg_chat_model = QComboBox()
        self.cmb_cfg_chat_model.setItemDelegate(QStyledItemDelegate())
        chat_default = self.cfg.get("ai", {}).get("chat_model", "llama3.1:8b")
        self.cmb_cfg_chat_model.addItems([chat_default, "llama3.1:8b", "mistral:7b", "gemma2:9b", "qwen2.5:7b"])
        row_ai_chat.addWidget(self.cmb_cfg_chat_model, 1)
        l_ai.addLayout(row_ai_chat)

        # 2. Heavy Dev Model (Git & Razonamiento Complejo)
        row_ai_heavy = QHBoxLayout()
        row_ai_heavy.addWidget(QLabel("Modelo Pesado Dev (Refactor & Tareas Git Complejas):"))
        self.cmb_cfg_heavy_model = QComboBox()
        self.cmb_cfg_heavy_model.setItemDelegate(QStyledItemDelegate())
        heavy_default = self.cfg.get("ai", {}).get("heavy_model", "qwen2.5-coder:14b")
        self.cmb_cfg_heavy_model.addItems([heavy_default, "qwen2.5-coder:14b", "deepseek-coder:14b", "llama3.1:8b"])
        row_ai_heavy.addWidget(self.cmb_cfg_heavy_model, 1)
        l_ai.addLayout(row_ai_heavy)

        # 3. Light Dev Model (Git Flow Rápido & Mensajes de Commit)
        row_ai_light = QHBoxLayout()
        row_ai_light.addWidget(QLabel("Modelo Ligero Dev (Git Rápido & Mensajes de Commit):"))
        self.cmb_cfg_light_model = QComboBox()
        self.cmb_cfg_light_model.setItemDelegate(QStyledItemDelegate())
        light_default = self.cfg.get("ai", {}).get("light_model", "qwen2.5-coder:7b")
        self.cmb_cfg_light_model.addItems([light_default, "qwen2.5-coder:7b", "llama3.2:3b", "gemma2:2b"])
        row_ai_light.addWidget(self.cmb_cfg_light_model, 1)
        l_ai.addLayout(row_ai_light)

        row_ai3 = QHBoxLayout()
        row_ai3.addWidget(QLabel("Endpoint Servidor:"))
        self.txt_cfg_endpoint = QLineEdit(self.cfg.get("ai", {}).get("endpoint", "http://localhost:11434"))
        row_ai3.addWidget(self.txt_cfg_endpoint, 1)
        l_ai.addLayout(row_ai3)

        s_layout.addWidget(card_ai)

        # -------------------------------------------------------------
        # Section 3: Entorno de Desarrollo ([development])
        # -------------------------------------------------------------
        card_dev = QFrame()
        card_dev.setProperty("class", "surface")
        l_dev = QVBoxLayout(card_dev)
        l_dev.setSpacing(10)

        lbl_sec_dev = QLabel("⚙️ Entornos de Desarrollo ([development])")
        lbl_sec_dev.setProperty("class", "section_title")
        l_dev.addWidget(lbl_sec_dev)

        self.chk_cfg_venv = QCheckBox("Detección automática de entornos virtuales Python (.venv)")
        self.chk_cfg_venv.setChecked(self.cfg.get("development", {}).get("venv_auto_detect", True))
        l_dev.addWidget(self.chk_cfg_venv)

        self.chk_cfg_docker = QCheckBox("Monitoreo de contenedores Docker activos")
        self.chk_cfg_docker.setChecked(self.cfg.get("development", {}).get("docker_monitor", True))
        l_dev.addWidget(self.chk_cfg_docker)

        s_layout.addWidget(card_dev)

        # -------------------------------------------------------------
        # Section 4: Mantenimiento y Sistema Operativo ([system])
        # -------------------------------------------------------------
        card_sys = QFrame()
        card_sys.setProperty("class", "surface")
        l_sys = QVBoxLayout(card_sys)
        l_sys.setSpacing(10)

        lbl_sec_sys = QLabel("🛡️ Mantenimiento y Sistema Operativo ([system])")
        lbl_sec_sys.setProperty("class", "section_title")
        l_sys.addWidget(lbl_sec_sys)

        self.chk_cfg_btrfs = QCheckBox("Habilitar Instantáneas Atómicas Btrfs (Snapshots antes de cambios)")
        self.chk_cfg_btrfs.setChecked(self.cfg.get("system", {}).get("btrfs_snapshots", True))
        l_sys.addWidget(self.chk_cfg_btrfs)

        row_snapper = QHBoxLayout()
        row_snapper.addWidget(QLabel("Configuración / Perfil de Snapper:"))
        self.txt_cfg_snapper = QLineEdit(self.cfg.get("system", {}).get("snapper_config", "root"))
        row_snapper.addWidget(self.txt_cfg_snapper, 1)
        l_sys.addLayout(row_snapper)

        self.chk_cfg_safe_upd = QCheckBox("Actualizaciones seguras con verificación previa de integridad")
        self.chk_cfg_safe_upd.setChecked(self.cfg.get("system", {}).get("safe_updates", True))
        l_sys.addWidget(self.chk_cfg_safe_upd)

        self.chk_cfg_arch_news = QCheckBox("Comprobar noticias y alertas críticas de Arch Linux antes de actualizar")
        self.chk_cfg_arch_news.setChecked(self.cfg.get("system", {}).get("check_arch_news", True))
        l_sys.addWidget(self.chk_cfg_arch_news)

        s_layout.addWidget(card_sys)

        # -------------------------------------------------------------
        # Section 5: Apariencia & Interfaz ([abraxas])
        # -------------------------------------------------------------
        card_app = QFrame()
        card_app.setProperty("class", "surface")
        l_app = QVBoxLayout(card_app)
        l_app.setSpacing(10)

        lbl_sec3 = QLabel("🎨 Apariencia y Sistema ([abraxas])")
        lbl_sec3.setProperty("class", "section_title")
        l_app.addWidget(lbl_sec3)

        row_app1 = QHBoxLayout()
        row_app1.addWidget(QLabel("Tema Visual:"))
        self.cmb_cfg_theme = QComboBox()
        self.cmb_cfg_theme.setItemDelegate(QStyledItemDelegate())
        self.cmb_cfg_theme.addItems([
            "🔄 Sincronizar con Sistema (Auto / Noctalia)",
            "Noctalia Minimal", 
            "Dark Cyberpunk", 
            "Monocromo Puro"
        ])
        curr_th = self.cfg.get("abraxas", {}).get("theme", "system_sync")
        if curr_th == "system_sync" or "sync" in curr_th or "auto" in curr_th:
            self.cmb_cfg_theme.setCurrentIndex(0)
        elif "cyberpunk" in curr_th:
            self.cmb_cfg_theme.setCurrentIndex(2)
        elif "monochrome" in curr_th:
            self.cmb_cfg_theme.setCurrentIndex(3)
        else:
            self.cmb_cfg_theme.setCurrentIndex(1)
        row_app1.addWidget(self.cmb_cfg_theme, 1)
        l_app.addLayout(row_app1)

        row_app2 = QHBoxLayout()
        row_app2.addWidget(QLabel("Interfaz por defecto para CLI:"))
        self.cmb_cfg_iface = QComboBox()
        self.cmb_cfg_iface.setItemDelegate(QStyledItemDelegate())
        self.cmb_cfg_iface.addItems(["gui (Ventana flotante)", "tui (Consola interactiva)"])
        row_app2.addWidget(self.cmb_cfg_iface, 1)
        l_app.addLayout(row_app2)

        s_layout.addWidget(card_app)

        # Status Label
        self.lbl_cfg_status = QLabel("")
        self.lbl_cfg_status.setProperty("class", "status_ok")
        s_layout.addWidget(self.lbl_cfg_status)

        # Bottom Save Button Bar
        btn_save = QPushButton("💾 Guardar Cambios en config.toml")
        btn_save.setProperty("class", "primary")
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setFixedHeight(40)
        btn_save.clicked.connect(self.save_config_file)
        s_layout.addWidget(btn_save)

        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        return page

    def browse_folder(self, line_edit):
        curr = os.path.expanduser(line_edit.text())
        folder = QFileDialog.getExistingDirectory(
            self, "Seleccionar Carpeta", curr if os.path.exists(curr) else os.path.expanduser("~")
        )
        if folder:
            line_edit.setText(folder)

    def save_config_file(self):
        # 1. Paths
        if "paths" not in self.cfg: self.cfg["paths"] = {}
        self.cfg["paths"]["projects_dir"] = self.txt_cfg_proj.text().strip()
        self.cfg["paths"]["vault_dir"] = self.txt_cfg_vault.text().strip()
        self.cfg["paths"]["snapshots_dir"] = self.txt_cfg_snap.text().strip()

        # 2. AI
        if "ai" not in self.cfg: self.cfg["ai"] = {}
        self.cfg["ai"]["enabled"] = self.chk_cfg_ai.isChecked()
        self.cfg["ai"]["provider"] = self.cmb_cfg_provider.currentText().split()[0]
        self.cfg["ai"]["chat_model"] = self.cmb_cfg_chat_model.currentText()
        self.cfg["ai"]["heavy_model"] = self.cmb_cfg_heavy_model.currentText()
        self.cfg["ai"]["light_model"] = self.cmb_cfg_light_model.currentText()
        self.cfg["ai"]["endpoint"] = self.txt_cfg_endpoint.text().strip()

        # 3. Development
        if "development" not in self.cfg: self.cfg["development"] = {}
        self.cfg["development"]["venv_auto_detect"] = self.chk_cfg_venv.isChecked()
        self.cfg["development"]["docker_monitor"] = self.chk_cfg_docker.isChecked()

        # 4. System
        if "system" not in self.cfg: self.cfg["system"] = {}
        self.cfg["system"]["btrfs_snapshots"] = self.chk_cfg_btrfs.isChecked()
        self.cfg["system"]["snapper_config"] = self.txt_cfg_snapper.text().strip()
        self.cfg["system"]["safe_updates"] = self.chk_cfg_safe_upd.isChecked()
        self.cfg["system"]["check_arch_news"] = self.chk_cfg_arch_news.isChecked()

        # 5. Abraxas Theme & Interface
        if "abraxas" not in self.cfg: self.cfg["abraxas"] = {}
        theme_raw = self.cmb_cfg_theme.currentText().lower()
        if "sincronizar" in theme_raw or "auto" in theme_raw:
            theme_key = "system_sync"
        elif "cyberpunk" in theme_raw: 
            theme_key = "dark_cyberpunk"
        elif "monocromo" in theme_raw: 
            theme_key = "monochrome"
        else: 
            theme_key = "noctalia"
        
        self.cfg["abraxas"]["theme"] = theme_key
        self.setStyleSheet(generate_stylesheet(theme_key))

        iface_raw = self.cmb_cfg_iface.currentText().lower()
        self.cfg["abraxas"]["default_interface"] = "gui" if "gui" in iface_raw else "tui"

        write_toml_dict(self.config_target, self.cfg)
        self.lbl_cfg_status.setText(f"✔ Configuración actualizada con éxito en {self.config_target}")

    def create_placeholder_page(self, title, subtitle, desc):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        lbl_t = QLabel(title)
        lbl_t.setProperty("class", "page_title")
        
        lbl_sub = QLabel(subtitle)
        lbl_sub.setProperty("class", "page_subtitle")
        
        layout.addWidget(lbl_t)
        layout.addWidget(lbl_sub)

        card = QFrame()
        card.setProperty("class", "surface")
        c_lay = QVBoxLayout(card)
        
        lbl_desc = QLabel(desc)
        lbl_desc.setProperty("class", "card_desc")
        lbl_desc.setWordWrap(True)
        c_lay.addWidget(lbl_desc)

        layout.addWidget(card)
        layout.addStretch()
        return page

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = NeosMainApp()
    window.show()
    sys.exit(app.exec())

