#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS | LUMEN - PROJECT WORKSPACE VIEW (DASHBOARD DEL PROYECTO)
# =====================================================================

import os
import subprocess
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QScrollArea, QGridLayout,
    QTextEdit, QApplication, QStackedWidget, QSizePolicy,
    QProgressBar
)
from PySide6.QtCore import Qt, Signal, QTimer, QThread

from core import get_version
from core.lumen_sync import get_full_project_sync
from core.ai import get_configured_model, audit_git_diff
from core.git_workflow import (
    get_project_semver, bump_semver, 
    generate_ia_commit_proposal, execute_commit_and_tag
)


class GitPushThread(QThread):
    """Hilo para ejecutar git push origin <branch> sin congelar la GUI."""
    finished_push = Signal(bool, str, str)

    def __init__(self, project_path: str, follow_tags: bool = False):
        super().__init__()
        self.project_path = project_path
        self.follow_tags = follow_tags

    def run(self):
        try:
            b_proc = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.project_path, capture_output=True, text=True, timeout=6
            )
            branch = b_proc.stdout.strip() or "main"

            cmd = ["git", "push", "--follow-tags", "origin", branch] if self.follow_tags else ["git", "push", "origin", branch]
            p_proc = subprocess.run(
                cmd,
                cwd=self.project_path, capture_output=True, text=True, timeout=45
            )
            if p_proc.returncode == 0:
                out = p_proc.stdout.strip() or p_proc.stderr.strip() or "Todo sincronizado con el repositorio remoto."
                self.finished_push.emit(True, branch, out)
            else:
                if self.follow_tags:
                    p1 = subprocess.run(["git", "push", "origin", branch], cwd=self.project_path, capture_output=True, text=True, timeout=45)
                    p2 = subprocess.run(["git", "push", "--tags"], cwd=self.project_path, capture_output=True, text=True, timeout=45)
                    if p1.returncode == 0:
                        self.finished_push.emit(True, branch, f"{p1.stdout}\n{p2.stdout}".strip())
                        return
                err = p_proc.stderr.strip() or p_proc.stdout.strip() or "Error desconocido durante git push."
                self.finished_push.emit(False, branch, err)
        except Exception as e:
            self.finished_push.emit(False, "unknown", str(e))


class IACommitThread(QThread):
    """Hilo para generar la propuesta de commit con IA (Protocolo Artemis) sin congelar la GUI."""
    finished_commit = Signal(bool, str, dict)

    def __init__(self, project_path: str, model_type: str, impact_type: str, target_ver: str):
        super().__init__()
        self.project_path = project_path
        self.model_type = model_type
        self.impact_type = impact_type
        self.target_ver = target_ver

    def run(self):
        try:
            res = generate_ia_commit_proposal(
                self.project_path,
                self.model_type,
                self.impact_type,
                self.target_ver
            )
            self.finished_commit.emit(True, "", res)
        except Exception as e:
            self.finished_commit.emit(False, str(e), {})


class IAAuditThread(QThread):
    """Hilo para analizar diff de git y consultar a Ollama sin congelar la GUI."""
    finished_audit = Signal(bool, str, dict)

    def __init__(self, project_path: str, model_type: str = "light"):
        super().__init__()
        self.project_path = project_path
        self.model_type = model_type

    def run(self):
        try:
            # 1. Obtener diff (staging primero, luego árbol de trabajo, luego último commit)
            d_cached = subprocess.run(
                ["git", "diff", "--cached"],
                cwd=self.project_path, capture_output=True, text=True, timeout=10
            )
            diff_text = d_cached.stdout.strip()

            if not diff_text:
                d_work = subprocess.run(
                    ["git", "diff", "HEAD"],
                    cwd=self.project_path, capture_output=True, text=True, timeout=10
                )
                diff_text = d_work.stdout.strip()

            if not diff_text:
                d_last = subprocess.run(
                    ["git", "diff", "HEAD~1", "HEAD"],
                    cwd=self.project_path, capture_output=True, text=True, timeout=10
                )
                diff_text = d_last.stdout.strip()

            if not diff_text:
                self.finished_audit.emit(
                    False, 
                    "No se detectaron diferencias (diff vacío) en staging, árbol de trabajo ni en el último commit.",
                    {}
                )
                return

            res = audit_git_diff(diff_text, model_type=self.model_type)
            self.finished_audit.emit(True, "", res)
        except Exception as e:
            self.finished_audit.emit(False, str(e), {})


class LumenCyberActionButton(QFrame):
    """Botón interactivo de diseño ciber-ilustre con icono, título, subtítulo y efectos de hover."""
    
    clicked = Signal(str)

    def __init__(self, icon: str, title: str, subtitle: str, accent_color="#6366f1", parent=None):
        super().__init__(parent)
        self.action_title = title
        self.accent_color = accent_color
        self.setCursor(Qt.PointingHandCursor)
        self.setProperty("class", "cyber_action_card")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(56)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(12)

        # Icono con contenedor estilizado
        self.lbl_icon = QLabel(icon)
        self.lbl_icon.setAlignment(Qt.AlignCenter)
        self.lbl_icon.setFixedSize(36, 36)
        self.lbl_icon.setStyleSheet(f"""
            QLabel {{
                background-color: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 8px;
                font-size: 16px;
            }}
        """)
        layout.addWidget(self.lbl_icon)

        # Textos (Título + Subtítulo)
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #f3f4f6;")

        self.lbl_sub = QLabel(subtitle)
        self.lbl_sub.setStyleSheet("font-size: 11px; color: #9ca3af;")

        text_layout.addWidget(self.lbl_title)
        text_layout.addWidget(self.lbl_sub)
        layout.addLayout(text_layout, 1)

        # Flecha indicadora derecha
        self.lbl_arrow = QLabel("›")
        self.lbl_arrow.setStyleSheet("font-size: 18px; font-weight: 800; color: #4b5563;")
        layout.addWidget(self.lbl_arrow)

        self.setStyleSheet(f"""
            QFrame.cyber_action_card {{
                background-color: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.07);
                border-radius: 8px;
            }}
            QFrame.cyber_action_card:hover {{
                background-color: rgba(99, 102, 241, 0.14);
                border: 1px solid {self.accent_color};
            }}
        """)

    def set_title(self, title: str):
        self.action_title = title
        self.lbl_title.setText(title)

    def set_subtitle(self, subtitle: str):
        self.lbl_sub.setText(subtitle)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.action_title)
        super().mousePressEvent(event)


class LumenTerminalDisplay(QTextEdit):
    """Visor de terminal de SOLO LECTURA con soporte de colores HTML ricos, tags ciberpunk y diseño estético."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMinimumHeight(150)
        self.setCursor(Qt.IBeamCursor)
        self.setLineWrapMode(QTextEdit.WidgetWidth)
        self.setStyleSheet("""
            QTextEdit {
                background-color: #07090e;
                color: #e5e7eb;
                font-family: 'JetBrains Mono', 'Fira Code', 'DejaVu Sans Mono', 'Consolas', monospace;
                font-size: 12.5px;
                line-height: 1.5;
                border: none;
                padding: 14px 18px;
                selection-background-color: #4f46e5;
                selection-color: #ffffff;
            }
            QScrollBar:vertical {
                background: #090b10;
                width: 10px;
                margin: 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #1f2430;
                min-height: 24px;
                border-radius: 4px;
                border: 1px solid rgba(255, 255, 255, 0.05);
            }
            QScrollBar::handle:vertical:hover {
                background: #6366f1;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

    def log(self, tag: str, message: str, tag_color: str = "#38bdf8", text_color: str = "#e5e7eb", prefix: str = "◈"):
        """Imprime una línea coloreada en la terminal con timestamp."""
        now = datetime.now().strftime("%H:%M:%S")
        html = (
            f"<div style='margin-bottom: 4px; font-family: monospace;'>"
            f"<span style='color: #6b7280; font-weight: 500;'>[{now}]</span> "
            f"<span style='color: {tag_color}; font-weight: 800;'>{prefix} [{tag}]</span> "
            f"<span style='color: {text_color};'>{message}</span>"
            f"</div>"
        )
        self.append(html)
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())

    def log_success(self, tag: str, message: str):
        self.log(tag, message, tag_color="#34d399", text_color="#a7f3d0", prefix="✔")

    def log_info(self, tag: str, message: str):
        self.log(tag, message, tag_color="#38bdf8", text_color="#e0e7ff", prefix="ℹ")

    def log_git(self, tag: str, message: str):
        self.log(tag, message, tag_color="#c084fc", text_color="#f3e8ff", prefix="🌿")

    def log_env(self, tag: str, message: str):
        self.log(tag, message, tag_color="#fbbf24", text_color="#fef3c7", prefix="⚡")

    def log_warn(self, tag: str, message: str):
        self.log(tag, message, tag_color="#f59e0b", text_color="#fed7aa", prefix="⚠")

    def log_error(self, tag: str, message: str):
        self.log(tag, message, tag_color="#f87171", text_color="#fecaca", prefix="✖")


class LumenProjectWorkspaceView(QWidget):
    """Vista modular de control de desarrollo y HUD con navegación directa y funciones reales Git e IA."""
    
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.app_version = get_version()
        self.project_data = {}
        self.push_thread = None
        self.audit_thread = None
        self.commit_thread = None
        self.selected_impact = "GAMMA"
        self.selected_target_ver = "v0.1.0"
        self.selected_model_type = "light"
        self.current_commit_proposal = {}
        self.cur_semver_options = {}
        self.init_ui()

        # Temporizador para la hora en vivo
        self.clock_timer = QTimer(self)
        self.clock_timer.setInterval(1000)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start()

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(14)

        # -------------------------------------------------------------
        # 1. COMMAND BAR SUPERIOR (NAVEGACIÓN & IDENTIFICADOR)
        # -------------------------------------------------------------
        top_bar = QFrame()
        top_bar.setStyleSheet("""
            QFrame {
                background-color: rgba(17, 19, 26, 0.85);
                border: 1px solid rgba(99, 102, 241, 0.25);
                border-radius: 10px;
                padding: 4px 8px;
            }
        """)
        tb_layout = QHBoxLayout(top_bar)
        tb_layout.setContentsMargins(10, 8, 12, 8)
        tb_layout.setSpacing(14)

        self.btn_back = QPushButton("◀  Volver al Selector")
        self.btn_back.setProperty("class", "browse")
        self.btn_back.setCursor(Qt.PointingHandCursor)
        self.btn_back.setStyleSheet("""
            QPushButton {
                background-color: rgba(99, 102, 241, 0.18);
                color: #c7d2fe;
                border: 1px solid rgba(99, 102, 241, 0.40);
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 700;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(99, 102, 241, 0.35);
                border-color: #818cf8;
                color: #ffffff;
            }
        """)
        self.btn_back.clicked.connect(self.back_requested.emit)
        tb_layout.addWidget(self.btn_back)

        # Separador vertical
        sep_top = QFrame()
        sep_top.setFrameShape(QFrame.VLine)
        sep_top.setStyleSheet("background-color: rgba(255, 255, 255, 0.10); max-width: 1px;")
        tb_layout.addWidget(sep_top)

        self.lbl_app_info = QLabel(f"❖  ABRAXAS  [v{self.app_version}]  •  CONTROLADOR LUMEN")
        self.lbl_app_info.setStyleSheet("font-size: 13.5px; font-weight: 800; color: #a5b4fc; letter-spacing: 0.5px;")
        tb_layout.addWidget(self.lbl_app_info)

        tb_layout.addStretch()

        # Botón de refresco manual
        self.btn_refresh = QPushButton("🔄 Sincronizar")
        self.btn_refresh.setProperty("class", "browse")
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.04);
                color: #9ca3af;
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11.5px;
                font-weight: 600;
            }
            QPushButton:hover {
                color: #ffffff;
                border-color: #6366f1;
            }
        """)
        self.btn_refresh.clicked.connect(self.refresh_current_project)
        tb_layout.addWidget(self.btn_refresh)

        # Status Pill
        self.lbl_status_pill = QLabel("🟢 SISTEMA CONECTADO")
        self.lbl_status_pill.setStyleSheet("""
            background-color: rgba(16, 185, 129, 0.12);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.35);
            border-radius: 12px;
            padding: 4px 12px;
            font-size: 11px;
            font-weight: 800;
        """)
        tb_layout.addWidget(self.lbl_status_pill)

        root_layout.addWidget(top_bar)

        # Área de Scroll General
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        scroll_content = QWidget()
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setContentsMargins(0, 0, 6, 0)
        content_layout.setSpacing(14)

        # -------------------------------------------------------------
        # 2. HUD GENERAL DEL PROYECTO (CONSERVADO EN LA PARTE SUPERIOR)
        # -------------------------------------------------------------
        self.hud_card = QFrame()
        self.hud_card.setProperty("class", "surface")
        self.hud_card.setStyleSheet("""
            QFrame.surface {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(19, 21, 29, 0.95), stop:1 rgba(15, 17, 23, 0.95));
                border: 1px solid rgba(99, 102, 241, 0.30);
                border-left: 5px solid #818cf8;
                border-radius: 12px;
            }
        """)
        hud_layout = QVBoxLayout(self.hud_card)
        hud_layout.setContentsMargins(20, 16, 20, 16)
        hud_layout.setSpacing(10)

        # Línea 1: Proyecto | Rama | Remoto
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        lbl_p_tag = QLabel("📁 Proyecto:")
        lbl_p_tag.setStyleSheet("font-weight: 700; color: #9ca3af; font-size: 13.5px;")
        self.lbl_proj_title = QLabel("Cargando...")
        self.lbl_proj_title.setStyleSheet("font-weight: 800; color: #fbbf24; font-size: 14px;")

        sep1 = QLabel(" | ")
        sep1.setStyleSheet("color: #4b5563; font-weight: 700;")

        lbl_b_tag = QLabel("🌿 Rama:")
        lbl_b_tag.setStyleSheet("font-weight: 700; color: #9ca3af; font-size: 13.5px;")
        self.lbl_proj_branch = QLabel("main")
        self.lbl_proj_branch.setStyleSheet("font-weight: 800; color: #38bdf8; font-size: 13.5px;")

        sep2 = QLabel(" | ")
        sep2.setStyleSheet("color: #4b5563; font-weight: 700;")

        lbl_r_tag = QLabel("🌐 Remoto:")
        lbl_r_tag.setStyleSheet("font-weight: 700; color: #9ca3af; font-size: 13.5px;")
        self.lbl_proj_remote = QLabel("origin/main")
        self.lbl_proj_remote.setStyleSheet("font-weight: 700; color: #c7d2fe; font-size: 13.5px;")

        row1.addWidget(lbl_p_tag)
        row1.addWidget(self.lbl_proj_title)
        row1.addWidget(sep1)
        row1.addWidget(lbl_b_tag)
        row1.addWidget(self.lbl_proj_branch)
        row1.addWidget(sep2)
        row1.addWidget(lbl_r_tag)
        row1.addWidget(self.lbl_proj_remote)
        row1.addStretch()
        hud_layout.addLayout(row1)

        # Línea 2: Entorno | Docker | Hora
        row2 = QHBoxLayout()
        row2.setSpacing(8)

        lbl_e_tag = QLabel("⚡ Entorno:")
        lbl_e_tag.setStyleSheet("font-weight: 700; color: #9ca3af; font-size: 13px;")
        self.lbl_env_status = QLabel("Detectando...")
        self.lbl_env_status.setStyleSheet("font-weight: 800; color: #34d399; font-size: 13px;")

        sep3 = QLabel(" | ")
        sep3.setStyleSheet("color: #4b5563; font-weight: 700;")

        lbl_d_tag = QLabel("🐳 Contenedores Docker:")
        lbl_d_tag.setStyleSheet("font-weight: 700; color: #9ca3af; font-size: 13px;")
        self.lbl_docker_status = QLabel("0 activos")
        self.lbl_docker_status.setStyleSheet("font-weight: 800; color: #60a5fa; font-size: 13px;")

        sep4 = QLabel(" | ")
        sep4.setStyleSheet("color: #4b5563; font-weight: 700;")

        lbl_h_tag = QLabel("🕒 Hora:")
        lbl_h_tag.setStyleSheet("font-weight: 700; color: #9ca3af; font-size: 13px;")
        self.lbl_current_time = QLabel("--:--:--")
        self.lbl_current_time.setStyleSheet("font-family: monospace; font-weight: 700; color: #e5e7eb; font-size: 13px;")

        row2.addWidget(lbl_e_tag)
        row2.addWidget(self.lbl_env_status)
        row2.addWidget(sep3)
        row2.addWidget(lbl_d_tag)
        row2.addWidget(self.lbl_docker_status)
        row2.addWidget(sep4)
        row2.addWidget(lbl_h_tag)
        row2.addWidget(self.lbl_current_time)
        row2.addStretch()
        hud_layout.addLayout(row2)

        # Línea 3: Git HUD: | Git Mod | Untracked | Deleted
        row3 = QHBoxLayout()
        row3.setSpacing(8)

        lbl_hud_title = QLabel("📊 Git HUD:")
        lbl_hud_title.setStyleSheet("font-weight: 800; color: #c084fc; font-size: 13px;")

        sep5 = QLabel(" | ")
        sep5.setStyleSheet("color: #4b5563; font-weight: 700;")

        lbl_m_tag = QLabel("📝 Git Mod:")
        lbl_m_tag.setStyleSheet("font-weight: 700; color: #9ca3af; font-size: 13px;")
        self.lbl_git_mod = QLabel("0 modificados")
        self.lbl_git_mod.setStyleSheet("font-weight: 700; color: #fbbf24; font-size: 13px;")

        sep6 = QLabel(" | ")
        sep6.setStyleSheet("color: #4b5563; font-weight: 700;")

        lbl_u_tag = QLabel("❓ Untracked:")
        lbl_u_tag.setStyleSheet("font-weight: 700; color: #9ca3af; font-size: 13px;")
        self.lbl_git_untracked = QLabel("0 no rastreados")
        self.lbl_git_untracked.setStyleSheet("font-weight: 700; color: #38bdf8; font-size: 13px;")

        sep7 = QLabel(" | ")
        sep7.setStyleSheet("color: #4b5563; font-weight: 700;")

        lbl_del_tag = QLabel("🗑️ Deleted:")
        lbl_del_tag.setStyleSheet("font-weight: 700; color: #9ca3af; font-size: 13px;")
        self.lbl_git_deleted = QLabel("0")
        self.lbl_git_deleted.setStyleSheet("font-weight: 700; color: #9ca3af; font-size: 13px;")

        row3.addWidget(lbl_hud_title)
        row3.addWidget(sep5)
        row3.addWidget(lbl_m_tag)
        row3.addWidget(self.lbl_git_mod)
        row3.addWidget(sep6)
        row3.addWidget(lbl_u_tag)
        row3.addWidget(self.lbl_git_untracked)
        row3.addWidget(sep7)
        row3.addWidget(lbl_del_tag)
        row3.addWidget(self.lbl_git_deleted)
        row3.addStretch()
        hud_layout.addLayout(row3)

        # Separador sutil
        sep_hud = QFrame()
        sep_hud.setFrameShape(QFrame.HLine)
        sep_hud.setStyleSheet("background-color: rgba(255, 255, 255, 0.08); max-height: 1px;")
        hud_layout.addWidget(sep_hud)

        # Línea 4: Historial reciente
        lbl_hist_head = QLabel("📜 Historial reciente (Últimos 4 commits):")
        lbl_hist_head.setStyleSheet("font-size: 13px; font-weight: 800; color: #e5e7eb;")
        hud_layout.addWidget(lbl_hist_head)

        # Contenedor dinámico de commits
        self.history_items_container = QWidget()
        self.history_items_layout = QVBoxLayout(self.history_items_container)
        self.history_items_layout.setContentsMargins(0, 0, 0, 0)
        self.history_items_layout.setSpacing(6)
        hud_layout.addWidget(self.history_items_container)

        content_layout.addWidget(self.hud_card)

        # -------------------------------------------------------------
        # 3. ZONA MODULAR DE SECTORES (QStackedWidget)
        # -------------------------------------------------------------
        self.sectors_stack = QStackedWidget()

        # =============================================================
        # PÁGINA 0: VISTA GENERAL DE LOS 4 SECTORES
        # =============================================================
        self.page_overview = QWidget()
        overview_layout = QGridLayout(self.page_overview)
        overview_layout.setContentsMargins(0, 0, 0, 0)
        overview_layout.setSpacing(14)

        # Sector 1 Card
        card_s1 = self.create_overview_sector_card(
            title="🔄  PRIMER SECTOR : CICLOS DE TRABAJO",
            accent_color="#38bdf8",
            sector_idx=1,
            actions=[
                ("🔄", "Ciclos de Trabajo", "ADD / IA Commit / IA Audit / Push"),
                ("🌿", "Control de Ramas", "Checkout / Crear / Borrar"),
                ("🔀", "Fusión de Ramas", "git merge"),
                ("⚡", "Estado y Sincronización", "Status / Fetch / Pull")
            ]
        )
        overview_layout.addWidget(card_s1, 0, 0)

        # Sector 2 Card
        card_s2 = self.create_overview_sector_card(
            title="🚀  SEGUNDO SECTOR : ENTORNOS Y EJECUCIÓN",
            accent_color="#10b981",
            sector_idx=2,
            actions=[
                ("💻", "Ejecutar proyecto en editor", "Lanzar espacio de trabajo en VS Code / IDE"),
                ("🐍", "Entornos python", "Gestor de paquetes, dependencias y virtualenv"),
                ("🐳", "Docker y puertos", "Control de contenedores, compose y mapeos")
            ]
        )
        overview_layout.addWidget(card_s2, 0, 1)

        # Sector 3 Card
        card_s3 = self.create_overview_sector_card(
            title="🧠  TERCER SECTOR : HERRAMIENTAS & IA",
            accent_color="#c084fc",
            sector_idx=3,
            actions=[
                ("🛡️", "Gestor de gitignore", "Plantillas inteligentes y reglas de exclusión"),
                ("📖", "Lector de documentación", "Visor interactivo de Markdown, README y APIs"),
                ("🤖", "Utilidades IA", "Asistente Ollama local, refactor y ayuda dev")
            ]
        )
        overview_layout.addWidget(card_s3, 1, 0)

        # Sector 4 Card
        card_s4 = self.create_overview_sector_card(
            title="👤  SECTOR CUATRO : USUARIO GIT",
            accent_color="#fbbf24",
            sector_idx=4,
            actions=[
                ("🏷️", "Usuario Git", "Nombre, correo y firma de autor para commits")
            ]
        )
        overview_layout.addWidget(card_s4, 1, 1)

        self.sectors_stack.addWidget(self.page_overview)

        # =============================================================
        # PÁGINA 1: VENTANA DEDICADA DEL SECTOR 1 (CICLOS DE TRABAJO & IA AUDIT)
        # =============================================================
        self.page_sector1_view = self.create_sector1_dedicated_view()
        self.sectors_stack.addWidget(self.page_sector1_view)

        # =============================================================
        # PÁGINA 2: VENTANA DEDICADA DEL SECTOR 2 (ENTORNOS Y EJECUCIÓN)
        # =============================================================
        self.page_sector2_view = self.create_simple_sector_view(
            title="🚀  SEGUNDO SECTOR : ENTORNOS Y EJECUCIÓN",
            accent_color="#10b981",
            actions=[
                ("💻", "Ejecutar proyecto en editor", "Lanzar espacio de trabajo en VS Code / IDE"),
                ("🐍", "Entornos python", "Gestor de paquetes, dependencias y virtualenv"),
                ("🐳", "Docker y puertos", "Control de contenedores, compose y mapeos")
            ]
        )
        self.sectors_stack.addWidget(self.page_sector2_view)

        # =============================================================
        # PÁGINA 3: VENTANA DEDICADA DEL SECTOR 3 (HERRAMIENTAS & IA)
        # =============================================================
        self.page_sector3_view = self.create_simple_sector_view(
            title="🧠  TERCER SECTOR : HERRAMIENTAS & IA",
            accent_color="#c084fc",
            actions=[
                ("🛡️", "Gestor de gitignore", "Plantillas inteligentes y reglas de exclusión"),
                ("📖", "Lector de documentación", "Visor interactivo de Markdown, README y APIs"),
                ("🤖", "Utilidades IA", "Asistente Ollama local, refactor y ayuda dev")
            ]
        )
        self.sectors_stack.addWidget(self.page_sector3_view)

        # =============================================================
        # PÁGINA 4: VENTANA DEDICADA DEL SECTOR 4 (USUARIO GIT)
        # =============================================================
        self.page_sector4_view = self.create_simple_sector_view(
            title="👤  SECTOR CUATRO : USUARIO GIT",
            accent_color="#fbbf24",
            actions=[
                ("🏷️", "Usuario Git", "Nombre, correo y firma de autor para commits")
            ]
        )
        self.sectors_stack.addWidget(self.page_sector4_view)

        content_layout.addWidget(self.sectors_stack)

        # -------------------------------------------------------------
        # 4. RECUADRO INFERIOR (TERMINAL DE SALIDA DE SOLO LECTURA)
        # -------------------------------------------------------------
        self.terminal_frame = QFrame()
        self.terminal_frame.setProperty("class", "surface")
        self.terminal_frame.setStyleSheet("""
            QFrame.surface {
                background-color: #07090e;
                border: 1px solid rgba(99, 102, 241, 0.25);
                border-radius: 10px;
            }
        """)
        b_layout = QVBoxLayout(self.terminal_frame)
        b_layout.setContentsMargins(0, 0, 0, 0)
        b_layout.setSpacing(0)

        # Barra de título de la terminal
        term_bar = QFrame()
        term_bar.setStyleSheet("""
            background-color: rgba(255, 255, 255, 0.03);
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            border-top-left-radius: 10px;
            border-top-right-radius: 10px;
            padding: 4px 10px;
        """)
        t_bar_layout = QHBoxLayout(term_bar)
        t_bar_layout.setContentsMargins(12, 7, 12, 7)
        t_bar_layout.setSpacing(10)

        # Dots de ventana Unix
        lbl_dots = QLabel("🔴  🟡  🟢")
        lbl_dots.setStyleSheet("font-size: 9px;")
        t_bar_layout.addWidget(lbl_dots)

        self.lbl_t_title = QLabel("lumen-terminal@abraxas:~$")
        self.lbl_t_title.setStyleSheet("font-family: monospace; font-size: 12px; font-weight: 700; color: #a5b4fc;")
        t_bar_layout.addWidget(self.lbl_t_title)

        t_bar_layout.addStretch()

        # Botón Copiar Log
        btn_copy = QPushButton("📋 Copiar")
        btn_copy.setCursor(Qt.PointingHandCursor)
        btn_copy.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.04);
                color: #9ca3af;
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 4px;
                padding: 3px 9px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                color: #ffffff;
                border-color: #6366f1;
                background-color: rgba(99, 102, 241, 0.20);
            }
        """)
        btn_copy.clicked.connect(self.copy_terminal_output)
        t_bar_layout.addWidget(btn_copy)

        # Botón Limpiar Visor
        btn_clear = QPushButton("🧹 Limpiar")
        btn_clear.setCursor(Qt.PointingHandCursor)
        btn_clear.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.04);
                color: #9ca3af;
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 4px;
                padding: 3px 9px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                color: #f87171;
                border-color: #ef4444;
                background-color: rgba(239, 68, 68, 0.15);
            }
        """)
        btn_clear.clicked.connect(self.clear_terminal_output)
        t_bar_layout.addWidget(btn_clear)

        lbl_t_status = QLabel("⚡ VISOR DE SALIDA [READ-ONLY]")
        lbl_t_status.setStyleSheet("font-size: 10px; font-weight: 800; color: #38bdf8; background-color: rgba(6, 182, 212, 0.12); border: 1px solid rgba(6, 182, 212, 0.35); border-radius: 4px; padding: 2px 8px; letter-spacing: 0.5px;")
        t_bar_layout.addWidget(lbl_t_status)

        b_layout.addWidget(term_bar)

        # Visor de texto (QTextEdit de Solo Lectura con soporte HTML coloreado)
        self.terminal_display = LumenTerminalDisplay()
        b_layout.addWidget(self.terminal_display)

        content_layout.addWidget(self.terminal_frame)

        scroll_area.setWidget(scroll_content)
        root_layout.addWidget(scroll_area, 1)

    # -----------------------------------------------------------------
    # CREACIÓN DE VISTAS DE SECTORES (DISEÑO PRECISO & COMPACTO)
    # -----------------------------------------------------------------
    def create_overview_sector_card(self, title: str, accent_color: str, sector_idx: int, actions: list) -> QFrame:
        """Crea una tarjeta para la vista general que permite entrar a la ventana limpia del sector."""
        card = QFrame()
        card.setProperty("class", "surface")
        card.setStyleSheet(f"""
            QFrame.surface {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(22, 24, 34, 0.95), stop:1 rgba(16, 18, 25, 0.95));
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-top: 3px solid {accent_color};
                border-radius: 10px;
            }}
        """)
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(16, 14, 16, 14)
        c_layout.setSpacing(10)

        # Header del Sector con botón de abrir
        h_layout = QHBoxLayout()
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(f"font-size: 12.5px; font-weight: 900; color: {accent_color}; letter-spacing: 0.5px;")
        h_layout.addWidget(lbl_title)
        h_layout.addStretch()

        btn_enter = QPushButton("Abrir Sector ›")
        btn_enter.setCursor(Qt.PointingHandCursor)
        btn_enter.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.04);
                color: {accent_color};
                border: 1px solid {accent_color};
                border-radius: 5px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {accent_color};
                color: #07090e;
            }}
        """)
        btn_enter.clicked.connect(lambda: self.open_sector_view(sector_idx, title))
        h_layout.addWidget(btn_enter)
        c_layout.addLayout(h_layout)

        for icon, act_title, act_sub in actions:
            btn = LumenCyberActionButton(icon, act_title, act_sub, accent_color=accent_color)
            btn.clicked.connect(lambda t=act_title, s=sector_idx, st=title: self.open_sector_and_handle(s, st, t))
            c_layout.addWidget(btn)

        c_layout.addStretch()
        return card

    def create_sector1_dedicated_view(self) -> QFrame:
        """Crea la ventana del Sector 1 con sub-páginas (0: Flujo Ciclos de Trabajo, 1: Selección IA AUDIT)."""
        card = QFrame()
        card.setProperty("class", "surface")
        card.setStyleSheet("""
            QFrame.surface {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(22, 24, 34, 0.95), stop:1 rgba(16, 18, 25, 0.95));
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-top: 3px solid #38bdf8;
                border-radius: 10px;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # Sub-stack interno para alternar entre Flujo y Vista IA AUDIT
        self.sector1_sub_stack = QStackedWidget()

        # =============================================================
        # SUB-PÁGINA 0: FLUJO PRINCIPAL DE CICLOS DE TRABAJO
        # =============================================================
        page_work = QWidget()
        w_lay = QVBoxLayout(page_work)
        w_lay.setContentsMargins(0, 0, 0, 0)
        w_lay.setSpacing(10)

        head_w = QHBoxLayout()
        head_w.setSpacing(12)

        btn_back_to_main = QPushButton("◀  Volver al Menú de Sectores")
        btn_back_to_main.setCursor(Qt.PointingHandCursor)
        btn_back_to_main.setStyleSheet("""
            QPushButton {
                background-color: rgba(56, 189, 248, 0.15);
                color: #bae6fd;
                border: 1px solid rgba(56, 189, 248, 0.40);
                border-radius: 6px;
                padding: 5px 12px;
                font-weight: 700;
                font-size: 11.5px;
            }
            QPushButton:hover {
                background-color: rgba(56, 189, 248, 0.30);
                border-color: #38bdf8;
                color: #ffffff;
            }
        """)
        btn_back_to_main.clicked.connect(self.go_back_to_sectors_overview)
        head_w.addWidget(btn_back_to_main)

        lbl_w_title = QLabel("🔄  PRIMER SECTOR : FLUJO DE CICLOS DE TRABAJO")
        lbl_w_title.setStyleSheet("font-size: 12.5px; font-weight: 900; color: #38bdf8; letter-spacing: 0.5px;")
        head_w.addWidget(lbl_w_title)
        head_w.addStretch()

        lbl_flow_pill = QLabel("[ADD ➔ IA AUDIT ➔ IA COMMIT ➔ PUSH]")
        lbl_flow_pill.setFixedHeight(24)
        lbl_flow_pill.setAlignment(Qt.AlignCenter)
        lbl_flow_pill.setStyleSheet("font-size: 10px; font-weight: 800; color: #818cf8; background-color: rgba(99, 102, 241, 0.15); border: 1px solid rgba(99, 102, 241, 0.35); border-radius: 4px; padding: 2px 8px;")
        head_w.addWidget(lbl_flow_pill)
        w_lay.addLayout(head_w)

        # Botón 1: ADD (Preparar Cambios)
        btn_add = LumenCyberActionButton("➕", "Add (Preparar Cambios)", "git add -A / Staging completo de archivos modificados y nuevos", accent_color="#34d399")
        btn_add.clicked.connect(self.run_git_add)
        w_lay.addWidget(btn_add)

        # Botón 2: IA AUDIT (Analizar Diff)
        btn_ia_audit = LumenCyberActionButton("🔍", "IA Audit (Analizar Diff)", "Auditoría inteligente del árbol de cambios y diff con IA (Ligero / Pesado)", accent_color="#38bdf8")
        btn_ia_audit.clicked.connect(self.open_ia_audit_subview)
        w_lay.addWidget(btn_ia_audit)

        # Botón 3: IA Commit (Generar commit)
        btn_ia_commit = LumenCyberActionButton("🤖", "IA Commit (Generar commit)", "Generación semántica de mensaje de commit estructurado con SemVer", accent_color="#c084fc")
        btn_ia_commit.clicked.connect(self.start_ia_commit_workflow)
        w_lay.addWidget(btn_ia_commit)

        # Botón 4: Commit Manual
        btn_commit_man = LumenCyberActionButton("✍️", "Commit Manual", "Redactar mensaje personalizado y registrar commit en el repositorio", accent_color="#fbbf24")
        btn_commit_man.clicked.connect(lambda: self.handle_action_click("Commit Manual"))
        w_lay.addWidget(btn_commit_man)

        # Botón 5: Push
        btn_push = LumenCyberActionButton("🚀", "Push", "Publicar commits locales confirmados a la rama remota origin", accent_color="#60a5fa")
        btn_push.clicked.connect(self.run_git_push)
        w_lay.addWidget(btn_push)

        # Botón 6: Volver
        btn_volver = LumenCyberActionButton("◀", "Volver", "Regresar al menú principal de Sectores", accent_color="#9ca3af")
        btn_volver.clicked.connect(self.go_back_to_sectors_overview)
        w_lay.addWidget(btn_volver)

        w_lay.addStretch()
        self.sector1_sub_stack.addWidget(page_work)

        # =============================================================
        # SUB-PÁGINA 1: SELECCIÓN DE MODELO PARA IA AUDIT
        # =============================================================
        page_ia_audit = QWidget()
        ia_lay = QVBoxLayout(page_ia_audit)
        ia_lay.setContentsMargins(0, 0, 0, 0)
        ia_lay.setSpacing(10)

        head_ia = QHBoxLayout()
        head_ia.setSpacing(12)

        btn_back_to_work = QPushButton("◀  Volver a Ciclos de Trabajo")
        btn_back_to_work.setCursor(Qt.PointingHandCursor)
        btn_back_to_work.setStyleSheet("""
            QPushButton {
                background-color: rgba(56, 189, 248, 0.15);
                color: #bae6fd;
                border: 1px solid rgba(56, 189, 248, 0.40);
                border-radius: 6px;
                padding: 5px 12px;
                font-weight: 700;
                font-size: 11.5px;
            }
            QPushButton:hover {
                background-color: rgba(56, 189, 248, 0.30);
                border-color: #38bdf8;
                color: #ffffff;
            }
        """)
        btn_back_to_work.clicked.connect(self.go_back_to_work_cycles)
        head_ia.addWidget(btn_back_to_work)

        lbl_ia_title = QLabel("🔍  AUDITORÍA DE DIFF CON INTELIGENCIA ARTIFICIAL")
        lbl_ia_title.setStyleSheet("font-size: 12.5px; font-weight: 900; color: #38bdf8; letter-spacing: 0.5px;")
        head_ia.addWidget(lbl_ia_title)
        head_ia.addStretch()

        lbl_engine_pill = QLabel("[OLLAMA ENGINE]")
        lbl_engine_pill.setFixedHeight(24)
        lbl_engine_pill.setAlignment(Qt.AlignCenter)
        lbl_engine_pill.setStyleSheet("font-size: 10px; font-weight: 800; color: #34d399; background-color: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.35); border-radius: 4px; padding: 2px 8px;")
        head_ia.addWidget(lbl_engine_pill)
        ia_lay.addLayout(head_ia)

        # Opción 1: Diff IA (Modelo Ligero)
        light_name = get_configured_model("light")
        self.btn_diff_light = LumenCyberActionButton(
            "⚡", 
            "Diff IA (Modelo Ligero)", 
            f"Auditoría ágil y rápida del diff • Modelo configurado: {light_name}", 
            accent_color="#38bdf8"
        )
        self.btn_diff_light.clicked.connect(lambda: self.run_ai_diff_audit("light"))
        ia_lay.addWidget(self.btn_diff_light)

        # Opción 2: Diff IA (Modelo Pesado)
        heavy_name = get_configured_model("heavy")
        self.btn_diff_heavy = LumenCyberActionButton(
            "🧠", 
            "Diff IA (Modelo Pesado)", 
            f"Auditoría exhaustiva y análisis profundo • Modelo configurado: {heavy_name}", 
            accent_color="#c084fc"
        )
        self.btn_diff_heavy.clicked.connect(lambda: self.run_ai_diff_audit("heavy"))
        ia_lay.addWidget(self.btn_diff_heavy)

        # Botón Volver
        btn_back_audit = LumenCyberActionButton(
            "◀", 
            "Volver", 
            "Regresar a las opciones del Ciclo de Trabajo", 
            accent_color="#9ca3af"
        )
        btn_back_audit.clicked.connect(self.go_back_to_work_cycles)
        ia_lay.addWidget(btn_back_audit)

        ia_lay.addStretch()
        self.sector1_sub_stack.addWidget(page_ia_audit)

        # =============================================================
        # SUB-PÁGINA 2: CONTROL DE VERSIONES (SemVer - Protocolo Artemis)
        # =============================================================
        page_semver = QWidget()
        semver_lay = QVBoxLayout(page_semver)
        semver_lay.setContentsMargins(0, 0, 0, 0)
        semver_lay.setSpacing(10)

        head_semver = QHBoxLayout()
        head_semver.setSpacing(12)

        btn_back_semver = QPushButton("◀  Volver a Ciclos de Trabajo")
        btn_back_semver.setCursor(Qt.PointingHandCursor)
        btn_back_semver.setStyleSheet("""
            QPushButton {
                background-color: rgba(99, 102, 241, 0.15);
                color: #c7d2fe;
                border: 1px solid rgba(99, 102, 241, 0.40);
                border-radius: 6px;
                padding: 5px 12px;
                font-weight: 700;
                font-size: 11.5px;
            }
            QPushButton:hover {
                background-color: rgba(99, 102, 241, 0.30);
                border-color: #818cf8;
                color: #ffffff;
            }
        """)
        btn_back_semver.clicked.connect(self.go_back_to_work_cycles)
        head_semver.addWidget(btn_back_semver)

        self.lbl_semver_title = QLabel("❖ CONTROL DE VERSIONES (SemVer: v0.1.0) ❖")
        self.lbl_semver_title.setStyleSheet("font-size: 12.5px; font-weight: 900; color: #fbbf24; letter-spacing: 0.5px;")
        head_semver.addWidget(self.lbl_semver_title)
        head_semver.addStretch()

        lbl_step1_pill = QLabel("[PASO 1 / 3: CLASIFICACIÓN]")
        lbl_step1_pill.setFixedHeight(24)
        lbl_step1_pill.setAlignment(Qt.AlignCenter)
        lbl_step1_pill.setStyleSheet("font-size: 10px; font-weight: 800; color: #fbbf24; background-color: rgba(251, 191, 36, 0.12); border: 1px solid rgba(251, 191, 36, 0.35); border-radius: 4px; padding: 2px 8px;")
        head_semver.addWidget(lbl_step1_pill)
        semver_lay.addLayout(head_semver)

        lbl_semver_desc = QLabel("Selecciona el nivel de impacto de los cambios a registrar según los estándares SemVer:")
        lbl_semver_desc.setStyleSheet("font-size: 11.5px; color: #9ca3af; margin-bottom: 2px;")
        semver_lay.addWidget(lbl_semver_desc)

        # 1. GAMMA (Patch)
        self.btn_gamma = LumenCyberActionButton(
            "🟢", "1. GAMMA (Patch) ➔ v0.1.1", 
            "Fix, ajuste menor, corrección puntual o documentación", 
            accent_color="#34d399"
        )
        self.btn_gamma.clicked.connect(lambda: self.select_semver_impact("GAMMA"))
        semver_lay.addWidget(self.btn_gamma)

        # 2. BETA (Minor)
        self.btn_beta = LumenCyberActionButton(
            "🟡", "2. BETA (Minor) ➔ v0.2.0", 
            "Nuevo módulo, funcionalidad o capacidad agregada", 
            accent_color="#fbbf24"
        )
        self.btn_beta.clicked.connect(lambda: self.select_semver_impact("BETA"))
        semver_lay.addWidget(self.btn_beta)

        # 3. ALPHA (Major)
        self.btn_alpha = LumenCyberActionButton(
            "🔴", "3. ALPHA (Major) ➔ v1.0.0", 
            "Reestructuración masiva, cambio mayor o de arquitectura", 
            accent_color="#f87171"
        )
        self.btn_alpha.clicked.connect(lambda: self.select_semver_impact("ALPHA"))
        semver_lay.addWidget(self.btn_alpha)

        # 4. Omitir bump
        self.btn_omit = LumenCyberActionButton(
            "⚪", "4. Omitir bump ➔ v0.1.0", 
            "Mantener versión actual sin incrementar etiqueta SemVer", 
            accent_color="#9ca3af"
        )
        self.btn_omit.clicked.connect(lambda: self.select_semver_impact("OMIT"))
        semver_lay.addWidget(self.btn_omit)

        # 5. Cancelar Commit
        btn_cancel_sem = LumenCyberActionButton(
            "◀", "Cancelar Commit", 
            "Regresar al menú de Ciclos de Trabajo", 
            accent_color="#6b7280"
        )
        btn_cancel_sem.clicked.connect(self.go_back_to_work_cycles)
        semver_lay.addWidget(btn_cancel_sem)

        semver_lay.addStretch()
        self.sector1_sub_stack.addWidget(page_semver)

        # =============================================================
        # SUB-PÁGINA 3: MOTOR IA PARA PROCESAMIENTO (Protocolo Artemis)
        # =============================================================
        page_ia_model = QWidget()
        ia_mod_lay = QVBoxLayout(page_ia_model)
        ia_mod_lay.setContentsMargins(0, 0, 0, 0)
        ia_mod_lay.setSpacing(10)

        head_mod = QHBoxLayout()
        head_mod.setSpacing(12)

        btn_back_to_sem = QPushButton("◀  Volver a Selección de Versión")
        btn_back_to_sem.setCursor(Qt.PointingHandCursor)
        btn_back_to_sem.setStyleSheet("""
            QPushButton {
                background-color: rgba(99, 102, 241, 0.15);
                color: #c7d2fe;
                border: 1px solid rgba(99, 102, 241, 0.40);
                border-radius: 6px;
                padding: 5px 12px;
                font-weight: 700;
                font-size: 11.5px;
            }
            QPushButton:hover {
                background-color: rgba(99, 102, 241, 0.30);
                border-color: #818cf8;
                color: #ffffff;
            }
        """)
        btn_back_to_sem.clicked.connect(lambda: self.sector1_sub_stack.setCurrentIndex(2))
        head_mod.addWidget(btn_back_to_sem)

        lbl_mod_title = QLabel("❖ MOTOR IA PARA PROCESAMIENTO ❖")
        lbl_mod_title.setStyleSheet("font-size: 12.5px; font-weight: 900; color: #ec4899; letter-spacing: 0.5px;")
        head_mod.addWidget(lbl_mod_title)
        head_mod.addStretch()

        lbl_step2_pill = QLabel("[PASO 2 / 3: MOTOR IA]")
        lbl_step2_pill.setFixedHeight(24)
        lbl_step2_pill.setAlignment(Qt.AlignCenter)
        lbl_step2_pill.setStyleSheet("font-size: 10px; font-weight: 800; color: #ec4899; background-color: rgba(236, 72, 153, 0.12); border: 1px solid rgba(236, 72, 153, 0.35); border-radius: 4px; padding: 2px 8px;")
        head_mod.addWidget(lbl_step2_pill)
        ia_mod_lay.addLayout(head_mod)

        lbl_mod_desc = QLabel("Selecciona la red neuronal local para sintetizar el commit:")
        lbl_mod_desc.setStyleSheet("font-size: 11.5px; color: #9ca3af; margin-bottom: 2px;")
        ia_mod_lay.addWidget(lbl_mod_desc)

        # 1. HEX (Modelo Ligero - Rápido)
        self.btn_commit_hex = LumenCyberActionButton(
            "🤖", "1. HEX (Qwen 7B - Rápido)", 
            "Generación ágil y concisa de título y cuerpo semántico", 
            accent_color="#38bdf8"
        )
        self.btn_commit_hex.clicked.connect(lambda: self.start_commit_model_generation("light"))
        ia_mod_lay.addWidget(self.btn_commit_hex)

        # 2. HENDRIX (Modelo Pesado - Pesado/Inteligente)
        self.btn_commit_hen = LumenCyberActionButton(
            "🧠", "2. HENDRIX (Qwen 14B - Pesado/Inteligente)", 
            "Análisis exhaustivo del diff y redacción técnica profunda", 
            accent_color="#c084fc"
        )
        self.btn_commit_hen.clicked.connect(lambda: self.start_commit_model_generation("heavy"))
        ia_mod_lay.addWidget(self.btn_commit_hen)

        # 3. Volver
        btn_back_mod = LumenCyberActionButton(
            "◀", "Volver a Selección de Versión", 
            "Regresar para modificar el nivel de impacto SemVer", 
            accent_color="#9ca3af"
        )
        btn_back_mod.clicked.connect(lambda: self.sector1_sub_stack.setCurrentIndex(2))
        ia_mod_lay.addWidget(btn_back_mod)

        ia_mod_lay.addStretch()
        self.sector1_sub_stack.addWidget(page_ia_model)

        # =============================================================
        # SUB-PÁGINA 4: ANIMACIÓN DE CARGA Y SÍNTESIS CON IA
        # =============================================================
        page_loading = QWidget()
        load_lay = QVBoxLayout(page_loading)
        load_lay.setContentsMargins(0, 20, 0, 20)
        load_lay.setSpacing(14)
        load_lay.setAlignment(Qt.AlignCenter)

        card_loader = QFrame()
        card_loader.setProperty("class", "surface")
        card_loader.setStyleSheet("""
            QFrame.surface {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(26, 22, 38, 0.95), stop:1 rgba(15, 12, 25, 0.95));
                border: 1px solid rgba(192, 132, 252, 0.35);
                border-radius: 12px;
                padding: 24px;
            }
        """)
        c_l_lay = QVBoxLayout(card_loader)
        c_l_lay.setSpacing(12)
        c_l_lay.setAlignment(Qt.AlignCenter)

        lbl_pulse_icon = QLabel("⏳")
        lbl_pulse_icon.setAlignment(Qt.AlignCenter)
        lbl_pulse_icon.setStyleSheet("font-size: 32px;")
        c_l_lay.addWidget(lbl_pulse_icon)

        self.lbl_commit_loading_title = QLabel("GENERANDO PROPUESTA DE COMMIT CON IA...")
        self.lbl_commit_loading_title.setAlignment(Qt.AlignCenter)
        self.lbl_commit_loading_title.setStyleSheet("font-size: 14px; font-weight: 900; color: #c084fc; letter-spacing: 0.8px;")
        c_l_lay.addWidget(self.lbl_commit_loading_title)

        self.lbl_commit_loading_sub = QLabel("Analizando git diff, clasificación de impacto y directivas de IA...")
        self.lbl_commit_loading_sub.setAlignment(Qt.AlignCenter)
        self.lbl_commit_loading_sub.setStyleSheet("font-size: 12px; color: #9ca3af;")
        c_l_lay.addWidget(self.lbl_commit_loading_sub)

        # Progress bar indeterminada con estilo Cyber
        self.commit_progress_bar = QProgressBar()
        self.commit_progress_bar.setRange(0, 0)
        self.commit_progress_bar.setFixedHeight(8)
        self.commit_progress_bar.setTextVisible(False)
        self.commit_progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #0b0c13;
                border: 1px solid rgba(192, 132, 252, 0.30);
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6366f1, stop:0.5 #c084fc, stop:1 #38bdf8);
                border-radius: 4px;
            }
        """)
        c_l_lay.addWidget(self.commit_progress_bar)

        load_lay.addWidget(card_loader)
        load_lay.addStretch()
        self.sector1_sub_stack.addWidget(page_loading)

        # =============================================================
        # SUB-PÁGINA 5: CONFIRMAR REGISTRO DE COMMIT (Protocolo Artemis)
        # =============================================================
        page_confirm = QWidget()
        conf_lay = QVBoxLayout(page_confirm)
        conf_lay.setContentsMargins(0, 0, 0, 0)
        conf_lay.setSpacing(10)

        head_conf = QHBoxLayout()
        head_conf.setSpacing(12)

        lbl_conf_head = QLabel("❖ CONFIRMAR REGISTRO DE COMMIT ❖")
        lbl_conf_head.setStyleSheet("font-size: 12.5px; font-weight: 900; color: #34d399; letter-spacing: 0.5px;")
        head_conf.addWidget(lbl_conf_head)
        head_conf.addStretch()

        lbl_step3_pill = QLabel("[PASO 3 / 3: CONFIRMACIÓN]")
        lbl_step3_pill.setFixedHeight(24)
        lbl_step3_pill.setAlignment(Qt.AlignCenter)
        lbl_step3_pill.setStyleSheet("font-size: 10px; font-weight: 800; color: #34d399; background-color: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.35); border-radius: 4px; padding: 2px 8px;")
        head_conf.addWidget(lbl_step3_pill)
        conf_lay.addLayout(head_conf)

        # Tarjeta resumen de la propuesta
        card_prop = QFrame()
        card_prop.setProperty("class", "surface")
        card_prop.setStyleSheet("""
            QFrame.surface {
                background-color: rgba(15, 17, 24, 0.85);
                border: 1px solid rgba(99, 102, 241, 0.30);
                border-left: 4px solid #34d399;
                border-radius: 8px;
                padding: 10px 14px;
            }
        """)
        cp_lay = QVBoxLayout(card_prop)
        cp_lay.setSpacing(6)

        self.lbl_prop_title = QLabel("TÍTULO: HEX:0001 [v0.1.0] | Inicialización")
        self.lbl_prop_title.setStyleSheet("font-family: monospace; font-size: 12.5px; font-weight: 800; color: #fbbf24;")
        cp_lay.addWidget(self.lbl_prop_title)

        self.lbl_prop_impact = QLabel("IMPACTO: GAMMA (Versión: v0.1.0)")
        self.lbl_prop_impact.setStyleSheet("font-family: monospace; font-size: 11.5px; color: #a5b4fc;")
        cp_lay.addWidget(self.lbl_prop_impact)

        self.lbl_prop_body = QLabel("CUERPO: ...")
        self.lbl_prop_body.setWordWrap(True)
        self.lbl_prop_body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lbl_prop_body.setStyleSheet("font-size: 12px; color: #e5e7eb; line-height: 1.4;")
        cp_lay.addWidget(self.lbl_prop_body)

        conf_lay.addWidget(card_prop)

        # Botón Confirmar y Registrar Commit
        self.btn_confirm_commit = LumenCyberActionButton(
            "✅", "1. Confirmar y Registrar Commit", 
            "Escribir commit en Git y crear etiqueta SemVer en el repositorio", 
            accent_color="#34d399"
        )
        self.btn_confirm_commit.clicked.connect(self.confirm_and_record_commit)
        conf_lay.addWidget(self.btn_confirm_commit)

        # Botón Descartar / Volver
        self.btn_discard_commit = LumenCyberActionButton(
            "❌", "2. Descartar / Volver", 
            "Descartar propuesta de commit y regresar al Ciclo de Trabajo", 
            accent_color="#f87171"
        )
        self.btn_discard_commit.clicked.connect(self.discard_commit_proposal)
        conf_lay.addWidget(self.btn_discard_commit)

        conf_lay.addStretch()
        self.sector1_sub_stack.addWidget(page_confirm)

        # =============================================================
        # SUB-PÁGINA 6: POST-COMMIT (OPCIÓN A PUSH O DESCARTAR)
        # =============================================================
        page_post_push = QWidget()
        pp_lay = QVBoxLayout(page_post_push)
        pp_lay.setContentsMargins(0, 0, 0, 0)
        pp_lay.setSpacing(10)

        head_pp = QHBoxLayout()
        head_pp.setSpacing(12)

        lbl_pp_head = QLabel("❖ COMMIT REGISTRADO EXITOSAMENTE ❖")
        lbl_pp_head.setStyleSheet("font-size: 12.5px; font-weight: 900; color: #60a5fa; letter-spacing: 0.5px;")
        head_pp.addWidget(lbl_pp_head)
        head_pp.addStretch()

        lbl_sync_pill = QLabel("[SINCRONIZACIÓN REMOTA]")
        lbl_sync_pill.setFixedHeight(24)
        lbl_sync_pill.setAlignment(Qt.AlignCenter)
        lbl_sync_pill.setStyleSheet("font-size: 10px; font-weight: 800; color: #60a5fa; background-color: rgba(96, 165, 250, 0.12); border: 1px solid rgba(96, 165, 250, 0.35); border-radius: 4px; padding: 2px 8px;")
        head_pp.addWidget(lbl_sync_pill)
        pp_lay.addLayout(head_pp)

        lbl_pp_desc = QLabel("El commit y la etiqueta han sido grabados localmente en Git. ¿Deseas sincronizarlos con GitHub?")
        lbl_pp_desc.setStyleSheet("font-size: 11.5px; color: #9ca3af; margin-bottom: 2px;")
        pp_lay.addWidget(lbl_pp_desc)

        # Botón 1: Push Ahora
        self.btn_post_push = LumenCyberActionButton(
            "🚀", "1. Hacer Push Ahora (Enviar cambios y tags a GitHub)", 
            "Ejecutar git push --follow-tags hacia la rama remota origin", 
            accent_color="#60a5fa"
        )
        self.btn_post_push.clicked.connect(self.execute_post_commit_push)
        pp_lay.addWidget(self.btn_post_push)

        # Botón 2: Descartar / Finalizar
        self.btn_post_skip = LumenCyberActionButton(
            "❌", "2. Descartar / Finalizar (No hacer push)", 
            "Mantener cambios en local y regresar al menú de Ciclos de Trabajo", 
            accent_color="#9ca3af"
        )
        self.btn_post_skip.clicked.connect(self.discard_post_commit_push)
        pp_lay.addWidget(self.btn_post_skip)

        pp_lay.addStretch()
        self.sector1_sub_stack.addWidget(page_post_push)

        layout.addWidget(self.sector1_sub_stack)
        return card

    def create_simple_sector_view(self, title: str, accent_color: str, actions: list) -> QFrame:
        """Crea una ventana dedicada y limpia para un sector específico con diseño consistente."""
        card = QFrame()
        card.setProperty("class", "surface")
        card.setStyleSheet(f"""
            QFrame.surface {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(22, 24, 34, 0.95), stop:1 rgba(16, 18, 25, 0.95));
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-top: 3px solid {accent_color};
                border-radius: 10px;
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # Barra superior de navegación del Sector
        nav_bar = QHBoxLayout()
        nav_bar.setSpacing(12)

        btn_back_sec = QPushButton("◀  Volver al Menú de Sectores")
        btn_back_sec.setCursor(Qt.PointingHandCursor)
        btn_back_sec.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.04);
                color: {accent_color};
                border: 1px solid {accent_color};
                border-radius: 6px;
                padding: 5px 12px;
                font-weight: 700;
                font-size: 11.5px;
            }}
            QPushButton:hover {{
                background-color: {accent_color};
                color: #07090e;
            }}
        """)
        btn_back_sec.clicked.connect(self.go_back_to_sectors_overview)
        nav_bar.addWidget(btn_back_sec)

        lbl_sec_title = QLabel(title)
        lbl_sec_title.setStyleSheet(f"font-size: 12.5px; font-weight: 900; color: {accent_color}; letter-spacing: 0.5px;")
        nav_bar.addWidget(lbl_sec_title)

        nav_bar.addStretch()
        layout.addLayout(nav_bar)

        for icon, act_title, act_sub in actions:
            btn = LumenCyberActionButton(icon, act_title, act_sub, accent_color=accent_color)
            btn.clicked.connect(self.handle_action_click)
            layout.addWidget(btn)

        layout.addStretch()
        return card

    # -----------------------------------------------------------------
    # NAVEGACIÓN DENTRO DE SECTORES Y CICLOS DE TRABAJO
    # -----------------------------------------------------------------
    def open_sector_view(self, sector_idx: int, sector_title: str):
        """Abre la ventana limpia dedicada del sector seleccionado."""
        self.sectors_stack.setCurrentIndex(sector_idx)
        if sector_idx == 1 and hasattr(self, "sector1_sub_stack"):
            self.sector1_sub_stack.setCurrentIndex(0)
        self.terminal_display.log("NAV", f"Abriendo ventana dedicada de <b>{sector_title}</b>.", tag_color="#38bdf8", prefix="📂")

    def open_sector_and_handle(self, sector_idx: int, sector_title: str, action_title: str):
        """Abre la ventana del sector o ejecuta la acción seleccionada."""
        if sector_idx == 1:
            if action_title == "Ciclos de Trabajo":
                self.open_sector_view(1, "Ciclos de Trabajo")
            else:
                self.handle_action_click(action_title)
        else:
            self.open_sector_view(sector_idx, sector_title)
            self.handle_action_click(action_title)

    def open_ia_audit_subview(self):
        """Abre la sub-vista de selección de modelo de IA para Auditoría de Diff."""
        self.sector1_sub_stack.setCurrentIndex(1)
        light_name = get_configured_model("light")
        heavy_name = get_configured_model("heavy")
        self.btn_diff_light.set_subtitle(f"Auditoría ágil y rápida del diff • Modelo configurado: {light_name}")
        self.btn_diff_heavy.set_subtitle(f"Auditoría exhaustiva y análisis profundo • Modelo configurado: {heavy_name}")
        self.terminal_display.log("WORKFLOW", "Accediendo a selección de modelo para <b>IA Audit</b> (Ligero / Pesado)...", tag_color="#38bdf8", prefix="🔍")

    def go_back_to_work_cycles(self):
        """Regresa a la página principal de Ciclos de Trabajo."""
        self.sector1_sub_stack.setCurrentIndex(0)
        self.terminal_display.log("NAV", "Regresando al menú de Ciclos de Trabajo.", tag_color="#9ca3af", prefix="◀")

    def go_back_to_sectors_overview(self):
        """Regresa directamente al menú principal de los 4 sectores en un solo clic."""
        self.sectors_stack.setCurrentIndex(0)
        if hasattr(self, "sector1_sub_stack"):
            self.sector1_sub_stack.setCurrentIndex(0)
        self.terminal_display.log("NAV", "Regresando al menú principal de Sectores.", tag_color="#9ca3af", prefix="◀")

    # -----------------------------------------------------------------
    # ACCIONES REALES: GIT ADD, GIT PUSH E IA AUDIT
    # -----------------------------------------------------------------
    def run_git_add(self):
        """Ejecuta git add -A en el proyecto activo, actualiza el staging y refresca el HUD."""
        path = self.project_data.get("path")
        if not path or not os.path.exists(path):
            self.terminal_display.log_error("GIT-ADD", "No hay un proyecto activo seleccionado.")
            return

        self.terminal_display.log("GIT-ADD", "Ejecutando staging completo de archivos (git add -A)...", tag_color="#34d399", prefix="➕")
        try:
            res = subprocess.run(["git", "add", "-A"], cwd=path, capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                st_proc = subprocess.run(["git", "status", "--short"], cwd=path, capture_output=True, text=True, timeout=5)
                st_lines = st_proc.stdout.strip().splitlines() if st_proc.stdout.strip() else []
                
                self.terminal_display.log_success("GIT-ADD", f"Staging completado con éxito. {len(st_lines)} archivo(s) preparados para commit.")
                for line in st_lines[:6]:
                    self.terminal_display.log("STAGED", line, tag_color="#34d399", prefix="•")
                if len(st_lines) > 6:
                    self.terminal_display.log("STAGED", f"... y {len(st_lines)-6} archivo(s) más.", tag_color="#9ca3af", prefix="•")
                
                # Actualizar el HUD superior inmediatamente
                self.refresh_current_project()
            else:
                self.terminal_display.log_error("GIT-ADD", f"Error al ejecutar git add: {res.stderr.strip()}")
        except Exception as e:
            self.terminal_display.log_error("GIT-ADD", f"Excepción al ejecutar git add: {e}")

    def run_git_push(self, follow_tags: bool = False):
        """Ejecuta git push origin <rama> en segundo plano y proyecta los resultados en la terminal."""
        path = self.project_data.get("path")
        if not path or not os.path.exists(path):
            self.terminal_display.log_error("GIT-PUSH", "No hay un proyecto activo seleccionado.")
            return

        if self.push_thread and self.push_thread.isRunning():
            self.terminal_display.log_warn("GIT-PUSH", "Ya hay una operación de push en curso.")
            return

        tag_str = " (con etiquetas --follow-tags)" if follow_tags else ""
        self.terminal_display.log("GIT-PUSH", f"Iniciando envío de commits{tag_str} hacia el repositorio remoto (origin)...", tag_color="#60a5fa", prefix="🚀")
        
        self.push_thread = GitPushThread(path, follow_tags=follow_tags)
        self.push_thread.finished_push.connect(self.on_push_finished)
        self.push_thread.start()

    def on_push_finished(self, success: bool, branch: str, msg: str):
        """Callback al finalizar git push."""
        if success:
            self.terminal_display.log_success("GIT-PUSH", f"Commits sincronizados exitosamente con origin/{branch}.")
            if msg:
                for line in msg.splitlines()[:5]:
                    self.terminal_display.log("REMOTE", line, tag_color="#60a5fa", prefix="🌐")
            self.refresh_current_project(reset_terminal=False)
        else:
            self.terminal_display.log_error("GIT-PUSH", f"Fallo al realizar push a origin/{branch}: {msg}")

    def run_ai_diff_audit(self, model_type: str):
        """Ejecuta la auditoría inteligente de Diff con el modelo seleccionado (light o heavy)."""
        path = self.project_data.get("path")
        if not path or not os.path.exists(path):
            self.terminal_display.log_error("IA-AUDIT", "No hay un proyecto activo seleccionado.")
            return

        if self.audit_thread and self.audit_thread.isRunning():
            self.terminal_display.log_warn("IA-AUDIT", "Ya hay una auditoría de IA en curso. Espera a que termine.")
            return

        model_name = get_configured_model(model_type)
        m_label = "Modelo Ligero" if model_type == "light" else "Modelo Pesado"
        color = "#38bdf8" if model_type == "light" else "#c084fc"

        self.terminal_display.log("IA-AUDIT", f"Iniciando auditoría con <b>{m_label}</b> [<code>{model_name}</code>]...", tag_color=color, prefix="🔍")
        self.terminal_display.log_info("AI-ENGINE", "Extrayendo diff y procesando telemetría con Ollama...")

        self.audit_thread = IAAuditThread(path, model_type=model_type)
        self.audit_thread.finished_audit.connect(self.on_audit_finished)
        self.audit_thread.start()

    def on_audit_finished(self, success: bool, err_msg: str, res: dict):
        """Callback al recibir el resultado de la auditoría de IA."""
        if not success:
            self.terminal_display.log_warn("IA-AUDIT", err_msg)
            return

        model_name = res.get("model_name", "Ollama")
        audit_text = res.get("audit_text", "")

        self.terminal_display.log_success("IA-AUDIT", f"Auditoría generada exitosamente por <b>{model_name}</b>:")
        
        # Formatear el reporte de auditoría en un recuadro estilizado en la terminal
        formatted_html = audit_text.replace("\n", "<br>").replace("### ", "<b>").replace("## ", "<b>").replace("**", "<b>").replace("* ", "• ")
        box_html = (
            f"<div style='background-color: rgba(99, 102, 241, 0.08); border-left: 4px solid #818cf8; "
            f"padding: 10px 14px; margin: 8px 0; border-radius: 4px; font-family: sans-serif; font-size: 12px; "
            f"color: #f3f4f6; line-height: 1.5;'>"
            f"<div style='font-weight: 800; color: #a5b4fc; margin-bottom: 6px; font-family: monospace;'>"
            f"📊 REPORTE DE AUDITORÍA DE DIFF [{model_name}]:"
            f"</div>"
            f"{formatted_html}"
            f"</div>"
        )
        self.terminal_display.append(box_html)
        self.terminal_display.verticalScrollBar().setValue(self.terminal_display.verticalScrollBar().maximum())

    # -----------------------------------------------------------------
    # PROTOCOLO ARTEMIS: FLUJO DE IA COMMIT (VERSIONS ➔ MODEL ➔ CONFIRM ➔ PUSH)
    # -----------------------------------------------------------------
    def start_ia_commit_workflow(self):
        """Inicia el flujo de commit semántico con IA según los protocolos de Artemis."""
        path = self.project_data.get("path")
        if not path or not os.path.exists(path):
            self.terminal_display.log_error("IA-COMMIT", "No hay un proyecto activo seleccionado.")
            return

        # 1. Comprobar si hay cambios preparados (staged)
        st_proc = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=path, capture_output=True, text=True, timeout=5)
        staged_files = st_proc.stdout.strip().splitlines() if st_proc.stdout.strip() else []
        
        if not staged_files:
            # Comprobar si hay cambios sin preparar para dar mensaje orientativo
            u_proc = subprocess.run(["git", "diff", "--name-only"], cwd=path, capture_output=True, text=True, timeout=5)
            unstaged_files = u_proc.stdout.strip().splitlines() if u_proc.stdout.strip() else []
            if unstaged_files:
                self.terminal_display.log("IA-COMMIT", "❌ <b>Stage vacío</b>. Tienes archivos modificados pero no preparados. Ejecuta <b>➕ Add (Preparar Cambios)</b> primero.", tag_color="#f87171", prefix="⚠️")
            else:
                self.terminal_display.log("IA-COMMIT", "❌ <b>Árbol de trabajo limpio</b>. No hay modificaciones pendientes para confirmar en commit.", tag_color="#f87171", prefix="⚠️")
            return

        # 2. Calcular versiones SemVer
        cur_ver = get_project_semver(path)
        next_gamma = bump_semver(cur_ver, "GAMMA")
        next_beta = bump_semver(cur_ver, "BETA")
        next_alpha = bump_semver(cur_ver, "ALPHA")

        self.lbl_semver_title.setText(f"❖ CONTROL DE VERSIONES (SemVer: {cur_ver}) ❖")
        self.btn_gamma.set_title(f"1. GAMMA (Patch) ➔ {next_gamma}")
        self.btn_gamma.set_subtitle(f"Fix, ajuste menor, docs • Siguiente versión: {next_gamma}")

        self.btn_beta.set_title(f"2. BETA (Minor) ➔ {next_beta}")
        self.btn_beta.set_subtitle(f"Nuevo módulo, funcionalidad • Siguiente versión: {next_beta}")

        self.btn_alpha.set_title(f"3. ALPHA (Major) ➔ {next_alpha}")
        self.btn_alpha.set_subtitle(f"Reestructuración masiva o cambio mayor • Siguiente versión: {next_alpha}")

        self.btn_omit.set_title(f"4. Omitir bump ➔ {cur_ver}")
        self.btn_omit.set_subtitle(f"Mantener versión actual {cur_ver} sin generar nuevo tag")

        self.cur_semver_options = {
            "GAMMA": next_gamma,
            "BETA": next_beta,
            "ALPHA": next_alpha,
            "OMIT": cur_ver
        }

        self.sector1_sub_stack.setCurrentIndex(2)
        self.terminal_display.log("IA-COMMIT", f"Iniciando protocolo de commit. Versión base detectada: <b style='color:#fbbf24;'>{cur_ver}</b>.", tag_color="#c084fc", prefix="🤖")
        self.terminal_display.log("STAGE", f"{len(staged_files)} archivo(s) preparados en staging listos para sintetizar.", tag_color="#34d399", prefix="📦")

    def select_semver_impact(self, impact_type: str):
        """Maneja la selección del nivel de impacto SemVer y pasa a seleccionar el motor de IA."""
        self.selected_impact = impact_type
        self.selected_target_ver = self.cur_semver_options.get(impact_type, "v0.1.0")

        # Cargar nombres de modelos configurados
        light_name = get_configured_model("light")
        heavy_name = get_configured_model("heavy")

        self.btn_commit_hex.set_title(f"1. HEX ({light_name} - Rápido)")
        self.btn_commit_hex.set_subtitle(f"Generación ágil y concisa de título y cuerpo semántico • {light_name}")

        self.btn_commit_hen.set_title(f"2. HENDRIX ({heavy_name} - Pesado/Inteligente)")
        self.btn_commit_hen.set_subtitle(f"Análisis exhaustivo del diff y redacción técnica profunda • {heavy_name}")

        self.sector1_sub_stack.setCurrentIndex(3)
        self.terminal_display.log("SEMVER", f"Impacto seleccionado: <b style='color:#34d399;'>{impact_type}</b> ➔ <b>{self.selected_target_ver}</b>.", tag_color="#34d399", prefix="🟢")

    def start_commit_model_generation(self, model_type: str):
        """Inicia la generación de la propuesta de commit con el modelo seleccionado (HEX o HENDRIX)."""
        path = self.project_data.get("path")
        if not path:
            return

        if self.commit_thread and self.commit_thread.isRunning():
            self.terminal_display.log_warn("IA-COMMIT", "Ya hay una generación de commit en curso. Por favor espera.")
            return

        self.selected_model_type = model_type
        model_name = get_configured_model(model_type)
        id_prefix = "HEX" if model_type == "light" else "HEN"

        # Actualizar textos de carga
        self.lbl_commit_loading_title.setText(f"GENERANDO PROPUESTA DE COMMIT CON {model_name.upper()}...")
        self.lbl_commit_loading_sub.setText(f"Motor: {id_prefix} ({model_type.upper()}) | Nivel de impacto: {self.selected_impact} [{self.selected_target_ver}]")

        self.sector1_sub_stack.setCurrentIndex(4)

        self.terminal_display.log("IA-COMMIT", f"Invocando red neuronal <b>{model_name}</b> ({id_prefix}) con impacto <b style='color:#fbbf24;'>{self.selected_impact}</b>...", tag_color="#ec4899", prefix="⏳")
        self.terminal_display.log_info("AI-ENGINE", "Extrayendo git diff en staging y aplicando directivas de razonamiento de IA...")

        self.commit_thread = IACommitThread(
            project_path=path,
            model_type=model_type,
            impact_type=self.selected_impact,
            target_ver=self.selected_target_ver
        )
        self.commit_thread.finished_commit.connect(self.on_commit_proposal_generated)
        self.commit_thread.start()

    def on_commit_proposal_generated(self, success: bool, err_msg: str, res: dict):
        """Callback al recibir la propuesta de commit generada por la IA."""
        if not success:
            self.terminal_display.log_error("IA-COMMIT", f"Error al generar commit con IA: {err_msg}")
            self.sector1_sub_stack.setCurrentIndex(3)
            return

        self.current_commit_proposal = res
        model_name = res.get("model_name", "Ollama")
        id_prefix = res.get("id_prefix", "HEX")
        commit_header = res.get("commit_header", "HEX:0001")
        title = res.get("title", "")
        body = res.get("body", "")
        impact = res.get("impact_type", "GAMMA")
        ver = res.get("target_ver", "v0.1.0")

        # Proyectar en la terminal inferior el resultado
        self.terminal_display.log("IA-COMMIT", f"Propuesta de commit generada exitosamente por <b>{model_name}</b>:", tag_color="#34d399", prefix="✔")

        report_box = (
            f"<div style='background-color: rgba(16, 185, 129, 0.08); border-left: 4px solid #34d399; "
            f"padding: 10px 14px; margin: 8px 0; border-radius: 4px; font-family: monospace; font-size: 12px; "
            f"color: #f3f4f6; line-height: 1.5;'>"
            f"<div style='font-weight: 800; color: #fbbf24; margin-bottom: 4px;'>"
            f"❖ PROPUESTA DE COMMIT ABRAXAS ({id_prefix}) ❖"
            f"</div>"
            f"<div style='margin-bottom: 2px;'><b style='color: #38bdf8;'>TÍTULO:</b> {commit_header} | {title}</div>"
            f"<div style='margin-bottom: 6px;'><b style='color: #c084fc;'>IMPACTO:</b> {impact} (Versión: {ver})</div>"
            f"<div><b style='color: #34d399;'>CUERPO:</b><br>{body}</div>"
            f"</div>"
        )
        self.terminal_display.append(report_box)
        self.terminal_display.verticalScrollBar().setValue(self.terminal_display.verticalScrollBar().maximum())

        # Actualizar tarjeta de confirmación en la UI
        self.lbl_prop_title.setText(f"TÍTULO: {commit_header} | {title}")
        self.lbl_prop_impact.setText(f"IMPACTO: {impact} (Versión: {ver})")
        self.lbl_prop_body.setText(f"CUERPO:\n{body}")

        # Pasar a la pantalla de confirmación (Página 5)
        self.sector1_sub_stack.setCurrentIndex(5)

    def confirm_and_record_commit(self):
        """Confirma y graba el commit y etiqueta SemVer en Git."""
        path = self.project_data.get("path")
        if not path or not self.current_commit_proposal:
            self.terminal_display.log_error("COMMIT", "No hay una propuesta de commit válida para confirmar.")
            return

        res = self.current_commit_proposal
        commit_header = res.get("commit_header", "HEX:0001")
        title = res.get("title", "")
        body = res.get("body", "")
        impact = res.get("impact_type", "GAMMA")
        ver = res.get("target_ver", "v0.1.0")

        self.terminal_display.log("COMMIT", f"Registrando commit en Git (<code>{commit_header} | {title}</code>)...", tag_color="#34d399", prefix="💾")

        ok, output = execute_commit_and_tag(
            project_path=path,
            commit_header=commit_header,
            title=title,
            body=body,
            impact_type=impact,
            target_ver=ver
        )

        if ok:
            self.terminal_display.log_success("COMMIT", f"Commit registrado con éxito en Git: <b>{commit_header} | {title}</b>")
            if impact != "OMIT" and ver:
                self.terminal_display.log("TAG", f"Etiqueta de versión SemVer <b>{ver}</b> creada.", tag_color="#818cf8", prefix="🏷️")

            # Refrescar el HUD sin borrar la salida de la terminal
            self.refresh_current_project(reset_terminal=False)

            # Pasar a la pantalla post-commit (Página 6: Opción a Push)
            self.sector1_sub_stack.setCurrentIndex(6)
        else:
            self.terminal_display.log_error("COMMIT", f"Error al ejecutar commit: {output}")

    def discard_commit_proposal(self):
        """Descarta la propuesta de commit generada y regresa a Ciclos de Trabajo."""
        self.current_commit_proposal = {}
        self.terminal_display.log("COMMIT", "Propuesta de commit descartada por el operador. No se realizaron cambios.", tag_color="#9ca3af", prefix="❌")
        self.sector1_sub_stack.setCurrentIndex(0)

    def execute_post_commit_push(self):
        """Ejecuta git push --follow-tags hacia el repositorio remoto y vuelve al menú."""
        self.sector1_sub_stack.setCurrentIndex(0)
        self.run_git_push(follow_tags=True)

    def discard_post_commit_push(self):
        """Omite el push y regresa directamente al menú principal de Ciclos de Trabajo."""
        self.terminal_display.log("PUSH", "Push remoto omitido. Los commits y etiquetas quedan guardados localmente.", tag_color="#9ca3af", prefix="ℹ")
        self.sector1_sub_stack.setCurrentIndex(0)

    # -----------------------------------------------------------------
    # MÉTODOS DE RELOJ, LOGS Y ACCIONES GENÉRICAS
    # -----------------------------------------------------------------
    def update_clock(self):
        """Actualiza la hora actual en tiempo real."""
        now_str = datetime.now().strftime("%H:%M:%S")
        self.lbl_current_time.setText(now_str)

    def copy_terminal_output(self):
        """Copia el texto plano actual del visor al portapapeles del sistema."""
        text = self.terminal_display.toPlainText()
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            self.terminal_display.log_info("CLIPBOARD", "Contenido del visor copiado al portapapeles.")

    def clear_terminal_output(self):
        """Limpia el contenido del visor terminal."""
        self.terminal_display.clear()
        p_name = self.project_data.get("name", "Proyecto")
        self.terminal_display.log(
            "READY", 
            f"Terminal lista para <b>{p_name}</b>.", 
            tag_color="#34d399", 
            prefix="❯"
        )

    def handle_action_click(self, action_title: str):
        """Maneja el clic interactivo en las acciones y proyecta el log coloreado en la terminal."""
        p_name = self.project_data.get("name", "Proyecto")
        
        actions_map = {
            "Ciclos de Trabajo": ("WORKFLOW", f"Accediendo al menú de <b>Ciclos de Trabajo</b> para <b>{p_name}</b>...", "#38bdf8", "🔄"),
            "IA Commit (Generar commit)": ("IA-COMMIT", f"Analizando cambios en staging para generar propuesta semántica de commit...", "#c084fc", "🤖"),
            "Commit Manual": ("COMMIT", f"Abriendo formulario para redacción de commit manual...", "#fbbf24", "✍️"),
            "Control de Ramas": ("GIT-BRANCH", f"Consultando matriz de ramas para <b>{p_name}</b>... (git branch -a)", "#c084fc", "🌿"),
            "Fusión de Ramas": ("GIT-MERGE", f"Preparando interfaz de fusión (merge) para <b>{p_name}</b>...", "#38bdf8", "🔀"),
            "Estado y Sincronización": ("GIT-SYNC", f"Verificando estado del árbol de trabajo (Status / Fetch / Pull)...", "#34d399", "⚡"),
            "Ejecutar proyecto en editor": ("IDE", f"Lanzando espacio de trabajo de <b>{p_name}</b> en editor externo...", "#38bdf8", "💻"),
            "Entornos python": ("VENV", f"Inspeccionando dependencias y entorno virtual de <b>{p_name}</b>...", "#fbbf24", "🐍"),
            "Docker y puertos": ("DOCKER", f"Verificando servicios Docker y mapeo de puertos para <b>{p_name}</b>...", "#60a5fa", "🐳"),
            "Gestor de gitignore": ("GITIGNORE", f"Analizando reglas y plantillas de exclusión en <code>.gitignore</code>...", "#c084fc", "🛡️"),
            "Lector de documentación": ("DOCS", f"Cargando lector de documentación y archivos README...", "#818cf8", "📖"),
            "Utilidades IA": ("AI-COPILOT", f"Iniciando puente de telemetría con modelo de IA local (Ollama)...", "#ec4899", "🤖"),
            "Usuario Git": ("USER", f"Consultando perfil de autor, correo y llaves de firma Git...", "#fbbf24", "👤")
        }

        if action_title in actions_map:
            tag, msg, color, prefix = actions_map[action_title]
            self.terminal_display.log(tag, msg, tag_color=color, prefix=prefix)
        else:
            self.terminal_display.log_info("ACTION", f"Ejecutando acción: <b>{action_title}</b>...")

    def set_project(self, folder_data: dict, reset_terminal: bool = True):
        """Sincroniza y carga en tiempo real la información del proyecto seleccionado en el HUD y terminal coloreada."""
        self.project_data = folder_data
        sync = get_full_project_sync(folder_data)

        # 1. Proyecto, Versión, Rama, Remoto
        self.lbl_proj_title.setText(f"{sync['name']} ({sync['version']})")
        self.lbl_proj_branch.setText(sync['git_info']['branch'])
        self.lbl_proj_remote.setText(sync['git_info']['remote'])

        # 2. Entorno, Docker, Hora
        env_text = sync['env_info']['text']
        self.lbl_env_status.setText(env_text)
        if sync['env_info']['is_active']:
            self.lbl_env_status.setStyleSheet("font-weight: 800; color: #34d399; font-size: 13px;")
        else:
            self.lbl_env_status.setStyleSheet("font-weight: 700; color: #9ca3af; font-size: 13px;")

        self.lbl_docker_status.setText(sync['docker_info']['text'])
        self.lbl_current_time.setText(sync['timestamp'])

        # 3. Git HUD
        self.lbl_git_mod.setText(sync['git_hud']['mod_str'])
        self.lbl_git_untracked.setText(sync['git_hud']['untracked_str'])
        self.lbl_git_deleted.setText(sync['git_hud']['deleted_str'])

        # 4. Historial reciente (Commits en tiempo real)
        while self.history_items_layout.count():
            item = self.history_items_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            elif item.layout():
                sub_lay = item.layout()
                while sub_lay.count():
                    sub_item = sub_lay.takeAt(0)
                    if sub_item.widget():
                        sub_item.widget().deleteLater()

        commits = sync.get("commits", [])
        if commits:
            for c in commits:
                row_c = QHBoxLayout()
                row_c.setSpacing(8)

                lbl_dot = QLabel("◈")
                lbl_dot.setStyleSheet(f"color: {c.get('color', '#38bdf8')}; font-size: 12px;")
                row_c.addWidget(lbl_dot)

                lbl_time = QLabel(c['time'])
                lbl_time.setStyleSheet("font-family: monospace; font-size: 12px; color: #9ca3af; font-weight: 600; min-width: 85px;")
                row_c.addWidget(lbl_time)

                lbl_c_title = QLabel(c['title'])
                lbl_c_title.setStyleSheet("font-size: 12.5px; color: #f3f4f6; font-weight: 600;")
                row_c.addWidget(lbl_c_title, 1)

                lbl_author = QLabel(f"👤 {c['author']}")
                lbl_author.setStyleSheet("font-size: 12px; color: #9ca3af;")
                row_c.addWidget(lbl_author)

                lbl_br = QLabel(f"[{c['branch']}]")
                lbl_br.setStyleSheet("font-family: monospace; font-size: 11.5px; color: #818cf8; font-weight: 700;")
                row_c.addWidget(lbl_br)

                self.history_items_layout.addLayout(row_c)
        else:
            lbl_empty = QLabel("  • (No hay historial de commits registrado para este proyecto)")
            lbl_empty.setStyleSheet("font-family: monospace; font-size: 12px; color: #6b7280; font-style: italic;")
            self.history_items_layout.addWidget(lbl_empty)

        # 5. Visor de terminal coloreado con HTML y diseño ciber-ilustre
        p_name_clean = sync['name'].lower().replace(" ", "-")
        self.lbl_t_title.setText(f"lumen-terminal@{p_name_clean}:~$")

        if reset_terminal:
            # SIEMPRE resetear al panel general de los 4 sectores al abrir un proyecto desde cero
            if hasattr(self, "sectors_stack"):
                self.sectors_stack.setCurrentIndex(0)
            if hasattr(self, "sector1_sub_stack"):
                self.sector1_sub_stack.setCurrentIndex(0)

            self.terminal_display.clear()
            self.terminal_display.log(
                "KERNEL", 
                f"Conectado a <b style='color:#fbbf24;'>{sync['name']}</b> <span style='color:#a5b4fc;'>[{sync['version']}]</span> en rama <b style='color:#38bdf8;'>{sync['git_info']['branch']}</b>",
                tag_color="#818cf8",
                prefix="❖"
            )
            self.terminal_display.log(
                "READY",
                "Esperando acciones...",
                tag_color="#34d399",
                prefix="❯"
            )

    def refresh_current_project(self, reset_terminal: bool = False):
        """Re-sincroniza el proyecto actual con el disco."""
        if self.project_data:
            self.set_project(self.project_data, reset_terminal=reset_terminal)
            self.terminal_display.log_success("SYNC", "HUD y estado del repositorio actualizados.")
