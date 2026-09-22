#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS | UMBRA - ADVANCED SECTORS DECK (ARTEMIS OPA PARITY)
# =====================================================================

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame, 
    QPushButton, QLineEdit, QStackedWidget, QScrollArea,
    QGraphicsDropShadowEffect, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QCursor

class SectorSwitcherPill(QFrame):
    """Selector de pestañas estilo cápsula táctica (Tab Switcher)."""
    def __init__(self, tab_names: list[str], on_change_callback, parent=None):
        super().__init__(parent)
        self.on_change_callback = on_change_callback
        self.buttons = []
        
        self.setStyleSheet("""
            SectorSwitcherPill {
                background-color: rgba(0, 0, 0, 0.40);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                padding: 2px;
            }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)

        for idx, name in enumerate(tab_names):
            btn = QPushButton(name)
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.clicked.connect(lambda _, i=idx: self._select_tab(i))
            layout.addWidget(btn)
            self.buttons.append(btn)

        self._update_styles(0)

    def _select_tab(self, index: int):
        self._update_styles(index)
        if self.on_change_callback:
            self.on_change_callback(index)

    def _update_styles(self, active_idx: int):
        for idx, btn in enumerate(self.buttons):
            if idx == active_idx:
                btn.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(99, 102, 241, 0.45), stop:1 rgba(168, 85, 247, 0.45));
                        border: 1px solid rgba(168, 85, 247, 0.60);
                        border-radius: 4px;
                        color: #ffffff;
                        font-size: 10px;
                        font-weight: 700;
                        padding: 3px 8px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background: transparent;
                        border: none;
                        color: rgba(255, 255, 255, 0.45);
                        font-size: 10px;
                        font-weight: 600;
                        padding: 3px 8px;
                    }
                    QPushButton:hover {
                        color: #ffffff;
                        background: rgba(255, 255, 255, 0.05);
                        border-radius: 4px;
                    }
                """)


class SectorHeader(QWidget):
    """Cabecera refinada de sector con micro-etiqueta y título."""
    def __init__(self, sector_num: str, title: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 2)
        layout.setSpacing(1)

        lbl_num = QLabel(sector_num)
        lbl_num.setStyleSheet("font-size: 9px; font-weight: 800; letter-spacing: 1.5px; color: rgba(255, 255, 255, 0.40); text-transform: uppercase;")
        layout.addWidget(lbl_num)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 13px; font-weight: 800; color: #ffffff; letter-spacing: 0.3px;")
        layout.addWidget(lbl_title)


class SectorCard(QFrame):
    """Contenedor de tarjeta de cristal obsidiana."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            SectorCard {
                background-color: rgba(18, 19, 26, 0.95);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
            }
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 3)
        self.setGraphicsEffect(shadow)


# =====================================================================
# SECTOR 1: 🛡️ RESILIENCIA BTRFS & SNAPSHOT SUITE (OPA 10_kernel.zsh)
# =====================================================================
class Sector1BtrfsView(SectorCard):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        # Header con Switcher Pill
        row_top = QHBoxLayout()
        row_top.setContentsMargins(0, 0, 0, 0)
        row_top.addWidget(SectorHeader("SECTOR 01 // RESILIENCIA", "🛡️ Escudo Btrfs & Limine"))
        row_top.addStretch()
        
        self.switcher = SectorSwitcherPill(["📸 Snapshots", "🐧 Kernels & Boot"], self._on_tab_changed)
        row_top.addWidget(self.switcher)
        layout.addLayout(row_top)

        # Stack de sub-vistas
        self.stack = QStackedWidget(self)

        # Sub-vista 1: Snapshots & Rollback
        self.view_snapshots = self._build_snapshots_subview()
        self.stack.addWidget(self.view_snapshots)

        # Sub-vista 2: Kernels & Bootloader Limine
        self.view_kernels = self._build_kernels_subview()
        self.stack.addWidget(self.view_kernels)

        layout.addWidget(self.stack, 1)

    def _on_tab_changed(self, idx: int):
        self.stack.setCurrentIndex(idx)

    def _build_snapshots_subview(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(8)

        # Mini form creación
        box_create = QFrame()
        box_create.setStyleSheet("background: rgba(255, 255, 255, 0.025); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 6px; padding: 4px;")
        l_c = QHBoxLayout(box_create)
        l_c.setContentsMargins(6, 4, 6, 4)
        l_c.setSpacing(6)

        inp = QLineEdit()
        inp.setPlaceholderText("Bautizar nuevo punto de restauración...")
        inp.setStyleSheet("background: rgba(0, 0, 0, 0.35); border: 1px solid rgba(255, 255, 255, 0.10); border-radius: 4px; padding: 5px 8px; color: #ffffff; font-size: 10px;")
        l_c.addWidget(inp, 1)

        btn_new = QPushButton("📸 Crear")
        btn_new.setCursor(QCursor(Qt.PointingHandCursor))
        btn_new.setStyleSheet("background: #6366f1; border: none; border-radius: 4px; color: #ffffff; font-size: 10px; font-weight: 700; padding: 5px 10px;")
        l_c.addWidget(btn_new)
        l.addWidget(box_create)

        # Lista de Snapshots con paridad OPA
        lbl_snaps = QLabel("TIMELINE DE SNAPSHOTS (BTRFS / SNAPPER)")
        lbl_snaps.setStyleSheet("font-size: 9px; font-weight: 700; color: rgba(255, 255, 255, 0.40); letter-spacing: 0.8px;")
        l.addWidget(lbl_snaps)

        items = [
            ("#12", "Pre-Update Kernel 7.2.6", "Hoy 17:59", "ARRANQUE LISTO", "#10b981"),
            ("#11", "Hestia TTS & Abraxas v1.0.0", "Hoy 14:20", "ESTABLE", "#38bdf8"),
            ("#10", "Snapper Timeline Automático", "Ayer 23:00", "HORARIO", "#94a3b8"),
            ("#09", "Configuración Limine Boot", "Ayer 18:30", "SISTEMA", "#a855f7"),
        ]

        for num, desc, fecha, tag_t, tag_c in items:
            card = QFrame()
            card.setStyleSheet("background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.04); border-radius: 6px; padding: 4px;")
            l_item = QHBoxLayout(card)
            l_item.setContentsMargins(6, 4, 6, 4)
            l_item.setSpacing(6)

            lbl_id = QLabel(num)
            lbl_id.setStyleSheet("font-size: 11px; font-weight: 800; color: #818cf8; font-family: monospace;")
            l_item.addWidget(lbl_id)

            l_meta = QVBoxLayout()
            l_meta.setSpacing(1)
            lbl_d = QLabel(desc)
            lbl_d.setStyleSheet("font-size: 10px; font-weight: 600; color: #e2e8f0;")
            lbl_f = QLabel(fecha)
            lbl_f.setStyleSheet("font-size: 8px; color: rgba(255, 255, 255, 0.40);")
            l_meta.addWidget(lbl_d)
            l_meta.addWidget(lbl_f)
            l_item.addLayout(l_meta, 1)

            lbl_tag = QLabel(tag_t)
            lbl_tag.setStyleSheet(f"font-size: 8px; font-weight: 700; color: {tag_c}; background: rgba(255, 255, 255, 0.05); padding: 2px 5px; border-radius: 3px;")
            l_item.addWidget(lbl_tag)
            l.addWidget(card)

        l.addStretch()

        # Acciones de Rollback y Diff
        row_act = QHBoxLayout()
        row_act.setSpacing(6)
        btn_diff = QPushButton("⚖️ Ver Diff")
        btn_diff.setStyleSheet("background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.10); border-radius: 4px; color: #c7d2fe; font-size: 9px; font-weight: 600; padding: 4px 6px;")
        btn_prune = QPushButton("🧹 Purgar (<10)")
        btn_prune.setStyleSheet("background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.10); border-radius: 4px; color: #c7d2fe; font-size: 9px; font-weight: 600; padding: 4px 6px;")
        btn_roll = QPushButton("🔄 Rollback @")
        btn_roll.setStyleSheet("background: rgba(239, 68, 68, 0.20); border: 1px solid rgba(239, 68, 68, 0.40); border-radius: 4px; color: #fca5a5; font-size: 9px; font-weight: 700; padding: 4px 8px;")
        row_act.addWidget(btn_diff)
        row_act.addWidget(btn_prune)
        row_act.addWidget(btn_roll)
        l.addLayout(row_act)

        return w

    def _build_kernels_subview(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(8)

        # Kernel en Ejecución
        card_k = QFrame()
        card_k.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(99, 102, 241, 0.15), stop:1 rgba(168, 85, 247, 0.15)); border: 1px solid rgba(99, 102, 241, 0.35); border-radius: 6px; padding: 6px;")
        l_k = QVBoxLayout(card_k)
        l_k.setContentsMargins(6, 6, 6, 6)
        l_k.setSpacing(3)

        lbl_kt = QLabel("KERNEL ACTIVO EN ARRANQUE")
        lbl_kt.setStyleSheet("font-size: 8px; font-weight: 800; color: #a5b4fc; letter-spacing: 0.8px;")
        l_k.addWidget(lbl_kt)

        lbl_kn = QLabel("linux-cachyos 7.2.6-1")
        lbl_kn.setStyleSheet("font-size: 13px; font-weight: 800; color: #ffffff; font-family: monospace;")
        l_k.addWidget(lbl_kn)

        lbl_ks = QLabel("Bore Scheduler · LTO Clang · x86-64-v3 · Limine Ready")
        lbl_ks.setStyleSheet("font-size: 9px; color: rgba(255, 255, 255, 0.60);")
        l_k.addWidget(lbl_ks)
        l.addWidget(card_k)

        # Kernels de Respaldo en Disco
        lbl_bk = QLabel("KERNELS INSTALADOS EN /BOOT")
        lbl_bk.setStyleSheet("font-size: 9px; font-weight: 700; color: rgba(255, 255, 255, 0.40); letter-spacing: 0.8px;")
        l.addWidget(lbl_bk)

        kernels_boot = [
            ("linux-zen 6.12.9-zen1", "Gaming & Low Latency", "Activar"),
            ("linux-lts 6.6.70-lts", "Rescate Long Term Support", "Activar")
        ]

        for kname, kdesc, btn_txt in kernels_boot:
            card_kb = QFrame()
            card_kb.setStyleSheet("background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.04); border-radius: 6px; padding: 5px;")
            l_kb = QHBoxLayout(card_kb)
            l_kb.setContentsMargins(6, 3, 6, 3)
            l_kb.setSpacing(6)

            l_kbi = QVBoxLayout()
            l_kbi.setSpacing(1)
            lbl_n = QLabel(kname)
            lbl_n.setStyleSheet("font-size: 10px; font-weight: 700; color: #e2e8f0; font-family: monospace;")
            lbl_d = QLabel(kdesc)
            lbl_d.setStyleSheet("font-size: 8px; color: rgba(255, 255, 255, 0.45);")
            l_kbi.addWidget(lbl_n)
            l_kbi.addWidget(lbl_d)
            l_kb.addLayout(l_kbi, 1)

            b_act = QPushButton(btn_txt)
            b_act.setStyleSheet("background: rgba(255, 255, 255, 0.06); border: 1px solid rgba(255, 255, 255, 0.10); border-radius: 4px; color: #ffffff; font-size: 8px; padding: 3px 6px;")
            l_kb.addWidget(b_act)
            l.addWidget(card_kb)

        l.addStretch()

        # Botón de Sincronización Limine
        btn_lim = QPushButton("🔄 Re-sincronizar y Re-firmar Limine Bootloader")
        btn_lim.setCursor(QCursor(Qt.PointingHandCursor))
        btn_lim.setStyleSheet("background: rgba(56, 189, 248, 0.15); border: 1px solid rgba(56, 189, 248, 0.35); border-radius: 5px; color: #7dd3fc; font-size: 9px; font-weight: 700; padding: 6px 8px;")
        l.addWidget(btn_lim)

        return w


# =====================================================================
# SECTOR 2: 📦 CENTRO DE ACTUALIZACIONES & PAQUETES (OPA 03_system.zsh)
# =====================================================================
class Sector2UpdatesView(SectorCard):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        # Header con Switcher Pill
        row_top = QHBoxLayout()
        row_top.setContentsMargins(0, 0, 0, 0)
        row_top.addWidget(SectorHeader("SECTOR 02 // SOFTWARE", "📦 Centro de Actualizaciones"))
        row_top.addStretch()
        
        self.switcher = SectorSwitcherPill(["📋 Pendientes", "🛡️ Auditoría & Dry-Run"], self._on_tab_changed)
        row_top.addWidget(self.switcher)
        layout.addLayout(row_top)

        self.stack = QStackedWidget(self)
        self.view_pending = self._build_pending_subview()
        self.stack.addWidget(self.view_pending)

        self.view_audit = self._build_audit_subview()
        self.stack.addWidget(self.view_audit)

        layout.addWidget(self.stack, 1)

    def _on_tab_changed(self, idx: int):
        self.stack.setCurrentIndex(idx)

    def _build_pending_subview(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(8)

        # Resumen superior
        box_stat = QFrame()
        box_stat.setStyleSheet("background: rgba(245, 158, 11, 0.08); border: 1px solid rgba(245, 158, 11, 0.25); border-radius: 6px; padding: 6px;")
        l_st = QHBoxLayout(box_stat)
        l_st.setContentsMargins(8, 4, 8, 4)
        
        lbl_cnt = QLabel("<b>1 Paquete Pendiente</b> · Descarga: ~1.2 MB")
        lbl_cnt.setStyleSheet("font-size: 10px; color: #fde68a;")
        l_st.addWidget(lbl_cnt)
        l_st.addStretch()

        badge_sync = QLabel("● CACHYOS AL DÍA")
        badge_sync.setStyleSheet("font-size: 8px; font-weight: 700; color: #10b981; background: rgba(16, 185, 129, 0.15); border-radius: 3px; padding: 1px 5px;")
        l_st.addWidget(badge_sync)
        l.addWidget(box_stat)

        # Lista de paquetes pendientes
        lbl_tb_tag = QLabel("LISTA COMPARATIVA DE VERSIONES (checkupdates)")
        lbl_tb_tag.setStyleSheet("font-size: 9px; font-weight: 700; color: rgba(255, 255, 255, 0.40); letter-spacing: 0.8px;")
        l.addWidget(lbl_tb_tag)

        packages = [
            ("pcsclite", "2.5.1-1", "2.5.2-1", "cachyos-v3", "Bibliotecas PCSC SmartCard"),
            ("cachyos-keyring", "202609-1", "202609-2", "cachyos", "Claves GPG de repositorios")
        ]

        for pkg, cur_v, new_v, repo, p_desc in packages:
            card_p = QFrame()
            card_p.setStyleSheet("background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.04); border-radius: 6px; padding: 6px;")
            l_p = QVBoxLayout(card_p)
            l_p.setContentsMargins(6, 4, 6, 4)
            l_p.setSpacing(2)

            row1 = QHBoxLayout()
            row1.setContentsMargins(0, 0, 0, 0)
            lbl_name = QLabel(f"<b>{pkg}</b>")
            lbl_name.setStyleSheet("font-size: 11px; color: #ffffff; font-family: monospace;")
            row1.addWidget(lbl_name)

            row1.addStretch()
            lbl_repo = QLabel(repo)
            lbl_repo.setStyleSheet("font-size: 8px; color: #a855f7; background: rgba(168, 85, 247, 0.15); padding: 1px 4px; border-radius: 3px;")
            row1.addWidget(lbl_repo)
            l_p.addLayout(row1)

            row2 = QHBoxLayout()
            lbl_diff = QLabel(f"<font color='#94a3b8'>{cur_v}</font>  →  <font color='#34d399'><b>{new_v}</b></font>")
            lbl_diff.setStyleSheet("font-size: 9px; font-family: monospace;")
            row2.addWidget(lbl_diff)
            row2.addStretch()
            l_p.addLayout(row2)

            lbl_subdesc = QLabel(p_desc)
            lbl_subdesc.setStyleSheet("font-size: 8px; color: rgba(255, 255, 255, 0.40);")
            l_p.addWidget(lbl_subdesc)

            l.addWidget(card_p)

        l.addStretch()

        # Botón de Actualización con Snapshot Previo
        btn_up = QPushButton("🚀 Actualizar con Snapshot Previo Automático")
        btn_up.setCursor(QCursor(Qt.PointingHandCursor))
        btn_up.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(99, 102, 241, 0.35), stop:1 rgba(168, 85, 247, 0.35));
                border: 1px solid rgba(168, 85, 247, 0.60);
                border-radius: 6px;
                color: #ffffff;
                font-size: 10px;
                font-weight: 700;
                padding: 6px 10px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(99, 102, 241, 0.50), stop:1 rgba(168, 85, 247, 0.50));
            }
        """)
        l.addWidget(btn_up)

        return w

    def _build_audit_subview(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(8)

        # Tarjeta de Auditoría Preventiva
        card_risk = QFrame()
        card_risk.setStyleSheet("background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.25); border-radius: 6px; padding: 8px;")
        l_r = QVBoxLayout(card_risk)
        l_r.setContentsMargins(6, 6, 6, 6)
        l_r.setSpacing(3)

        lbl_rt = QLabel("EVALUACIÓN PREVENTIVA DE IMPACTO")
        lbl_rt.setStyleSheet("font-size: 8px; font-weight: 800; color: #6ee7b7; letter-spacing: 0.8px;")
        l_r.addWidget(lbl_rt)

        lbl_rs = QLabel("NIVEL DE RIESGO: <font color='#10b981'><b>NULO / SEGURO</b></font>")
        lbl_rs.setStyleSheet("font-size: 11px; font-weight: 700; color: #ffffff;")
        l_r.addWidget(lbl_rs)

        lbl_rd = QLabel("• Cero conflictos con drivers NVIDIA 570.xx<br>• Cero impacto en arranque o módulos del kernel<br>• No requiere reinicio de estación")
        lbl_rd.setStyleSheet("font-size: 9px; color: rgba(255, 255, 255, 0.70); line-height: 1.3;")
        l_r.addWidget(lbl_rd)
        l.addWidget(card_risk)

        # Estado de Mirrors y Conectividad
        box_mirror = QFrame()
        box_mirror.setStyleSheet("background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.04); border-radius: 6px; padding: 6px;")
        l_m = QVBoxLayout(box_mirror)
        l_m.setContentsMargins(6, 4, 6, 4)
        l_m.setSpacing(2)

        lbl_mt = QLabel("VELOCIDAD DE REPOSITORIOS (MIRRORS)")
        lbl_mt.setStyleSheet("font-size: 8px; font-weight: 700; color: rgba(255, 255, 255, 0.40);")
        l_m.addWidget(lbl_mt)

        lbl_mn = QLabel("cachyos.org · Latencia: <font color='#10b981'><b>12 ms</b></font> (Sincronizado)")
        lbl_mn.setStyleSheet("font-size: 9px; color: #e2e8f0;")
        l_m.addWidget(lbl_mn)
        l.addWidget(box_mirror)

        l.addStretch()

        btn_dry = QPushButton("🔍 Simular Actualización Dry-Run (pacman -Syup)")
        btn_dry.setStyleSheet("background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 5px; color: #ffffff; font-size: 9px; font-weight: 600; padding: 6px 8px;")
        l.addWidget(btn_dry)

        return w


# =====================================================================
# SECTOR 3: 🧹 STORAGE INSPECTOR & HIGIENE SRE (OPA 11_storage + 03_system)
# =====================================================================
class Sector3MaintenanceView(SectorCard):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        # Header con Switcher Pill
        row_top = QHBoxLayout()
        row_top.setContentsMargins(0, 0, 0, 0)
        row_top.addWidget(SectorHeader("SECTOR 03 // HIGIENE", "🧹 Storage & Mantenimiento"))
        row_top.addStretch()
        
        self.switcher = SectorSwitcherPill(["💾 Storage & Steam", "⚡ Purga & Daemons"], self._on_tab_changed)
        row_top.addWidget(self.switcher)
        layout.addLayout(row_top)

        self.stack = QStackedWidget(self)
        self.view_storage = self._build_storage_subview()
        self.stack.addWidget(self.view_storage)

        self.view_clean = self._build_clean_subview()
        self.stack.addWidget(self.view_clean)

        layout.addWidget(self.stack, 1)

    def _on_tab_changed(self, idx: int):
        self.stack.setCurrentIndex(idx)

    def _build_storage_subview(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(8)

        # Desglose de Subvolúmenes Btrfs
        lbl_subv = QLabel("SUBVOLÚMENES BTRFS RAÍZ")
        lbl_subv.setStyleSheet("font-size: 9px; font-weight: 700; color: rgba(255, 255, 255, 0.40); letter-spacing: 0.8px;")
        l.addWidget(lbl_subv)

        subvols = [
            ("@ (Sistema Raíz /)", "24.2 GB", "9%"),
            ("@home (Datos Silvynth)", "142.8 GB", "28%"),
            ("@snapshots (12 Puntos)", "18.4 GB", "4%")
        ]

        for s_name, s_size, s_pct in subvols:
            card_s = QFrame()
            card_s.setStyleSheet("background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.04); border-radius: 5px; padding: 4px;")
            l_s = QHBoxLayout(card_s)
            l_s.setContentsMargins(6, 3, 6, 3)
            
            lbl_sn = QLabel(s_name)
            lbl_sn.setStyleSheet("font-size: 10px; color: #cbd5e1; font-family: monospace;")
            l_s.addWidget(lbl_sn)

            l_s.addStretch()
            lbl_sz = QLabel(f"<b>{s_size}</b> ({s_pct})")
            lbl_sz.setStyleSheet("font-size: 9px; color: #38bdf8;")
            l_s.addWidget(lbl_sz)
            l.addWidget(card_s)

        # Inspector de Steam & Gaming
        lbl_stm = QLabel("BIBLIOTECA STEAM & SHADERS (yorha_storage_steam)")
        lbl_stm.setStyleSheet("font-size: 9px; font-weight: 700; color: rgba(255, 255, 255, 0.40); letter-spacing: 0.8px; margin-top: 2px;")
        l.addWidget(lbl_stm)

        steam_items = [
            ("Juegos Instalados", "110 GB", "#ffffff"),
            ("Compatdata & Proton Prefixes", "14.2 GB", "#fbbf24"),
            ("Shader Pre-Cache", "3.8 GB", "#a855f7")
        ]

        for st_name, st_size, st_col in steam_items:
            card_st = QFrame()
            card_st.setStyleSheet("background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.04); border-radius: 5px; padding: 3px;")
            l_st = QHBoxLayout(card_st)
            l_st.setContentsMargins(6, 2, 6, 2)
            
            lbl_stn = QLabel(st_name)
            lbl_stn.setStyleSheet("font-size: 9px; color: #cbd5e1;")
            l_st.addWidget(lbl_stn)

            l_st.addStretch()
            lbl_sts = QLabel(f"<b>{st_size}</b>")
            lbl_sts.setStyleSheet(f"font-size: 9px; color: {st_col};")
            l_st.addWidget(lbl_sts)
            l.addWidget(card_st)

        l.addStretch()

        btn_scan_big = QPushButton("📦 Rastrear Archivos Gigantes >1GB en $HOME")
        btn_scan_big.setStyleSheet("background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.10); border-radius: 5px; color: #e2e8f0; font-size: 9px; font-weight: 600; padding: 5px 8px;")
        l.addWidget(btn_scan_big)

        return w

    def _build_clean_subview(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(8)

        # Módulos de limpieza táctica
        lbl_pur = QLabel("MÓDULOS DE RECLAMACIÓN RÁPIDA")
        lbl_pur.setStyleSheet("font-size: 9px; font-weight: 700; color: rgba(255, 255, 255, 0.40); letter-spacing: 0.8px;")
        l.addWidget(lbl_pur)

        purge_modules = [
            ("Journalctl Logs", "742 MB ocupados", "Limpiar (<50M)", "#f59e0b"),
            ("Paquetes Huérfanos", "0 huérfanos (Limpio)", "Optimizado", "#10b981"),
            ("Caché Pacman (pkg)", "1.4 GB en /var/cache", "Trim Cache", "#38bdf8")
        ]

        for p_name, p_sub, p_btn, p_col in purge_modules:
            card_pm = QFrame()
            card_pm.setStyleSheet("background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.04); border-radius: 5px; padding: 4px;")
            l_pm = QHBoxLayout(card_pm)
            l_pm.setContentsMargins(6, 3, 6, 3)

            l_pmi = QVBoxLayout()
            l_pmi.setSpacing(1)
            lbl_pmn = QLabel(p_name)
            lbl_pmn.setStyleSheet("font-size: 10px; font-weight: 700; color: #e2e8f0;")
            lbl_pms = QLabel(p_sub)
            lbl_pms.setStyleSheet(f"font-size: 8px; color: {p_col};")
            l_pmi.addWidget(lbl_pmn)
            l_pmi.addWidget(lbl_pms)
            l_pm.addLayout(l_pmi, 1)

            btn_act = QPushButton(p_btn)
            btn_act.setStyleSheet("background: rgba(255, 255, 255, 0.06); border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 4px; color: #ffffff; font-size: 8px; font-weight: 600; padding: 3px 6px;")
            l_pm.addWidget(btn_act)
            l.addWidget(card_pm)

        # Estado de Daemons Vitales
        lbl_dm = QLabel("ESTADO DE SERVICIOS VITALES (SYSTEMD)")
        lbl_dm.setStyleSheet("font-size: 9px; font-weight: 700; color: rgba(255, 255, 255, 0.40); letter-spacing: 0.8px; margin-top: 2px;")
        l.addWidget(lbl_dm)

        box_d = QFrame()
        box_d.setStyleSheet("background: rgba(0, 0, 0, 0.25); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 5px;")
        l_d = QVBoxLayout(box_d)
        l_d.setContentsMargins(6, 4, 6, 4)
        l_d.setSpacing(3)

        daemons = [
            ("docker.service", "● ACTIVO (3 Contenedores)", "#10b981"),
            ("ollama.service", "● ACTIVO (Qwen 2.5)", "#10b981"),
            ("snapper-cleanup.timer", "● ACTIVO (Diario)", "#38bdf8"),
            ("postgresql.service", "○ STANDBY", "rgba(255, 255, 255, 0.40)")
        ]

        for d_n, d_s, d_c in daemons:
            row_d = QHBoxLayout()
            row_d.setContentsMargins(0, 0, 0, 0)
            lbl_dn = QLabel(d_n)
            lbl_dn.setStyleSheet("font-size: 9px; font-family: monospace; color: #cbd5e1;")
            row_d.addWidget(lbl_dn)
            row_d.addStretch()
            lbl_ds = QLabel(d_s)
            lbl_ds.setStyleSheet(f"font-size: 8px; font-weight: 700; color: {d_c};")
            row_d.addWidget(lbl_ds)
            l_d.addLayout(row_d)

        l.addWidget(box_d)
        l.addStretch()

        btn_all_purge = QPushButton("⚡ Purga Táctica Global (Recuperar ~2.1 GB)")
        btn_all_purge.setCursor(QCursor(Qt.PointingHandCursor))
        btn_all_purge.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(16, 185, 129, 0.25), stop:1 rgba(6, 182, 212, 0.25));
                border: 1px solid rgba(16, 185, 129, 0.50);
                border-radius: 5px;
                color: #a7f3d0;
                font-size: 9px;
                font-weight: 700;
                padding: 6px 8px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(16, 185, 129, 0.40), stop:1 rgba(6, 182, 212, 0.40));
            }
        """)
        l.addWidget(btn_all_purge)

        return w


# =====================================================================
# CONTENEDOR PRINCIPAL DE LOS 3 SECTORES EN COLUMNAS
# =====================================================================
class UmbraSectorsDeck(QWidget):
    """Contenedor de 3 columnas de cristal obsidiana con pestañas de OPA."""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Columna 1: Resiliencia & Kernels
        self.sector1 = Sector1BtrfsView(self)
        layout.addWidget(self.sector1, 1)

        # Columna 2: Actualizaciones & Auditoría
        self.sector2 = Sector2UpdatesView(self)
        layout.addWidget(self.sector2, 1)

        # Columna 3: Storage & Mantenimiento
        self.sector3 = Sector3MaintenanceView(self)
        layout.addWidget(self.sector3, 1)
