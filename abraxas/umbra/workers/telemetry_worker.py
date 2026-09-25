#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS 2.0 | UMBRA - TELEMETRY WORKERS (ASYNC QTHREAD)
# =====================================================================

import time
from PySide6.QtCore import QThread, Signal
from abraxas.umbra.services.telemetry import UmbraHardwareCollector, UmbraStatusRibbonCollector

class UmbraTelemetryWorker(QThread):
    """Worker asíncrono para telemetría de hardware en tiempo real."""
    data_updated = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.collector = UmbraHardwareCollector()
        self.running = True

    def stop(self):
        self.running = False

    def run(self):
        while self.running:
            try:
                snapshot = self.collector.collect_snapshot()
                self.data_updated.emit(snapshot)
            except Exception:
                pass
            time.sleep(0.8)

class UmbraRibbonWorker(QThread):
    """Worker asíncrono para métricas de Obsidian, Pacman y Btrfs."""
    ribbon_updated = Signal(dict)

    def __init__(self, vault_dir="/home/silvynth/Vault/01_Obsidian", parent=None):
        super().__init__(parent)
        self.collector = UmbraStatusRibbonCollector(vault_dir=vault_dir)
        self.running = True

    def stop(self):
        self.running = False

    def run(self):
        while self.running:
            try:
                snapshot = self.collector.collect_ribbon_snapshot()
                self.ribbon_updated.emit(snapshot)
            except Exception:
                pass
            time.sleep(2.5)
