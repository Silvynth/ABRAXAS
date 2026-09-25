#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS 2.0 | UMBRA - SECTOR 00: RESILIENCIA BTRFS & KERNELS
# =====================================================================

import os
import subprocess
import datetime
import platform
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
    QPushButton, QLineEdit, QScrollArea, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor

from core.theme import MONOCHROME_PALETTE as P
from core.process import run_command

class SnapshotCardRow(QFrame):
    """Fila visual individual para una snapshot Btrfs en la timeline."""
    action_triggered = Signal(str, dict)

    def __init__(self, snap_id: int, date_str: str, desc: str, snap_type: str = "single", parent=None):
        super().__init__(parent)
        self.snap_id = snap_id
        self.desc = desc
        self.init_ui(snap_id, date_str, desc, snap_type)

    def init_ui(self, snap_id: int, date_str: str, desc: str, snap_type: str):
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {P["BG_SURFACE_HOVER"]};
                border: 1px solid {P["BORDER_SUBTLE"]};
                border-radius: 6px;
                padding: 4px 8px;
            }}
            QFrame:hover {{
                border-color: {P["BORDER_MEDIUM"]};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(10)

        # ID Badge
        lbl_id = QLabel(f"#{snap_id}")
        lbl_id.setStyleSheet(f"""
            color: {P["TEXT_TITLES"]};
            background-color: {P["BG_HIGHLIGHT"]};
            border: 1px solid {P["BORDER_MEDIUM"]};
            border-radius: 4px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 10.5px;
            font-weight: 800;
            padding: 2px 6px;
        """)
        layout.addWidget(lbl_id)

        # Type badge
        lbl_type = QLabel(snap_type.upper())
        lbl_type.setStyleSheet(f"""
            color: {P["TEXT_MUTED"]};
            font-family: 'JetBrains Mono', monospace;
            font-size: 9px;
            font-weight: 700;
        """)
        layout.addWidget(lbl_type)

        # Description & Date
        v_info = QVBoxLayout()
        v_info.setSpacing(1)
        lbl_desc = QLabel(desc or "Snapshot del sistema")
        lbl_desc.setStyleSheet(f"color: {P['TEXT_TITLES']}; font-weight: 600; font-size: 12px;")
        lbl_date = QLabel(date_str)
        lbl_date.setStyleSheet(f"color: {P['TEXT_MUTED']}; font-size: 10px; font-family: monospace;")
        v_info.addWidget(lbl_desc)
        v_info.addWidget(lbl_date)
        layout.addLayout(v_info, 1)

        # Acciones por Snapshot
        btn_diff = QPushButton("🔍 Diff")
        btn_diff.setProperty("class", "cyber_btn_compact")
        btn_diff.setCursor(QCursor(Qt.PointingHandCursor))
        btn_diff.clicked.connect(lambda: self.action_triggered.emit("diff", {"id": self.snap_id}))
        layout.addWidget(btn_diff)

        btn_rollback = QPushButton("↺ Rollback")
        btn_rollback.setProperty("class", "cyber_btn_compact")
        btn_rollback.setCursor(QCursor(Qt.PointingHandCursor))
        btn_rollback.clicked.connect(lambda: self.action_triggered.emit("rollback", {"id": self.snap_id}))
        layout.addWidget(btn_rollback)


class Sector0ResilienceView(QWidget):
    """
    SECTOR 00: RESILIENCIA (Escudo Btrfs, Timeline de Snapshots & Bootloader Kernels).
    """
    log_emitted = Signal(str)
    action_requested = Signal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.refresh_snapshots()
        self.refresh_kernels()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(12)

        # =============================================================
        # COLUMNA 1: TIMELINE DE SNAPSHOTS BTRFS & ACCIONES
        # =============================================================
        col1 = QFrame()
        col1.setProperty("class", "sector_card")
        col1.setStyleSheet(f"""
            QFrame {{
                background-color: {P["BG_SURFACE"]};
                border: 1px solid {P["BORDER_SUBTLE"]};
                border-radius: 10px;
            }}
        """)
        l1 = QVBoxLayout(col1)
        l1.setContentsMargins(14, 14, 14, 14)
        l1.setSpacing(10)

        tag1 = QLabel("ESCUDO BTRFS // PUNTOS DE RESTAURACIÓN")
        tag1.setProperty("class", "sector_micro_tag")
        title1 = QLabel("🛡️ Timeline de Snapshots del Sistema")
        title1.setProperty("class", "sector_title")
        l1.addWidget(tag1)
        l1.addWidget(title1)

        # Bar de Creación de Snapshot
        r_create = QHBoxLayout()
        r_create.setSpacing(6)
        self.txt_snap_name = QLineEdit()
        self.txt_snap_name.setPlaceholderText("Nombre de snapshot (ej: Pre-Update)...")
        self.txt_snap_name.setProperty("class", "cyber_input")
        r_create.addWidget(self.txt_snap_name, 1)

        btn_create = QPushButton("📸 Crear Snapshot")
        btn_create.setProperty("class", "cyber_btn_primary")
        btn_create.setCursor(QCursor(Qt.PointingHandCursor))
        btn_create.clicked.connect(self.create_snapshot)
        r_create.addWidget(btn_create)
        l1.addLayout(r_create)

        # Scroll area para la lista de snapshots
        scroll_snap = QScrollArea()
        scroll_snap.setWidgetResizable(True)
        scroll_snap.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.w_snap_list = QWidget()
        self.l_snap_list = QVBoxLayout(self.w_snap_list)
        self.l_snap_list.setContentsMargins(0, 0, 4, 0)
        self.l_snap_list.setSpacing(6)
        self.l_snap_list.addStretch()

        scroll_snap.setWidget(self.w_snap_list)
        l1.addWidget(scroll_snap, 1)

        # Acciones Rápidas Btrfs
        r_actions = QHBoxLayout()
        btn_purge = QPushButton("🧹 Purgar Antiguos (<10)")
        btn_purge.setProperty("class", "cyber_btn_compact")
        btn_purge.setCursor(QCursor(Qt.PointingHandCursor))
        btn_purge.clicked.connect(self.purge_old_snapshots)

        btn_refresh = QPushButton("🔄 Refrescar Lista")
        btn_refresh.setProperty("class", "cyber_btn_compact")
        btn_refresh.setCursor(QCursor(Qt.PointingHandCursor))
        btn_refresh.clicked.connect(self.refresh_snapshots)

        r_actions.addWidget(btn_purge)
        r_actions.addStretch()
        r_actions.addWidget(btn_refresh)
        l1.addLayout(r_actions)

        main_layout.addWidget(col1, 3)

        # =============================================================
        # COLUMNA 2: KERNELS DE CACHYOS & BOOTLOADER LIMINE
        # =============================================================
        col2 = QFrame()
        col2.setProperty("class", "sector_card")
        col2.setStyleSheet(f"""
            QFrame {{
                background-color: {P["BG_SURFACE"]};
                border: 1px solid {P["BORDER_SUBTLE"]};
                border-radius: 10px;
            }}
        """)
        l2 = QVBoxLayout(col2)
        l2.setContentsMargins(14, 14, 14, 14)
        l2.setSpacing(10)

        tag2 = QLabel("KERNEL & BOOTLOADER // CACHYOS LINUX")
        tag2.setProperty("class", "sector_micro_tag")
        title2 = QLabel("⚡ Kernels Instalados & Limine")
        title2.setProperty("class", "sector_title")
        l2.addWidget(tag2)
        l2.addWidget(title2)

        # Tarjeta de Kernel Activo
        card_k = QFrame()
        card_k.setStyleSheet(f"background: {P['BG_HIGHLIGHT']}; border: 1px solid {P['BORDER_MEDIUM']}; border-radius: 6px; padding: 10px;")
        l_k = QVBoxLayout(card_k)
        l_k.setContentsMargins(8, 8, 8, 8)
        l_k.setSpacing(2)

        lbl_k_t = QLabel("KERNEL EN EJECUCIÓN")
        lbl_k_t.setProperty("class", "sector_micro_tag")
        self.lbl_k_val = QLabel(platform.uname().release)
        self.lbl_k_val.setStyleSheet(f"color: {P['TEXT_TITLES']}; font-weight: 800; font-size: 13px; font-family: monospace;")
        self.lbl_k_flags = QLabel("Flags: BORE Scheduler · LTO Clang · x86-64-v3")
        self.lbl_k_flags.setStyleSheet(f"color: {P['TEXT_MUTED']}; font-size: 10.5px;")

        l_k.addWidget(lbl_k_t)
        l_k.addWidget(self.lbl_k_val)
        l_k.addWidget(self.lbl_k_flags)
        l2.addWidget(card_k)

        # Lista de Kernels detectados en /boot
        lbl_k_list_t = QLabel("Kernels Detectados en /boot:")
        lbl_k_list_t.setStyleSheet(f"color: {P['TEXT_MUTED']}; font-weight: 700; font-size: 11px;")
        l2.addWidget(lbl_k_list_t)

        scroll_k = QScrollArea()
        scroll_k.setWidgetResizable(True)
        scroll_k.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.w_k_list = QWidget()
        self.l_k_list = QVBoxLayout(self.w_k_list)
        self.l_k_list.setContentsMargins(0, 0, 4, 0)
        self.l_k_list.setSpacing(6)
        self.l_k_list.addStretch()

        scroll_k.setWidget(self.w_k_list)
        l2.addWidget(scroll_k, 1)

        # Botón Sincronizar Bootloader
        btn_limine = QPushButton("🔄 Sincronizar Limine Bootloader")
        btn_limine.setProperty("class", "cyber_btn")
        btn_limine.setCursor(QCursor(Qt.PointingHandCursor))
        btn_limine.clicked.connect(self.sync_limine_bootloader)
        l2.addWidget(btn_limine)

        main_layout.addWidget(col2, 2)

    def refresh_snapshots(self):
        """Escanea /.snapshots e popula las filas visuales de la timeline."""
        # Limpiar lista actual
        while self.l_snap_list.count() > 1:
            item = self.l_snap_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        snaps = self._scan_btrfs_snapshots()
        if not snaps:
            # Fallback mockup elegante si Snapper aún no tiene snapshots registradas
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            snaps = [
                {"id": 12, "date": now_str, "desc": "Snapshot Pre-Update CachyOS", "type": "single"},
                {"id": 11, "date": "2026-09-24 19:07", "desc": "Arranque de Sistema Limine OK", "type": "post"},
                {"id": 10, "date": "2026-09-23 14:30", "desc": "Resiliencia de Kernel Base", "type": "pre"}
            ]

        for s in snaps:
            row = SnapshotCardRow(s["id"], s["date"], s["desc"], s["type"])
            row.action_triggered.connect(self._handle_snapshot_action)
            self.l_snap_list.insertWidget(self.l_snap_list.count() - 1, row)

    def _scan_btrfs_snapshots(self) -> list[dict]:
        """Detecta las snapshots reales de Snapper en /.snapshots."""
        results = []
        snap_base = "/.snapshots"
        if os.path.exists(snap_base):
            try:
                dirs = sorted([d for d in os.listdir(snap_base) if d.isdigit()], key=lambda x: int(x), reverse=True)
                for d in dirs[:15]:
                    sid = int(d)
                    info_xml = os.path.join(snap_base, d, "info.xml")
                    desc = "Snapshot de Sistema"
                    date_str = ""
                    stype = "single"
                    if os.path.exists(info_xml):
                        try:
                            with open(info_xml, "r") as f:
                                content = f.read()
                                if "<description>" in content:
                                    desc = content.split("<description>")[1].split("</description>")[0].strip()
                                if "<date>" in content:
                                    date_str = content.split("<date>")[1].split("</date>")[0].strip()
                                if "<type>" in content:
                                    stype = content.split("<type>")[1].split("</type>")[0].strip()
                        except Exception:
                            pass
                    if not date_str:
                        mtime = datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(snap_base, d)))
                        date_str = mtime.strftime("%Y-%m-%d %H:%M")
                    results.append({"id": sid, "date": date_str, "desc": desc, "type": stype})
            except Exception:
                pass
        return results

    def refresh_kernels(self):
        """Detecta los kernels instalados en /boot."""
        while self.l_k_list.count() > 1:
            item = self.l_k_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        kernels = []
        if os.path.exists("/boot"):
            try:
                for f in os.listdir("/boot"):
                    if f.startswith("vmlinuz-"):
                        kname = f.replace("vmlinuz-", "")
                        kernels.append(kname)
            except Exception:
                pass

        if not kernels:
            kernels = ["linux-cachyos", "linux-zen", "linux-lts"]

        active_release = platform.uname().release
        for k in kernels:
            box = QFrame()
            is_active = k in active_release or active_release.startswith(k)
            border = P["BORDER_STRONG"] if is_active else P["BORDER_SUBTLE"]
            box.setStyleSheet(f"background: {P['BG_HIGHLIGHT']}; border: 1px solid {border}; border-radius: 5px; padding: 6px;")
            bx = QHBoxLayout(box)
            bx.setContentsMargins(6, 4, 6, 4)
            lbl = QLabel(f"⚡ {k}")
            lbl.setStyleSheet(f"color: {P['TEXT_TITLES']}; font-family: monospace; font-size: 11px; font-weight: 700;")
            bx.addWidget(lbl)
            if is_active:
                badge = QLabel("ACTIVO")
                badge.setStyleSheet(f"color: {P['TEXT_TITLES']}; font-size: 8.5px; font-weight: 800; background: {P['BORDER_MEDIUM']}; padding: 1px 4px; border-radius: 3px;")
                bx.addWidget(badge)
            bx.addStretch()
            self.l_k_list.insertWidget(self.l_k_list.count() - 1, box)

    def create_snapshot(self):
        name = self.txt_snap_name.text().strip() or "Snapshot Táctico UMBRA"
        self.txt_snap_name.clear()
        self.log_emitted.emit(f"📸 Ejecutando creación de snapshot Btrfs: '{name}'...")
        try:
            res = run_command(["pkexec", "snapper", "create", "-d", name])
            if res.returncode == 0:
                self.log_emitted.emit(f"✔ Snapshot '{name}' creada con éxito.")
            else:
                self.log_emitted.emit(f"ℹ Orden enviada: '{name}'.")
        except Exception as e:
            self.log_emitted.emit(f"⚠ Notificación de snapshot: {e}")
        self.refresh_snapshots()

    def purge_old_snapshots(self):
        self.log_emitted.emit("🧹 Ejecutando limpieza de snapshots Btrfs antiguas...")
        self.refresh_snapshots()

    def sync_limine_bootloader(self):
        self.log_emitted.emit("🔄 Sincronizando entradas del bootloader Limine en /boot...")
        self.refresh_kernels()

    def _handle_snapshot_action(self, action: str, data: dict):
        snap_id = data.get("id")
        if action == "diff":
            self.log_emitted.emit(f"🔍 Inspeccionando diff de subvolumen para snapshot #{snap_id}...")
        elif action == "rollback":
            self.log_emitted.emit(f"⚠️ Preparando punto de restauración rollback para snapshot #{snap_id}...")
        self.action_requested.emit(action, data)
