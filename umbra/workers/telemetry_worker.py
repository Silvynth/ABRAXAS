#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS 2.0 | UMBRA - TELEMETRY WORKERS (ASYNC QTHREAD)
# =====================================================================

import time
from PySide6.QtCore import QThread, Signal
from umbra.services.telemetry import UmbraHardwareCollector, UmbraStatusRibbonCollector

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

    def __init__(self, parent=None, vault_dir=None):
        super().__init__(parent)
        # Si el primer argumento posicional fue un string (vault_dir histórico)
        if isinstance(parent, str) and vault_dir is None:
            vault_dir = parent
        if vault_dir is None or not isinstance(vault_dir, str):
            from core.config import load_config
            try:
                cfg = load_config()
                import os
                v = str(cfg.paths.vault_dir)
                if os.path.isdir(os.path.join(v, "01_Obsidian")):
                    vault_dir = os.path.join(v, "01_Obsidian")
                else:
                    vault_dir = v
            except Exception:
                vault_dir = "/home/silvynth/Vault/01_Obsidian"

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
