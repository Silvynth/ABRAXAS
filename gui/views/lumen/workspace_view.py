#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS | LUMEN - PROJECT WORKSPACE VIEW (DASHBOARD DEL PROYECTO)
# =====================================================================

import os
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QScrollArea, QGridLayout
)
from PySide6.QtCore import Qt, Signal

from core import get_version


class LumenCyberActionButton(QFrame):
    """Botón interactivo de diseño ciber-ilustre con icono, título, subtítulo y efectos de hover."""
    
    clicked = Signal()

    def __init__(self, icon: str, title: str, subtitle: str, accent_color="#6366f1", parent=None):
        super().__init__(parent)
        self.accent_color = accent_color
        self.setCursor(Qt.PointingHandCursor)
        self.setProperty("class", "cyber_action_card")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
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

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class LumenProjectWorkspaceView(QWidget):
    """Vista ilustre y épica de control de desarrollo y HUD de proyecto en LUMEN."""
    
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.app_version = get_version()
        self.project_data = {}
        self.init_ui()

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
        # 2. HUD GENERAL DEL PROYECTO (UN SOLO CUADRO LIMPIO)
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
        self.lbl_proj_title = QLabel("ABRAXAS (v0.1.0)")
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
        self.lbl_env_status = QLabel("Activado (.venv)")
        self.lbl_env_status.setStyleSheet("font-weight: 800; color: #34d399; font-size: 13px;")

        sep3 = QLabel(" | ")
        sep3.setStyleSheet("color: #4b5563; font-weight: 700;")

        lbl_d_tag = QLabel("🐳 Contenedores Docker:")
        lbl_d_tag.setStyleSheet("font-weight: 700; color: #9ca3af; font-size: 13px;")
        self.lbl_docker_status = QLabel("2 activos")
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
        self.lbl_git_mod = QLabel("3 archivos modificados")
        self.lbl_git_mod.setStyleSheet("font-weight: 700; color: #fbbf24; font-size: 13px;")

        sep6 = QLabel(" | ")
        sep6.setStyleSheet("color: #4b5563; font-weight: 700;")

        lbl_u_tag = QLabel("❓ Untracked:")
        lbl_u_tag.setStyleSheet("font-weight: 700; color: #9ca3af; font-size: 13px;")
        self.lbl_git_untracked = QLabel("1 no rastreado")
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

        demo_commits = [
            ("Hace 25 min", "feat: arquitectura de navegación y selector de proyectos", "Silvynth", "main", "#38bdf8"),
            ("Hace 2 horas", "refactor: optimización de temas y estilos visuales", "Silvynth", "main", "#c084fc"),
            ("Hace 5 horas", "fix: corrección de dimensiones de tarjetas y clipping", "Silvynth", "main", "#fbbf24"),
            ("Hace 1 día", "init: estructura base y controlador de motor dev", "Silvynth", "main", "#34d399")
        ]

        for time_s, title_s, author_s, branch_s, color_accent in demo_commits:
            row_c = QHBoxLayout()
            row_c.setSpacing(8)

            lbl_dot = QLabel("◈")
            lbl_dot.setStyleSheet(f"color: {color_accent}; font-size: 12px;")
            row_c.addWidget(lbl_dot)

            lbl_time = QLabel(time_s)
            lbl_time.setStyleSheet("font-family: monospace; font-size: 12px; color: #9ca3af; font-weight: 600; min-width: 85px;")
            row_c.addWidget(lbl_time)

            lbl_c_title = QLabel(title_s)
            lbl_c_title.setStyleSheet("font-size: 12.5px; color: #f3f4f6; font-weight: 600;")
            row_c.addWidget(lbl_c_title, 1)

            lbl_author = QLabel(f"👤 {author_s}")
            lbl_author.setStyleSheet("font-size: 12px; color: #9ca3af;")
            row_c.addWidget(lbl_author)

            lbl_br = QLabel(f"[{branch_s}]")
            lbl_br.setStyleSheet("font-family: monospace; font-size: 11.5px; color: #818cf8; font-weight: 700;")
            row_c.addWidget(lbl_br)

            hud_layout.addLayout(row_c)

        content_layout.addWidget(self.hud_card)

        # -------------------------------------------------------------
        # 3. LOS CUATRO SECTORES DE HERRAMIENTAS (UN CUADRO POR SECTOR)
        # -------------------------------------------------------------
        sectors_grid = QGridLayout()
        sectors_grid.setSpacing(14)

        # SECTOR 1: Ciclos de Trabajo
        card_s1 = self.create_cyber_sector_card(
            title="🔄  PRIMER SECTOR : CICLOS DE TRABAJO",
            accent_color="#38bdf8",
            actions=[
                ("🌿", "Control de ramas", "Crear, cambiar y listar ramas locales y remotas"),
                ("🔀", "Fusión de ramas", "Merge, rebase y resolución de conflictos"),
                ("🔄", "Estado y sincronización", "Fetch, pull, push y sincronización con origin")
            ]
        )
        sectors_grid.addWidget(card_s1, 0, 0)

        # SECTOR 2: Entornos y Ejecución
        card_s2 = self.create_cyber_sector_card(
            title="🚀  SEGUNDO SECTOR : ENTORNOS Y EJECUCIÓN",
            accent_color="#10b981",
            actions=[
                ("💻", "Ejecutar proyecto en editor", "Lanzar espacio de trabajo en VS Code / IDE"),
                ("🐍", "Entornos python", "Gestor de paquetes, dependencias y virtualenv"),
                ("🐳", "Docker y puertos", "Control de contenedores, compose y mapeos")
            ]
        )
        sectors_grid.addWidget(card_s2, 0, 1)

        # SECTOR 3: Herramientas & IA
        card_s3 = self.create_cyber_sector_card(
            title="🧠  TERCER SECTOR : HERRAMIENTAS & IA",
            accent_color="#c084fc",
            actions=[
                ("🛡️", "Gestor de gitignore", "Plantillas inteligentes y reglas de exclusión"),
                ("📖", "Lector de documentación", "Visor interactivo de Markdown, README y APIs"),
                ("🤖", "Utilidades IA", "Asistente Ollama local, refactor y ayuda dev")
            ]
        )
        sectors_grid.addWidget(card_s3, 1, 0)

        # SECTOR 4: Usuario Git
        card_s4 = self.create_cyber_sector_card(
            title="👤  SECTOR CUATRO : USUARIO GIT",
            accent_color="#fbbf24",
            actions=[
                ("🏷️", "Usuario Git", "Nombre, correo y firma de autor para commits")
            ]
        )
        sectors_grid.addWidget(card_s4, 1, 1)

        content_layout.addLayout(sectors_grid)

        # -------------------------------------------------------------
        # 4. RECUADRO INFERIOR (INTERFAZ DE RESULTADOS & SALIDA TERMINAL)
        # -------------------------------------------------------------
        self.bottom_empty_card = QFrame()
        self.bottom_empty_card.setProperty("class", "surface")
        self.bottom_empty_card.setStyleSheet("""
            QFrame.surface {
                background-color: #0c0e14;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
            }
        """)
        b_layout = QVBoxLayout(self.bottom_empty_card)
        b_layout.setContentsMargins(0, 0, 0, 0)
        b_layout.setSpacing(0)

        # Barra de título de la terminal
        term_bar = QFrame()
        term_bar.setStyleSheet("""
            background-color: rgba(255, 255, 255, 0.03);
            border-bottom: 1px solid rgba(255, 255, 255, 0.07);
            border-top-left-radius: 10px;
            border-top-right-radius: 10px;
            padding: 4px 10px;
        """)
        t_bar_layout = QHBoxLayout(term_bar)
        t_bar_layout.setContentsMargins(12, 6, 12, 6)
        t_bar_layout.setSpacing(8)

        # Dots de ventana Unix
        lbl_dots = QLabel("🔴  🟡  🟢")
        lbl_dots.setStyleSheet("font-size: 9px;")
        t_bar_layout.addWidget(lbl_dots)

        self.lbl_t_title = QLabel("lumen-terminal@abraxas:~$")
        self.lbl_t_title.setStyleSheet("font-family: monospace; font-size: 12px; font-weight: 700; color: #9ca3af;")
        t_bar_layout.addWidget(self.lbl_t_title)

        t_bar_layout.addStretch()

        lbl_t_status = QLabel("⚡ INTERFAZ DE RESULTADOS & SALIDA")
        lbl_t_status.setStyleSheet("font-size: 10.5px; font-weight: 800; color: #6366f1; letter-spacing: 0.5px;")
        t_bar_layout.addWidget(lbl_t_status)

        b_layout.addWidget(term_bar)

        # Cuerpo del espacio de salida
        term_body = QFrame()
        term_body.setMinimumHeight(150)
        tb_layout_body = QVBoxLayout(term_body)
        tb_layout_body.setContentsMargins(18, 16, 18, 16)
        tb_layout_body.setSpacing(6)

        self.lbl_prompt1 = QLabel("❯  Kernel Lumen v0.3.0 listo para ejecución.")
        self.lbl_prompt1.setStyleSheet("font-family: monospace; font-size: 12px; color: #34d399;")
        tb_layout_body.addWidget(self.lbl_prompt1)

        self.lbl_prompt2 = QLabel("❯  Selecciona una acción en los sectores superiores para ejecutar y visualizar resultados...")
        self.lbl_prompt2.setStyleSheet("font-family: monospace; font-size: 12px; color: #6b7280;")
        tb_layout_body.addWidget(self.lbl_prompt2)

        tb_layout_body.addStretch()
        b_layout.addWidget(term_body)

        content_layout.addWidget(self.bottom_empty_card)

        scroll_area.setWidget(scroll_content)
        root_layout.addWidget(scroll_area, 1)

    def create_cyber_sector_card(self, title: str, accent_color: str, actions: list) -> QFrame:
        """Crea una tarjeta única por sector con botones ilustres."""
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

        # Header del Sector
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(f"font-size: 12.5px; font-weight: 900; color: {accent_color}; letter-spacing: 0.5px;")
        c_layout.addWidget(lbl_title)

        for icon, act_title, act_sub in actions:
            btn = LumenCyberActionButton(icon, act_title, act_sub, accent_color=accent_color)
            c_layout.addWidget(btn)

        c_layout.addStretch()
        return card

    def set_project(self, folder_data: dict):
        """Carga la información del proyecto en el HUD."""
        self.project_data = folder_data
        p_name = folder_data.get("name", "Proyecto")
        p_path = folder_data.get("path", "")
        
        now_str = datetime.now().strftime("%H:%M:%S")
        self.lbl_current_time.setText(now_str)

        # Título y versión
        self.lbl_proj_title.setText(f"{p_name} (v0.1.0)")
        self.lbl_t_title.setText(f"lumen-terminal@{p_name.lower()}:~$")
        
        # Git branch / status si existe
        git_path = os.path.join(p_path, ".git") if p_path else ""
        if git_path and os.path.exists(git_path):
            self.lbl_proj_branch.setText("main")
            self.lbl_proj_remote.setText("origin/main")
        else:
            self.lbl_proj_branch.setText("(Sin Git)")
            self.lbl_proj_remote.setText("Local")
