#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS | NEOS - PROYECTOS VIEW (LISTA UNIFICADA & ÁRBOL)
# =====================================================================

import os
import subprocess
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QLineEdit, QFrame, QScrollArea,
    QTreeView, QHeaderView, QSplitter, QFileSystemModel
)
from PySide6.QtCore import Qt, QDir

from core.projects import list_project_folders, get_projects_dir

class ProjectRowWidget(QFrame):
    """Fila interactiva dentro del recuadro unificado de proyectos."""
    
    def __init__(self, folder_data, on_select_cb, parent=None):
        super().__init__(parent)
        self.folder_data = folder_data
        self.on_select_cb = on_select_cb
        self.is_selected = False

        self.setProperty("class", "project_row")
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(3)

        # Fila superior: Icono + Nombre + Badge
        r_top = QHBoxLayout()
        r_top.setSpacing(8)
        
        self.lbl_name = QLabel(f"📁  {folder_data['name']}")
        self.lbl_name.setProperty("class", "project_name")

        # Detectar si contiene .git para badge especializado
        git_path = os.path.join(folder_data["path"], ".git")
        tag_text = "Git Repo" if os.path.exists(git_path) else "Carpeta"
        self.lbl_tag = QLabel(tag_text)
        self.lbl_tag.setProperty("class", "badge_dir")

        r_top.addWidget(self.lbl_name, 1)
        r_top.addWidget(self.lbl_tag)
        layout.addLayout(r_top)

        # Fila inferior: Ruta completa
        self.lbl_path = QLabel(folder_data["path"])
        self.lbl_path.setProperty("class", "project_path")
        layout.addWidget(self.lbl_path)

    def set_active(self, active: bool):
        self.is_selected = active
        self.setProperty("selected", "true" if active else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.on_select_cb(self.folder_data, self)
        super().mousePressEvent(event)


class ProjectsView(QWidget):
    """Vista de proyectos con lista contenida en un único recuadro y árbol interactivo inferior."""
    
    def __init__(self, config_target, parent=None):
        super().__init__(parent)
        self.config_target = config_target
        self.row_widgets = []
        self.selected_path = ""

        self.init_ui()
        self.load_projects()

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(12)

        # -------------------------------------------------------------
        # 1. ENCABEZADO
        # -------------------------------------------------------------
        lbl_t = QLabel("📁 PROYECTOS")
        lbl_t.setProperty("class", "page_title")
        
        lbl_sub = QLabel("Explorador de Repositorios & Árbol de Contenido")
        lbl_sub.setProperty("class", "page_subtitle")
        
        root_layout.addWidget(lbl_t)
        root_layout.addWidget(lbl_sub)

        # -------------------------------------------------------------
        # 2. BARRA DE CONTROL (RUTA ACTIVA, BUSCADOR, RECARGA)
        # -------------------------------------------------------------
        top_card = QFrame()
        top_card.setProperty("class", "surface")
        top_layout = QVBoxLayout(top_card)
        top_layout.setSpacing(10)

        # Fila de Ruta y Contador
        row_path = QHBoxLayout()
        self.lbl_projects_path = QLabel("📁 Ruta: ")
        self.lbl_projects_path.setStyleSheet("font-family: monospace; font-size: 12px; font-weight: 500;")
        
        self.lbl_projects_count = QLabel("0 carpetas")
        self.lbl_projects_count.setProperty("class", "count_badge")

        row_path.addWidget(self.lbl_projects_path, 1)
        row_path.addWidget(self.lbl_projects_count)
        top_layout.addLayout(row_path)

        # Fila de Filtro y Botón
        row_actions = QHBoxLayout()
        self.txt_filter = QLineEdit()
        self.txt_filter.setPlaceholderText("🔍 Filtrar proyectos por nombre...")
        self.txt_filter.textChanged.connect(self.filter_projects)
        
        btn_refresh = QPushButton("🔄 Recargar")
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.clicked.connect(self.load_projects)

        row_actions.addWidget(self.txt_filter, 1)
        row_actions.addWidget(btn_refresh)
        top_layout.addLayout(row_actions)

        root_layout.addWidget(top_card)

        # -------------------------------------------------------------
        # 3. SPLITTER VERTICAL (LISTA UNIFICADA ARRIBA + ÁRBOL ABAJO)
        # -------------------------------------------------------------
        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.setChildrenCollapsible(False)

        # --- SECCIÓN SUPERIOR: CONTENEDOR ÚNICO DE CARPETAS ---
        top_container = QWidget()
        top_c_layout = QVBoxLayout(top_container)
        top_c_layout.setContentsMargins(0, 0, 0, 0)
        top_c_layout.setSpacing(6)

        lbl_list_header = QLabel("📦 Carpetas de Proyectos:")
        lbl_list_header.setStyleSheet("font-weight: 700; font-size: 12px; color: #9ca3af;")
        top_c_layout.addWidget(lbl_list_header)

        # Scroll Area que aloja el único recuadro contenedor
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        self.list_container_widget = QWidget()
        self.list_container_layout = QVBoxLayout(self.list_container_widget)
        self.list_container_layout.setContentsMargins(0, 0, 8, 0)
        self.list_container_layout.setSpacing(0)

        # Recuadro unificado (Single Surface Card) para todas las filas
        self.unified_box = QFrame()
        self.unified_box.setProperty("class", "project_list_card")
        self.unified_box_layout = QVBoxLayout(self.unified_box)
        self.unified_box_layout.setContentsMargins(0, 0, 0, 0)
        self.unified_box_layout.setSpacing(0)

        self.list_container_layout.addWidget(self.unified_box)
        self.list_container_layout.addStretch()

        self.scroll_area.setWidget(self.list_container_widget)
        top_c_layout.addWidget(self.scroll_area)
        self.splitter.addWidget(top_container)

        # --- SECCIÓN INFERIOR: ÁRBOL DE CONTENIDO (ESTRUCTURA) ---
        bottom_container = QFrame()
        bottom_container.setProperty("class", "surface")
        bottom_layout = QVBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(14, 12, 14, 12)
        bottom_layout.setSpacing(10)

        # Barra de título del árbol y controles de expansión
        tree_header_row = QHBoxLayout()
        self.lbl_tree_title = QLabel("🌳 Árbol de Contenido (Selecciona un proyecto)")
        self.lbl_tree_title.setProperty("class", "section_title")
        tree_header_row.addWidget(self.lbl_tree_title, 1)

        btn_expand = QPushButton("➕ Desplegar")
        btn_expand.setProperty("class", "browse")
        btn_expand.setCursor(Qt.PointingHandCursor)
        btn_expand.setToolTip("Desplegar todas las carpetas del árbol")
        btn_expand.clicked.connect(self.expand_all_tree)

        btn_collapse = QPushButton("➖ Colapsar")
        btn_collapse.setProperty("class", "browse")
        btn_collapse.setCursor(Qt.PointingHandCursor)
        btn_collapse.setToolTip("Colapsar todas las carpetas del árbol")
        btn_collapse.clicked.connect(self.collapse_all_tree)

        btn_open = QPushButton("📂 Abrir en Carpeta")
        btn_open.setProperty("class", "browse")
        btn_open.setCursor(Qt.PointingHandCursor)
        btn_open.setToolTip("Abrir carpeta en el explorador de archivos del sistema")
        btn_open.clicked.connect(self.open_in_file_manager)

        tree_header_row.addWidget(btn_expand)
        tree_header_row.addWidget(btn_collapse)
        tree_header_row.addWidget(btn_open)
        bottom_layout.addLayout(tree_header_row)

        # Modelo y Vista del Árbol de Archivos
        self.file_model = QFileSystemModel()
        self.file_model.setFilter(QDir.AllDirs | QDir.Files | QDir.NoDotAndDotDot)
        
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.file_model)
        self.tree_view.setAnimated(True)
        self.tree_view.setIndentation(20)
        self.tree_view.setSortingEnabled(True)
        self.tree_view.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tree_view.header().setStretchLastSection(True)

        bottom_layout.addWidget(self.tree_view)
        self.splitter.addWidget(bottom_container)

        # Proporción inicial del splitter (40% lista arriba, 60% árbol abajo)
        self.splitter.setSizes([200, 300])

        root_layout.addWidget(self.splitter)

    def load_projects(self):
        base_dir, folders = list_project_folders(self.config_target)
        self.lbl_projects_path.setText(f"📁 Ruta: {base_dir if base_dir else 'No configurada en config.toml'}")
        self.lbl_projects_count.setText(f"{len(folders)} {'carpeta' if len(folders) == 1 else 'carpetas'}")

        # Limpiar filas existentes dentro del recuadro unificado
        while self.unified_box_layout.count():
            item = self.unified_box_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self.row_widgets = []

        if not base_dir or not os.path.exists(base_dir):
            lbl_empty = QLabel(f"⚠️ El directorio establecido en config.toml no existe en el sistema:\n{base_dir}")
            lbl_empty.setProperty("class", "card_desc")
            lbl_empty.setWordWrap(True)
            lbl_empty.setContentsMargins(16, 16, 16, 16)
            self.unified_box_layout.addWidget(lbl_empty)
            self.set_tree_root("")
            return

        if not folders:
            lbl_empty = QLabel("ℹ No se encontraron carpetas dentro del directorio de proyectos.")
            lbl_empty.setProperty("class", "card_desc")
            lbl_empty.setContentsMargins(16, 16, 16, 16)
            self.unified_box_layout.addWidget(lbl_empty)
            self.set_tree_root("")
            return

        first_row = None
        for idx, folder in enumerate(folders):
            row = ProjectRowWidget(folder, self.on_row_clicked)
            if idx == len(folders) - 1:
                row.setProperty("class", "project_row project_row_last")
            
            self.unified_box_layout.addWidget(row)
            self.row_widgets.append((folder["name"].lower(), row, folder))
            if idx == 0:
                first_row = (folder, row)

        # Seleccionar automáticamente el primer proyecto o mantener el activo
        target_folder = None
        target_row = None
        if self.selected_path:
            for name, row, folder in self.row_widgets:
                if folder["path"] == self.selected_path:
                    target_folder = folder
                    target_row = row
                    break

        if not target_folder and first_row:
            target_folder, target_row = first_row

        if target_folder and target_row:
            self.on_row_clicked(target_folder, target_row)

        # Aplicar filtro activo si existe
        if hasattr(self, "txt_filter") and self.txt_filter.text().strip():
            self.filter_projects(self.txt_filter.text().strip())

    def on_row_clicked(self, folder_data, clicked_row):
        # Desmarcar todas las filas y marcar la seleccionada
        for _, row, _ in self.row_widgets:
            row.set_active(row == clicked_row)

        self.selected_path = folder_data["path"]
        self.set_tree_root(self.selected_path, folder_data["name"])

    def set_tree_root(self, path, name=""):
        if not path or not os.path.exists(path):
            self.lbl_tree_title.setText("🌳 Árbol de Contenido (Ningún proyecto seleccionado)")
            self.file_model.setRootPath("")
            self.tree_view.setRootIndex(self.file_model.index(""))
            return

        display_name = name or os.path.basename(path)
        self.lbl_tree_title.setText(f"🌳 Estructura de Contenido: {display_name}")
        self.file_model.setRootPath(path)
        root_index = self.file_model.index(path)
        self.tree_view.setRootIndex(root_index)

    def expand_all_tree(self):
        self.tree_view.expandAll()

    def collapse_all_tree(self):
        self.tree_view.collapseAll()

    def open_in_file_manager(self):
        if self.selected_path and os.path.exists(self.selected_path):
            try:
                subprocess.Popen(["xdg-open", self.selected_path])
            except Exception as e:
                print(f"Error al abrir carpeta: {e}")

    def filter_projects(self, query):
        q = query.strip().lower()
        for name, row, folder in self.row_widgets:
            row.setVisible(q in name if q else True)
