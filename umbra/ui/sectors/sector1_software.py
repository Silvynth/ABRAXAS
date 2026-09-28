#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS 2.0 | UMBRA - SECTOR 01: SOFTWARE & CENTRO DE UPDATES
#  Diseño de Alta Densidad Haute Horlogerie (Split 3:2)
# =====================================================================

import os
import re
import subprocess
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
    QPushButton, QScrollArea, QLineEdit, QSizePolicy, QToolTip,
    QDialog
)
from PySide6.QtCore import Qt, Signal, QTimer, QProcess, QThread
from PySide6.QtGui import QCursor, QPainter, QColor, QLinearGradient

from core.theme import MONOCHROME_PALETTE as P
from core.process import run_command


class CompactPackageRow(QFrame):
    """
    Fila ultra-compacta de alta densidad (24px) inspirada en instrumentación suiza.
    Incluye barra de llenado progresivo con haz de luz platino en tiempo real.
    """
    clicked = Signal(dict)

    def __init__(self, pkg_data: dict, parent=None):
        super().__init__(parent)
        self.pkg_data = pkg_data
        self.is_selected = False
        self.progress = 0.0
        self.status = "pending"  # "pending", "updating", "completed"
        self.init_ui()

    def init_ui(self):
        self.setFixedHeight(24)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self._apply_style()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 1, 6, 1)
        layout.setSpacing(8)

        # 1. Micro-Badge de Criticidad (Fijo 44px)
        prio = self.pkg_data.get("priority", 4)
        tag_map = {1: "CRIT", 2: "CORE", 3: "SUBS", 4: "APPS", 5: "AUR"}
        self.lbl_crit = QLabel(tag_map.get(prio, "APPS"))
        self.lbl_crit.setFixedWidth(44)
        self.lbl_crit.setAlignment(Qt.AlignCenter)

        if prio == 1:
            self.lbl_crit.setStyleSheet(f"color: #ffffff; background: rgba(255, 255, 255, 0.12); border: 1px solid {P['BORDER_STRONG']}; border-radius: 3px; font-size: 8px; font-weight: 800; font-family: 'JetBrains Mono', monospace;")
        elif prio == 2:
            self.lbl_crit.setStyleSheet(f"color: #e2e8f0; background: {P['BG_HIGHLIGHT']}; border: 1px solid {P['BORDER_MEDIUM']}; border-radius: 3px; font-size: 8px; font-weight: 700; font-family: 'JetBrains Mono', monospace;")
        elif prio == 5:
            self.lbl_crit.setStyleSheet(f"color: #9ca3af; background: rgba(255, 255, 255, 0.04); border: 1px solid {P['BORDER_SUBTLE']}; border-radius: 3px; font-size: 8px; font-weight: 700; font-family: 'JetBrains Mono', monospace;")
        else:
            self.lbl_crit.setStyleSheet(f"color: {P['TEXT_MUTED']}; border: 1px solid {P['BORDER_SUBTLE']}; border-radius: 3px; font-size: 8px; font-weight: 600; font-family: 'JetBrains Mono', monospace;")
        layout.addWidget(self.lbl_crit)

        # 2. Nombre del Paquete (Fijo 145px)
        self.lbl_name = QLabel(self.pkg_data.get("name", ""))
        self.lbl_name.setFixedWidth(145)
        self.lbl_name.setStyleSheet(f"color: {P['TEXT_TITLES']}; font-size: 11px; font-weight: 700; font-family: 'JetBrains Mono', monospace;")
        layout.addWidget(self.lbl_name)

        # 3. Transición de Versión (Expansible)
        self.old_v = self.pkg_data.get("old_version", "")
        self.new_v = self.pkg_data.get("new_version", "")
        self.lbl_vers = QLabel(f"<span style='color:{P['TEXT_MUTED']};'>{self.old_v}</span> <span style='color:{P['BORDER_MEDIUM']};'>➔</span> <span style='color:#ffffff; font-weight:700;'>{self.new_v}</span>")
        self.lbl_vers.setStyleSheet("font-size: 10px; font-family: 'JetBrains Mono', monospace;")
        layout.addWidget(self.lbl_vers, 1)

        # 4. Peso de Descarga (Fijo 75px)
        self.lbl_size = QLabel(self.pkg_data.get("size", "--"))
        self.lbl_size.setFixedWidth(75)
        self.lbl_size.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_size.setStyleSheet(f"color: {P['TEXT_BODY']}; font-size: 10px; font-family: 'JetBrains Mono', monospace;")
        layout.addWidget(self.lbl_size)

        # 5. Fecha de Lanzamiento (Fijo 75px)
        self.lbl_date = QLabel(self.pkg_data.get("date", "--"))
        self.lbl_date.setFixedWidth(75)
        self.lbl_date.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_date.setStyleSheet(f"color: {P['TEXT_MUTED']}; font-size: 9.5px; font-family: 'JetBrains Mono', monospace;")
        layout.addWidget(self.lbl_date)

    def _apply_style(self):
        if self.is_selected:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {P["ACCENT_PILL"]};
                    border: 1px solid {P["BORDER_STRONG"]};
                    border-radius: 4px;
                }}
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

    def set_selected(self, selected: bool):
        self.is_selected = selected
        self._apply_style()

    def set_progress(self, progress: float):
        self.progress = max(0.0, min(1.0, progress))
        self.update()

    def set_status(self, status: str):
        self.status = status
        if status == "completed":
            self.mark_completed()
        elif status == "updating":
            self.start_progressive_fill()
        self.update()

    def start_progressive_fill(self):
        """Inicia el barrido progresivo de cristal platino para este paquete."""
        self.status = "updating"
        self._target_progress = 0.95
        self.lbl_vers.setText(f"<span style='color:{P['TEXT_TITLES']};'>{self.old_v}</span> <span style='color:#ffffff;'>⟳</span> <span style='color:#ffffff; font-weight:700;'>{self.new_v}</span>")
        if not hasattr(self, "_anim_timer") or self._anim_timer is None:
            self._anim_timer = QTimer(self)
            self._anim_timer.setInterval(25)
            self._anim_timer.timeout.connect(self._step_internal_fill)
        if not self._anim_timer.isActive():
            self._anim_timer.start()

    def _step_internal_fill(self):
        if self.progress < getattr(self, "_target_progress", 0.95):
            self.progress = min(0.95, self.progress + 0.06)
            self.update()
        else:
            if hasattr(self, "_anim_timer") and self._anim_timer and self._anim_timer.isActive():
                self._anim_timer.stop()

    def mark_completed(self):
        """Consolida la fila como 100% actualizada con checkmark definitivo."""
        self.status = "completed"
        self.progress = 1.0
        if hasattr(self, "_anim_timer") and self._anim_timer and self._anim_timer.isActive():
            self._anim_timer.stop()
        self.lbl_vers.setText(f"<span style='color:{P['TEXT_MUTED']};'>{self.old_v}</span> <span style='color:#ffffff; font-weight:800;'>✔</span> <span style='color:#ffffff; font-weight:700;'>{self.new_v}</span>")
        self.lbl_crit.setStyleSheet(f"color: #ffffff; background: {P['ACCENT_PILL']}; border: 1px solid {P['BORDER_STRONG']}; border-radius: 3px; font-size: 8px; font-weight: 800; font-family: 'JetBrains Mono', monospace;")
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.progress > 0.0:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            w = int(self.width() * self.progress)
            h = self.height()

            if self.status == "completed":
                painter.fillRect(0, 0, self.width(), h, QColor(255, 255, 255, 14))
                painter.setPen(QColor(255, 255, 255, 40))
                painter.drawRect(0, 0, self.width() - 1, h - 1)
            else:
                grad = QLinearGradient(0, 0, w, 0)
                grad.setColorAt(0.0, QColor(255, 255, 255, 10))
                grad.setColorAt(0.7, QColor(255, 255, 255, 30))
                grad.setColorAt(1.0, QColor(255, 255, 255, 65))
                painter.fillRect(0, 0, w, h, grad)
                # Haz de luz conductor en el borde de avance
                painter.fillRect(max(0, w - 2), 0, 2, h, QColor(255, 255, 255, 220))
            painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.pkg_data)


class PasswordAuthDialog(QDialog):
    """
    Modal Haute Horlogerie de autenticación privilegiada (sudo).
    Diseño Obsidian Glass con verificación de contraseña previa a actualización.
    """
    def __init__(self, pkg_count: int, parent=None):
        super().__init__(parent)
        self.password = ""
        self.setWindowTitle("Autenticación Privilegiada")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(440)
        self.init_ui(pkg_count)

    def init_ui(self, pkg_count: int):
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

        lbl_tag = QLabel("◈ AUTENTICACIÓN PRIVILEGIADA // SUDO ROOT")
        lbl_tag.setStyleSheet(f"color: {P['TEXT_MICRO']}; font-size: 8.5px; font-weight: 800; letter-spacing: 1.2px; font-family: 'JetBrains Mono', monospace;")
        c_layout.addWidget(lbl_tag)

        lbl_title = QLabel("Confirmar Actualización de Sistema")
        lbl_title.setStyleSheet(f"color: {P['TEXT_TITLES']}; font-size: 15px; font-weight: 800;")
        c_layout.addWidget(lbl_title)

        lbl_sub = QLabel(
            f"Se aplicarán actualizaciones a {pkg_count} paquetes del sistema.\n"
            "Introduce tu contraseña de administrador para autorizar la operación:"
        )
        lbl_sub.setStyleSheet(f"color: {P['TEXT_BODY']}; font-size: 11px; line-height: 1.4;")
        lbl_sub.setWordWrap(True)
        c_layout.addWidget(lbl_sub)

        # Input de Contraseña
        self.txt_pass = QLineEdit()
        self.txt_pass.setEchoMode(QLineEdit.Password)
        self.txt_pass.setPlaceholderText("Contraseña de sudo...")
        self.txt_pass.setStyleSheet(f"""
            QLineEdit {{
                background-color: {P["BG_HIGHLIGHT"]};
                border: 1px solid {P["BORDER_MEDIUM"]};
                border-radius: 4px;
                color: #ffffff;
                font-family: 'JetBrains Mono', monospace;
                font-size: 12px;
                padding: 8px 10px;
            }}
            QLineEdit:focus {{
                border-color: #ffffff;
            }}
        """)
        self.txt_pass.returnPressed.connect(self._verify_and_accept)
        c_layout.addWidget(self.txt_pass)

        # Mensaje de Error
        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet("color: #ef4444; font-size: 10px; font-family: 'JetBrains Mono', monospace;")
        self.lbl_error.setVisible(False)
        c_layout.addWidget(self.lbl_error)

        # Botones
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

        btn_ok = QPushButton("⚡ AUTENTICAR Y ACTUALIZAR")
        btn_ok.setCursor(QCursor(Qt.PointingHandCursor))
        btn_ok.setStyleSheet(f"""
            QPushButton {{
                background-color: #ffffff;
                border: 1px solid #ffffff;
                border-radius: 4px;
                color: #0a0b0e;
                font-family: 'JetBrains Mono', monospace;
                font-size: 9.5px;
                font-weight: 800;
                padding: 7px 16px;
            }}
            QPushButton:hover {{
                background-color: #e2e8f0;
            }}
        """)
        btn_ok.clicked.connect(self._verify_and_accept)
        h_btns.addWidget(btn_ok)

        c_layout.addLayout(h_btns)
        layout.addWidget(card)

    def _verify_and_accept(self):
        pwd = self.txt_pass.text().strip()
        if not pwd:
            self.lbl_error.setText("⚠ La contraseña no puede estar vacía.")
            self.lbl_error.setVisible(True)
            return

        self.password = pwd
        self.accept()


class CheckUpdatesWorker(QThread):
    """Worker asíncrono para detección de actualizaciones pacman y AUR sin congelar la UI."""
    updates_ready = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        parsed = []
        try:
            res = run_command(["checkupdates"])
            if res.returncode == 0 and res.stdout.strip():
                for l in res.stdout.strip().split("\n"):
                    parts = l.split()
                    if len(parts) >= 4 and parts[2] == "->":
                        p_name = parts[0]
                        cur_v = parts[1]
                        new_v = parts[3]
                        prio, cat = Sector1SoftwareView._classify_package(p_name)
                        parsed.append({
                            "name": p_name,
                            "old_version": cur_v,
                            "new_version": new_v,
                            "priority": prio,
                            "category": cat,
                            "size": "--",
                            "date": "--",
                            "source": "repo"
                        })
        except Exception:
            pass

        if not parsed:
            try:
                res_q = run_command(["pacman", "-Qu"])
                if res_q.returncode == 0 and res_q.stdout.strip():
                    for l in res_q.stdout.strip().split("\n"):
                        parts = l.split()
                        if len(parts) >= 4 and parts[2] == "->":
                            p_name = parts[0]
                            cur_v = parts[1]
                            new_v = parts[3]
                            prio, cat = Sector1SoftwareView._classify_package(p_name)
                            parsed.append({
                                "name": p_name,
                                "old_version": cur_v,
                                "new_version": new_v,
                                "priority": prio,
                                "category": cat,
                                "size": "--",
                                "date": "--",
                                "source": "repo"
                            })
            except Exception:
                pass

        if not self._running:
            return

        try:
            aur_res = run_command(["yay", "-Qua"])
            if aur_res.returncode == 0 and aur_res.stdout.strip():
                for l in aur_res.stdout.strip().split("\n"):
                    parts = l.split()
                    if len(parts) >= 4 and parts[2] == "->":
                        p_name = parts[0]
                        cur_v = parts[1]
                        new_v = parts[3]
                        parsed.append({
                            "name": p_name,
                            "old_version": cur_v,
                            "new_version": new_v,
                            "priority": 5,
                            "category": "AUR (Arch User Repository)",
                            "size": "AUR Build",
                            "date": "Reciente",
                            "source": "aur"
                        })
        except Exception:
            pass

        if not self._running:
            return

        Sector1SoftwareView._enrich_metadata_batch(parsed)
        parsed.sort(key=lambda x: (x["priority"], x["name"]))
        self.updates_ready.emit(parsed)


class Sector1SoftwareView(QWidget):
    """
    SECTOR 01: SOFTWARE & CENTRO DE ACTUALIZACIONES
    Topología Dividida 3:2: Catálogo de paquetes a la izquierda, Acciones de Actualización e Inspector a la derecha.
    """
    log_emitted = Signal(str)
    action_requested = Signal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.packages_cache = []
        self.active_filter_prio = 0
        self.selected_row_widget = None
        self.rows_map = {}
        self.update_proc = None
        self.check_worker = None
        self.active_pkg_name = None
        self.pacman_pkg_regex = re.compile(
            r'\(\s*(\d+)/(\d+)\)\s+(?:actualizando|instalando|upgrading|installing|reinstalando|reinstalling)\s+([a-zA-Z0-9@._+-]+)',
            re.IGNORECASE
        )
        self.pacman_down_regex = re.compile(
            r'(?:descargando|downloading)\s+([a-zA-Z0-9@._+-]+)',
            re.IGNORECASE
        )
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(12)

        # =============================================================
        # COLUMNA 1 (IZQUIERDA - RATIO 3): CATÁLOGO DE ALTA DENSIDAD
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

        # Micro-tag & Título
        tag1 = QLabel("CATÁLOGO DE ACTUALIZACIONES // CACHYOS + AUR")
        tag1.setProperty("class", "sector_micro_tag")
        title1 = QLabel("📦 Paquetes Pendientes de Update")
        title1.setProperty("class", "sector_title")
        l1.addWidget(tag1)
        l1.addWidget(title1)

        # Fila de Filtros Tácticos por Criticidad
        r_filters = QHBoxLayout()
        r_filters.setSpacing(5)

        self.btn_f_all = QPushButton("TODOS (0)")
        self.btn_f_crit = QPushButton("◈ CRÍTICO (0)")
        self.btn_f_core = QPushButton("◈ CORE (0)")
        self.btn_f_subs = QPushButton("◈ SUBS (0)")
        self.btn_f_apps = QPushButton("◈ APPS (0)")
        self.btn_f_aur = QPushButton("◈ AUR (0)")

        self.filter_buttons = [self.btn_f_all, self.btn_f_crit, self.btn_f_core, self.btn_f_subs, self.btn_f_apps, self.btn_f_aur]
        for i, btn in enumerate(self.filter_buttons):
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.setCheckable(True)
            btn.setProperty("class", "cyber_btn_toggle")
            btn.clicked.connect(lambda _, idx=i: self._apply_filter(idx))
            r_filters.addWidget(btn)

        self.btn_f_all.setChecked(True)
        r_filters.addStretch()
        l1.addLayout(r_filters)

        # Entrada de Búsqueda Rápida
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Filtrar paquete por nombre...")
        self.txt_search.setProperty("class", "cyber_input")
        self.txt_search.textChanged.connect(self._filter_by_text)
        l1.addWidget(self.txt_search)

        # Cabecera Fija de Tabla
        h_table = QFrame()
        h_table.setFixedHeight(20)
        h_table.setStyleSheet(f"background: {P['BG_HIGHLIGHT']}; border-radius: 3px;")
        l_th = QHBoxLayout(h_table)
        l_th.setContentsMargins(6, 0, 6, 0)
        l_th.setSpacing(8)

        th_crit = QLabel("TIPO")
        th_crit.setFixedWidth(44)
        th_crit.setAlignment(Qt.AlignCenter)
        th_crit.setStyleSheet(f"color: {P['TEXT_MICRO']}; font-size: 8.5px; font-weight: 800; font-family: 'JetBrains Mono', monospace;")

        th_name = QLabel("PAQUETE")
        th_name.setFixedWidth(145)
        th_name.setStyleSheet(f"color: {P['TEXT_MICRO']}; font-size: 8.5px; font-weight: 800; font-family: 'JetBrains Mono', monospace;")

        th_ver = QLabel("TRANSICIÓN DE VERSIÓN")
        th_ver.setStyleSheet(f"color: {P['TEXT_MICRO']}; font-size: 8.5px; font-weight: 800; font-family: 'JetBrains Mono', monospace;")

        th_size = QLabel("PESO")
        th_size.setFixedWidth(75)
        th_size.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        th_size.setStyleSheet(f"color: {P['TEXT_MICRO']}; font-size: 8.5px; font-weight: 800; font-family: 'JetBrains Mono', monospace;")

        th_date = QLabel("FECHA")
        th_date.setFixedWidth(75)
        th_date.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        th_date.setStyleSheet(f"color: {P['TEXT_MICRO']}; font-size: 8.5px; font-weight: 800; font-family: 'JetBrains Mono', monospace;")

        l_th.addWidget(th_crit)
        l_th.addWidget(th_name)
        l_th.addWidget(th_ver, 1)
        l_th.addWidget(th_size)
        l_th.addWidget(th_date)
        l1.addWidget(h_table)

        # Lista de Filas Compactas (Scroll Area)
        self.scroll_pkgs = QScrollArea()
        self.scroll_pkgs.setWidgetResizable(True)
        self.scroll_pkgs.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.w_rows = QWidget()
        self.l_rows = QVBoxLayout(self.w_rows)
        self.l_rows.setContentsMargins(0, 0, 4, 0)
        self.l_rows.setSpacing(2)
        self.l_rows.addStretch()

        self.scroll_pkgs.setWidget(self.w_rows)
        l1.addWidget(self.scroll_pkgs, 1)

        main_layout.addWidget(col1, 3)

        # =============================================================
        # COLUMNA 2 (DERECHA - RATIO 2): ACCIONES & INSPECTOR
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
        l2.setSpacing(12)

        tag2 = QLabel("CONTROL DE ACTUALIZACIONES // OPERACIONES")
        tag2.setProperty("class", "sector_micro_tag")
        title2 = QLabel("⚡ Operaciones del Sistema")
        title2.setProperty("class", "sector_title")
        l2.addWidget(tag2)
        l2.addWidget(title2)

        # Panel de Acciones Tácticas
        card_actions = QFrame()
        card_actions.setStyleSheet(f"background: {P['BG_HIGHLIGHT']}; border: 1px solid {P['BORDER_SUBTLE']}; border-radius: 6px; padding: 10px;")
        l_act = QVBoxLayout(card_actions)
        l_act.setContentsMargins(10, 10, 10, 10)
        l_act.setSpacing(8)

        # Fila 1: Comprobar & Actualizar
        r_top_btns = QHBoxLayout()
        r_top_btns.setSpacing(8)

        self.btn_check = QPushButton("🔄 Comprobar Actualizaciones")
        self.btn_check.setProperty("class", "cyber_btn")
        self.btn_check.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_check.clicked.connect(self.check_updates)

        self.btn_update = QPushButton("⚡ Actualizar")
        self.btn_update.setProperty("class", "cyber_btn_primary")
        self.btn_update.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_update.clicked.connect(self.apply_updates)

        r_top_btns.addWidget(self.btn_check, 1)
        r_top_btns.addWidget(self.btn_update, 1)
        l_act.addLayout(r_top_btns)

        # Fila 2 (Justo debajo): Reiniciar en Rojo (Desactivado hasta completar actualización)
        self.btn_reboot = QPushButton("⏻ Reiniciar")
        self.btn_reboot.setEnabled(False)
        self.btn_reboot.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_reboot.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 82, 82, 0.08);
                color: #ff5252;
                border: 1px solid rgba(255, 82, 82, 0.35);
                border-radius: 6px;
                min-height: 28px;
                font-weight: 700;
                font-size: 11px;
                font-family: 'JetBrains Mono', monospace;
            }
            QPushButton:hover {
                background-color: rgba(255, 82, 82, 0.20);
                border-color: #ff5252;
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: #ff5252;
                color: #0a0b0e;
            }
            QPushButton:disabled {
                background-color: rgba(255, 255, 255, 0.02);
                border-color: rgba(255, 255, 255, 0.07);
                color: rgba(255, 255, 255, 0.2);
            }
        """)
        self.btn_reboot.clicked.connect(self.reboot_system)
        l_act.addWidget(self.btn_reboot)

        # Resumen de telemetría de paquetes
        self.lbl_stats_summary = QLabel("Sincronizando estado...")
        self.lbl_stats_summary.setStyleSheet(f"color: {P['TEXT_MUTED']}; font-size: 10px; font-family: 'JetBrains Mono', monospace; margin-top: 2px;")
        l_act.addWidget(self.lbl_stats_summary)

        l2.addWidget(card_actions)

        # Panel Inspector de Detalle (Nombre, Fecha de update, Peso, Categoría)
        card_inspector = QFrame()
        card_inspector.setStyleSheet(f"background: {P['BG_HIGHLIGHT']}; border: 1px solid {P['BORDER_SUBTLE']}; border-radius: 6px; padding: 12px;")
        l_insp = QVBoxLayout(card_inspector)
        l_insp.setContentsMargins(12, 10, 12, 10)
        l_insp.setSpacing(10)

        lbl_insp_t = QLabel("INSPECTOR DE PAQUETE // DETALLE")
        lbl_insp_t.setStyleSheet(f"color: {P['TEXT_MICRO']}; font-size: 8.5px; font-weight: 800; letter-spacing: 1.2px; font-family: 'JetBrains Mono', monospace;")
        l_insp.addWidget(lbl_insp_t)

        # 1. NOMBRE
        v_name = QVBoxLayout()
        v_name.setSpacing(2)
        lbl_t_n = QLabel("NOMBRE")
        lbl_t_n.setStyleSheet(f"color: {P['TEXT_MICRO']}; font-size: 8px; font-weight: 700; font-family: 'JetBrains Mono', monospace;")
        self.val_name = QLabel("Selecciona un paquete")
        self.val_name.setStyleSheet(f"color: {P['TEXT_TITLES']}; font-size: 13px; font-weight: 800; font-family: 'JetBrains Mono', monospace;")
        v_name.addWidget(lbl_t_n)
        v_name.addWidget(self.val_name)
        l_insp.addLayout(v_name)

        # 2. FECHA DE UPDATE
        v_date = QVBoxLayout()
        v_date.setSpacing(2)
        lbl_t_d = QLabel("FECHA DE UPDATE")
        lbl_t_d.setStyleSheet(f"color: {P['TEXT_MICRO']}; font-size: 8px; font-weight: 700; font-family: 'JetBrains Mono', monospace;")
        self.val_date = QLabel("--")
        self.val_date.setStyleSheet(f"color: {P['TEXT_BODY']}; font-size: 12px; font-family: 'JetBrains Mono', monospace;")
        v_date.addWidget(lbl_t_d)
        v_date.addWidget(self.val_date)
        l_insp.addLayout(v_date)

        # 3. PESO
        v_size = QVBoxLayout()
        v_size.setSpacing(2)
        lbl_t_s = QLabel("PESO")
        lbl_t_s.setStyleSheet(f"color: {P['TEXT_MICRO']}; font-size: 8px; font-weight: 700; font-family: 'JetBrains Mono', monospace;")
        self.val_size = QLabel("--")
        self.val_size.setStyleSheet(f"color: {P['TEXT_BODY']}; font-size: 12px; font-weight: 700; font-family: 'JetBrains Mono', monospace;")
        v_size.addWidget(lbl_t_s)
        v_size.addWidget(self.val_size)
        l_insp.addLayout(v_size)

        # 4. CATEGORÍA
        v_cat = QVBoxLayout()
        v_cat.setSpacing(2)
        lbl_t_c = QLabel("CATEGORÍA")
        lbl_t_c.setStyleSheet(f"color: {P['TEXT_MICRO']}; font-size: 8px; font-weight: 700; font-family: 'JetBrains Mono', monospace;")
        self.val_cat = QLabel("--")
        self.val_cat.setStyleSheet(f"color: {P['TEXT_TITLES']}; font-size: 11px; font-family: 'JetBrains Mono', monospace;")
        v_cat.addWidget(lbl_t_c)
        v_cat.addWidget(self.val_cat)
        l_insp.addLayout(v_cat)

        l_insp.addStretch()
        l2.addWidget(card_inspector, 1)

        main_layout.addWidget(col2, 2)

        # Sincronización inicial de paquetes
        self.check_updates()

    def check_updates(self):
        """
        Escanea mediante checkupdates y yay -Qua para paridad 1:1 total
        con el Status Ribbon (77 paquetes) de forma completamente asíncrona.
        """
        if self.check_worker and self.check_worker.isRunning():
            return

        self.log_emitted.emit("🔍 Comprobando actualizaciones en repositorios oficiales y AUR...")
        self.btn_check.setEnabled(False)
        self.btn_check.setText("⏳ Comprobando...")

        self.check_worker = CheckUpdatesWorker(self)
        self.check_worker.updates_ready.connect(self._on_updates_ready)
        self.check_worker.start()

    def _on_updates_ready(self, parsed: list[dict]):
        self.packages_cache = parsed

        # Actualizar contadores de botones de filtro
        counts = {0: len(parsed), 1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for p in parsed:
            counts[p.get("priority", 4)] += 1

        self.btn_f_all.setText(f"TODOS ({counts[0]})")
        self.btn_f_crit.setText(f"◈ CRÍTICO ({counts[1]})")
        self.btn_f_core.setText(f"◈ CORE ({counts[2]})")
        self.btn_f_subs.setText(f"◈ SUBS ({counts[3]})")
        self.btn_f_apps.setText(f"◈ APPS ({counts[4]})")
        self.btn_f_aur.setText(f"◈ AUR ({counts[5]})")

        self.lbl_stats_summary.setText(f"{counts[0]} paquetes pendientes · {counts[1]} críticos.")
        self.log_emitted.emit(f"✔ Comprobación completada: {counts[0]} paquetes detectados en total.")

        # Poblar lista compacta
        self._populate_rows(parsed)

        self.btn_check.setEnabled(True)
        self.btn_check.setText("🔄 Comprobar Actualizaciones")

    def teardown(self):
        """Detiene de forma limpia el worker de comprobación si está en ejecución."""
        if self.check_worker and self.check_worker.isRunning():
            self.check_worker.stop()
            if not self.check_worker.wait(150):
                self.check_worker.terminate()
                self.check_worker.wait(100)

    @staticmethod
    def _enrich_metadata_batch(packages: list[dict]):
        repo_pkgs = [p["name"] for p in packages if p.get("source") == "repo"]
        if not repo_pkgs:
            return
        try:
            res = run_command(["pacman", "-Si"] + repo_pkgs[:85])
            blocks = res.stdout.strip().split("\n\n")
            meta_map = {}
            for b in blocks:
                m = {}
                for line in b.strip().split("\n"):
                    if ":" in line:
                        k, v = line.split(":", 1)
                        m[k.strip().lower()] = v.strip()
                p_name = m.get("nombre")
                if p_name and p_name not in meta_map:
                    raw_date = m.get("fecha de creación", "--")
                    parts = raw_date.split()
                    cleaned = f"{parts[1]} {parts[2]} {parts[3]}" if len(parts) >= 4 else raw_date[:10]
                    meta_map[p_name] = {
                        "size": m.get("tamaño de la descarga", "--"),
                        "date": cleaned,
                    }

            for p in packages:
                if p["name"] in meta_map:
                    p["size"] = meta_map[p["name"]]["size"]
                    p["date"] = meta_map[p["name"]]["date"]
        except Exception:
            pass

    @staticmethod
    def _clean_date(full_date: str) -> str:
        parts = full_date.split()
        if len(parts) >= 4:
            return f"{parts[1]} {parts[2]} {parts[3]}"
        return full_date[:10]

    @staticmethod
    def _classify_package(name: str) -> tuple[int, str]:
        n = name.lower()
        if n.startswith(("linux-cachyos", "linux-", "linux")) or \
           any(k in n for k in ["nvidia", "ucode", "firmware", "limine", "mkinitcpio", "btrfs-progs", "vmlinuz", "dkms"]):
            return 1, "Kernel, Bootloader & Hardware"
        if any(k in n for k in ["systemd", "glibc", "util-linux", "coreutils", "openssl", "bubblewrap", "dbus", "pacman", "polkit", "sudo", "cachyos-settings", "bpf", "cpupower", "expat", "shadow", "pam"]):
            return 2, "Servicios Base & Seguridad"
        if any(k in n for k in ["pipewire", "wireplumber", "ffmpeg", "gstreamer", "gst-", "electron", "alsa", "fluidsynth", "openexr", "openjph", "lib", "mesa", "wayland", "xorg", "vulkan"]):
            return 3, "Runtimes, Audio & Video"
        return 4, "Software de Usuario"

    def _clear_rows(self):
        while self.l_rows.count() > 1:
            item = self.l_rows.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.rows_map = {}
        self.selected_row_widget = None

    def _populate_rows(self, packages: list[dict]):
        self._clear_rows()
        for p in packages:
            row = CompactPackageRow(p, self)
            row.clicked.connect(self._on_row_clicked)
            self.l_rows.insertWidget(self.l_rows.count() - 1, row)
            self.rows_map[p["name"]] = row

        if packages:
            first_row = self.rows_map[packages[0]["name"]]
            self._select_row(first_row, packages[0])

    def _on_row_clicked(self, pkg_data: dict):
        p_name = pkg_data.get("name")
        if p_name in self.rows_map:
            self._select_row(self.rows_map[p_name], pkg_data)

    def _select_row(self, row_widget: CompactPackageRow, pkg_data: dict):
        if self.selected_row_widget:
            self.selected_row_widget.set_selected(False)
        self.selected_row_widget = row_widget
        self.selected_row_widget.set_selected(True)

        # Actualizar Inspector de 4 datos exactos
        self.val_name.setText(pkg_data.get("name", "--"))
        self.val_date.setText(pkg_data.get("date", "--"))
        self.val_size.setText(pkg_data.get("size", "--"))
        self.val_cat.setText(pkg_data.get("category", "--"))

    def _apply_filter(self, filter_idx: int):
        self.active_filter_prio = filter_idx
        for i, btn in enumerate(self.filter_buttons):
            btn.setChecked(i == filter_idx)

        search_text = self.txt_search.text().strip().lower()
        for p in self.packages_cache:
            row = self.rows_map.get(p["name"])
            if not row:
                continue

            matches_prio = (filter_idx == 0) or (p["priority"] == filter_idx)
            matches_text = (not search_text) or (search_text in p["name"].lower())
            row.setVisible(matches_prio and matches_text)

    def _filter_by_text(self, text: str):
        search_text = text.strip().lower()
        for p in self.packages_cache:
            row = self.rows_map.get(p["name"])
            if not row:
                continue

            matches_prio = (self.active_filter_prio == 0) or (p["priority"] == self.active_filter_prio)
            matches_text = (not search_text) or (search_text in p["name"].lower())
            row.setVisible(matches_prio and matches_text)

    def apply_updates(self):
        """Ejecuta la actualización real de pacman en vivo vinculada al motor de animación progresiva."""
        if not self.packages_cache:
            self.log_emitted.emit("ℹ No hay paquetes pendientes de actualización.")
            return

        # 1. Diálogo de confirmación con password
        auth_dlg = PasswordAuthDialog(len(self.packages_cache), parent=self.window())
        if auth_dlg.exec() != QDialog.Accepted or not auth_dlg.password:
            self.log_emitted.emit("◈ Actualización cancelada por el usuario.")
            return

        user_password = auth_dlg.password

        # 2. Bloqueo táctico de controles mientras se ejecuta la transacción
        self.btn_update.setEnabled(False)
        self.btn_update.setText("⚡ Actualizando Sistema...")
        self.btn_check.setEnabled(False)
        self.btn_reboot.setEnabled(False)

        total_pkgs = len(self.packages_cache)
        self.log_emitted.emit(f"⚡ Autenticación verificada. Despachando 'sudo pacman -Syu --noconfirm' ({total_pkgs} paquetes)...")
        self.lbl_stats_summary.setText(f"Iniciando descarga y transacción ({total_pkgs} paquetes)...")

        self.active_pkg_name = None

        # 3. Iniciar QProcess asíncrono en segundo plano
        if self.update_proc:
            try:
                self.update_proc.terminate()
            except Exception:
                pass

        self.update_proc = QProcess(self)
        self.update_proc.readyReadStandardOutput.connect(self._on_proc_stdout)
        self.update_proc.readyReadStandardError.connect(self._on_proc_stderr)
        self.update_proc.finished.connect(self._on_proc_finished)

        # Iniciar sudo con flag -S para suministrar el password por stdin
        self.update_proc.start("sudo", ["-S", "-p", "", "pacman", "-Syu", "--noconfirm"])
        self.update_proc.write(f"{user_password}\n".encode())

    def _on_proc_stdout(self):
        if not self.update_proc:
            return
        raw_data = self.update_proc.readAllStandardOutput().data().decode("utf-8", errors="replace")
        lines = [l.strip() for l in raw_data.replace("\r", "\n").split("\n") if l.strip()]

        for line in lines:
            # Emitir a la terminal táctica de UMBRA
            self.log_emitted.emit(f"pacman: {line}")

            # 1. Detección de instalación / actualización de paquete en disco
            m = self.pacman_pkg_regex.search(line)
            if m:
                cur, tot, pkg_name = m.groups()
                cur_i = int(cur)
                tot_i = int(tot)

                # Si había un paquete anterior en curso, consolidar con checkmark
                if self.active_pkg_name and self.active_pkg_name != pkg_name:
                    old_row = self.rows_map.get(self.active_pkg_name)
                    if old_row:
                        old_row.mark_completed()

                self.active_pkg_name = pkg_name
                row = self.rows_map.get(pkg_name)
                if row:
                    row.start_progressive_fill()
                    self.scroll_pkgs.ensureWidgetVisible(row)

                self.lbl_stats_summary.setText(f"Actualizando ({cur_i}/{tot_i}): {pkg_name}...")
                continue

            # 2. Detección de fase de descarga
            m_down = self.pacman_down_regex.search(line)
            if m_down:
                raw_pkg = m_down.group(1).split("-")[0]
                row = self.rows_map.get(raw_pkg)
                if row and row.status == "pending":
                    row.status = "updating"
                    row.progress = 0.25
                    row.update()

    def _on_proc_stderr(self):
        if not self.update_proc:
            return
        raw_err = self.update_proc.readAllStandardError().data().decode("utf-8", errors="replace")
        lines = [l.strip() for l in raw_err.replace("\r", "\n").split("\n") if l.strip()]
        for line in lines:
            if not line.lower().startswith("[sudo]"):
                self.log_emitted.emit(f"pacman [stderr]: {line}")

    def _on_proc_finished(self, exit_code: int, exit_status):
        # Consolidar el último paquete activo
        if self.active_pkg_name:
            last_row = self.rows_map.get(self.active_pkg_name)
            if last_row:
                last_row.mark_completed()

        if exit_code == 0:
            # Marcar paquetes de repositorios oficiales como completados
            for p in self.packages_cache:
                if p.get("source") != "aur":
                    row = self.rows_map.get(p["name"])
                    if row:
                        row.mark_completed()

            # Revisar si existen paquetes de AUR pendientes
            aur_pkgs = [p["name"] for p in self.packages_cache if p.get("source") == "aur"]
            if aur_pkgs:
                self.log_emitted.emit(f"⚡ Repositorios oficiales actualizados. Procediendo con {len(aur_pkgs)} paquetes de AUR...")
                self._run_aur_updates(aur_pkgs)
            else:
                self._finalize_all_updates()
        else:
            self.log_emitted.emit(f"❌ La actualización de pacman finalizó con código de error {exit_code}.")
            self.lbl_stats_summary.setText(f"⚠ Error en la actualización (Código {exit_code})")
            self.btn_update.setEnabled(True)
            self.btn_update.setText("⚡ Reintentar Actualizar")
            self.btn_check.setEnabled(True)

    def _run_aur_updates(self, aur_pkgs: list[str]):
        """Lanza actualización de AUR vía yay como usuario sin root."""
        self.update_proc = QProcess(self)
        self.update_proc.readyReadStandardOutput.connect(self._on_proc_stdout)
        self.update_proc.readyReadStandardError.connect(self._on_proc_stderr)
        self.update_proc.finished.connect(lambda ec, es: self._finalize_all_updates())
        self.update_proc.start("yay", ["-S", "--noconfirm", *aur_pkgs])

    def _finalize_all_updates(self):
        for row in self.rows_map.values():
            row.mark_completed()

        total = len(self.packages_cache)
        self.log_emitted.emit(f"✔ Transacción completada: {total} paquetes actualizados exitosamente en el sistema.")
        self.log_emitted.emit("⏻ ATENCIÓN: El núcleo del sistema y librerías base requieren un reinicio para consolidar cambios.")
        self.btn_update.setText("✔ Sistema al día")
        self.btn_check.setEnabled(True)
        self.lbl_stats_summary.setText(f"✔ {total} paquetes al día · Reinicio del sistema requerido")

        # Habilitar el botón Reiniciar en rojo vivo de alta visibilidad
        self.btn_reboot.setEnabled(True)
        self.btn_reboot.setText("⏻ Reiniciar Sistema (Requerido)")
        self.btn_reboot.setStyleSheet("""
            QPushButton {
                background-color: rgba(239, 68, 68, 0.22);
                color: #ffffff;
                border: 1px solid #ef4444;
                border-radius: 6px;
                min-height: 28px;
                font-weight: 800;
                font-size: 11px;
                font-family: 'JetBrains Mono', monospace;
            }
            QPushButton:hover {
                background-color: #ef4444;
                color: #ffffff;
                border-color: #f87171;
            }
            QPushButton:pressed {
                background-color: #dc2626;
                color: #ffffff;
            }
        """)

        self.action_requested.emit("pacman_update_finished", {"packages_count": total})

    def reboot_system(self):
        """Dispara orden de reinicio del sistema."""
        self.log_emitted.emit("⚠️ Orden de reinicio del sistema solicitada.")
        try:
            run_command(["systemctl", "reboot"])
        except Exception:
            pass
        self.action_requested.emit("system_reboot", {})
