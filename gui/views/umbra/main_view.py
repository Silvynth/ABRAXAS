#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS | UMBRA - MAIN VIEW
# =====================================================================

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame, QHBoxLayout, 
    QMessageBox, QInputDialog, QSizePolicy
)
from PySide6.QtCore import Qt
from gui.views.umbra.top_telemetry_hud import UmbraTopTelemetryHUD
from gui.views.umbra.status_ribbon import UmbraStatusRibbon
from gui.views.umbra.workers import UmbraTelemetryWorker
from gui.views.umbra.drawer_terminal import UmbraDrawerTerminal
from gui.views.umbra.sectors_view import UmbraSectorsDeck

class UmbraView(QWidget):
    """
    Vista principal del dominio UMBRA:
    - Cubierta Superior: Inmutable, fija y responsive (Telemetry HUD + Status Ribbon).
    - Cubierta Inferior: Área operativa dinámica (Sectores en columnas + Terminal deslizante).
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.init_worker()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # =============================================================
        # 1. CUBIERTA SUPERIOR FIJA E INMUTABLE (PINNED TOP DECK)
        # NUNCA SE DESPLAZA NI SE MUEVE POR NINGUNA ACCIÓN INFERIOR
        # =============================================================
        self.top_deck = QWidget()
        self.top_deck.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        top_layout = QVBoxLayout(self.top_deck)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(10)

        # Cabecera de Página
        header_box = QVBoxLayout()
        header_box.setSpacing(3)
        
        lbl_t = QLabel("⚙  UMBRA")
        lbl_t.setProperty("class", "page_title")
        
        lbl_sub = QLabel("Núcleo Operador & Kernel — Resiliencia Btrfs, Monitoreo SRE e Infraestructura")
        lbl_sub.setProperty("class", "page_subtitle")
        
        header_box.addWidget(lbl_t)
        header_box.addWidget(lbl_sub)
        top_layout.addLayout(header_box)

        # Barra 1: PANEL FLOTANTE SUPERIOR (TELEMETRÍA HAUTE HORLOGERIE)
        self.telemetry_hud = UmbraTopTelemetryHUD()
        self.telemetry_hud.btn_snap.clicked.connect(self._on_snapshot_clicked)
        top_layout.addWidget(self.telemetry_hud)

        # Barra 2: CINTA DE ESTADO COMPLEMENTARIA (SEGUNDO CEREBRO, PAQUETES, BTRFS, CICLO 24H)
        self.status_ribbon = UmbraStatusRibbon()
        top_layout.addWidget(self.status_ribbon)

        # Añadir cubierta fija sin stretch (stretch=0)
        layout.addWidget(self.top_deck, 0)

        # =============================================================
        # 2. CUBIERTA INFERIOR DE TRABAJO (LOWER WORK DECK)
        # Ocupa el espacio restante (stretch=1). Los sectores y la consola
        # operan exclusivamente dentro de esta zona sin afectar lo superior.
        # =============================================================
        self.work_deck = QWidget()
        self.work_deck.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        work_layout = QVBoxLayout(self.work_deck)
        work_layout.setContentsMargins(0, 0, 0, 0)
        work_layout.setSpacing(8)

        # 3 Columnas Operativas de Sectores
        self.sectors_deck = UmbraSectorsDeck(self.work_deck)
        work_layout.addWidget(self.sectors_deck, 1)

        # Terminal Táctica Desplegable (Sliding Drawer con Manija _)
        self.drawer_terminal = UmbraDrawerTerminal(self.work_deck)
        self.drawer_terminal.state_changed.connect(self._on_terminal_state_changed)
        work_layout.addWidget(self.drawer_terminal, 0)

        layout.addWidget(self.work_deck, 1)

    def _on_terminal_state_changed(self, mode):
        """Oculta o muestra los sectores según el estado de la terminal sin mover la cubierta superior."""
        if mode == "full" or mode is True:
            self.sectors_deck.setVisible(False)
        else:
            self.sectors_deck.setVisible(True)

    def init_worker(self):
        """Inicia el worker de telemetría en segundo plano."""
        self.worker = UmbraTelemetryWorker(self)
        self.worker.telemetry_updated.connect(self.telemetry_hud.update_telemetry)
        self.worker.ribbon_updated.connect(self.status_ribbon.update_ribbon)
        self.worker.snapshot_result.connect(self._on_snapshot_result)
        self.worker.start()

    def _on_snapshot_clicked(self):
        """Dispara creación de snapshot rápido."""
        text, ok = QInputDialog.getText(
            self, 
            "Snapshot Btrfs Express", 
            "Descripción de la instantánea:",
            text="Snapshot manual desde Abraxas UMBRA"
        )
        if ok and text.strip():
            desc = text.strip()
            self.telemetry_hud.btn_snap.setEnabled(False)
            self.telemetry_hud.btn_snap.setText("⏳ Creando...")
            
            # Registrar en la consola
            self.drawer_terminal.display.log_btrfs("BTRFS", f"Solicitando creación de snapshot atómico: <b>{desc}</b>...")
            self.worker.trigger_snapshot(desc)

    def _on_snapshot_result(self, success: bool, message: str):
        self.telemetry_hud.btn_snap.setEnabled(True)
        self.telemetry_hud.btn_snap.setText("📸 Snapshot Rápido")
        if success:
            self.drawer_terminal.display.log_success("BTRFS", message)
            QMessageBox.information(self, "Escudo Btrfs", message)
        else:
            self.drawer_terminal.display.log_error("BTRFS", message)
            QMessageBox.warning(self, "Escudo Btrfs", message)

    def closeEvent(self, event):
        if hasattr(self, "worker") and self.worker.isRunning():
            self.worker.stop()
        super().closeEvent(event)
