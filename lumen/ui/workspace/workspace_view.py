"""
❖ ABRAXAS 2.0 | Lumen UI: Orquestador del Espacio de Trabajo (Workspace View)
Integra:
- Panel Superior (HUD Dual con contexto y telemetría de hardware).
- Barra de navegación táctica (SectorSwitcherPill).
- Sector 00: Topología, Grafo vertical de toda la altura, Commits, Autores y Archivos Modificados/Añadidos/Eliminados.
- Sectores 01, 02, 03: Dominios dedicados de GitOps, Entornos/Runtime e IA.
- CyberTerminal inferior unificada y compartida con Umbra.
"""

from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QStackedWidget
)
from PySide6.QtCore import Qt, Signal, QTimer, QFileSystemWatcher

from core.process import run_command
from core.semver import detect_project_semver
from lumen.models.project import Project
from lumen.ui.workspace.project_hud import ProjectHud
from lumen.ui.workspace.sectors.sector0_overview import Sector0OverviewView
from lumen.ui.workspace.sectors.sector1_git import Sector1GitView
from lumen.ui.workspace.sectors.sector2_env import Sector2EnvView
from lumen.ui.workspace.sectors.sector3_ai import Sector3AiView
from ui.controls.switcher_pill import SectorSwitcherPill
from ui.terminal.cyber_terminal import CyberTerminal

class LumenWorkspaceView(QWidget):
    """Orquestador central del panel de desarrollo táctico para un proyecto activo."""
    
    back_to_selector_requested = Signal()

    def __init__(self, project: Project = None, parent=None):
        super().__init__(parent)
        self.project = project
        self.init_ui()

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(10)

        # -------------------------------------------------------------
        # 1. PANEL SUPERIOR DEL PROYECTO (HUD DUAL - CONSERVADO)
        # -------------------------------------------------------------
        self.hud = ProjectHud(self.project)
        self.hud.back_requested.connect(self.back_to_selector_requested.emit)
        self.hud.refresh_requested.connect(self.refresh_project)
        root_layout.addWidget(self.hud)

        # -------------------------------------------------------------
        # 2. SELECTOR DE VISTA (Pill Switcher: Sector 0 a Sector 3)
        # -------------------------------------------------------------
        self.pill_nav = SectorSwitcherPill()
        self.pill_nav.sector_changed.connect(self.switch_sector_view)
        root_layout.addWidget(self.pill_nav)

        # -------------------------------------------------------------
        # 3. ZONA DINÁMICA DE SECTORES (QStackedWidget)
        # -------------------------------------------------------------
        self.main_stack = QStackedWidget()

        # Sector 00: Panorama Ejecutivo (Grafo vertical + Commits/Autores + Archivos)
        self.sector0 = Sector0OverviewView(self.project)
        self.sector0.log_emitted.connect(self._on_log_emitted)
        self.sector0.action_requested.connect(self._on_action_requested)
        self.main_stack.addWidget(self.sector0)

        # Sector 01: Protocolo Git y Operaciones
        self.sector1 = Sector1GitView(self.project)
        self.sector1.log_emitted.connect(self._on_log_emitted)
        self.sector1.action_requested.connect(self._on_action_requested)
        self.main_stack.addWidget(self.sector1)

        # Sector 02: Entornos & Runtime
        self.sector2 = Sector2EnvView(self.project)
        self.sector2.log_emitted.connect(self._on_log_emitted)
        self.sector2.action_requested.connect(self._on_action_requested)
        self.main_stack.addWidget(self.sector2)

        # Sector 03: Herramientas & IA Local
        self.sector3 = Sector3AiView(self.project)
        self.sector3.log_emitted.connect(self._on_log_emitted)
        self.sector3.action_requested.connect(self._on_action_requested)
        self.main_stack.addWidget(self.sector3)

        root_layout.addWidget(self.main_stack, 1)

        # -------------------------------------------------------------
        # 4. TERMINAL TÁCTICA INTERACTIVA INFERIOR (COMPARTIDA CON UMBRA)
        # -------------------------------------------------------------
        proj_name = self.project.name if self.project else "workspace"
        self.terminal = CyberTerminal(prompt=f"lumen@{proj_name}:~$")
        self.terminal.state_changed.connect(self._on_terminal_state_changed)
        root_layout.addWidget(self.terminal)

        # -------------------------------------------------------------
        # 5. MOTOR DE REACTIVIDAD Y SINCRONIZACIÓN AUTOMÁTICA EN VIVO
        # -------------------------------------------------------------
        self.sync_debounce_timer = QTimer(self)
        self.sync_debounce_timer.setSingleShot(True)
        self.sync_debounce_timer.setInterval(300)
        self.sync_debounce_timer.timeout.connect(self.sync_workspace)

        self.fs_watcher = QFileSystemWatcher(self)
        self.fs_watcher.fileChanged.connect(self._schedule_sync)
        self.fs_watcher.directoryChanged.connect(self._schedule_sync)

        # Reactividad ante comandos en la terminal integrada (cd, checkout, add, commit, etc.)
        self.terminal.sync_requested.connect(self._schedule_sync)
        self.terminal.process_finished.connect(lambda _: self._schedule_sync())

        if self.project and self.project.path:
            self.terminal.set_working_directory(str(self.project.path))
            self._setup_fs_watcher(Path(self.project.path))

    def _setup_fs_watcher(self, path: Path):
        """Configura o renueva las rutas monitorizadas por QFileSystemWatcher."""
        if not hasattr(self, "fs_watcher") or not path or not path.is_dir():
            return

        existing = self.fs_watcher.files() + self.fs_watcher.directories()
        if existing:
            self.fs_watcher.removePaths(existing)

        to_watch = [str(path)]
        git_dir = path / ".git"
        if git_dir.is_dir():
            to_watch.append(str(git_dir))
            head_file = git_dir / "HEAD"
            if head_file.exists():
                to_watch.append(str(head_file))
            index_file = git_dir / "index"
            if index_file.exists():
                to_watch.append(str(index_file))
            refs_heads = git_dir / "refs" / "heads"
            if refs_heads.is_dir():
                to_watch.append(str(refs_heads))

        for p in to_watch:
            try:
                self.fs_watcher.addPath(p)
            except Exception:
                pass

    def _schedule_sync(self, *args):
        """Programa una sincronización debounced evitando saturación de eventos."""
        if self.project and self.project.path:
            self.sync_debounce_timer.start()

    def sync_workspace(self):
        """Actualiza silenciosamente el estado del proyecto y todos los sectores en vivo."""
        if not self.project or not self.project.path or not self.project.path.is_dir():
            return

        path = self.project.path
        is_git = (path / ".git").is_dir()
        current_branch = ""
        is_dirty = False
        staged = 0
        unstaged = 0
        untracked = 0

        if is_git:
            b_res = run_command(["git", "branch", "--show-current"], cwd=path)
            current_branch = b_res.stdout.strip() or "HEAD (detached)"

            s_res = run_command(["git", "status", "--porcelain"], cwd=path)
            lines = [l for l in s_res.stdout.splitlines() if l.strip()]
            is_dirty = len(lines) > 0
            for l in lines:
                if len(l) >= 2:
                    if l.startswith("??"):
                        untracked += 1
                    else:
                        if l[0] != " ":
                            staged += 1
                        if l[1] != " ":
                            unstaged += 1

        semver = detect_project_semver(path)

        # Actualizar entidad de datos
        self.project.is_git = is_git
        self.project.current_branch = current_branch
        self.project.semver = semver.lstrip("vV")
        self.project.is_dirty = is_dirty
        self.project.staged_count = staged
        self.project.unstaged_count = unstaged
        self.project.untracked_count = untracked

        # Re-sincronizar sectores y HUD
        self.hud.update_project(self.project)
        self.sector0.update_project(self.project)
        self.sector1.update_project(self.project)
        self.sector2.update_project(self.project)
        self.sector3.update_project(self.project)

        # Re-asegurar rutas vigiladas si el FS eliminó o recreó ficheros
        self._setup_fs_watcher(path)

    def set_project(self, project: Project):
        """Asigna un nuevo proyecto activo y sincroniza todos los componentes."""
        self.project = project
        self.hud.update_project(project)
        self.sector0.update_project(project)
        self.sector1.update_project(project)
        self.sector2.update_project(project)
        self.sector3.update_project(project)
        self.terminal.set_prompt(f"lumen@{project.name}:~$")
        if project and project.path:
            self.terminal.set_working_directory(str(project.path))
            self._setup_fs_watcher(Path(project.path))
        self.terminal.log_success("WORKSPACE", f"Espacio de trabajo montado para <b>{project.name}</b> (v{project.semver})")

    def switch_sector_view(self, index: int):
        """Alterna entre el Sector 0 (Topología/Estado) y los sectores 1, 2, 3."""
        self.main_stack.setCurrentIndex(index)
        sector_names = [
            "SECTOR 00: TOPOLOGÍA & ESTADO",
            "SECTOR 01: PROTOCOLO GIT",
            "SECTOR 02: RUNTIME & ENTORNOS",
            "SECTOR 03: HERRAMIENTAS & IA"
        ]
        if 0 <= index < len(sector_names):
            self.terminal.log_info("NAV", f"Navegando a: {sector_names[index]}")

    def refresh_project(self):
        """Refresco manual disparado por el botón Sincronizar del HUD."""
        if self.project:
            self.sync_workspace()
            self.terminal.log_info("HUD", "Telemetría del proyecto y ramas sincronizada con éxito.")

    def _on_terminal_state_changed(self, mode: str):
        """Oculta los sectores si la terminal se maximiza al 100% de la vista."""
        if mode == "maximized":
            self.main_stack.setVisible(False)
            self.pill_nav.setVisible(False)
        else:
            self.main_stack.setVisible(True)
            self.pill_nav.setVisible(True)

    def _on_log_emitted(self, msg: str):
        self.terminal.append_log(msg)

    def _on_action_requested(self, action: str, data: dict):
        self.terminal.log_info("ACTION", f"Comando disparado: <b>{action}</b> {data if data else ''}")

    def teardown(self):
        """Finaliza todos los procesos en segundo plano, hilos, watchers y timers al salir del proyecto."""
        # 1. Detener timer de sincronización
        if hasattr(self, "sync_debounce_timer") and self.sync_debounce_timer.isActive():
            self.sync_debounce_timer.stop()

        # 2. Desregistrar rutas de vigilancia del filesystem
        if hasattr(self, "fs_watcher"):
            existing = self.fs_watcher.files() + self.fs_watcher.directories()
            if existing:
                self.fs_watcher.removePaths(existing)

        # 3. Finalizar hilos y timers del HUD
        if hasattr(self, "hud") and self.hud:
            self.hud.teardown()

        # 4. Finalizar cualquier proceso activo en la CyberTerminal
        if hasattr(self, "terminal") and self.terminal:
            self.terminal.shutdown()

        # 5. Teardown en sectores
        for sector in [getattr(self, f"sector{i}", None) for i in range(4)]:
            if sector and hasattr(sector, "teardown"):
                try:
                    sector.teardown()
                except Exception:
                    pass

        # 6. Desactivar venv de Python si estaba activo en la sesión
        try:
            from core.environments import deactivate_python_venv
            deactivate_python_venv()
        except Exception:
            pass

        self.project = None

    def closeEvent(self, event):
        """Detiene de forma limpia los hilos y temporizadores al cerrar."""
        self.teardown()
        super().closeEvent(event)
