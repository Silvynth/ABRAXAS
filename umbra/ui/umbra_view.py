#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS 2.0 | UMBRA - MAIN DOMAIN VIEW (ORCHESTRATOR)
# =====================================================================

from PySide6.QtWidgets import QWidget, QVBoxLayout, QFrame, QLabel, QHBoxLayout, QStackedWidget
from PySide6.QtCore import Qt

from core.theme import MONOCHROME_PALETTE as P
from umbra.ui.hud import UmbraTopTelemetryHUD
from umbra.ui.ribbon import UmbraStatusRibbon
from umbra.ui.sectors import (
    Sector0ResilienceView, Sector1SoftwareView, Sector2HygieneView
)
from umbra.workers.telemetry_worker import UmbraTelemetryWorker, UmbraRibbonWorker
from ui.controls.switcher_pill import SectorSwitcherPill
from ui.terminal.cyber_terminal import CyberTerminal

class UmbraView(QWidget):
    """
    Vista principal del Dominio UMBRA (Abraxas 2.0):
    1. Parte superior: Ambos paneles fijados (HUD de Telemetría + Cinta de Estado Ribbon).
    2. Navegación capsular de 3 Sectores (Sector 00 habilitado; Sectores 01 y 02 en preparación).
    3. Zona central: QStackedWidget con los sectores tácticos del sistema.
    4. Parte inferior: Terminal interactiva CyberTerminal.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("UmbraView")
        self.init_ui()
        self.start_workers()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # -------------------------------------------------------------
        # 1. PANELES SUPERIORES FIJADOS (HUD TELEMETRÍA + RIBBON DE ESTADO)
        # -------------------------------------------------------------
        top_container = QWidget()
        top_layout = QVBoxLayout(top_container)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(8)

        self.hud = UmbraTopTelemetryHUD(self)
        self.ribbon = UmbraStatusRibbon(self)

        top_layout.addWidget(self.hud)
        top_layout.addWidget(self.ribbon)
        layout.addWidget(top_container)

        # -------------------------------------------------------------
        # 2. BARRA DE NAVEGACIÓN CAPSULAR (3 SECTORES DEL SISTEMA)
        # -------------------------------------------------------------
        umbra_sectors = [
            ("🛡  SECTOR 00: RESILIENCIA BTRFS", "Escudo Btrfs, Timeline de Snapshots & Bootloader Limine/Kernels"),
            ("📦  SECTOR 01: SOFTWARE & AUDITORÍA", "Centro de actualizaciones Pacman, Auditoría Nvidia y Dry-Run"),
            ("🧹  SECTOR 02: HIGIENIZACIÓN & DAEMONS", "Inspector de almacenamiento Btrfs/Steam, purga SRE y demonios Systemd")
        ]
        self.pill_nav = SectorSwitcherPill(sectors=umbra_sectors)
        self.pill_nav.sector_changed.connect(self.switch_sector)
        layout.addWidget(self.pill_nav)

        # -------------------------------------------------------------
        # 3. ZONA CENTRAL DINÁMICA: SECTORES TÁCTICOS (QStackedWidget)
        # -------------------------------------------------------------
        self.main_stack = QStackedWidget()

        # Sector 00: Resiliencia (HABILITADO & COMPLETO)
        self.sector0 = Sector0ResilienceView(self)
        self.sector0.log_emitted.connect(self._on_log_emitted)
        self.sector0.action_requested.connect(self._on_action_requested)
        self.main_stack.addWidget(self.sector0)

        # Sector 01: Software (Placeholder en preparación)
        self.sector1 = Sector1SoftwareView(self)
        self.main_stack.addWidget(self.sector1)

        # Sector 02: Higiene (Placeholder en preparación)
        self.sector2 = Sector2HygieneView(self)
        self.main_stack.addWidget(self.sector2)

        layout.addWidget(self.main_stack, 1)

        # -------------------------------------------------------------
        # 4. TERMINAL TÁCTICA DEBAJO
        # -------------------------------------------------------------
        self.terminal = CyberTerminal(prompt="umbra@cachyos:~$", parent=self)
        self.terminal.append_raw_line("❖ UMBRA KERNEL & SYSTEM OPERATOR [Neos 2.0.0]")
        self.terminal.append_raw_line("● Hilos de telemetría iniciados en segundo plano.")
        self.terminal.state_changed.connect(self._on_terminal_state_changed)
        layout.addWidget(self.terminal)

    def switch_sector(self, index: int):
        self.main_stack.setCurrentIndex(index)
        names = ["SECTOR 00: RESILIENCIA BTRFS", "SECTOR 01: SOFTWARE & AUDITORÍA", "SECTOR 02: HIGIENIZACIÓN & DAEMONS"]
        if 0 <= index < len(names):
            self.terminal.log_info("NAV", f"Sector activo: {names[index]}")

    def start_workers(self):
        """Inicia los hilos de telemetría de forma asíncrona."""
        self.telemetry_worker = UmbraTelemetryWorker(self)
        self.telemetry_worker.data_updated.connect(self.hud.update_telemetry)
        self.telemetry_worker.start()

        self.ribbon_worker = UmbraRibbonWorker(self)
        self.ribbon_worker.ribbon_updated.connect(self.ribbon.update_ribbon)
        self.ribbon_worker.start()

    def _on_terminal_state_changed(self, mode: str):
        if mode == "maximized":
            self.main_stack.setVisible(False)
            self.pill_nav.setVisible(False)
        else:
            self.main_stack.setVisible(True)
            self.pill_nav.setVisible(True)

    def _on_log_emitted(self, msg: str):
        self.terminal.append_log(msg)

    def _on_action_requested(self, action: str, data: dict):
        self.terminal.log_info("ACTION", f"Acción de sistema: <b>{action}</b> {data if data else ''}")

    def closeEvent(self, event):
        """Detención limpia de hilos."""
        if hasattr(self, "telemetry_worker") and self.telemetry_worker.isRunning():
            self.telemetry_worker.stop()
            self.telemetry_worker.wait(500)
        if hasattr(self, "ribbon_worker") and self.ribbon_worker.isRunning():
            self.ribbon_worker.stop()
            self.ribbon_worker.wait(500)
        super().closeEvent(event)
