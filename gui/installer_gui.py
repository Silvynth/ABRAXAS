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
    QComboBox
)
from PySide6.QtCore import Qt, QTimer

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from core.setup import write_toml_dict, read_toml_dict, TEMPLATE_PATH, get_target_config_path

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

/* Surface Cards */
QFrame.surface {{
    background-color: {BG_SURFACE};
    border: 1px solid {BORDER_BASE};
    border-radius: 10px;
    padding: 16px;
}}

QFrame.stat_card {{
    background-color: {BG_SURFACE};
    border: 1px solid {BORDER_BASE};
    border-radius: 8px;
    padding: 12px;
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
}}

QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {BORDER_BASE};
    border-radius: 4px;
    background-color: {BG_INPUT};
}}

QRadioButton::indicator {{
    border-radius: 8px;
}}

QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
}}

/* Combo Dropdown */
QComboBox {{
    background-color: {BG_INPUT};
    border: 1px solid {BORDER_BASE};
    border-radius: 7px;
    padding: 7px 12px;
    color: {TEXT_PRIMARY};
    font-size: 13px;
}}

QComboBox:hover {{
    border-color: #3b3e4f;
}}

QComboBox:focus {{
    border-color: {BORDER_FOCUS};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
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
        
        if self.is_preview:
            self.setWindowTitle("ABRAXAS — Asistente de Instalación [Vista Previa]")
        else:
            self.setWindowTitle("ABRAXAS — Asistente de Instalación")
            
        self.setFixedSize(780, 580)
        self.setStyleSheet(STYLESHEET)
        
        # Hardware Probe & Config
        self.hw_info = probe_system_hardware()
        self.config_target = get_target_config_path()
        self.cfg = read_toml_dict(self.config_target) or read_toml_dict(TEMPLATE_PATH)
        
        self.init_ui()
        self.center_window()

    def center_window(self):
        qr = self.frameGeometry()
        cp = self.screen().availableGeometry().center()
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
        
        lbl_ver = QLabel("v0.1.0")
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
        c_layout.setSpacing(14)

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
        v_box.setContentsMargins(0, 0, 0, 0)
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
        b_box.setContentsMargins(0, 0, 0, 0)
        b_box.setSpacing(4)
        
        lbl_snap = QLabel("Subvolumen de instantáneas raíz (ej. Snapper):")
        lbl_snap.setProperty("class", "label_muted")
        self.txt_snap = QLineEdit(self.cfg.get("paths", {}).get("snapshots_dir", "/.snapshots"))
        b_box.addWidget(lbl_snap)
        b_box.addWidget(self.txt_snap)
        c_layout.addWidget(self.btrfs_container)

        layout.addWidget(card)
        layout.addStretch()
        return page

    # =================================================================
    #  PAGE 3: ENGINE, AI & HARDWARE PROFILES
    # =================================================================
    def create_hardware_ai_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(14)

        lbl_title = QLabel("Motor, IA y Perfil de Rendimiento")
        lbl_title.setProperty("class", "page_title")
        lbl_sub = QLabel("Ajusta la asistencia de inteligencia artificial local y el comportamiento energético.")
        lbl_sub.setProperty("class", "page_subtitle")
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_sub)

        # Card: AI Section
        card_ai = QFrame()
        card_ai.setProperty("class", "surface")
        c_ai = QVBoxLayout(card_ai)
        c_ai.setSpacing(10)

        self.chk_ai = QCheckBox("Habilitar Asistente de IA Local (Ollama)")
        self.chk_ai.setChecked(self.cfg.get("ai", {}).get("enabled", True))
        self.chk_ai.toggled.connect(self.toggle_ai_section)
        c_ai.addWidget(self.chk_ai)

        self.ai_container = QWidget()
        l_aic = QVBoxLayout(self.ai_container)
        l_aic.setContentsMargins(0, 0, 0, 0)
        l_aic.setSpacing(6)

        ai_row = QHBoxLayout()
        ai_row.setSpacing(8)
        lbl_model_tag = QLabel("Modelo Predeterminado:")
        lbl_model_tag.setProperty("class", "label_muted")
        self.cmb_model = QComboBox()
        self.lbl_ai_status = QLabel("● Buscando Ollama...")
        self.lbl_ai_status.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        
        ai_row.addWidget(lbl_model_tag)
        ai_row.addWidget(self.cmb_model, 1)
        ai_row.addWidget(self.lbl_ai_status)
        l_aic.addLayout(ai_row)
        c_ai.addWidget(self.ai_container)
        layout.addWidget(card_ai)

        # Card: Hardware Profile & Appearance
        card_hw = QFrame()
        card_hw.setProperty("class", "surface")
        c_hw = QVBoxLayout(card_hw)
        c_hw.setSpacing(12)

        lbl_prof_t = QLabel("Perfil de Rendimiento:")
        lbl_prof_t.setProperty("class", "section_title")
        c_hw.addWidget(lbl_prof_t)

        h_profiles = QHBoxLayout()
        h_profiles.setSpacing(10)

        self.rb_auto = QRadioButton("Auto (Equilibrado)")
        self.rb_high = QRadioButton("Alto Rendimiento")
        self.rb_eco = QRadioButton("Bajo Consumo")
        
        if self.hw_info["ram_gb"] >= 16 and self.hw_info["cuda"]:
            self.rb_high.setChecked(True)
        else:
            self.rb_auto.setChecked(True)

        h_profiles.addWidget(self.rb_auto)
        h_profiles.addWidget(self.rb_high)
        h_profiles.addWidget(self.rb_eco)
        c_hw.addLayout(h_profiles)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setStyleSheet(f"background-color: {BORDER_BASE}; max-height: 1px; border: none;")
        c_hw.addWidget(div)

        # Visual Theme
        t_row = QHBoxLayout()
        t_row.setSpacing(8)
        lbl_thm = QLabel("Tema Visual:")
        lbl_thm.setProperty("class", "section_title")
        self.cmb_theme = QComboBox()
        self.cmb_theme.addItems([
            "Noctalia Minimal (Sincronizado con el sistema)", 
            "Dark Cyberpunk", 
            "Monocromo Puro"
        ])
        t_row.addWidget(lbl_thm)
        t_row.addWidget(self.cmb_theme, 1)
        c_hw.addLayout(t_row)

        layout.addWidget(card_hw)
        layout.addStretch()

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

    def scan_ollama_models(self):
        models = []
        try:
            req = urllib.request.Request("http://localhost:11434/api/tags")
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                models = [m.get('name') for m in data.get('models', [])]
        except Exception:
            pass

        self.cmb_model.clear()
        if models:
            self.lbl_ai_status.setText("● En línea")
            self.lbl_ai_status.setStyleSheet(f"color: {SUCCESS}; font-size: 11px; font-weight: 600;")
            for m in models:
                self.cmb_model.addItem(m)
        else:
            self.lbl_ai_status.setText("○ Desconectado")
            self.lbl_ai_status.setStyleSheet(f"color: {WARNING}; font-size: 11px;")
            self.cmb_model.addItems(["qwen2.5-coder:7b", "llama3.1:8b", "qwen2.5-coder:14b"])

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
        if "paths" not in self.cfg: self.cfg["paths"] = {}
        self.cfg["paths"]["projects_dir"] = self.txt_projects.text().strip()
        self.cfg["paths"]["vault_dir"] = self.txt_vault.text().strip() if self.chk_vault_enable.isChecked() else ""
        self.cfg["paths"]["snapshots_dir"] = self.txt_snap.text().strip() if self.chk_btrfs_enable.isChecked() else ""

        # 2. Hardware
        if "hardware" not in self.cfg: self.cfg["hardware"] = {}
        if self.rb_high.isChecked(): self.cfg["hardware"]["profile"] = "high_performance"
        elif self.rb_eco.isChecked(): self.cfg["hardware"]["profile"] = "low_power"
        else: self.cfg["hardware"]["profile"] = "auto"

        # 3. Módulos
        if "modules" not in self.cfg: self.cfg["modules"] = {}
        if "umbra" not in self.cfg["modules"]: self.cfg["modules"]["umbra"] = {}
        self.cfg["modules"]["umbra"]["btrfs_snapshots"] = self.chk_btrfs_enable.isChecked()

        if "nous" not in self.cfg["modules"]: self.cfg["modules"]["nous"] = {}
        self.cfg["modules"]["nous"]["obsidian_sync"] = self.chk_vault_enable.isChecked()

        # 4. IA
        if "ai" not in self.cfg: self.cfg["ai"] = {}
        self.cfg["ai"]["enabled"] = self.chk_ai.isChecked()
        self.cfg["ai"]["default_model"] = self.cmb_model.currentText() if self.chk_ai.isChecked() else ""

        # 5. Tema
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
            
        self.progress_bar.setValue(100)
        
        btrfs_status = f"<font color='{SUCCESS}'>Activo ({self.cfg['paths']['snapshots_dir']})</font>" if self.cfg["modules"]["umbra"]["btrfs_snapshots"] else f"<font color='{TEXT_MUTED}'>Deshabilitado</font>"
        ai_status = f"<font color='{SUCCESS}'>Habilitada ({self.cfg['ai']['default_model']})</font>" if self.cfg["ai"]["enabled"] else f"<font color='{TEXT_MUTED}'>Deshabilitada</font>"
        vault_status = f"{self.cfg['paths']['vault_dir']}" if self.cfg["modules"]["nous"]["obsidian_sync"] else f"<font color='{TEXT_MUTED}'>Omitido</font>"

        if self.is_preview:
            self.lbl_finish_status.setText("Simulación Completada con Éxito")
            summary_text = (
                f"<b>Resumen de Parámetros Configurados:</b><br/><br/>"
                f"• <b>Destino:</b> {self.config_target} <font color='{WARNING}'>(Modo Simulación: Intacto)</font><br/>"
                f"• <b>Proyectos Git (LUMEN):</b> {self.cfg['paths']['projects_dir']}<br/>"
                f"• <b>Bóveda Obsidian (NOUS):</b> {vault_status}<br/>"
                f"• <b>Protección Btrfs (UMBRA):</b> {btrfs_status}<br/>"
                f"• <b>Asistente IA Local:</b> {ai_status}<br/>"
                f"• <b>Perfil de Rendimiento:</b> {self.cfg['hardware']['profile'].upper()}<br/><br/>"
                f"<font color='{SUCCESS}'>✔ No se realizaron modificaciones en el sistema.</font>"
            )
            self.btn_next.setText("Cerrar Simulación")
        else:
            self.lbl_finish_status.setText("Instalación de ABRAXAS Completada")
            summary_text = (
                f"<b>Configuración Generada:</b><br/><br/>"
                f"• <b>Archivo:</b> {self.config_target} (chmod 600)<br/>"
                f"• <b>Proyectos Git (LUMEN):</b> {self.cfg['paths']['projects_dir']}<br/>"
                f"• <b>Bóveda Obsidian (NOUS):</b> {vault_status}<br/>"
                f"• <b>Protección Btrfs (UMBRA):</b> {btrfs_status}<br/>"
                f"• <b>Asistente IA Local:</b> {ai_status}<br/>"
                f"• <b>Perfil de Rendimiento:</b> {self.cfg['hardware']['profile'].upper()}<br/><br/>"
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
