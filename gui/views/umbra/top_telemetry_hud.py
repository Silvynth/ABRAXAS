#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS | UMBRA - TOP TELEMETRY HUD (HAUTE HORLOGERIE DESIGN)
# =====================================================================

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame, 
    QProgressBar, QPushButton, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QVariantAnimation, QEasingCurve
from PySide6.QtGui import QColor, QFont, QCursor

class FilamentBar(QProgressBar):
    """Micro-filamento luminoso ultra-delgado de precisión (3px) con animación fluida analógica."""
    def __init__(self, value=0, color_start="#6366f1", color_end="#a855f7", parent=None):
        super().__init__(parent)
        self.setTextVisible(False)
        self.setFixedHeight(3)
        self.setRange(0, 100)
        super().setValue(value)
        self.setStyleSheet(f"""
            QProgressBar {{
                background-color: rgba(255, 255, 255, 0.07);
                border: none;
                border-radius: 1px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {color_start}, stop:1 {color_end});
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
    """Módulo individual con jerarquía de alta relojería: Micro-label, Cifra, Filamento, Sub-métrica."""
    def __init__(self, label: str, value: str, subtext: str, bar_pct: int, 
                 c_start: str, c_end: str, val_suffix: str = "", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)

        # 1. Micro-etiqueta superior refinada
        lbl_tag = QLabel(label)
        lbl_tag.setStyleSheet("""
            font-size: 9px;
            font-weight: 700;
            letter-spacing: 1.5px;
            color: rgba(255, 255, 255, 0.42);
            text-transform: uppercase;
        """)
        layout.addWidget(lbl_tag)

        # 2. Cifra principal destacada
        val_box = QHBoxLayout()
        val_box.setContentsMargins(0, 0, 0, 0)
        val_box.setSpacing(4)
        
        self.lbl_val = QLabel(value)
        self.lbl_val.setStyleSheet("""
            font-size: 19px;
            font-weight: 800;
            color: #ffffff;
            font-family: 'JetBrains Mono', 'Fira Code', 'DejaVu Sans Mono', monospace;
        """)
        val_box.addWidget(self.lbl_val)

        self.lbl_suf = None
        if val_suffix:
            self.lbl_suf = QLabel(val_suffix)
            self.lbl_suf.setStyleSheet("font-size: 11px; font-weight: 600; color: rgba(255, 255, 255, 0.50); padding-bottom: 2px;")
            val_box.addWidget(self.lbl_suf, alignment=Qt.AlignBottom)
        val_box.addStretch()
        layout.addLayout(val_box)

        # 3. Micro-línea de filamento luminoso
        self.bar = FilamentBar(bar_pct, c_start, c_end)
        layout.addWidget(self.bar)

        # 4. Sub-métrica técnica fina
        self.lbl_sub = QLabel(subtext)
        self.lbl_sub.setStyleSheet("""
            font-size: 10px;
            font-weight: 500;
            color: rgba(255, 255, 255, 0.55);
            margin-top: 2px;
        """)
        layout.addWidget(self.lbl_sub)

    def set_metric(self, value: str = None, subtext: str = None, bar_pct: int = None, val_suffix: str = None):
        if value is not None:
            self.lbl_val.setText(str(value))
        if subtext is not None:
            self.lbl_sub.setText(str(subtext))
        if bar_pct is not None:
            self.bar.setValue(int(bar_pct))
        if val_suffix is not None and self.lbl_suf is not None:
            self.lbl_suf.setText(str(val_suffix))


class UmbraTopTelemetryHUD(QFrame):
    """
    Panel flotante superior de UMBRA:
    Estética Studio SRE / Haute Horlogerie en monobloque de cristal obsidiana.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.setObjectName("umbra_top_telemetry_hud")
        self.setStyleSheet("""
            QFrame#umbra_top_telemetry_hud {
                background-color: rgba(18, 19, 26, 0.95);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
            }
        """)

        # Sombra sutil difusa para efecto flotante
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(12)

        def make_divider():
            div = QFrame()
            div.setFrameShape(QFrame.VLine)
            div.setStyleSheet("color: rgba(255, 255, 255, 0.08); max-width: 1px; margin: 4px 2px;")
            return div

        # 1. CÓMPUTO: CPU
        self.inst_cpu = TelemetryInstrument(
            label="PROCESADOR",
            value="24 %",
            subtext="42°C · 5.4 GHz · i7-14700K",
            bar_pct=24,
            c_start="#06b6d4",
            c_end="#6366f1"
        )
        main_layout.addWidget(self.inst_cpu)
        main_layout.addWidget(make_divider())

        # 2. MEMORIA: RAM DDR5
        self.inst_ram = TelemetryInstrument(
            label="MEMORIA RAM",
            value="5.8 GB",
            subtext="31.2 GB Total · DDR5 (18%)",
            bar_pct=18,
            c_start="#e879f9",
            c_end="#818cf8"
        )
        main_layout.addWidget(self.inst_ram)
        main_layout.addWidget(make_divider())

        # 3. GRÁFICOS: GPU & VRAM
        self.inst_gpu = TelemetryInstrument(
            label="GPU & VRAM",
            value="1.6 GB",
            subtext="RTX 4070 SUPER · 53°C (13%)",
            bar_pct=13,
            c_start="#38bdf8",
            c_end="#6366f1"
        )
        main_layout.addWidget(self.inst_gpu)
        main_layout.addWidget(make_divider())

        # 4. ALMACENAMIENTO: BTRFS ROOT
        self.inst_disk = TelemetryInstrument(
            label="ALMACENAMIENTO",
            value="1.8 TB",
            val_suffix="Libre",
            subtext="Btrfs Root · R: 45M  W: 12M",
            bar_pct=9,
            c_start="#10b981",
            c_end="#34d399"
        )
        main_layout.addWidget(self.inst_disk)
        main_layout.addWidget(make_divider())

        # 5. ENLACE: RED & PING
        self.inst_net = TelemetryInstrument(
            label="ENLACE DE RED",
            value="14.2 MB/s",
            subtext="↓ 12.4M · ↑ 1.8M · 18 ms",
            bar_pct=25,
            c_start="#f59e0b",
            c_end="#fbbf24"
        )
        main_layout.addWidget(self.inst_net)
        main_layout.addWidget(make_divider())

        # 6. POD DE IDENTIDAD & ACCIÓN RÁPIDA (OPERADOR & SNAPSHOT)
        pod_op = QWidget()
        pod_layout = QVBoxLayout(pod_op)
        pod_layout.setContentsMargins(6, 4, 6, 4)
        pod_layout.setSpacing(4)

        # Operador + Badge
        row_title = QHBoxLayout()
        row_title.setContentsMargins(0, 0, 0, 0)
        row_title.setSpacing(6)

        self.lbl_op = QLabel("SILVYNTH")
        self.lbl_op.setStyleSheet("font-size: 13px; font-weight: 800; color: #ffffff; letter-spacing: 0.8px;")
        row_title.addWidget(self.lbl_op)

        badge_live = QLabel("● ACTIVO")
        badge_live.setStyleSheet("""
            font-size: 9px;
            font-weight: 700;
            color: #10b981;
            background-color: rgba(16, 185, 129, 0.15);
            border-radius: 4px;
            padding: 1px 5px;
        """)
        row_title.addWidget(badge_live)
        row_title.addStretch()
        pod_layout.addLayout(row_title)

        # Distro & Kernel
        self.lbl_distro = QLabel("CachyOS Linux · 6.16.8-cachyos")
        self.lbl_distro.setStyleSheet("font-size: 10px; font-weight: 500; color: rgba(255, 255, 255, 0.50);")
        pod_layout.addWidget(self.lbl_distro)

        # Botón Snapshot Express
        self.btn_snap = QPushButton("📸 Snapshot Rápido")
        self.btn_snap.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_snap.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(99, 102, 241, 0.25), stop:1 rgba(168, 85, 247, 0.25));
                border: 1px solid rgba(99, 102, 241, 0.45);
                border-radius: 6px;
                color: #e0e7ff;
                font-size: 10px;
                font-weight: 700;
                padding: 4px 10px;
                margin-top: 2px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(99, 102, 241, 0.40), stop:1 rgba(168, 85, 247, 0.40));
                border-color: rgba(168, 85, 247, 0.70);
                color: #ffffff;
            }
        """)
        pod_layout.addWidget(self.btn_snap)

        main_layout.addWidget(pod_op)

    def update_telemetry(self, data: dict):
        """Actualiza todos los instrumentos del HUD con telemetría viva."""
        if not data:
            return

        # 1. CPU
        cpu_pct = data.get("cpu_pct", 0)
        cpu_temp = data.get("cpu_temp", 40)
        cpu_ghz = data.get("cpu_ghz", 4.0)
        cpu_model = data.get("cpu_model", "Intel Core")
        self.inst_cpu.set_metric(
            value=f"{cpu_pct} %",
            subtext=f"{cpu_temp}°C · {cpu_ghz} GHz · {cpu_model}",
            bar_pct=cpu_pct
        )

        # 2. RAM
        ram_used = data.get("ram_used_gb", 0.0)
        ram_total = data.get("ram_total_gb", 31.2)
        ram_pct = data.get("ram_pct", 0)
        self.inst_ram.set_metric(
            value=f"{ram_used:.1f} GB",
            subtext=f"{ram_total:.1f} GB Total · DDR5 ({ram_pct}%)",
            bar_pct=ram_pct
        )

        # 3. GPU
        gpu_pct = data.get("gpu_pct", 0)
        gpu_temp = data.get("gpu_temp", 45)
        vram_used = data.get("gpu_vram_used_gb", 0.0)
        vram_total = data.get("gpu_vram_total_gb", 12.0)
        gpu_model = data.get("gpu_model", "RTX GPU")
        vram_pct = int((vram_used / vram_total) * 100) if vram_total > 0 else 0
        self.inst_gpu.set_metric(
            value=f"{vram_used:.1f} GB",
            subtext=f"{gpu_model} · {gpu_temp}°C ({gpu_pct}%)",
            bar_pct=vram_pct
        )

        # 4. ALMACENAMIENTO (Btrfs Root)
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

        # 5. ENLACE DE RED & LATENCIA
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

        # 6. POD OPERADOR
        operator = data.get("operator_name", "SILVYNTH")
        self.lbl_op.setText(operator)
        distro = data.get("distro_name", "CachyOS Linux")
        kernel = data.get("kernel_version", "")
        if kernel:
            self.lbl_distro.setText(f"{distro} · {kernel}")
