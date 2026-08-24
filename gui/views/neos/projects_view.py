#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS | NEOS - PROYECTOS VIEW CON MODOS DE ACCIÓN & GRAFO
# =====================================================================

import os
import subprocess
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QLineEdit, QFrame, QScrollArea,
    QTreeView, QHeaderView, QSplitter, QFileSystemModel,
    QStackedWidget
)
from PySide6.QtCore import Qt, QDir

from core.projects import list_project_folders, get_projects_dir
from gui.views.neos.graph_canvas import ProjectGraphCanvas

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
    """Vista de proyectos con alternancia de modos (Buscar, Crear, Sincronizar, Purgar) y vista de Grafo/Árbol."""
    
    def __init__(self, config_target, parent=None):
        super().__init__(parent)
        self.config_target = config_target
        self.row_widgets = []
        self.selected_path = ""
        self.current_mode = "graph"
        self.action_mode = "search"

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
        
        lbl_sub = QLabel("Explorador de Repositorios & Grafo de Estructura")
        lbl_sub.setProperty("class", "page_subtitle")
        
        root_layout.addWidget(lbl_t)
        root_layout.addWidget(lbl_sub)

        # -------------------------------------------------------------
        # 2. BARRA DE CONTROL & MODOS DE ACCIÓN (BUSCAR, CREAR, SYNC, PURGAR)
        # -------------------------------------------------------------
        top_card = QFrame()
        top_card.setProperty("class", "surface")
        top_layout = QVBoxLayout(top_card)
        top_layout.setSpacing(10)

        # Fila 1: Ruta y Contador
        row_path = QHBoxLayout()
        self.lbl_projects_path = QLabel("📁 Ruta: ")
        self.lbl_projects_path.setStyleSheet("font-family: monospace; font-size: 12px; font-weight: 500;")
        
        self.lbl_projects_count = QLabel("0 carpetas")
        self.lbl_projects_count.setProperty("class", "count_badge")

        row_path.addWidget(self.lbl_projects_path, 1)
        row_path.addWidget(self.lbl_projects_count)
        top_layout.addLayout(row_path)

        # Fila 2: Botones de Alternancia de Modos (Verde, Amarillo, Morado, Rojo)
        row_modes = QHBoxLayout()
        row_modes.setSpacing(8)

        lbl_mode_tag = QLabel("Modo:")
        lbl_mode_tag.setStyleSheet("font-size: 11px; color: #9ca3af; font-weight: 700;")
        row_modes.addWidget(lbl_mode_tag)

        # 1. Buscar (Verde)
        self.btn_mode_search = QPushButton("🔍 Buscar")
        self.btn_mode_search.setProperty("class", "btn_mode_green")
        self.btn_mode_search.setCheckable(True)
        self.btn_mode_search.setChecked(True)
        self.btn_mode_search.setCursor(Qt.PointingHandCursor)
        self.btn_mode_search.clicked.connect(lambda: self.set_action_mode("search"))
        row_modes.addWidget(self.btn_mode_search)

        # 2. Crear Proyecto (Amarillo)
        self.btn_mode_create = QPushButton("✨ Crear")
        self.btn_mode_create.setProperty("class", "btn_mode_yellow")
        self.btn_mode_create.setCheckable(True)
        self.btn_mode_create.setCursor(Qt.PointingHandCursor)
        self.btn_mode_create.clicked.connect(lambda: self.set_action_mode("create"))
        row_modes.addWidget(self.btn_mode_create)

        # 3. Sincronizar Proyecto (Morado)
        self.btn_mode_sync = QPushButton("🔄 Sincronizar")
        self.btn_mode_sync.setProperty("class", "btn_mode_purple")
        self.btn_mode_sync.setCheckable(True)
        self.btn_mode_sync.setCursor(Qt.PointingHandCursor)
        self.btn_mode_sync.clicked.connect(lambda: self.set_action_mode("sync"))
        row_modes.addWidget(self.btn_mode_sync)

        # 4. Purgar / Eliminar Proyecto (Rojo)
        self.btn_mode_purge = QPushButton("🗑️ Purgar")
        self.btn_mode_purge.setProperty("class", "btn_mode_red")
        self.btn_mode_purge.setCheckable(True)
        self.btn_mode_purge.setCursor(Qt.PointingHandCursor)
        self.btn_mode_purge.clicked.connect(lambda: self.set_action_mode("purge"))
        row_modes.addWidget(self.btn_mode_purge)

        row_modes.addStretch()
        top_layout.addLayout(row_modes)

        # Fila 3: Campo de Entrada Dinámico y Botón de Ejecución
        row_actions = QHBoxLayout()
        self.txt_action_input = QLineEdit()
        self.txt_action_input.setPlaceholderText("🔍 Filtrar proyectos por nombre...")
        self.txt_action_input.textChanged.connect(self.on_input_text_changed)
        
        self.btn_action_exec = QPushButton("🔄 Recargar")
        self.btn_action_exec.setProperty("class", "browse")
        self.btn_action_exec.setCursor(Qt.PointingHandCursor)
        self.btn_action_exec.clicked.connect(self.on_action_execute)

        row_actions.addWidget(self.txt_action_input, 1)
        row_actions.addWidget(self.btn_action_exec)
        top_layout.addLayout(row_actions)

        root_layout.addWidget(top_card)

        # -------------------------------------------------------------
        # 3. SPLITTER VERTICAL (LISTA UNIFICADA ARRIBA + GRAFO/ÁRBOL ABAJO)
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

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        self.list_container_widget = QWidget()
        self.list_container_layout = QVBoxLayout(self.list_container_widget)
        self.list_container_layout.setContentsMargins(0, 0, 8, 0)
        self.list_container_layout.setSpacing(0)

        # Recuadro unificado para todas las filas
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

        # --- SECCIÓN INFERIOR: VISTA DE GRAFO & ÁRBOL DE CONTENIDO ---
        bottom_container = QFrame()
        bottom_container.setProperty("class", "surface")
        bottom_layout = QVBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(14, 12, 14, 12)
        bottom_layout.setSpacing(10)

        # Barra superior de controles del grafo/árbol
        tree_header_row = QHBoxLayout()
        self.lbl_tree_title = QLabel("🕸️ Grafo de Estructura (Selecciona un proyecto)")
        self.lbl_tree_title.setProperty("class", "section_title")
        tree_header_row.addWidget(self.lbl_tree_title, 1)

        # Selector de Vista: [🕸️ Grafo] / [📁 Árbol]
        self.btn_view_graph = QPushButton("🕸️ Grafo")
        self.btn_view_graph.setProperty("class", "primary")
        self.btn_view_graph.setCursor(Qt.PointingHandCursor)
        self.btn_view_graph.clicked.connect(lambda: self.switch_view_mode("graph"))

        self.btn_view_tree = QPushButton("📁 Árbol")
        self.btn_view_tree.setProperty("class", "browse")
        self.btn_view_tree.setCursor(Qt.PointingHandCursor)
        self.btn_view_tree.clicked.connect(lambda: self.switch_view_mode("tree"))

        # Controles de Profundidad (+1 / -1) para el Grafo
        self.lbl_depth_title = QLabel("Profundidad:")
        self.lbl_depth_title.setStyleSheet("font-size: 11px; color: #9ca3af; font-weight: 600;")
        
        self.lbl_depth_val = QLabel("Nivel 2")
        self.lbl_depth_val.setProperty("class", "count_badge")

        self.btn_depth_minus = QPushButton("−1")
        self.btn_depth_minus.setProperty("class", "browse")
        self.btn_depth_minus.setCursor(Qt.PointingHandCursor)
        self.btn_depth_minus.setToolTip("Reducir profundidad de carpetas (-1)")
        self.btn_depth_minus.clicked.connect(lambda: self.adjust_depth(-1))

        self.btn_depth_plus = QPushButton("+1")
        self.btn_depth_plus.setProperty("class", "browse")
        self.btn_depth_plus.setCursor(Qt.PointingHandCursor)
        self.btn_depth_plus.setToolTip("Aumentar profundidad de carpetas (+1)")
        self.btn_depth_plus.clicked.connect(lambda: self.adjust_depth(1))

        self.btn_center_graph = QPushButton("🎯 Centrar")
        self.btn_center_graph.setProperty("class", "browse")
        self.btn_center_graph.setCursor(Qt.PointingHandCursor)
        self.btn_center_graph.setToolTip("Centrar vista del grafo")
        self.btn_center_graph.clicked.connect(self.center_graph_view)

        # Controles para la vista de Árbol clásico
        self.btn_expand = QPushButton("➕ Desplegar")
        self.btn_expand.setProperty("class", "browse")
        self.btn_expand.setCursor(Qt.PointingHandCursor)
        self.btn_expand.setVisible(False)
        self.btn_expand.clicked.connect(self.expand_all_tree)

        self.btn_collapse = QPushButton("➖ Colapsar")
        self.btn_collapse.setProperty("class", "browse")
        self.btn_collapse.setCursor(Qt.PointingHandCursor)
        self.btn_collapse.setVisible(False)
        self.btn_collapse.clicked.connect(self.collapse_all_tree)

        btn_open = QPushButton("📂 Abrir")
        btn_open.setProperty("class", "browse")
        btn_open.setCursor(Qt.PointingHandCursor)
        btn_open.setToolTip("Abrir en el gestor de archivos de Linux")
        btn_open.clicked.connect(self.open_in_file_manager)

        # Añadir widgets al encabezado
        tree_header_row.addWidget(self.btn_view_graph)
        tree_header_row.addWidget(self.btn_view_tree)
        tree_header_row.addSpacing(6)
        tree_header_row.addWidget(self.lbl_depth_title)
        tree_header_row.addWidget(self.btn_depth_minus)
        tree_header_row.addWidget(self.lbl_depth_val)
        tree_header_row.addWidget(self.btn_depth_plus)
        tree_header_row.addSpacing(6)
        tree_header_row.addWidget(self.btn_center_graph)
        tree_header_row.addWidget(self.btn_expand)
        tree_header_row.addWidget(self.btn_collapse)
        tree_header_row.addWidget(btn_open)
        bottom_layout.addLayout(tree_header_row)

        # Stack con [0: Grafo Interactivo Canvas, 1: Árbol QTreeView]
        self.bottom_stack = QStackedWidget()

        # 1. Canvas del Grafo
        self.graph_canvas = ProjectGraphCanvas()
        self.bottom_stack.addWidget(self.graph_canvas)

        # 2. Árbol de Carpetas
        self.tree_widget_container = QWidget()
        tree_lay = QVBoxLayout(self.tree_widget_container)
        tree_lay.setContentsMargins(0, 0, 0, 0)

        self.file_model = QFileSystemModel()
        self.file_model.setFilter(QDir.AllDirs | QDir.Files | QDir.NoDotAndDotDot)
        
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.file_model)
        self.tree_view.setAnimated(True)
        self.tree_view.setIndentation(20)
        self.tree_view.setSortingEnabled(True)
        self.tree_view.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tree_view.header().setStretchLastSection(True)

        tree_lay.addWidget(self.tree_view)
        self.bottom_stack.addWidget(self.tree_widget_container)

        bottom_layout.addWidget(self.bottom_stack)
        self.splitter.addWidget(bottom_container)

        # Proporción inicial del splitter (35% lista arriba, 65% grafo/árbol abajo)
        self.splitter.setSizes([180, 360])

        root_layout.addWidget(self.splitter)

    def set_action_mode(self, mode: str):
        """Alterna entre los 4 modos de acción: Buscar (Verde), Crear (Amarillo), Sincronizar (Morado), Purgar (Rojo)."""
        self.action_mode = mode

        self.btn_mode_search.setChecked(mode == "search")
        self.btn_mode_create.setChecked(mode == "create")
        self.btn_mode_sync.setChecked(mode == "sync")
        self.btn_mode_purge.setChecked(mode == "purge")

        if mode == "search":
            self.txt_action_input.setPlaceholderText("🔍 Filtrar proyectos por nombre...")
            self.btn_action_exec.setText("🔄 Recargar")
            self.btn_action_exec.setProperty("class", "browse")
            self.filter_projects(self.txt_action_input.text().strip())
        elif mode == "create":
            self.txt_action_input.setPlaceholderText("✨ Nombre del nuevo proyecto a crear en la ruta...")
            self.btn_action_exec.setText("➕ Crear")
            self.btn_action_exec.setProperty("class", "btn_mode_yellow")
        elif mode == "sync":
            self.txt_action_input.setPlaceholderText("🔄 Repositorio Git remoto o rama a sincronizar...")
            self.btn_action_exec.setText("⚡ Sincronizar")
            self.btn_action_exec.setProperty("class", "btn_mode_purple")
        elif mode == "purge":
            self.txt_action_input.setPlaceholderText("🗑️ Nombre de la carpeta a purgar / eliminar...")
            self.btn_action_exec.setText("⚠️ Purgar")
            self.btn_action_exec.setProperty("class", "btn_mode_red")

        self.btn_action_exec.style().unpolish(self.btn_action_exec)
        self.btn_action_exec.style().polish(self.btn_action_exec)

    def on_input_text_changed(self, text):
        if self.action_mode == "search":
            self.filter_projects(text)

    def on_action_execute(self):
        if self.action_mode == "search":
            self.load_projects()
        elif self.action_mode == "create":
            # Espacio listo para la creación de proyectos
            self.load_projects()
        elif self.action_mode == "sync":
            # Espacio listo para la sincronización Git
            pass
        elif self.action_mode == "purge":
            # Espacio listo para la purga de carpetas
            pass

    def adjust_depth(self, delta):
        new_depth = self.graph_canvas.change_depth(delta)
        self.lbl_depth_val.setText(f"Nivel {new_depth}")

    def switch_view_mode(self, mode: str):
        self.current_mode = mode
        if mode == "graph":
            self.bottom_stack.setCurrentIndex(0)
            self.btn_view_graph.setProperty("class", "primary")
            self.btn_view_tree.setProperty("class", "browse")
            self.btn_center_graph.setVisible(True)
            self.lbl_depth_title.setVisible(True)
            self.lbl_depth_val.setVisible(True)
            self.btn_depth_minus.setVisible(True)
            self.btn_depth_plus.setVisible(True)
            self.btn_expand.setVisible(False)
            self.btn_collapse.setVisible(False)
            display_name = os.path.basename(self.selected_path) if self.selected_path else "Ninguno"
            self.lbl_tree_title.setText(f"🕸️ Grafo de Estructura: {display_name}")
        else:
            self.bottom_stack.setCurrentIndex(1)
            self.btn_view_graph.setProperty("class", "browse")
            self.btn_view_tree.setProperty("class", "primary")
            self.btn_center_graph.setVisible(False)
            self.lbl_depth_title.setVisible(False)
            self.lbl_depth_val.setVisible(False)
            self.btn_depth_minus.setVisible(False)
            self.btn_depth_plus.setVisible(False)
            self.btn_expand.setVisible(True)
            self.btn_collapse.setVisible(True)
            display_name = os.path.basename(self.selected_path) if self.selected_path else "Ninguno"
            self.lbl_tree_title.setText(f"🌳 Árbol de Carpetas: {display_name}")

        self.btn_view_graph.style().unpolish(self.btn_view_graph)
        self.btn_view_graph.style().polish(self.btn_view_graph)
        self.btn_view_tree.style().unpolish(self.btn_view_tree)
        self.btn_view_tree.style().polish(self.btn_view_tree)

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
            self.set_active_project("")
            return

        if not folders:
            lbl_empty = QLabel("ℹ No se encontraron carpetas dentro del directorio de proyectos.")
            lbl_empty.setProperty("class", "card_desc")
            lbl_empty.setContentsMargins(16, 16, 16, 16)
            self.unified_box_layout.addWidget(lbl_empty)
            self.set_active_project("")
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

        if hasattr(self, "txt_action_input") and self.txt_action_input.text().strip() and self.action_mode == "search":
            self.filter_projects(self.txt_action_input.text().strip())

    def on_row_clicked(self, folder_data, clicked_row):
        for _, row, _ in self.row_widgets:
            row.set_active(row == clicked_row)

        self.selected_path = folder_data["path"]
        self.set_active_project(self.selected_path, folder_data["name"])

    def set_active_project(self, path, name=""):
        if not path or not os.path.exists(path):
            self.lbl_tree_title.setText("🕸️ Grafo de Estructura (Ningún proyecto seleccionado)")
            self.file_model.setRootPath("")
            self.tree_view.setRootIndex(self.file_model.index(""))
            self.graph_canvas.build_graph_from_directory("")
            return

        display_name = name or os.path.basename(path)
        if self.current_mode == "graph":
            self.lbl_tree_title.setText(f"🕸️ Grafo de Estructura: {display_name}")
        else:
            self.lbl_tree_title.setText(f"🌳 Árbol de Carpetas: {display_name}")

        # 1. Actualizar Grafo en cuadrícula fija
        self.graph_canvas.build_graph_from_directory(path)

        # 2. Actualizar Árbol QTreeView
        self.file_model.setRootPath(path)
        root_index = self.file_model.index(path)
        self.tree_view.setRootIndex(root_index)

    def center_graph_view(self):
        self.graph_canvas.center_graph()

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
