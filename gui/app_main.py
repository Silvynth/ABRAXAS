#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS | NEOS CONTROL CENTER (PySide6 Main GUI)
# =====================================================================

import sys
import os

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QStackedWidget, QFrame
)
from PySide6.QtCore import Qt

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from core import get_version

# =====================================================================
#  MINIMALIST DESIGN SYSTEM & COLOR TOKENS
# =====================================================================
BG_MAIN = "#0d0e12"
BG_SIDEBAR = "#12131a"
BG_SURFACE = "#15161c"
BG_SURFACE_HOVER = "#1c1d24"
BG_INPUT = "#0f1015"
BORDER_BASE = "#22242e"
BORDER_FOCUS = "#6366f1"

TEXT_PRIMARY = "#f3f4f6"
TEXT_SECONDARY = "#9ca3af"
TEXT_MUTED = "#6b7280"

ACCENT = "#6366f1"
ACCENT_HOVER = "#4f46e5"
ACCENT_LIGHT = "#e0e7ff"
CYAN = "#06b6d4"
SUCCESS = "#10b981"
WARNING = "#f59e0b"

STYLESHEET = f"""
QWidget {{
    background-color: {BG_MAIN};
    color: {TEXT_PRIMARY};
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    font-size: 13px;
}}

QLabel {{
    background-color: transparent;
}}

/* Sidebar Frame */
QFrame.sidebar {{
    background-color: {BG_SIDEBAR};
    border-right: 1px solid {BORDER_BASE};
}}

/* Nav Buttons */
QPushButton.nav_btn {{
    background-color: transparent;
    border: none;
    border-radius: 8px;
    color: {TEXT_SECONDARY};
    padding: 10px 14px;
    font-size: 13px;
    font-weight: 600;
    text-align: left;
}}

QPushButton.nav_btn:hover {{
    background-color: rgba(99, 102, 241, 0.12);
    color: {ACCENT_LIGHT};
}}

QPushButton.nav_btn:checked {{
    background-color: {ACCENT};
    color: #ffffff;
    font-weight: 700;
}}

/* Surface Card */
QFrame.surface {{
    background-color: {BG_SURFACE};
    border: 1px solid {BORDER_BASE};
    border-radius: 10px;
    padding: 16px;
}}

QLabel.page_title {{
    color: {TEXT_PRIMARY};
    font-size: 22px;
    font-weight: 700;
    letter-spacing: -0.5px;
}}

QLabel.page_subtitle {{
    color: {TEXT_SECONDARY};
    font-size: 13px;
}}

QLabel.version_badge {{
    background-color: #1e1f29;
    color: {CYAN};
    border: 1px solid rgba(6, 182, 212, 0.3);
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}}
"""

class NeosMainApp(QWidget):
    def __init__(self):
        super().__init__()
        self.app_version = get_version()
        self.setWindowTitle(f"ABRAXAS | NEOS Control Center (v{self.app_version})")
        self.setMinimumSize(940, 640)
        self.setStyleSheet(STYLESHEET)

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
        lbl_brand.setStyleSheet(f"font-size: 20px; font-weight: 800; color: {TEXT_PRIMARY}; letter-spacing: 1px;")
        
        lbl_subbrand = QLabel("ABRAXAS Control Center")
        lbl_subbrand.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED}; font-weight: 500;")
        
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
        self.page_config = self.create_placeholder_page(
            "🛠 CONFIG", 
            "Configuración General", 
            "Ajustes de rutas, temas de interfaz y módulos activos en config.toml."
        )

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
        lbl_desc.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 14px; line-height: 1.5;")
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

