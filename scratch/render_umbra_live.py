import sys
import os
import time
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from gui.views.umbra.main_view import UmbraView

app = QApplication.instance() or QApplication(sys.argv)

view = UmbraView()
view.resize(1180, 720)
view.show()

def capture():
    # Dejar que el worker emita al menos una actualización viva
    view.grab().save("scratch/umbra_live_hud.png")
    view.close()
    app.quit()

QTimer.singleShot(1600, capture)
app.exec()
