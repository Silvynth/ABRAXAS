#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS | UMBRA - MAIN VIEW
# =====================================================================

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame

class UmbraView(QWidget):
    """Vista principal del dominio UMBRA (Núcleo Operador & Kernel)."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        lbl_t = QLabel("⚙ UMBRA")
        lbl_t.setProperty("class", "page_title")
        
        lbl_sub = QLabel("Núcleo Operador & Kernel")
        lbl_sub.setProperty("class", "page_subtitle")
        
        layout.addWidget(lbl_t)
        layout.addWidget(lbl_sub)

        card = QFrame()
        card.setProperty("class", "surface")
        c_lay = QVBoxLayout(card)
        
        lbl_desc = QLabel("Mantenimiento del sistema, estado de Kernels y respaldos atómicos Btrfs (Snapshots).")
        lbl_desc.setProperty("class", "card_desc")
        lbl_desc.setWordWrap(True)
        c_lay.addWidget(lbl_desc)

        layout.addWidget(card)
        layout.addStretch()

