#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS 2.0 | UMBRA - STATUS RIBBON (THEME LINKED)
# =====================================================================

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame, 
    QProgressBar, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QTime, QDate, QTimer, QVariantAnimation, QEasingCurve
from PySide6.QtGui import QColor

from core.theme import MONOCHROME_PALETTE as P

class DayCycleFilament(QProgressBar):
    """Barra ultra-fina (3px) con animación fluida que mide el avance del día (24h)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTextVisible(False)
        self.setFixedHeight(3)
        self.setRange(0, 100)
        self.setStyleSheet(f"""
            QProgressBar {{
                background-color: {P["BG_HIGHLIGHT"]};
                border: none;
                border-radius: 1px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {P["TEXT_TITLES"]}, stop:1 {P["TEXT_MUTED"]});
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

class RibbonBay(QWidget):
    """Módulo individual para la cinta de estado."""
    def __init__(self, label: str, value_widget: QWidget, subtext_widget: QWidget, 
                 filament_widget: QWidget = None, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(2)

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
        layout.addWidget(value_widget)

        if filament_widget:
            layout.addWidget(filament_widget)

        layout.addWidget(subtext_widget)


class UmbraStatusRibbon(QFrame):
    """
    Sub-barra inferior de UMBRA (Cinta de Estado y Resiliencia):
    Enlazada a theme.py
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.setObjectName("umbra_status_ribbon")
        self.setStyleSheet(f"""
            QFrame#umbra_status_ribbon {{
                background-color: {P["BG_SURFACE"]};
                border: 1px solid {P["BORDER_SUBTLE"]};
                border-radius: 10px;
            }}
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 140))
        shadow.setOffset(0, 3)
        self.setGraphicsEffect(shadow)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 10, 16, 10)
        main_layout.setSpacing(14)

        def make_divider():
            div = QFrame()
            div.setFrameShape(QFrame.VLine)
            div.setStyleSheet(f"color: {P['BORDER_SUBTLE']}; max-width: 1px; margin: 4px 2px;")
            return div

        # 1. SEGUNDO CEREBRO: OBSIDIAN
        w_vault_val = QWidget()
        l_vv = QHBoxLayout(w_vault_val)
        l_vv.setContentsMargins(0, 0, 0, 0)
        l_vv.setSpacing(6)

        self.lbl_n96 = QLabel("N --")
        self.lbl_n96.setStyleSheet(f"""
            font-size: 18px;
            font-weight: 800;
            color: {P["TEXT_TITLES"]};
            font-family: 'JetBrains Mono', monospace;
        """)
        l_vv.addWidget(self.lbl_n96)

        badge_vault = QLabel("OBSIDIAN")
        badge_vault.setStyleSheet(f"""
            font-size: 9px;
            font-weight: 700;
            color: {P["TEXT_TITLES"]};
            background-color: {P["BG_HIGHLIGHT"]};
            border: 1px solid {P["BORDER_SUBTLE"]};
            border-radius: 4px;
            padding: 1px 6px;
        """)
        l_vv.addWidget(badge_vault)
        l_vv.addStretch()

        self.lbl_vault_sub = QLabel("Fichas Técnicas")
        self.lbl_vault_sub.setStyleSheet(f"font-size: 10px; font-weight: 500; color: {P['TEXT_MUTED']}; margin-top: 2px;")

        bay_vault = RibbonBay("S E G U N D O   C E R E B R O", w_vault_val, self.lbl_vault_sub)
        main_layout.addWidget(bay_vault)
        main_layout.addWidget(make_divider())

        # 2. SISTEMA & PAQUETES
        w_pkg_val = QWidget()
        l_pv = QHBoxLayout(w_pkg_val)
        l_pv.setContentsMargins(0, 0, 0, 0)
        l_pv.setSpacing(6)

        self.lbl_pkg_num = QLabel("SISTEMA AL DÍA")
        self.lbl_pkg_num.setStyleSheet(f"""
            font-size: 16px;
            font-weight: 800;
            color: {P["TEXT_TITLES"]};
            font-family: 'JetBrains Mono', monospace;
        """)
        l_pv.addWidget(self.lbl_pkg_num)

        self.badge_pkg = QLabel("● SINCRONIZADO")
        self.badge_pkg.setStyleSheet(f"""
            font-size: 9px;
            font-weight: 700;
            color: {P["TEXT_TITLES"]};
            background-color: {P["BG_HIGHLIGHT"]};
            border: 1px solid {P["BORDER_SUBTLE"]};
            border-radius: 4px;
            padding: 1px 6px;
        """)
        l_pv.addWidget(self.badge_pkg)
        l_pv.addStretch()

        self.lbl_pkg_sub = QLabel("CachyOS / Arch al día")
        self.lbl_pkg_sub.setStyleSheet(f"font-size: 10px; font-weight: 500; color: {P['TEXT_MUTED']}; margin-top: 2px;")

        bay_pkg = RibbonBay("S I S T E M A   &   P A Q U E T E S", w_pkg_val, self.lbl_pkg_sub)
        main_layout.addWidget(bay_pkg)
        main_layout.addWidget(make_divider())

        # 3. ESCUDO TEMPORAL BTRFS
        w_btrfs_val = QWidget()
        l_bv = QHBoxLayout(w_btrfs_val)
        l_bv.setContentsMargins(0, 0, 0, 0)
        l_bv.setSpacing(6)

        self.lbl_btrfs_num = QLabel("PUNTOS OK")
        self.lbl_btrfs_num.setStyleSheet(f"""
            font-size: 16px;
            font-weight: 800;
            color: {P["TEXT_TITLES"]};
            font-family: 'JetBrains Mono', monospace;
        """)
        l_bv.addWidget(self.lbl_btrfs_num)

        self.badge_btrfs = QLabel("✔ ARRANQUE LISTO")
        self.badge_btrfs.setStyleSheet(f"""
            font-size: 9px;
            font-weight: 700;
            color: {P["TEXT_TITLES"]};
            background-color: {P["BG_HIGHLIGHT"]};
            border: 1px solid {P["BORDER_SUBTLE"]};
            border-radius: 4px;
            padding: 1px 6px;
        """)
        l_bv.addWidget(self.badge_btrfs)
        l_bv.addStretch()

        self.lbl_btrfs_sub = QLabel("Limine Bootloader OK")
        self.lbl_btrfs_sub.setStyleSheet(f"font-size: 10px; font-weight: 500; color: {P['TEXT_MUTED']}; margin-top: 2px;")

        bay_btrfs = RibbonBay("E S C U D O   B T R F S", w_btrfs_val, self.lbl_btrfs_sub)
        main_layout.addWidget(bay_btrfs)
        main_layout.addWidget(make_divider())

        # 4. CICLO DIARIO & FECHA (24H)
        w_time_val = QWidget()
        l_tv = QHBoxLayout(w_time_val)
        l_tv.setContentsMargins(0, 0, 0, 0)
        l_tv.setSpacing(6)

        dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        now_date = QDate.currentDate()
        dia_nom = dias[now_date.dayOfWeek() - 1]
        mes_nom = meses[now_date.month() - 1]
        fecha_str = f"{dia_nom}, {now_date.day()} de {mes_nom}"

        self.lbl_date = QLabel(fecha_str)
        self.lbl_date.setStyleSheet(f"""
            font-size: 15px;
            font-weight: 700;
            color: {P["TEXT_TITLES"]};
            letter-spacing: 0.2px;
        """)
        l_tv.addWidget(self.lbl_date)

        self.badge_day_pct = QLabel("0%")
        self.badge_day_pct.setStyleSheet(f"""
            font-size: 9px;
            font-weight: 700;
            color: {P["TEXT_TITLES"]};
            background-color: {P["BG_HIGHLIGHT"]};
            border: 1px solid {P["BORDER_SUBTLE"]};
            border-radius: 4px;
            padding: 1px 6px;
        """)
        l_tv.addWidget(self.badge_day_pct)
        l_tv.addStretch()

        self.day_bar = DayCycleFilament()

        self.lbl_time_sub = QLabel("Muestreando ciclo diario...")
        self.lbl_time_sub.setStyleSheet(f"font-size: 10px; font-weight: 500; color: {P['TEXT_MUTED']}; margin-top: 2px;")

        bay_time = RibbonBay("C I C L O   D I A R I O   ( 2 4 H )", w_time_val, self.lbl_time_sub, self.day_bar)
        main_layout.addWidget(bay_time)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_day_progress)
        self.timer.start(5000)
        self._update_day_progress()

    def _update_day_progress(self):
        t = QTime.currentTime()
        msecs = t.msecsSinceStartOfDay()
        total_msecs = 86400 * 1000
        pct = max(0, min(100, int((msecs / total_msecs) * 100)))
        
        self.day_bar.setValue(pct)
        self.badge_day_pct.setText(f"{pct}%")

        rem_secs = 86400 - (msecs // 1000)
        rem_h = rem_secs // 3600
        rem_m = (rem_secs % 3600) // 60
        hora_str = t.toString("HH:mm")

        self.lbl_time_sub.setText(f"{hora_str} · {rem_h}h {rem_m}m para medianoche (00:00)")

    def update_ribbon(self, data: dict):
        if not data:
            return

        # 1. Obsidian
        vault_total = data.get("vault_total", 0)
        vault_today = data.get("vault_today", 0)
        self.lbl_n96.setText(f"N - {vault_total}")
        if vault_today > 0:
            today_str = f"{vault_today} Documentadas Hoy"
        else:
            today_str = "0 Nuevas Hoy"
        self.lbl_vault_sub.setText(f"{vault_total} Fichas Técnicas · {today_str}")

        # 2. Paquetes
        pkg_cnt = data.get("pkg_count", 0)
        pkg_summary = data.get("pkg_summary", "Sistema sincronizado")
        if pkg_cnt == 0:
            self.lbl_pkg_num.setText("SISTEMA AL DÍA")
            self.badge_pkg.setText("● SINCRONIZADO")
        else:
            self.lbl_pkg_num.setText(f"{pkg_cnt} PENDIENTE{'S' if pkg_cnt > 1 else ''}")
            self.badge_pkg.setText("● ACTUALIZACIÓN")
        self.lbl_pkg_sub.setText(pkg_summary)

        # 3. Btrfs
        snap_cnt = data.get("snap_count", 12)
        snap_desc = data.get("snap_desc", "Limine Bootloader OK")
        self.lbl_btrfs_num.setText(f"{snap_cnt} PUNTOS")
        self.lbl_btrfs_sub.setText(snap_desc)
