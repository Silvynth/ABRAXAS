"""
❖ ABRAXAS 2.0 | Lumen UI: Vista del Selector de Proyectos
Panel interactivo para explorar, filtrar y abrir espacios de trabajo de desarrollo.
"""

from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, Signal

from abraxas.core.config import AppConfig, load_config
from abraxas.core.semver import detect_project_semver
from abraxas.core.process import run_command
from abraxas.lumen.models.project import Project
from abraxas.lumen.ui.selector.project_row import ProjectSelectorRow

class LumenSelectorView(QWidget):
    """Selector de proyectos de Lumen con filtrado en vivo y acceso al Workspace."""
    
    project_opened = Signal(Project)

    def __init__(self, cfg: AppConfig = None, parent=None):
        super().__init__(parent)
        self.cfg = cfg or load_config()
        self.projects: list[Project] = []
        self.rows: list[tuple[Project, ProjectSelectorRow]] = []
        self.selected_project: Project | None = None

        self.init_ui()
        self.load_projects()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # 1. Cabecera táctica
        header = QFrame()
        header.setProperty("class", "sector_card")
        h_layout = QVBoxLayout(header)
        h_layout.setContentsMargins(20, 16, 20, 16)
        h_layout.setSpacing(6)

        tag = QLabel("MOTOR DEV // SELECTOR DE PROYECTOS")
        tag.setProperty("class", "sector_micro_tag")
        
        title = QLabel("❖ LUMEN: Espacios de Trabajo")
        title.setProperty("class", "sector_title")

        desc = QLabel(
            "Haz doble clic en cualquier repositorio para desplegar su panel de control "
            "táctico (GitOps, Entornos de ejecución y Utilidades IA)."
        )
        desc.setProperty("class", "sector_desc")

        h_layout.addWidget(tag)
        h_layout.addWidget(title)
        h_layout.addWidget(desc)
        layout.addWidget(header)

        # 2. Barra de búsqueda y controles
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(10)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Filtrar repositorios por nombre o ruta...")
        self.txt_search.setStyleSheet(
            "background-color: #0c0d10; border: 1px solid rgba(255, 255, 255, 0.08); "
            "border-radius: 8px; padding: 10px 14px; color: #ffffff; font-size: 13px;"
        )
        self.txt_search.textChanged.connect(self.filter_projects)
        filter_bar.addWidget(self.txt_search, 1)

        self.btn_refresh = QPushButton("🔄 Recargar")
        self.btn_refresh.setProperty("class", "cyber_btn")
        self.btn_refresh.clicked.connect(self.load_projects)
        filter_bar.addWidget(self.btn_refresh)

        self.lbl_count = QLabel("0 proyectos")
        self.lbl_count.setStyleSheet(
            "background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.08); "
            "border-radius: 6px; padding: 6px 12px; color: #94a3b8; font-family: 'JetBrains Mono', monospace; font-size: 11px;"
        )
        filter_bar.addWidget(self.lbl_count)

        layout.addLayout(filter_bar)

        # 3. Lista con scroll
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")

        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 6, 0)
        self.container_layout.setSpacing(8)

        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll, 1)

        # 4. Barra inferior de acción
        bottom_bar = QHBoxLayout()
        self.btn_open_workspace = QPushButton("🚀 Abrir Espacio de Trabajo")
        self.btn_open_workspace.setProperty("class", "cyber_btn_primary")
        self.btn_open_workspace.setEnabled(False)
        self.btn_open_workspace.clicked.connect(self._on_open_clicked)

        bottom_bar.addStretch()
        bottom_bar.addWidget(self.btn_open_workspace)
        layout.addLayout(bottom_bar)

    def load_projects(self):
        """Escanea los proyectos en el directorio de desarrollo configurado."""
        # Limpiar contenedor existente
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        self.projects.clear()
        self.rows.clear()
        self.selected_project = None
        self.btn_open_workspace.setEnabled(False)

        p_dir = self.cfg.paths.projects_dir
        if not p_dir.is_dir():
            lbl_empty = QLabel(f"⚠️ El directorio de proyectos no existe: {p_dir}")
            lbl_empty.setStyleSheet("color: #64748b; font-size: 13px; padding: 20px;")
            self.container_layout.addWidget(lbl_empty)
            self.lbl_count.setText("0 proyectos")
            return

        for entry in sorted(p_dir.iterdir(), key=lambda p: p.name.lower()):
            if not entry.is_dir() or entry.name.startswith("."):
                continue

            # Detectar si es repositorio Git
            is_git = (entry / ".git").is_dir()
            current_branch = ""
            is_dirty = False
            total_changes = 0

            if is_git:
                b_res = run_command(["git", "branch", "--show-current"], cwd=entry)
                current_branch = b_res.stdout.strip() or "HEAD (detached)"
                
                s_res = run_command(["git", "status", "--porcelain"], cwd=entry)
                lines = [l for l in s_res.stdout.splitlines() if l.strip()]
                is_dirty = len(lines) > 0
                total_changes = len(lines)

            # Detectar SemVer
            semver = detect_project_semver(entry)

            proj = Project(
                path=entry,
                name=entry.name,
                is_git=is_git,
                current_branch=current_branch,
                semver=semver.lstrip("vV"),
                is_dirty=is_dirty,
                unstaged_count=total_changes
            )
            self.projects.append(proj)

            row = ProjectSelectorRow(proj)
            row.selected.connect(self._on_row_selected)
            row.double_clicked.connect(self._on_row_double_clicked)

            self.rows.append((proj, row))
            self.container_layout.addWidget(row)

        self.container_layout.addStretch()
        self.lbl_count.setText(f"{len(self.projects)} proyectos")

    def filter_projects(self, text: str):
        query = text.strip().lower()
        visible_count = 0
        for proj, row in self.rows:
            match = query in proj.name.lower() or query in str(proj.path).lower()
            row.setVisible(match)
            if match:
                visible_count += 1
        self.lbl_count.setText(f"{visible_count} proyectos")

    def _on_row_selected(self, project: Project):
        self.selected_project = project
        self.btn_open_workspace.setEnabled(True)
        for p, r in self.rows:
            r.set_selected(p.path == project.path)

    def _on_row_double_clicked(self, project: Project):
        self.selected_project = project
        self.project_opened.emit(project)

    def _on_open_clicked(self):
        if self.selected_project:
            self.project_opened.emit(self.selected_project)
