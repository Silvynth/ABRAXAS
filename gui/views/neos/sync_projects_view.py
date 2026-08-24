#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS | NEOS - GITHUB REPO SYNC & EXPLORER VIEW
# =====================================================================

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QLineEdit, QFrame, QScrollArea,
    QProgressBar, QRadioButton, QButtonGroup
)
from PySide6.QtCore import Qt, Signal, QThread

from core.projects import get_projects_dir
from core.github import (
    check_gh_cli_authenticated, fetch_repos_gh_cli, 
    fetch_repos_api, clone_repository, pull_repository
)

class GitActionWorker(QThread):
    """Hilo para clonar o hacer pull de repositorios en segundo plano sin congelar la GUI."""
    finished = Signal(bool, str, str) # success, message, target_dir

    def __init__(self, action: str, url: str, dest_or_path: str, full_name: str = "", parent=None):
        super().__init__(parent)
        self.action = action
        self.url = url
        self.dest_or_path = dest_or_path
        self.full_name = full_name

    def run(self):
        try:
            if self.action == "clone":
                clone_repository(self.url, self.dest_or_path, self.full_name)
                self.finished.emit(True, f"✅ Repositorio clonado exitosamente en: {self.dest_or_path}", self.dest_or_path)
            elif self.action == "pull":
                msg = pull_repository(self.dest_or_path)
                self.finished.emit(True, f"✅ Repositorio actualizado:\n{msg}", self.dest_or_path)
        except Exception as e:
            self.finished.emit(False, str(e), "")


class GithubRepoCardWidget(QFrame):
    """Tarjeta interactiva para representar un repositorio de GitHub."""
    
    def __init__(self, repo_data: dict, projects_dir: str, on_action_cb, parent=None):
        super().__init__(parent)
        self.repo_data = repo_data
        self.projects_dir = projects_dir
        self.on_action_cb = on_action_cb
        
        self.local_path = os.path.join(self.projects_dir, repo_data["name"])
        self.is_cloned = os.path.exists(self.local_path)

        self.setProperty("class", "project_row")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)

        # Fila Superior: Nombre + Badges + Botón de Acción
        r_top = QHBoxLayout()
        r_top.setSpacing(10)

        icon = "🔒" if repo_data.get("is_private") else "🌐"
        self.lbl_name = QLabel(f"🐙 {repo_data['name']}")
        self.lbl_name.setProperty("class", "project_name")
        r_top.addWidget(self.lbl_name)

        # Badge de Visibilidad
        vis_tag = "Privado" if repo_data.get("is_private") else "Público"
        self.lbl_vis = QLabel(f"{icon} {vis_tag}")
        self.lbl_vis.setProperty("class", "badge_dir")
        r_top.addWidget(self.lbl_vis)

        # Lenguaje
        lang = repo_data.get("language", "Varios")
        self.lbl_lang = QLabel(f"🏷️ {lang}")
        self.lbl_lang.setStyleSheet("font-size: 11px; color: #9ca3af; font-weight: 500;")
        r_top.addWidget(self.lbl_lang)

        # Estrellas
        stars = repo_data.get("stars", 0)
        if stars > 0:
            lbl_stars = QLabel(f"⭐ {stars}")
            lbl_stars.setStyleSheet("font-size: 11px; color: #fbbf24; font-weight: 600;")
            r_top.addWidget(lbl_stars)

        r_top.addStretch()

        # Botón de Acción (Clonar o Git Pull)
        if self.is_cloned:
            lbl_cloned = QLabel("✅ En Local")
            lbl_cloned.setStyleSheet("color: #10b981; font-weight: 700; font-size: 12px;")
            r_top.addWidget(lbl_cloned)

            self.btn_action = QPushButton("🔄 Git Pull")
            self.btn_action.setProperty("class", "browse")
            self.btn_action.setCursor(Qt.PointingHandCursor)
            self.btn_action.clicked.connect(lambda: self.on_action_cb("pull", self.repo_data, self.local_path))
            r_top.addWidget(self.btn_action)
        else:
            self.btn_action = QPushButton("📥 Clonar a Proyectos")
            self.btn_action.setProperty("class", "btn_mode_purple")
            self.btn_action.setCursor(Qt.PointingHandCursor)
            self.btn_action.clicked.connect(lambda: self.on_action_cb("clone", self.repo_data, self.local_path))
            r_top.addWidget(self.btn_action)

        layout.addLayout(r_top)

        # Descripción
        desc = repo_data.get("description", "Sin descripción.")
        self.lbl_desc = QLabel(desc)
        self.lbl_desc.setStyleSheet("color: #9ca3af; font-size: 12px;")
        self.lbl_desc.setWordWrap(True)
        layout.addWidget(self.lbl_desc)

        # Fila Inferior: URL y Fecha de actualización
        r_bot = QHBoxLayout()
        lbl_url = QLabel(repo_data.get("url", ""))
        lbl_url.setStyleSheet("font-family: monospace; font-size: 11px; color: #6366f1;")
        r_bot.addWidget(lbl_url, 1)

        pushed = repo_data.get("pushed_at", "")
        if pushed:
            lbl_date = QLabel(f"📅 Actualizado: {pushed}")
            lbl_date.setStyleSheet("font-size: 11px; color: #6b7280;")
            r_bot.addWidget(lbl_date)

        layout.addLayout(r_bot)


class SyncProjectsView(QWidget):
    """Vista de sincronización con GitHub para listar repositorios y clonarlos al entorno local."""

    project_synced = Signal(str) # Emite la ruta local cuando un repo es clonado
    back_requested = Signal()    # Emite cuando el usuario desea regresar al explorador

    def __init__(self, config_target, parent=None):
        super().__init__(parent)
        self.config_target = config_target
        self.projects_dir = get_projects_dir(self.config_target)
        self.repos_data = []
        self.card_widgets = []
        self.worker = None

        self.init_ui()
        self.detect_and_load_github()

    def refresh_dir(self):
        self.projects_dir = get_projects_dir(self.config_target)
        self.render_repos_list()

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(12)

        # -------------------------------------------------------------
        # 1. BARRA DE CONEXIÓN Y AUTENTICACIÓN
        # -------------------------------------------------------------
        top_card = QFrame()
        top_card.setProperty("class", "surface")
        l_top = QVBoxLayout(top_card)
        l_top.setSpacing(10)

        r_auth_status = QHBoxLayout()
        self.lbl_auth_status = QLabel("🔍 Verificando sesión de GitHub...")
        self.lbl_auth_status.setStyleSheet("font-weight: 600; font-size: 12px; color: #c084fc;")
        r_auth_status.addWidget(self.lbl_auth_status, 1)

        btn_reload = QPushButton("🔄 Actualizar Repositorios")
        btn_reload.setProperty("class", "btn_mode_purple")
        btn_reload.setCursor(Qt.PointingHandCursor)
        btn_reload.clicked.connect(self.detect_and_load_github)
        r_auth_status.addWidget(btn_reload)
        l_top.addLayout(r_auth_status)

        # Fila de Entrada Manual (Usuario de GitHub o Token)
        r_manual = QHBoxLayout()
        self.txt_github_user = QLineEdit()
        self.txt_github_user.setPlaceholderText("Usuario de GitHub o Token Personal (PAT) para repositorios privados...")
        self.txt_github_user.returnPressed.connect(self.load_from_input)
        
        btn_fetch = QPushButton("🔍 Explorar")
        btn_fetch.setProperty("class", "browse")
        btn_fetch.setCursor(Qt.PointingHandCursor)
        btn_fetch.clicked.connect(self.load_from_input)

        r_manual.addWidget(self.txt_github_user, 1)
        r_manual.addWidget(btn_fetch)
        l_top.addLayout(r_manual)

        root_layout.addWidget(top_card)

        # -------------------------------------------------------------
        # 2. FILTRO Y CONTADORES
        # -------------------------------------------------------------
        r_filter = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Filtrar repositorios por nombre, descripción o lenguaje...")
        self.txt_search.textChanged.connect(self.filter_repos)
        r_filter.addWidget(self.txt_search, 1)

        self.lbl_count = QLabel("0 repositorios")
        self.lbl_count.setProperty("class", "count_badge")
        r_filter.addWidget(self.lbl_count)
        root_layout.addLayout(r_filter)

        # -------------------------------------------------------------
        # 3. BARRA DE PROGRESO Y MENSAJE DE ESTADO
        # -------------------------------------------------------------
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        root_layout.addWidget(self.progress_bar)

        self.lbl_status = QLabel("")
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setStyleSheet("font-size: 12px; font-weight: 600; color: #a855f7;")
        self.lbl_status.setVisible(False)
        root_layout.addWidget(self.lbl_status)

        # -------------------------------------------------------------
        # 4. LISTA DE REPOSITORIOS EN RECUADRO UNIFICADO
        # -------------------------------------------------------------
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 8, 0)
        self.list_layout.setSpacing(0)

        self.unified_box = QFrame()
        self.unified_box.setProperty("class", "project_list_card")
        self.unified_box_layout = QVBoxLayout(self.unified_box)
        self.unified_box_layout.setContentsMargins(0, 0, 0, 0)
        self.unified_box_layout.setSpacing(0)

        self.list_layout.addWidget(self.unified_box)
        self.list_layout.addStretch()

        self.scroll_area.setWidget(self.list_container)
        root_layout.addWidget(self.scroll_area, 1)

    def detect_and_load_github(self):
        """Intenta cargar primero vía GitHub CLI 'gh' si está autenticado; de lo contrario pide usuario/token."""
        self.lbl_status.setVisible(False)
        is_auth, msg = check_gh_cli_authenticated()
        
        if is_auth:
            self.lbl_auth_status.setText(f"✅ Conectado a GitHub CLI ({msg})")
            self.lbl_auth_status.setStyleSheet("font-weight: 600; font-size: 12px; color: #10b981;")
            try:
                self.repos_data = fetch_repos_gh_cli()
                self.render_repos_list()
                return
            except Exception as e:
                self.lbl_status.setText(f"⚠️ {e}")
                self.lbl_status.setVisible(True)

        self.lbl_auth_status.setText("ℹ Ingresa tu usuario o Token de GitHub para explorar tus repositorios:")
        self.lbl_auth_status.setStyleSheet("font-weight: 600; font-size: 12px; color: #9ca3af;")

    def load_from_input(self):
        query = self.txt_github_user.text().strip()
        if not query:
            self.detect_and_load_github()
            return

        self.lbl_status.setText("⏳ Consultando repositorios en GitHub...")
        self.lbl_status.setStyleSheet("font-size: 12px; font-weight: 600; color: #a855f7;")
        self.lbl_status.setVisible(True)

        try:
            if query.startswith("ghp_") or query.startswith("github_pat_"):
                self.repos_data = fetch_repos_api(token=query)
            else:
                self.repos_data = fetch_repos_api(username=query)

            self.lbl_status.setVisible(False)
            self.render_repos_list()
        except Exception as e:
            self.lbl_status.setText(f"❌ {e}")
            self.lbl_status.setStyleSheet("font-size: 12px; font-weight: 600; color: #ef4444;")
            self.lbl_status.setVisible(True)

    def render_repos_list(self):
        while self.unified_box_layout.count():
            item = self.unified_box_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        self.card_widgets = []
        self.lbl_count.setText(f"{len(self.repos_data)} repositorios")

        if not self.repos_data:
            lbl_empty = QLabel("No se encontraron repositorios de GitHub. Ingresa tu usuario o conecta GitHub CLI.")
            lbl_empty.setProperty("class", "card_desc")
            lbl_empty.setContentsMargins(16, 16, 16, 16)
            self.unified_box_layout.addWidget(lbl_empty)
            return

        for idx, repo in enumerate(self.repos_data):
            card = GithubRepoCardWidget(repo, self.projects_dir, self.handle_repo_action)
            if idx == len(self.repos_data) - 1:
                card.setProperty("class", "project_row project_row_last")
            self.unified_box_layout.addWidget(card)
            
            search_str = f"{repo['name']} {repo.get('description', '')} {repo.get('language', '')}".lower()
            self.card_widgets.append((search_str, card))

        if self.txt_search.text().strip():
            self.filter_repos(self.txt_search.text().strip())

    def filter_repos(self, query):
        q = query.strip().lower()
        visible_count = 0
        for search_str, card in self.card_widgets:
            match = (q in search_str) if q else True
            card.setVisible(match)
            if match:
                visible_count += 1
        self.lbl_count.setText(f"{visible_count} repositorios")

    def handle_repo_action(self, action: str, repo_data: dict, target_path: str):
        clone_url = repo_data.get("clone_url") or repo_data.get("url")
        full_name = repo_data.get("full_name") or repo_data.get("name")
        repo_name = repo_data.get("name")

        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(True)
        self.lbl_status.setVisible(True)

        if action == "clone":
            self.lbl_status.setText(f"⏳ Clonando '{full_name}' en {target_path}...")
            self.lbl_status.setStyleSheet("font-size: 12px; font-weight: 600; color: #a855f7;")
            self.worker = GitActionWorker("clone", clone_url, target_path, full_name=full_name)
        else:
            self.lbl_status.setText(f"⏳ Actualizando '{repo_name}' (git pull)...")
            self.lbl_status.setStyleSheet("font-size: 12px; font-weight: 600; color: #a855f7;")
            self.worker = GitActionWorker("pull", clone_url, target_path, full_name=full_name)

        self.worker.finished.connect(self.on_git_action_finished)
        self.worker.start()

    def on_git_action_finished(self, success: bool, message: str, target_dir: str):
        self.progress_bar.setVisible(False)
        self.lbl_status.setText(message)
        
        if success:
            self.lbl_status.setStyleSheet("font-size: 12px; font-weight: 600; color: #10b981;")
            self.render_repos_list()
            if target_dir:
                self.project_synced.emit(target_dir)
        else:
            self.lbl_status.setStyleSheet("font-size: 12px; font-weight: 600; color: #ef4444;")
