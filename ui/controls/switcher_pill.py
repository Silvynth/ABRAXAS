"""
❖ ABRAXAS 2.0 | Shared UI: SectorSwitcherPill
Cápsula táctica de navegación para alternar fluidamente entre los sectores de desarrollo.
Permite alternar entre vista de 3 columnas simultáneas (Pilares) y sectores individuales.
"""

from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt, Signal

class SectorSwitcherPill(QFrame):
    """Píldora selectora para alternar entre sub-sectores tácticos o vista columnas."""
    
    sector_changed = Signal(int)

    def __init__(self, sectors=None, parent=None):
        super().__init__(parent)
        self.buttons = []
        self.sectors = sectors or [
            ("☷  SECTOR 0: TOPOLOGÍA & ESTADO", "Vista ejecutiva limpia: grafo en vertical, commits, autores y estado de archivos"),
            ("🌿  SECTOR 1: PROTOCOLO GIT", "Control de versiones, staging, ramas y sincronización"),
            ("⚙  SECTOR 2: ENTORNOS & RUNTIME", "Venvs, editores de código y Docker"),
            ("🧠  SECTOR 3: HERRAMIENTAS & IA", "Copiloto local, auditoría y documentación")
        ]
        self.init_ui()

    def init_ui(self):
        self.setProperty("class", "switcher_pill")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        for idx, (title, tip) in enumerate(self.sectors):
            btn = QPushButton(title)
            btn.setProperty("class", "switcher_pill_btn")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(tip)
            btn.setFixedHeight(30)
            btn.clicked.connect(lambda _, i=idx: self.select_sector(i))
            self.buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch()
        self.select_sector(0)

    def select_sector(self, index: int):
        for i, b in enumerate(self.buttons):
            b.setChecked(i == index)
        self.sector_changed.emit(index)
