"""
❖ ABRAXAS 2.0 | Lumen UI: Fila interactiva de proyecto en selector
Diseño monocromático puro con manija de reordenación, badges tácticos y doble clic.
"""

from pathlib import Path
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor

from lumen.models.project import Project

class ProjectSelectorRow(QFrame):
    """Fila interactiva táctica para seleccionar un proyecto en Lumen."""
    
    selected = Signal(Project)
    double_clicked = Signal(Project)

    def __init__(self, project: Project, parent=None):
        super().__init__(parent)
        self.project = project
        self.is_active = False

        self.setProperty("class", "sector_card")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(64)

        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(14)

        # 1. Manija de arrastre (☰)
        self.lbl_handle = QLabel("☰")
        self.lbl_handle.setStyleSheet(
            "color: #64748b; font-size: 16px; font-weight: 900; padding: 2px 6px;"
        )
        self.lbl_handle.setCursor(Qt.SizeVerCursor)
        self.lbl_handle.setToolTip("Arrastrar para reordenar proyectos")
        layout.addWidget(self.lbl_handle)

        # 2. Información del proyecto (Nombre y Ruta)
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        info_layout.setContentsMargins(0, 0, 0, 0)

        # Fila superior de título
        title_row = QHBoxLayout()
        title_row.setSpacing(8)

        lbl_icon = QLabel("📁" if not self.project.is_git else "❖")
        lbl_icon.setStyleSheet("font-size: 13px; color: #ffffff;")
        
        lbl_name = QLabel(self.project.name)
        lbl_name.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: 700; letter-spacing: -0.2px;")
        
        title_row.addWidget(lbl_icon)
        title_row.addWidget(lbl_name)
        title_row.addStretch()
        info_layout.addLayout(title_row)

        # Ruta en monospace
        lbl_path = QLabel(str(self.project.path))
        lbl_path.setStyleSheet("color: #64748b; font-size: 11px; font-family: 'JetBrains Mono', monospace;")
        info_layout.addWidget(lbl_path)

        layout.addLayout(info_layout, 1)

        # 3. Badges técnicos (SemVer, Rama, Estado Git)
        badges_layout = QHBoxLayout()
        badges_layout.setSpacing(6)

        # Badge SemVer
        lbl_semver = QLabel(f"v{self.project.semver}")
        lbl_semver.setStyleSheet(
            "background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); "
            "border-radius: 4px; padding: 3px 7px; color: #ffffff; font-family: 'JetBrains Mono', monospace; font-size: 11px;"
        )
        badges_layout.addWidget(lbl_semver)

        # Badge de Rama si es Git
        if self.project.is_git:
            lbl_branch = QLabel(f"● {self.project.current_branch or 'git'}")
            lbl_branch.setStyleSheet(
                "background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); "
                "border-radius: 4px; padding: 3px 7px; color: #cbd5e1; font-family: 'JetBrains Mono', monospace; font-size: 11px;"
            )
            badges_layout.addWidget(lbl_branch)

        # Indicador de cambios (Clean o Cambios)
        dirty_text = "Clean" if not self.project.is_dirty else f"{self.project.total_changes_count} modif"
        lbl_dirty = QLabel(dirty_text)
        lbl_dirty.setStyleSheet(
            "background: transparent; border: 1px solid rgba(255, 255, 255, 0.08); "
            "border-radius: 4px; padding: 3px 6px; color: #94a3b8; font-size: 10px; font-weight: 600; text-transform: uppercase;"
        )
        badges_layout.addWidget(lbl_dirty)

        layout.addLayout(badges_layout)

    def set_selected(self, selected: bool):
        self.is_active = selected
        if selected:
            self.setStyleSheet(
                "background-color: #1a1c24; border: 1px solid #ffffff; border-radius: 12px;"
            )
        else:
            self.setStyleSheet("")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.selected.emit(self.project)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.double_clicked.emit(self.project)
        super().mouseDoubleClickEvent(event)
