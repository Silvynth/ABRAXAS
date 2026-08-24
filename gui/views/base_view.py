#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS | BASE & PLACEHOLDER VIEWS
# =====================================================================

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame

class PlaceholderView(QWidget):
    """Vista de plantilla para submódulos o páginas en desarrollo."""
    def __init__(self, title, subtitle, desc, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        lbl_t = QLabel(title)
        lbl_t.setProperty("class", "page_title")
        
        lbl_sub = QLabel(subtitle)
        lbl_sub.setProperty("class", "page_subtitle")
        
        layout.addWidget(lbl_t)
        layout.addWidget(lbl_sub)

        card = QFrame()
        card.setProperty("class", "surface")
        c_lay = QVBoxLayout(card)
        
        lbl_desc = QLabel(desc)
        lbl_desc.setProperty("class", "card_desc")
        lbl_desc.setWordWrap(True)
        c_lay.addWidget(lbl_desc)

        layout.addWidget(card)
        layout.addStretch()

