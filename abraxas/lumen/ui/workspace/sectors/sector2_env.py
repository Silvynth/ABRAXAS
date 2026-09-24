"""
❖ ABRAXAS 2.0 | Lumen UI: Sector 02 - Runtime, Editores & Docker
Lanzador de entornos de desarrollo, gestión de venvs, dependencias y contenedores.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QGridLayout
)
from PySide6.QtCore import Qt, Signal

from abraxas.lumen.models.project import Project

class Sector2EnvView(QWidget):
    """Sector táctico 02: Entornos virtuales, lanzador de editores y Docker."""
    
    action_requested = Signal(str, dict)
    log_emitted = Signal(str)

    def __init__(self, project: Project = None, parent=None):
        super().__init__(parent)
        self.project = project
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # 1. Cabecera del sector
        card_header = QFrame()
        card_header.setProperty("class", "sector_card")
        ch_layout = QVBoxLayout(card_header)
        ch_layout.setContentsMargins(20, 14, 20, 14)
        ch_layout.setSpacing(4)

        tag = QLabel("SECTOR 02 // RUNTIME, EDITORES & DOCKER")
        tag.setProperty("class", "sector_micro_tag")
        title = QLabel("❖ Entornos de Ejecución & Aislamiento")
        title.setProperty("class", "sector_title")
        
        ch_layout.addWidget(tag)
        ch_layout.addWidget(title)
        layout.addWidget(card_header)

        # 2. Tarjeta de Lanzador de Editores
        editor_box = QFrame()
        editor_box.setProperty("class", "sector_card")
        eb_layout = QVBoxLayout(editor_box)
        eb_layout.setContentsMargins(16, 14, 16, 14)
        eb_layout.setSpacing(10)

        eb_title = QLabel("🚀 Lanzador Rápido de IDEs")
        eb_title.setStyleSheet("color: #ffffff; font-weight: 700; font-size: 13px;")
        eb_layout.addWidget(eb_title)

        editors_row = QHBoxLayout()
        editors_row.setSpacing(8)

        editors = [
            ("💻 VS Code", "code"),
            ("⚡ Cursor", "cursor"),
            ("💎 Zed", "zed"),
            ("🐍 PyCharm", "pycharm"),
            ("📟 Neovim", "nvim")
        ]

        for name, cmd in editors:
            btn = QPushButton(name)
            btn.setProperty("class", "cyber_btn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, c=cmd, n=name: self._launch_editor(c, n))
            editors_row.addWidget(btn)

        editors_row.addStretch()
        eb_layout.addLayout(editors_row)
        layout.addWidget(editor_box)

        # 3. Grid: Entorno Virtual Python (.venv) & Docker
        grid = QGridLayout()
        grid.setSpacing(12)

        # Venv Box
        venv_box = QFrame()
        venv_box.setProperty("class", "sector_card")
        vb_layout = QVBoxLayout(venv_box)
        vb_layout.setContentsMargins(16, 14, 16, 14)
        vb_layout.setSpacing(8)

        self.lbl_venv_status = QLabel("🐍 Python Venv: No detectado")
        self.lbl_venv_status.setStyleSheet("color: #ffffff; font-weight: 700; font-size: 13px;")
        vb_layout.addWidget(self.lbl_venv_status)

        v_actions = QHBoxLayout()
        v_actions.setSpacing(6)

        self.btn_install_reqs = QPushButton("📦 Pip Install Reqs")
        self.btn_install_reqs.setProperty("class", "cyber_btn")
        self.btn_install_reqs.clicked.connect(lambda: self._emit_action("pip_install_requirements"))

        self.btn_freeze = QPushButton("❄ Pip Freeze")
        self.btn_freeze.setProperty("class", "cyber_btn")
        self.btn_freeze.clicked.connect(lambda: self._emit_action("pip_freeze"))

        v_actions.addWidget(self.btn_install_reqs)
        v_actions.addWidget(self.btn_freeze)
        v_actions.addStretch()
        vb_layout.addLayout(v_actions)
        grid.addWidget(venv_box, 0, 0)

        # Docker Box
        docker_box = QFrame()
        docker_box.setProperty("class", "sector_card")
        db_layout = QVBoxLayout(docker_box)
        db_layout.setContentsMargins(16, 14, 16, 14)
        db_layout.setSpacing(8)

        self.lbl_docker_status = QLabel("🐳 Contenedores Docker: Listo")
        self.lbl_docker_status.setStyleSheet("color: #ffffff; font-weight: 700; font-size: 13px;")
        db_layout.addWidget(self.lbl_docker_status)

        d_actions = QHBoxLayout()
        d_actions.setSpacing(6)

        self.btn_docker_list = QPushButton("📋 Listar Contenedores")
        self.btn_docker_list.setProperty("class", "cyber_btn")
        self.btn_docker_list.clicked.connect(lambda: self._emit_action("docker_list"))

        d_actions.addWidget(self.btn_docker_list)
        d_actions.addStretch()
        db_layout.addLayout(d_actions)
        grid.addWidget(docker_box, 0, 1)

        layout.addLayout(grid)
        layout.addStretch()

    def update_project(self, project: Project):
        self.project = project
        if project:
            has_venv = (project.path / ".venv").is_dir() or (project.path / "venv").is_dir()
            v_text = "🐍 Python Venv: Activo (.venv)" if has_venv else "🐍 Python Venv: No detectado"
            self.lbl_venv_status.setText(v_text)

    def _launch_editor(self, cmd: str, name: str):
        self.action_requested.emit("launch_editor", {"editor": cmd})
        self.log_emitted.emit(f"🚀 Abriendo proyecto con {name} ({cmd})...")

    def _emit_action(self, action_name: str):
        self.action_requested.emit(action_name, {})
        self.log_emitted.emit(f"Acción invocada: [{action_name}] en {self.project.name if self.project else 'desconocido'}")
