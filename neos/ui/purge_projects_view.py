#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS | NEOS - PURGE / DELETE PROJECTS VIEW
# =====================================================================

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QLineEdit, QFrame, QScrollArea,
    QMessageBox
)
from PySide6.QtCore import Qt, Signal

from core.projects import list_project_folders, purge_project_folder, get_projects_dir, check_project_unsaved_changes

class PurgeProjectRowWidget(QFrame):
    """Fila interactiva para mostrar un proyecto con botón de purga directa."""
    
    def __init__(self, folder_data: dict, on_purge_cb, parent=None):
        super().__init__(parent)
        self.folder_data = folder_data
        self.on_purge_cb = on_purge_cb

        self.setProperty("class", "project_row")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)

        # Fila Superior: Nombre + Badge + Botón de Purga
        r_top = QHBoxLayout()
        r_top.setSpacing(10)

        self.lbl_name = QLabel(f"📁 {folder_data['name']}")
        self.lbl_name.setProperty("class", "project_name")
        self.lbl_name.setStyleSheet("font-weight: 700; font-size: 14px; color: #f87171;")
        r_top.addWidget(self.lbl_name)

        # Detectar si es repositorio Git
        git_path = os.path.join(folder_data["path"], ".git")
        tag_text = "Git Repo" if os.path.exists(git_path) else "Carpeta"
        lbl_tag = QLabel(tag_text)
        lbl_tag.setProperty("class", "badge_dir")
        r_top.addWidget(lbl_tag)

        # Badge de cambios sin guardar en Git
        unsaved = folder_data.get("unsaved", {})
        if unsaved.get("has_unsaved"):
            lbl_unsaved = QLabel(f"⚠️ {unsaved.get('summary', 'Cambios sin guardar')}")
            lbl_unsaved.setStyleSheet(
                "font-size: 11px; font-weight: 600; color: #fbbf24; "
                "background: rgba(251, 191, 36, 0.12); border: 1px solid rgba(251, 191, 36, 0.35); "
                "border-radius: 4px; padding: 2px 6px;"
            )
            lbl_unsaved.setToolTip("El proyecto tiene cambios locales no guardados o commits sin subir a GitHub")
            r_top.addWidget(lbl_unsaved)

        # Tamaño en disco
        size_str = folder_data.get("size_str", "")
        if size_str:
            lbl_size = QLabel(f"💾 {size_str}")
            lbl_size.setStyleSheet("font-size: 11px; color: #9ca3af; font-family: monospace;")
            r_top.addWidget(lbl_size)

        r_top.addStretch()

        # Botón de Purga
        btn_purge = QPushButton("🗑️ Purgar")
        btn_purge.setProperty("class", "btn_mode_red")
        btn_purge.setCursor(Qt.PointingHandCursor)
        btn_purge.setToolTip(f"Eliminar definitivamente la carpeta '{folder_data['name']}'")
        btn_purge.clicked.connect(lambda: self.on_purge_cb(self.folder_data))
        r_top.addWidget(btn_purge)

        layout.addLayout(r_top)

        # Fila Inferior: Ruta completa
        lbl_path = QLabel(folder_data["path"])
        lbl_path.setProperty("class", "project_path")
        layout.addWidget(lbl_path)


class PurgeProjectsView(QWidget):
    """Vista de purga para eliminar proyectos de forma segura dentro del directorio de config.toml."""

    project_purged = Signal(str) # Emite la ruta de la carpeta eliminada
    back_requested = Signal()

    def __init__(self, config_target, parent=None):
        super().__init__(parent)
        self.config_target = config_target
        self.row_widgets = []
        self.folders_data = []

        self.init_ui()
        self.load_folders()

    def refresh_folders(self):
        self.load_folders()

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(12)

        # -------------------------------------------------------------
        # 1. BANNER DE ADVERTENCIA
        # -------------------------------------------------------------
        warn_card = QFrame()
        warn_card.setStyleSheet("""
            QFrame {
                background-color: rgba(239, 68, 68, 0.08);
                border: 1px solid rgba(239, 68, 68, 0.35);
                border-radius: 8px;
                padding: 12px 16px;
            }
        """)
        l_warn = QVBoxLayout(warn_card)
        l_warn.setSpacing(4)

        lbl_warn_title = QLabel("⚠️ ZONA DE PURGA PERMANENTE")
        lbl_warn_title.setStyleSheet("font-weight: 700; font-size: 13px; color: #ef4444;")
        l_warn.addWidget(lbl_warn_title)

        self.lbl_warn_desc = QLabel("Las carpetas eliminadas se borrarán por completo del disco. Solo se pueden purgar proyectos dentro de la ruta configurada en config.toml.")
        self.lbl_warn_desc.setStyleSheet("font-size: 12px; color: #fca5a5;")
        self.lbl_warn_desc.setWordWrap(True)
        l_warn.addWidget(self.lbl_warn_desc)

        root_layout.addWidget(warn_card)

        # -------------------------------------------------------------
        # 2. BARRA DE BÚSQUEDA Y CONTADOR
        # -------------------------------------------------------------
        r_filter = QHBoxLayout()
        self.txt_filter = QLineEdit()
        self.txt_filter.setPlaceholderText("🔍 Filtrar proyectos a purgar por nombre...")
        self.txt_filter.textChanged.connect(self.filter_projects)
        r_filter.addWidget(self.txt_filter, 1)

        self.lbl_count = QLabel("0 carpetas")
        self.lbl_count.setProperty("class", "count_badge")
        r_filter.addWidget(self.lbl_count)

        btn_reload = QPushButton("🔄 Recargar")
        btn_reload.setProperty("class", "browse")
        btn_reload.setCursor(Qt.PointingHandCursor)
        btn_reload.clicked.connect(self.load_folders)
        r_filter.addWidget(btn_reload)

        root_layout.addLayout(r_filter)

        # Mensaje de estado de eliminación
        self.lbl_status = QLabel("")
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setStyleSheet("font-size: 12px; font-weight: 600; color: #10b981;")
        self.lbl_status.setVisible(False)
        root_layout.addWidget(self.lbl_status)

        # -------------------------------------------------------------
        # 3. LISTADO DE CARPETAS EN RECUADRO UNIFICADO
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

    def load_folders(self):
        base_dir, self.folders_data = list_project_folders(self.config_target)
        self.lbl_count.setText(f"{len(self.folders_data)} {'carpeta' if len(self.folders_data) == 1 else 'carpetas'}")
        
        while self.unified_box_layout.count():
            item = self.unified_box_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        self.row_widgets = []

        if not base_dir or not os.path.exists(base_dir):
            lbl_empty = QLabel(f"⚠️ El directorio establecido en config.toml no existe:\n{base_dir}")
            lbl_empty.setProperty("class", "card_desc")
            lbl_empty.setContentsMargins(16, 16, 16, 16)
            self.unified_box_layout.addWidget(lbl_empty)
            return

        if not self.folders_data:
            lbl_empty = QLabel("ℹ No hay carpetas en el directorio de proyectos para purgar.")
            lbl_empty.setProperty("class", "card_desc")
            lbl_empty.setContentsMargins(16, 16, 16, 16)
            self.unified_box_layout.addWidget(lbl_empty)
            return

        for idx, folder in enumerate(self.folders_data):
            row = PurgeProjectRowWidget(folder, self.confirm_purge_folder)
            if idx == len(self.folders_data) - 1:
                row.setProperty("class", "project_row project_row_last")
            self.unified_box_layout.addWidget(row)
            self.row_widgets.append((folder["name"].lower(), row))

        if self.txt_filter.text().strip():
            self.filter_projects(self.txt_filter.text().strip())

    def filter_projects(self, query):
        q = query.strip().lower()
        visible_count = 0
        for name, row in self.row_widgets:
            match = (q in name) if q else True
            row.setVisible(match)
            if match:
                visible_count += 1
        self.lbl_count.setText(f"{visible_count} {'carpeta' if visible_count == 1 else 'carpetas'}")

    def confirm_purge_folder(self, folder_data: dict):
        """Muestra un diálogo modal de confirmación antes de purgar definitivamente."""
        name = folder_data["name"]
        path = folder_data["path"]

        # 1. Comprobar si hay cambios o archivos sin guardar en Git
        unsaved = check_project_unsaved_changes(path)
        has_unsaved = unsaved.get("has_unsaved", False)

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)

        if has_unsaved:
            box.setWindowTitle("⚠️ Advertencia: Archivos Sin Guardar")
            box.setText(f"<h3>⚠️ ¡Atención: Hay cambios sin guardar en '{name}'!</h3>")

            details = []
            mod_files = unsaved.get("modified_files", [])
            if mod_files:
                details.append(f"<b>📄 Archivos modificados sin confirmar ({len(mod_files)}):</b>")
                for f in mod_files[:6]:
                    details.append(f"&nbsp;&nbsp;• <code>{f}</code>")
                if len(mod_files) > 6:
                    details.append(f"&nbsp;&nbsp;<i>... y {len(mod_files) - 6} más</i>")

            untracked = unsaved.get("untracked_files", [])
            if untracked:
                details.append(f"<b>✨ Archivos nuevos sin seguimiento ({len(untracked)}):</b>")
                for f in untracked[:5]:
                    details.append(f"&nbsp;&nbsp;• <code>{f}</code>")
                if len(untracked) > 5:
                    details.append(f"&nbsp;&nbsp;<i>... y {len(untracked) - 5} más</i>")

            unpushed = unsaved.get("unpushed_commits", 0)
            if unpushed > 0:
                details.append(f"<b>⬆️ Commits locales no subidos al remoto:</b> {unpushed}")

            body_details = "<br>".join(details)
            box.setInformativeText(
                f"El proyecto contiene archivos o modificaciones <b>que no han sido guardadas ni enviadas a Git</b>:<br><br>"
                f"{body_details}<br><br>"
                f"Ruta: <code>{path}</code><br><br>"
                f"Si continúas, <b>estos cambios y todo el proyecto se eliminarán permanentemente al 100%</b> del disco sin posibilidad de recuperación.<br><br>"
                f"<font color='#ef4444'><b>¿Deseas purgar el proyecto de todos modos?</b></font>"
            )
            btn_confirm = box.addButton("🗑️ Purgar de Todos Modos (100%)", QMessageBox.AcceptRole)
        else:
            box.setWindowTitle("⚠️ Confirmar Purga de Proyecto")
            box.setText(f"<h3>¿Estás seguro de purgar el proyecto?</h3>")
            box.setInformativeText(
                f"La carpeta <b>'{name}'</b> y todos sus archivos se eliminarán permanentemente del disco.<br><br>"
                f"<code>{path}</code><br><br>"
                f"<font color='#ef4444'><b>Esta acción es irreversible y purgará el proyecto al 100%.</b></font>"
            )
            btn_confirm = box.addButton("🗑️ Purgar Permanentemente", QMessageBox.AcceptRole)

        btn_cancel = box.addButton("❌ Cancelar", QMessageBox.RejectRole)
        box.setDefaultButton(btn_cancel)
        box.exec()

        if box.clickedButton() == btn_confirm:
            try:
                purge_project_folder(path, self.config_target)

                # Desvincular de orden de Lumen si estaba registrado
                try:
                    from core.paths import get_project_order_file
                    order_file = str(get_project_order_file())
                    if os.path.exists(order_file):
                        import json
                        with open(order_file, "r", encoding="utf-8") as f:
                            order = json.load(f)
                        if name in order:
                            order.remove(name)
                            with open(order_file, "w", encoding="utf-8") as f:
                                json.dump(order, f, indent=2)
                except Exception:
                    pass

                self.lbl_status.setText(f"✅ Proyecto '{name}' purgado al 100% correctamente del sistema.")
                self.lbl_status.setStyleSheet("font-size: 12px; font-weight: 600; color: #10b981;")
                self.lbl_status.setVisible(True)
                
                self.load_folders()
                self.project_purged.emit(path)
            except Exception as e:
                self.lbl_status.setText(f"❌ Error al purgar proyecto: {e}")
                self.lbl_status.setStyleSheet("font-size: 12px; font-weight: 600; color: #ef4444;")
                self.lbl_status.setVisible(True)

