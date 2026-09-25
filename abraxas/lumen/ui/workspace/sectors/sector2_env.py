"""
❖ ABRAXAS 2.0 | Lumen UI: Sector 02 - Runtime, Editores & Docker
Lanzador de entornos de desarrollo, gestión de venvs, dependencias, puertos activos y contenedores Docker.
Estructura en 3 Paneles:
- Panel Izquierdo (Vertical): Docker & Compose (estado del daemon, compose actions, lista de contenedores y acciones).
- Panel Central (Apilado Vertical):
  - Superior: Entornos Python (venv activo/inactivo, versión, creación, pip install, pip freeze, lista de paquetes).
  - Inferior: Puertos Activos del Sistema (puertos en escucha, proceso, PID, abrir en navegador, matar proceso).
- Panel Derecho (Vertical): Lista de IDEs / Editores instalados (VS Code, Cursor, Zed, PyCharm, Neovim, etc., abrir proyecto y fijar preferido).
"""

import os
import shutil
import webbrowser
from pathlib import Path
from typing import Optional, List, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QSplitter, QLineEdit, QDialog,
    QMessageBox, QTextEdit, QSizePolicy, QCheckBox,
    QStackedWidget, QButtonGroup, QApplication
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor, QTextCursor

from abraxas.lumen.models.project import Project
from core.environments import (
    detect_installed_editors, get_preferred_editor, set_preferred_editor, launch_project_in_editor,
    inspect_python_venv, activate_python_venv, deactivate_python_venv, create_python_venv,
    install_project_dependencies, install_custom_packages, uninstall_package, freeze_dependencies_to_file,
    list_installed_packages, inspect_docker_status, list_docker_containers,
    execute_docker_container_action, get_docker_container_logs, execute_docker_prune,
    execute_compose_action, inspect_network_ports, kill_process_by_pid
)


class Sector2EnvView(QWidget):
    """
    Sector táctico 02: Entornos virtuales, lanzador de editores, Docker y puertos activos.
    Diseño en 3 Columnas:
    1. Docker (Vertical Izquierda)
    2. Entornos Python & Puertos Activos (Apilados en el Centro)
    3. Lista de IDEs / Editores (Vertical Derecha)
    """

    action_requested = Signal(str, dict)
    log_emitted = Signal(str)

    def __init__(self, project: Project = None, parent=None):
        super().__init__(parent)
        self.project = project
        self._installed_packages_cache: List[tuple[str, str]] = []
        self.current_logs_target: Optional[str] = None
        self.current_logs_is_compose: bool = False
        self.init_ui()

        if self.project:
            self.update_project(self.project)

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Splitter principal horizontal de 3 paneles
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setChildrenCollapsible(False)

        # =============================================================
        # 1. PANEL IZQUIERDO (VERTICAL): DOCKER & COMPOSE
        # =============================================================
        card_docker = QFrame()
        card_docker.setProperty("class", "sector_card")
        docker_layout = QVBoxLayout(card_docker)
        docker_layout.setContentsMargins(14, 12, 14, 12)
        docker_layout.setSpacing(10)

        # Encabezado Docker
        d_header = QHBoxLayout()
        d_box = QVBoxLayout()
        d_box.setSpacing(2)
        lbl_d_tag = QLabel("VIRTUALIZACIÓN // DOCKER")
        lbl_d_tag.setProperty("class", "sector_micro_tag")
        lbl_d_title = QLabel("🐳 Docker & Compose Engine")
        lbl_d_title.setProperty("class", "sector_title")
        d_box.addWidget(lbl_d_tag)
        d_box.addWidget(lbl_d_title)
        d_header.addLayout(d_box)

        d_header.addStretch()

        self.btn_refresh_docker = QPushButton("🔄")
        self.btn_refresh_docker.setProperty("class", "cyber_btn_compact")
        self.btn_refresh_docker.setFixedSize(28, 28)
        self.btn_refresh_docker.setCursor(Qt.PointingHandCursor)
        self.btn_refresh_docker.setToolTip("Refrescar estado de Docker y contenedores")
        self.btn_refresh_docker.clicked.connect(self._refresh_docker)
        d_header.addWidget(self.btn_refresh_docker)

        self.btn_docker_prune = QPushButton("🧹")
        self.btn_docker_prune.setProperty("class", "cyber_btn_compact")
        self.btn_docker_prune.setFixedSize(28, 28)
        self.btn_docker_prune.setCursor(Qt.PointingHandCursor)
        self.btn_docker_prune.setToolTip("Ejecutar Docker System Prune (limpiar recursos huérfanos)")
        self.btn_docker_prune.clicked.connect(self._execute_docker_prune_dialog)
        d_header.addWidget(self.btn_docker_prune)

        docker_layout.addLayout(d_header)

        # Selector de Sub-sector: Engine vs Logs
        sub_row = QHBoxLayout()
        sub_row.setSpacing(6)

        self.docker_sub_group = QButtonGroup(self)
        self.docker_sub_group.setExclusive(True)

        self.btn_sub_engine = QPushButton("🐳 Engine")
        self.btn_sub_engine.setCheckable(True)
        self.btn_sub_engine.setChecked(True)
        self.btn_sub_engine.setProperty("class", "cyber_btn_toggle")
        self.btn_sub_engine.setCursor(Qt.PointingHandCursor)
        self.btn_sub_engine.setToolTip("Ver contenedores, compose y controles de ejecución")
        self.btn_sub_engine.clicked.connect(lambda: self._switch_docker_subview(0))
        self.docker_sub_group.addButton(self.btn_sub_engine, 0)
        sub_row.addWidget(self.btn_sub_engine)

        self.btn_sub_logs = QPushButton("📜 Logs")
        self.btn_sub_logs.setCheckable(True)
        self.btn_sub_logs.setProperty("class", "cyber_btn_toggle")
        self.btn_sub_logs.setCursor(Qt.PointingHandCursor)
        self.btn_sub_logs.setToolTip("Terminal táctica de registros de Docker")
        self.btn_sub_logs.clicked.connect(lambda: self._switch_docker_subview(1))
        self.docker_sub_group.addButton(self.btn_sub_logs, 1)
        sub_row.addWidget(self.btn_sub_logs)

        sub_row.addStretch()
        docker_layout.addLayout(sub_row)

        # Stacked Widget con 2 páginas: 0 = Engine, 1 = Terminal de Logs
        self.docker_stack = QStackedWidget()

        # -------------------------------------------------------------
        # PÁGINA 0: DOCKER ENGINE (CONTENEDORES & COMPOSE)
        # -------------------------------------------------------------
        self.docker_engine_page = QWidget()
        engine_layout = QVBoxLayout(self.docker_engine_page)
        engine_layout.setContentsMargins(0, 0, 0, 0)
        engine_layout.setSpacing(8)

        # Barra de estado del daemon
        d_status_row = QHBoxLayout()
        d_status_row.setSpacing(6)
        self.lbl_docker_daemon = QLabel("○ Daemon Inactivo")
        self.lbl_docker_daemon.setProperty("class", "badge_pending")
        d_status_row.addWidget(self.lbl_docker_daemon)

        self.lbl_docker_compose_badge = QLabel("Sin Compose")
        self.lbl_docker_compose_badge.setProperty("class", "badge_telemetry")
        d_status_row.addWidget(self.lbl_docker_compose_badge)
        d_status_row.addStretch()
        engine_layout.addLayout(d_status_row)

        # Acciones de Docker Compose (si el proyecto tiene compose)
        self.compose_actions_box = QFrame()
        self.compose_actions_box.setProperty("class", "env_item_row")
        c_act_layout = QVBoxLayout(self.compose_actions_box)
        c_act_layout.setContentsMargins(8, 6, 8, 6)
        c_act_layout.setSpacing(6)

        self.lbl_compose_file = QLabel("Docker Compose:")
        self.lbl_compose_file.setProperty("class", "sector_desc")
        c_act_layout.addWidget(self.lbl_compose_file)

        c_btns = QHBoxLayout()
        c_btns.setSpacing(6)

        self.btn_compose_up = QPushButton("🚀 Up")
        self.btn_compose_up.setProperty("class", "cyber_btn_compact")
        self.btn_compose_up.setCursor(Qt.PointingHandCursor)
        self.btn_compose_up.setToolTip("docker compose up -d")
        self.btn_compose_up.clicked.connect(lambda: self._trigger_compose_action("up"))
        c_btns.addWidget(self.btn_compose_up)

        self.btn_compose_down = QPushButton("⏹ Down")
        self.btn_compose_down.setProperty("class", "cyber_btn_compact")
        self.btn_compose_down.setCursor(Qt.PointingHandCursor)
        self.btn_compose_down.setToolTip("docker compose down")
        self.btn_compose_down.clicked.connect(lambda: self._trigger_compose_action("down"))
        c_btns.addWidget(self.btn_compose_down)

        self.btn_compose_restart = QPushButton("🔄 Restart")
        self.btn_compose_restart.setProperty("class", "cyber_btn_compact")
        self.btn_compose_restart.setCursor(Qt.PointingHandCursor)
        self.btn_compose_restart.setToolTip("docker compose restart")
        self.btn_compose_restart.clicked.connect(lambda: self._trigger_compose_action("restart"))
        c_btns.addWidget(self.btn_compose_restart)

        self.btn_compose_logs = QPushButton("📜 Logs")
        self.btn_compose_logs.setProperty("class", "cyber_btn_compact")
        self.btn_compose_logs.setCursor(Qt.PointingHandCursor)
        self.btn_compose_logs.setToolTip("Ver registros de docker compose en la terminal")
        self.btn_compose_logs.clicked.connect(self._show_compose_logs)
        c_btns.addWidget(self.btn_compose_logs)

        c_btns.addStretch()
        c_act_layout.addLayout(c_btns)
        engine_layout.addWidget(self.compose_actions_box)
        self.compose_actions_box.setVisible(False)

        # Encabezado lista de contenedores
        c_list_head = QHBoxLayout()
        lbl_c_list_title = QLabel("Contenedores:")
        lbl_c_list_title.setProperty("class", "sector_desc")
        c_list_head.addWidget(lbl_c_list_title)
        c_list_head.addStretch()

        self.lbl_containers_count = QLabel("0 contenedores")
        self.lbl_containers_count.setProperty("class", "badge_telemetry")
        c_list_head.addWidget(self.lbl_containers_count)
        engine_layout.addLayout(c_list_head)

        # Lista scrolleable de contenedores
        scroll_containers = QScrollArea()
        scroll_containers.setProperty("class", "clean_scroll")
        scroll_containers.setWidgetResizable(True)

        self.containers_container = QWidget()
        self.containers_layout = QVBoxLayout(self.containers_container)
        self.containers_layout.setContentsMargins(0, 0, 0, 0)
        self.containers_layout.setSpacing(6)
        scroll_containers.setWidget(self.containers_container)
        engine_layout.addWidget(scroll_containers, 1)

        self.docker_stack.addWidget(self.docker_engine_page)

        # -------------------------------------------------------------
        # PÁGINA 1: DOCKER LOGS TERMINAL (SIN INTERACCIÓN)
        # -------------------------------------------------------------
        self.docker_logs_page = QWidget()
        logs_layout = QVBoxLayout(self.docker_logs_page)
        logs_layout.setContentsMargins(0, 0, 0, 0)
        logs_layout.setSpacing(6)

        # Barra superior de la terminal de logs
        logs_toolbar = QHBoxLayout()
        logs_toolbar.setSpacing(6)

        self.btn_back_to_engine = QPushButton("← Contenedores")
        self.btn_back_to_engine.setProperty("class", "cyber_btn_compact")
        self.btn_back_to_engine.setCursor(Qt.PointingHandCursor)
        self.btn_back_to_engine.setToolTip("Volver al gestor de contenedores")
        self.btn_back_to_engine.clicked.connect(lambda: self._switch_docker_subview(0))
        logs_toolbar.addWidget(self.btn_back_to_engine)

        self.lbl_terminal_title = QLabel("Logs: -")
        self.lbl_terminal_title.setProperty("class", "badge_telemetry")
        logs_toolbar.addWidget(self.lbl_terminal_title)

        logs_toolbar.addStretch()

        self.btn_refresh_terminal_logs = QPushButton("🔄")
        self.btn_refresh_terminal_logs.setProperty("class", "cyber_btn_compact")
        self.btn_refresh_terminal_logs.setFixedSize(28, 28)
        self.btn_refresh_terminal_logs.setCursor(Qt.PointingHandCursor)
        self.btn_refresh_terminal_logs.setToolTip("Refrescar registros")
        self.btn_refresh_terminal_logs.clicked.connect(self._refresh_active_logs)
        logs_toolbar.addWidget(self.btn_refresh_terminal_logs)

        self.btn_copy_terminal_logs = QPushButton("📋")
        self.btn_copy_terminal_logs.setProperty("class", "cyber_btn_compact")
        self.btn_copy_terminal_logs.setFixedSize(28, 28)
        self.btn_copy_terminal_logs.setCursor(Qt.PointingHandCursor)
        self.btn_copy_terminal_logs.setToolTip("Copiar registros al portapapeles")
        self.btn_copy_terminal_logs.clicked.connect(self._copy_terminal_logs)
        logs_toolbar.addWidget(self.btn_copy_terminal_logs)

        self.btn_clear_terminal_logs = QPushButton("🗑")
        self.btn_clear_terminal_logs.setProperty("class", "cyber_btn_compact")
        self.btn_clear_terminal_logs.setFixedSize(28, 28)
        self.btn_clear_terminal_logs.setCursor(Qt.PointingHandCursor)
        self.btn_clear_terminal_logs.setToolTip("Limpiar registros de la pantalla")
        self.btn_clear_terminal_logs.clicked.connect(self._clear_terminal_logs)
        logs_toolbar.addWidget(self.btn_clear_terminal_logs)

        logs_layout.addLayout(logs_toolbar)

        # Terminal única sin interacción (Read-only, monospace)
        self.txt_docker_terminal = QTextEdit()
        self.txt_docker_terminal.setProperty("class", "cyber_terminal")
        self.txt_docker_terminal.setReadOnly(True)
        self.txt_docker_terminal.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.txt_docker_terminal.setPlaceholderText("Selecciona 'Logs' en cualquier contenedor de la pestaña Engine para inspeccionar su salida aquí...")
        logs_layout.addWidget(self.txt_docker_terminal, 1)

        self.docker_stack.addWidget(self.docker_logs_page)
        docker_layout.addWidget(self.docker_stack, 1)

        self.main_splitter.addWidget(card_docker)

        # =============================================================
        # 2. PANEL CENTRAL (APILADO VERTICAL): PYTHON & PUERTOS ACTIVOS
        # =============================================================
        center_container = QWidget()
        center_layout = QVBoxLayout(center_container)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)

        self.center_splitter = QSplitter(Qt.Vertical)
        self.center_splitter.setChildrenCollapsible(False)

        # -------------------------------------------------------------
        # 2.1 ARRIBA: ENTORNOS VIRTUALES PYTHON & DEPENDENCIAS
        # -------------------------------------------------------------
        card_python = QFrame()
        card_python.setProperty("class", "sector_card")
        py_layout = QVBoxLayout(card_python)
        py_layout.setContentsMargins(14, 12, 14, 12)
        py_layout.setSpacing(8)

        # Encabezado Python
        py_head = QHBoxLayout()
        py_box = QVBoxLayout()
        py_box.setSpacing(2)
        lbl_py_tag = QLabel("RUNTIME // PYTHON")
        lbl_py_tag.setProperty("class", "sector_micro_tag")
        lbl_py_title = QLabel("🐍 Entornos Virtuales & Paquetes")
        lbl_py_title.setProperty("class", "sector_title")
        py_box.addWidget(lbl_py_tag)
        py_box.addWidget(lbl_py_title)
        py_head.addLayout(py_box)

        py_head.addStretch()

        self.lbl_venv_badge = QLabel("○ Sin Entorno")
        self.lbl_venv_badge.setProperty("class", "badge_pending")
        py_head.addWidget(self.lbl_venv_badge)

        self.btn_refresh_py = QPushButton("🔄")
        self.btn_refresh_py.setProperty("class", "cyber_btn_compact")
        self.btn_refresh_py.setFixedSize(28, 28)
        self.btn_refresh_py.setCursor(Qt.PointingHandCursor)
        self.btn_refresh_py.setToolTip("Refrescar entorno Python y dependencias")
        self.btn_refresh_py.clicked.connect(self._refresh_python_env)
        py_head.addWidget(self.btn_refresh_py)

        py_layout.addLayout(py_head)

        # Información del intérprete y venv
        self.lbl_venv_details = QLabel("Entorno: No detectado | Intérprete: Base del sistema")
        self.lbl_venv_details.setProperty("class", "sector_desc")
        py_layout.addWidget(self.lbl_venv_details)

        # Botonera de acciones de Venv
        py_btn_row = QHBoxLayout()
        py_btn_row.setSpacing(6)

        self.btn_toggle_venv = QPushButton("⚡ Activar")
        self.btn_toggle_venv.setProperty("class", "cyber_btn_compact")
        self.btn_toggle_venv.setCursor(Qt.PointingHandCursor)
        self.btn_toggle_venv.setToolTip("Activar o desactivar el entorno virtual en la sesión actual")
        self.btn_toggle_venv.clicked.connect(self._toggle_venv_activation)
        py_btn_row.addWidget(self.btn_toggle_venv)

        self.btn_create_venv = QPushButton("✨ Crear .venv")
        self.btn_create_venv.setProperty("class", "cyber_btn_compact")
        self.btn_create_venv.setCursor(Qt.PointingHandCursor)
        self.btn_create_venv.setToolTip("Crear un nuevo entorno virtual en la raíz del proyecto")
        self.btn_create_venv.clicked.connect(self._create_venv_dialog)
        py_btn_row.addWidget(self.btn_create_venv)

        self.btn_pip_install = QPushButton("📦 Pip Install")
        self.btn_pip_install.setProperty("class", "cyber_btn_compact")
        self.btn_pip_install.setCursor(Qt.PointingHandCursor)
        self.btn_pip_install.setToolTip("Instalar dependencias desde requirements.txt o instalar paquete")
        self.btn_pip_install.clicked.connect(self._pip_install_dialog)
        py_btn_row.addWidget(self.btn_pip_install)

        self.btn_pip_freeze = QPushButton("❄ Freeze")
        self.btn_pip_freeze.setProperty("class", "cyber_btn_compact")
        self.btn_pip_freeze.setCursor(Qt.PointingHandCursor)
        self.btn_pip_freeze.setToolTip("Guardar paquetes instalados a requirements.txt")
        self.btn_pip_freeze.clicked.connect(self._pip_freeze)
        py_btn_row.addWidget(self.btn_pip_freeze)

        py_btn_row.addStretch()
        py_layout.addLayout(py_btn_row)

        # Filtro de búsqueda y lista de paquetes instalados
        pkg_filter_row = QHBoxLayout()
        pkg_filter_row.setSpacing(6)
        self.txt_filter_pkg = QLineEdit()
        self.txt_filter_pkg.setProperty("class", "cyber_input")
        self.txt_filter_pkg.setPlaceholderText("Filtrar paquetes instalados...")
        self.txt_filter_pkg.textChanged.connect(self._filter_packages)
        pkg_filter_row.addWidget(self.txt_filter_pkg, 1)

        self.lbl_pkg_count = QLabel("0 paquetes")
        self.lbl_pkg_count.setProperty("class", "badge_telemetry")
        pkg_filter_row.addWidget(self.lbl_pkg_count)
        py_layout.addLayout(pkg_filter_row)

        # Lista scrolleable de paquetes
        scroll_packages = QScrollArea()
        scroll_packages.setProperty("class", "clean_scroll")
        scroll_packages.setWidgetResizable(True)

        self.packages_container = QWidget()
        self.packages_layout = QVBoxLayout(self.packages_container)
        self.packages_layout.setContentsMargins(0, 0, 0, 0)
        self.packages_layout.setSpacing(3)
        scroll_packages.setWidget(self.packages_container)
        py_layout.addWidget(scroll_packages, 1)

        self.center_splitter.addWidget(card_python)

        # -------------------------------------------------------------
        # 2.2 ABAJO: PUERTOS ACTIVOS DEL SISTEMA (NETWORK LISTENERS)
        # -------------------------------------------------------------
        card_ports = QFrame()
        card_ports.setProperty("class", "sector_card")
        ports_layout = QVBoxLayout(card_ports)
        ports_layout.setContentsMargins(14, 12, 14, 12)
        ports_layout.setSpacing(8)

        # Encabezado Puertos
        p_head = QHBoxLayout()
        p_box = QVBoxLayout()
        p_box.setSpacing(2)
        lbl_p_tag = QLabel("RED // PUERTOS ACTIVOS")
        lbl_p_tag.setProperty("class", "sector_micro_tag")
        lbl_p_title = QLabel("📡 Puertos en Escucha del Sistema")
        lbl_p_title.setProperty("class", "sector_title")
        p_box.addWidget(lbl_p_tag)
        p_box.addWidget(lbl_p_title)
        p_head.addLayout(p_box)

        p_head.addStretch()

        self.lbl_ports_count = QLabel("0 activos")
        self.lbl_ports_count.setProperty("class", "badge_telemetry")
        p_head.addWidget(self.lbl_ports_count)

        self.btn_refresh_ports = QPushButton("🔄")
        self.btn_refresh_ports.setProperty("class", "cyber_btn_compact")
        self.btn_refresh_ports.setFixedSize(28, 28)
        self.btn_refresh_ports.setCursor(Qt.PointingHandCursor)
        self.btn_refresh_ports.setToolTip("Escanear puertos TCP abiertos en el sistema")
        self.btn_refresh_ports.clicked.connect(self._refresh_network_ports)
        p_head.addWidget(self.btn_refresh_ports)

        ports_layout.addLayout(p_head)

        lbl_p_desc = QLabel("Servicios y servidores de desarrollo locales actualmente escuchando conexiones:")
        lbl_p_desc.setProperty("class", "sector_desc")
        ports_layout.addWidget(lbl_p_desc)

        # Lista scrolleable de puertos
        scroll_ports = QScrollArea()
        scroll_ports.setProperty("class", "clean_scroll")
        scroll_ports.setWidgetResizable(True)

        self.ports_container = QWidget()
        self.ports_layout = QVBoxLayout(self.ports_container)
        self.ports_layout.setContentsMargins(0, 0, 0, 0)
        self.ports_layout.setSpacing(4)
        scroll_ports.setWidget(self.ports_container)
        ports_layout.addWidget(scroll_ports, 1)

        self.center_splitter.addWidget(card_ports)

        # Proporción vertical del panel central (50% venv, 50% puertos)
        self.center_splitter.setSizes([300, 300])
        center_layout.addWidget(self.center_splitter, 1)

        self.main_splitter.addWidget(center_container)

        # =============================================================
        # 3. PANEL DERECHO (VERTICAL): LISTA DE IDES / EDITORES
        # =============================================================
        card_editors = QFrame()
        card_editors.setProperty("class", "sector_card")
        editors_layout = QVBoxLayout(card_editors)
        editors_layout.setContentsMargins(14, 12, 14, 12)
        editors_layout.setSpacing(10)

        # Encabezado Editores
        e_header = QHBoxLayout()
        e_box = QVBoxLayout()
        e_box.setSpacing(2)
        lbl_e_tag = QLabel("DESARROLLO // EDITORES")
        lbl_e_tag.setProperty("class", "sector_micro_tag")
        lbl_e_title = QLabel("🚀 Lanzador de IDEs")
        lbl_e_title.setProperty("class", "sector_title")
        e_box.addWidget(lbl_e_tag)
        e_box.addWidget(lbl_e_title)
        e_header.addLayout(e_box)

        e_header.addStretch()

        self.btn_refresh_editors = QPushButton("🔄")
        self.btn_refresh_editors.setProperty("class", "cyber_btn_compact")
        self.btn_refresh_editors.setFixedSize(28, 28)
        self.btn_refresh_editors.setCursor(Qt.PointingHandCursor)
        self.btn_refresh_editors.setToolTip("Re-escanear editores e IDEs instalados en el PATH")
        self.btn_refresh_editors.clicked.connect(self._refresh_editors)
        e_header.addWidget(self.btn_refresh_editors)

        editors_layout.addLayout(e_header)

        # Subtítulo explicativo
        lbl_e_desc = QLabel("Abre el proyecto activo en tu entorno de desarrollo favorito con un solo clic:")
        lbl_e_desc.setProperty("class", "sector_desc")
        lbl_e_desc.setWordWrap(True)
        editors_layout.addWidget(lbl_e_desc)

        # Editor preferido banner
        self.lbl_preferred_editor = QLabel("★ Preferido: -")
        self.lbl_preferred_editor.setProperty("class", "badge_telemetry")
        editors_layout.addWidget(self.lbl_preferred_editor)

        # Lista scrolleable vertical de editores
        scroll_editors = QScrollArea()
        scroll_editors.setProperty("class", "clean_scroll")
        scroll_editors.setWidgetResizable(True)

        self.editors_container = QWidget()
        self.editors_layout = QVBoxLayout(self.editors_container)
        self.editors_layout.setContentsMargins(0, 0, 0, 0)
        self.editors_layout.setSpacing(6)
        scroll_editors.setWidget(self.editors_container)
        editors_layout.addWidget(scroll_editors, 1)

        self.main_splitter.addWidget(card_editors)

        # Proporción horizontal de las 3 columnas: 33% Docker, 37% Python & Puertos, 30% IDEs
        self.main_splitter.setSizes([370, 420, 310])
        root_layout.addWidget(self.main_splitter, 1)

    # =============================================================
    # LÓGICA DE ACTUALIZACIÓN & SINCRONIZACIÓN GENERAL
    # =============================================================
    def update_project(self, project: Project):
        """Actualiza la telemetría del proyecto para Docker, Python y Editores."""
        self.project = project
        self._refresh_docker()
        self._refresh_python_env()
        self._refresh_network_ports()
        self._refresh_editors()

    # =============================================================
    # 1. ACCIONES & TELEMETRÍA: DOCKER & COMPOSE
    # =============================================================
    def _refresh_docker(self):
        """Inspecciona el daemon de Docker, compose y lista contenedores."""
        p_path = str(self.project.path) if self.project and self.project.path else None
        d_status = inspect_docker_status(p_path)

        if not d_status.get("installed"):
            self.lbl_docker_daemon.setText("Docker no instalado")
            self.lbl_docker_daemon.setProperty("class", "badge_pending")
        elif d_status.get("daemon_running"):
            self.lbl_docker_daemon.setText("● Daemon Activo")
            self.lbl_docker_daemon.setProperty("class", "badge_staged")
        else:
            self.lbl_docker_daemon.setText("○ Daemon Inactivo")
            self.lbl_docker_daemon.setProperty("class", "badge_pending")

        self.lbl_docker_daemon.style().unpolish(self.lbl_docker_daemon)
        self.lbl_docker_daemon.style().polish(self.lbl_docker_daemon)

        # Estado de Compose / Dockerfile en el proyecto
        has_compose = d_status.get("has_compose", False)
        compose_files = d_status.get("compose_files", [])
        has_dockerfile = d_status.get("has_dockerfile", False)

        if has_compose and compose_files:
            c_name = compose_files[0]
            self.lbl_docker_compose_badge.setText(f"Compose: {c_name}")
            self.lbl_docker_compose_badge.setProperty("class", "badge_staged")
            self.lbl_compose_file.setText(f"Archivo Compose detectado: <b>{c_name}</b>")
            self.compose_actions_box.setVisible(True)
        elif has_dockerfile:
            self.lbl_docker_compose_badge.setText("Dockerfile detectado")
            self.lbl_docker_compose_badge.setProperty("class", "badge_telemetry")
            self.compose_actions_box.setVisible(False)
        else:
            self.lbl_docker_compose_badge.setText("Sin Docker")
            self.lbl_docker_compose_badge.setProperty("class", "badge_pending")
            self.compose_actions_box.setVisible(False)

        self.lbl_docker_compose_badge.style().unpolish(self.lbl_docker_compose_badge)
        self.lbl_docker_compose_badge.style().polish(self.lbl_docker_compose_badge)

        # Poblar contenedores pasando el path del proyecto para aislar el contexto
        self._populate_containers_list()

    def _populate_containers_list(self):
        """Llena la lista de contenedores Docker en la vista vertical aislando por el proyecto actual."""
        while self.containers_layout.count():
            item = self.containers_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        p_path = str(self.project.path) if self.project and self.project.path else None
        d_status = inspect_docker_status(p_path) if p_path else {}
        has_docker = d_status.get("has_compose", False) or d_status.get("has_dockerfile", False)

        if not has_docker:
            self.lbl_containers_count.setText("0 contenedores (Sin Docker)")

            empty_card = QFrame()
            empty_card.setProperty("class", "env_item_row")
            ec_layout = QVBoxLayout(empty_card)
            ec_layout.setContentsMargins(12, 12, 12, 12)
            ec_layout.setSpacing(6)

            lbl_title = QLabel("○ Sin entorno Docker en este proyecto")
            lbl_title.setStyleSheet("font-weight: 700; color: #94a3b8; font-size: 11px;")
            ec_layout.addWidget(lbl_title)

            lbl_desc = QLabel(
                "Este proyecto no contiene definiciones de Dockerfile ni docker-compose.yml.\n"
                "Para no sobrecargar la vista, los contenedores de otros proyectos o globales del sistema se ocultan automáticamente."
            )
            lbl_desc.setProperty("class", "sector_desc")
            lbl_desc.setWordWrap(True)
            ec_layout.addWidget(lbl_desc)

            self.containers_layout.addWidget(empty_card)
            self.containers_layout.addStretch()
            return

        containers = list_docker_containers(p_path)
        running_count = sum(1 for c in containers if c.get("is_running"))
        self.lbl_containers_count.setText(f"{running_count} activos / {len(containers)} total")

        if not containers:
            lbl_empty = QLabel(
                "No hay contenedores registrados para este proyecto.\n"
                "Usa 'Up' en Compose para levantar el stack de servicios."
            )
            lbl_empty.setProperty("class", "sector_desc")
            lbl_empty.setWordWrap(True)
            self.containers_layout.addWidget(lbl_empty)
            self.containers_layout.addStretch()
            return

        for c in containers:
            row = QFrame()
            row.setProperty("class", "env_item_row")
            r_layout = QVBoxLayout(row)
            r_layout.setContentsMargins(8, 8, 8, 8)
            r_layout.setSpacing(4)

            # Fila superior: Estado, Nombre, Imagen
            head = QHBoxLayout()
            head.setSpacing(6)

            is_running = c.get("is_running", False)
            dot = QLabel("●" if is_running else "○")
            dot.setStyleSheet("color: #34d399;" if is_running else "color: #94a3b8;")
            head.addWidget(dot)

            name = QLabel(c.get("name", "container"))
            name.setProperty("class", "file_path_label")
            head.addWidget(name)

            img = QLabel(f"({c.get('image', '')})")
            img.setProperty("class", "sector_desc")
            head.addWidget(img)
            head.addStretch()

            status_lbl = QLabel(c.get("status", ""))
            status_lbl.setProperty("class", "badge_telemetry")
            head.addWidget(status_lbl)
            r_layout.addLayout(head)

            # Fila media: Puertos (si los hay)
            ports_str = c.get("ports", "").strip()
            if ports_str:
                p_lbl = QLabel(f"Puertos: {ports_str}")
                p_lbl.setStyleSheet("font-family: 'JetBrains Mono', monospace; font-size: 10px; color: #cbd5e1;")
                r_layout.addWidget(p_lbl)

            # Fila de acciones por contenedor
            act_row = QHBoxLayout()
            act_row.setSpacing(4)
            c_name = c.get("name", "")

            if is_running:
                btn_stop = QPushButton("⏹ Stop")
                btn_stop.setProperty("class", "cyber_btn_compact")
                btn_stop.setCursor(Qt.PointingHandCursor)
                btn_stop.clicked.connect(lambda _, cn=c_name: self._container_action("stop", cn))
                act_row.addWidget(btn_stop)
            else:
                btn_start = QPushButton("▶ Start")
                btn_start.setProperty("class", "cyber_btn_compact")
                btn_start.setCursor(Qt.PointingHandCursor)
                btn_start.clicked.connect(lambda _, cn=c_name: self._container_action("start", cn))
                act_row.addWidget(btn_start)

            btn_restart = QPushButton("🔄 Restart")
            btn_restart.setProperty("class", "cyber_btn_compact")
            btn_restart.setCursor(Qt.PointingHandCursor)
            btn_restart.clicked.connect(lambda _, cn=c_name: self._container_action("restart", cn))
            act_row.addWidget(btn_restart)

            btn_logs = QPushButton("📜 Logs")
            btn_logs.setProperty("class", "cyber_btn_compact")
            btn_logs.setCursor(Qt.PointingHandCursor)
            btn_logs.clicked.connect(lambda _, cn=c_name: self._show_container_logs(cn))
            act_row.addWidget(btn_logs)

            btn_rm = QPushButton("🗑")
            btn_rm.setProperty("class", "cyber_btn_danger_compact")
            btn_rm.setCursor(Qt.PointingHandCursor)
            btn_rm.setToolTip("Eliminar contenedor")
            btn_rm.clicked.connect(lambda _, cn=c_name: self._container_action("remove", cn))
            act_row.addWidget(btn_rm)

            act_row.addStretch()
            r_layout.addLayout(act_row)

            self.containers_layout.addWidget(row)

        self.containers_layout.addStretch()

    def _set_terminal_content(self, text: str):
        """Escribe texto en la terminal táctica de Docker y posiciona el cursor al final."""
        self.txt_docker_terminal.setPlainText(text)
        cursor = self.txt_docker_terminal.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.txt_docker_terminal.setTextCursor(cursor)

    def _container_action(self, action: str, container_name: str):
        """Ejecuta una acción sobre un contenedor y canaliza la salida directamente a la terminal de logs."""
        self.current_logs_target = container_name
        self.current_logs_is_compose = False
        self.lbl_terminal_title.setText(f"Logs: {container_name}")
        self._switch_docker_subview(1)

        self._set_terminal_content(f"$ docker {action} {container_name}\nEjecutando acción...")
        QApplication.processEvents()

        ok, msg = execute_docker_container_action(action, container_name)
        if ok:
            out_text = f"$ docker {action} {container_name}\n✔ {msg}"
            if action in ["start", "restart"]:
                ok_logs, logs = get_docker_container_logs(container_name, tail_lines=80)
                if ok_logs and logs:
                    out_text += f"\n\n--- [Registros de {container_name}] ---\n{logs}"
            self._set_terminal_content(out_text)
        else:
            self._set_terminal_content(f"$ docker {action} {container_name} [FALLO]\n❌ {msg}")

        self._populate_containers_list()

    def _switch_docker_subview(self, index: int):
        """Alterna entre la vista de Engine (0) y la Terminal de Logs (1) en el sub-sector de Docker."""
        self.docker_stack.setCurrentIndex(index)
        if index == 0:
            self.btn_sub_engine.setChecked(True)
        else:
            self.btn_sub_logs.setChecked(True)

    def _show_container_logs(self, container_name: str):
        """Cambia a la terminal integrada de Docker y muestra los registros del contenedor."""
        self.current_logs_target = container_name
        self.current_logs_is_compose = False
        self.lbl_terminal_title.setText(f"Logs: {container_name}")
        self._switch_docker_subview(1)
        self._refresh_active_logs()

    def _show_compose_logs(self):
        """Cambia a la terminal integrada de Docker y muestra los registros de Docker Compose."""
        if not self.project or not self.project.path:
            return
        p_path = str(self.project.path)
        d_status = inspect_docker_status(p_path)
        compose_files = d_status.get("compose_files", [])
        if not compose_files:
            self._switch_docker_subview(1)
            self._set_terminal_content("⚠️ No se encontró ningún archivo docker-compose en el proyecto.")
            return

        c_file = os.path.join(p_path, compose_files[0])
        self.current_logs_target = c_file
        self.current_logs_is_compose = True
        self.lbl_terminal_title.setText(f"Logs: Compose ({compose_files[0]})")
        self._switch_docker_subview(1)
        self._refresh_active_logs()

    def _refresh_active_logs(self):
        """Actualiza el contenido de la terminal de logs para el objetivo actualmente seleccionado."""
        if not self.current_logs_target:
            self._set_terminal_content("No hay ningún contenedor o compose seleccionado para inspeccionar logs.")
            return

        if self.current_logs_is_compose:
            ok, logs = execute_compose_action(self.current_logs_target, "logs")
        else:
            ok, logs = get_docker_container_logs(self.current_logs_target, tail_lines=150)

        if ok and logs:
            self._set_terminal_content(logs)
        elif not ok:
            self._set_terminal_content(f"Error al obtener logs:\n{logs}")
        else:
            self._set_terminal_content("No hay registros disponibles para el objetivo seleccionado.")

    def _copy_terminal_logs(self):
        """Copia el texto actual de la terminal de logs al portapapeles del sistema."""
        text = self.txt_docker_terminal.toPlainText()
        if text:
            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText(text)

    def _clear_terminal_logs(self):
        """Limpia el contenido de la terminal de logs."""
        self.txt_docker_terminal.clear()

    def _trigger_compose_action(self, action: str):
        """Ejecuta up, down o restart sobre el archivo compose del proyecto y canaliza la salida a la terminal de logs."""
        if not self.project or not self.project.path:
            return
        p_path = str(self.project.path)
        d_status = inspect_docker_status(p_path)
        compose_files = d_status.get("compose_files", [])
        if not compose_files:
            self._switch_docker_subview(1)
            self._set_terminal_content("⚠️ No se encontró ningún archivo docker-compose en el proyecto.")
            return

        c_file = os.path.join(p_path, compose_files[0])
        self.current_logs_target = c_file
        self.current_logs_is_compose = True
        self.lbl_terminal_title.setText(f"Logs: Compose ({compose_files[0]})")
        self._switch_docker_subview(1)

        self._set_terminal_content(f"$ docker compose -f {compose_files[0]} {action}\nEjecutando acción...")
        QApplication.processEvents()

        ok, msg = execute_compose_action(c_file, action)
        if ok:
            out_text = f"$ docker compose -f {compose_files[0]} {action}\n✔ {msg}"
            if action in ["up", "restart"]:
                ok_l, logs = execute_compose_action(c_file, "logs")
                if ok_l and logs:
                    out_text += f"\n\n--- [Registros de Compose / Service Logs] ---\n{logs}"
            self._set_terminal_content(out_text)
        else:
            self._set_terminal_content(f"$ docker compose -f {compose_files[0]} {action} [FALLO]\n❌ {msg}")
        self._refresh_docker()

    def _execute_docker_prune_dialog(self):
        """Diálogo de confirmación para docker system prune con salida en la terminal de logs."""
        reply = QMessageBox.question(
            self,
            "Limpieza de Docker (System Prune)",
            "¿Deseas ejecutar 'docker system prune'?\nEsto liberará contenedores detenidos, redes huérfanas y cachés no utilizadas.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.current_logs_target = "System Prune"
            self.current_logs_is_compose = False
            self.lbl_terminal_title.setText("Logs: Docker System Prune")
            self._switch_docker_subview(1)
            self._set_terminal_content("$ docker system prune -f\nEjecutando limpieza de recursos huérfanos...")
            QApplication.processEvents()

            ok, msg = execute_docker_prune()
            if ok:
                self._set_terminal_content(f"$ docker system prune -f\n✔ {msg}\n\n✨ Limpieza de sistema Docker completada.")
            else:
                self._set_terminal_content(f"$ docker system prune -f [ERROR]\n❌ {msg}")
            self._refresh_docker()

    # =============================================================
    # 2. ACCIONES & TELEMETRÍA: PYTHON VENV & PAQUETES
    # =============================================================
    def _refresh_python_env(self):
        """Inspecciona y actualiza la información del entorno virtual Python."""
        if not self.project or not self.project.path:
            return

        p_path = str(self.project.path)
        v_info = inspect_python_venv(p_path)

        if v_info.get("has_venv"):
            v_name = v_info.get("venv_name", ".venv")
            py_ver = v_info.get("python_version", "Python 3")
            is_active = v_info.get("is_active", False)

            if is_active:
                self.lbl_venv_badge.setText("● ACTIVO EN SESIÓN")
                self.lbl_venv_badge.setProperty("class", "badge_staged")
                self.btn_toggle_venv.setText("⏹ Desactivar")
            else:
                self.lbl_venv_badge.setText("○ INACTIVO")
                self.lbl_venv_badge.setProperty("class", "badge_pending")
                self.btn_toggle_venv.setText("⚡ Activar")

            pkg_count = v_info.get("package_count", 0)
            self.lbl_venv_details.setText(f"Entorno: <b>{v_name}</b> | {py_ver} | <b>{pkg_count} paquetes</b>")
            self.btn_toggle_venv.setEnabled(True)
            self.btn_pip_install.setEnabled(True)
            self.btn_pip_freeze.setEnabled(True)

            # Cargar lista de paquetes instalados
            v_full_path = v_info.get("venv_path", "")
            if v_full_path:
                self._installed_packages_cache = list_installed_packages(v_full_path)
            else:
                self._installed_packages_cache = []
        else:
            self.lbl_venv_badge.setText("○ Sin Entorno")
            self.lbl_venv_badge.setProperty("class", "badge_pending")
            self.lbl_venv_details.setText("No se detectó entorno virtual (.venv) en este proyecto.")
            self.btn_toggle_venv.setText("⚡ Activar")
            self.btn_toggle_venv.setEnabled(False)
            self.btn_pip_install.setEnabled(False)
            self.btn_pip_freeze.setEnabled(False)
            self._installed_packages_cache = []

            # Limpiar lista y mostrar estado inicial con botón de creación directa
            while self.packages_layout.count():
                item = self.packages_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            self.lbl_pkg_count.setText("0 paquetes")

            empty_box = QFrame()
            empty_box.setProperty("class", "env_item_row")
            eb_l = QVBoxLayout(empty_box)
            eb_l.setContentsMargins(12, 12, 12, 12)
            eb_l.setSpacing(6)

            lbl_t = QLabel("○ Sin entorno virtual configurado")
            lbl_t.setStyleSheet("font-weight: 700; color: #94a3b8; font-size: 11px;")
            eb_l.addWidget(lbl_t)

            lbl_d = QLabel("Crea un entorno virtual aislado para instalar paquetes y gestionar dependencias.")
            lbl_d.setProperty("class", "sector_desc")
            lbl_d.setWordWrap(True)
            eb_l.addWidget(lbl_d)

            btn_quick_venv = QPushButton("✨ Crear .venv ahora")
            btn_quick_venv.setProperty("class", "cyber_btn_primary")
            btn_quick_venv.setCursor(Qt.PointingHandCursor)
            btn_quick_venv.clicked.connect(self._create_venv_dialog)
            eb_l.addWidget(btn_quick_venv)

            self.packages_layout.addWidget(empty_box)
            self.packages_layout.addStretch()

        self.lbl_venv_badge.style().unpolish(self.lbl_venv_badge)
        self.lbl_venv_badge.style().polish(self.lbl_venv_badge)

        if v_info.get("has_venv"):
            self._render_packages_list(self._installed_packages_cache)

    def _render_packages_list(self, packages: List[tuple[str, str]]):
        """Renderiza los paquetes en la lista scrolleable con acciones tácticas."""
        while self.packages_layout.count():
            item = self.packages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.lbl_pkg_count.setText(f"{len(packages)} paquetes")

        if not packages:
            lbl_empty = QLabel("No hay paquetes instalados o entorno vacío.")
            lbl_empty.setProperty("class", "sector_desc")
            self.packages_layout.addWidget(lbl_empty)
            self.packages_layout.addStretch()
            return

        for name, version in packages:
            row = QFrame()
            row.setProperty("class", "env_item_row")
            r_l = QHBoxLayout(row)
            r_l.setContentsMargins(6, 4, 6, 4)
            r_l.setSpacing(6)

            lbl_n = QLabel(name)
            lbl_n.setProperty("class", "file_path_label")
            r_l.addWidget(lbl_n)
            r_l.addStretch()

            if version:
                lbl_v = QLabel(f"v{version}")
                lbl_v.setProperty("class", "badge_telemetry")
                r_l.addWidget(lbl_v)

            btn_rm_pkg = QPushButton("🗑")
            btn_rm_pkg.setProperty("class", "cyber_btn_danger_compact")
            btn_rm_pkg.setFixedSize(22, 22)
            btn_rm_pkg.setCursor(Qt.PointingHandCursor)
            btn_rm_pkg.setToolTip(f"Desinstalar paquete {name}")
            btn_rm_pkg.clicked.connect(lambda _, pn=name: self._confirm_uninstall_package(pn))
            r_l.addWidget(btn_rm_pkg)

            self.packages_layout.addWidget(row)

        self.packages_layout.addStretch()

    def _confirm_uninstall_package(self, package_name: str):
        """Pide confirmación y desinstala un paquete del entorno virtual."""
        reply = QMessageBox.question(
            self,
            "Desinstalar Paquete",
            f"¿Deseas desinstalar el paquete <b>{package_name}</b> del entorno virtual?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if not self.project or not self.project.path:
                return
            p_path = str(self.project.path)
            v_info = inspect_python_venv(p_path)
            v_full = v_info.get("venv_path", "")
            if not v_full:
                return
            self.log_emitted.emit(f"🗑 Desinstalando paquete <b>{package_name}</b>...")
            ok, msg = uninstall_package(p_path, v_full, package_name)
            if ok:
                self.log_emitted.emit(f"✨ {msg}")
            else:
                self.log_emitted.emit(f"⚠️ {msg}")
            self._refresh_python_env()

    def _filter_packages(self, query: str):
        """Filtra reactivamente la lista de paquetes instalados según el texto."""
        q = query.strip().lower()
        if not q:
            self._render_packages_list(self._installed_packages_cache)
            return

        filtered = [pkg for pkg in self._installed_packages_cache if q in pkg[0].lower()]
        self._render_packages_list(filtered)

    def _toggle_venv_activation(self):
        """Conmuta la activación del entorno virtual en el proceso de Abraxas."""
        if not self.project or not self.project.path:
            return
        p_path = str(self.project.path)
        v_info = inspect_python_venv(p_path)
        v_full = v_info.get("venv_path", "")

        if v_info.get("is_active"):
            ok, msg = deactivate_python_venv()
            self.log_emitted.emit(f"🐍 {msg}")
        else:
            if v_full:
                ok, msg = activate_python_venv(v_full)
                self.log_emitted.emit(f"🐍 {msg}")
            else:
                self.log_emitted.emit("No se encontró ruta de entorno virtual para activar.")

        self._refresh_python_env()

    def _create_venv_dialog(self):
        """Diálogo modal para crear un nuevo entorno virtual."""
        if not self.project or not self.project.path:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Crear Entorno Virtual Python")
        dialog.setFixedWidth(400)
        dialog.setProperty("class", "cyber_dialog")

        d_layout = QVBoxLayout(dialog)
        d_layout.setContentsMargins(18, 16, 18, 16)
        d_layout.setSpacing(10)

        lbl_t = QLabel("✨ Nuevo Entorno Virtual Python:")
        lbl_t.setProperty("class", "sector_title")
        d_layout.addWidget(lbl_t)

        lbl_name = QLabel("Nombre de la carpeta:")
        lbl_name.setProperty("class", "sector_desc")
        d_layout.addWidget(lbl_name)

        txt_name = QLineEdit(".venv")
        txt_name.setProperty("class", "cyber_input")
        d_layout.addWidget(txt_name)

        has_uv = bool(shutil.which("uv"))
        chk_uv = QCheckBox("⚡ Usar 'uv' (ultrarrápido)" if has_uv else "uv no disponible (usando python -m venv)")
        chk_uv.setEnabled(has_uv)
        chk_uv.setChecked(has_uv)
        d_layout.addWidget(chk_uv)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setProperty("class", "cyber_btn")
        btn_cancel.clicked.connect(dialog.reject)
        btn_row.addWidget(btn_cancel)

        btn_confirm = QPushButton("Crear Entorno")
        btn_confirm.setProperty("class", "cyber_btn_primary")
        btn_confirm.clicked.connect(dialog.accept)
        btn_row.addWidget(btn_confirm)

        d_layout.addLayout(btn_row)

        if dialog.exec() == QDialog.Accepted:
            v_name = txt_name.text().strip() or ".venv"
            use_uv = chk_uv.isChecked() and has_uv
            self.log_emitted.emit(f"🐍 Creando entorno virtual <b>{v_name}</b> (uv={use_uv})...")
            ok, msg = create_python_venv(str(self.project.path), use_uv=use_uv, venv_name=v_name)
            if ok:
                self.log_emitted.emit(f"✨ {msg}")
                # Autoactivar
                v_full = os.path.join(str(self.project.path), v_name)
                activate_python_venv(v_full)
            else:
                self.log_emitted.emit(f"⚠️ Error al crear entorno: {msg}")
            self._refresh_python_env()

    def _pip_install_dialog(self):
        """Diálogo para instalar dependencias de requirements.txt o paquete ad-hoc."""
        if not self.project or not self.project.path:
            return

        p_path = str(self.project.path)
        v_info = inspect_python_venv(p_path)
        v_full = v_info.get("venv_path", "")
        if not v_full:
            self.log_emitted.emit("No hay un entorno virtual activo para instalar paquetes.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Pip Install: Paquetes o Requisitos")
        dialog.setFixedWidth(440)
        dialog.setProperty("class", "cyber_dialog")

        d_layout = QVBoxLayout(dialog)
        d_layout.setContentsMargins(18, 16, 18, 16)
        d_layout.setSpacing(10)

        lbl_t = QLabel("📦 Instalación de Dependencias:")
        lbl_t.setProperty("class", "sector_title")
        d_layout.addWidget(lbl_t)

        has_reqs = os.path.exists(os.path.join(p_path, "requirements.txt"))
        btn_reqs = QPushButton("📄 Instalar desde requirements.txt" if has_reqs else "📄 requirements.txt (no encontrado)")
        btn_reqs.setProperty("class", "cyber_btn")
        btn_reqs.setEnabled(has_reqs)
        btn_reqs.setCursor(Qt.PointingHandCursor)
        d_layout.addWidget(btn_reqs)

        lbl_sep = QLabel("O ingresa paquetes específicos a instalar (separados por espacio):")
        lbl_sep.setProperty("class", "sector_desc")
        d_layout.addWidget(lbl_sep)

        txt_pkgs = QLineEdit()
        txt_pkgs.setProperty("class", "cyber_input")
        txt_pkgs.setPlaceholderText("ej. fastapi uvicorn pydantic...")
        d_layout.addWidget(txt_pkgs)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setProperty("class", "cyber_btn")
        btn_cancel.clicked.connect(dialog.reject)
        btn_row.addWidget(btn_cancel)

        btn_install_custom = QPushButton("Instalar Paquetes")
        btn_install_custom.setProperty("class", "cyber_btn_primary")
        btn_row.addWidget(btn_install_custom)

        d_layout.addLayout(btn_row)

        def _do_install_reqs():
            dialog.accept()
            self.log_emitted.emit("📦 Instalando dependencias desde requirements.txt...")
            ok, msg = install_project_dependencies(p_path, v_full)
            if ok:
                self.log_emitted.emit(f"✨ {msg}")
            else:
                self.log_emitted.emit(f"⚠️ {msg}")
            self._refresh_python_env()

        def _do_install_custom():
            pkgs = txt_pkgs.text().strip().split()
            if not pkgs:
                return
            dialog.accept()
            self.log_emitted.emit(f"📦 Instalando paquetes: {', '.join(pkgs)}...")
            ok, msg = install_custom_packages(p_path, v_full, pkgs)
            if ok:
                self.log_emitted.emit(f"✨ {msg}")
            else:
                self.log_emitted.emit(f"⚠️ {msg}")
            self._refresh_python_env()

        btn_reqs.clicked.connect(_do_install_reqs)
        btn_install_custom.clicked.connect(_do_install_custom)

        dialog.exec()

    def _pip_freeze(self):
        """Ejecuta freeze y guarda los paquetes actuales en requirements.txt."""
        if not self.project or not self.project.path:
            return
        p_path = str(self.project.path)
        v_info = inspect_python_venv(p_path)
        v_full = v_info.get("venv_path", "")
        if not v_full:
            self.log_emitted.emit("No hay un entorno virtual activo para congelar dependencias.")
            return

        self.log_emitted.emit("❄ Congelando dependencias a requirements.txt...")
        ok, msg = freeze_dependencies_to_file(p_path, v_full)
        if ok:
            self.log_emitted.emit(f"✨ {msg}")
        else:
            self.log_emitted.emit(f"⚠️ {msg}")

    # =============================================================
    # 3. ACCIONES & TELEMETRÍA: PUERTOS ACTIVOS DEL SISTEMA
    # =============================================================
    def _refresh_network_ports(self):
        """Escanea los puertos TCP en escucha en el sistema y puebla la lista."""
        while self.ports_layout.count():
            item = self.ports_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        ports = inspect_network_ports()
        self.lbl_ports_count.setText(f"{len(ports)} activos")

        if not ports:
            lbl_empty = QLabel("No se detectaron puertos TCP en estado LISTEN.")
            lbl_empty.setProperty("class", "sector_desc")
            self.ports_layout.addWidget(lbl_empty)
            self.ports_layout.addStretch()
            return

        for p in ports:
            port_num = p.get("port", 0)
            cmd = p.get("command", "desconocido")
            pid = p.get("pid", "?")
            proto = p.get("protocol", "TCP")
            addr = p.get("address", "*")

            row = QFrame()
            row.setProperty("class", "env_item_row")
            r_l = QHBoxLayout(row)
            r_l.setContentsMargins(8, 6, 8, 6)
            r_l.setSpacing(8)

            # Badge de puerto
            lbl_port = QLabel(f":{port_num}")
            lbl_port.setStyleSheet("font-family: 'JetBrains Mono', monospace; font-size: 13px; font-weight: 800; color: #ffffff;")
            r_l.addWidget(lbl_port)

            # Proceso y comando
            lbl_proc = QLabel(f"<b>{cmd}</b> ({proto} @ {addr})")
            lbl_proc.setProperty("class", "sector_desc")
            r_l.addWidget(lbl_proc)

            # Badge PID
            lbl_pid = QLabel(f"PID: {pid}")
            lbl_pid.setProperty("class", "badge_telemetry")
            r_l.addWidget(lbl_pid)

            r_l.addStretch()

            # Botón Abrir en Navegador
            btn_open = QPushButton("🌐 Abrir")
            btn_open.setProperty("class", "cyber_btn_compact")
            btn_open.setCursor(Qt.PointingHandCursor)
            btn_open.setToolTip(f"Abrir http://localhost:{port_num} en el navegador")
            btn_open.clicked.connect(lambda _, pn=port_num: self._open_browser_port(pn))
            r_l.addWidget(btn_open)

            # Botón Matar proceso (si hay PID válido)
            if pid and pid != "?":
                btn_kill = QPushButton("⏹ Kill")
                btn_kill.setProperty("class", "cyber_btn_danger_compact")
                btn_kill.setCursor(Qt.PointingHandCursor)
                btn_kill.setToolTip(f"Terminar proceso '{cmd}' (PID: {pid})")
                btn_kill.clicked.connect(lambda _, pd=pid, pn=port_num, cm=cmd: self._kill_port_process(pd, pn, cm))
                r_l.addWidget(btn_kill)

            self.ports_layout.addWidget(row)

        self.ports_layout.addStretch()

    def _open_browser_port(self, port: int):
        """Abre localhost:port en el navegador predeterminado."""
        url = f"http://localhost:{port}"
        self.log_emitted.emit(f"🌐 Abriendo {url} en el navegador...")
        webbrowser.open(url)

    def _kill_port_process(self, pid: str, port: int, command: str):
        """Diálogo de confirmación para terminar un proceso que ocupa un puerto."""
        reply = QMessageBox.question(
            self,
            "Confirmar Terminación de Proceso",
            f"¿Deseas terminar forzosamente el proceso <b>{command}</b> (PID: {pid}) que ocupa el puerto <b>:{port}</b>?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            ok, msg = kill_process_by_pid(pid)
            if ok:
                self.log_emitted.emit(f"⏹ Proceso {command} (PID {pid}) terminado con éxito.")
            else:
                self.log_emitted.emit(f"⚠️ Error al terminar proceso: {msg}")
            self._refresh_network_ports()

    # =============================================================
    # 4. ACCIONES & TELEMETRÍA: LISTA DE IDES / EDITORES
    # =============================================================
    def _refresh_editors(self):
        """Detecta editores instalados y puebla la lista vertical de la derecha."""
        while self.editors_layout.count():
            item = self.editors_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        editors = detect_installed_editors()
        pref_id = get_preferred_editor()

        pref_name = pref_id
        for e in editors:
            if e["id"] == pref_id:
                pref_name = f"{e['icon']} {e['name']}"
                break
        self.lbl_preferred_editor.setText(f"★ Editor Preferido: <b>{pref_name}</b>")

        if not editors:
            lbl_empty = QLabel("No se detectaron editores o IDEs conocidos en el PATH del sistema.")
            lbl_empty.setProperty("class", "sector_desc")
            self.editors_layout.addWidget(lbl_empty)
            self.editors_layout.addStretch()
            return

        for ed in editors:
            e_id = ed["id"]
            e_name = ed["name"]
            e_icon = ed["icon"]
            e_type = ed["type"]
            e_bin = ed["bin_path"]
            is_pref = (e_id == pref_id)

            card = QFrame()
            card.setProperty("class", "env_item_row_active" if is_pref else "env_item_row")
            c_l = QVBoxLayout(card)
            c_l.setContentsMargins(10, 8, 10, 8)
            c_l.setSpacing(6)

            # Fila 1: Icono, Nombre, Badge preferido
            h_row = QHBoxLayout()
            h_row.setSpacing(6)

            icon_lbl = QLabel(e_icon)
            icon_lbl.setStyleSheet("font-size: 16px;")
            h_row.addWidget(icon_lbl)

            name_lbl = QLabel(f"<b>{e_name}</b>")
            name_lbl.setProperty("class", "file_path_label")
            h_row.addWidget(name_lbl)
            h_row.addStretch()

            if is_pref:
                badge_p = QLabel("★ PREFERIDO")
                badge_p.setProperty("class", "badge_staged")
                h_row.addWidget(badge_p)
            c_l.addLayout(h_row)

            # Fila 2: Tipo y Binario
            desc_lbl = QLabel(f"{e_type.upper()} // <code>{e_bin}</code>")
            desc_lbl.setStyleSheet("font-size: 9.5px; color: #94a3b8; font-family: 'JetBrains Mono', monospace;")
            c_l.addWidget(desc_lbl)

            # Fila 3: Botonera
            b_row = QHBoxLayout()
            b_row.setSpacing(6)

            btn_launch = QPushButton(f"🚀 Abrir en {e_id}")
            btn_launch.setProperty("class", "cyber_btn_primary" if is_pref else "cyber_btn")
            btn_launch.setCursor(Qt.PointingHandCursor)
            btn_launch.clicked.connect(lambda _, cmd=e_id, nm=e_name: self._launch_editor(cmd, nm))
            b_row.addWidget(btn_launch)

            if not is_pref:
                btn_set_pref = QPushButton("★ Preferido")
                btn_set_pref.setProperty("class", "cyber_btn_compact")
                btn_set_pref.setCursor(Qt.PointingHandCursor)
                btn_set_pref.setToolTip(f"Fijar {e_name} como editor predeterminado del proyecto")
                btn_set_pref.clicked.connect(lambda _, cmd=e_id: self._set_default_editor(cmd))
                b_row.addWidget(btn_set_pref)

            b_row.addStretch()
            c_l.addLayout(b_row)

            self.editors_layout.addWidget(card)

        self.editors_layout.addStretch()

    def _launch_editor(self, cmd: str, name: str):
        """Lanza el editor apuntando al proyecto activo."""
        if not self.project or not self.project.path:
            self.log_emitted.emit("No hay ningún proyecto activo cargado.")
            return

        p_path = str(self.project.path)
        self.log_emitted.emit(f"🚀 Abriendo proyecto con <b>{name}</b> ({cmd})...")
        ok, msg = launch_project_in_editor(cmd, p_path)
        if ok:
            self.log_emitted.emit(f"✨ {msg}")
            self.action_requested.emit("editor_launched", {"editor": cmd, "project": self.project.name})
        else:
            self.log_emitted.emit(f"⚠️ Error al abrir editor: {msg}")

    def _set_default_editor(self, cmd: str):
        """Fija el editor preferido y refresca la lista."""
        set_preferred_editor(cmd)
        self.log_emitted.emit(f"★ Editor preferido actualizado a: <b>{cmd}</b>")
        self._refresh_editors()

    def teardown(self):
        """Limpia cachés, vacía la terminal de logs y resetea estados de Docker."""
        self._installed_packages_cache.clear()
        self.txt_docker_terminal.clear()
        self.current_logs_target = None
        self.current_logs_is_compose = False
