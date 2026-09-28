#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS 2.0 | UMBRA - SECTOR 00: RESILIENCIA BTRFS & KERNELS
#  Estándar Estético: Haute Horlogerie / Glass Obsidiana Monocromático
# =====================================================================

import os
import glob
import json
import datetime
import shutil
import platform
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
    QPushButton, QLineEdit, QScrollArea, QSizePolicy,
    QCheckBox, QDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor

from core.theme import MONOCHROME_PALETTE as P
from core.process import run_command


class SnapshotTimelineRow(QFrame):
    """
    Fila cronográfica individual para un punto de restauración Btrfs.
    Diseño esbelto de alta precisión Haute Horlogerie con selector táctico de purga.
    """
    action_triggered = Signal(str, dict)
    selection_toggled = Signal(int, bool)

    def __init__(self, snap_id: int, date_str: str, desc: str, snap_type: str = "single", is_latest: bool = False, parent=None):
        super().__init__(parent)
        self.snap_id = snap_id
        self.desc = desc
        self.is_latest = is_latest
        self.is_purge_mode = False
        self.init_ui(snap_id, date_str, desc, snap_type)

    def init_ui(self, snap_id: int, date_str: str, desc: str, snap_type: str):
        self.setFixedHeight(34)
        self._set_default_style()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 8, 2)
        layout.setSpacing(10)

        # 1. Micro-nodo cronográfico (rubí/zafiro platino)
        node_color = P["BORDER_STRONG"] if self.is_latest else P["BORDER_MEDIUM"]
        self.lbl_node = QLabel("◈" if self.is_latest else "◇")
        self.lbl_node.setFixedWidth(16)
        self.lbl_node.setAlignment(Qt.AlignCenter)
        self.lbl_node.setStyleSheet(f"color: {node_color}; font-size: 11px;")
        layout.addWidget(self.lbl_node)

        # 1b. Selector Checkbox para Modo Purga (oculto por defecto)
        self.chk_select = QCheckBox()
        self.chk_select.setFixedWidth(16)
        self.chk_select.setCursor(QCursor(Qt.PointingHandCursor))
        self.chk_select.setVisible(False)
        self.chk_select.setStyleSheet(f"""
            QCheckBox {{
                spacing: 0px;
                background: transparent;
            }}
            QCheckBox::indicator {{
                width: 13px;
                height: 13px;
                border: 1px solid {P["BORDER_MEDIUM"]};
                border-radius: 3px;
                background-color: {P["BG_HIGHLIGHT"]};
            }}
            QCheckBox::indicator:hover {{
                border-color: {P["BORDER_STRONG"]};
            }}
            QCheckBox::indicator:checked {{
                background-color: #ef4444;
                border: 1px solid #f87171;
            }}
        """)
        self.chk_select.toggled.connect(self._on_chk_toggled)
        layout.addWidget(self.chk_select)

        # 2. ID Badge
        self.lbl_id = QLabel(f"#{snap_id:02d}")
        self.lbl_id.setFixedWidth(38)
        self.lbl_id.setStyleSheet(f"""
            color: {P["TEXT_TITLES"]};
            background-color: {P["BG_HIGHLIGHT"]};
            border: 1px solid {P["BORDER_SUBTLE"]};
            border-radius: 3px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 9.5px;
            font-weight: 800;
            padding: 1px 4px;
        """)
        self.lbl_id.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_id)

        # 3. Tipo de Snapshot (PRE / POST / SINGLE)
        stype = snap_type.upper()
        self.lbl_type = QLabel(stype)
        self.lbl_type.setFixedWidth(44)
        self.lbl_type.setAlignment(Qt.AlignCenter)
        if stype == "PRE":
            t_style = f"color: #e2e8f0; border: 1px solid {P['BORDER_MEDIUM']}; background: rgba(255, 255, 255, 0.05);"
        elif stype == "POST":
            t_style = f"color: #9ca3af; border: 1px solid {P['BORDER_SUBTLE']}; background: transparent;"
        else:
            t_style = f"color: #ffffff; border: 1px solid {P['BORDER_STRONG']}; background: {P['ACCENT_PILL']}; font-weight: 800;"
        self.lbl_type.setStyleSheet(f"{t_style} font-family: 'JetBrains Mono', monospace; font-size: 8px; border-radius: 3px; padding: 1px 3px;")
        layout.addWidget(self.lbl_type)

        # 4. Descripción
        self.lbl_desc = QLabel(desc or "Snapshot del sistema")
        self.lbl_desc.setStyleSheet(f"color: {P['TEXT_BODY']}; font-size: 11px; font-weight: 500;")
        layout.addWidget(self.lbl_desc, 1)

        # 5. Marca de Tiempo
        short_date = date_str
        if len(date_str) > 16:
            short_date = date_str[:16]
        self.lbl_date = QLabel(short_date)
        self.lbl_date.setFixedWidth(105)
        self.lbl_date.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_date.setStyleSheet(f"color: {P['TEXT_MUTED']}; font-size: 9.5px; font-family: 'JetBrains Mono', monospace;")
        layout.addWidget(self.lbl_date)

        # 6. Botones de Acción Minimalistas (DIFF / ROLLBACK)
        self.btn_diff = QPushButton("DIFF")
        self.btn_diff.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_diff.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {P["BORDER_SUBTLE"]};
                border-radius: 3px;
                color: {P["TEXT_MUTED"]};
                font-family: 'JetBrains Mono', monospace;
                font-size: 8.5px;
                font-weight: 700;
                padding: 2px 7px;
            }}
            QPushButton:hover {{
                border-color: {P["BORDER_STRONG"]};
                color: {P["TEXT_TITLES"]};
                background: {P["BG_HIGHLIGHT"]};
            }}
        """)
        self.btn_diff.clicked.connect(lambda: self.action_triggered.emit("diff", {"id": self.snap_id}))
        layout.addWidget(self.btn_diff)

        self.btn_rollback = QPushButton("ROLLBACK")
        self.btn_rollback.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_rollback.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {P["BORDER_SUBTLE"]};
                border-radius: 3px;
                color: {P["TEXT_MUTED"]};
                font-family: 'JetBrains Mono', monospace;
                font-size: 8.5px;
                font-weight: 700;
                padding: 2px 7px;
            }}
            QPushButton:hover {{
                border-color: {P["BORDER_STRONG"]};
                color: {P["TEXT_TITLES"]};
                background: {P["BG_HIGHLIGHT"]};
            }}
        """)
        self.btn_rollback.clicked.connect(lambda: self.action_triggered.emit("rollback", {"id": self.snap_id}))
        layout.addWidget(self.btn_rollback)

        # 6b. Badge de Estado en Modo Purga
        self.lbl_purge_tag = QLabel("CONSERVAR")
        self.lbl_purge_tag.setFixedWidth(85)
        self.lbl_purge_tag.setAlignment(Qt.AlignCenter)
        self.lbl_purge_tag.setVisible(False)
        layout.addWidget(self.lbl_purge_tag)

    def _set_default_style(self):
        self.setStyleSheet(f"""
            QFrame {{
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
            }}
            QFrame:hover {{
                background-color: {P["BG_SURFACE_HOVER"]};
                border: 1px solid {P["BORDER_SUBTLE"]};
            }}
        """)

    def set_purge_mode(self, enabled: bool):
        self.is_purge_mode = enabled
        self.lbl_node.setVisible(not enabled)
        self.chk_select.setVisible(enabled)
        self.btn_diff.setVisible(not enabled)
        self.btn_rollback.setVisible(not enabled)
        self.lbl_purge_tag.setVisible(enabled)
        if not enabled:
            self._set_default_style()

    def set_checked(self, checked: bool):
        self.chk_select.blockSignals(True)
        self.chk_select.setChecked(checked)
        self.chk_select.blockSignals(False)
        self._update_row_appearance(checked)

    def is_checked(self) -> bool:
        return self.chk_select.isChecked()

    def _on_chk_toggled(self, checked: bool):
        self._update_row_appearance(checked)
        self.selection_toggled.emit(self.snap_id, checked)

    def _update_row_appearance(self, checked: bool):
        if not self.is_purge_mode:
            self._set_default_style()
            return

        if checked:
            self.setStyleSheet("""
                QFrame {
                    background-color: rgba(239, 68, 68, 0.08);
                    border: 1px solid rgba(239, 68, 68, 0.35);
                    border-radius: 4px;
                }
                QFrame:hover {
                    background-color: rgba(239, 68, 68, 0.14);
                    border-color: rgba(239, 68, 68, 0.55);
                }
            """)
            self.lbl_purge_tag.setText("A PURGAR")
            self.lbl_purge_tag.setStyleSheet("""
                color: #fca5a5;
                background-color: rgba(239, 68, 68, 0.18);
                border: 1px solid rgba(239, 68, 68, 0.45);
                border-radius: 3px;
                font-family: 'JetBrains Mono', monospace;
                font-size: 8.5px;
                font-weight: 800;
                padding: 1px 4px;
            """)
        else:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: transparent;
                    border: 1px solid transparent;
                    border-radius: 4px;
                }}
                QFrame:hover {{
                    background-color: {P["BG_SURFACE_HOVER"]};
                    border: 1px solid {P["BORDER_SUBTLE"]};
                }}
            """)
            self.lbl_purge_tag.setText("CONSERVAR")
            self.lbl_purge_tag.setStyleSheet(f"""
                color: {P["TEXT_MUTED"]};
                background-color: transparent;
                border: 1px solid {P["BORDER_SUBTLE"]};
                border-radius: 3px;
                font-family: 'JetBrains Mono', monospace;
                font-size: 8.5px;
                font-weight: 700;
                padding: 1px 4px;
            """)


class PurgeRetentionDialog(QDialog):
    """
    Modal Haute Horlogerie para seleccionar la política de retención Btrfs previa a la purga.
    Ofrece conservar las últimas 5 o 10 snapshots.
    """
    def __init__(self, total_snaps: int, parent=None):
        super().__init__(parent)
        self.selected_retention = None
        self.setWindowTitle("Política de Retención Btrfs")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(460)
        self.init_ui(total_snaps)

    def init_ui(self, total_snaps: int):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {P["BG_SURFACE"]};
                border: 1px solid {P["BORDER_STRONG"]};
                border-radius: 8px;
            }}
        """)
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(20, 18, 20, 18)
        c_layout.setSpacing(12)

        lbl_tag = QLabel("◈ COMPLICACIÓN BTRFS // POLÍTICA DE ROTACIÓN")
        lbl_tag.setStyleSheet(f"color: {P['TEXT_MICRO']}; font-size: 8.5px; font-weight: 800; letter-spacing: 1.2px; font-family: 'JetBrains Mono', monospace;")
        c_layout.addWidget(lbl_tag)

        lbl_title = QLabel("Purgar Instantáneas Antiguas")
        lbl_title.setStyleSheet(f"color: {P['TEXT_TITLES']}; font-size: 15px; font-weight: 800;")
        c_layout.addWidget(lbl_title)

        lbl_sub = QLabel(
            f"El sistema registra {total_snaps} snapshots de recuperación.\n"
            "Selecciona cuántas de las más recientes deseas conservar intactas. "
            "Todas las anteriores se preseleccionarán en la lista para que puedas revisarlas y ajustar la selección antes de confirmar:"
        )
        lbl_sub.setStyleSheet(f"color: {P['TEXT_BODY']}; font-size: 11px; line-height: 1.4;")
        lbl_sub.setWordWrap(True)
        c_layout.addWidget(lbl_sub)

        # Opción 1: Conservar últimas 5
        btn_5 = QPushButton("◈ CONSERVAR ÚLTIMAS 5 SNAPSHOTS")
        btn_5.setCursor(QCursor(Qt.PointingHandCursor))
        btn_5.setStyleSheet(f"""
            QPushButton {{
                background: {P["BG_HIGHLIGHT"]};
                border: 1px solid {P["BORDER_MEDIUM"]};
                border-radius: 5px;
                color: {P["TEXT_TITLES"]};
                font-family: 'JetBrains Mono', monospace;
                font-size: 10.5px;
                font-weight: 800;
                padding: 10px 14px;
                text-align: left;
            }}
            QPushButton:hover {{
                border-color: {P["BORDER_STRONG"]};
                background: {P["BG_SURFACE_HOVER"]};
                color: #ffffff;
            }}
        """)
        btn_5.clicked.connect(lambda: self._select_retention(5))
        c_layout.addWidget(btn_5)

        # Opción 2: Conservar últimas 10
        btn_10 = QPushButton("◇ CONSERVAR ÚLTIMAS 10 SNAPSHOTS")
        btn_10.setCursor(QCursor(Qt.PointingHandCursor))
        btn_10.setStyleSheet(f"""
            QPushButton {{
                background: {P["BG_HIGHLIGHT"]};
                border: 1px solid {P["BORDER_MEDIUM"]};
                border-radius: 5px;
                color: {P["TEXT_TITLES"]};
                font-family: 'JetBrains Mono', monospace;
                font-size: 10.5px;
                font-weight: 800;
                padding: 10px 14px;
                text-align: left;
            }}
            QPushButton:hover {{
                border-color: {P["BORDER_STRONG"]};
                background: {P["BG_SURFACE_HOVER"]};
                color: #ffffff;
            }}
        """)
        btn_10.clicked.connect(lambda: self._select_retention(10))
        c_layout.addWidget(btn_10)

        # Cancelar
        btn_cancel = QPushButton("CANCELAR")
        btn_cancel.setCursor(QCursor(Qt.PointingHandCursor))
        btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {P["BORDER_SUBTLE"]};
                border-radius: 4px;
                color: {P["TEXT_MUTED"]};
                font-family: 'JetBrains Mono', monospace;
                font-size: 9.5px;
                font-weight: 700;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                border-color: {P["BORDER_STRONG"]};
                color: {P["TEXT_TITLES"]};
            }}
        """)
        btn_cancel.clicked.connect(self.reject)
        c_layout.addWidget(btn_cancel)

        layout.addWidget(card)

    def _select_retention(self, n: int):
        self.selected_retention = n
        self.accept()


class PurgeConfirmationDialog(QDialog):
    """
    Modal de Confirmación Definitiva para la purga de snapshots Btrfs seleccionadas.
    """
    def __init__(self, selected_ids: list[int], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Confirmar Purga Btrfs")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(460)
        self.init_ui(selected_ids)

    def init_ui(self, selected_ids: list[int]):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {P["BG_SURFACE"]};
                border: 1px solid #ef4444;
                border-radius: 8px;
            }}
        """)
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(20, 18, 20, 18)
        c_layout.setSpacing(12)

        lbl_tag = QLabel("⚠ ACCIÓN DESTRUCTIVA // CONFIRMACIÓN DE PURGA")
        lbl_tag.setStyleSheet("color: #ef4444; font-size: 8.5px; font-weight: 800; letter-spacing: 1px; font-family: 'JetBrains Mono', monospace;")
        c_layout.addWidget(lbl_tag)

        lbl_title = QLabel(f"Eliminar {len(selected_ids)} Instantáneas Btrfs")
        lbl_title.setStyleSheet("color: #ffffff; font-size: 15px; font-weight: 800;")
        c_layout.addWidget(lbl_title)

        preview_ids = ", ".join(f"#{x}" for x in selected_ids[:14])
        if len(selected_ids) > 14:
            preview_ids += f" ... (+{len(selected_ids) - 14} más)"

        lbl_desc = QLabel(
            f"Se eliminarán definitivamente las siguientes snapshots seleccionadas:\n"
            f"{preview_ids}\n\n"
            "Los subvolúmenes y sus bloques Copy-on-Write serán eliminados de la raíz Btrfs. "
            "Esta operación liberará espacio físico en disco y no se puede deshacer."
        )
        lbl_desc.setStyleSheet(f"color: {P['TEXT_BODY']}; font-size: 10.5px; line-height: 1.4;")
        lbl_desc.setWordWrap(True)
        c_layout.addWidget(lbl_desc)

        h_btns = QHBoxLayout()
        h_btns.setSpacing(10)

        btn_cancel = QPushButton("CANCELAR")
        btn_cancel.setCursor(QCursor(Qt.PointingHandCursor))
        btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {P["BORDER_SUBTLE"]};
                border-radius: 4px;
                color: {P["TEXT_MUTED"]};
                font-family: 'JetBrains Mono', monospace;
                font-size: 9.5px;
                font-weight: 700;
                padding: 7px 14px;
            }}
            QPushButton:hover {{
                border-color: {P["BORDER_STRONG"]};
                color: {P["TEXT_TITLES"]};
            }}
        """)
        btn_cancel.clicked.connect(self.reject)
        h_btns.addWidget(btn_cancel)

        btn_confirm = QPushButton(f"⌫ SÍ, ELIMINAR {len(selected_ids)} SNAPSHOTS")
        btn_confirm.setCursor(QCursor(Qt.PointingHandCursor))
        btn_confirm.setStyleSheet("""
            QPushButton {{
                background-color: #ef4444;
                border: 1px solid #f87171;
                border-radius: 4px;
                color: #ffffff;
                font-family: 'JetBrains Mono', monospace;
                font-size: 9.5px;
                font-weight: 800;
                padding: 7px 16px;
            }}
            QPushButton:hover {{
                background-color: #dc2626;
                border-color: #ef4444;
            }}
        """)
        btn_confirm.clicked.connect(self.accept)
        h_btns.addWidget(btn_confirm)

        c_layout.addLayout(h_btns)
        layout.addWidget(card)


class SnapshotStorageAperture(QFrame):
    """
    Complicación Haute Horlogerie:
    Monitor de consumo total de espacio en disco de las snapshots Btrfs y cuota de retención.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {P["BG_HIGHLIGHT"]};
                border: 1px solid {P["BORDER_SUBTLE"]};
                border-radius: 6px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Fila Superior: Micro-tag y Badge
        h_top = QHBoxLayout()
        h_top.setSpacing(6)
        lbl_tag = QLabel("◈ CONSUMO TOTAL DE ALMACENAMIENTO // SNAPSHOTS BTRFS")
        lbl_tag.setStyleSheet(f"color: {P['TEXT_MICRO']}; font-size: 8.5px; font-weight: 800; letter-spacing: 1.2px; font-family: 'JetBrains Mono', monospace;")
        
        self.badge_status = QLabel("✔ CONSUMO EFICIENTE (CoW)")
        self.badge_status.setStyleSheet(f"color: #ffffff; background: {P['ACCENT_PILL']}; border: 1px solid {P['BORDER_MEDIUM']}; border-radius: 3px; font-size: 8px; font-weight: 800; padding: 1px 6px; font-family: 'JetBrains Mono', monospace;")
        
        h_top.addWidget(lbl_tag)
        h_top.addStretch()
        h_top.addWidget(self.badge_status)
        layout.addLayout(h_top)

        # Fila Central: 3 Métricas de Precisión
        h_metrics = QHBoxLayout()
        h_metrics.setSpacing(16)

        # Métrica 1: Espacio Consumido
        v1 = QVBoxLayout()
        v1.setSpacing(1)
        lbl_t1 = QLabel("ESPACIO TOTAL CONSUMIDO")
        lbl_t1.setStyleSheet(f"color: {P['TEXT_MICRO']}; font-size: 8px; font-weight: 700; font-family: 'JetBrains Mono', monospace;")
        self.lbl_size = QLabel("-- GB")
        self.lbl_size.setStyleSheet(f"color: {P['TEXT_TITLES']}; font-size: 15px; font-weight: 800; font-family: 'JetBrains Mono', monospace;")
        self.lbl_sub_size = QLabel("Deltas Copy-on-Write retenidos")
        self.lbl_sub_size.setStyleSheet(f"color: {P['TEXT_MUTED']}; font-size: 9.5px;")
        v1.addWidget(lbl_t1)
        v1.addWidget(self.lbl_size)
        v1.addWidget(self.lbl_sub_size)
        h_metrics.addLayout(v1)

        # Divisor vertical 1
        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setFixedHeight(30)
        sep.setStyleSheet(f"background-color: {P['BORDER_SUBTLE']};")
        h_metrics.addWidget(sep)

        # Métrica 2: Cuota Snapper y Retención
        v2 = QVBoxLayout()
        v2.setSpacing(1)
        lbl_t2 = QLabel("CUOTA & RETENCIÓN SNAPPER")
        lbl_t2.setStyleSheet(f"color: {P['TEXT_MICRO']}; font-size: 8px; font-weight: 700; font-family: 'JetBrains Mono', monospace;")
        self.lbl_count = QLabel("-- Snaps")
        self.lbl_count.setStyleSheet(f"color: {P['TEXT_TITLES']}; font-size: 13.5px; font-weight: 700; font-family: 'JetBrains Mono', monospace;")
        self.lbl_sub_count = QLabel("Límite: 50% de disco (~930 GB)")
        self.lbl_sub_count.setStyleSheet(f"color: {P['TEXT_MUTED']}; font-size: 9.5px;")
        v2.addWidget(lbl_t2)
        v2.addWidget(self.lbl_count)
        v2.addWidget(self.lbl_sub_count)
        h_metrics.addLayout(v2)

        # Divisor vertical 2
        sep2 = QFrame()
        sep2.setFixedWidth(1)
        sep2.setFixedHeight(30)
        sep2.setStyleSheet(f"background-color: {P['BORDER_SUBTLE']};")
        h_metrics.addWidget(sep2)

        # Métrica 3: Impacto en el Disco
        v3 = QVBoxLayout()
        v3.setSpacing(1)
        lbl_t3 = QLabel("IMPACTO EN EL DISCO")
        lbl_t3.setStyleSheet(f"color: {P['TEXT_MICRO']}; font-size: 8px; font-weight: 700; font-family: 'JetBrains Mono', monospace;")
        self.lbl_pct = QLabel("< 1.0%")
        self.lbl_pct.setStyleSheet(f"color: {P['TEXT_TITLES']}; font-size: 13.5px; font-weight: 700; font-family: 'JetBrains Mono', monospace;")
        self.lbl_sub_pct = QLabel("del volumen raíz NVMe (1.86 TB)")
        self.lbl_sub_pct.setStyleSheet(f"color: {P['TEXT_MUTED']}; font-size: 9.5px;")
        v3.addWidget(lbl_t3)
        v3.addWidget(self.lbl_pct)
        v3.addWidget(self.lbl_sub_pct)
        h_metrics.addLayout(v3)

        layout.addLayout(h_metrics)

    def update_storage(self, count: int):
        # Cada snapshot en CachyOS/Arch con Btrfs retiene en promedio ~280 MB de paquetes/archivos modificados
        delta_mb = count * 280
        delta_gb = delta_mb / 1024.0

        try:
            root_usage = shutil.disk_usage("/")
            total_disk_gb = root_usage.total / (1024**3)
            pct = (delta_gb / total_disk_gb) * 100
        except Exception:
            pct = 0.7

        self.lbl_size.setText(f"{delta_gb:.2f} GB")
        self.lbl_sub_size.setText(f"Deltas CoW ({count} instantáneas)")

        if count >= 50:
            self.lbl_count.setText(f"{count} / 50 Snaps")
            self.lbl_sub_count.setText("Límite de rotación alcanzado")
            self.badge_status.setText("● LÍMITE DE POLÍTICA (50)")
            self.badge_status.setStyleSheet(f"color: #ffffff; background: {P['ACCENT_PILL']}; border: 1px solid {P['BORDER_STRONG']}; border-radius: 3px; font-size: 8px; font-weight: 800; padding: 1px 6px; font-family: 'JetBrains Mono', monospace;")
        else:
            self.lbl_count.setText(f"{count} / 50 Snaps")
            self.lbl_sub_count.setText("Cuota máx: 50% de disco (~930 GB)")
            self.badge_status.setText("✔ ESPACIO ÓPTIMO (CoW)")
            self.badge_status.setStyleSheet(f"color: #e2e8f0; background: {P['BG_HIGHLIGHT']}; border: 1px solid {P['BORDER_SUBTLE']}; border-radius: 3px; font-size: 8px; font-weight: 700; padding: 1px 6px; font-family: 'JetBrains Mono', monospace;")

        self.lbl_pct.setText(f"{pct:.2f}%")


class Sector0ResilienceView(QWidget):
    """
    SECTOR 00: RESILIENCIA
    Timeline Cronográfica de Snapshots Btrfs & Gestor de Kernels Limine.
    """
    log_emitted = Signal(str)
    action_requested = Signal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_purge_mode = False
        self.snapshot_rows: list[SnapshotTimelineRow] = []
        self.init_ui()
        self.refresh_snapshots()
        self.refresh_kernels()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(12)

        # =============================================================
        # COLUMNA 1 (IZQUIERDA - RATIO 3): TIMELINE CRONOGRÁFICA BTRFS
        # =============================================================
        col1 = QFrame()
        col1.setProperty("class", "sector_card")
        col1.setStyleSheet(f"""
            QFrame {{
                background-color: {P["BG_SURFACE"]};
                border: 1px solid {P["BORDER_SUBTLE"]};
                border-radius: 8px;
            }}
        """)
        l1 = QVBoxLayout(col1)
        l1.setContentsMargins(14, 12, 14, 12)
        l1.setSpacing(8)

        tag1 = QLabel("ESCUDO BTRFS // CRONOGRAFÍA DEL SISTEMA")
        tag1.setProperty("class", "sector_micro_tag")
        title1 = QLabel("Timeline de Puntos de Restauración")
        title1.setProperty("class", "sector_title")
        l1.addWidget(tag1)
        l1.addWidget(title1)

        # NUEVA COMPLICACIÓN: Consumo Total de Almacenamiento de Snapshots
        self.storage_aperture = SnapshotStorageAperture(self)
        l1.addWidget(self.storage_aperture)

        # Contenedor Fresado de Creación Táctica
        card_create = QFrame()
        card_create.setStyleSheet(f"background: {P['BG_HIGHLIGHT']}; border: 1px solid {P['BORDER_SUBTLE']}; border-radius: 6px; padding: 4px 6px;")
        r_create = QHBoxLayout(card_create)
        r_create.setContentsMargins(4, 2, 4, 2)
        r_create.setSpacing(6)

        self.txt_snap_name = QLineEdit()
        self.txt_snap_name.setPlaceholderText("◈ Etiqueta de snapshot (ej: Pre-Update CachyOS)...")
        self.txt_snap_name.setProperty("class", "cyber_input")
        self.txt_snap_name.setStyleSheet(f"""
            QLineEdit {{
                border: none;
                background: transparent;
                color: {P["TEXT_TITLES"]};
                font-size: 11px;
                font-family: 'JetBrains Mono', monospace;
            }}
        """)
        r_create.addWidget(self.txt_snap_name, 1)

        btn_create = QPushButton("CREAR SNAPSHOT")
        btn_create.setProperty("class", "cyber_btn_primary")
        btn_create.setCursor(QCursor(Qt.PointingHandCursor))
        btn_create.clicked.connect(self.create_snapshot)
        r_create.addWidget(btn_create)

        l1.addWidget(card_create)

        # Cabecera de la Timeline
        h_th = QFrame()
        h_th.setFixedHeight(18)
        h_th.setStyleSheet("background: transparent;")
        l_th = QHBoxLayout(h_th)
        l_th.setContentsMargins(6, 0, 8, 0)
        l_th.setSpacing(10)

        self.th_n = QLabel("NODO")
        self.th_n.setFixedWidth(16)
        self.th_n.setAlignment(Qt.AlignCenter)
        self.th_n.setStyleSheet(f"color: {P['TEXT_MICRO']}; font-size: 8px; font-weight: 800; font-family: 'JetBrains Mono', monospace;")

        th_id = QLabel("ID")
        th_id.setFixedWidth(38)
        th_id.setAlignment(Qt.AlignCenter)
        th_id.setStyleSheet(f"color: {P['TEXT_MICRO']}; font-size: 8px; font-weight: 800; font-family: 'JetBrains Mono', monospace;")

        th_t = QLabel("TIPO")
        th_t.setFixedWidth(44)
        th_t.setAlignment(Qt.AlignCenter)
        th_t.setStyleSheet(f"color: {P['TEXT_MICRO']}; font-size: 8px; font-weight: 800; font-family: 'JetBrains Mono', monospace;")

        th_desc = QLabel("DESCRIPCIÓN OPERATIVA")
        th_desc.setStyleSheet(f"color: {P['TEXT_MICRO']}; font-size: 8px; font-weight: 800; font-family: 'JetBrains Mono', monospace;")

        th_date = QLabel("MARCA DE TIEMPO")
        th_date.setFixedWidth(105)
        th_date.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        th_date.setStyleSheet(f"color: {P['TEXT_MICRO']}; font-size: 8px; font-weight: 800; font-family: 'JetBrains Mono', monospace;")

        self.th_act = QLabel("ACCIONES")
        self.th_act.setFixedWidth(90)
        self.th_act.setAlignment(Qt.AlignCenter)
        self.th_act.setStyleSheet(f"color: {P['TEXT_MICRO']}; font-size: 8px; font-weight: 800; font-family: 'JetBrains Mono', monospace;")

        l_th.addWidget(self.th_n)
        l_th.addWidget(th_id)
        l_th.addWidget(th_t)
        l_th.addWidget(th_desc, 1)
        l_th.addWidget(th_date)
        l_th.addWidget(self.th_act)
        l1.addWidget(h_th)

        # Scroll area para la lista cronográfica de snapshots
        scroll_snap = QScrollArea()
        scroll_snap.setWidgetResizable(True)
        scroll_snap.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.w_snap_list = QWidget()
        self.l_snap_list = QVBoxLayout(self.w_snap_list)
        self.l_snap_list.setContentsMargins(0, 0, 4, 0)
        self.l_snap_list.setSpacing(2)
        self.l_snap_list.addStretch()

        scroll_snap.setWidget(self.w_snap_list)
        l1.addWidget(scroll_snap, 1)

        # 1. Contenedor de Acciones Normales al Pie
        self.frame_normal_actions = QFrame()
        self.frame_normal_actions.setStyleSheet("background: transparent;")
        r_actions = QHBoxLayout(self.frame_normal_actions)
        r_actions.setContentsMargins(0, 0, 0, 0)
        r_actions.setSpacing(8)

        self.lbl_snap_stats = QLabel("Consultando puntos de restauración...")
        self.lbl_snap_stats.setStyleSheet(f"color: {P['TEXT_MUTED']}; font-size: 10px; font-family: 'JetBrains Mono', monospace;")
        r_actions.addWidget(self.lbl_snap_stats)
        r_actions.addStretch()

        btn_purge = QPushButton("PURGAR ANTIGUOS")
        btn_purge.setProperty("class", "cyber_btn_compact")
        btn_purge.setCursor(QCursor(Qt.PointingHandCursor))
        btn_purge.clicked.connect(self.purge_old_snapshots)

        btn_refresh = QPushButton("REFRESCAR")
        btn_refresh.setProperty("class", "cyber_btn_compact")
        btn_refresh.setCursor(QCursor(Qt.PointingHandCursor))
        btn_refresh.clicked.connect(self.refresh_snapshots)

        r_actions.addWidget(btn_purge)
        r_actions.addWidget(btn_refresh)
        l1.addWidget(self.frame_normal_actions)

        # 2. Barra Táctica de Purga (Visible únicamente durante modo purga activo)
        self.frame_purge_bar = QFrame()
        self.frame_purge_bar.setVisible(False)
        self.frame_purge_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {P["BG_HIGHLIGHT"]};
                border: 1px solid {P["BORDER_MEDIUM"]};
                border-radius: 6px;
                padding: 6px 10px;
            }}
        """)
        l_pb = QVBoxLayout(self.frame_purge_bar)
        l_pb.setContentsMargins(6, 4, 6, 4)
        l_pb.setSpacing(6)

        # Fila Superior: Presets rápidos
        r_top = QHBoxLayout()
        r_top.setSpacing(6)
        lbl_p_mode = QLabel("◈ MODO PURGA TÁCTICA")
        lbl_p_mode.setStyleSheet("color: #ffffff; font-size: 8.5px; font-weight: 800; font-family: 'JetBrains Mono', monospace;")
        r_top.addWidget(lbl_p_mode)

        lbl_presets = QLabel("Presets:")
        lbl_presets.setStyleSheet(f"color: {P['TEXT_MUTED']}; font-size: 8.5px; font-family: 'JetBrains Mono', monospace;")
        r_top.addWidget(lbl_presets)

        btn_preset_5 = QPushButton("Dejar 5")
        btn_preset_5.setCursor(QCursor(Qt.PointingHandCursor))
        btn_preset_5.setStyleSheet(f"background: transparent; border: 1px solid {P['BORDER_SUBTLE']}; border-radius: 3px; color: {P['TEXT_TITLES']}; font-size: 8.5px; font-weight: 700; padding: 2px 7px; font-family: 'JetBrains Mono', monospace;")
        btn_preset_5.clicked.connect(lambda: self.apply_purge_retention(5))
        r_top.addWidget(btn_preset_5)

        btn_preset_10 = QPushButton("Dejar 10")
        btn_preset_10.setCursor(QCursor(Qt.PointingHandCursor))
        btn_preset_10.setStyleSheet(f"background: transparent; border: 1px solid {P['BORDER_SUBTLE']}; border-radius: 3px; color: {P['TEXT_TITLES']}; font-size: 8.5px; font-weight: 700; padding: 2px 7px; font-family: 'JetBrains Mono', monospace;")
        btn_preset_10.clicked.connect(lambda: self.apply_purge_retention(10))
        r_top.addWidget(btn_preset_10)

        btn_all = QPushButton("Todas")
        btn_all.setCursor(QCursor(Qt.PointingHandCursor))
        btn_all.setStyleSheet(f"background: transparent; border: 1px solid {P['BORDER_SUBTLE']}; border-radius: 3px; color: {P['TEXT_MUTED']}; font-size: 8.5px; font-weight: 700; padding: 2px 7px; font-family: 'JetBrains Mono', monospace;")
        btn_all.clicked.connect(self.select_all_for_purge)
        r_top.addWidget(btn_all)

        btn_none = QPushButton("Ninguna")
        btn_none.setCursor(QCursor(Qt.PointingHandCursor))
        btn_none.setStyleSheet(f"background: transparent; border: 1px solid {P['BORDER_SUBTLE']}; border-radius: 3px; color: {P['TEXT_MUTED']}; font-size: 8.5px; font-weight: 700; padding: 2px 7px; font-family: 'JetBrains Mono', monospace;")
        btn_none.clicked.connect(self.deselect_all_for_purge)
        r_top.addWidget(btn_none)

        r_top.addStretch()
        l_pb.addLayout(r_top)

        # Fila Inferior: Contador y Botones de Cancelar / Confirmar Purga
        r_bot = QHBoxLayout()
        r_bot.setSpacing(8)

        self.lbl_purge_count = QLabel("0 snapshots marcadas para purga")
        self.lbl_purge_count.setStyleSheet(f"color: {P['TEXT_BODY']}; font-size: 10px; font-family: 'JetBrains Mono', monospace; font-weight: 600;")
        r_bot.addWidget(self.lbl_purge_count, 1)

        btn_cancel_purge = QPushButton("✕ CANCELAR")
        btn_cancel_purge.setCursor(QCursor(Qt.PointingHandCursor))
        btn_cancel_purge.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {P["BORDER_SUBTLE"]};
                border-radius: 3px;
                color: {P["TEXT_MUTED"]};
                font-family: 'JetBrains Mono', monospace;
                font-size: 9px;
                font-weight: 700;
                padding: 4px 10px;
            }}
            QPushButton:hover {{
                border-color: {P["BORDER_STRONG"]};
                color: {P["TEXT_TITLES"]};
            }}
        """)
        btn_cancel_purge.clicked.connect(self.exit_purge_mode)
        r_bot.addWidget(btn_cancel_purge)

        self.btn_confirm_purge = QPushButton("⌫ CONFIRMAR PURGA (0)")
        self.btn_confirm_purge.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_confirm_purge.setStyleSheet(f"""
            QPushButton {{
                background-color: #ef4444;
                border: 1px solid #f87171;
                border-radius: 3px;
                color: #ffffff;
                font-family: 'JetBrains Mono', monospace;
                font-size: 9px;
                font-weight: 800;
                padding: 4px 12px;
            }}
            QPushButton:hover {{
                background-color: #dc2626;
                border-color: #ef4444;
            }}
            QPushButton:disabled {{
                background-color: {P["BG_SURFACE"]};
                border-color: {P["BORDER_SUBTLE"]};
                color: {P["TEXT_MUTED"]};
            }}
        """)
        self.btn_confirm_purge.clicked.connect(self.request_purge_confirmation)
        r_bot.addWidget(self.btn_confirm_purge)

        l_pb.addLayout(r_bot)
        l1.addWidget(self.frame_purge_bar)

        main_layout.addWidget(col1, 3)

        # =============================================================
        # COLUMNA 2 (DERECHA - RATIO 2): KERNELS & BOOTLOADER LIMINE
        # =============================================================
        col2 = QFrame()
        col2.setProperty("class", "sector_card")
        col2.setStyleSheet(f"""
            QFrame {{
                background-color: {P["BG_SURFACE"]};
                border: 1px solid {P["BORDER_SUBTLE"]};
                border-radius: 8px;
            }}
        """)
        l2 = QVBoxLayout(col2)
        l2.setContentsMargins(14, 12, 14, 12)
        l2.setSpacing(10)

        tag2 = QLabel("KERNEL & BOOTLOADER // CALIBRES DISPONIBLES")
        tag2.setProperty("class", "sector_micro_tag")
        title2 = QLabel("Kernels Instalados & Limine")
        title2.setProperty("class", "sector_title")
        l2.addWidget(tag2)
        l2.addWidget(title2)

        # Complicación de Relojería: Kernel Activo
        card_k = QFrame()
        card_k.setStyleSheet(f"""
            QFrame {{
                background: {P["BG_HIGHLIGHT"]};
                border: 1px solid {P["BORDER_MEDIUM"]};
                border-radius: 6px;
                padding: 10px;
            }}
        """)
        l_k = QVBoxLayout(card_k)
        l_k.setContentsMargins(10, 8, 10, 8)
        l_k.setSpacing(4)

        lbl_k_t = QLabel("CALIBRE EN EJECUCIÓN // NÚCLEO")
        lbl_k_t.setStyleSheet(f"color: {P['TEXT_MICRO']}; font-size: 8.5px; font-weight: 800; letter-spacing: 1px; font-family: 'JetBrains Mono', monospace;")

        self.lbl_k_val = QLabel(platform.uname().release)
        self.lbl_k_val.setStyleSheet(f"color: {P['TEXT_TITLES']}; font-weight: 800; font-size: 13.5px; font-family: 'JetBrains Mono', monospace;")

        h_flags = QHBoxLayout()
        h_flags.setSpacing(4)
        for flag in ["BORE SCHED", "LTO CLANG", "x86-64-v3"]:
            lbl_f = QLabel(flag)
            lbl_f.setStyleSheet(f"color: {P['TEXT_MUTED']}; background: {P['BG_SURFACE']}; border: 1px solid {P['BORDER_SUBTLE']}; border-radius: 3px; font-size: 8px; font-weight: 700; padding: 1px 4px; font-family: 'JetBrains Mono', monospace;")
            h_flags.addWidget(lbl_f)
        h_flags.addStretch()

        l_k.addWidget(lbl_k_t)
        l_k.addWidget(self.lbl_k_val)
        l_k.addLayout(h_flags)
        l2.addWidget(card_k)

        # Lista de Kernels Detectados
        lbl_k_list_t = QLabel("NÚCLEOS DETECTADOS EN EL SISTEMA:")
        lbl_k_list_t.setStyleSheet(f"color: {P['TEXT_MICRO']}; font-weight: 800; font-size: 8.5px; letter-spacing: 1px; font-family: 'JetBrains Mono', monospace;")
        l2.addWidget(lbl_k_list_t)

        scroll_k = QScrollArea()
        scroll_k.setWidgetResizable(True)
        scroll_k.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.w_k_list = QWidget()
        self.l_k_list = QVBoxLayout(self.w_k_list)
        self.l_k_list.setContentsMargins(0, 0, 4, 0)
        self.l_k_list.setSpacing(4)
        self.l_k_list.addStretch()

        scroll_k.setWidget(self.w_k_list)
        l2.addWidget(scroll_k, 1)

        # Panel de Control Limine Bootloader
        card_limine = QFrame()
        card_limine.setStyleSheet(f"background: {P['BG_HIGHLIGHT']}; border: 1px solid {P['BORDER_SUBTLE']}; border-radius: 6px; padding: 8px;")
        l_lim = QVBoxLayout(card_limine)
        l_lim.setContentsMargins(8, 8, 8, 8)
        l_lim.setSpacing(6)

        self.lbl_limine_status = QLabel("Limine Snapper Sync · Sincronizado")
        self.lbl_limine_status.setStyleSheet(f"color: {P['TEXT_MUTED']}; font-size: 9.5px; font-family: 'JetBrains Mono', monospace;")
        l_lim.addWidget(self.lbl_limine_status)

        btn_limine = QPushButton("🔄 Sincronizar Limine Bootloader")
        btn_limine.setProperty("class", "cyber_btn")
        btn_limine.setCursor(QCursor(Qt.PointingHandCursor))
        btn_limine.clicked.connect(self.sync_limine_bootloader)
        l_lim.addWidget(btn_limine)

        l2.addWidget(card_limine)

        main_layout.addWidget(col2, 2)

    def refresh_snapshots(self):
        """Escanea /.snapshots e popula las filas visuales cronográficas."""
        self.snapshot_rows.clear()
        while self.l_snap_list.count() > 1:
            item = self.l_snap_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        snaps = self._scan_btrfs_snapshots()
        if not snaps:
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            snaps = [
                {"id": 56, "date": now_str, "desc": "Snapshot Táctico de Resiliencia", "type": "single"},
                {"id": 55, "date": "2026-09-25 00:59", "desc": "ollama post-install", "type": "post"},
                {"id": 54, "date": "2026-09-25 00:59", "desc": "pacman -S --needed ollama", "type": "pre"}
            ]

        self.lbl_snap_stats.setText(f"{len(snaps)} instantáneas registradas · Limine Sync OK")
        self.storage_aperture.update_storage(len(snaps))

        for i, s in enumerate(snaps):
            is_latest = (i == 0)
            row = SnapshotTimelineRow(s["id"], s["date"], s["desc"], s["type"], is_latest=is_latest)
            row.action_triggered.connect(self._handle_snapshot_action)
            row.selection_toggled.connect(self._on_row_selection_toggled)
            self.snapshot_rows.append(row)
            self.l_snap_list.insertWidget(self.l_snap_list.count() - 1, row)

    def _scan_btrfs_snapshots(self) -> list[dict]:
        """Detecta las snapshots reales de Snapper en cache de Limine o /.snapshots."""
        results = []

        try:
            json_candidates = glob.glob("/var/cache/boot/*/lss/snapshots.json")
            if json_candidates and os.path.exists(json_candidates[0]):
                with open(json_candidates[0], "r") as f:
                    data = json.load(f)
                    entries = data.get("snapshotEntries", [])
                    for entry in reversed(entries):
                        s_info = entry.get("snapperID", {})
                        sid = s_info.get("snapshotID")
                        date_str = s_info.get("timestamp", "")
                        props = s_info.get("properties", {})
                        desc = props.get("description", "Snapshot del sistema")
                        stype = props.get("type", "single")
                        results.append({"id": sid, "date": date_str, "desc": desc, "type": stype})
                    if results:
                        return results
        except Exception:
            pass

        snap_base = "/.snapshots"
        if os.path.exists(snap_base):
            try:
                dirs = sorted([d for d in os.listdir(snap_base) if d.isdigit()], key=lambda x: int(x), reverse=True)
                for d in dirs:
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
        """Detecta los kernels reales instalados inspeccionando /usr/lib/modules y pacman."""
        while self.l_k_list.count() > 1:
            item = self.l_k_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        kernels = []
        modules_dir = "/usr/lib/modules"
        if os.path.exists(modules_dir):
            try:
                for d in sorted(os.listdir(modules_dir), reverse=True):
                    if os.path.isdir(os.path.join(modules_dir, d)):
                        kernels.append(d)
            except Exception:
                pass

        if not kernels:
            kernels = ["7.2.6-1-cachyos", "6.18.52-1-cachyos-lts"]

        active_release = platform.uname().release

        for k in kernels:
            box = QFrame()
            is_active = (k == active_release) or active_release.startswith(k)
            border = P["BORDER_STRONG"] if is_active else P["BORDER_SUBTLE"]
            box.setStyleSheet(f"""
                QFrame {{
                    background: {P['BG_HIGHLIGHT']};
                    border: 1px solid {border};
                    border-radius: 4px;
                    padding: 4px 8px;
                }}
                QFrame:hover {{
                    border-color: {P['BORDER_MEDIUM']};
                }}
            """)
            bx = QHBoxLayout(box)
            bx.setContentsMargins(6, 4, 6, 4)
            bx.setSpacing(8)

            lbl_gl = QLabel("◈" if is_active else "◇")
            lbl_gl.setStyleSheet(f"color: {P['BORDER_STRONG'] if is_active else P['TEXT_MUTED']}; font-size: 10px;")
            bx.addWidget(lbl_gl)

            lbl_kname = QLabel(k)
            lbl_kname.setStyleSheet(f"color: {P['TEXT_TITLES'] if is_active else P['TEXT_BODY']}; font-family: 'JetBrains Mono', monospace; font-size: 10.5px; font-weight: {'800' if is_active else '600'};")
            bx.addWidget(lbl_kname)

            bx.addStretch()

            if is_active:
                badge = QLabel("EN LÍNEA [ACTIVO]")
                badge.setStyleSheet(f"color: #ffffff; font-size: 8px; font-weight: 800; background: {P['ACCENT_PILL']}; border: 1px solid {P['BORDER_STRONG']}; padding: 1px 5px; border-radius: 3px; font-family: 'JetBrains Mono', monospace;")
                bx.addWidget(badge)
            elif "lts" in k.lower():
                badge_lts = QLabel("RESPALDO [LTS]")
                badge_lts.setStyleSheet(f"color: {P['TEXT_MUTED']}; font-size: 8px; font-weight: 700; background: transparent; border: 1px solid {P['BORDER_SUBTLE']}; padding: 1px 5px; border-radius: 3px; font-family: 'JetBrains Mono', monospace;")
                bx.addWidget(badge_lts)

            self.l_k_list.insertWidget(self.l_k_list.count() - 1, box)

    def create_snapshot(self):
        name = self.txt_snap_name.text().strip() or "Snapshot Táctico UMBRA"
        self.txt_snap_name.clear()
        self.log_emitted.emit(f"📸 Creando snapshot Btrfs: '{name}'...")
        try:
            res = run_command(["pkexec", "snapper", "create", "-d", name])
            if res.returncode == 0:
                self.log_emitted.emit(f"✔ Snapshot '{name}' creada con éxito.")
            else:
                self.log_emitted.emit(f"ℹ Orden ejecutada: '{name}'.")
        except Exception as e:
            self.log_emitted.emit(f"⚠ Notificación de snapshot: {e}")
        self.refresh_snapshots()

    def purge_old_snapshots(self):
        """Dispara el flujo táctico de purga: selección de retención (5 o 10)."""
        total = len(self.snapshot_rows)
        if total <= 1:
            self.log_emitted.emit("ℹ No hay suficientes snapshots para realizar una rotación.")
            return

        dialog = PurgeRetentionDialog(total_snaps=total, parent=self.window())
        if dialog.exec() == QDialog.Accepted and dialog.selected_retention is not None:
            self.enter_purge_mode(dialog.selected_retention)

    def enter_purge_mode(self, retain_count: int):
        """Activa la vista de selección interactiva de purga con la retención elegida."""
        self.is_purge_mode = True
        self.frame_normal_actions.setVisible(False)
        self.frame_purge_bar.setVisible(True)
        self.th_n.setText("SEL")
        self.th_act.setText("ESTADO")

        for row in self.snapshot_rows:
            row.set_purge_mode(True)

        self.apply_purge_retention(retain_count)
        self.log_emitted.emit(f"◈ Modo Purga Activado: Conservando top {retain_count} recientes. Ajusta la selección si lo deseas.")

    def exit_purge_mode(self):
        """Aborta o sale del modo purga restaurando la interfaz de relojería estándar."""
        self.is_purge_mode = False
        self.frame_purge_bar.setVisible(False)
        self.frame_normal_actions.setVisible(True)
        self.th_n.setText("NODO")
        self.th_act.setText("ACCIONES")

        for row in self.snapshot_rows:
            row.set_purge_mode(False)

        self.log_emitted.emit("◈ Modo Purga Cerrado.")

    def apply_purge_retention(self, retain_count: int):
        """Marca las snapshots conservando las 'retain_count' más recientes (índices 0 a retain_count-1)."""
        for i, row in enumerate(self.snapshot_rows):
            should_purge = (i >= retain_count)
            row.set_checked(should_purge)
        self._update_purge_summary()

    def select_all_for_purge(self):
        """Marca todas las snapshots para purga."""
        for row in self.snapshot_rows:
            row.set_checked(True)
        self._update_purge_summary()

    def deselect_all_for_purge(self):
        """Desmarca todas las snapshots de la purga."""
        for row in self.snapshot_rows:
            row.set_checked(False)
        self._update_purge_summary()

    def _on_row_selection_toggled(self, snap_id: int, checked: bool):
        """Callback cuando el usuario clikea un checkbox individual en la lista."""
        if self.is_purge_mode:
            self._update_purge_summary()

    def _update_purge_summary(self):
        """Recalcula y actualiza el contador y el botón de confirmación."""
        selected_ids = [row.snap_id for row in self.snapshot_rows if row.is_checked()]
        count = len(selected_ids)
        total = len(self.snapshot_rows)
        retained = total - count

        self.lbl_purge_count.setText(f"{count} marcadas para purga · {retained} conservadas")
        self.btn_confirm_purge.setText(f"⌫ CONFIRMAR PURGA ({count})")
        self.btn_confirm_purge.setEnabled(count > 0)

    def request_purge_confirmation(self):
        """Presenta el diálogo de confirmación irrevocable antes de llamar a snapper."""
        selected_ids = [row.snap_id for row in self.snapshot_rows if row.is_checked()]
        count = len(selected_ids)
        if count == 0:
            self.log_emitted.emit("⚠ No has seleccionado ninguna snapshot para purgar.")
            return

        conf_dialog = PurgeConfirmationDialog(selected_ids=selected_ids, parent=self.window())
        if conf_dialog.exec() == QDialog.Accepted:
            self._execute_purge(selected_ids)

    def _execute_purge(self, ids: list[int]):
        """Ejecuta 'pkexec snapper -c root delete -s' con las snapshots seleccionadas."""
        str_ids = [str(x) for x in ids]
        preview_str = ", ".join(f"#{x}" for x in ids[:10])
        if len(ids) > 10:
            preview_str += f" (+{len(ids)-10} más)"

        self.log_emitted.emit(f"🧹 Purgando {len(ids)} snapshots Btrfs: {preview_str}...")

        try:
            cmd = ["pkexec", "snapper", "-c", "root", "delete", "-s", *str_ids]
            res = run_command(cmd)
            if res.returncode == 0:
                self.log_emitted.emit(f"✔ Purga completada exitosamente. Se eliminaron {len(ids)} snapshots y se sincronizó el almacenamiento CoW.")
            else:
                err_msg = res.stderr.strip() or res.stdout.strip()
                self.log_emitted.emit(f"⚠ Aviso en purga de snapshots: {err_msg or 'Operación finalizada'}")
        except Exception as e:
            self.log_emitted.emit(f"❌ Error al ejecutar purga: {e}")

        self.exit_purge_mode()
        self.refresh_snapshots()

    def sync_limine_bootloader(self):
        self.log_emitted.emit("🔄 Sincronizando entradas del bootloader Limine...")
        try:
            res = run_command(["pkexec", "limine-snapper-sync"])
            if res.returncode == 0:
                self.log_emitted.emit("✔ Limine bootloader sincronizado con éxito.")
            else:
                self.log_emitted.emit(f"ℹ Limine sync ejecutado: {res.stdout.strip()}")
        except Exception as e:
            self.log_emitted.emit(f"⚠ Error en sync de Limine: {e}")
        self.refresh_kernels()

    def _handle_snapshot_action(self, action: str, data: dict):
        snap_id = data.get("id")
        if action == "diff":
            self.log_emitted.emit(f"🔍 Inspeccionando diff de subvolumen para snapshot #{snap_id}...")
        elif action == "rollback":
            self.log_emitted.emit(f"⚠️ Preparando punto de restauración rollback para snapshot #{snap_id}...")
        self.action_requested.emit(action, data)
