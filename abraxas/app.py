#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS 2.0 | NEOS SHELL & ORCHESTRATOR (PySide6)
# =====================================================================

import sys
import os
from pathlib import Path

# Resolver la raíz del repositorio y aislar el paquete abraxas en sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent

# Limpiar subdirectorio de abraxas de sys.path para evitar colisiones entre abraxas/core y core/
sys.path = [p for p in sys.path if Path(p).resolve() != SCRIPT_DIR.resolve()]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QStackedWidget, QFrame, QScrollArea, QGridLayout
)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt

from abraxas import get_version
from abraxas.core.paths import get_assets_dir, get_active_config_path
from abraxas.core.config import load_config
from abraxas.core.theme import generate_monochrome_stylesheet
from gui.views.neos import ProjectsView
from gui.views.umbra.main_view import UmbraView
from abraxas.lumen.ui.lumen_view import LumenView

class NeosShellWindow(QWidget):
    """Ventana principal del Shell Neos 2.0: Orquestador modular de dominios."""
    
    def __init__(self):
        super().__init__()
        self.setObjectName("NeosShellWindow")
        self.cfg = load_config()
        self.app_version = get_version()
        
        self.setWindowTitle(f"ABRAXAS 2.0 | Neos Shell (v{self.app_version}) [Monochrome Mode]")
        self.setMinimumSize(1000, 680)

        # Icono de la ventana
        icon_path = get_assets_dir() / "abraxas_icon.svg"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        # Aplicar diseño puramente monocromático (Haute Horlogerie / Cero distracciones)
        self.setStyleSheet(generate_monochrome_stylesheet())

        self.init_ui()
        self.center_window()

    def closeEvent(self, event):
        """Limpieza y detención ordenada de hilos en segundo plano."""
        if hasattr(self, "page_umbra"):
            self.page_umbra.close()
        if hasattr(self, "page_lumen"):
            self.page_lumen.close()
        if hasattr(self, "page_proyectos") and hasattr(self.page_proyectos, "sync_page"):
            sp = self.page_proyectos.sync_page
            if hasattr(sp, "detect_worker") and sp.detect_worker and sp.detect_worker.isRunning():
                sp.detect_worker.quit()
                sp.detect_worker.wait(500)
        super().closeEvent(event)

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
        # 1. SIDEBAR NAVEGADOR
        # -------------------------------------------------------------
        sidebar = QFrame()
        sidebar.setProperty("class", "sidebar")
        sidebar.setFixedWidth(230)
        
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(16, 20, 16, 20)
        sb_layout.setSpacing(8)

        # Brand header
        lbl_brand = QLabel("❖ NEOS 2.0")
        lbl_brand.setProperty("class", "brand_title")
        
        lbl_subbrand = QLabel("ABRAXAS Modular Platform")
        lbl_subbrand.setProperty("class", "brand_subtitle")
        
        sb_layout.addWidget(lbl_brand)
        sb_layout.addWidget(lbl_subbrand)
        sb_layout.addSpacing(16)

        # Menu Nav Buttons
        self.nav_buttons = []
        menu_items = [
            ("⚙  UMBRA", "Dominio Sistema, Kernel & Telemetría"),
            ("💻  LUMEN", "Dominio Dev, GitOps & IA Local"),
            ("📁  PROYECTOS", "Explorador de Repositorios & Grafo de Estructura"),
            ("🛠  REGLAS CONFIG", "Inspección de Configuración Tipada")
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

        # Badge de arquitectura
        lbl_badge = QLabel(f"v{self.app_version} (Modular)")
        lbl_badge.setProperty("class", "version_badge")
        sb_layout.addWidget(lbl_badge)

        root_layout.addWidget(sidebar)

        # -------------------------------------------------------------
        # 2. CONTENEDOR CENTRAL DE PÁGINAS (STACKED WIDGET)
        # -------------------------------------------------------------
        content_area = QWidget()
        content_area.setObjectName("content_area")
        c_layout = QVBoxLayout(content_area)
        c_layout.setContentsMargins(28, 24, 28, 24)
        c_layout.setSpacing(16)

        self.stacked = QStackedWidget()

        # Construir páginas del sistema
        self.page_umbra = UmbraView()
        self.page_lumen = LumenView(self.cfg)
        self.page_proyectos = ProjectsView(str(get_active_config_path()))
        self.page_proyectos.set_theme("monochrome")
        self.page_config = self._build_config_preview()

        self.stacked.addWidget(self.page_umbra)
        self.stacked.addWidget(self.page_lumen)
        self.stacked.addWidget(self.page_proyectos)
        self.stacked.addWidget(self.page_config)

        c_layout.addWidget(self.stacked)
        root_layout.addWidget(content_area)

        # Seleccionar primera pestaña por defecto
        self.switch_tab(0)

    def switch_tab(self, index: int):
        self.stacked.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)
        if index == 1 and hasattr(self, "page_lumen"):
            self.page_lumen.reload()
        elif index == 2 and hasattr(self, "page_proyectos"):
            self.page_proyectos.load_projects()

    def _build_umbra_preview(self) -> QWidget:
        """Página preliminar del dominio UMBRA."""
        panel = QFrame()
        panel.setProperty("class", "sector_card")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        tag = QLabel("DOMINIO 01 // OPERADOR DE SISTEMA & KERNEL")
        tag.setProperty("class", "sector_micro_tag")
        title = QLabel("❖ Núcleo UMBRA: Telemetría & Monitor de Host")
        title.setProperty("class", "sector_title")
        desc = QLabel(
            "Este dominio gestiona la telemetría agnóstica de hardware, sensores térmicos, "
            "monitoreo de daemons en segundo plano y la terminal deslizante del sistema."
        )
        desc.setWordWrap(True)
        desc.setProperty("class", "sector_desc")

        # Grid de estado rápido
        grid = QGridLayout()
        grid.setSpacing(12)

        items = [
            ("Arquitectura SO", "Linux x86_64"),
            ("Snapshots Btrfs", "Habilitado" if self.cfg.system.btrfs_snapshots else "Deshabilitado"),
            ("Config Snapper", self.cfg.system.snapper_config),
            ("Estado Motor", "Listo (Modular v2)")
        ]

        for i, (k, v) in enumerate(items):
            box = QFrame()
            box.setStyleSheet("background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 12px;")
            b_lay = QVBoxLayout(box)
            b_lay.setContentsMargins(8, 8, 8, 8)
            lbl_k = QLabel(k)
            lbl_k.setProperty("class", "sector_micro_tag")
            lbl_v = QLabel(v)
            lbl_v.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: bold; font-family: 'JetBrains Mono', monospace;")
            b_lay.addWidget(lbl_k)
            b_lay.addWidget(lbl_v)
            grid.addWidget(box, i // 2, i % 2)

        layout.addWidget(tag)
        layout.addWidget(title)
        layout.addWidget(desc)
        layout.addSpacing(10)
        layout.addLayout(grid)
        layout.addStretch()
        return panel


    def _build_config_preview(self) -> QWidget:
        """Página preliminar de inspección de reglas de configuración."""
        panel = QFrame()
        panel.setProperty("class", "sector_card")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        tag = QLabel("FOUNDATION // MOTOR DE CONFIGURACIÓN TIPADO")
        tag.setProperty("class", "sector_micro_tag")
        title = QLabel("❖ Reglas Activas de Configuración (Single Source of Truth)")
        title.setProperty("class", "sector_title")
        
        cfg_path_str = str(self.cfg.config_path or "No definido")
        desc = QLabel(f"Archivo activo: {cfg_path_str}")
        desc.setProperty("class", "sector_desc")
        desc.setStyleSheet("color: #9ca3af; font-size: 12px; font-family: monospace;")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")

        inner = QWidget()
        in_layout = QVBoxLayout(inner)
        in_layout.setSpacing(8)

        rules = [
            ("Tema Activo", self.cfg.abraxas.theme),
            ("Ruta Vault Obsidian", str(self.cfg.paths.vault_dir)),
            ("Vault Existe", "Sí" if self.cfg.paths.vault_dir_exists else "No"),
            ("Endpoint IA", self.cfg.ai.endpoint),
            ("Temperatura IA", str(self.cfg.ai.temperature)),
            ("Modelo Heavy", self.cfg.ai.heavy_model or "No asignado"),
            ("Modelo Light", self.cfg.ai.light_model or "No asignado"),
            ("Guardado Atómico", "Habilitado (Anti-Corrupción .tmp -> replace)")
        ]

        for k, v in rules:
            row = QHBoxLayout()
            lbl_k = QLabel(k)
            lbl_k.setStyleSheet("color: #9ca3af; font-size: 13px; font-weight: bold;")
            lbl_v = QLabel(str(v))
            lbl_v.setStyleSheet("color: #f3f4f6; font-size: 13px; font-family: monospace;")
            row.addWidget(lbl_k)
            row.addStretch()
            row.addWidget(lbl_v)
            in_layout.addLayout(row)

        scroll.setWidget(inner)

        layout.addWidget(tag)
        layout.addWidget(title)
        layout.addWidget(desc)
        layout.addSpacing(10)
        layout.addWidget(scroll)
        return panel

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ABRAXAS 2.0")
    app.setApplicationDisplayName("ABRAXAS 2.0 (Preview)")
    
    icon_path = get_assets_dir() / "abraxas_icon.svg"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = NeosShellWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
