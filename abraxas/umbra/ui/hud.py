#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS 2.0 | UMBRA - TOP TELEMETRY HUD (THEME LINKED & DUAL FILAMENT)
# =====================================================================

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame, 
    QProgressBar, QPushButton, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QVariantAnimation, QEasingCurve
from PySide6.QtGui import QColor, QCursor

from abraxas.core.theme import MONOCHROME_PALETTE as P

class FilamentBar(QProgressBar):
    """Micro-filamento luminoso ultra-delgado de precisión (3px) con animación fluida analógica."""
    def __init__(self, value=0, color_start=None, color_end=None, parent=None):
        super().__init__(parent)
        self.setTextVisible(False)
        self.setFixedHeight(3)
        self.setRange(0, 100)
        super().setValue(value)
        
        c_start = color_start or P["TEXT_TITLES"]
        c_end = color_end or P["TEXT_MUTED"]

        self.setStyleSheet(f"""
            QProgressBar {{
                background-color: {P["BG_HIGHLIGHT"]};
                border: none;
                border-radius: 1px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {c_start}, stop:1 {c_end});
                border-radius: 1px;
            }}
        """)
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(750)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.valueChanged.connect(self._apply_val)

    def _apply_val(self, val):
        super().setValue(int(val))

    def setValue(self, target):
        target = max(0, min(100, int(target)))
        if self._anim.state() == QVariantAnimation.Running:
            self._anim.stop()
        self._anim.setStartValue(self.value())
        self._anim.setEndValue(target)
        self._anim.start()

class TelemetryInstrument(QWidget):
    """Módulo individual Haute Horlogerie (soporta doble barrita para Uso % y Temperatura °C)."""
    def __init__(self, label: str, value: str, subtext: str, bar_pct: int, 
                 c_start: str = None, c_end: str = None, val_suffix: str = "", 
                 is_dual: bool = False, bar_temp_pct: int = 0, parent=None):
        super().__init__(parent)
        self.is_dual = is_dual
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)

        # 1. Micro-etiqueta superior
        lbl_tag = QLabel(label)
        lbl_tag.setStyleSheet(f"""
            font-size: 9px;
            font-weight: 700;
            letter-spacing: 1.5px;
            color: {P["TEXT_MICRO"]};
            text-transform: uppercase;
            font-family: 'JetBrains Mono', monospace;
        """)
        layout.addWidget(lbl_tag)

        # 2. Cifra principal destacada
        val_box = QHBoxLayout()
        val_box.setContentsMargins(0, 0, 0, 0)
        val_box.setSpacing(4)
        
        self.lbl_val = QLabel(value)
        self.lbl_val.setStyleSheet(f"""
            font-size: 16px;
            font-weight: 800;
            color: {P["TEXT_TITLES"]};
            font-family: 'JetBrains Mono', monospace;
        """)
        val_box.addWidget(self.lbl_val)

        self.lbl_suf = None
        if val_suffix:
            self.lbl_suf = QLabel(val_suffix)
            self.lbl_suf.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {P['TEXT_MUTED']}; padding-bottom: 2px;")
            val_box.addWidget(self.lbl_suf, alignment=Qt.AlignBottom)
        val_box.addStretch()
        layout.addLayout(val_box)

        # 3. Barrita(s) de filamento (Doble barrita para Uso y Temperatura)
        if self.is_dual:
            bars_layout = QVBoxLayout()
            bars_layout.setContentsMargins(0, 0, 0, 0)
            bars_layout.setSpacing(2)

            self.bar_use = FilamentBar(bar_pct, c_start or P["TEXT_TITLES"], c_end or P["TEXT_MUTED"])
            self.bar_use.setToolTip("Filamento 1: Uso (%)")
            self.bar_temp = FilamentBar(bar_temp_pct, "rgba(255, 255, 255, 0.70)", "rgba(255, 255, 255, 0.20)")
            self.bar_temp.setToolTip("Filamento 2: Temperatura (°C)")

            bars_layout.addWidget(self.bar_use)
            bars_layout.addWidget(self.bar_temp)
            layout.addLayout(bars_layout)
        else:
            self.bar_use = FilamentBar(bar_pct, c_start, c_end)
            layout.addWidget(self.bar_use)

        # 4. Sub-métrica técnica
        self.lbl_sub = QLabel(subtext)
        self.lbl_sub.setStyleSheet(f"""
            font-size: 10px;
            font-weight: 500;
            color: {P["TEXT_MUTED"]};
            margin-top: 2px;
        """)
        layout.addWidget(self.lbl_sub)

    def set_metric(self, value: str = None, subtext: str = None, bar_pct: int = None, 
                   val_suffix: str = None, bar_temp_pct: int = None):
        if value is not None:
            self.lbl_val.setText(str(value))
        if subtext is not None:
            self.lbl_sub.setText(str(subtext))
        if bar_pct is not None:
            self.bar_use.setValue(int(bar_pct))
        if self.is_dual and bar_temp_pct is not None:
            self.bar_temp.setValue(int(bar_temp_pct))
        if val_suffix is not None and self.lbl_suf is not None:
            self.lbl_suf.setText(str(val_suffix))


class UmbraTopTelemetryHUD(QFrame):
    """
    Panel flotante superior de UMBRA (HUD):
    Enlazado directamente a abraxas.core.theme (Haute Horlogerie / Glass Obsidiana).
    CPU y GPU implementan DOBLE BARRITA (Filamento 1: Uso %, Filamento 2: Temperatura °C).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.setObjectName("umbra_top_telemetry_hud")
        self.setStyleSheet(f"""
            QFrame#umbra_top_telemetry_hud {{
                background-color: {P["BG_SURFACE"]};
                border: 1px solid {P["BORDER_SUBTLE"]};
                border-radius: 10px;
            }}
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 140))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(12)

        def make_divider():
            div = QFrame()
            div.setFrameShape(QFrame.VLine)
            div.setStyleSheet(f"color: {P['BORDER_SUBTLE']}; max-width: 1px; margin: 4px 2px;")
            return div

        # 1. CÓMPUTO: CPU (Doble barrita: Uso % y Temp °C)
        self.inst_cpu = TelemetryInstrument(
            label="PROCESADOR (CPU)",
            value="0% · 0°C",
            subtext="Muestreando CPU...",
            bar_pct=0,
            is_dual=True,
            bar_temp_pct=0
        )
        main_layout.addWidget(self.inst_cpu)
        main_layout.addWidget(make_divider())

        # 2. MEMORIA: RAM DDR5
        self.inst_ram = TelemetryInstrument(
            label="MEMORIA RAM",
            value="-- GB",
            subtext="Muestreando RAM...",
            bar_pct=0,
            c_start=P["TEXT_TITLES"],
            c_end=P["TEXT_MUTED"]
        )
        main_layout.addWidget(self.inst_ram)
        main_layout.addWidget(make_divider())

        # 3. GRÁFICOS: GPU (Doble barrita: Uso % y Temp °C)
        self.inst_gpu = TelemetryInstrument(
            label="GRÁFICOS (GPU)",
            value="0% · 0°C",
            subtext="Muestreando GPU...",
            bar_pct=0,
            is_dual=True,
            bar_temp_pct=0
        )
        main_layout.addWidget(self.inst_gpu)
        main_layout.addWidget(make_divider())

        # 4. ALMACENAMIENTO: BTRFS ROOT
        self.inst_disk = TelemetryInstrument(
            label="ALMACENAMIENTO",
            value="-- TB",
            val_suffix="Libre",
            subtext="Btrfs Root",
            bar_pct=0,
            c_start=P["TEXT_TITLES"],
            c_end=P["TEXT_MUTED"]
        )
        main_layout.addWidget(self.inst_disk)
        main_layout.addWidget(make_divider())

        # 5. ENLACE: RED & PING
        self.inst_net = TelemetryInstrument(
            label="ENLACE DE RED",
            value="-- MB/s",
            subtext="Muestreando Enlace...",
            bar_pct=0,
            c_start=P["TEXT_TITLES"],
            c_end=P["TEXT_MUTED"]
        )
        main_layout.addWidget(self.inst_net)
        main_layout.addWidget(make_divider())

        # 6. POD DE IDENTIDAD & ACCIÓN RÁPIDA (OPERADOR & SNAPSHOT)
        pod_op = QWidget()
        pod_layout = QVBoxLayout(pod_op)
        pod_layout.setContentsMargins(6, 4, 6, 4)
        pod_layout.setSpacing(4)

        row_title = QHBoxLayout()
        row_title.setContentsMargins(0, 0, 0, 0)
        row_title.setSpacing(6)

        self.lbl_op = QLabel("SILVYNTH")
        self.lbl_op.setStyleSheet(f"font-size: 13px; font-weight: 800; color: {P['TEXT_TITLES']}; letter-spacing: 0.8px;")
        row_title.addWidget(self.lbl_op)

        badge_live = QLabel("● ACTIVO")
        badge_live.setStyleSheet(f"""
            font-size: 9px;
            font-weight: 700;
            color: {P["TEXT_TITLES"]};
            background-color: {P["BG_HIGHLIGHT"]};
            border: 1px solid {P["BORDER_SUBTLE"]};
            border-radius: 4px;
            padding: 1px 5px;
        """)
        row_title.addWidget(badge_live)
        row_title.addStretch()
        pod_layout.addLayout(row_title)

        self.lbl_distro = QLabel("CachyOS Linux")
        self.lbl_distro.setStyleSheet(f"font-size: 10px; font-weight: 500; color: {P['TEXT_MUTED']};")
        pod_layout.addWidget(self.lbl_distro)

        self.btn_snap = QPushButton("📸 Snapshot Rápido")
        self.btn_snap.setProperty("class", "cyber_btn_compact")
        self.btn_snap.setCursor(QCursor(Qt.PointingHandCursor))
        pod_layout.addWidget(self.btn_snap)

        main_layout.addWidget(pod_op)

    def update_telemetry(self, data: dict):
        """Actualiza los instrumentos del HUD (CPU y GPU actualizan doble barrita de Uso y Temp)."""
        if not data:
            return

        # 1. CPU (Uso % & Temp °C en Doble Barrita)
        cpu_pct = data.get("cpu_pct", 0)
        cpu_temp = data.get("cpu_temp", 40)
        cpu_ghz = data.get("cpu_ghz", 4.0)
        cpu_model = data.get("cpu_model", "Intel Core")
        self.inst_cpu.set_metric(
            value=f"{cpu_pct}% · {cpu_temp}°C",
            subtext=f"{cpu_ghz} GHz · {cpu_model}",
            bar_pct=cpu_pct,
            bar_temp_pct=min(100, max(0, int(cpu_temp)))
        )

        # 2. RAM
        ram_used = data.get("ram_used_gb", 0.0)
        ram_total = data.get("ram_total_gb", 31.2)
        ram_pct = data.get("ram_pct", 0)
        self.inst_ram.set_metric(
            value=f"{ram_used:.1f} GB",
            subtext=f"{ram_total:.1f} GB Total ({ram_pct}%)",
            bar_pct=ram_pct
        )

        # 3. GPU (Uso % & Temp °C en Doble Barrita)
        gpu_pct = data.get("gpu_pct", 0)
        gpu_temp = data.get("gpu_temp", 45)
        vram_used = data.get("gpu_vram_used_gb", 0.0)
        vram_total = data.get("gpu_vram_total_gb", 12.0)
        gpu_model = data.get("gpu_model", "GPU")
        self.inst_gpu.set_metric(
            value=f"{gpu_pct}% · {gpu_temp}°C",
            subtext=f"VRAM {vram_used:.1f}/{vram_total:.1f} GB · {gpu_model}",
            bar_pct=gpu_pct,
            bar_temp_pct=min(100, max(0, int(gpu_temp)))
        )

        # 4. Storage
        disk_free = data.get("disk_free_tb", 1.8)
        disk_read = data.get("disk_read_mbs", 0.0)
        disk_write = data.get("disk_write_mbs", 0.0)
        disk_used_pct = data.get("disk_used_pct", 10)
        self.inst_disk.set_metric(
            value=f"{disk_free:.1f} TB",
            val_suffix="Libre",
            subtext=f"Btrfs Root · R: {disk_read:.1f}M  W: {disk_write:.1f}M",
            bar_pct=disk_used_pct
        )

        # 5. Network
        net_rx = data.get("net_rx_mbs", 0.0)
        net_tx = data.get("net_tx_mbs", 0.0)
        ping = data.get("net_ping_ms", 15)
        total_rate = net_rx + net_tx
        net_bar = min(100, int((total_rate / 20.0) * 100)) if total_rate > 0.05 else 15
        
        display_val = f"{total_rate:.1f} MB/s" if total_rate >= 0.1 else f"{ping} ms"
        self.inst_net.set_metric(
            value=display_val,
            subtext=f"↓ {net_rx:.1f}M · ↑ {net_tx:.1f}M · {ping} ms",
            bar_pct=net_bar
        )

        # 6. Pod Operador
        operator = data.get("operator_name", "SILVYNTH")
        self.lbl_op.setText(operator)
        distro = data.get("distro_name", "CachyOS Linux")
        kernel = data.get("kernel_version", "")
        if kernel:
            self.lbl_distro.setText(f"{distro} · {kernel}")
