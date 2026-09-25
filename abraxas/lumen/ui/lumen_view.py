"""
❖ ABRAXAS 2.0 | Lumen UI: Vista Raíz del Dominio Lumen (LumenView)
Enrutador de alta velocidad que alterna entre el Selector de Proyectos y el Workspace Dashboard.
"""

import gc
from typing import Optional
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
        self.workspace_page: Optional[LumenWorkspaceView] = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.stack = QStackedWidget()

        # Página 0: Selector de Proyectos
        self.selector_page = LumenSelectorView(self.cfg)
        self.selector_page.project_opened.connect(self.open_workspace)
        self.stack.addWidget(self.selector_page)

        layout.addWidget(self.stack)

    def open_workspace(self, project: Project):
        """Abre el espacio de trabajo iniciando una instancia completamente fresca y optimizada."""
        self._purge_workspace()

        self.workspace_page = LumenWorkspaceView(project)
        self.workspace_page.back_to_selector_requested.connect(self.return_to_selector)
        self.stack.addWidget(self.workspace_page)
        self.stack.setCurrentWidget(self.workspace_page)

    def return_to_selector(self):
        """Regresa a la cuadrícula de proyectos finalizando todos los procesos y liberando memoria."""
        self.stack.setCurrentIndex(0)
        self._purge_workspace()
        self.selector_page.load_projects()

    def _purge_workspace(self):
        """Finaliza todos los procesos en segundo plano, hilos, watchers y destruye el workspace previo."""
        if self.workspace_page is not None:
            try:
                self.workspace_page.teardown()
                self.stack.removeWidget(self.workspace_page)
                self.workspace_page.deleteLater()
            except Exception:
                pass
            finally:
                self.workspace_page = None
                gc.collect()

    def reload(self):
        """Recarga la lista de proyectos en el selector si está activo."""
        if self.stack.currentIndex() == 0:
            self.selector_page.load_projects()

    def closeEvent(self, event):
        """Propaga el cierre para detener trabajadores en segundo plano."""
        self._purge_workspace()
        super().closeEvent(event)
