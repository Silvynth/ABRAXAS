"""
❖ ABRAXAS 2.0 | Lumen UI: Fila interactiva de proyecto en selector
Diseño monocromático puro con manija de reordenación, badges tácticos y doble clic.
"""

from pathlib import Path
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor

from lumen.models.project import Project
from core.theme import MONOCHROME_PALETTE as P, get_theme_palette

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
            f"color: {P['TEXT_MUTED']}; font-size: 16px; font-weight: 900; padding: 2px 6px;"
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

        self.lbl_icon = QLabel("📁" if not self.project.is_git else "❖")
        self.lbl_icon.setStyleSheet(f"font-size: 13px; color: {P['TEXT_TITLES']};")
        
        self.lbl_name = QLabel(self.project.name)
        self.lbl_name.setStyleSheet(f"color: {P['TEXT_TITLES']}; font-size: 14px; font-weight: 700; letter-spacing: -0.2px;")
        
        title_row.addWidget(self.lbl_icon)
        title_row.addWidget(self.lbl_name)
        title_row.addStretch()
        info_layout.addLayout(title_row)

        # Ruta en monospace
        self.lbl_path = QLabel(str(self.project.path))
        self.lbl_path.setStyleSheet(f"color: {P['TEXT_MUTED']}; font-size: 11px; font-family: 'JetBrains Mono', monospace;")
        info_layout.addWidget(self.lbl_path)

        layout.addLayout(info_layout, 1)

        # 3. Badges técnicos (SemVer, Rama, Estado Git)
        badges_layout = QHBoxLayout()
        badges_layout.setSpacing(6)

        # Badge SemVer
        self.lbl_semver = QLabel(f"v{self.project.semver}")
        self.lbl_semver.setStyleSheet(
            f"background: {P['BG_HIGHLIGHT']}; border: 1px solid {P['BORDER_SUBTLE']}; "
            f"border-radius: 4px; padding: 3px 7px; color: {P['TEXT_TITLES']}; font-family: 'JetBrains Mono', monospace; font-size: 11px;"
        )
        badges_layout.addWidget(self.lbl_semver)

        # Badge de Rama si es Git
        if self.project.is_git:
            self.lbl_branch = QLabel(f"● {self.project.current_branch or 'git'}")
            self.lbl_branch.setStyleSheet(
                f"background: {P['BG_HIGHLIGHT']}; border: 1px solid {P['BORDER_SUBTLE']}; "
                f"border-radius: 4px; padding: 3px 7px; color: {P['TEXT_BODY']}; font-family: 'JetBrains Mono', monospace; font-size: 11px;"
            )
            badges_layout.addWidget(self.lbl_branch)

        # Indicador de cambios (Clean o Cambios)
        dirty_text = "Clean" if not self.project.is_dirty else f"{self.project.total_changes_count} modif"
        self.lbl_dirty = QLabel(dirty_text)
        self.lbl_dirty.setStyleSheet(
            f"background: transparent; border: 1px solid {P['BORDER_SUBTLE']}; "
            f"border-radius: 4px; padding: 3px 6px; color: {P['TEXT_MUTED']}; font-size: 10px; font-weight: 600; text-transform: uppercase;"
        )
        badges_layout.addWidget(self.lbl_dirty)

        layout.addLayout(badges_layout)

    def refresh_theme(self):
        p = get_theme_palette()
        self.lbl_handle.setStyleSheet(f"color: {p['TEXT_MUTED']}; font-size: 16px; font-weight: 900; padding: 2px 6px;")
        self.lbl_icon.setStyleSheet(f"font-size: 13px; color: {p['TEXT_TITLES']};")
        self.lbl_name.setStyleSheet(f"color: {p['TEXT_TITLES']}; font-size: 14px; font-weight: 700; letter-spacing: -0.2px;")
        self.lbl_path.setStyleSheet(f"color: {p['TEXT_MUTED']}; font-size: 11px; font-family: 'JetBrains Mono', monospace;")
        self.lbl_semver.setStyleSheet(f"background: {p['BG_HIGHLIGHT']}; border: 1px solid {p['BORDER_SUBTLE']}; border-radius: 4px; padding: 3px 7px; color: {p['TEXT_TITLES']}; font-family: 'JetBrains Mono', monospace; font-size: 11px;")
        if hasattr(self, "lbl_branch"):
            self.lbl_branch.setStyleSheet(f"background: {p['BG_HIGHLIGHT']}; border: 1px solid {p['BORDER_SUBTLE']}; border-radius: 4px; padding: 3px 7px; color: {p['TEXT_BODY']}; font-family: 'JetBrains Mono', monospace; font-size: 11px;")
        self.lbl_dirty.setStyleSheet(f"background: transparent; border: 1px solid {p['BORDER_SUBTLE']}; border-radius: 4px; padding: 3px 6px; color: {p['TEXT_MUTED']}; font-size: 10px; font-weight: 600; text-transform: uppercase;")
        if self.is_active:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {p['ACCENT_PILL']};
                    border: 1px solid {p['BORDER_STRONG']};
                    border-radius: 10px;
                }}
            """)

    def set_selected(self, selected: bool):
        self.is_active = selected
        p = get_theme_palette()
        if selected:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {p['ACCENT_PILL']};
                    border: 1px solid {p['BORDER_STRONG']};
                    border-radius: 10px;
                }}
            """)
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
