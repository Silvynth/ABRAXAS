"""
❖ ABRAXAS 2.0 | Lumen UI: Sector 03 - Herramientas, Documentación & IA Local
Arquitectura de 3 Sub-sectores Tácticos:
- 3.1: Exclusiones & Secretos (.gitignore, presets automáticos, blindaje de .env y generación de .env.example)
- 3.2: Lector de Documentación & CHANGELOG (indexación de markdown, visor dual render/raw y generación con IA)
- 3.3: Auditoría & IA Local (telemetría de Ollama, auditoría de diffs recientes y análisis de seguridad)
"""

import os
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTextEdit, QSplitter, QScrollArea, QLineEdit,
    QCheckBox, QButtonGroup, QRadioButton, QMessageBox, QApplication,
    QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer, QThread
from PySide6.QtGui import QCursor, QTextCursor

from abraxas.lumen.models.project import Project
from abraxas.ui.controls.switcher_pill import SectorSwitcherPill
from core.environments import launch_project_in_editor, get_preferred_editor
from core.utilities import (
    inspect_gitignore_and_env, apply_gitignore_preset, add_custom_gitignore_rule,
    create_base_env_file, generate_env_example_file, scan_project_documentation,
    read_markdown_file, generate_ai_changelog, check_ollama_status,
    execute_history_ai_audit
)


# =====================================================================
# WORKERS ASÍNCRONOS (QThread) PARA IA NO BLOQUEANTE
# =====================================================================

class AIChangelogWorker(QThread):
    """Worker en segundo plano para generar CHANGELOG con IA sin congelar la GUI."""
    finished_generation = Signal(bool, str)

    def __init__(self, project_path: str, count: int = 15, parent=None):
        super().__init__(parent)
        self.project_path = project_path
        self.count = count

    def run(self):
        ok, res = generate_ai_changelog(self.project_path, count=self.count)
        self.finished_generation.emit(ok, res)


class AIAuditWorkerThread(QThread):
    """Worker en segundo plano para auditar diffs acumulados con Ollama."""
    finished_audit = Signal(bool, str)

    def __init__(self, project_path: str, commit_count: int = 5, model_choice: str = "light", parent=None):
        super().__init__(parent)
        self.project_path = project_path
        self.commit_count = commit_count
        self.model_choice = model_choice

    def run(self):
        ok, res = execute_history_ai_audit(self.project_path, commit_count=self.commit_count, model_choice=self.model_choice)
        self.finished_audit.emit(ok, res)


# =====================================================================
# SUB-SECTOR 3.1: EXCLUSIONES & SECRETOS (.GITIGNORE & .ENV)
# =====================================================================

class SubSector31GitignoreView(QWidget):
    """Sub-sector 3.1: Gestor inteligente de .gitignore, presets de stack y secretos .env."""

    log_emitted = Signal(str)
    action_requested = Signal(str, dict)

    def __init__(self, project: Project = None, parent=None):
        super().__init__(parent)
        self.project = project
        self.active_file_type = "gitignore"  # "gitignore", "env_example", "env"
        self.init_ui()

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        # -------------------------------------------------------------
        # PANEL IZQUIERDO: ACCIONES & TELEMETRÍA (42%)
        # -------------------------------------------------------------
        left_card = QFrame()
        left_card.setProperty("class", "sector_card")
        l_layout = QVBoxLayout(left_card)
        l_layout.setContentsMargins(14, 12, 14, 12)
        l_layout.setSpacing(10)

        # Encabezado
        head_box = QVBoxLayout()
        head_box.setSpacing(2)
        lbl_tag = QLabel("CONFIGURACIÓN // EXCLUSIONES & SECRETOS")
        lbl_tag.setProperty("class", "sector_micro_tag")
        lbl_title = QLabel("🛡 Gestor de .gitignore & .env")
        lbl_title.setProperty("class", "sector_title")
        head_box.addWidget(lbl_tag)
        head_box.addWidget(lbl_title)
        l_layout.addLayout(head_box)

        # Telemetría de estado
        telemetry_frame = QFrame()
        telemetry_frame.setProperty("class", "env_item_row")
        t_layout = QVBoxLayout(telemetry_frame)
        t_layout.setContentsMargins(10, 8, 10, 8)
        t_layout.setSpacing(6)

        t_row1 = QHBoxLayout()
        self.lbl_gitignore_status = QLabel("● .gitignore: 0 reglas")
        self.lbl_gitignore_status.setProperty("class", "badge_telemetry")
        t_row1.addWidget(self.lbl_gitignore_status)
        t_row1.addStretch()

        self.btn_refresh = QPushButton("🔄")
        self.btn_refresh.setProperty("class", "cyber_btn_compact")
        self.btn_refresh.setFixedSize(26, 26)
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.setToolTip("Recargar estado de exclusiones y entorno")
        self.btn_refresh.clicked.connect(self.refresh_status)
        t_row1.addWidget(self.btn_refresh)
        t_layout.addLayout(t_row1)

        t_row2 = QHBoxLayout()
        self.lbl_env_status = QLabel("○ .env: No detectado")
        self.lbl_env_status.setProperty("class", "badge_pending")
        t_row2.addWidget(self.lbl_env_status)

        self.lbl_example_badge = QLabel("Sin .env.example")
        self.lbl_example_badge.setProperty("class", "badge_telemetry")
        t_row2.addWidget(self.lbl_example_badge)
        t_row2.addStretch()
        t_layout.addLayout(t_row2)

        l_layout.addWidget(telemetry_frame)

        # Presets rápidos
        lbl_presets = QLabel("Inyectar Presets a .gitignore:")
        lbl_presets.setProperty("class", "sector_desc")
        l_layout.addWidget(lbl_presets)

        p_row1 = QHBoxLayout()
        p_row1.setSpacing(6)
        btn_pre_py = QPushButton("🐍 Python")
        btn_pre_py.setProperty("class", "cyber_btn_compact")
        btn_pre_py.setCursor(Qt.PointingHandCursor)
        btn_pre_py.setToolTip("Añade __pycache__, .venv, .pytest_cache, dist, etc.")
        btn_pre_py.clicked.connect(lambda: self._apply_preset("python"))
        p_row1.addWidget(btn_pre_py)

        btn_pre_node = QPushButton("🌐 Node / Web")
        btn_pre_node.setProperty("class", "cyber_btn_compact")
        btn_pre_node.setCursor(Qt.PointingHandCursor)
        btn_pre_node.setToolTip("Añade node_modules, .next, dist, build, etc.")
        btn_pre_node.clicked.connect(lambda: self._apply_preset("node"))
        p_row1.addWidget(btn_pre_node)

        btn_pre_ide = QPushButton("💻 IDEs & OS")
        btn_pre_ide.setProperty("class", "cyber_btn_compact")
        btn_pre_ide.setCursor(Qt.PointingHandCursor)
        btn_pre_ide.setToolTip("Añade .vscode, .idea, .DS_Store, *.swp, etc.")
        btn_pre_ide.clicked.connect(lambda: self._apply_preset("ide"))
        p_row1.addWidget(btn_pre_ide)
        l_layout.addLayout(p_row1)

        p_row2 = QHBoxLayout()
        p_row2.setSpacing(6)
        btn_pre_sec = QPushButton("🔐 Seguridad")
        btn_pre_sec.setProperty("class", "cyber_btn_compact")
        btn_pre_sec.setCursor(Qt.PointingHandCursor)
        btn_pre_sec.setToolTip("Blindaje de *.pem, *.key, secrets/, credentials.json, id_rsa, etc.")
        btn_pre_sec.clicked.connect(lambda: self._apply_preset("security"))
        p_row2.addWidget(btn_pre_sec)

        btn_pre_all = QPushButton("✨ Pack Completo")
        btn_pre_all.setProperty("class", "cyber_btn_primary")
        btn_pre_all.setCursor(Qt.PointingHandCursor)
        btn_pre_all.setToolTip("Aplica todos los presets combinados (Python + Node + IDEs + Seguridad)")
        btn_pre_all.clicked.connect(lambda: self._apply_preset("all"))
        p_row2.addWidget(btn_pre_all)
        l_layout.addLayout(p_row2)

        # Entrada para regla personalizada
        lbl_custom = QLabel("Añadir regla personalizada:")
        lbl_custom.setProperty("class", "sector_desc")
        l_layout.addWidget(lbl_custom)

        custom_row = QHBoxLayout()
        custom_row.setSpacing(6)
        self.txt_custom_rule = QLineEdit()
        self.txt_custom_rule.setProperty("class", "cyber_input")
        self.txt_custom_rule.setPlaceholderText("ej. *.log, temp/, cache/")
        self.txt_custom_rule.returnPressed.connect(self._add_custom_rule)
        custom_row.addWidget(self.txt_custom_rule, 1)

        btn_add_rule = QPushButton("+ Añadir")
        btn_add_rule.setProperty("class", "cyber_btn")
        btn_add_rule.setCursor(Qt.PointingHandCursor)
        btn_add_rule.clicked.connect(self._add_custom_rule)
        custom_row.addWidget(btn_add_rule)
        l_layout.addLayout(custom_row)

        # Acciones de variables de entorno (.env)
        lbl_env_actions = QLabel("Gestión de Entorno & Secretos:")
        lbl_env_actions.setProperty("class", "sector_desc")
        l_layout.addWidget(lbl_env_actions)

        env_btn_row = QHBoxLayout()
        env_btn_row.setSpacing(6)

        self.btn_create_env = QPushButton("✨ Crear .env")
        self.btn_create_env.setProperty("class", "cyber_btn_compact")
        self.btn_create_env.setCursor(Qt.PointingHandCursor)
        self.btn_create_env.setToolTip("Crea un archivo .env inicial y asegura su blindaje en .gitignore")
        self.btn_create_env.clicked.connect(self._create_env_file)
        env_btn_row.addWidget(self.btn_create_env)

        self.btn_gen_example = QPushButton("🛡 Generar .env.example")
        self.btn_gen_example.setProperty("class", "cyber_btn_compact")
        self.btn_gen_example.setCursor(Qt.PointingHandCursor)
        self.btn_gen_example.setToolTip("Genera una plantilla anonimizada para compartir en el repositorio")
        self.btn_gen_example.clicked.connect(self._gen_example_file)
        env_btn_row.addWidget(self.btn_gen_example)

        l_layout.addLayout(env_btn_row)

        # Abrir en editor
        self.btn_open_in_editor = QPushButton("🚀 Abrir en Editor de Código")
        self.btn_open_in_editor.setProperty("class", "cyber_btn")
        self.btn_open_in_editor.setCursor(Qt.PointingHandCursor)
        self.btn_open_in_editor.clicked.connect(self._open_project_in_editor)
        l_layout.addWidget(self.btn_open_in_editor)

        l_layout.addStretch()
        splitter.addWidget(left_card)

        # -------------------------------------------------------------
        # PANEL DERECHO: VISOR & EDITOR EN VIVO (58%)
        # -------------------------------------------------------------
        right_card = QFrame()
        right_card.setProperty("class", "sector_card")
        r_layout = QVBoxLayout(right_card)
        r_layout.setContentsMargins(14, 12, 14, 12)
        r_layout.setSpacing(8)

        # Selector de archivo activo
        file_nav = QHBoxLayout()
        file_nav.setSpacing(6)

        self.btn_view_gitignore = QPushButton("📄 .gitignore")
        self.btn_view_gitignore.setCheckable(True)
        self.btn_view_gitignore.setChecked(True)
        self.btn_view_gitignore.setProperty("class", "cyber_btn_toggle")
        self.btn_view_gitignore.setCursor(Qt.PointingHandCursor)
        self.btn_view_gitignore.clicked.connect(lambda: self._switch_file_view("gitignore"))
        file_nav.addWidget(self.btn_view_gitignore)

        self.btn_view_example = QPushButton("🔒 .env.example")
        self.btn_view_example.setCheckable(True)
        self.btn_view_example.setProperty("class", "cyber_btn_toggle")
        self.btn_view_example.setCursor(Qt.PointingHandCursor)
        self.btn_view_example.clicked.connect(lambda: self._switch_file_view("env_example"))
        file_nav.addWidget(self.btn_view_example)

        self.btn_view_env = QPushButton("⚙ .env (Local)")
        self.btn_view_env.setCheckable(True)
        self.btn_view_env.setProperty("class", "cyber_btn_toggle")
        self.btn_view_env.setCursor(Qt.PointingHandCursor)
        self.btn_view_env.clicked.connect(lambda: self._switch_file_view("env"))
        file_nav.addWidget(self.btn_view_env)

        file_nav.addStretch()

        self.btn_save_file = QPushButton("💾 Guardar")
        self.btn_save_file.setProperty("class", "cyber_btn_primary")
        self.btn_save_file.setCursor(Qt.PointingHandCursor)
        self.btn_save_file.clicked.connect(self._save_active_file)
        file_nav.addWidget(self.btn_save_file)

        r_layout.addLayout(file_nav)

        self.lbl_active_filepath = QLabel(".gitignore")
        self.lbl_active_filepath.setStyleSheet("font-family: 'JetBrains Mono', monospace; font-size: 10px; color: #94a3b8;")
        r_layout.addWidget(self.lbl_active_filepath)

        self.txt_editor = QTextEdit()
        self.txt_editor.setProperty("class", "cyber_terminal")
        self.txt_editor.setStyleSheet(
            "background-color: #0c0d10; border: 1px solid rgba(255, 255, 255, 0.08); "
            "border-radius: 6px; padding: 10px; color: #e2e8f0; font-family: 'JetBrains Mono', monospace; font-size: 11px;"
        )
        r_layout.addWidget(self.txt_editor, 1)

        splitter.addWidget(right_card)
        splitter.setSizes([420, 580])
        root_layout.addWidget(splitter, 1)

    def update_project(self, project: Project):
        self.project = project
        self.refresh_status()

    def refresh_status(self):
        """Inspecciona y actualiza la vista de exclusiones y variables."""
        if not self.project or not self.project.path:
            return

        p_path = str(self.project.path)
        info = inspect_gitignore_and_env(p_path)

        if info.get("has_gitignore"):
            self.lbl_gitignore_status.setText(f"● .gitignore: {info.get('rules_count', 0)} reglas")
            self.lbl_gitignore_status.setProperty("class", "badge_staged")
        else:
            self.lbl_gitignore_status.setText("○ Sin .gitignore")
            self.lbl_gitignore_status.setProperty("class", "badge_pending")

        if info.get("has_env"):
            if info.get("env_is_ignored"):
                self.lbl_env_status.setText(f"● .env Blindado ({info.get('env_vars_count', 0)} vars)")
                self.lbl_env_status.setProperty("class", "badge_staged")
            else:
                self.lbl_env_status.setText("⚠️ .env EXPUESTO (Sin ignorar)")
                self.lbl_env_status.setProperty("class", "badge_pending")
            self.btn_create_env.setEnabled(False)
            self.btn_gen_example.setEnabled(True)
        else:
            self.lbl_env_status.setText("○ Sin .env")
            self.lbl_env_status.setProperty("class", "badge_pending")
            self.btn_create_env.setEnabled(True)
            self.btn_gen_example.setEnabled(False)

        if info.get("has_example"):
            self.lbl_example_badge.setText("● .env.example disponible")
            self.lbl_example_badge.setProperty("class", "badge_staged")
        else:
            self.lbl_example_badge.setText("Sin .env.example")
            self.lbl_example_badge.setProperty("class", "badge_telemetry")

        self.lbl_gitignore_status.style().unpolish(self.lbl_gitignore_status)
        self.lbl_gitignore_status.style().polish(self.lbl_gitignore_status)
        self.lbl_env_status.style().unpolish(self.lbl_env_status)
        self.lbl_env_status.style().polish(self.lbl_env_status)

        self._load_active_file_content()

    def _switch_file_view(self, file_type: str):
        self.active_file_type = file_type
        self.btn_view_gitignore.setChecked(file_type == "gitignore")
        self.btn_view_example.setChecked(file_type == "env_example")
        self.btn_view_env.setChecked(file_type == "env")
        self._load_active_file_content()

    def _get_active_file_path(self) -> str:
        if not self.project or not self.project.path:
            return ""
        p_path = str(self.project.path)
        if self.active_file_type == "gitignore":
            return os.path.join(p_path, ".gitignore")
        elif self.active_file_type == "env_example":
            return os.path.join(p_path, ".env.example")
        else:
            return os.path.join(p_path, ".env")

    def _load_active_file_content(self):
        f_path = self._get_active_file_path()
        if not f_path:
            self.txt_editor.clear()
            return

        rel_name = os.path.basename(f_path)
        self.lbl_active_filepath.setText(f_path)

        if os.path.exists(f_path):
            try:
                with open(f_path, "r", encoding="utf-8", errors="ignore") as f:
                    self.txt_editor.setPlainText(f.read())
            except Exception as e:
                self.txt_editor.setPlainText(f"Error al abrir {rel_name}: {e}")
        else:
            self.txt_editor.setPlainText(f"# El archivo '{rel_name}' no existe aún en la raíz del proyecto.")

    def _save_active_file(self):
        f_path = self._get_active_file_path()
        if not f_path:
            return
        content = self.txt_editor.toPlainText()
        try:
            with open(f_path, "w", encoding="utf-8") as f:
                f.write(content)
            self.log_emitted.emit(f"💾 Guardado: <b>{os.path.basename(f_path)}</b>.")
            self.refresh_status()
        except Exception as e:
            self.log_emitted.emit(f"⚠️ Error al guardar: {e}")

    def _apply_preset(self, preset_type: str):
        if not self.project or not self.project.path:
            return
        p_path = str(self.project.path)
        ok, msg, count = apply_gitignore_preset(p_path, preset_type)
        if ok:
            self.log_emitted.emit(f"✨ Preset [{preset_type.upper()}]: {msg}")
        else:
            self.log_emitted.emit(f"⚠️ Error al aplicar preset: {msg}")
        self.refresh_status()

    def _add_custom_rule(self):
        rule = self.txt_custom_rule.text().strip()
        if not rule or not self.project or not self.project.path:
            return
        p_path = str(self.project.path)
        ok, msg = add_custom_gitignore_rule(p_path, rule)
        if ok:
            self.log_emitted.emit(f"✔ {msg}")
            self.txt_custom_rule.clear()
        else:
            self.log_emitted.emit(f"⚠️ {msg}")
        self.refresh_status()

    def _create_env_file(self):
        if not self.project or not self.project.path:
            return
        p_path = str(self.project.path)
        ok, msg = create_base_env_file(p_path)
        if ok:
            self.log_emitted.emit(f"✨ {msg}")
            self._switch_file_view("env")
        else:
            self.log_emitted.emit(f"⚠️ {msg}")
        self.refresh_status()

    def _gen_example_file(self):
        if not self.project or not self.project.path:
            return
        p_path = str(self.project.path)
        ok, msg = generate_env_example_file(p_path)
        if ok:
            self.log_emitted.emit(f"✨ {msg}")
            self._switch_file_view("env_example")
        else:
            self.log_emitted.emit(f"⚠️ {msg}")
        self.refresh_status()

    def _open_project_in_editor(self):
        if not self.project or not self.project.path:
            return
        ed_id = get_preferred_editor()
        p_path = str(self.project.path)
        self.log_emitted.emit(f"🚀 Abriendo proyecto con <b>{ed_id}</b>...")
        ok, msg = launch_project_in_editor(ed_id, p_path)
        if ok:
            self.log_emitted.emit(f"✨ {msg}")
        else:
            self.log_emitted.emit(f"⚠️ {msg}")


# =====================================================================
# SUB-SECTOR 3.2: LECTOR DE DOCUMENTACIÓN & CHANGELOG IA
# =====================================================================

class SubSector32DocsView(QWidget):
    """Sub-sector 3.2: Escáner interactivo de Markdown y generador de CHANGELOG con IA."""

    log_emitted = Signal(str)
    action_requested = Signal(str, dict)

    def __init__(self, project: Project = None, parent=None):
        super().__init__(parent)
        self.project = project
        self.scanned_docs: List[Dict] = []
        self.selected_doc: Optional[Dict] = None
        self.view_mode = "rendered"  # "rendered" vs "raw"
        self._changelog_worker: Optional[AIChangelogWorker] = None
        self.init_ui()

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        # -------------------------------------------------------------
        # PANEL IZQUIERDO: ÍNDICE DE DOCUMENTACIÓN & CHANGELOG IA (35%)
        # -------------------------------------------------------------
        left_card = QFrame()
        left_card.setProperty("class", "sector_card")
        l_layout = QVBoxLayout(left_card)
        l_layout.setContentsMargins(14, 12, 14, 12)
        l_layout.setSpacing(10)

        # Encabezado
        head_box = QVBoxLayout()
        head_box.setSpacing(2)
        lbl_tag = QLabel("DOCUMENTACIÓN // ÍNDICE TÁCTICO")
        lbl_tag.setProperty("class", "sector_micro_tag")
        lbl_title = QLabel("📖 Documentos & Markdown")
        lbl_title.setProperty("class", "sector_title")
        head_box.addWidget(lbl_tag)
        head_box.addWidget(lbl_title)
        l_layout.addLayout(head_box)

        # Barra de búsqueda / recarga de docs
        search_row = QHBoxLayout()
        search_row.setSpacing(6)
        self.txt_filter_docs = QLineEdit()
        self.txt_filter_docs.setProperty("class", "cyber_input")
        self.txt_filter_docs.setPlaceholderText("Buscar documentos...")
        self.txt_filter_docs.textChanged.connect(self._filter_docs)
        search_row.addWidget(self.txt_filter_docs, 1)

        btn_rescan = QPushButton("🔄")
        btn_rescan.setProperty("class", "cyber_btn_compact")
        btn_rescan.setFixedSize(28, 28)
        btn_rescan.setCursor(Qt.PointingHandCursor)
        btn_rescan.setToolTip("Re-escanear documentos Markdown en el proyecto")
        btn_rescan.clicked.connect(self.scan_documents)
        search_row.addWidget(btn_rescan)
        l_layout.addLayout(search_row)

        # Conteo
        self.lbl_docs_count = QLabel("0 documentos encontrados")
        self.lbl_docs_count.setProperty("class", "badge_telemetry")
        l_layout.addWidget(self.lbl_docs_count)

        # Lista scrolleable de documentos
        scroll = QScrollArea()
        scroll.setProperty("class", "clean_scroll")
        scroll.setWidgetResizable(True)

        self.docs_container = QWidget()
        self.docs_layout = QVBoxLayout(self.docs_container)
        self.docs_layout.setContentsMargins(0, 0, 0, 0)
        self.docs_layout.setSpacing(4)
        scroll.setWidget(self.docs_container)
        l_layout.addWidget(scroll, 1)

        # Generador de CHANGELOG IA
        ai_box = QFrame()
        ai_box.setProperty("class", "env_item_row")
        ab_l = QVBoxLayout(ai_box)
        ab_l.setContentsMargins(10, 8, 10, 8)
        ab_l.setSpacing(6)

        lbl_ai_t = QLabel("SÍNTESIS // CHANGELOG AUTOMÁTICO")
        lbl_ai_t.setProperty("class", "sector_micro_tag")
        ab_l.addWidget(lbl_ai_t)

        self.btn_gen_changelog = QPushButton("📝 Generar CHANGELOG con IA")
        self.btn_gen_changelog.setProperty("class", "cyber_btn_primary")
        self.btn_gen_changelog.setCursor(Qt.PointingHandCursor)
        self.btn_gen_changelog.setToolTip("Sintetiza los últimos 15 commits en un archivo CHANGELOG estructurado mediante Ollama")
        self.btn_gen_changelog.clicked.connect(self._start_changelog_generation)
        ab_l.addWidget(self.btn_gen_changelog)

        l_layout.addWidget(ai_box)
        splitter.addWidget(left_card)

        # -------------------------------------------------------------
        # PANEL DERECHO: VISOR MARKDOWN DUAL (65%)
        # -------------------------------------------------------------
        right_card = QFrame()
        right_card.setProperty("class", "sector_card")
        r_layout = QVBoxLayout(right_card)
        r_layout.setContentsMargins(14, 12, 14, 12)
        r_layout.setSpacing(8)

        # Toolbar superior del visor
        v_toolbar = QHBoxLayout()
        v_toolbar.setSpacing(6)

        self.lbl_viewer_filename = QLabel("Selecciona un documento para visualizar...")
        self.lbl_viewer_filename.setProperty("class", "sector_title")
        v_toolbar.addWidget(self.lbl_viewer_filename, 1)

        self.btn_mode_rendered = QPushButton("👁 Renderizado")
        self.btn_mode_rendered.setCheckable(True)
        self.btn_mode_rendered.setChecked(True)
        self.btn_mode_rendered.setProperty("class", "cyber_btn_toggle")
        self.btn_mode_rendered.setCursor(Qt.PointingHandCursor)
        self.btn_mode_rendered.clicked.connect(lambda: self._set_view_mode("rendered"))
        v_toolbar.addWidget(self.btn_mode_rendered)

        self.btn_mode_raw = QPushButton("📝 Código (Raw)")
        self.btn_mode_raw.setCheckable(True)
        self.btn_mode_raw.setProperty("class", "cyber_btn_toggle")
        self.btn_mode_raw.setCursor(Qt.PointingHandCursor)
        self.btn_mode_raw.clicked.connect(lambda: self._set_view_mode("raw"))
        v_toolbar.addWidget(self.btn_mode_raw)

        self.btn_save_doc = QPushButton("💾 Guardar")
        self.btn_save_doc.setProperty("class", "cyber_btn_compact")
        self.btn_save_doc.setCursor(Qt.PointingHandCursor)
        self.btn_save_doc.clicked.connect(self._save_current_doc)
        v_toolbar.addWidget(self.btn_save_doc)

        self.btn_copy_doc = QPushButton("📋")
        self.btn_copy_doc.setProperty("class", "cyber_btn_compact")
        self.btn_copy_doc.setFixedSize(28, 28)
        self.btn_copy_doc.setCursor(Qt.PointingHandCursor)
        self.btn_copy_doc.setToolTip("Copiar contenido al portapapeles")
        self.btn_copy_doc.clicked.connect(self._copy_doc_content)
        v_toolbar.addWidget(self.btn_copy_doc)

        r_layout.addLayout(v_toolbar)

        # Visor de documento
        self.txt_doc_viewer = QTextEdit()
        self.txt_doc_viewer.setProperty("class", "cyber_terminal")
        self.txt_doc_viewer.setStyleSheet(
            "background-color: #0c0d10; border: 1px solid rgba(255, 255, 255, 0.08); "
            "border-radius: 6px; padding: 12px; color: #e2e8f0; font-family: 'JetBrains Mono', monospace; font-size: 11px;"
        )
        r_layout.addWidget(self.txt_doc_viewer, 1)

        splitter.addWidget(right_card)
        splitter.setSizes([350, 650])
        root_layout.addWidget(splitter, 1)

    def update_project(self, project: Project):
        self.project = project
        self.scan_documents()

    def scan_documents(self):
        """Escanea los documentos Markdown en el proyecto."""
        if not self.project or not self.project.path:
            return

        p_path = str(self.project.path)
        self.scanned_docs = scan_project_documentation(p_path)
        self.lbl_docs_count.setText(f"{len(self.scanned_docs)} documentos")
        self._render_docs_list(self.scanned_docs)

        # Auto-seleccionar README si existe y no hay documento seleccionado
        if self.scanned_docs and not self.selected_doc:
            readme = next((d for d in self.scanned_docs if d.get("is_readme")), self.scanned_docs[0])
            self._select_doc(readme)

    def _render_docs_list(self, docs: List[Dict]):
        while self.docs_layout.count():
            item = self.docs_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not docs:
            lbl_empty = QLabel("No se encontraron archivos Markdown en el proyecto.")
            lbl_empty.setProperty("class", "sector_desc")
            self.docs_layout.addWidget(lbl_empty)
            self.docs_layout.addStretch()
            return

        for doc in docs:
            rel = doc.get("relative", "")
            size_kb = doc.get("size_kb", 0)
            is_active = (self.selected_doc and self.selected_doc.get("path") == doc.get("path"))

            row = QFrame()
            row.setProperty("class", "env_item_row_active" if is_active else "env_item_row")
            r_l = QHBoxLayout(row)
            r_l.setContentsMargins(8, 6, 8, 6)
            r_l.setSpacing(6)

            icon = "📖" if doc.get("is_readme") else "📄"
            lbl_i = QLabel(icon)
            r_l.addWidget(lbl_i)

            lbl_name = QLabel(f"<b>{doc.get('name')}</b>")
            lbl_name.setProperty("class", "file_path_label")
            r_l.addWidget(lbl_name)
            r_l.addStretch()

            lbl_sz = QLabel(f"{size_kb} KB")
            lbl_sz.setProperty("class", "badge_telemetry")
            r_l.addWidget(lbl_sz)

            btn_open = QPushButton("Ver")
            btn_open.setProperty("class", "cyber_btn_compact")
            btn_open.setCursor(Qt.PointingHandCursor)
            btn_open.clicked.connect(lambda _, d=doc: self._select_doc(d))
            r_l.addWidget(btn_open)

            self.docs_layout.addWidget(row)

        self.docs_layout.addStretch()

    def _filter_docs(self, query: str):
        q = query.strip().lower()
        if not q:
            self._render_docs_list(self.scanned_docs)
            return
        filtered = [d for d in self.scanned_docs if q in d.get("relative", "").lower()]
        self._render_docs_list(filtered)

    def _select_doc(self, doc: Dict):
        self.selected_doc = doc
        self.lbl_viewer_filename.setText(f"📄 {doc.get('relative')}")
        content = read_markdown_file(doc.get("path", ""))
        self._display_content(content)
        self._render_docs_list(self.scanned_docs)

    def _set_view_mode(self, mode: str):
        self.view_mode = mode
        self.btn_mode_rendered.setChecked(mode == "rendered")
        self.btn_mode_raw.setChecked(mode == "raw")
        if self.selected_doc:
            content = read_markdown_file(self.selected_doc.get("path", ""))
            self._display_content(content)

    def _display_content(self, text: str):
        if self.view_mode == "rendered":
            self.txt_doc_viewer.setMarkdown(text)
        else:
            self.txt_doc_viewer.setPlainText(text)

    def _save_current_doc(self):
        if not self.selected_doc:
            return
        f_path = self.selected_doc.get("path")
        content = self.txt_doc_viewer.toPlainText()
        try:
            with open(f_path, "w", encoding="utf-8") as f:
                f.write(content)
            self.log_emitted.emit(f"💾 Documento guardado: <b>{self.selected_doc.get('name')}</b>")
            self.scan_documents()
        except Exception as e:
            self.log_emitted.emit(f"⚠️ Error al guardar documento: {e}")

    def _copy_doc_content(self):
        content = self.txt_doc_viewer.toPlainText()
        if content:
            QApplication.clipboard().setText(content)
            self.log_emitted.emit("📋 Contenido copiado al portapapeles.")

    def _start_changelog_generation(self):
        if not self.project or not self.project.path:
            return
        p_path = str(self.project.path)
        self.btn_gen_changelog.setEnabled(False)
        self.btn_gen_changelog.setText("⏳ Sintetizando CHANGELOG...")
        self.log_emitted.emit("🤖 Iniciando síntesis de CHANGELOG con IA de Ollama local...")

        self._changelog_worker = AIChangelogWorker(p_path, count=15, parent=self)
        self._changelog_worker.finished_generation.connect(self._on_changelog_finished)
        self._changelog_worker.start()

    def _on_changelog_finished(self, success: bool, content: str):
        self.btn_gen_changelog.setEnabled(True)
        self.btn_gen_changelog.setText("📝 Generar CHANGELOG con IA")
        if success:
            self.lbl_viewer_filename.setText("✨ CHANGELOG.md (Generado con IA)")
            self._display_content(content)
            self.log_emitted.emit("✨ CHANGELOG.md generado exitosamente con IA local.")

            # Sugerir guardar a CHANGELOG.md
            reply = QMessageBox.question(
                self,
                "Guardar CHANGELOG.md",
                "¿Deseas guardar la propuesta generada en el archivo CHANGELOG.md del proyecto?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes and self.project:
                target_f = os.path.join(str(self.project.path), "CHANGELOG.md")
                with open(target_f, "w", encoding="utf-8") as f:
                    f.write(content)
                self.log_emitted.emit("💾 Archivo <b>CHANGELOG.md</b> creado y guardado.")
                self.scan_documents()
        else:
            self.log_emitted.emit(f"⚠️ Error en la generación de CHANGELOG: {content}")

    def teardown(self):
        if self._changelog_worker and self._changelog_worker.isRunning():
            self._changelog_worker.terminate()
            self._changelog_worker.wait(300)


# =====================================================================
# SUB-SECTOR 3.3: AUDITORÍA & IA LOCAL (OLLAMA)
# =====================================================================

class SubSector33AiAuditView(QWidget):
    """Sub-sector 3.3: Auditoría semántica de código y telemetría de Ollama local."""

    log_emitted = Signal(str)
    action_requested = Signal(str, dict)

    def __init__(self, project: Project = None, parent=None):
        super().__init__(parent)
        self.project = project
        self._audit_worker: Optional[AIAuditWorkerThread] = None
        self.init_ui()

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        # -------------------------------------------------------------
        # PANEL IZQUIERDO: CONTROLES & ESTADO OLLAMA (40%)
        # -------------------------------------------------------------
        left_card = QFrame()
        left_card.setProperty("class", "sector_card")
        l_layout = QVBoxLayout(left_card)
        l_layout.setContentsMargins(14, 12, 14, 12)
        l_layout.setSpacing(10)

        # Encabezado
        head_box = QVBoxLayout()
        head_box.setSpacing(2)
        lbl_tag = QLabel("INTELIGENCIA // OLLAMA LOCAL")
        lbl_tag.setProperty("class", "sector_micro_tag")
        lbl_title = QLabel("🧠 Copiloto & Auditoría de Código")
        lbl_title.setProperty("class", "sector_title")
        head_box.addWidget(lbl_tag)
        head_box.addWidget(lbl_title)
        l_layout.addLayout(head_box)

        # Estado del demonio Ollama
        ollama_frame = QFrame()
        ollama_frame.setProperty("class", "env_item_row")
        of_l = QVBoxLayout(ollama_frame)
        of_l.setContentsMargins(10, 8, 10, 8)
        of_l.setSpacing(6)

        of_head = QHBoxLayout()
        self.lbl_ollama_badge = QLabel("○ Ollama Desconectado")
        self.lbl_ollama_badge.setProperty("class", "badge_pending")
        of_head.addWidget(self.lbl_ollama_badge)
        of_head.addStretch()

        self.btn_refresh_ollama = QPushButton("🔄")
        self.btn_refresh_ollama.setProperty("class", "cyber_btn_compact")
        self.btn_refresh_ollama.setFixedSize(26, 26)
        self.btn_refresh_ollama.setCursor(Qt.PointingHandCursor)
        self.btn_refresh_ollama.setToolTip("Verificar conexión con Ollama en localhost:11434")
        self.btn_refresh_ollama.clicked.connect(self.check_service_status)
        of_head.addWidget(self.btn_refresh_ollama)
        of_l.addLayout(of_head)

        self.lbl_ollama_models = QLabel("Modelos: Verificando...")
        self.lbl_ollama_models.setProperty("class", "sector_desc")
        self.lbl_ollama_models.setWordWrap(True)
        of_l.addWidget(self.lbl_ollama_models)

        l_layout.addWidget(ollama_frame)

        # Parámetros de Auditoría de Diffs
        lbl_audit_cfg = QLabel("Profundidad de Auditoría (Historial):")
        lbl_audit_cfg.setProperty("class", "sector_desc")
        l_layout.addWidget(lbl_audit_cfg)

        self.diff_depth_group = QButtonGroup(self)
        depth_row = QHBoxLayout()
        depth_row.setSpacing(6)

        self.rb_depth_3 = QRadioButton("3 commits")
        self.rb_depth_5 = QRadioButton("5 commits")
        self.rb_depth_10 = QRadioButton("10 commits")
        self.rb_depth_5.setChecked(True)

        self.diff_depth_group.addButton(self.rb_depth_3, 3)
        self.diff_depth_group.addButton(self.rb_depth_5, 5)
        self.diff_depth_group.addButton(self.rb_depth_10, 10)

        depth_row.addWidget(self.rb_depth_3)
        depth_row.addWidget(self.rb_depth_5)
        depth_row.addWidget(self.rb_depth_10)
        depth_row.addStretch()
        l_layout.addLayout(depth_row)

        # Selección de Modelo
        lbl_model_cfg = QLabel("Modelo de Inferencia:")
        lbl_model_cfg.setProperty("class", "sector_desc")
        l_layout.addWidget(lbl_model_cfg)

        model_row = QHBoxLayout()
        model_row.setSpacing(6)
        self.model_group = QButtonGroup(self)

        self.rb_model_light = QRadioButton("⚡ Ligero (7B)")
        self.rb_model_heavy = QRadioButton("🧠 Robusto (14B+)")
        self.rb_model_light.setChecked(True)

        self.model_group.addButton(self.rb_model_light, 1)
        self.model_group.addButton(self.rb_model_heavy, 2)

        model_row.addWidget(self.rb_model_light)
        model_row.addWidget(self.rb_model_heavy)
        model_row.addStretch()
        l_layout.addLayout(model_row)

        # Botón de disparo de auditoría
        self.btn_run_audit = QPushButton("🛡 Iniciar Auditoría de Diffs")
        self.btn_run_audit.setProperty("class", "cyber_btn_primary")
        self.btn_run_audit.setCursor(Qt.PointingHandCursor)
        self.btn_run_audit.setToolTip("Analiza el diff acumulado de los últimos commits buscando vulnerabilidades y regresiones")
        self.btn_run_audit.clicked.connect(self._start_audit)
        l_layout.addWidget(self.btn_run_audit)

        l_layout.addStretch()
        splitter.addWidget(left_card)

        # -------------------------------------------------------------
        # PANEL DERECHO: REPORTE & VISOR DE AUDITORÍA (60%)
        # -------------------------------------------------------------
        right_card = QFrame()
        right_card.setProperty("class", "sector_card")
        r_layout = QVBoxLayout(right_card)
        r_layout.setContentsMargins(14, 12, 14, 12)
        r_layout.setSpacing(8)

        # Encabezado reporte
        rep_head = QHBoxLayout()
        rep_head.setSpacing(6)

        lbl_rep_t = QLabel("📄 Informe Técnico de Auditoría")
        lbl_rep_t.setProperty("class", "sector_title")
        rep_head.addWidget(lbl_rep_t)
        rep_head.addStretch()

        self.btn_copy_audit = QPushButton("📋 Copiar Reporte")
        self.btn_copy_audit.setProperty("class", "cyber_btn_compact")
        self.btn_copy_audit.setCursor(Qt.PointingHandCursor)
        self.btn_copy_audit.clicked.connect(self._copy_audit_report)
        rep_head.addWidget(self.btn_copy_audit)

        self.btn_clear_audit = QPushButton("🗑")
        self.btn_clear_audit.setProperty("class", "cyber_btn_compact")
        self.btn_clear_audit.setFixedSize(28, 28)
        self.btn_clear_audit.setCursor(Qt.PointingHandCursor)
        self.btn_clear_audit.setToolTip("Limpiar reporte de la pantalla")
        self.btn_clear_audit.clicked.connect(lambda: self.txt_audit_display.clear())
        rep_head.addWidget(self.btn_clear_audit)

        r_layout.addLayout(rep_head)

        # Visor del reporte
        self.txt_audit_display = QTextEdit()
        self.txt_audit_display.setProperty("class", "cyber_terminal")
        self.txt_audit_display.setReadOnly(True)
        self.txt_audit_display.setPlaceholderText(
            "Configura la profundidad y pulsa 'Iniciar Auditoría' para evaluar el código con IA local..."
        )
        self.txt_audit_display.setStyleSheet(
            "background-color: #0c0d10; border: 1px solid rgba(255, 255, 255, 0.08); "
            "border-radius: 6px; padding: 12px; color: #e2e8f0; font-family: 'JetBrains Mono', monospace; font-size: 11px;"
        )
        r_layout.addWidget(self.txt_audit_display, 1)

        splitter.addWidget(right_card)
        splitter.setSizes([400, 600])
        root_layout.addWidget(splitter, 1)

        self.check_service_status()

    def update_project(self, project: Project):
        self.project = project
        self.check_service_status()

    def check_service_status(self):
        """Verifica la conectividad con el daemon de Ollama."""
        status = check_ollama_status()
        if status.get("running"):
            self.lbl_ollama_badge.setText("● Ollama Activo (localhost:11434)")
            self.lbl_ollama_badge.setProperty("class", "badge_staged")
            models = status.get("models", [])
            if models:
                mod_str = ", ".join(models[:4])
                if len(models) > 4:
                    mod_str += f" (+{len(models)-4} más)"
                self.lbl_ollama_models.setText(f"Modelos detectados: <b>{mod_str}</b>")
            else:
                self.lbl_ollama_models.setText("Ollama conectado pero sin modelos instalados en la biblioteca.")
            self.btn_run_audit.setEnabled(True)
        else:
            self.lbl_ollama_badge.setText("○ Ollama Inactivo")
            self.lbl_ollama_badge.setProperty("class", "badge_pending")
            self.lbl_ollama_models.setText("Servicio Ollama no responde en localhost:11434.")
            self.btn_run_audit.setEnabled(False)

        self.lbl_ollama_badge.style().unpolish(self.lbl_ollama_badge)
        self.lbl_ollama_badge.style().polish(self.lbl_ollama_badge)

    def _start_audit(self):
        if not self.project or not self.project.path:
            return
        p_path = str(self.project.path)
        depth = self.diff_depth_group.checkedId() or 5
        model_type = "heavy" if self.rb_model_heavy.isChecked() else "light"

        self.btn_run_audit.setEnabled(False)
        self.btn_run_audit.setText("⏳ Auditando código...")
        self.txt_audit_display.setPlainText(
            f"🔍 Extrayendo diff de los últimos {depth} commits y enviando a Ollama ({model_type})...\n"
            "Por favor espera, este análisis examina vulnerabilidades, regresiones y coherencia de arquitectura."
        )
        self.log_emitted.emit(f"🛡 Iniciando auditoría con IA local de los últimos {depth} commits...")

        self._audit_worker = AIAuditWorkerThread(p_path, commit_count=depth, model_choice=model_type, parent=self)
        self._audit_worker.finished_audit.connect(self._on_audit_finished)
        self._audit_worker.start()

    def _on_audit_finished(self, success: bool, report: str):
        self.btn_run_audit.setEnabled(True)
        self.btn_run_audit.setText("🛡 Iniciar Auditoría de Diffs")
        if success:
            self.txt_audit_display.setMarkdown(report)
            self.log_emitted.emit("✨ Auditoría de código completada exitosamente.")
        else:
            self.txt_audit_display.setPlainText(f"Error en la auditoría:\n{report}")
            self.log_emitted.emit(f"⚠️ {report}")

    def _copy_audit_report(self):
        text = self.txt_audit_display.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            self.log_emitted.emit("📋 Reporte copiado al portapapeles.")

    def teardown(self):
        if self._audit_worker and self._audit_worker.isRunning():
            self._audit_worker.terminate()
            self._audit_worker.wait(300)


# =====================================================================
# VISTA PRINCIPAL DEL SECTOR 03: HERRAMIENTAS & IA
# =====================================================================

class Sector3AiView(QWidget):
    """
    Sector táctico 03: Agentes IA locales, análisis de seguridad y documentación.
    Incorpora los 3 subsectores:
    - 3.1: Exclusiones & Secretos (.gitignore & .env)
    - 3.2: Lector de Documentación & CHANGELOG IA
    - 3.3: Auditoría & IA Local (Ollama)
    """

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
        root_layout.setSpacing(8)

        # -------------------------------------------------------------
        # PÍLDORA SELECTORA DE SUB-SECTORES (Pill Switcher)
        # -------------------------------------------------------------
        sub_sectors = [
            ("🛡  3.1 EXCLUSIONES & SECRETOS", "Gestor inteligente de .gitignore, presets y protección de variables .env"),
            ("📖  3.2 DOCUMENTACIÓN & DOCS", "Lector interactivo de Markdown y generador de CHANGELOG con IA"),
            ("🧠  3.3 AUDITORÍA & IA LOCAL", "Auditoría semántica de código con Ollama y verificación de seguridad")
        ]
        self.sub_pill = SectorSwitcherPill(sectors=sub_sectors)
        self.sub_pill.sector_changed.connect(self.switch_sub_sector)
        root_layout.addWidget(self.sub_pill)

        # -------------------------------------------------------------
        # STACK DE SUB-SECTORES (QStackedWidget)
        # -------------------------------------------------------------
        from PySide6.QtWidgets import QStackedWidget
        self.sub_stack = QStackedWidget()

        # 3.1 Exclusiones & Secretos
        self.sub31_view = SubSector31GitignoreView(self.project)
        self.sub31_view.log_emitted.connect(self.log_emitted.emit)
        self.sub31_view.action_requested.connect(self.action_requested.emit)
        self.sub_stack.addWidget(self.sub31_view)

        # 3.2 Documentación & CHANGELOG
        self.sub32_view = SubSector32DocsView(self.project)
        self.sub32_view.log_emitted.connect(self.log_emitted.emit)
        self.sub32_view.action_requested.connect(self.action_requested.emit)
        self.sub_stack.addWidget(self.sub32_view)

        # 3.3 Auditoría & IA Local
        self.sub33_view = SubSector33AiAuditView(self.project)
        self.sub33_view.log_emitted.connect(self.log_emitted.emit)
        self.sub33_view.action_requested.connect(self.action_requested.emit)
        self.sub_stack.addWidget(self.sub33_view)

        root_layout.addWidget(self.sub_stack, 1)

        # Abrir por defecto el Sub-sector 3.1
        self.sub_stack.setCurrentIndex(0)
        self.sub_pill.select_sector(0)

    def switch_sub_sector(self, index: int):
        """Cambia fluidamente entre los 3 sub-sectores tácticos."""
        self.sub_stack.setCurrentIndex(index)
        names = ["3.1 Exclusiones & Secretos", "3.2 Documentación & Docs", "3.3 Auditoría & IA Local"]
        if 0 <= index < len(names):
            self.log_emitted.emit(f"Sub-sector activo: <b>{names[index]}</b>")

        if index == 0 and hasattr(self, "sub31_view"):
            self.sub31_view.update_project(self.project)
        elif index == 1 and hasattr(self, "sub32_view"):
            self.sub32_view.update_project(self.project)
        elif index == 2 and hasattr(self, "sub33_view"):
            self.sub33_view.update_project(self.project)

    def update_project(self, project: Project):
        """Propaga la actualización del proyecto a todas las sub-vistas."""
        self.project = project
        if hasattr(self, "sub31_view"):
            self.sub31_view.update_project(project)
        if hasattr(self, "sub32_view"):
            self.sub32_view.update_project(project)
        if hasattr(self, "sub33_view"):
            self.sub33_view.update_project(project)

    def teardown(self):
        """Detiene de forma limpia trabajadores en segundo plano de todos los sub-sectores."""
        if hasattr(self, "sub32_view") and hasattr(self.sub32_view, "teardown"):
            self.sub32_view.teardown()
        if hasattr(self, "sub33_view") and hasattr(self.sub33_view, "teardown"):
            self.sub33_view.teardown()
