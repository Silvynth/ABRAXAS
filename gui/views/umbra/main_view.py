#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS | UMBRA - MAIN VIEW
# =====================================================================

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame, QHBoxLayout, 
    QMessageBox, QInputDialog
)
from PySide6.QtCore import Qt
from gui.views.umbra.top_telemetry_hud import UmbraTopTelemetryHUD
from gui.views.umbra.status_ribbon import UmbraStatusRibbon
from gui.views.umbra.workers import UmbraTelemetryWorker

class UmbraView(QWidget):
    """Vista principal del dominio UMBRA (Núcleo Operador & Kernel)."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.init_worker()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # 1. Cabecera de Página
        header_box = QVBoxLayout()
        header_box.setSpacing(4)
        
        lbl_t = QLabel("⚙  UMBRA")
        lbl_t.setProperty("class", "page_title")
        
        lbl_sub = QLabel("Núcleo Operador & Kernel — Resiliencia Btrfs, Monitoreo SRE e Infraestructura")
        lbl_sub.setProperty("class", "page_subtitle")
        
        header_box.addWidget(lbl_t)
        header_box.addWidget(lbl_sub)
        layout.addLayout(header_box)

        # 2. PANEL FLOTANTE SUPERIOR: INSTRUMENT CLUSTER DE TELEMETRÍA DE ALTA GAMA
        self.telemetry_hud = UmbraTopTelemetryHUD()
        self.telemetry_hud.btn_snap.clicked.connect(self._on_snapshot_clicked)
        layout.addWidget(self.telemetry_hud)

        # 3. CINTA DE ESTADO COMPLEMENTARIA (SEGUNDO CEREBRO, PAQUETES, BTRFS, CICLO 24H)
        self.status_ribbon = UmbraStatusRibbon()
        layout.addWidget(self.status_ribbon)

        # 4. CONTENEDOR DE SECTORES OPERATIVOS (MAQUETA VISUAL)
        sectors_frame = QFrame()
        sectors_frame.setProperty("class", "surface")
        s_layout = QVBoxLayout(sectors_frame)
        s_layout.setContentsMargins(20, 20, 20, 20)
        s_layout.setSpacing(14)

        lbl_sec_title = QLabel("<b>🛡️ SECTORES OPERATIVOS DE UMBRA</b>")
        lbl_sec_title.setStyleSheet("font-size: 14px; color: #ffffff;")
        s_layout.addWidget(lbl_sec_title)

        lbl_desc = QLabel(
            "El panel superior muestra la telemetría viva de alta precisión de tu estación (CPU, GPU, RAM, NVMe y Enlace). "
            "En esta zona inferior se desplegarán los 3 sectores de mando: "
            "<b>Sector 1:</b> Instantáneas Atómicas Btrfs & Snapper, "
            "<b>Sector 2:</b> Gestor de Kernels y Evaluación Preventiva de Actualizaciones, y "
            "<b>Sector 3:</b> Purgador de Sistema, Caché y Daemons Vitales."
        )
        lbl_desc.setStyleSheet("font-size: 12px; color: rgba(255, 255, 255, 0.65); line-height: 1.4;")
        lbl_desc.setWordWrap(True)
        s_layout.addWidget(lbl_desc)

        layout.addWidget(sectors_frame)
        layout.addStretch()

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
            self.telemetry_hud.btn_snap.setEnabled(False)
            self.telemetry_hud.btn_snap.setText("⏳ Creando...")
            self.worker.trigger_snapshot(text.strip())

    def _on_snapshot_result(self, success: bool, message: str):
        self.telemetry_hud.btn_snap.setEnabled(True)
        self.telemetry_hud.btn_snap.setText("📸 Snapshot Rápido")
        if success:
            QMessageBox.information(self, "Escudo Btrfs", message)
        else:
            QMessageBox.warning(self, "Escudo Btrfs", message)

    def closeEvent(self, event):
        if hasattr(self, "worker") and self.worker.isRunning():
            self.worker.stop()
        super().closeEvent(event)
