#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS | UMBRA - BACKGROUND TELEMETRY & RIBBON WORKERS
# =====================================================================

from PySide6.QtCore import QThread, Signal
from core.umbra_backend import UmbraHardwareCollector, UmbraStatusRibbonCollector
import subprocess

class UmbraRibbonWorker(QThread):
    """
    Hilo de trabajo desacoplado para tareas de mayor I/O:
    - Escaneo de Vault de Obsidian
    - Chequeo de actualizaciones pacman (checkupdates)
    - Verificación de snapshots Btrfs
    """
    ribbon_updated = Signal(dict)

    def __init__(self, collector: UmbraStatusRibbonCollector, parent=None):
        super().__init__(parent)
        self.collector = collector
        self._running = True

    def run(self):
        while self._running:
            try:
                data = self.collector.collect_ribbon_snapshot()
                if self._running:
                    self.ribbon_updated.emit(data)
            except Exception:
                pass
            
            # Intervalo de 2 segundos para reflejo inmediato de notas y snapshots
            for _ in range(20):
                if not self._running:
                    break
                self.msleep(100)

    def stop(self):
        self._running = False
        self.wait(1000)


class UmbraTelemetryWorker(QThread):
    """
    Hilo de ultra-alta frecuencia para métricas vivas de hardware (800ms).
    Desacoplado de I/O pesado para máxima fluidez y cero bloqueos.
    """
    telemetry_updated = Signal(dict)
    ribbon_updated = Signal(dict)
    snapshot_result = Signal(bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True
        self.hw_collector = UmbraHardwareCollector()
        self.ribbon_collector = UmbraStatusRibbonCollector()
        
        # Sub-worker desacoplado para la cinta de estado
        self.ribbon_worker = UmbraRibbonWorker(self.ribbon_collector, self)
        self.ribbon_worker.ribbon_updated.connect(self.ribbon_updated)

        self._snapshot_requested = False
        self._snapshot_desc = ""

    def run(self):
        # Iniciar sub-hilo del ribbon
        self.ribbon_worker.start()

        while self._running:
            # 1. Telemetría de hardware rápida (< 1ms)
            try:
                data_hw = self.hw_collector.collect_snapshot()
                if self._running:
                    self.telemetry_updated.emit(data_hw)
            except Exception:
                pass

            # 2. Snapshot si fue solicitado
            if self._snapshot_requested:
                self._execute_snapshot()

            # Cadencia de 800ms para máxima suavidad visual
            for _ in range(8):
                if not self._running:
                    break
                self.msleep(100)

    def trigger_snapshot(self, desc: str = "Instantánea manual desde Abraxas UMBRA"):
        self._snapshot_desc = desc
        self._snapshot_requested = True

    def _execute_snapshot(self):
        self._snapshot_requested = False
        desc = self._snapshot_desc or "Instantánea desde Abraxas UMBRA"
        try:
            cmd = ["pkexec", "snapper", "create", "-c", "root", "-d", desc]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if res.returncode == 0:
                self.snapshot_result.emit(True, f"Snapshot creado con éxito: {desc}")
                # Refrescar ribbon inmediatamente
                data_ribbon = self.ribbon_collector.collect_ribbon_snapshot()
                self.ribbon_updated.emit(data_ribbon)
            else:
                err = res.stderr.strip() or "Permisos denegados o cancelado."
                self.snapshot_result.emit(False, f"Fallo al crear snapshot: {err}")
        except subprocess.TimeoutExpired:
            self.snapshot_result.emit(False, "Tiempo de espera agotado al solicitar permisos.")
        except Exception as e:
            self.snapshot_result.emit(False, f"Error: {str(e)}")

    def stop(self):
        self._running = False
        if hasattr(self, "ribbon_worker") and self.ribbon_worker.isRunning():
            self.ribbon_worker.stop()
        self.wait(1000)
