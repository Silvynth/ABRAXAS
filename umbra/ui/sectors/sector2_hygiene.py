#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS 2.0 | UMBRA - SECTOR 02: HIGIENIZACIÓN & ALMACENAMIENTO
#  Estándar Estético: Haute Horlogerie / Glass Obsidiana Monocromático
# =====================================================================

import os
import subprocess
import json
import shutil
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
    QPushButton, QScrollArea, QSizePolicy, QToolTip
)
from PySide6.QtCore import Qt, Signal, QRectF, QThread
from PySide6.QtGui import QPainter, QColor, QPen, QLinearGradient, QCursor, QPainterPath

from core.theme import MONOCHROME_PALETTE as P, STORAGE_PALETTE
from core.process import run_command


class SegmentedStorageBar(QWidget):
    """
    Barra segmentada de precisión arquitectónica (Haute Horlogerie).
    Canal fresado con filamentos de titanio y platino de alto contraste.
    Al hacer clic en un segmento:
      - El bloque enfocado se eleva a brillo puro y recibe un marco de zafiro polar.
      - Todos los demás bloques se atenúan a carbón mate translúcido.
    """
    segment_selected = Signal(object)

    def __init__(self, segments: list[dict], total_bytes: int, parent=None):
        super().__init__(parent)
        self.segments = segments
        self.total_bytes = max(1, total_bytes)
        self.selected_index: int | None = None
        self.hover_index: int | None = None
        self._rects: list[QRectF] = []

        self.setFixedHeight(18)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_data(self, segments: list[dict], total_bytes: int):
        self.segments = segments
        self.total_bytes = max(1, total_bytes)
        self.selected_index = None
        self.hover_index = None
        self.update()

    def select_segment_by_index(self, index: int | None):
        if index is None or index == self.selected_index:
            self.selected_index = None
        else:
            if 0 <= index < len(self.segments):
                self.selected_index = index
            else:
                self.selected_index = None

        selected_seg = self.segments[self.selected_index] if self.selected_index is not None else None
        self.segment_selected.emit(selected_seg)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        radius = 4.0

        # 1. Canal base fresado (fondo ranurado de reloj de precisión)
        base_path = QPainterPath()
        base_path.addRoundedRect(QRectF(0, 0, w, h), radius, radius)
        painter.fillPath(base_path, QColor(P["BG_INPUT"]))

        if not self.segments:
            return

        self._rects = []
        cur_x = 0.0
        total_segs = len(self.segments)
        gap = 1.5
        available_w = max(1.0, w - ((total_segs - 1) * gap))

        for i, seg in enumerate(self.segments):
            ratio = seg.get("size_bytes", 0) / self.total_bytes
            seg_w = max(4.0, ratio * available_w)
            if i == total_segs - 1:
                seg_w = max(4.0, w - cur_x)
            r = QRectF(cur_x, 0, seg_w, h)
            self._rects.append(r)
            cur_x += seg_w + gap

        # 2. Renderizado de precisión con micro-gradientes monocromáticos
        painter.save()
        painter.setClipPath(base_path)

        for i, (seg, rect) in enumerate(zip(self.segments, self._rects)):
            raw_c = seg.get("color", QColor("#666666"))
            base_color = QColor(raw_c) if not isinstance(raw_c, QColor) else raw_c
            is_free = seg.get("is_free", False)

            # Gradiente vertical de titanio pulido (luz superior -> sombra base)
            grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())

            if self.selected_index is not None:
                if i == self.selected_index:
                    # Enfoque puro: Blanco polar / Titanio con luz de zafiro
                    c_top = QColor(min(255, base_color.red() + 30), min(255, base_color.green() + 30), min(255, base_color.blue() + 30), 255)
                    c_bot = QColor(base_color.red(), base_color.green(), base_color.blue(), 255)
                else:
                    # Atenuación extrema a carbón translúcido
                    alpha = 18 if is_free else 35
                    c_top = QColor(255, 255, 255, alpha)
                    c_bot = QColor(100, 100, 100, alpha)
            else:
                if is_free:
                    # Espacio libre: Carbón mate técnico con borde de respiración
                    c_top = QColor(P["BG_SURFACE_HOVER"])
                    c_bot = QColor(P["BG_SURFACE"])
                else:
                    # Reposo: Titanio natural calibrado
                    c_top = QColor(min(255, base_color.red() + 20), min(255, base_color.green() + 20), min(255, base_color.blue() + 20), 235)
                    c_bot = QColor(base_color.red(), base_color.green(), base_color.blue(), 215)

            grad.setColorAt(0.0, c_top)
            grad.setColorAt(1.0, c_bot)
            painter.fillRect(rect, grad)

            # Micro-filamento de luz superior (0.5px) para dar aspecto de bisel de reloj
            if (self.selected_index is None and not is_free) or (i == self.selected_index):
                painter.setPen(QPen(QColor(255, 255, 255, 90 if i != self.selected_index else 180), 1))
                painter.drawLine(rect.topLeft() + QRectF(0, 0.5, 0, 0).topLeft(), rect.topRight() + QRectF(0, 0.5, 0, 0).topRight())

            # Borde de zafiro para el segmento enfocado
            if i == self.selected_index:
                painter.setPen(QPen(QColor(P["BORDER_STRONG"]), 1.5))
                painter.drawRect(rect.adjusted(0.75, 0.75, -0.75, -0.75))
            elif i == self.hover_index and self.selected_index is None:
                painter.setPen(QPen(QColor(255, 255, 255, 80), 1))
                painter.drawRect(rect.adjusted(0.5, 0.5, -0.5, -0.5))

        painter.restore()

        # Marco exterior del canal
        painter.setPen(QPen(QColor(P["BORDER_SUBTLE"]), 1))
        painter.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), radius, radius)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.position()
            clicked_idx = None
            for i, r in enumerate(self._rects):
                if r.contains(pos):
                    clicked_idx = i
                    break
            self.select_segment_by_index(clicked_idx)

    def mouseMoveEvent(self, event):
        pos = event.position()
        found_idx = None
        for i, r in enumerate(self._rects):
            if r.contains(pos):
                found_idx = i
                break

        if found_idx != self.hover_index:
            self.hover_index = found_idx
            self.update()

        if found_idx is not None and found_idx < len(self.segments):
            seg = self.segments[found_idx]
            self.setCursor(QCursor(Qt.PointingHandCursor))
            pct = (seg.get("size_bytes", 0) / self.total_bytes) * 100
            QToolTip.showText(
                event.globalPosition().toPoint(),
                f"<b>{seg.get('label')}</b><br>{seg.get('size_str')} ({pct:.1f}% del total)",
                self
            )
        else:
            self.setCursor(QCursor(Qt.ArrowCursor))
            QToolTip.hideText()

    def leaveEvent(self, event):
        self.hover_index = None
        self.update()


class StorageInspectorBox(QFrame):
    """
    Apertura táctica de inspección (Complicación de Relojería).
    Estructurada en columnas limpias: [Calibre / Cifra] [Identidad / Ruta] [Acción Directa].
    """
    action_requested = Signal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_seg = None
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {P["BG_HIGHLIGHT"]};
                border: 1px solid {P["BORDER_SUBTLE"]};
                border-radius: 6px;
            }}
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(16)

        # Micro-indicador vertical de cuarzo
        self.indicator_bar = QFrame()
        self.indicator_bar.setFixedWidth(3)
        self.indicator_bar.setFixedHeight(30)
        self.indicator_bar.setStyleSheet(f"background-color: {P['BORDER_MEDIUM']}; border-radius: 1px;")
        layout.addWidget(self.indicator_bar)

        # Columna 1: Cifra / Métrica destacada
        v_metric = QVBoxLayout()
        v_metric.setSpacing(1)
        self.lbl_tag = QLabel("ESTADO DEL CALIBRE")
        self.lbl_tag.setStyleSheet(f"color: {P['TEXT_MICRO']}; font-size: 8.5px; font-weight: 700; letter-spacing: 1.2px; font-family: 'JetBrains Mono', monospace;")
        self.lbl_metric = QLabel("AUDITORÍA GLOBAL")
        self.lbl_metric.setStyleSheet(f"color: {P['TEXT_TITLES']}; font-size: 13px; font-weight: 800; font-family: 'JetBrains Mono', monospace;")
        v_metric.addWidget(self.lbl_tag)
        v_metric.addWidget(self.lbl_metric)
        layout.addLayout(v_metric)

        # Separador vertical fino
        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setFixedHeight(26)
        sep.setStyleSheet(f"background-color: {P['BORDER_SUBTLE']};")
        layout.addWidget(sep)

        # Columna 2: Identidad & Ubicación
        v_desc = QVBoxLayout()
        v_desc.setSpacing(1)
        self.lbl_cat = QLabel("Haz clic en cualquier segmento de la barra para aislar y auditar su masa de datos.")
        self.lbl_cat.setStyleSheet(f"color: {P['TEXT_MUTED']}; font-size: 11px;")
        self.lbl_path = QLabel("")
        self.lbl_path.setStyleSheet(f"color: {P['TEXT_MICRO']}; font-size: 10px; font-family: 'JetBrains Mono', monospace;")
        self.lbl_path.setVisible(False)
        v_desc.addWidget(self.lbl_cat)
        v_desc.addWidget(self.lbl_path)
        layout.addLayout(v_desc, 1)

        # Columna 3: Botón de Acción Táctica
        self.btn_action = QPushButton("📂 Abrir Carpeta")
        self.btn_action.setProperty("class", "cyber_btn_compact")
        self.btn_action.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_action.setVisible(False)
        self.btn_action.clicked.connect(self._on_action_clicked)
        layout.addWidget(self.btn_action)

    def _on_action_clicked(self):
        if not self.current_seg:
            return
        action_type = self.current_seg.get("action_type", "open_folder")
        if action_type == "open_folder":
            path = self.current_seg.get("path", "")
            if path and os.path.exists(path):
                self.action_requested.emit("open_folder", {"path": path})
        elif action_type == "mount_dev":
            dev = self.current_seg.get("dev", "")
            if dev:
                self.action_requested.emit("mount_dev", {"device": dev})

    def set_segment(self, seg: dict | None, total_bytes: int):
        self.current_seg = seg
        if seg is None:
            self.indicator_bar.setStyleSheet(f"background-color: {P['BORDER_MEDIUM']}; border-radius: 1px;")
            self.lbl_tag.setText("ESTADO DEL CALIBRE")
            self.lbl_metric.setText("AUDITORÍA GLOBAL")
            self.lbl_cat.setText("Haz clic en cualquier segmento de la barra para aislar y auditar su masa de datos.")
            self.lbl_path.setVisible(False)
            self.btn_action.setVisible(False)
            return

        raw_c = seg.get("color", QColor("#ffffff"))
        color = QColor(raw_c) if not isinstance(raw_c, QColor) else raw_c
        c_hex = color.name()

        self.indicator_bar.setStyleSheet(f"background-color: {c_hex}; border-radius: 1px;")

        pct = (seg.get("size_bytes", 0) / max(1, total_bytes)) * 100
        label = seg.get("label", "Desconocido")
        size_str = seg.get("size_str", "")
        category = seg.get("category", "Archivo / Directorio Masivo")
        path = seg.get("path", "")
        dev = seg.get("dev", "")
        is_mounted = seg.get("is_mounted", True)

        self.lbl_tag.setText(f"{category.upper()} // {pct:.1f}%")
        self.lbl_metric.setText(f"{label} · {size_str}")

        if not is_mounted and dev:
            self.lbl_cat.setText(f"Dispositivo extraíble conectado ({dev})")
            self.lbl_path.setText(f"Estado: Listo para montar vía udisksctl")
            self.lbl_path.setVisible(True)
            self.btn_action.setText("⚡ Montar Dispositivo")
            self.btn_action.setVisible(True)
            seg["action_type"] = "mount_dev"
        elif path and os.path.exists(path):
            self.lbl_cat.setText(f"Ubicación en sistema de archivos:")
            self.lbl_path.setText(path)
            self.lbl_path.setVisible(True)
            self.btn_action.setText("📂 Abrir Carpeta")
            self.btn_action.setVisible(True)
            seg["action_type"] = "open_folder"
        else:
            self.lbl_cat.setText("Volumen del sistema / Subvolumen Btrfs")
            self.lbl_path.setVisible(False)
            self.btn_action.setVisible(False)


class DiskCard(QFrame):
    """
    Tarjeta de Disco Físico inspirada en alta relojería monocromática.
    """
    action_requested = Signal(str, dict)

    def __init__(self, disk_id: str, model_name: str, total_bytes: int, used_bytes: int, 
                 segments: list[dict], badge_text: str = "", disk_type: str = "nvme", parent=None):
        super().__init__(parent)
        self.disk_id = disk_id
        self.total_bytes = total_bytes
        self.used_bytes = used_bytes
        self.segments = segments
        self.badge_text = badge_text
        self.disk_type = disk_type
        self.init_ui(model_name)

    def init_ui(self, model_name: str):
        self.setProperty("class", "sector_card")
        self.setStyleSheet(f"""
            QFrame.sector_card {{
                background-color: {P["BG_SURFACE"]};
                border: 1px solid {P["BORDER_SUBTLE"]};
                border-radius: 8px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)

        # 1. Cabecera técnica refinada
        h_box = QHBoxLayout()
        h_box.setSpacing(10)

        # Micro-tag superior
        v_title = QVBoxLayout()
        v_title.setSpacing(1)

        bus_label = "NVME GEN4 // SISTEMA" if self.disk_type == "nvme" else ("USB EXTRAÍBLE" if self.disk_type == "usb" else "SATA BUS // SECUNDARIO")
        lbl_micro = QLabel(f"◈ DISCO // {self.disk_id.upper()}  ·  {bus_label}")
        lbl_micro.setStyleSheet(f"color: {P['TEXT_MICRO']}; font-size: 8.5px; font-weight: 700; letter-spacing: 1.2px; font-family: 'JetBrains Mono', monospace;")

        lbl_name = QLabel(model_name)
        lbl_name.setStyleSheet(f"color: {P['TEXT_TITLES']}; font-weight: 700; font-size: 13px; font-family: 'JetBrains Mono', monospace;")

        v_title.addWidget(lbl_micro)
        v_title.addWidget(lbl_name)
        h_box.addLayout(v_title)

        if self.badge_text:
            badge = QLabel(self.badge_text)
            badge.setStyleSheet(f"color: {P['TEXT_BODY']}; font-size: 9px; font-weight: 700; background: {P['BG_HIGHLIGHT']}; border: 1px solid {P['BORDER_MEDIUM']}; padding: 2px 7px; border-radius: 4px; font-family: 'JetBrains Mono', monospace;")
            h_box.addWidget(badge)

        h_box.addStretch()

        # Telemetría de capacidad compacta
        free_bytes = max(0, self.total_bytes - self.used_bytes)
        pct_used = (self.used_bytes / max(1, self.total_bytes)) * 100
        lbl_stats = QLabel(f"<span style='color:{P['TEXT_TITLES']}; font-weight:800;'>{_fmt_size(self.used_bytes)}</span> <span style='color:{P['TEXT_MICRO']};'>({pct_used:.1f}%)</span>  ·  <span style='color:{P['TEXT_MUTED']};'>{_fmt_size(free_bytes)} Libre</span>")
        lbl_stats.setStyleSheet("font-size: 11px; font-family: 'JetBrains Mono', monospace;")
        h_box.addWidget(lbl_stats)

        layout.addLayout(h_box)

        # 2. Barra de Almacenamiento Segmentada
        self.bar = SegmentedStorageBar(self.segments, self.total_bytes, self)
        layout.addWidget(self.bar)

        # 3. Micro-Leyenda Arquitectónica (Swatches finos en lugar de botones pesados)
        pills_layout = QHBoxLayout()
        pills_layout.setSpacing(6)
        self.pill_buttons = []

        for i, seg in enumerate(self.segments):
            raw_c = seg.get("color", QColor("#888888"))
            color = QColor(raw_c) if not isinstance(raw_c, QColor) else raw_c
            c_hex = color.name()
            label = seg.get("label", "")
            size_str = seg.get("size_str", "")

            btn_pill = QPushButton(f"■ {label}  {size_str}")
            btn_pill.setCursor(QCursor(Qt.PointingHandCursor))
            btn_pill.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: 1px solid {P["BORDER_SUBTLE"]};
                    border-radius: 3px;
                    color: {c_hex};
                    font-size: 9.5px;
                    font-family: 'JetBrains Mono', monospace;
                    font-weight: 600;
                    padding: 2px 7px;
                }}
                QPushButton:hover {{
                    border-color: {P["BORDER_STRONG"]};
                    background: {P["BG_HIGHLIGHT"]};
                    color: {P["TEXT_TITLES"]};
                }}
            """)
            btn_pill.clicked.connect(lambda _, idx=i: self.bar.select_segment_by_index(idx))
            pills_layout.addWidget(btn_pill)
            self.pill_buttons.append(btn_pill)

        pills_layout.addStretch()
        layout.addLayout(pills_layout)

        # 4. Apertura Táctica de Inspección
        self.inspector = StorageInspectorBox(self)
        self.inspector.action_requested.connect(self.action_requested.emit)
        self.bar.segment_selected.connect(self._on_segment_selected)
        layout.addWidget(self.inspector)

    def _on_segment_selected(self, seg: dict | None):
        self.inspector.set_segment(seg, self.total_bytes)
        sel_idx = self.bar.selected_index
        for i, btn in enumerate(self.pill_buttons):
            seg_i = self.segments[i]
            raw_c = seg_i.get("color", QColor(P["TEXT_TITLES"]))
            color = QColor(raw_c) if not isinstance(raw_c, QColor) else raw_c
            c_hex = color.name()

            if sel_idx is not None:
                if i == sel_idx:
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background: {P["ACCENT_PILL"]};
                            border: 1px solid {P["BORDER_STRONG"]};
                            border-radius: 3px;
                            color: {P["TEXT_TITLES"]};
                            font-size: 9.5px;
                            font-family: 'JetBrains Mono', monospace;
                            font-weight: 800;
                            padding: 2px 7px;
                        }}
                    """)
                else:
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background: transparent;
                            border: 1px solid transparent;
                            color: rgba(255, 255, 255, 0.20);
                            font-size: 9.5px;
                            font-family: 'JetBrains Mono', monospace;
                            font-weight: 500;
                            padding: 2px 7px;
                        }}
                    """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        border: 1px solid {P["BORDER_SUBTLE"]};
                        border-radius: 3px;
                        color: {c_hex};
                        font-size: 9.5px;
                        font-family: 'JetBrains Mono', monospace;
                        font-weight: 600;
                        padding: 2px 7px;
                    }}
                    QPushButton:hover {{
                        border-color: {P["BORDER_STRONG"]};
                        background: {P["BG_HIGHLIGHT"]};
                        color: {P["TEXT_TITLES"]};
                    }}
                """)


class DiskScanWorker(QThread):
    """Worker asíncrono para escaneo de topología física de discos sin bloquear la UI."""
    disks_ready = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        try:
            disks = Sector2HygieneView._gather_all_disks_static(lambda: self._running)
            if self._running:
                self.disks_ready.emit(disks)
        except Exception:
            pass


class Sector2HygieneView(QWidget):
    """
    SECTOR 02: HIGIENIZACIÓN & ALMACENAMIENTO DE PRECISIÓN
    """
    log_emitted = Signal(str)
    action_requested = Signal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scan_worker = None
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(12)

        # 1. Cabecera Táctica del Sector
        top_card = QFrame()
        top_card.setProperty("class", "sector_card")
        top_card.setStyleSheet(f"""
            QFrame {{
                background-color: {P["BG_SURFACE"]};
                border: 1px solid {P["BORDER_SUBTLE"]};
                border-radius: 8px;
                padding: 10px 14px;
            }}
        """)
        top_l = QHBoxLayout(top_card)
        top_l.setContentsMargins(10, 8, 10, 8)
        top_l.setSpacing(12)

        v_head = QVBoxLayout()
        v_head.setSpacing(2)
        tag = QLabel("DOMINIO UMBRA // SECTOR 02")
        tag.setProperty("class", "sector_micro_tag")
        title = QLabel("Higienización de Almacenamiento & Auditoría de Masa Crítica")
        title.setProperty("class", "sector_title")
        desc = QLabel("Inspección continua de bloques físicos (NVMe, SATA y USB). Selecciona cualquier segmento para aislar su volumen.")
        desc.setStyleSheet(f"color: {P['TEXT_MUTED']}; font-size: 11px;")
        v_head.addWidget(tag)
        v_head.addWidget(title)
        v_head.addWidget(desc)
        top_l.addLayout(v_head, 1)

        # Acciones de Auditoría
        r_actions = QHBoxLayout()
        r_actions.setSpacing(6)

        btn_refresh = QPushButton("🔄 Re-auditar Almacenamiento")
        btn_refresh.setProperty("class", "cyber_btn_compact")
        btn_refresh.setCursor(QCursor(Qt.PointingHandCursor))
        btn_refresh.clicked.connect(self.refresh_disks)

        r_actions.addWidget(btn_refresh)
        top_l.addLayout(r_actions)

        main_layout.addWidget(top_card)

        # 2. Scroll Area con las tarjetas de los discos
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.w_disks = QWidget()
        self.l_disks = QVBoxLayout(self.w_disks)
        self.l_disks.setContentsMargins(0, 0, 4, 0)
        self.l_disks.setSpacing(12)
        self.l_disks.addStretch()

        scroll.setWidget(self.w_disks)
        main_layout.addWidget(scroll, 1)

        self.refresh_disks()

    def refresh_disks(self):
        """Escanea todos los discos del sistema y puebla la UI de forma asíncrona."""
        if self.scan_worker and self.scan_worker.isRunning():
            return

        self.log_emitted.emit("🔍 Escaneando topología física de almacenamiento...")
        self.scan_worker = DiskScanWorker(self)
        self.scan_worker.disks_ready.connect(self._on_disks_scanned)
        self.scan_worker.start()

    def _on_disks_scanned(self, disks_data: list[dict]):
        while self.l_disks.count() > 1:
            item = self.l_disks.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for d in disks_data:
            card = DiskCard(
                disk_id=d["disk_id"],
                model_name=d["model_name"],
                total_bytes=d["total_bytes"],
                used_bytes=d["used_bytes"],
                segments=d["segments"],
                badge_text=d.get("badge", ""),
                disk_type=d.get("disk_type", "sata"),
                parent=self
            )
            card.action_requested.connect(self._handle_action)
            self.l_disks.insertWidget(self.l_disks.count() - 1, card)

        self.log_emitted.emit(f"✔ Auditoría completada: {len(disks_data)} unidades físicas sincronizadas.")

    def teardown(self):
        """Detiene de forma limpia el worker de escaneo de discos si está activo."""
        if self.scan_worker and self.scan_worker.isRunning():
            self.scan_worker.stop()
            if not self.scan_worker.wait(150):
                self.scan_worker.terminate()
                self.scan_worker.wait(100)

    def _gather_all_disks(self) -> list[dict]:
        return self._gather_all_disks_static()

    @staticmethod
    def _gather_all_disks_static(is_running_cb=None) -> list[dict]:
        """Detecta dinámicamente todos los discos y los ordena: Principal del SO primero, luego de mayor a menor."""
        try:
            res = run_command(["lsblk", "-J", "-b", "-o", "NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS,MODEL,TRAN,HOTPLUG,RM"])
            if res.returncode != 0 or not res.stdout:
                return Sector2HygieneView._fallback_nvme_data_static()
            
            data = json.loads(res.stdout)
            devices = data.get("blockdevices", [])
        except Exception:
            return Sector2HygieneView._fallback_nvme_data_static()

        primary_disks = []
        secondary_disks = []

        for dev in devices:
            d_type = dev.get("type", "")
            d_name = dev.get("name", "")
            if d_type != "disk" or d_name.startswith(("zram", "loop")):
                continue

            d_size = dev.get("size", 0)
            d_model = dev.get("model", "Almacenamiento Físico")
            d_tran = (dev.get("tran") or "").lower()
            is_hotplug = dev.get("hotplug") or dev.get("rm") or False

            children = dev.get("children", [])
            has_root = any("/" in (p.get("mountpoints") or []) for p in children)

            if has_root:
                disk_category = "nvme" if ("nvme" in d_name or d_tran == "nvme") else "sata"
                badge = "SISTEMA OPERATIVO PRINCIPAL"
            elif d_tran == "usb" or is_hotplug:
                disk_category = "usb"
                badge = "USB REMOVIBLE"
            elif d_tran == "nvme" or "nvme" in d_name:
                disk_category = "nvme"
                badge = "NVMe SECUNDARIO"
            else:
                disk_category = "sata"
                badge = "SATA STORAGE"

            segments, used_accum = Sector2HygieneView._build_disk_segments_static(d_name, d_size, children, disk_category, is_running_cb)

            disk_info = {
                "disk_id": d_name,
                "model_name": f"{d_model} ({_fmt_size(d_size)})",
                "total_bytes": d_size,
                "used_bytes": used_accum,
                "segments": segments,
                "badge": badge,
                "disk_type": disk_category,
                "is_primary": has_root
            }

            if has_root:
                primary_disks.append(disk_info)
            else:
                secondary_disks.append(disk_info)

        # Regla de ordenamiento: primario siempre al inicio, el resto por tamaño descendente
        secondary_disks.sort(key=lambda x: x["total_bytes"], reverse=True)
        return primary_disks + secondary_disks

    def _build_disk_segments(self, disk_name: str, total_bytes: int, children: list[dict], disk_type: str) -> tuple[list[dict], int]:
        return Sector2HygieneView._build_disk_segments_static(disk_name, total_bytes, children, disk_type)

    @staticmethod
    def _build_disk_segments_static(disk_name: str, total_bytes: int, children: list[dict], disk_type: str, is_running_cb=None) -> tuple[list[dict], int]:
        segments = []
        color_idx = 0
        used_accum = 0

        has_root = any("/" in (p.get("mountpoints") or []) for p in children)

        if has_root:
            root_usage = shutil.disk_usage("/")
            used_accum = root_usage.used

            steam_common = os.path.expanduser("~/.local/share/Steam/steamapps/common")
            total_games_size = 0
            if os.path.exists(steam_common):
                try:
                    game_entries = []
                    for entry in os.scandir(steam_common):
                        if entry.is_dir() and not entry.is_symlink():
                            try:
                                res = run_command(["du", "-sb", entry.path])
                                if res.returncode == 0:
                                    b = int(res.stdout.split()[0])
                                    if b >= 1024 * 1024 * 1024:
                                        game_entries.append((entry.name, b, entry.path))
                                        total_games_size += b
                            except Exception:
                                pass

                    game_entries.sort(key=lambda x: x[1], reverse=True)
                    for name, sz, pth in game_entries[:4]:
                        segments.append({
                            "id": f"game_{name}",
                            "label": name,
                            "size_bytes": sz,
                            "size_str": _fmt_size(sz),
                            "color": QColor(STORAGE_PALETTE[color_idx % len(STORAGE_PALETTE)]),
                            "path": pth,
                            "category": "Juego Steam (Masa Crítica)"
                        })
                        color_idx += 1

                    other_games_size = sum(x[1] for x in game_entries[4:])
                    if other_games_size > 0:
                        segments.append({
                            "id": "other_steam",
                            "label": "Otros Juegos Steam",
                            "size_bytes": other_games_size,
                            "size_str": _fmt_size(other_games_size),
                            "color": QColor(STORAGE_PALETTE[color_idx % len(STORAGE_PALETTE)]),
                            "path": steam_common,
                            "category": "Biblioteca Steam (>1 GB c/u)"
                        })
                        color_idx += 1
                except Exception:
                    pass

            pacman_cache = "/var/cache/pacman/pkg"
            if os.path.exists(pacman_cache):
                try:
                    res = run_command(["du", "-sb", pacman_cache])
                    if res.returncode == 0:
                        sz = int(res.stdout.split()[0])
                        segments.append({
                            "id": "pacman_cache",
                            "label": "Caché Pacman",
                            "size_bytes": sz,
                            "size_str": _fmt_size(sz),
                            "color": QColor(STORAGE_PALETTE[color_idx % len(STORAGE_PALETTE)]),
                            "path": pacman_cache,
                            "category": "Caché de Sistema & Paquetes"
                        })
                        color_idx += 1
                except Exception:
                    pass

            user_cache = os.path.expanduser("~/.cache")
            if os.path.exists(user_cache):
                try:
                    res = run_command(["du", "-sb", user_cache])
                    if res.returncode == 0:
                        sz = int(res.stdout.split()[0])
                        segments.append({
                            "id": "user_cache",
                            "label": "Caché de Usuario",
                            "size_bytes": sz,
                            "size_str": _fmt_size(sz),
                            "color": QColor(STORAGE_PALETTE[color_idx % len(STORAGE_PALETTE)]),
                            "path": user_cache,
                            "category": "Cachés de Navegadores y Apps"
                        })
                        color_idx += 1
                except Exception:
                    pass

            vault_p = os.path.expanduser("~/Vault")
            if os.path.exists(vault_p):
                try:
                    res = run_command(["du", "-sb", vault_p])
                    if res.returncode == 0:
                        sz = int(res.stdout.split()[0])
                        if sz > 50 * 1024 * 1024:
                            segments.append({
                                "id": "vault",
                                "label": "Bóveda Obsidian",
                                "size_bytes": sz,
                                "size_str": _fmt_size(sz),
                                "color": QColor(STORAGE_PALETTE[color_idx % len(STORAGE_PALETTE)]),
                                "path": vault_p,
                                "category": "Segundo Cerebro Obsidian"
                            })
                            color_idx += 1
                except Exception:
                    pass

            accounted = sum(s["size_bytes"] for s in segments)
            base_sz = max(10 * 1024 * 1024 * 1024, used_accum - accounted)
            segments.append({
                "id": "system_base",
                "label": "Sistema Raíz & Binarios",
                "size_bytes": base_sz,
                "size_str": _fmt_size(base_sz),
                "color": QColor(STORAGE_PALETTE[color_idx % len(STORAGE_PALETTE)]),
                "path": "/",
                "category": "Archivos CachyOS (/usr, /etc)"
            })
            color_idx += 1

            free_sz = max(0, total_bytes - used_accum)
            segments.append({
                "id": "free_space",
                "label": "Espacio Disponible",
                "size_bytes": free_sz,
                "size_str": _fmt_size(free_sz),
                "color": QColor(P["BG_SURFACE_HOVER"]),
                "path": "",
                "category": "Almacenamiento Libre en Btrfs",
                "is_free": True
            })

            return segments, used_accum

        for part in children:
            p_name = part.get("name", "")
            p_size = part.get("size", 0)
            p_fs = part.get("fstype") or "RAW"
            mounts = [m for m in (part.get("mountpoints") or []) if m]

            if mounts:
                m_path = mounts[0]
                try:
                    u = shutil.disk_usage(m_path)
                    part_used = u.used
                    used_accum += part_used

                    segments.append({
                        "id": f"part_{p_name}",
                        "label": f"{p_name} ({m_path})",
                        "size_bytes": part_used,
                        "size_str": _fmt_size(part_used),
                        "color": QColor(STORAGE_PALETTE[color_idx % len(STORAGE_PALETTE)]),
                        "path": m_path,
                        "category": f"Partición Montada ({p_fs})",
                        "is_mounted": True
                    })
                    color_idx += 1
                except Exception:
                    used_accum += p_size
                    segments.append({
                        "id": f"part_{p_name}",
                        "label": f"{p_name} [{p_fs}]",
                        "size_bytes": p_size,
                        "size_str": _fmt_size(p_size),
                        "color": QColor(STORAGE_PALETTE[color_idx % len(STORAGE_PALETTE)]),
                        "path": "",
                        "category": f"Partición {p_fs}",
                        "is_mounted": True
                    })
                    color_idx += 1
            else:
                used_accum += p_size
                segments.append({
                    "id": f"part_{p_name}",
                    "label": f"{p_name} [{p_fs}]",
                    "size_bytes": p_size,
                    "size_str": _fmt_size(p_size),
                    "color": QColor(STORAGE_PALETTE[color_idx % len(STORAGE_PALETTE)]),
                    "path": "",
                    "dev": f"/dev/{p_name}",
                    "category": f"Partición {p_fs} (Sin Montar)",
                    "is_mounted": False
                })
                color_idx += 1

        free_sda = max(0, total_bytes - used_accum)
        if free_sda > 1024 * 1024 * 1024:
            segments.append({
                "id": f"free_{disk_name}",
                "label": "Espacio Disponible",
                "size_bytes": free_sda,
                "size_str": _fmt_size(free_sda),
                "color": QColor(P["BG_SURFACE_HOVER"]),
                "path": "",
                "category": "Espacio Libre / Sin Asignar",
                "is_free": True
            })

        return segments, used_accum

    def _fallback_nvme_data(self) -> list[dict]:
        return Sector2HygieneView._fallback_nvme_data_static()

    @staticmethod
    def _fallback_nvme_data_static() -> list[dict]:
        root_usage = shutil.disk_usage("/")
        return [{
            "disk_id": "nvme0n1",
            "model_name": f"NVMe SSD ({_fmt_size(root_usage.total)})",
            "total_bytes": root_usage.total,
            "used_bytes": root_usage.used,
            "segments": [
                {
                    "id": "used",
                    "label": "Espacio Usado",
                    "size_bytes": root_usage.used,
                    "size_str": _fmt_size(root_usage.used),
                    "color": QColor(STORAGE_PALETTE[0]),
                    "path": "/",
                    "category": "Sistema & Datos"
                },
                {
                    "id": "free",
                    "label": "Espacio Disponible",
                    "size_bytes": root_usage.free,
                    "size_str": _fmt_size(root_usage.free),
                    "color": QColor(P["BG_SURFACE_HOVER"]),
                    "path": "",
                    "category": "Libre",
                    "is_free": True
                }
            ],
            "badge": "SISTEMA OPERATIVO PRINCIPAL",
            "disk_type": "nvme"
        }]

    def _handle_action(self, action: str, data: dict):
        if action == "open_folder":
            path = data.get("path", "")
            self.log_emitted.emit(f"📂 Abriendo gestor de archivos en: {path}")
            try:
                subprocess.Popen(["xdg-open", path])
            except Exception as e:
                self.log_emitted.emit(f"⚠ Error al abrir carpeta: {e}")
        elif action == "mount_dev":
            device = data.get("device", "")
            self.log_emitted.emit(f"🔌 Montando dispositivo {device} vía udisksctl...")
            try:
                res = run_command(["udisksctl", "mount", "-b", device])
                if res.returncode == 0:
                    self.log_emitted.emit(f"✔ Dispositivo montado: {res.stdout.strip()}")
                else:
                    self.log_emitted.emit(f"ℹ Respuesta de montaje: {res.stdout.strip() or res.stderr.strip()}")
            except Exception as e:
                self.log_emitted.emit(f"⚠ Error al montar: {e}")
            self.refresh_disks()

        self.action_requested.emit(action, data)


def _fmt_size(b: int) -> str:
    """Formatea bytes en formato legible."""
    if b >= 1024 * 1024 * 1024 * 1024:
        return f"{b / (1024**4):.2f} TB"
    elif b >= 1024 * 1024 * 1024:
        return f"{b / (1024**3):.1f} GB"
    elif b >= 1024 * 1024:
        return f"{b / (1024**2):.1f} MB"
    elif b >= 1024:
        return f"{b / 1024:.1f} KB"
    return f"{b} B"
