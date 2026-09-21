#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS | LUMEN - MAIN VIEW (SELECTOR DE PROYECTOS & MOTOR DEV)
# =====================================================================

import os
import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QLineEdit, QFrame, QScrollArea,
    QStackedWidget
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QPoint, QEasingCurve, QSize

from core.projects import list_project_folders, get_projects_dir
from core.setup import get_target_config_path
from gui.views.lumen.workspace_view import LumenProjectWorkspaceView


def get_lumen_order_file():
    """Obtiene la ruta del archivo de configuración para el orden personalizado de proyectos."""
    cfg_dir = os.path.expanduser("~/.config/abraxas")
    os.makedirs(cfg_dir, exist_ok=True)
    return os.path.join(cfg_dir, "lumen_project_order.json")


def load_lumen_order():
    """Carga el orden guardado de proyectos."""
    fpath = get_lumen_order_file()
    if os.path.exists(fpath):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_lumen_order(order_list):
    """Guarda el orden personalizado de proyectos."""
    fpath = get_lumen_order_file()
    try:
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(order_list, f, indent=2)
    except Exception as e:
        print(f"Error al guardar orden de proyectos en Lumen: {e}")


class LumenDragHandle(QLabel):
    """Manejador de 3 líneas horizontales (☰) ubicado a la extrema izquierda para reordenar verticalmente."""
    
    def __init__(self, parent_row, parent=None):
        super().__init__("☰", parent)
        self.parent_row = parent_row
        self.drag_active = False
        self.setFixedWidth(30)
        self.setAlignment(Qt.AlignCenter)
        self.setCursor(Qt.SizeVerCursor)
        self.setToolTip("Arrastra verticalmente para mover la posición de este proyecto")
        self.setStyleSheet("""
            QLabel {
                color: #6b7280;
                font-size: 18px;
                font-weight: 900;
                padding: 4px 2px;
                border-radius: 5px;
                background-color: rgba(255, 255, 255, 0.02);
            }
            QLabel:hover {
                color: #818cf8;
                background-color: rgba(99, 102, 241, 0.18);
            }
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_active = True
            global_y = event.globalPosition().toPoint().y()
            self.parent_row.container.begin_drag(self.parent_row, global_y)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.drag_active:
            global_y = event.globalPosition().toPoint().y()
            self.parent_row.container.update_drag(self.parent_row, global_y)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.drag_active and event.button() == Qt.LeftButton:
            self.drag_active = False
            self.parent_row.container.end_drag(self.parent_row)
            event.accept()
        else:
            super().mouseReleaseEvent(event)


class LumenProjectRowWidget(QFrame):
    """Fila interactiva para seleccionar y reordenar un proyecto dentro de Lumen."""
    
    def __init__(self, folder_data, rank, container, on_select_cb, on_double_click_cb, parent=None):
        super().__init__(parent or container)
        self.folder_data = folder_data
        self.rank = rank
        self.container = container
        self.on_select_cb = on_select_cb
        self.on_double_click_cb = on_double_click_cb
        self.is_selected = False
        self.is_dragging = False

        self.setProperty("class", "project_row")
        self.setCursor(Qt.PointingHandCursor)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(14, 8, 16, 8)
        main_layout.setSpacing(12)

        # 1. Manilla de 3 líneas horizontales a la IZQUIERDA DEL TODO
        self.drag_handle = LumenDragHandle(self)
        main_layout.addWidget(self.drag_handle)

        # 2. Contenedor de Información del Proyecto
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(4)

        # Fila superior: Badge de Rango + Icono + Nombre + Badges de Git / Tamaño
        r_top = QHBoxLayout()
        r_top.setSpacing(10)
        r_top.setAlignment(Qt.AlignVCenter)

        self.lbl_rank = QLabel()
        self.lbl_rank.setAlignment(Qt.AlignCenter)

        self.lbl_name = QLabel(f"💻  {folder_data['name']}")
        
        git_path = os.path.join(folder_data["path"], ".git")
        tag_text = "Git Repo" if os.path.exists(git_path) else "Carpeta"
        self.lbl_tag = QLabel(tag_text)
        self.lbl_tag.setAlignment(Qt.AlignCenter)
        self.lbl_tag.setStyleSheet("""
            QLabel {
                background-color: rgba(99, 102, 241, 0.14);
                color: #c7d2fe;
                border: 1px solid rgba(99, 102, 241, 0.35);
                border-radius: 5px;
                padding: 0px 10px;
                min-height: 24px;
                max-height: 24px;
                font-size: 12px;
                font-weight: 600;
            }
        """)

        size_str = folder_data.get("size_str", "")
        self.lbl_size = QLabel(size_str)
        self.lbl_size.setAlignment(Qt.AlignCenter)
        self.lbl_size.setStyleSheet("""
            QLabel {
                background-color: rgba(6, 182, 212, 0.10);
                color: #38bdf8;
                border: 1px solid rgba(6, 182, 212, 0.30);
                border-radius: 5px;
                padding: 0px 10px;
                min-height: 24px;
                max-height: 24px;
                font-size: 12px;
                font-weight: 600;
            }
        """)

        r_top.addWidget(self.lbl_rank)
        r_top.addWidget(self.lbl_name, 1)
        if size_str:
            r_top.addWidget(self.lbl_size)
        r_top.addWidget(self.lbl_tag)
        info_layout.addLayout(r_top)

        # Fila inferior: Ruta completa
        self.lbl_path = QLabel(folder_data["path"])
        self.lbl_path.setStyleSheet("font-family: monospace; font-size: 12px; color: #9ca3af;")
        info_layout.addWidget(self.lbl_path)

        main_layout.addLayout(info_layout, 1)

        # Aplicar colores vibrantes según el Rango inicial
        self.apply_rank_styling()

    def set_rank(self, new_rank: int):
        """Actualiza el rango del proyecto y sus colores correspondientes."""
        self.rank = new_rank
        self.apply_rank_styling()

    def apply_rank_styling(self):
        """Aplica estilos vibrantes para los 3 primeros proyectos y blanco para el resto."""
        if self.rank == 1:
            # 1er Lugar: Oro / Ámbar Vibrante (El más importante)
            self.lbl_rank.setText("👑 #1 TOP")
            self.lbl_rank.setStyleSheet(
                "QLabel {"
                "  background-color: rgba(245, 158, 11, 0.20); "
                "  color: #fbbf24; "
                "  border: 1px solid rgba(245, 158, 11, 0.6); "
                "  border-radius: 6px; "
                "  padding: 0px 9px; "
                "  min-height: 24px; "
                "  max-height: 24px; "
                "  font-weight: 900; "
                "  font-size: 12px;"
                "}"
            )
            self.lbl_name.setStyleSheet("color: #fbbf24; font-size: 15px; font-weight: 800;")
            border_css = "border-left: 5px solid #f59e0b; border: 1px solid rgba(245, 158, 11, 0.25);"
            bg_css = "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(245, 158, 11, 0.12), stop:1 rgba(245, 158, 11, 0.02));"
        elif self.rank == 2:
            # 2do Lugar: Cian Eléctrico Vibrante
            self.lbl_rank.setText("⚡ #2")
            self.lbl_rank.setStyleSheet(
                "QLabel {"
                "  background-color: rgba(56, 189, 248, 0.20); "
                "  color: #38bdf8; "
                "  border: 1px solid rgba(56, 189, 248, 0.6); "
                "  border-radius: 6px; "
                "  padding: 0px 9px; "
                "  min-height: 24px; "
                "  max-height: 24px; "
                "  font-weight: 900; "
                "  font-size: 12px;"
                "}"
            )
            self.lbl_name.setStyleSheet("color: #38bdf8; font-size: 15px; font-weight: 800;")
            border_css = "border-left: 5px solid #0ea5e9; border: 1px solid rgba(14, 165, 233, 0.25);"
            bg_css = "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(14, 165, 233, 0.12), stop:1 rgba(14, 165, 233, 0.02));"
        elif self.rank == 3:
            # 3er Lugar: Violeta / Púrpura Neón
            self.lbl_rank.setText("🔮 #3")
            self.lbl_rank.setStyleSheet(
                "QLabel {"
                "  background-color: rgba(192, 132, 252, 0.20); "
                "  color: #c084fc; "
                "  border: 1px solid rgba(192, 132, 252, 0.6); "
                "  border-radius: 6px; "
                "  padding: 0px 9px; "
                "  min-height: 24px; "
                "  max-height: 24px; "
                "  font-weight: 900; "
                "  font-size: 12px;"
                "}"
            )
            self.lbl_name.setStyleSheet("color: #c084fc; font-size: 15px; font-weight: 800;")
            border_css = "border-left: 5px solid #a855f7; border: 1px solid rgba(168, 85, 247, 0.25);"
            bg_css = "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(168, 85, 247, 0.12), stop:1 rgba(168, 85, 247, 0.02));"
        else:
            # Resto de proyectos: Color blanco estándar
            self.lbl_rank.setText(f"📄 #{self.rank}")
            self.lbl_rank.setStyleSheet(
                "QLabel {"
                "  background-color: rgba(255, 255, 255, 0.05); "
                "  color: #9ca3af; "
                "  border: 1px solid rgba(255, 255, 255, 0.15); "
                "  border-radius: 6px; "
                "  padding: 0px 9px; "
                "  min-height: 24px; "
                "  max-height: 24px; "
                "  font-weight: 700; "
                "  font-size: 12px;"
                "}"
            )
            self.lbl_name.setStyleSheet("color: #ffffff; font-size: 14.5px; font-weight: 600;")
            border_css = "border-left: 5px solid rgba(255, 255, 255, 0.15); border: 1px solid rgba(255, 255, 255, 0.06);"
            bg_css = "background-color: rgba(255, 255, 255, 0.02);"

        if self.is_dragging:
            self.setStyleSheet(
                "QFrame.project_row { "
                "  border: 1px solid #818cf8; "
                "  border-left: 6px solid #6366f1; "
                "  background-color: rgba(99, 102, 241, 0.32); "
                "  border-radius: 10px; "
                "}"
            )
        elif self.is_selected:
            self.setStyleSheet(
                f"QFrame.project_row {{ "
                f"  {border_css} "
                f"  background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(99, 102, 241, 0.25), stop:1 rgba(99, 102, 241, 0.06)); "
                f"  border-radius: 10px; "
                f"}}"
            )
        else:
            self.setStyleSheet(
                f"QFrame.project_row {{ "
                f"  {border_css} "
                f"  {bg_css} "
                f"  border-radius: 10px; "
                f"}}"
            )

    def set_active(self, active: bool):
        self.is_selected = active
        self.setProperty("selected", "true" if active else "false")
        self.apply_rank_styling()

    def set_dragging_visual(self, active: bool):
        self.is_dragging = active
        self.apply_rank_styling()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.on_select_cb(self.folder_data, self)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.on_double_click_cb(self.folder_data)
        super().mouseDoubleClickEvent(event)


class LumenProjectListContainer(QWidget):
    """Contenedor interactivo con reordenamiento animado vertical (solo sube y baja con posición X fija)."""
    
    order_changed = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows = []
        self.all_folders = []
        self.row_height = 84
        self.spacing = 4
        self.dragged_row = None
        self.drag_start_global_y = 0
        self.drag_start_local_y = 0
        self.target_slot = 0
        self.anims = []

        self.setProperty("class", "project_list_card")
        self.setStyleSheet("QWidget { background-color: transparent; }")

    def minimumSizeHint(self):
        total_h = max(1, len(self.rows) * (self.row_height + self.spacing))
        return QSize(200, total_h)

    def sizeHint(self):
        total_h = max(1, len(self.rows) * (self.row_height + self.spacing))
        return QSize(300, total_h)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.width()
        for r in self.rows:
            r.resize(w, self.row_height)
        self.relayout_rows(animate=False)

    def relayout_rows(self, animate=True, exclude=None, target_slot=None):
        """Posiciona las filas verticalmente con animación suave de subida/bajada."""
        for a in self.anims:
            if a != getattr(self, "finish_anim", None):
                a.stop()
        self.anims = []

        w = self.width()
        slot = 0
        for r in self.rows:
            if r == exclude:
                continue
            if exclude and target_slot is not None and slot == target_slot:
                slot += 1
            
            target_y = slot * (self.row_height + self.spacing)
            r.resize(w, self.row_height)
            
            if animate and r.y() != target_y:
                anim = QPropertyAnimation(r, b"pos", self)
                anim.setDuration(160)
                anim.setEasingCurve(QEasingCurve.OutCubic)
                anim.setStartValue(r.pos())
                anim.setEndValue(QPoint(0, target_y))
                anim.start()
                self.anims.append(anim)
            else:
                r.move(0, target_y)
            slot += 1

    def begin_drag(self, row, global_y):
        """Inicia el arrastre vertical de la fila."""
        self.dragged_row = row
        self.drag_start_global_y = global_y
        self.drag_start_local_y = row.y()
        self.current_slot = self.rows.index(row)
        self.target_slot = self.current_slot
        row.raise_()
        row.set_dragging_visual(True)

    def update_drag(self, row, global_y):
        """Actualiza la posición vertical (X siempre 0, solo sube y baja)."""
        if not self.dragged_row or self.dragged_row != row:
            return
        
        delta_y = global_y - self.drag_start_global_y
        min_y = 0
        max_y = (len(self.rows) - 1) * (self.row_height + self.spacing)
        new_y = max(min_y, min(max_y, self.drag_start_local_y + delta_y))
        
        # Posición horizontal estrictamente fija en 0
        row.move(0, new_y)

        # Calcular slot de destino y animar desplazamiento de las demás filas
        slot_size = self.row_height + self.spacing
        hover_slot = max(0, min(len(self.rows) - 1, round(new_y / slot_size)))
        
        if hover_slot != self.target_slot:
            self.target_slot = hover_slot
            self.relayout_rows(animate=True, exclude=row, target_slot=hover_slot)

    def end_drag(self, row):
        """Finaliza el arrastre y anima la colocación en el slot seleccionado."""
        if not self.dragged_row or self.dragged_row != row:
            return

        final_y = self.target_slot * (self.row_height + self.spacing)
        
        self.finish_anim = QPropertyAnimation(row, b"pos", self)
        self.finish_anim.setDuration(160)
        self.finish_anim.setEasingCurve(QEasingCurve.OutCubic)
        self.finish_anim.setStartValue(row.pos())
        self.finish_anim.setEndValue(QPoint(0, final_y))

        def on_finished():
            row.set_dragging_visual(False)
            if row in self.rows:
                self.rows.remove(row)
                self.rows.insert(self.target_slot, row)
            
            # Reordenar lista de carpetas y guardar
            self.all_folders = [r.folder_data for r in self.rows]
            save_lumen_order([f["name"] for f in self.all_folders])

            # Actualizar colores y badges según nueva posición
            for idx, r in enumerate(self.rows):
                r.set_rank(idx + 1)
            
            self.relayout_rows(animate=False)
            self.dragged_row = None
            self.order_changed.emit(self.all_folders)

        self.finish_anim.finished.connect(on_finished)
        self.finish_anim.start()
        self.anims.append(self.finish_anim)


class LumenView(QWidget):
    """Vista principal del dominio LUMEN con Selector de Proyectos y Workspace Dashboard interactivo."""
    
    project_selected = Signal(dict)

    def __init__(self, config_target=None, parent=None):
        super().__init__(parent)
        self.config_target = config_target or get_target_config_path()
        self.selected_project = None
        self.selected_path = ""

        self.init_ui()
        self.load_projects()

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Main Stacked Widget (Página 0: Selector de proyectos, Página 1: Workspace Dashboard)
        self.main_stack = QStackedWidget(self)

        # =============================================================
        # PÁGINA 0: SELECTOR DE PROYECTOS
        # =============================================================
        self.selector_page = QWidget()
        sel_layout = QVBoxLayout(self.selector_page)
        sel_layout.setContentsMargins(0, 0, 0, 0)
        sel_layout.setSpacing(12)

        # Encabezado
        lbl_t = QLabel("💻 LUMEN")
        lbl_t.setProperty("class", "page_title")
        
        lbl_sub = QLabel("Motor Dev & IA Local — Espacio de Trabajo")
        lbl_sub.setProperty("class", "page_subtitle")
        
        sel_layout.addWidget(lbl_t)
        sel_layout.addWidget(lbl_sub)

        # Barra de Control y Búsqueda
        top_card = QFrame()
        top_card.setProperty("class", "surface")
        top_layout = QVBoxLayout(top_card)
        top_layout.setSpacing(10)

        # Fila 1: Ruta y Contador
        row_path = QHBoxLayout()
        self.lbl_projects_path = QLabel("📁 Ruta: ")
        self.lbl_projects_path.setStyleSheet("font-family: monospace; font-size: 12px; font-weight: 500;")
        
        self.lbl_projects_count = QLabel("0 proyectos")
        self.lbl_projects_count.setProperty("class", "count_badge")

        row_path.addWidget(self.lbl_projects_path, 1)
        row_path.addWidget(self.lbl_projects_count)
        top_layout.addLayout(row_path)

        # Fila 2: Barra de búsqueda reactiva y recarga
        row_search = QHBoxLayout()
        row_search.setContentsMargins(0, 0, 0, 0)
        row_search.setSpacing(8)

        self.txt_filter = QLineEdit()
        self.txt_filter.setPlaceholderText("🔍 Buscar proyecto para trabajar en Lumen...")
        self.txt_filter.textChanged.connect(self.filter_projects)
        
        btn_refresh = QPushButton("🔄 Recargar")
        btn_refresh.setProperty("class", "browse")
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.clicked.connect(self.load_projects)

        row_search.addWidget(self.txt_filter, 1)
        row_search.addWidget(btn_refresh)
        top_layout.addLayout(row_search)

        sel_layout.addWidget(top_card)

        # Selector de proyectos scrollable
        lbl_list_header = QLabel("📦 Proyectos Disponibles (Doble clic para entrar • Arrastra ☰ para priorizar):")
        lbl_list_header.setStyleSheet("font-weight: 700; font-size: 12px; color: #9ca3af;")
        sel_layout.addWidget(lbl_list_header)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        # Contenedor animado vertical
        self.list_container = LumenProjectListContainer()
        self.list_container.order_changed.connect(self.on_order_changed)
        self.scroll_area.setWidget(self.list_container)

        sel_layout.addWidget(self.scroll_area, 1)
        self.main_stack.addWidget(self.selector_page)

        # =============================================================
        # PÁGINA 1: WORKSPACE DASHBOARD DEL PROYECTO SELECCIONADO
        # =============================================================
        self.workspace_page = LumenProjectWorkspaceView()
        self.workspace_page.back_requested.connect(self.go_back_to_selector)
        self.main_stack.addWidget(self.workspace_page)

        root_layout.addWidget(self.main_stack)

    def load_projects(self):
        """Carga proyectos del disco y los ordena según la preferencia guardada del usuario."""
        base_dir, folders = list_project_folders(self.config_target)
        self.lbl_projects_path.setText(f"📁 Ruta: {base_dir if base_dir else 'No configurada en config.toml'}")
        self.lbl_projects_count.setText(f"{len(folders)} {'proyecto' if len(folders) == 1 else 'proyectos'}")

        # Limpiar filas existentes en el contenedor
        for r in self.list_container.rows:
            r.deleteLater()
        self.list_container.rows = []
        self.list_container.all_folders = []

        if not base_dir or not os.path.exists(base_dir) or not folders:
            self.selected_project = None
            self.selected_path = ""
            return

        # Ordenar según el orden guardado
        saved_order = load_lumen_order()
        
        def sort_key(f):
            name = f["name"]
            path = f["path"]
            if name in saved_order:
                return (0, saved_order.index(name))
            elif path in saved_order:
                return (0, saved_order.index(path))
            return (1, name.lower())

        sorted_folders = sorted(folders, key=sort_key)
        self.list_container.all_folders = sorted_folders

        # Crear filas dentro del contenedor
        first_row = None
        for idx, folder in enumerate(sorted_folders):
            rank = idx + 1
            row = LumenProjectRowWidget(
                folder_data=folder,
                rank=rank,
                container=self.list_container,
                on_select_cb=self.on_row_clicked,
                on_double_click_cb=self.open_project_workspace
            )
            row.show()
            self.list_container.rows.append(row)
            if idx == 0:
                first_row = (folder, row)

        # Ajustar altura total del contenedor para el QScrollArea
        total_h = len(sorted_folders) * (self.list_container.row_height + self.list_container.spacing)
        self.list_container.setFixedHeight(total_h)
        self.list_container.relayout_rows(animate=False)

        # Mantener seleccionado el proyecto previo o seleccionar el primero por defecto
        target_folder = None
        target_row = None
        if self.selected_path:
            for r in self.list_container.rows:
                if r.folder_data["path"] == self.selected_path:
                    target_folder = r.folder_data
                    target_row = r
                    break

        if target_folder and target_row:
            for r in self.list_container.rows:
                r.set_active(r == target_row)
            self.selected_project = target_folder
            self.selected_path = target_folder["path"]
            if hasattr(self, "workspace_page") and self.main_stack.currentIndex() == 1:
                self.workspace_page.set_project(target_folder, reset_terminal=True)
            self.project_selected.emit(target_folder)

        if hasattr(self, "txt_filter") and self.txt_filter.text().strip():
            self.filter_projects(self.txt_filter.text().strip())

    def open_project_workspace(self, folder_data: dict):
        """Abre el espacio de trabajo del proyecto al hacer doble clic."""
        self.selected_project = folder_data
        self.selected_path = folder_data.get("path", "")
        self.workspace_page.set_project(folder_data, reset_terminal=True)
        self.main_stack.setCurrentIndex(1)

    def go_back_to_selector(self):
        """Regresa a la pantalla del selector de proyectos."""
        self.main_stack.setCurrentIndex(0)
        self.load_projects()

    def on_order_changed(self, new_folders):
        """Callback cuando el usuario reordena arrastrando verticalmente."""
        pass

    def on_row_clicked(self, folder_data, clicked_row):
        """Maneja la selección interactiva de un proyecto."""
        for r in self.list_container.rows:
            r.set_active(r == clicked_row)

        self.selected_project = folder_data
        self.selected_path = folder_data["path"]
        if hasattr(self, "workspace_page") and self.main_stack.currentIndex() == 1:
            self.workspace_page.set_project(folder_data, reset_terminal=True)
        self.project_selected.emit(folder_data)

    def filter_projects(self, query):
        """Filtra la lista de proyectos en tiempo real según el texto de búsqueda."""
        q = query.strip().lower()
        visible_count = 0
        for r in self.list_container.rows:
            match = (q in r.folder_data["name"].lower()) if q else True
            r.setVisible(match)
            if match:
                visible_count += 1





