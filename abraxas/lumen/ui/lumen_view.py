"""
❖ ABRAXAS 2.0 | Lumen UI: Vista Raíz del Dominio Lumen (LumenView)
Enrutador de alta velocidad que alterna entre el Selector de Proyectos y el Workspace Dashboard.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QStackedWidget
from abraxas.core.config import AppConfig
from abraxas.lumen.models.project import Project
from abraxas.lumen.ui.selector.selector_view import LumenSelectorView
from abraxas.lumen.ui.workspace.workspace_view import LumenWorkspaceView

class LumenView(QWidget):
    """Vista principal del dominio Lumen: Enrutador entre Selector y Workspace."""
    
    def __init__(self, cfg: AppConfig = None, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.stack = QStackedWidget()

        # Página 0: Selector de Proyectos
        self.selector_page = LumenSelectorView(self.cfg)
        self.selector_page.project_opened.connect(self.open_workspace)

        # Página 1: Workspace Dashboard
        self.workspace_page = LumenWorkspaceView()
        self.workspace_page.back_to_selector_requested.connect(self.return_to_selector)

        self.stack.addWidget(self.selector_page)
        self.stack.addWidget(self.workspace_page)

        layout.addWidget(self.stack)

    def open_workspace(self, project: Project):
        """Abre el espacio de trabajo para el proyecto seleccionado."""
        self.workspace_page.set_project(project)
        self.stack.setCurrentIndex(1)

    def return_to_selector(self):
        """Regresa a la cuadrícula de selección de repositorios."""
        self.stack.setCurrentIndex(0)
        self.selector_page.load_projects()

    def reload(self):
        """Recarga la lista de proyectos en el selector si está activo."""
        if self.stack.currentIndex() == 0:
            self.selector_page.load_projects()

    def closeEvent(self, event):
        """Propaga el cierre para detener trabajadores en segundo plano."""
        if hasattr(self, "workspace_page"):
            self.workspace_page.close()
        super().closeEvent(event)
