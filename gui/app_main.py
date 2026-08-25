#!/home/silvynth/Proyectos/ABRAXAS/venv/bin/python
# =====================================================================
#  ❖ ABRAXAS | NEOS CONTROL CENTER (PySide6 Main GUI)
# =====================================================================

import sys
import os

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QStackedWidget, QFrame
)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from core.setup import read_toml_dict, get_target_config_path
from core import get_version
from gui.theme import generate_stylesheet
from gui.views.neos import ProjectsView, ConfigView, UpdatesView
from gui.views.umbra import UmbraView
from gui.views.lumen import LumenView

class NeosMainApp(QWidget):
    """Ventana principal modular del Centro de Control NEOS (ABRAXAS)."""
    
    def __init__(self):
        super().__init__()
        self.app_version = get_version()
        self.setWindowTitle(f"ABRAXAS | NEOS Control Center (v{self.app_version})")
        self.setMinimumSize(940, 640)

        # Icono de la ventana
        icon_path = os.path.join(ROOT_DIR, "assets", "abraxas_icon.svg")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.config_target = get_target_config_path()
        self.cfg = read_toml_dict(self.config_target)

        # Aplicar tema inicial activo
        initial_theme = self.cfg.get("abraxas", {}).get("theme", "system_sync")
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
        # 2. MAIN CONTENT STACK (MODULAR VIEWS: UMBRA, LUMEN, NEOS)
        # -------------------------------------------------------------
        content_area = QWidget()
        c_layout = QVBoxLayout(content_area)
        c_layout.setContentsMargins(28, 24, 28, 24)
        c_layout.setSpacing(16)

        self.stacked = QStackedWidget()

        # Page 0: UMBRA (views/umbra/)
        self.page_umbra = UmbraView()
        
        # Page 1: LUMEN (views/lumen/)
        self.page_lumen = LumenView()

        # Page 2: PROYECTOS (views/neos/projects_view.py)
        self.page_proyectos = ProjectsView(self.config_target)

        # Page 3: ACTUALIZACIÓN (views/neos/updates_view.py)
        self.page_actualizacion = UpdatesView()

        # Page 4: CONFIG (views/neos/config_view.py)
        self.page_config = ConfigView(self.config_target)
        self.page_config.theme_changed.connect(self.apply_theme)
        self.page_config.config_saved.connect(self.on_config_saved)

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
        if index == 2 and hasattr(self, "page_proyectos"):
            self.page_proyectos.load_projects()

    def apply_theme(self, theme_key):
        self.setStyleSheet(generate_stylesheet(theme_key))

    def on_config_saved(self, new_cfg):
        self.cfg = new_cfg
        if hasattr(self, "page_proyectos"):
            self.page_proyectos.load_projects()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("ABRAXAS")
    app.setApplicationDisplayName("ABRAXAS")
    app.setDesktopFileName("abraxas.desktop")
    
    icon_path = os.path.join(ROOT_DIR, "assets", "abraxas_icon.svg")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = NeosMainApp()
    window.show()
    sys.exit(app.exec())
