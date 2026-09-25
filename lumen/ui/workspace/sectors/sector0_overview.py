"""
❖ ABRAXAS 2.0 | Lumen UI: Sector 00 - Topología, Red & Estado de Archivos (Sector 0)
Panel ejecutivo limpio y puramente visual que abarca en vertical desde el HUD hasta la Terminal:
- Izquierda: Grafo de ramas y bifurcaciones en toda la altura vertical.
- Derecha Superior: Historial cronológico de commits y lista de autores del proyecto.
- Derecha Inferior: Listado limpio de archivos Modificados, Añadidos y Eliminados (solo nombrándolos).
"""

import subprocess
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QScrollArea, QSplitter, QSizePolicy, QGridLayout
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor

from lumen.models.project import Project
from lumen.ui.git_graph_canvas import LumenHorizontalGitGraphView


class ExpandableCommitCard(QFrame):
    """
    Ficha de commit expandible en el Timeline de Versiones.
    Permite desplegar/colapsar haciendo clic en el botón de la esquina o doble clic en la tarjeta
    para inspeccionar el commit completo, su SHA y sus mensajes/descripción detallada.
    """
    def __init__(self, c_hash: str, full_hash: str, author: str, date_rel: str, subject: str, body: str, parent=None):
        super().__init__(parent)
        self.c_hash = c_hash
        self.full_hash = full_hash
        self.author = author
        self.date_rel = date_rel
        self.subject = subject
        self.body = body.strip()
        self.is_expanded = False

        self.setObjectName("ExpandableCommitCard")
        self.setStyleSheet("""
            QFrame#ExpandableCommitCard {
                background: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 6px;
            }
            QFrame#ExpandableCommitCard:hover {
                background: rgba(255, 255, 255, 0.04);
                border-color: rgba(255, 255, 255, 0.09);
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # 1. Cabecera (Hash + Título + Botón chevron de la esquina)
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(6)

        lbl_h = QLabel(self.c_hash)
        lbl_h.setStyleSheet("""
            font-family: 'JetBrains Mono', monospace;
            font-size: 10px;
            font-weight: 700;
            color: #38bdf8;
            background: rgba(56, 189, 248, 0.08);
            border: 1px solid rgba(56, 189, 248, 0.20);
            border-radius: 3px;
            padding: 1px 5px;
        """)
        header_row.addWidget(lbl_h)

        lbl_s = QLabel(self.subject)
        lbl_s.setStyleSheet("color: #ffffff; font-size: 10.5px; font-weight: 600;")
        lbl_s.setWordWrap(True)
        header_row.addWidget(lbl_s, 1)

        # Botón interactivo de despliegue en la esquina superior derecha
        self.btn_toggle = QPushButton("▶")
        self.btn_toggle.setFixedSize(20, 20)
        self.btn_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_toggle.setToolTip("Desplegar commit completo y mensajes detallados")
        self.btn_toggle.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.05);
                color: #94a3b8;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 3px;
                font-size: 8px;
                font-weight: 800;
                padding: 0px;
            }
            QPushButton:hover {
                background: rgba(56, 189, 248, 0.20);
                color: #38bdf8;
                border-color: rgba(56, 189, 248, 0.40);
            }
        """)
        self.btn_toggle.clicked.connect(self.toggle_expanded)
        header_row.addWidget(self.btn_toggle)
        layout.addLayout(header_row)

        # 2. Metadatos (Autor y Fecha relativa)
        lbl_meta = QLabel(f"👤 {self.author} • 🕒 {self.date_rel}")
        lbl_meta.setStyleSheet("color: #64748b; font-size: 9px;")
        layout.addWidget(lbl_meta)

        # 3. Contenedor Desplegable con Detalles (Oculto por defecto)
        self.details_container = QFrame()
        self.details_container.setVisible(False)
        self.details_container.setStyleSheet("""
            background: rgba(0, 0, 0, 0.40);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 5px;
        """)
        d_layout = QVBoxLayout(self.details_container)
        d_layout.setContentsMargins(8, 7, 8, 7)
        d_layout.setSpacing(5)

        # SHA Completo
        sha_box = QHBoxLayout()
        sha_box.setSpacing(6)
        lbl_sha_tag = QLabel("SHA:")
        lbl_sha_tag.setStyleSheet("color: #64748b; font-size: 8.5px; font-weight: 800; font-family: monospace;")
        sha_box.addWidget(lbl_sha_tag)

        lbl_sha_val = QLabel(self.full_hash)
        lbl_sha_val.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lbl_sha_val.setStyleSheet("color: #94a3b8; font-family: 'JetBrains Mono', monospace; font-size: 8.5px;")
        sha_box.addWidget(lbl_sha_val, 1)
        d_layout.addLayout(sha_box)

        # Mensaje / Cuerpo completo del commit
        if self.body:
            lbl_body_tag = QLabel("MENSAJE DETALLADO:")
            lbl_body_tag.setStyleSheet("color: #38bdf8; font-size: 8.5px; font-weight: 800; letter-spacing: 0.8px;")
            d_layout.addWidget(lbl_body_tag)

            lbl_body_text = QLabel(self.body)
            lbl_body_text.setWordWrap(True)
            lbl_body_text.setTextInteractionFlags(Qt.TextSelectableByMouse)
            lbl_body_text.setStyleSheet("""
                color: #e2e8f0;
                font-family: 'JetBrains Mono', 'Inter', monospace;
                font-size: 9.5px;
                line-height: 1.4;
                background: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.04);
                border-radius: 4px;
                padding: 6px 8px;
            """)
            d_layout.addWidget(lbl_body_text)
        else:
            lbl_no_body = QLabel("(Sin cuerpo o descripción adicional en este commit)")
            lbl_no_body.setStyleSheet("color: #475569; font-size: 9px; font-style: italic;")
            d_layout.addWidget(lbl_no_body)

        layout.addWidget(self.details_container)

    def mouseDoubleClickEvent(self, event):
        self.toggle_expanded()
        super().mouseDoubleClickEvent(event)

    def toggle_expanded(self):
        self.is_expanded = not self.is_expanded
        self.details_container.setVisible(self.is_expanded)
        self.btn_toggle.setText("▼" if self.is_expanded else "▶")
        if self.is_expanded:
            self.btn_toggle.setStyleSheet("""
                QPushButton {
                    background: rgba(56, 189, 248, 0.20);
                    color: #38bdf8;
                    border: 1px solid rgba(56, 189, 248, 0.40);
                    border-radius: 3px;
                    font-size: 8px;
                    font-weight: 800;
                    padding: 0px;
                }
            """)
        else:
            self.btn_toggle.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.05);
                    color: #94a3b8;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 3px;
                    font-size: 8px;
                    font-weight: 800;
                    padding: 0px;
                }
                QPushButton:hover {
                    background: rgba(56, 189, 248, 0.20);
                    color: #38bdf8;
                    border-color: rgba(56, 189, 248, 0.40);
                }
            """)


class Sector0OverviewView(QWidget):
    """
    Sector 0: Vista panorámica ejecutiva de alta observabilidad.
    Ocupa toda la altura vertical disponible entre el HUD superior y la Terminal inferior.
    """
    
    log_emitted = Signal(str)
    action_requested = Signal(str, dict)

    def __init__(self, project: Project = None, parent=None):
        super().__init__(parent)
        self.project = project
        self.init_ui()

        if self.project:
            self.update_project(self.project)

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Splitter principal horizontal que divide el Grafo a la izquierda y la información a la derecha
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: rgba(255, 255, 255, 0.05);
                width: 3px;
            }
            QSplitter::handle:hover {
                background-color: #64748b;
            }
        """)

        # =============================================================
        # 1. PANEL IZQUIERDO: GRAFO DE RAMAS VERTICAL COMPLETO
        # =============================================================
        self.left_card = QFrame()
        self.left_card.setProperty("class", "sector_card")
        self.left_card.setStyleSheet("""
            QFrame {
                background-color: #0c0d10;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 10px;
            }
        """)
        left_layout = QVBoxLayout(self.left_card)
        left_layout.setContentsMargins(14, 12, 14, 12)
        left_layout.setSpacing(8)

        # Barra superior del grafo con controles de zoom
        g_header = QHBoxLayout()
        g_header.setSpacing(8)

        lbl_g_tag = QLabel("SECTOR 00 // TOPOLOGÍA DE RED")
        lbl_g_tag.setStyleSheet("color: #64748b; font-size: 9px; font-weight: 800; letter-spacing: 1.5px;")
        
        lbl_g_title = QLabel("🌿 Grafo de Ramas & Bifurcaciones")
        lbl_g_title.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 800; letter-spacing: 0.3px;")
        
        g_title_box = QVBoxLayout()
        g_title_box.setSpacing(2)
        g_title_box.addWidget(lbl_g_tag)
        g_title_box.addWidget(lbl_g_title)
        g_header.addLayout(g_title_box)

        g_header.addStretch()

        self.btn_orient = QPushButton("↕ Vertical")
        self.btn_orient.setProperty("class", "cyber_btn")
        self.btn_orient.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.04);
                color: #38bdf8;
                border: 1px solid rgba(56, 189, 248, 0.25);
                border-radius: 4px;
                font-family: 'JetBrains Mono', monospace;
                font-size: 10px;
                font-weight: 700;
                padding: 3px 8px;
            }
            QPushButton:hover {
                background: rgba(56, 189, 248, 0.12);
                border-color: #38bdf8;
            }
        """)
        self.btn_orient.setToolTip("Alternar orientación: Vertical (VS Code Git Graph) / Horizontal")
        self.btn_orient.clicked.connect(self._toggle_orientation)
        g_header.addWidget(self.btn_orient)

        btn_zoom_in = QPushButton("➕")
        btn_zoom_in.setProperty("class", "cyber_btn")
        btn_zoom_in.setFixedSize(26, 26)
        btn_zoom_in.setToolTip("Acercar Grafo")
        btn_zoom_in.clicked.connect(self._zoom_in)
        g_header.addWidget(btn_zoom_in)

        btn_zoom_out = QPushButton("➖")
        btn_zoom_out.setProperty("class", "cyber_btn")
        btn_zoom_out.setFixedSize(26, 26)
        btn_zoom_out.setToolTip("Alejar Grafo")
        btn_zoom_out.clicked.connect(self._zoom_out)
        g_header.addWidget(btn_zoom_out)

        btn_zoom_reset = QPushButton("↺")
        btn_zoom_reset.setProperty("class", "cyber_btn")
        btn_zoom_reset.setFixedSize(26, 26)
        btn_zoom_reset.setToolTip("Restablecer Vista")
        btn_zoom_reset.clicked.connect(self._zoom_reset)
        g_header.addWidget(btn_zoom_reset)

        left_layout.addLayout(g_header)

        # Lienzo del grafo horizontal expandiéndose a toda la altura vertical
        self.git_graph = LumenHorizontalGitGraphView(self.left_card)
        self.git_graph.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.git_graph.setStyleSheet("""
            QGraphicsView {
                background-color: #08090b;
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 8px;
            }
        """)
        left_layout.addWidget(self.git_graph, 1)

        self.main_splitter.addWidget(self.left_card)

        # =============================================================
        # 2. PANEL DERECHO: COMMITS + AUTORES (ARRIBA) Y ARCHIVOS (ABAJO)
        # =============================================================
        self.right_container = QWidget()
        right_layout = QVBoxLayout(self.right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        # Splitter vertical derecho para separar Commits/Autores de los Archivos
        self.right_splitter = QSplitter(Qt.Vertical)
        self.right_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: rgba(255, 255, 255, 0.05);
                height: 3px;
            }
            QSplitter::handle:hover {
                background-color: #64748b;
            }
        """)

        # -------------------------------------------------------------
        # PARTE SUPERIOR DERECHA: Historial de Commits + Autores
        # -------------------------------------------------------------
        self.top_right_widget = QWidget()
        top_right_layout = QHBoxLayout(self.top_right_widget)
        top_right_layout.setContentsMargins(0, 0, 0, 0)
        top_right_layout.setSpacing(10)

        # Sub-Card 1: Historial de los Commits
        self.commits_card = QFrame()
        self.commits_card.setProperty("class", "sector_card")
        self.commits_card.setStyleSheet("""
            QFrame {
                background-color: #0c0d10;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 10px;
            }
        """)
        c_layout = QVBoxLayout(self.commits_card)
        c_layout.setContentsMargins(12, 10, 12, 10)
        c_layout.setSpacing(6)

        lbl_c_tag = QLabel("TIMELINE DE VERSIONES")
        lbl_c_tag.setStyleSheet("color: #64748b; font-size: 8.5px; font-weight: 800; letter-spacing: 1.2px;")
        lbl_c_title = QLabel("📜 Historial de Commits")
        lbl_c_title.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: 800;")
        c_layout.addWidget(lbl_c_tag)
        c_layout.addWidget(lbl_c_title)

        scroll_c = QScrollArea()
        scroll_c.setWidgetResizable(True)
        scroll_c.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.commits_list_widget = QWidget()
        self.commits_list_layout = QVBoxLayout(self.commits_list_widget)
        self.commits_list_layout.setContentsMargins(0, 0, 4, 0)
        self.commits_list_layout.setSpacing(5)
        scroll_c.setWidget(self.commits_list_widget)
        c_layout.addWidget(scroll_c, 1)

        top_right_layout.addWidget(self.commits_card, 6)

        # Sub-Card 2: Autores del Proyecto
        self.authors_card = QFrame()
        self.authors_card.setProperty("class", "sector_card")
        self.authors_card.setStyleSheet("""
            QFrame {
                background-color: #0c0d10;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 10px;
            }
        """)
        a_layout = QVBoxLayout(self.authors_card)
        a_layout.setContentsMargins(12, 10, 12, 10)
        a_layout.setSpacing(6)

        lbl_a_tag = QLabel("CONTRIBUIDORES")
        lbl_a_tag.setStyleSheet("color: #64748b; font-size: 8.5px; font-weight: 800; letter-spacing: 1.2px;")
        lbl_a_title = QLabel("👥 Autores del Proyecto")
        lbl_a_title.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: 800;")
        a_layout.addWidget(lbl_a_tag)
        a_layout.addWidget(lbl_a_title)

        scroll_a = QScrollArea()
        scroll_a.setWidgetResizable(True)
        scroll_a.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.authors_list_widget = QWidget()
        self.authors_list_layout = QVBoxLayout(self.authors_list_widget)
        self.authors_list_layout.setContentsMargins(0, 0, 4, 0)
        self.authors_list_layout.setSpacing(5)
        scroll_a.setWidget(self.authors_list_widget)
        a_layout.addWidget(scroll_a, 1)

        top_right_layout.addWidget(self.authors_card, 4)

        self.right_splitter.addWidget(self.top_right_widget)

        # -------------------------------------------------------------
        # PARTE INFERIOR DERECHA: Archivos Modificados, Añadidos y Eliminados
        # -------------------------------------------------------------
        self.files_card = QFrame()
        self.files_card.setProperty("class", "sector_card")
        self.files_card.setStyleSheet("""
            QFrame {
                background-color: #0c0d10;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 10px;
            }
        """)
        f_layout = QVBoxLayout(self.files_card)
        f_layout.setContentsMargins(14, 10, 14, 10)
        f_layout.setSpacing(6)

        f_header = QHBoxLayout()
        f_title_box = QVBoxLayout()
        f_title_box.setSpacing(2)
        lbl_f_tag = QLabel("ESTADO DEL WORKSPACE // CAMBIOS ACTIVOS")
        lbl_f_tag.setStyleSheet("color: #64748b; font-size: 8.5px; font-weight: 800; letter-spacing: 1.2px;")
        lbl_f_title = QLabel("📂 Archivos Modificados, Añadidos y Eliminados")
        lbl_f_title.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: 800;")
        f_title_box.addWidget(lbl_f_tag)
        f_title_box.addWidget(lbl_f_title)
        f_header.addLayout(f_title_box)
        f_header.addStretch()

        self.lbl_files_summary = QLabel("0 cambios detectados")
        self.lbl_files_summary.setStyleSheet("""
            color: #94a3b8; font-size: 10.5px; font-weight: 700;
            background: rgba(255, 255, 255, 0.04); border-radius: 4px; padding: 2px 8px;
        """)
        f_header.addWidget(self.lbl_files_summary)
        f_layout.addLayout(f_header)

        # 3 Columnas de Archivos: Modificados | Añadidos | Eliminados
        files_columns_box = QHBoxLayout()
        files_columns_box.setSpacing(10)

        # Columna 1: Modificados
        col_mod = QVBoxLayout()
        col_mod.setSpacing(4)
        lbl_col_m = QLabel("📝 Modificados")
        lbl_col_m.setStyleSheet("color: #cbd5e1; font-size: 11px; font-weight: 700;")
        col_mod.addWidget(lbl_col_m)

        scroll_m = QScrollArea()
        scroll_m.setWidgetResizable(True)
        scroll_m.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.mod_list_widget = QWidget()
        self.mod_list_layout = QVBoxLayout(self.mod_list_widget)
        self.mod_list_layout.setContentsMargins(0, 0, 2, 0)
        self.mod_list_layout.setSpacing(3)
        self.mod_list_layout.setAlignment(Qt.AlignTop)
        scroll_m.setWidget(self.mod_list_widget)
        col_mod.addWidget(scroll_m, 1)
        files_columns_box.addLayout(col_mod, 1)

        # Columna 2: Añadidos
        col_add = QVBoxLayout()
        col_add.setSpacing(4)
        lbl_col_a = QLabel("➕ Añadidos")
        lbl_col_a.setStyleSheet("color: #e2e8f0; font-size: 11px; font-weight: 700;")
        col_add.addWidget(lbl_col_a)

        scroll_add = QScrollArea()
        scroll_add.setWidgetResizable(True)
        scroll_add.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.add_list_widget = QWidget()
        self.add_list_layout = QVBoxLayout(self.add_list_widget)
        self.add_list_layout.setContentsMargins(0, 0, 2, 0)
        self.add_list_layout.setSpacing(3)
        self.add_list_layout.setAlignment(Qt.AlignTop)
        scroll_add.setWidget(self.add_list_widget)
        col_add.addWidget(scroll_add, 1)
        files_columns_box.addLayout(col_add, 1)

        # Columna 3: Eliminados
        col_del = QVBoxLayout()
        col_del.setSpacing(4)
        lbl_col_d = QLabel("🗑️ Eliminados")
        lbl_col_d.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 700;")
        col_del.addWidget(lbl_col_d)

        scroll_del = QScrollArea()
        scroll_del.setWidgetResizable(True)
        scroll_del.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.del_list_widget = QWidget()
        self.del_list_layout = QVBoxLayout(self.del_list_widget)
        self.del_list_layout.setContentsMargins(0, 0, 2, 0)
        self.del_list_layout.setSpacing(3)
        self.del_list_layout.setAlignment(Qt.AlignTop)
        scroll_del.setWidget(self.del_list_widget)
        col_del.addWidget(scroll_del, 1)
        files_columns_box.addLayout(col_del, 1)

        f_layout.addLayout(files_columns_box, 1)
        self.right_splitter.addWidget(self.files_card)

        # Proporciones verticales derecha: 50% arriba, 50% abajo
        self.right_splitter.setSizes([260, 240])

        right_layout.addWidget(self.right_splitter)
        self.main_splitter.addWidget(self.right_container)

        # Proporciones principales: 52% Grafo a la izquierda, 48% Información a la derecha
        self.main_splitter.setSizes([520, 480])

        root_layout.addWidget(self.main_splitter)

    # -------------------------------------------------------------
    # CARGA Y ACTUALIZACIÓN DE DATOS
    # -------------------------------------------------------------
    def update_project(self, project: Project):
        """Actualiza el grafo, commits, autores y estado de archivos del proyecto."""
        self.project = project
        p_path = str(project.path) if project and project.path else ""

        if not p_path or not Path(p_path).is_dir():
            return

        # 1. Cargar Grafo de Ramas (Izquierda, 100% altura)
        try:
            self.git_graph.load_project_graph(p_path)
        except Exception:
            pass

        # 2. Cargar Commits Recientes
        self._load_commits(p_path)

        # 3. Cargar Autores
        self._load_authors(p_path)

        # 4. Cargar Archivos Modificados, Añadidos y Eliminados
        self._load_files_status(p_path)

    def _load_commits(self, p_path: str):
        while self.commits_list_layout.count() > 0:
            item = self.commits_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cmd = ["git", "log", "-n25", "--pretty=format:%h\x1f%H\x1f%an\x1f%ar\x1f%s\x1f%b\x1e"]
        try:
            res = subprocess.run(cmd, cwd=p_path, capture_output=True, text=True, timeout=4)
            raw = res.stdout.strip()
            entries = raw.split("\x1e") if raw else []
        except Exception:
            entries = []

        if not entries:
            lbl_empty = QLabel("Sin historial disponible.")
            lbl_empty.setStyleSheet("color: #64748b; font-size: 10.5px; font-style: italic;")
            self.commits_list_layout.addWidget(lbl_empty)
            return

        for entry in entries:
            entry = entry.strip()
            if not entry:
                continue
            parts = entry.split("\x1f")
            if len(parts) < 5:
                continue
            c_hash = parts[0].strip()
            full_hash = parts[1].strip()
            author = parts[2].strip()
            date_rel = parts[3].strip()
            subject = parts[4].strip()
            body = parts[5].strip() if len(parts) > 5 else ""

            card = ExpandableCommitCard(c_hash, full_hash, author, date_rel, subject, body)
            self.commits_list_layout.addWidget(card)

    def _load_authors(self, p_path: str):
        while self.authors_list_layout.count() > 0:
            item = self.authors_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.authors_list_layout.setAlignment(Qt.AlignTop)

        cmd = ["git", "shortlog", "-sn", "--all", "--no-merges"]
        try:
            res = subprocess.run(cmd, cwd=p_path, capture_output=True, text=True, timeout=3)
            lines = res.stdout.strip().splitlines()
        except Exception:
            lines = []

        if not lines:
            lbl_empty = QLabel("Sin autores registrados.")
            lbl_empty.setStyleSheet("color: #64748b; font-size: 10.5px; font-style: italic;")
            self.authors_list_layout.addWidget(lbl_empty)
            return

        authors = []
        for line in lines:
            line = line.strip()
            if line:
                parts = line.split("\t", 1)
                if len(parts) == 2:
                    name = parts[1].strip()
                    if name and not any(name.lower() == a.lower() for a in authors):
                        authors.append(name)

        for author_name in authors:
            lbl_item = QLabel(f"•  {author_name}")
            lbl_item.setStyleSheet("""
                color: #e2e8f0;
                font-size: 11px;
                font-weight: 500;
                padding: 3px 2px;
            """)
            self.authors_list_layout.addWidget(lbl_item)

    def _load_files_status(self, p_path: str):
        """Obtiene y clasifica los archivos modificados, añadidos y eliminados."""
        # Limpiar listas
        for layout in (self.mod_list_layout, self.add_list_layout, self.del_list_layout):
            while layout.count() > 0:
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

        cmd = ["git", "status", "--porcelain"]
        try:
            res = subprocess.run(cmd, cwd=p_path, capture_output=True, text=True, timeout=3)
            lines = res.stdout.strip().splitlines()
        except Exception:
            lines = []

        mod_files = []
        add_files = []
        del_files = []

        for line in lines:
            if len(line) < 3:
                continue
            status = line[:2]
            filename = line[3:].strip()
            if "M" in status:
                mod_files.append(filename)
            elif "?" in status or "A" in status:
                add_files.append(filename)
            elif "D" in status:
                del_files.append(filename)

        total_changes = len(mod_files) + len(add_files) + len(del_files)
        self.lbl_files_summary.setText(f"{total_changes} cambios activos")

        def populate(files: list, target_layout: QVBoxLayout, empty_msg: str):
            if not files:
                lbl_e = QLabel(empty_msg)
                lbl_e.setStyleSheet("color: #475569; font-size: 10px; font-style: italic; padding: 2px;")
                target_layout.addWidget(lbl_e)
                return
            for f in files:
                lbl_f = QLabel(f)
                lbl_f.setWordWrap(True)
                lbl_f.setStyleSheet("""
                    color: #cbd5e1;
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 10.5px;
                    background: rgba(255, 255, 255, 0.02);
                    border-radius: 3px;
                    padding: 2px 4px;
                """)
                target_layout.addWidget(lbl_f)

        populate(mod_files, self.mod_list_layout, "Ninguno modificado")
        populate(add_files, self.add_list_layout, "Ninguno añadido")
        populate(del_files, self.del_list_layout, "Ninguno eliminado")

    # Controles de Zoom del Grafo
    def _zoom_in(self):
        if hasattr(self, "git_graph"):
            self.git_graph.zoom_in()

    def _zoom_out(self):
        if hasattr(self, "git_graph"):
            self.git_graph.zoom_out()

    def _zoom_reset(self):
        if hasattr(self, "git_graph"):
            self.git_graph.reset_zoom()

    def _toggle_orientation(self):
        if hasattr(self, "git_graph"):
            new_orient = self.git_graph.toggle_orientation()
            if hasattr(self, "btn_orient"):
                if new_orient == "vertical":
                    self.btn_orient.setText("↕ Vertical")
                else:
                    self.btn_orient.setText("↔ Horizontal")
