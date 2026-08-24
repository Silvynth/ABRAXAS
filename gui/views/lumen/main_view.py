#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS | LUMEN - MAIN VIEW
# =====================================================================

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame

class LumenView(QWidget):
    """Vista principal del dominio LUMEN (Motor Dev & IA Local)."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        lbl_t = QLabel("💻 LUMEN")
        lbl_t.setProperty("class", "page_title")
        
        lbl_sub = QLabel("Motor Dev & IA Local")
        lbl_sub.setProperty("class", "page_subtitle")
        
        layout.addWidget(lbl_t)
        layout.addWidget(lbl_sub)

        card = QFrame()
        card.setProperty("class", "surface")
        c_lay = QVBoxLayout(card)
        
        lbl_desc = QLabel("Gestión de flujos de desarrollo, Docker, entornos virtuales y asistencia de IA Ollama local.")
        lbl_desc.setProperty("class", "card_desc")
        lbl_desc.setWordWrap(True)
        c_lay.addWidget(lbl_desc)

        layout.addWidget(card)
        layout.addStretch()

