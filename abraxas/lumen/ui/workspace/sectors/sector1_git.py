"""
❖ ABRAXAS 2.0 | Lumen UI: Sector 01 - Protocolo Git & Ciclos de Versión
Control operativo de versiones: ramas, staging interactivo, diffs y commits asistidos por IA.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QLineEdit, QTextEdit, QScrollArea
)
from PySide6.QtCore import Qt, Signal

from abraxas.lumen.models.project import Project

class Sector1GitView(QWidget):
    """Sector táctico 01: Protocolo Git y flujo operativo de trabajo de versiones."""
    
    action_requested = Signal(str, dict)
    log_emitted = Signal(str)

    def __init__(self, project: Project = None, parent=None):
        super().__init__(parent)
        self.project = project
        self.init_ui()

        if self.project:
            self.update_project(self.project)

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(10)

        # 1. Cabecera del sector
        card_header = QFrame()
        card_header.setProperty("class", "sector_card")
        ch_layout = QVBoxLayout(card_header)
        ch_layout.setContentsMargins(16, 12, 16, 12)
        ch_layout.setSpacing(4)

        tag = QLabel("SECTOR 01 // PROTOCOLO GIT & CONTROL DE RAMAS")
        tag.setProperty("class", "sector_micro_tag")
        title = QLabel("❖ Flujo Operativo GitOps & Commits Asistidos")
        title.setProperty("class", "sector_title")
        
        ch_layout.addWidget(tag)
        ch_layout.addWidget(title)
        root_layout.addWidget(card_header)

        # Scroll general del sector
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        content = QWidget()
        c_layout = QVBoxLayout(content)
        c_layout.setContentsMargins(0, 0, 4, 0)
        c_layout.setSpacing(10)

        # 2. Barra de botones tácticos de acción rápida
        actions_frame = QFrame()
        actions_frame.setProperty("class", "sector_card")
        act_layout = QHBoxLayout(actions_frame)
        act_layout.setContentsMargins(12, 10, 12, 10)
        act_layout.setSpacing(8)

        self.btn_stage_all = QPushButton("📌 Stage All")
        self.btn_stage_all.setProperty("class", "cyber_btn")
        self.btn_stage_all.clicked.connect(lambda: self._emit_action("stage_all"))

        self.btn_ai_commit = QPushButton("✨ Proponer con IA")
        self.btn_ai_commit.setProperty("class", "cyber_btn_primary")
        self.btn_ai_commit.clicked.connect(lambda: self._emit_action("ai_commit_proposal"))

        self.btn_push = QPushButton("⬆ Push")
        self.btn_push.setProperty("class", "cyber_btn")
        self.btn_push.clicked.connect(lambda: self._emit_action("git_push"))

        self.btn_pull = QPushButton("⬇ Pull")
        self.btn_pull.setProperty("class", "cyber_btn")
        self.btn_pull.clicked.connect(lambda: self._emit_action("git_pull"))

        act_layout.addWidget(self.btn_stage_all)
        act_layout.addWidget(self.btn_ai_commit)
        act_layout.addWidget(self.btn_push)
        act_layout.addWidget(self.btn_pull)
        c_layout.addWidget(actions_frame)

        # 3. Control de Ramas
        branch_card = QFrame()
        branch_card.setProperty("class", "sector_card")
        b_layout = QVBoxLayout(branch_card)
        b_layout.setContentsMargins(14, 12, 14, 12)
        b_layout.setSpacing(8)

        lbl_b_title = QLabel("🌿 Control de Ramas")
        lbl_b_title.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: 800;")
        b_layout.addWidget(lbl_b_title)

        branch_row = QHBoxLayout()
        self.lbl_active_branch = QLabel("Rama activa: main")
        self.lbl_active_branch.setStyleSheet("color: #94a3b8; font-size: 11px;")
        branch_row.addWidget(self.lbl_active_branch)
        branch_row.addStretch()

        self.btn_new_branch = QPushButton("➕ Nueva Rama")
        self.btn_new_branch.setProperty("class", "cyber_btn")
        self.btn_new_branch.setFixedHeight(24)
        self.btn_new_branch.clicked.connect(lambda: self._emit_action("new_branch_dialog"))
        branch_row.addWidget(self.btn_new_branch)
        b_layout.addLayout(branch_row)

        c_layout.addWidget(branch_card)

        # 4. Redactor de Commits
        commit_card = QFrame()
        commit_card.setProperty("class", "sector_card")
        cm_layout = QVBoxLayout(commit_card)
        cm_layout.setContentsMargins(14, 12, 14, 12)
        cm_layout.setSpacing(8)

        lbl_cm_title = QLabel("✍️ Redactor de Commits")
        lbl_cm_title.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: 800;")
        cm_layout.addWidget(lbl_cm_title)

        self.txt_commit_msg = QTextEdit()
        self.txt_commit_msg.setPlaceholderText("Escribe el mensaje del commit o genera una propuesta con IA...")
        self.txt_commit_msg.setFixedHeight(75)
        self.txt_commit_msg.setStyleSheet("""
            QTextEdit {
                background: #08090b;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                color: #ffffff;
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
                padding: 6px;
            }
        """)
        cm_layout.addWidget(self.txt_commit_msg)

        cm_btn_row = QHBoxLayout()
        cm_btn_row.addStretch()
        self.btn_commit = QPushButton("🚀 Confirmar Commit")
        self.btn_commit.setProperty("class", "cyber_btn_primary")
        self.btn_commit.setFixedHeight(28)
        self.btn_commit.clicked.connect(self._submit_commit)
        cm_btn_row.addWidget(self.btn_commit)
        cm_layout.addLayout(cm_btn_row)

        c_layout.addWidget(commit_card)

        scroll.setWidget(content)
        root_layout.addWidget(scroll, 1)

    def update_project(self, project: Project):
        self.project = project
        branch = project.current_branch if project and project.current_branch else "main"
        self.lbl_active_branch.setText(f"Rama activa: <b>{branch}</b>")

    def _submit_commit(self):
        msg = self.txt_commit_msg.toPlainText().strip()
        if msg:
            self._emit_action("git_commit", {"message": msg})
            self.txt_commit_msg.clear()

    def _emit_action(self, action_name: str, payload: dict = None):
        data = payload or {}
        self.action_requested.emit(action_name, data)
        self.log_emitted.emit(f"Acción Git disparada: <b>{action_name}</b>")
