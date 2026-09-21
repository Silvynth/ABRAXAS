#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS | MINIMALIST GRAPHICAL INSTALLER & WIZARD (PySide6)
# =====================================================================

import sys
import os
import subprocess
import shutil
import urllib.request
import json

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QLineEdit, QFileDialog, QStackedWidget, 
    QRadioButton, QCheckBox, QFrame, QProgressBar,
    QComboBox, QStyledItemDelegate, QTextEdit, QScrollArea
)
from PySide6.QtCore import Qt, QTimer

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from core.setup import (
    write_toml_dict, read_toml_dict, TEMPLATE_PATH, get_target_config_path,
    detect_git_identity, sync_global_gitconfig
)
from core.environments import detect_installed_editors, get_preferred_editor, set_preferred_editor
from core import get_version, __app_name__

# =====================================================================
#  MINIMALIST DESIGN SYSTEM & COLOR TOKENS
# =====================================================================
BG_MAIN = "#0d0e12"
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

SUCCESS = "#10b981"
WARNING = "#f59e0b"
CYAN = "#06b6d4"

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

/* Surface Cards */
QFrame.surface {{
    background-color: {BG_SURFACE};
    border: 1px solid {BORDER_BASE};
    border-radius: 10px;
    padding: 16px;
}}

QFrame.surface QLabel {{
    background-color: transparent;
}}

QFrame.stat_card {{
    background-color: {BG_SURFACE};
    border: 1px solid {BORDER_BASE};
    border-radius: 8px;
    padding: 12px;
}}

QFrame.stat_card QLabel {{
    background-color: transparent;
}}

QFrame.stat_card:hover {{
    border-color: #323542;
    background-color: {BG_SURFACE_HOVER};
}}

/* Typography */
QLabel.app_brand {{
    color: {TEXT_PRIMARY};
    font-size: 16px;
    font-weight: 800;
    letter-spacing: 1.5px;
}}

QLabel.page_title {{
    color: {TEXT_PRIMARY};
    font-size: 20px;
    font-weight: 700;
    letter-spacing: -0.3px;
}}

QLabel.page_subtitle {{
    color: {TEXT_SECONDARY};
    font-size: 13px;
    line-height: 1.4;
}}

QLabel.section_title {{
    color: {TEXT_PRIMARY};
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.2px;
}}

QLabel.label_muted {{
    color: {TEXT_MUTED};
    font-size: 12px;
}}

/* Badges & Pills */
QLabel.version_tag {{
    background-color: #1e1f29;
    color: {TEXT_SECONDARY};
    border: 1px solid {BORDER_BASE};
    border-radius: 4px;
    padding: 2px 6px;
    font-size: 10px;
    font-weight: 600;
}}

QLabel.preview_tag {{
    background-color: rgba(245, 158, 11, 0.12);
    color: {WARNING};
    border: 1px solid rgba(245, 158, 11, 0.3);
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.5px;
}}

QLabel.feature_chip {{
    background-color: #171821;
    color: {TEXT_SECONDARY};
    border: 1px solid {BORDER_BASE};
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 12px;
}}

/* Input Fields */
QLineEdit {{
    background-color: {BG_INPUT};
    border: 1px solid {BORDER_BASE};
    border-radius: 7px;
    padding: 8px 12px;
    color: {TEXT_PRIMARY};
    font-size: 13px;
    selection-background-color: {ACCENT};
}}

QLineEdit:focus {{
    border: 1px solid {BORDER_FOCUS};
    background-color: #12131a;
}}

/* Buttons */
QPushButton {{
    background-color: #1e1f29;
    border: 1px solid {BORDER_BASE};
    border-radius: 7px;
    color: {TEXT_PRIMARY};
    padding: 8px 16px;
    font-weight: 600;
    font-size: 13px;
}}

QPushButton:hover {{
    background-color: {BG_SURFACE_HOVER};
    border-color: #3b3e4f;
    color: #ffffff;
}}

QPushButton:pressed {{
    background-color: #161720;
}}

QPushButton.primary {{
    background-color: {ACCENT};
    color: #ffffff;
    border: none;
    border-radius: 7px;
    padding: 9px 20px;
    font-weight: 600;
    font-size: 13px;
}}

QPushButton.primary:hover {{
    background-color: {ACCENT_HOVER};
}}

QPushButton.browse {{
    background-color: #1a1b24;
    border: 1px solid {BORDER_BASE};
    border-radius: 7px;
    padding: 8px 14px;
    font-size: 12px;
    font-weight: 500;
}}

QPushButton.browse:hover {{
    border-color: {BORDER_FOCUS};
    color: {ACCENT_LIGHT};
}}

/* CheckBoxes & RadioButtons */
QCheckBox, QRadioButton {{
    color: {TEXT_PRIMARY};
    spacing: 10px;
    font-size: 13px;
    font-weight: 500;
    background-color: transparent;
}}

QCheckBox::indicator, QRadioButton::indicator {{
    width: 18px;
    height: 18px;
    border: 1px solid {BORDER_BASE};
    border-radius: 5px;
    background-color: {BG_INPUT};
}}

QRadioButton::indicator {{
    border-radius: 9px;
}}

QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
    border-color: {BORDER_FOCUS};
}}

QCheckBox::indicator:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
    image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='3.5' stroke-linecap='round' stroke-linejoin='round'><polyline points='20 6 9 17 4 12'></polyline></svg>");
}}

QRadioButton::indicator:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
    image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='8' height='8' viewBox='0 0 24 24' fill='white'><circle cx='12' cy='12' r='8'/></svg>");
}}

QCheckBox QLabel, QRadioButton QLabel {{
    background-color: transparent;
}}

QFrame QWidget {{
    background-color: transparent;
}}

/* Combo Dropdown */
QComboBox {{
    background-color: #12131a;
    border: 1px solid {BORDER_BASE};
    border-radius: 8px;
    padding: 8px 14px;
    color: {TEXT_PRIMARY};
    font-size: 13px;
    font-weight: 500;
}}

QComboBox:hover {{
    border-color: {CYAN};
    background-color: #161722;
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 30px;
    border: none;
}}

QComboBox::down-arrow {{
    image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2306b6d4' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'><polyline points='6 9 12 15 18 9'></polyline></svg>");
    width: 12px;
    height: 12px;
}}

QComboBox QAbstractItemView {{
    background-color: #141620;
    border: 1px solid rgba(6, 182, 212, 0.4);
    border-radius: 8px;
    color: {TEXT_PRIMARY};
    selection-background-color: rgba(6, 182, 212, 0.25);
    selection-color: #ffffff;
    outline: 0px;
    padding: 4px;
}}

QComboBox QAbstractItemView::item {{
    min-height: 28px;
    padding: 6px 10px;
    color: {TEXT_PRIMARY};
    border-radius: 4px;
    background-color: transparent;
}}

QComboBox QAbstractItemView::item:hover {{
    background-color: rgba(6, 182, 212, 0.20);
    color: {CYAN};
}}

QComboBox QAbstractItemView::item:selected {{
    background-color: rgba(6, 182, 212, 0.30);
    color: #ffffff;
}}

/* Progress Bar */
QProgressBar {{
    background-color: {BG_INPUT};
    border: 1px solid {BORDER_BASE};
    border-radius: 4px;
    text-align: center;
    color: transparent;
    height: 6px;
}}

QProgressBar::chunk {{
    background-color: {ACCENT};
    border-radius: 3px;
}}
"""

def probe_system_hardware():
    """Telemetría ligera del hardware en vivo (CPU, RAM, GPU)"""
    ram_gb = 8.0
    try:
        with open('/proc/meminfo') as f:
            for line in f:
                if 'MemTotal' in line:
                    ram_gb = round(int(line.split()[1]) / (1024 * 1024), 1)
                    break
    except Exception:
        pass

    cpu_name = "Procesador Multi-Core"
    cores = os.cpu_count() or 4
    try:
        with open('/proc/cpuinfo') as f:
            for line in f:
                if 'model name' in line:
                    cpu_name = line.split(':', 1)[1].strip()
                    cpu_name = cpu_name.replace('(R)', '').replace('(TM)', '').replace('Processor', '').strip()
                    break
    except Exception:
        pass

    gpu_name = "Gráficos Integrados"
    has_cuda = False
    if shutil.which('nvidia-smi'):
        try:
            out = subprocess.check_output(['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader'], text=True).strip()
            if out:
                gpu_name = out
                has_cuda = True
        except Exception:
            pass
    elif shutil.which('lspci'):
        try:
            out = subprocess.check_output(['lspci'], text=True)
            for l in out.splitlines():
                if 'VGA' in l or '3D' in l:
                    gpu_name = l.split(':', 2)[-1].strip()
                    break
        except Exception:
            pass

    return {
        "cpu": cpu_name,
        "cores": cores,
        "ram": f"{ram_gb} GB",
        "gpu": gpu_name,
        "cuda": has_cuda,
        "ram_gb": ram_gb
    }

class AbraxasInstallerGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.is_preview = any(arg in sys.argv for arg in ["--preview", "--dry-run", "-p", "--simulated"])
        
        self.app_version = get_version()
        if self.is_preview:
            self.setWindowTitle(f"ABRAXAS v{self.app_version} — Asistente de Instalación [Vista Previa]")
        else:
            self.setWindowTitle(f"ABRAXAS v{self.app_version} — Asistente de Instalación")
            
        self.setMinimumSize(820, 680)
        self.resize(840, 710)
        self.setStyleSheet(STYLESHEET)
        
        # Hardware Probe & Config
        self.hw_info = probe_system_hardware()
        self.config_target = get_target_config_path()
        self.cfg = read_toml_dict(self.config_target) or read_toml_dict(TEMPLATE_PATH)
        
        try:
            self.init_ui()
            self.center_window()
        except Exception as e:
            import traceback
            traceback.print_exc()

    def center_window(self):
        screen = self.screen()
        if screen:
            qr = self.frameGeometry()
            cp = screen.availableGeometry().center()
            qr.moveCenter(cp)
            self.move(qr.topLeft())

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 26, 32, 26)
        main_layout.setSpacing(16)

        # -------------------------------------------------------------
        # 1. TOP HEADER & MINIMALIST STEPPER
        # -------------------------------------------------------------
        header_row = QHBoxLayout()
        header_row.setSpacing(10)

        # Brand mark
        lbl_brand = QLabel("ABRAXAS")
        lbl_brand.setProperty("class", "app_brand")
        
        lbl_ver = QLabel(f"v{self.app_version}")
        lbl_ver.setProperty("class", "version_tag")
        
        header_row.addWidget(lbl_brand)
        header_row.addWidget(lbl_ver)

        if self.is_preview:
            lbl_preview = QLabel("MODO SIMULACIÓN")
            lbl_preview.setProperty("class", "preview_tag")
            header_row.addWidget(lbl_preview)

        header_row.addStretch()

        # Step indicator tabs
        self.step_labels = []
        steps_text = ["01 Inicio", "02 Almacenamiento", "03 Motor & IA", "04 Resumen"]
        
        for i, st in enumerate(steps_text):
            lbl_s = QLabel(st)
            lbl_s.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; font-weight: 600; padding: 4px 8px;")
            self.step_labels.append(lbl_s)
            header_row.addWidget(lbl_s)
            if i < len(steps_text) - 1:
                sep = QLabel("›")
                sep.setStyleSheet(f"color: #2b2e3b; font-size: 12px;")
                header_row.addWidget(sep)

        main_layout.addLayout(header_row)

        # Subtle divider
        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setStyleSheet(f"background-color: {BORDER_BASE}; max-height: 1px; border: none;")
        main_layout.addWidget(div)

        # -------------------------------------------------------------
        # 2. STACKED CONTENT AREA
        # -------------------------------------------------------------
        self.stacked = QStackedWidget()
        self.page_welcome = self.create_welcome_page()
        self.page_paths = self.create_paths_page()
        self.page_hardware_ai = self.create_hardware_ai_page()
        self.page_finish = self.create_finish_page()

        self.stacked.addWidget(self.page_welcome)
        self.stacked.addWidget(self.page_paths)
        self.stacked.addWidget(self.page_hardware_ai)
        self.stacked.addWidget(self.page_finish)
        main_layout.addWidget(self.stacked)

        # -------------------------------------------------------------
        # 3. BOTTOM NAVIGATION BAR
        # -------------------------------------------------------------
        self.nav_layout = QHBoxLayout()
        self.nav_layout.setContentsMargins(0, 8, 0, 0)
        
        self.btn_back = QPushButton("Atrás")
        self.btn_back.setCursor(Qt.PointingHandCursor)
        self.btn_back.clicked.connect(self.prev_page)
        self.btn_back.hide()
        
        self.btn_next = QPushButton("Continuar ➔")
        self.btn_next.setProperty("class", "primary")
        self.btn_next.setCursor(Qt.PointingHandCursor)
        self.btn_next.clicked.connect(self.next_page)

        self.nav_layout.addWidget(self.btn_back)
        self.nav_layout.addStretch()
        self.nav_layout.addWidget(self.btn_next)
        main_layout.addLayout(self.nav_layout)

        self.update_stepper(0)

    def update_stepper(self, current_idx):
        for i, lbl in enumerate(self.step_labels):
            if i == current_idx:
                lbl.setStyleSheet(f"color: {ACCENT_LIGHT}; font-size: 11px; font-weight: 700; background-color: #1a1c26; border-radius: 4px; padding: 4px 8px;")
            elif i < current_idx:
                lbl.setStyleSheet(f"color: {SUCCESS}; font-size: 11px; font-weight: 600; padding: 4px 8px;")
            else:
                lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; font-weight: 500; padding: 4px 8px;")

    # =================================================================
    #  PAGE 1: WELCOME & HARDWARE TELEMETRY
    # =================================================================
    def create_welcome_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(14)

        # Header Title
        lbl_title = QLabel("Bienvenido a ABRAXAS")
        lbl_title.setProperty("class", "page_title")
        lbl_sub = QLabel(
            "Entorno operativo dualista para Linux que integra terminal moderna, interfaz gráfica minimalista "
            "y asistencia inteligente local."
        )
        lbl_sub.setProperty("class", "page_subtitle")
        lbl_sub.setWordWrap(True)
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_sub)

        # Hardware Stat Cards (3 Columns)
        hw_grid = QHBoxLayout()
        hw_grid.setSpacing(10)

        # CPU Card
        c_cpu = QFrame()
        c_cpu.setProperty("class", "stat_card")
        l_cpu = QVBoxLayout(c_cpu)
        l_cpu.setContentsMargins(12, 10, 12, 10)
        l_cpu.setSpacing(4)
        lbl_cpu_t = QLabel("PROCESADOR")
        lbl_cpu_t.setProperty("class", "label_muted")
        lbl_cpu_v = QLabel(self.hw_info["cpu"])
        lbl_cpu_v.setStyleSheet(f"font-weight: 600; font-size: 13px; color: {TEXT_PRIMARY};")
        lbl_cpu_v.setWordWrap(True)
        lbl_cpu_sub = QLabel(f"{self.hw_info['cores']} núcleos lógicos detectados")
        lbl_cpu_sub.setProperty("class", "label_muted")
        l_cpu.addWidget(lbl_cpu_t)
        l_cpu.addWidget(lbl_cpu_v)
        l_cpu.addWidget(lbl_cpu_sub)
        hw_grid.addWidget(c_cpu)

        # RAM Card
        c_ram = QFrame()
        c_ram.setProperty("class", "stat_card")
        l_ram = QVBoxLayout(c_ram)
        l_ram.setContentsMargins(12, 10, 12, 10)
        l_ram.setSpacing(4)
        lbl_ram_t = QLabel("MEMORIA DEL SISTEMA")
        lbl_ram_t.setProperty("class", "label_muted")
        lbl_ram_v = QLabel(self.hw_info["ram"])
        lbl_ram_v.setStyleSheet(f"font-weight: 600; font-size: 13px; color: {TEXT_PRIMARY};")
        lbl_ram_sub = QLabel("Asignación dinámica de búfer")
        lbl_ram_sub.setProperty("class", "label_muted")
        l_ram.addWidget(lbl_ram_t)
        l_ram.addWidget(lbl_ram_v)
        l_ram.addWidget(lbl_ram_sub)
        hw_grid.addWidget(c_ram)

        # GPU Card
        c_gpu = QFrame()
        c_gpu.setProperty("class", "stat_card")
        l_gpu = QVBoxLayout(c_gpu)
        l_gpu.setContentsMargins(12, 10, 12, 10)
        l_gpu.setSpacing(4)
        lbl_gpu_t = QLabel("ACELERACIÓN GRÁFICA")
        lbl_gpu_t.setProperty("class", "label_muted")
        lbl_gpu_v = QLabel(self.hw_info["gpu"])
        lbl_gpu_v.setStyleSheet(f"font-weight: 600; font-size: 13px; color: {TEXT_PRIMARY};")
        lbl_gpu_v.setWordWrap(True)
        tag_cuda = "Aceleración CUDA Activa" if self.hw_info["cuda"] else "Renderizado Directo"
        lbl_gpu_sub = QLabel(tag_cuda)
        lbl_gpu_sub.setStyleSheet(f"color: {SUCCESS if self.hw_info['cuda'] else TEXT_MUTED}; font-size: 11px;")
        l_gpu.addWidget(lbl_gpu_t)
        l_gpu.addWidget(lbl_gpu_v)
        l_gpu.addWidget(lbl_gpu_sub)
        hw_grid.addWidget(c_gpu)

        layout.addLayout(hw_grid)

        # Feature Highlights
        feat_card = QFrame()
        feat_card.setProperty("class", "surface")
        l_feat = QVBoxLayout(feat_card)
        l_feat.setSpacing(10)
        
        lbl_feat_h = QLabel("Principios Fundamentales:")
        lbl_feat_h.setProperty("class", "section_title")
        l_feat.addWidget(lbl_feat_h)

        f_row = QHBoxLayout()
        f_row.setSpacing(8)
        
        f1 = QLabel("⚡ <b>Rendimiento Puro:</b> Cero dependencias pesadas innecesarias.")
        f1.setProperty("class", "feature_chip")
        f1.setWordWrap(True)
        
        f2 = QLabel("🔒 <b>Privacidad Absoluta:</b> 100% de tus datos permanecen locales.")
        f2.setProperty("class", "feature_chip")
        f2.setWordWrap(True)
        
        f3 = QLabel("🧩 <b>Modular:</b> Activa solo los componentes que utilizas.")
        f3.setProperty("class", "feature_chip")
        f3.setWordWrap(True)

        f_row.addWidget(f1)
        f_row.addWidget(f2)
        f_row.addWidget(f3)
        l_feat.addLayout(f_row)

        layout.addWidget(feat_card)
        layout.addStretch()
        return page

    # =================================================================
    #  PAGE 2: STORAGE & MODULES
    # =================================================================
    def create_paths_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(14)

        lbl_title = QLabel("Almacenamiento y Módulos")
        lbl_title.setProperty("class", "page_title")
        lbl_sub = QLabel("Configura las ubicaciones base donde ABRAXAS organizará tus repositorios y respaldos.")
        lbl_sub.setProperty("class", "page_subtitle")
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_sub)

        # Main Storage Card
        card = QFrame()
        card.setProperty("class", "surface")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(16, 14, 16, 16)
        c_layout.setSpacing(10)

        # 1. Projects Directory (LUMEN)
        c_layout.addWidget(QLabel("Directorio raíz para proyectos y repositorios Git:"))
        h1 = QHBoxLayout()
        h1.setSpacing(8)
        self.txt_projects = QLineEdit(self.cfg.get("paths", {}).get("projects_dir", "~/Proyectos"))
        btn_browse_proj = QPushButton("Examinar")
        btn_browse_proj.setProperty("class", "browse")
        btn_browse_proj.clicked.connect(lambda: self.browse_folder(self.txt_projects))
        h1.addWidget(self.txt_projects)
        h1.addWidget(btn_browse_proj)
        c_layout.addLayout(h1)

        # Divider
        div1 = QFrame()
        div1.setFrameShape(QFrame.HLine)
        div1.setStyleSheet(f"background-color: {BORDER_BASE}; max-height: 1px; border: none;")
        c_layout.addWidget(div1)

        # 2. Obsidian Vault (NOUS)
        self.chk_vault_enable = QCheckBox("Integrar Bóveda de Notas / Obsidian (NOUS)")
        self.chk_vault_enable.setChecked(True)
        self.chk_vault_enable.toggled.connect(self.toggle_vault_section)
        c_layout.addWidget(self.chk_vault_enable)

        self.vault_container = QWidget()
        v_box = QHBoxLayout(self.vault_container)
        v_box.setContentsMargins(0, 2, 0, 4)
        v_box.setSpacing(8)
        self.txt_vault = QLineEdit(self.cfg.get("paths", {}).get("vault_dir", "~/Vault"))
        btn_browse_vault = QPushButton("Examinar")
        btn_browse_vault.setProperty("class", "browse")
        btn_browse_vault.clicked.connect(lambda: self.browse_folder(self.txt_vault))
        v_box.addWidget(self.txt_vault)
        v_box.addWidget(btn_browse_vault)
        c_layout.addWidget(self.vault_container)

        # Divider
        div2 = QFrame()
        div2.setFrameShape(QFrame.HLine)
        div2.setStyleSheet(f"background-color: {BORDER_BASE}; max-height: 1px; border: none;")
        c_layout.addWidget(div2)

        # 3. Btrfs Snapshots (UMBRA)
        self.chk_btrfs_enable = QCheckBox("Activar Instantáneas Atómicas Btrfs (UMBRA)")
        self.chk_btrfs_enable.setChecked(False)
        self.chk_btrfs_enable.toggled.connect(self.toggle_btrfs_section)
        c_layout.addWidget(self.chk_btrfs_enable)

        self.btrfs_container = QWidget()
        self.btrfs_container.setVisible(False)
        b_box = QVBoxLayout(self.btrfs_container)
        b_box.setContentsMargins(0, 2, 0, 4)
        b_box.setSpacing(4)
        
        lbl_snap = QLabel("Subvolumen de instantáneas raíz (ej. Snapper):")
        lbl_snap.setProperty("class", "label_muted")
        self.txt_snap = QLineEdit(self.cfg.get("paths", {}).get("snapshots_dir", "/.snapshots"))
        b_box.addWidget(lbl_snap)
        b_box.addWidget(self.txt_snap)
        c_layout.addWidget(self.btrfs_container)

        # Divider
        div3 = QFrame()
        div3.setFrameShape(QFrame.HLine)
        div3.setStyleSheet(f"background-color: {BORDER_BASE}; max-height: 1px; border: none;")
        c_layout.addWidget(div3)

        # 4. Git Identity
        lbl_git_sec = QLabel("Identidad Git & GitHub ([git]):")
        lbl_git_sec.setProperty("class", "section_title")
        c_layout.addWidget(lbl_git_sec)

        lbl_git_sub = QLabel("Firma de autoría para commits y releases en LUMEN (evita bloqueos en Git).")
        lbl_git_sub.setProperty("class", "label_muted")
        c_layout.addWidget(lbl_git_sub)

        def_git_user = self.cfg.get("git", {}).get("user_name", "")
        def_git_email = self.cfg.get("git", {}).get("user_email", "")
        if not def_git_user or not def_git_email:
            det_u, det_e = detect_git_identity()
            if not def_git_user: def_git_user = det_u
            if not def_git_email: def_git_email = det_e

        row_git = QHBoxLayout()
        row_git.setSpacing(8)

        v_gu = QVBoxLayout()
        v_gu.setSpacing(2)
        v_gu.addWidget(QLabel("Usuario Git (user.name):"))
        self.txt_git_user = QLineEdit(def_git_user)
        self.txt_git_user.setPlaceholderText("ej. Tu Nombre o Usuario")
        v_gu.addWidget(self.txt_git_user)
        row_git.addLayout(v_gu, 1)

        v_ge = QVBoxLayout()
        v_ge.setSpacing(2)
        v_ge.addWidget(QLabel("Correo Git (user.email):"))
        self.txt_git_email = QLineEdit(def_git_email)
        self.txt_git_email.setPlaceholderText("ej. correo@ejemplo.com")
        v_ge.addWidget(self.txt_git_email)
        row_git.addLayout(v_ge, 1)

        c_layout.addLayout(row_git)

        self.chk_git_sync = QCheckBox("Sincronizar automáticamente con ~/.gitconfig global")
        self.chk_git_sync.setChecked(self.cfg.get("git", {}).get("auto_sync_global", True))
        c_layout.addWidget(self.chk_git_sync)

        # 3. Editor de Código Preferido (LUMEN Sector 2)
        sep_ed = QFrame()
        sep_ed.setFrameShape(QFrame.HLine)
        sep_ed.setStyleSheet("color: rgba(255, 255, 255, 0.10); margin-top: 6px; margin-bottom: 6px;")
        c_layout.addWidget(sep_ed)

        lbl_ed = QLabel("<b>💻 Editor de Código Preferido (LUMEN Sector 2):</b>")
        c_layout.addWidget(lbl_ed)

        lbl_ed_sub = QLabel("Se utilizará por defecto para abrir proyectos y archivos desde el HUD.")
        lbl_ed_sub.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        c_layout.addWidget(lbl_ed_sub)

        self.cmb_editor = QComboBox()
        self.cmb_editor.setItemDelegate(QStyledItemDelegate(self.cmb_editor))
        self.cmb_editor.setStyleSheet(f"""
            QComboBox {{
                background-color: {BG_INPUT};
                border: 1px solid {BORDER_BASE};
                border-radius: 6px;
                padding: 6px 12px;
                color: {TEXT_PRIMARY};
                font-weight: 600;
            }}
            QComboBox:focus {{
                border-color: {BORDER_FOCUS};
            }}
            QComboBox QAbstractItemView {{
                background-color: {BG_SURFACE};
                border: 1px solid {BORDER_BASE};
                selection-background-color: {ACCENT};
                selection-color: #ffffff;
                padding: 4px;
            }}
        """)
        installed_eds = detect_installed_editors()
        current_pref = get_preferred_editor()
        
        if installed_eds:
            for ed in installed_eds:
                self.cmb_editor.addItem(f"{ed['icon']} {ed['name']}", ed['id'])
            for idx in range(self.cmb_editor.count()):
                if self.cmb_editor.itemData(idx) == current_pref:
                    self.cmb_editor.setCurrentIndex(idx)
                    break
        else:
            self.cmb_editor.addItem("💻 code (VS Code / Predeterminado)", "code")

        c_layout.addWidget(self.cmb_editor)

        layout.addWidget(card)
        layout.addStretch()
        return page

    def create_hardware_ai_page(self):
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")

        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(0, 4, 10, 4)
        layout.setSpacing(14)

        lbl_title = QLabel("Motor, IA, Skills y Personalización")
        lbl_title.setProperty("class", "page_title")
        lbl_sub = QLabel("Configura los 3 modelos de inteligencia artificial local, sus directivas de comportamiento y tema visual.")
        lbl_sub.setProperty("class", "page_subtitle")
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_sub)

        # -------------------------------------------------------------
        # Card 1: Modelos de Inteligencia Artificial (Ollama)
        # -------------------------------------------------------------
        card_ai = QFrame()
        card_ai.setProperty("class", "surface")
        c_ai = QVBoxLayout(card_ai)
        c_ai.setSpacing(12)

        ai_head = QHBoxLayout()
        self.chk_ai = QCheckBox("Habilitar Asistencia de IA Local (Ollama)")
        self.chk_ai.setChecked(self.cfg.get("ai", {}).get("enabled", True))
        self.chk_ai.toggled.connect(self.toggle_ai_section)
        ai_head.addWidget(self.chk_ai)
        ai_head.addStretch()

        self.lbl_ai_status = QLabel("● Buscando Ollama...")
        self.lbl_ai_status.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        ai_head.addWidget(self.lbl_ai_status)
        c_ai.addLayout(ai_head)

        self.ai_container = QWidget()
        l_aic = QVBoxLayout(self.ai_container)
        l_aic.setContentsMargins(0, 4, 0, 0)
        l_aic.setSpacing(10)

        # 1. Modelo Conversacional (Chatbox & Obsidian)
        row_chat = QVBoxLayout()
        row_chat.setSpacing(4)
        lbl_chat = QLabel("1. Modelo Conversacional (Chatbox & Obsidian):")
        lbl_chat.setProperty("class", "label_muted")
        h_chat = QHBoxLayout()
        h_chat.setSpacing(8)
        self.cmb_chat_model = QComboBox()
        self.cmb_chat_model.setItemDelegate(QStyledItemDelegate(self.cmb_chat_model))
        self.txt_chat_model = QLineEdit(self.cfg.get("ai", {}).get("chat_model", ""))
        self.txt_chat_model.setPlaceholderText("Sin modelo (descarga con 'ollama pull <modelo>')")
        h_chat.addWidget(self.cmb_chat_model, 3)
        h_chat.addWidget(self.txt_chat_model, 2)
        row_chat.addWidget(lbl_chat)
        row_chat.addLayout(h_chat)
        l_aic.addLayout(row_chat)

        # 2. Modelo Dev Pesado (Refactor & Auditoría Profunda)
        row_heavy = QVBoxLayout()
        row_heavy.setSpacing(4)
        lbl_heavy = QLabel("2. Modelo Dev Pesado (Refactor & Auditoría Profunda):")
        lbl_heavy.setProperty("class", "label_muted")
        h_heavy = QHBoxLayout()
        h_heavy.setSpacing(8)
        self.cmb_heavy_model = QComboBox()
        self.cmb_heavy_model.setItemDelegate(QStyledItemDelegate(self.cmb_heavy_model))
        self.txt_heavy_model = QLineEdit(self.cfg.get("ai", {}).get("heavy_model", ""))
        self.txt_heavy_model.setPlaceholderText("Sin modelo (descarga con 'ollama pull <modelo>')")
        h_heavy.addWidget(self.cmb_heavy_model, 3)
        h_heavy.addWidget(self.txt_heavy_model, 2)
        row_heavy.addWidget(lbl_heavy)
        row_heavy.addLayout(h_heavy)
        l_aic.addLayout(row_heavy)

        # 3. Modelo Dev Ligero (Git Rápido & IA Commit)
        row_light = QVBoxLayout()
        row_light.setSpacing(4)
        lbl_light = QLabel("3. Modelo Dev Ligero (Git Rápido & IA Commit):")
        lbl_light.setProperty("class", "label_muted")
        h_light = QHBoxLayout()
        h_light.setSpacing(8)
        self.cmb_light_model = QComboBox()
        self.cmb_light_model.setItemDelegate(QStyledItemDelegate(self.cmb_light_model))
        self.txt_light_model = QLineEdit(self.cfg.get("ai", {}).get("light_model", ""))
        self.txt_light_model.setPlaceholderText("Sin modelo (descarga con 'ollama pull <modelo>')")
        h_light.addWidget(self.cmb_light_model, 3)
        h_light.addWidget(self.txt_light_model, 2)
        row_light.addWidget(lbl_light)
        row_light.addLayout(h_light)
        l_aic.addLayout(row_light)

        # Conectar cambios de combos a los campos de texto
        self.cmb_chat_model.currentIndexChanged.connect(lambda: self.on_model_combo_changed(self.cmb_chat_model, self.txt_chat_model))
        self.cmb_heavy_model.currentIndexChanged.connect(lambda: self.on_model_combo_changed(self.cmb_heavy_model, self.txt_heavy_model))
        self.cmb_light_model.currentIndexChanged.connect(lambda: self.on_model_combo_changed(self.cmb_light_model, self.txt_light_model))

        c_ai.addWidget(self.ai_container)
        layout.addWidget(card_ai)

        # -------------------------------------------------------------
        # Card 2: Directivas de Comportamiento & Skills de IA (Texto Genérico)
        # -------------------------------------------------------------
        self.card_skills = QFrame()
        self.card_skills.setProperty("class", "surface")
        c_sk = QVBoxLayout(self.card_skills)
        c_sk.setSpacing(10)

        head_sk = QHBoxLayout()
        lbl_sk_title = QLabel("📜  Skills & Directivas de Comportamiento de IA")
        lbl_sk_title.setProperty("class", "section_title")
        lbl_sk_title.setStyleSheet(f"color: {CYAN}; font-weight: 700;")
        head_sk.addWidget(lbl_sk_title)
        head_sk.addStretch()

        btn_load_defaults = QPushButton("🔄 Cargar Valores Predeterminados")
        btn_load_defaults.setCursor(Qt.PointingHandCursor)
        btn_load_defaults.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(6, 182, 212, 0.15);
                color: {CYAN};
                border: 1px solid rgba(6, 182, 212, 0.35);
                border-radius: 5px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: rgba(6, 182, 212, 0.28);
                color: #ffffff;
            }}
        """)
        btn_load_defaults.clicked.connect(self.restore_default_skills)
        head_sk.addWidget(btn_load_defaults)
        c_sk.addLayout(head_sk)

        lbl_sk_desc = QLabel("Texto genérico predeterminado disponible para personalizar las instrucciones de sistema de cada modelo:")
        lbl_sk_desc.setProperty("class", "label_muted")
        lbl_sk_desc.setWordWrap(True)
        c_sk.addWidget(lbl_sk_desc)

        # 1. Skill Conversacional
        lbl_sk_c = QLabel("Skill Conversacional (Chatbox / Oracle):")
        lbl_sk_c.setStyleSheet(f"font-size: 11.5px; font-weight: 600; color: {TEXT_PRIMARY};")
        self.txt_sk_chat = QTextEdit()
        self.txt_sk_chat.setFixedHeight(65)
        self.txt_sk_chat.setStyleSheet(f"background-color: {BG_INPUT}; border: 1px solid {BORDER_BASE}; border-radius: 6px; font-size: 11.5px; color: {TEXT_PRIMARY}; padding: 6px;")
        c_sk.addWidget(lbl_sk_c)
        c_sk.addWidget(self.txt_sk_chat)

        # 2. Skill Modelo Dev Pesado (Auditoría Profunda & Refactor)
        lbl_sk_h = QLabel("Skill Modelo Dev Pesado (Auditoría Profunda & Refactor):")
        lbl_sk_h.setStyleSheet(f"font-size: 11.5px; font-weight: 600; color: {TEXT_PRIMARY};")
        self.txt_sk_heavy = QTextEdit()
        self.txt_sk_heavy.setFixedHeight(75)
        self.txt_sk_heavy.setStyleSheet(f"background-color: {BG_INPUT}; border: 1px solid {BORDER_BASE}; border-radius: 6px; font-size: 11.5px; color: {TEXT_PRIMARY}; padding: 6px;")
        c_sk.addWidget(lbl_sk_h)
        c_sk.addWidget(self.txt_sk_heavy)

        # 3. Skill Modelo Dev Ligero (Git Rápido & IA Commit)
        lbl_sk_l = QLabel("Skill Modelo Dev Ligero (Git Rápido & IA Commit):")
        lbl_sk_l.setStyleSheet(f"font-size: 11.5px; font-weight: 600; color: {TEXT_PRIMARY};")
        self.txt_sk_light = QTextEdit()
        self.txt_sk_light.setFixedHeight(75)
        self.txt_sk_light.setStyleSheet(f"background-color: {BG_INPUT}; border: 1px solid {BORDER_BASE}; border-radius: 6px; font-size: 11.5px; color: {TEXT_PRIMARY}; padding: 6px;")
        c_sk.addWidget(lbl_sk_l)
        c_sk.addWidget(self.txt_sk_light)

        # Cargar textos genéricos iniciales
        self.load_generic_skills()
        layout.addWidget(self.card_skills)

        # -------------------------------------------------------------
        # Card 3: Tema Visual
        # -------------------------------------------------------------
        card_theme = QFrame()
        card_theme.setProperty("class", "surface")
        c_th = QVBoxLayout(card_theme)
        c_th.setSpacing(10)

        t_row = QHBoxLayout()
        t_row.setSpacing(8)
        lbl_thm = QLabel("Tema Visual:")
        lbl_thm.setProperty("class", "section_title")
        self.cmb_theme = QComboBox()
        self.cmb_theme.setItemDelegate(QStyledItemDelegate(self.cmb_theme))
        self.cmb_theme.addItems([
            "Noctalia Minimal (Sincronizado con el sistema)", 
            "Dark Cyberpunk", 
            "Monocromo Puro"
        ])
        t_row.addWidget(lbl_thm)
        t_row.addWidget(self.cmb_theme, 1)
        c_th.addLayout(t_row)

        layout.addWidget(card_theme)
        layout.addStretch()

        scroll.setWidget(content_widget)
        page_layout.addWidget(scroll)

        # Scan Ollama Models in background
        self.scan_ollama_models()
        return page

    # =================================================================
    #  PAGE 4: SUMMARY & FINISH
    # =================================================================
    def create_finish_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(14)

        self.lbl_finish_status = QLabel("Listo para aplicar configuración...")
        self.lbl_finish_status.setProperty("class", "page_title")
        layout.addWidget(self.lbl_finish_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.summary_card = QFrame()
        self.summary_card.setProperty("class", "surface")
        s_layout = QVBoxLayout(self.summary_card)
        s_layout.setSpacing(10)

        self.lbl_summary = QLabel("Procesando preferencias...")
        self.lbl_summary.setStyleSheet(f"color: {TEXT_PRIMARY}; line-height: 1.6;")
        self.lbl_summary.setWordWrap(True)
        s_layout.addWidget(self.lbl_summary)

        layout.addWidget(self.summary_card)
        layout.addStretch()
        return page

    # =================================================================
    #  HELPERS & EVENT HANDLERS
    # =================================================================
    def toggle_vault_section(self, checked):
        self.vault_container.setVisible(checked)

    def toggle_btrfs_section(self, checked):
        self.btrfs_container.setVisible(checked)

    def toggle_ai_section(self, checked):
        self.ai_container.setVisible(checked)
        if hasattr(self, "card_skills"):
            self.card_skills.setVisible(checked)

    def on_model_combo_changed(self, cmb, txt):
        data = cmb.currentData()
        if data:
            txt.setText(data)

    def load_generic_skills(self):
        """Carga el texto genérico predeterminado disponible para personalizar las directivas."""
        chat_path = os.path.join(ROOT_DIR, "skills", "chat_skill.txt")
        chat_path = os.path.join(ROOT_DIR, "skills", "chat_skill.txt")
        if os.path.exists(chat_path):
            try:
                with open(chat_path, "r", encoding="utf-8") as f:
                    self.txt_sk_chat.setPlainText(f.read().strip())
            except Exception:
                pass

        heavy_path = os.path.join(ROOT_DIR, "skills", "heavy_skill.txt")
        if os.path.exists(heavy_path):
            try:
                with open(heavy_path, "r", encoding="utf-8") as f:
                    self.txt_sk_heavy.setPlainText(f.read().strip())
            except Exception:
                pass

        light_path = os.path.join(ROOT_DIR, "skills", "light_skill.txt")
        if os.path.exists(light_path):
            try:
                with open(light_path, "r", encoding="utf-8") as f:
                    self.txt_sk_light.setPlainText(f.read().strip())
            except Exception:
                pass

    def restore_default_skills(self):
        """Limpia las directivas de skills."""
        self.txt_sk_chat.clear()
        self.txt_sk_heavy.clear()
        self.txt_sk_light.clear()

    def scan_ollama_models(self):
        models_info = []
        # 1. Intentar HTTP API de Ollama
        try:
            req = urllib.request.Request("http://localhost:11434/api/tags")
            with urllib.request.urlopen(req, timeout=1.2) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                for m in data.get('models', []):
                    name = m.get('name')
                    size_bytes = m.get('size', 0)
                    size_gb = f"{round(size_bytes / (1024**3), 1)} GB" if size_bytes else ""
                    models_info.append((name, size_gb))
        except Exception:
            pass

        # 2. Fallback CLI `ollama list`
        if not models_info and shutil.which("ollama"):
            try:
                out = subprocess.check_output(["ollama", "list"], text=True, timeout=2.0)
                lines = out.strip().splitlines()
                if len(lines) > 1:
                    for line in lines[1:]:
                        parts = line.split()
                        if len(parts) >= 3:
                            name = parts[0]
                            size = f"{parts[2]} {parts[3]}" if len(parts) >= 4 else parts[2]
                            models_info.append((name, size))
            except Exception:
                pass

        combos = [self.cmb_chat_model, self.cmb_heavy_model, self.cmb_light_model]
        for cmb in combos:
            cmb.blockSignals(True)
            cmb.clear()

        if models_info:
            self.lbl_ai_status.setText(f"● Ollama Activo ({len(models_info)} modelo{'s' if len(models_info) > 1 else ''})")
            self.lbl_ai_status.setStyleSheet(f"color: {SUCCESS}; font-size: 11px; font-weight: 600;")
            for name, size in models_info:
                display_label = f"⚡  {name} ({size})" if size else f"⚡  {name}"
                for cmb in combos:
                    cmb.addItem(display_label, userData=name)

            # Seleccionar automáticamente solo si existen modelos instalados
            chat_val = self.txt_chat_model.text().strip()
            heavy_val = self.txt_heavy_model.text().strip()
            light_val = self.txt_light_model.text().strip()

            def select_best(cmb, target_str):
                for i in range(cmb.count()):
                    d = cmb.itemData(i) or ""
                    if target_str and target_str.lower() in d.lower():
                        cmb.setCurrentIndex(i)
                        return d
                if cmb.count() > 0:
                    return cmb.itemData(0) or cmb.currentText()
                return target_str

            c_found = select_best(self.cmb_chat_model, chat_val)
            if not chat_val and c_found: self.txt_chat_model.setText(c_found)

            h_found = select_best(self.cmb_heavy_model, heavy_val)
            if not heavy_val and h_found: self.txt_heavy_model.setText(h_found)

            l_found = select_best(self.cmb_light_model, light_val)
            if not light_val and l_found: self.txt_light_model.setText(l_found)
        else:
            self.lbl_ai_status.setText("○ Sin modelos instalados en Ollama")
            self.lbl_ai_status.setStyleSheet(f"color: {WARNING}; font-size: 11px;")
            for cmb in combos:
                cmb.addItem("⚠️ Ningún modelo instalado", userData="")

            # No autocompletar modelos ficticios si no hay ninguno instalado
            self.txt_chat_model.clear()
            self.txt_heavy_model.clear()
            self.txt_light_model.clear()

        for cmb in combos:
            cmb.blockSignals(False)

    def browse_folder(self, line_edit):
        curr = os.path.expanduser(line_edit.text())
        folder = QFileDialog.getExistingDirectory(
            self, 
            "Seleccionar Carpeta", 
            curr if os.path.exists(curr) else os.path.expanduser("~")
        )
        if folder:
            line_edit.setText(folder)

    def next_page(self):
        idx = self.stacked.currentIndex()
        if idx == 0:
            self.stacked.setCurrentIndex(1)
            self.btn_back.show()
            self.btn_next.setText("Siguiente ➔")
            self.update_stepper(1)
        elif idx == 1:
            self.stacked.setCurrentIndex(2)
            self.btn_next.setText("Instalar ABRAXAS ➔" if not self.is_preview else "Simular Instalación ➔")
            self.update_stepper(2)
        elif idx == 2:
            self.stacked.setCurrentIndex(3)
            self.btn_back.hide()
            self.btn_next.setEnabled(False)
            self.btn_next.setText("Procesando...")
            self.update_stepper(3)
            self.perform_installation()
        elif idx == 3:
            self.close()

    def prev_page(self):
        idx = self.stacked.currentIndex()
        if idx == 1:
            self.stacked.setCurrentIndex(0)
            self.btn_back.hide()
            self.btn_next.setText("Continuar ➔")
            self.update_stepper(0)
        elif idx == 2:
            self.stacked.setCurrentIndex(1)
            self.btn_next.setText("Siguiente ➔")
            self.update_stepper(1)

    def perform_installation(self):
        # 1. Rutas
        # 1. Rutas
        if "paths" not in self.cfg: self.cfg["paths"] = {}
        self.cfg["paths"]["projects_dir"] = self.txt_projects.text().strip()
        self.cfg["paths"]["vault_dir"] = self.txt_vault.text().strip() if self.chk_vault_enable.isChecked() else ""

        # 1.5. Git Identity
        if "git" not in self.cfg: self.cfg["git"] = {}
        self.cfg["git"]["user_name"] = self.txt_git_user.text().strip()
        self.cfg["git"]["user_email"] = self.txt_git_email.text().strip()
        self.cfg["git"]["auto_sync_global"] = self.chk_git_sync.isChecked()

        # 1.6. Editor Preferido (LUMEN)
        if "environments" not in self.cfg: self.cfg["environments"] = {}
        self.cfg["environments"]["preferred_editor"] = self.cmb_editor.currentData() or "code"

        # 2. Sistema
        if "system" not in self.cfg: self.cfg["system"] = {}
        self.cfg["system"]["btrfs_snapshots"] = self.chk_btrfs_enable.isChecked()
        self.cfg["system"]["snapper_config"] = "root"

        # 3. IA (3 Modelos & Skills)
        if "ai" not in self.cfg: self.cfg["ai"] = {}
        self.cfg["ai"]["enabled"] = self.chk_ai.isChecked()
        
        chat_m = self.txt_chat_model.text().strip() or self.cmb_chat_model.currentData() or self.cmb_chat_model.currentText()
        heavy_m = self.txt_heavy_model.text().strip() or self.cmb_heavy_model.currentData() or self.cmb_heavy_model.currentText()
        light_m = self.txt_light_model.text().strip() or self.cmb_light_model.currentData() or self.cmb_light_model.currentText()

        self.cfg["ai"]["chat_model"] = chat_m
        self.cfg["ai"]["heavy_model"] = heavy_m
        self.cfg["ai"]["light_model"] = light_m

        if "skills" not in self.cfg["ai"]: self.cfg["ai"]["skills"] = {}
        self.cfg["ai"]["skills"]["chat_skill_path"] = "skills/chat_skill.txt"
        self.cfg["ai"]["skills"]["heavy_skill_path"] = "skills/heavy_skill.txt"
        self.cfg["ai"]["skills"]["light_skill_path"] = "skills/light_skill.txt"

        # 4. Tema
        if "abraxas" not in self.cfg: self.cfg["abraxas"] = {}
        theme_raw = self.cmb_theme.currentText().lower()
        if "cyberpunk" in theme_raw: self.cfg["abraxas"]["theme"] = "dark_cyberpunk"
        elif "monocromo" in theme_raw: self.cfg["abraxas"]["theme"] = "monochrome"
        else: self.cfg["abraxas"]["theme"] = "noctalia"

        QTimer.singleShot(300, lambda: self.progress_bar.setValue(50))
        QTimer.singleShot(700, self.finish_installation)

    def finish_installation(self):
        if not self.is_preview:
            write_toml_dict(self.config_target, self.cfg)

            # Sincronizar identidad Git global si corresponde
            if self.cfg.get("git", {}).get("auto_sync_global", True):
                g_u = self.cfg.get("git", {}).get("user_name", "")
                g_e = self.cfg.get("git", {}).get("user_email", "")
                if g_u or g_e:
                    sync_global_gitconfig(g_u, g_e)
            
            # Guardar editor preferido en disco para Lumen Sector 2
            sel_ed = self.cfg.get("environments", {}).get("preferred_editor", "code")
            set_preferred_editor(sel_ed)

            # Guardar archivos de Skills personalizados o vacíos en el disco
            skills_dir = os.path.join(ROOT_DIR, "skills")
            os.makedirs(skills_dir, exist_ok=True)
            try:
                with open(os.path.join(skills_dir, "chat_skill.txt"), "w", encoding="utf-8") as f:
                    f.write(self.txt_sk_chat.toPlainText().strip())
                with open(os.path.join(skills_dir, "heavy_skill.txt"), "w", encoding="utf-8") as f:
                    f.write(self.txt_sk_heavy.toPlainText().strip())
                with open(os.path.join(skills_dir, "light_skill.txt"), "w", encoding="utf-8") as f:
                    f.write(self.txt_sk_light.toPlainText().strip())
            except Exception as e:
                print(f"Error escribiendo directivas de skills: {e}")

            # Registrar lanzador de escritorio y comando abx
            launcher_sh = os.path.join(ROOT_DIR, "scripts", "install_desktop_launcher.sh")
            if os.path.exists(launcher_sh):
                try:
                    subprocess.run(["bash", launcher_sh], check=False, capture_output=True)
                except Exception as e:
                    print(f"Error registrando lanzador de escritorio: {e}")

            # Crear directorios de proyectos y bóveda de Obsidian si corresponde
            try:
                p_dir = os.path.expanduser(self.cfg.get("paths", {}).get("projects_dir", "~/Proyectos"))
                if p_dir:
                    os.makedirs(p_dir, exist_ok=True)
                if self.chk_vault_enable.isChecked():
                    v_dir = os.path.expanduser(self.cfg.get("paths", {}).get("vault_dir", ""))
                    if v_dir:
                        os.makedirs(os.path.join(v_dir, "00_Inbox"), exist_ok=True)
                        os.makedirs(os.path.join(v_dir, "01_Proyectos"), exist_ok=True)
                        os.makedirs(os.path.join(v_dir, "02_Memoria"), exist_ok=True)
            except Exception as e:
                print(f"Error inicializando directorios de trabajo: {e}")
            
        self.progress_bar.setValue(100)
        
        btrfs_status = f"<font color='{SUCCESS}'>Activo</font>" if self.cfg.get("system", {}).get("btrfs_snapshots", False) else f"<font color='{TEXT_MUTED}'>Deshabilitado</font>"
        ai_status = (
            f"<font color='{SUCCESS}'>Habilitada</font><br/>"
            f"&nbsp;&nbsp;• <b>Chat:</b> {self.cfg['ai']['chat_model']}<br/>"
            f"&nbsp;&nbsp;• <b>Pesado (Audit):</b> {self.cfg['ai']['heavy_model']}<br/>"
            f"&nbsp;&nbsp;• <b>Ligero (Commit):</b> {self.cfg['ai']['light_model']}<br/>"
            f"&nbsp;&nbsp;• <b>Skills:</b> Directivas configuradas en <code>skills/</code>"
        ) if self.cfg["ai"]["enabled"] else f"<font color='{TEXT_MUTED}'>Deshabilitada</font>"
        vault_status = f"{self.cfg['paths']['vault_dir']}" if self.chk_vault_enable.isChecked() else f"<font color='{TEXT_MUTED}'>Omitido</font>"
        editor_label = self.cmb_editor.currentText()

        if self.is_preview:
            self.lbl_finish_status.setText("Simulación Completada con Éxito")
            summary_text = (
                f"<b>Resumen de Parámetros Configurados:</b><br/><br/>"
                f"• <b>Destino:</b> {self.config_target} <font color='{WARNING}'>(Modo Simulación: Intacto)</font><br/>"
                f"• <b>Proyectos Git (LUMEN):</b> {self.cfg['paths']['projects_dir']}<br/>"
                f"• <b>Editor Preferido (LUMEN):</b> {editor_label}<br/>"
                f"• <b>Bóveda Obsidian (NOUS):</b> {vault_status}<br/>"
                f"• <b>Protección Btrfs (UMBRA):</b> {btrfs_status}<br/>"
                f"• <b>Asistente IA Local & Skills:</b><br/>{ai_status}<br/><br/>"
                f"<font color='{SUCCESS}'>✔ No se realizaron modificaciones en el sistema.</font>"
            )
            self.btn_next.setText("Cerrar Simulación")
        else:
            self.lbl_finish_status.setText(f"Instalación de ABRAXAS v{self.app_version} Completada")
            summary_text = (
                f"<b>Configuración Generada:</b><br/><br/>"
                f"• <b>Archivo:</b> {self.config_target} (chmod 600)<br/>"
                f"• <b>Proyectos Git (LUMEN):</b> {self.cfg['paths']['projects_dir']}<br/>"
                f"• <b>Editor Preferido (LUMEN):</b> {editor_label}<br/>"
                f"• <b>Bóveda Obsidian (NOUS):</b> {vault_status}<br/>"
                f"• <b>Protección Btrfs (UMBRA):</b> {btrfs_status}<br/>"
                f"• <b>Asistente IA Local & Skills:</b><br/>{ai_status}<br/><br/>"
                f"<font color='{CYAN}'>Todo listo. Inicia tu entorno ejecutando <b>abx</b> en tu terminal.</font>"
            )
            self.btn_next.setText("Finalizar")

        self.lbl_summary.setText(summary_text)
        self.btn_next.setEnabled(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = AbraxasInstallerGUI()
    gui.show()
    sys.exit(app.exec())
