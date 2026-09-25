"""
❖ ABRAXAS 2.0 | Lumen UI: HUD Superior del Proyecto (Dual-Deck Mission Control)
Panel superior dividido en 2:
- Izquierda: Visor del Proyecto, Rama, Remoto, Entorno, Docker, Hora y Git HUD.
- Derecha: Telemetría de Hardware en vivo (CPU, GPU, RAM, Red con barras de uso y temperatura).
Estética Haute Horlogerie monocromática de ultra-precisión.
"""

from datetime import datetime
from pathlib import Path
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, 
    QProgressBar, QGridLayout, QWidget, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer, QThread, QVariantAnimation, QEasingCurve, QUrl
from PySide6.QtGui import QDesktopServices, QCursor

from lumen.models.project import Project
from core.lumen_sync import get_full_project_sync
from core.umbra_backend import UmbraHardwareCollector


class TelemetryFilamentBar(QProgressBar):
    """Barra filamento de precisión (4px) con animación fluida analógica."""
    
    def __init__(self, color_start: str = "#64748b", color_end: str = "#cbd5e1", parent=None):
        super().__init__(parent)
        self.setTextVisible(False)
        self.setFixedHeight(4)
        self.setRange(0, 100)
        self.setValue(0)
        self.setStyleSheet(f"""
            QProgressBar {{
                background-color: rgba(255, 255, 255, 0.06);
                border: none;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {color_start}, stop:1 {color_end});
                border-radius: 2px;
            }}
        """)
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(400)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.valueChanged.connect(self._apply_val)

    def _apply_val(self, val):
        super().setValue(int(val))

    def set_animated_value(self, target: int):
        target = max(0, min(100, int(target)))
        if self._anim.state() == QVariantAnimation.Running:
            self._anim.stop()
        self._anim.setStartValue(self.value())
        self._anim.setEndValue(target)
        self._anim.start()


class HardwareTelemetryWorker(QThread):
    """Worker en segundo plano para recolectar métricas de hardware sin congelar la GUI."""
    telemetry_ready = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True
        self.collector = UmbraHardwareCollector()

    def run(self):
        while self._running:
            try:
                snap = self.collector.collect_snapshot()
                if self._running:
                    self.telemetry_ready.emit(snap)
            except Exception:
                pass
            
            # Muestreo cada 1200ms
            for _ in range(12):
                if not self._running:
                    break
                self.msleep(100)

    def stop(self):
        self._running = False
        if not self.wait(400):
            self.terminate()
            self.wait(200)


class ProjectHud(QFrame):
    """
    HUD Superior del Espacio de Trabajo Lumen:
    Dividido exactamente en 2 sub-paneles simétricos:
    - Izquierda: Visor del Proyecto & GitOps.
    - Derecha: Telemetría de Hardware en vivo con barras de uso y temperatura.
    """
    
    back_requested = Signal()
    refresh_requested = Signal()

    def __init__(self, project: Project = None, parent=None):
        super().__init__(parent)
        self.project = project
        self.setProperty("class", "sector_card")
        self.setObjectName("lumen_project_hud")
        
        self.init_ui()
        self.init_telemetry_worker()
        self.init_clock_timer()

        if self.project:
            self.update_project(self.project)

    def init_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(18, 14, 18, 14)
        self.main_layout.setSpacing(18)

        # =============================================================
        # 1. SUB-PANEL IZQUIERDO: VISOR DE PROYECTO & GITOPS
        # =============================================================
        self.left_panel = QWidget()
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        # Fila de Acciones Tácticas y Navegación
        nav_row = QHBoxLayout()
        nav_row.setSpacing(8)

        self.btn_back = QPushButton("◀ Proyectos")
        self.btn_back.setProperty("class", "cyber_btn")
        self.btn_back.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_back.setFixedHeight(24)
        self.btn_back.setStyleSheet("font-size: 11px; font-weight: 700; padding: 2px 10px;")
        self.btn_back.clicked.connect(self.back_requested.emit)
        nav_row.addWidget(self.btn_back)

        self.btn_open_folder = QPushButton("📂 Abrir")
        self.btn_open_folder.setProperty("class", "cyber_btn")
        self.btn_open_folder.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_open_folder.setFixedHeight(24)
        self.btn_open_folder.setStyleSheet("font-size: 11px; padding: 2px 8px;")
        self.btn_open_folder.clicked.connect(self._open_project_folder)
        nav_row.addWidget(self.btn_open_folder)

        self.btn_refresh = QPushButton("🔄 Sincronizar")
        self.btn_refresh.setProperty("class", "cyber_btn")
        self.btn_refresh.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_refresh.setFixedHeight(24)
        self.btn_refresh.setStyleSheet("font-size: 11px; padding: 2px 8px;")
        self.btn_refresh.clicked.connect(self._on_refresh_clicked)
        nav_row.addWidget(self.btn_refresh)

        nav_row.addStretch()

        self.lbl_system_badge = QLabel("🟢 SISTEMA CONECTADO")
        self.lbl_system_badge.setStyleSheet("""
            background-color: rgba(255, 255, 255, 0.05);
            color: #e2e8f0;
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 4px;
            padding: 2px 8px;
            font-size: 10px;
            font-weight: 800;
            letter-spacing: 0.5px;
        """)
        nav_row.addWidget(self.lbl_system_badge)
        left_layout.addLayout(nav_row)

        # Línea 1: Proyecto | Rama | Remoto
        row1 = QHBoxLayout()
        row1.setSpacing(6)

        lbl_p_tag = QLabel("📁 Proyecto:")
        lbl_p_tag.setStyleSheet("color: #94a3b8; font-weight: 700; font-size: 12px;")
        self.lbl_proj_title = QLabel("Cargando...")
        self.lbl_proj_title.setStyleSheet("color: #ffffff; font-weight: 800; font-size: 13px;")

        sep1 = QLabel(" | ")
        sep1.setStyleSheet("color: #475569; font-weight: 700;")

        lbl_b_tag = QLabel("🌿 Rama:")
        lbl_b_tag.setStyleSheet("color: #94a3b8; font-weight: 700; font-size: 12px;")
        self.lbl_proj_branch = QLabel("main")
        self.lbl_proj_branch.setStyleSheet("color: #e2e8f0; font-weight: 800; font-size: 12px;")

        sep2 = QLabel(" | ")
        sep2.setStyleSheet("color: #475569; font-weight: 700;")

        lbl_r_tag = QLabel("🌐 Remoto:")
        lbl_r_tag.setStyleSheet("color: #94a3b8; font-weight: 700; font-size: 12px;")
        self.lbl_proj_remote = QLabel("Local")
        self.lbl_proj_remote.setStyleSheet("color: #cbd5e1; font-weight: 700; font-size: 12px;")

        row1.addWidget(lbl_p_tag)
        row1.addWidget(self.lbl_proj_title)
        row1.addWidget(sep1)
        row1.addWidget(lbl_b_tag)
        row1.addWidget(self.lbl_proj_branch)
        row1.addWidget(sep2)
        row1.addWidget(lbl_r_tag)
        row1.addWidget(self.lbl_proj_remote)
        row1.addStretch()
        left_layout.addLayout(row1)

        # Línea 2: Entorno | Contenedores Docker | Hora
        row2 = QHBoxLayout()
        row2.setSpacing(6)

        lbl_e_tag = QLabel("⚡ Entorno:")
        lbl_e_tag.setStyleSheet("color: #94a3b8; font-weight: 700; font-size: 12px;")
        self.lbl_env_status = QLabel("Sin Entorno")
        self.lbl_env_status.setStyleSheet("color: #e2e8f0; font-weight: 800; font-size: 12px;")

        sep3 = QLabel(" | ")
        sep3.setStyleSheet("color: #475569; font-weight: 700;")

        lbl_d_tag = QLabel("🐳 Contenedores Docker:")
        lbl_d_tag.setStyleSheet("color: #94a3b8; font-weight: 700; font-size: 12px;")
        self.lbl_docker_status = QLabel("0 activos")
        self.lbl_docker_status.setStyleSheet("color: #cbd5e1; font-weight: 700; font-size: 12px;")

        sep4 = QLabel(" | ")
        sep4.setStyleSheet("color: #475569; font-weight: 700;")

        lbl_h_tag = QLabel("🕒 Hora:")
        lbl_h_tag.setStyleSheet("color: #94a3b8; font-weight: 700; font-size: 12px;")
        self.lbl_current_time = QLabel("--:--:--")
        self.lbl_current_time.setStyleSheet(
            "font-family: 'JetBrains Mono', monospace; font-weight: 700; color: #ffffff; font-size: 12px;"
        )

        row2.addWidget(lbl_e_tag)
        row2.addWidget(self.lbl_env_status)
        row2.addWidget(sep3)
        row2.addWidget(lbl_d_tag)
        row2.addWidget(self.lbl_docker_status)
        row2.addWidget(sep4)
        row2.addWidget(lbl_h_tag)
        row2.addWidget(self.lbl_current_time)
        row2.addStretch()
        left_layout.addLayout(row2)

        # Línea 3: Git HUD: | Git Mod | Untracked | Deleted
        row3 = QHBoxLayout()
        row3.setSpacing(6)

        lbl_hud_title = QLabel("📊 Git HUD: | ")
        lbl_hud_title.setStyleSheet("color: #64748b; font-weight: 800; font-size: 12px;")

        lbl_m_tag = QLabel("📝 Git Mod:")
        lbl_m_tag.setStyleSheet("color: #94a3b8; font-weight: 700; font-size: 12px;")
        self.lbl_git_mod = QLabel("0 modificados")
        self.lbl_git_mod.setStyleSheet("color: #e2e8f0; font-weight: 700; font-size: 12px;")

        sep5 = QLabel(" | ")
        sep5.setStyleSheet("color: #475569; font-weight: 700;")

        lbl_u_tag = QLabel("❓ Untracked:")
        lbl_u_tag.setStyleSheet("color: #94a3b8; font-weight: 700; font-size: 12px;")
        self.lbl_git_untracked = QLabel("0 no rastreados")
        self.lbl_git_untracked.setStyleSheet("color: #cbd5e1; font-weight: 700; font-size: 12px;")

        sep6 = QLabel(" | ")
        sep6.setStyleSheet("color: #475569; font-weight: 700;")

        lbl_del_tag = QLabel("🗑️ Deleted:")
        lbl_del_tag.setStyleSheet("color: #94a3b8; font-weight: 700; font-size: 12px;")
        self.lbl_git_deleted = QLabel("0")
        self.lbl_git_deleted.setStyleSheet("color: #94a3b8; font-weight: 700; font-size: 12px;")

        row3.addWidget(lbl_hud_title)
        row3.addWidget(lbl_m_tag)
        row3.addWidget(self.lbl_git_mod)
        row3.addWidget(sep5)
        row3.addWidget(lbl_u_tag)
        row3.addWidget(self.lbl_git_untracked)
        row3.addWidget(sep6)
        row3.addWidget(lbl_del_tag)
        row3.addWidget(self.lbl_git_deleted)
        row3.addStretch()
        left_layout.addLayout(row3)

        self.main_layout.addWidget(self.left_panel, 6)

        # =============================================================
        # SEPARADOR VERTICAL
        # =============================================================
        sep_center = QFrame()
        sep_center.setFrameShape(QFrame.VLine)
        sep_center.setStyleSheet("background-color: rgba(255, 255, 255, 0.08); max-width: 1px;")
        self.main_layout.addWidget(sep_center)

        # =============================================================
        # 2. SUB-PANEL DERECHO: TELEMETRÍA DE HARDWARE EN VIVO
        # =============================================================
        self.right_panel = QWidget()
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)

        # Grid 2x2 para instrumentos de hardware
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(8)

        # -------------------------------------------------------------
        # Celda (0, 0): PROCESADOR (CPU: Barra de uso y de temperatura)
        # -------------------------------------------------------------
        cpu_box = QVBoxLayout()
        cpu_box.setSpacing(2)

        self.lbl_cpu_head = QLabel("⚡ PROCESADOR (CPU)")
        self.lbl_cpu_head.setStyleSheet("color: #94a3b8; font-size: 9.5px; font-weight: 800; letter-spacing: 1px;")
        cpu_box.addWidget(self.lbl_cpu_head)

        cpu_val_row = QHBoxLayout()
        self.lbl_cpu_usage = QLabel("0%")
        self.lbl_cpu_usage.setStyleSheet("color: #ffffff; font-weight: 800; font-size: 12.5px; font-family: 'JetBrains Mono', monospace;")
        self.lbl_cpu_temp = QLabel("🌡 0°C")
        self.lbl_cpu_temp.setStyleSheet("color: #cbd5e1; font-weight: 700; font-size: 11px;")
        cpu_val_row.addWidget(self.lbl_cpu_usage)
        cpu_val_row.addStretch()
        cpu_val_row.addWidget(self.lbl_cpu_temp)
        cpu_box.addLayout(cpu_val_row)

        self.bar_cpu_usage = TelemetryFilamentBar(color_start="#64748b", color_end="#e2e8f0")
        self.bar_cpu_temp = TelemetryFilamentBar(color_start="#475569", color_end="#94a3b8")
        cpu_box.addWidget(self.bar_cpu_usage)
        cpu_box.addWidget(self.bar_cpu_temp)
        grid.addLayout(cpu_box, 0, 0)

        # -------------------------------------------------------------
        # Celda (0, 1): GRÁFICA (GPU: Barra de uso y de temperatura)
        # -------------------------------------------------------------
        gpu_box = QVBoxLayout()
        gpu_box.setSpacing(2)

        self.lbl_gpu_head = QLabel("🎮 GRÁFICA (GPU)")
        self.lbl_gpu_head.setStyleSheet("color: #94a3b8; font-size: 9.5px; font-weight: 800; letter-spacing: 1px;")
        gpu_box.addWidget(self.lbl_gpu_head)

        gpu_val_row = QHBoxLayout()
        self.lbl_gpu_usage = QLabel("0%")
        self.lbl_gpu_usage.setStyleSheet("color: #ffffff; font-weight: 800; font-size: 12.5px; font-family: 'JetBrains Mono', monospace;")
        self.lbl_gpu_temp = QLabel("🌡 0°C")
        self.lbl_gpu_temp.setStyleSheet("color: #cbd5e1; font-weight: 700; font-size: 11px;")
        gpu_val_row.addWidget(self.lbl_gpu_usage)
        gpu_val_row.addStretch()
        gpu_val_row.addWidget(self.lbl_gpu_temp)
        gpu_box.addLayout(gpu_val_row)

        self.bar_gpu_usage = TelemetryFilamentBar(color_start="#64748b", color_end="#e2e8f0")
        self.bar_gpu_temp = TelemetryFilamentBar(color_start="#475569", color_end="#94a3b8")
        gpu_box.addWidget(self.bar_gpu_usage)
        gpu_box.addWidget(self.bar_gpu_temp)
        grid.addLayout(gpu_box, 0, 1)

        # -------------------------------------------------------------
        # Celda (1, 0): MEMORIA RAM (Barra de uso)
        # -------------------------------------------------------------
        ram_box = QVBoxLayout()
        ram_box.setSpacing(2)

        self.lbl_ram_head = QLabel("💾 MEMORIA RAM")
        self.lbl_ram_head.setStyleSheet("color: #94a3b8; font-size: 9.5px; font-weight: 800; letter-spacing: 1px;")
        ram_box.addWidget(self.lbl_ram_head)

        ram_val_row = QHBoxLayout()
        self.lbl_ram_usage = QLabel("0%")
        self.lbl_ram_usage.setStyleSheet("color: #ffffff; font-weight: 800; font-size: 12.5px; font-family: 'JetBrains Mono', monospace;")
        self.lbl_ram_detail = QLabel("0.0 / 0.0 GB")
        self.lbl_ram_detail.setStyleSheet("color: #cbd5e1; font-weight: 600; font-size: 10.5px;")
        ram_val_row.addWidget(self.lbl_ram_usage)
        ram_val_row.addStretch()
        ram_val_row.addWidget(self.lbl_ram_detail)
        ram_box.addLayout(ram_val_row)

        self.bar_ram_usage = TelemetryFilamentBar(color_start="#475569", color_end="#cbd5e1")
        ram_box.addWidget(self.bar_ram_usage)
        grid.addLayout(ram_box, 1, 0)

        # -------------------------------------------------------------
        # Celda (1, 1): ENLACE DE RED (Barra de uso)
        # -------------------------------------------------------------
        net_box = QVBoxLayout()
        net_box.setSpacing(2)

        self.lbl_net_head = QLabel("🌐 ENLACE DE RED")
        self.lbl_net_head.setStyleSheet("color: #94a3b8; font-size: 9.5px; font-weight: 800; letter-spacing: 1px;")
        net_box.addWidget(self.lbl_net_head)

        net_val_row = QHBoxLayout()
        self.lbl_net_speed = QLabel("↓ 0 MB/s  ↑ 0 MB/s")
        self.lbl_net_speed.setStyleSheet("color: #ffffff; font-weight: 700; font-size: 11px; font-family: 'JetBrains Mono', monospace;")
        self.lbl_net_ping = QLabel("● 0 ms")
        self.lbl_net_ping.setStyleSheet("color: #94a3b8; font-weight: 600; font-size: 10.5px;")
        net_val_row.addWidget(self.lbl_net_speed)
        net_val_row.addStretch()
        net_val_row.addWidget(self.lbl_net_ping)
        net_box.addLayout(net_val_row)

        self.bar_net_usage = TelemetryFilamentBar(color_start="#334155", color_end="#94a3b8")
        net_box.addWidget(self.bar_net_usage)
        grid.addLayout(net_box, 1, 1)

        right_layout.addLayout(grid)
        self.main_layout.addWidget(self.right_panel, 5)

    def init_telemetry_worker(self):
        """Inicia el hilo de telemetría de hardware en segundo plano."""
        self.worker = HardwareTelemetryWorker(self)
        self.worker.telemetry_ready.connect(self.update_telemetry)
        self.worker.start()

    def init_clock_timer(self):
        """Actualiza la hora del HUD cada segundo."""
        self.clock_timer = QTimer(self)
        self.clock_timer.setInterval(1000)
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start()
        self._update_clock()

    def _update_clock(self):
        self.lbl_current_time.setText(datetime.now().strftime("%H:%M:%S"))

    def update_project(self, project: Project):
        """Actualiza el sub-panel izquierdo con la telemetría real del proyecto."""
        self.project = project
        p_path = str(project.path) if project and project.path else ""

        try:
            sync = get_full_project_sync(p_path) if p_path else {}
        except Exception:
            sync = {}

        # 1. Proyecto | Rama | Remoto
        name = sync.get("name") or (project.name if project else "Sin Proyecto")
        ver = sync.get("version") or (f"v{project.semver}" if project else "v0.0.0")
        self.lbl_proj_title.setText(f"{name} ({ver})")

        git_info = sync.get("git_info", {})
        branch = git_info.get("branch") or (project.current_branch if project else "(Sin Git)")
        self.lbl_proj_branch.setText(branch)

        remote = git_info.get("remote") or "Local"
        self.lbl_proj_remote.setText(remote)

        # 2. Entorno | Docker
        env_info = sync.get("env_info")
        env_text = env_info.get("text", "Sin Entorno") if isinstance(env_info, dict) else "Sin Entorno"
        self.lbl_env_status.setText(env_text)

        docker_info = sync.get("docker_info")
        docker_text = docker_info.get("text", "0 activos") if isinstance(docker_info, dict) else "0 activos"
        self.lbl_docker_status.setText(docker_text)

        # 3. Git HUD
        git_hud = sync.get("git_hud", {})
        self.lbl_git_mod.setText(git_hud.get("mod_str", "0 modificados"))
        self.lbl_git_untracked.setText(git_hud.get("untracked_str", "0 no rastreados"))
        self.lbl_git_deleted.setText(str(git_hud.get("deleted_str", "0")))

    def update_telemetry(self, snap: dict):
        """Actualiza el sub-panel derecho con los datos vivos de hardware."""
        # 1. CPU
        cpu_model = snap.get("cpu_model", "CPU")
        self.lbl_cpu_head.setText(f"⚡ PROCESADOR ({cpu_model})")
        
        cpu_pct = snap.get("cpu_pct", 0)
        cpu_temp = snap.get("cpu_temp", 0)
        self.lbl_cpu_usage.setText(f"{cpu_pct}%")
        self.lbl_cpu_temp.setText(f"🌡 {cpu_temp}°C")
        self.bar_cpu_usage.set_animated_value(cpu_pct)
        self.bar_cpu_temp.set_animated_value(min(100, int((cpu_temp / 100.0) * 100)))

        # 2. GPU
        gpu_model = snap.get("gpu_model", "GPU")
        self.lbl_gpu_head.setText(f"🎮 GRÁFICA ({gpu_model})")
        
        gpu_pct = snap.get("gpu_pct", 0)
        gpu_temp = snap.get("gpu_temp", 0)
        self.lbl_gpu_usage.setText(f"{gpu_pct}%")
        self.lbl_gpu_temp.setText(f"🌡 {gpu_temp}°C")
        self.bar_gpu_usage.set_animated_value(gpu_pct)
        self.bar_gpu_temp.set_animated_value(min(100, int((gpu_temp / 100.0) * 100)))

        # 3. RAM
        ram_pct = snap.get("ram_pct", 0)
        ram_used = snap.get("ram_used_gb", 0.0)
        ram_total = snap.get("ram_total_gb", 0.0)
        self.lbl_ram_usage.setText(f"{ram_pct}%")
        self.lbl_ram_detail.setText(f"{ram_used:.1f} / {ram_total:.1f} GB")
        self.bar_ram_usage.set_animated_value(ram_pct)

        # 4. RED
        rx = snap.get("net_rx_mbs", 0.0)
        tx = snap.get("net_tx_mbs", 0.0)
        ping = snap.get("net_ping_ms", 0)
        self.lbl_net_speed.setText(f"↓ {rx:.1f}M  ↑ {tx:.1f}M")
        self.lbl_net_ping.setText(f"● {ping} ms")
        net_activity_pct = min(100, int((rx + tx) * 5))
        self.bar_net_usage.set_animated_value(net_activity_pct)

    def _open_project_folder(self):
        if self.project and self.project.path.is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.project.path)))

    def _on_refresh_clicked(self):
        if self.project:
            self.update_project(self.project)
        self.refresh_requested.emit()

    def teardown(self):
        """Detiene de forma limpia el worker de hardware y temporizadores."""
        if hasattr(self, "worker") and self.worker.isRunning():
            self.worker.stop()
        if hasattr(self, "clock_timer") and self.clock_timer.isActive():
            self.clock_timer.stop()

    def closeEvent(self, event):
        """Detiene de forma limpia el worker de hardware al cerrar."""
        self.teardown()
        super().closeEvent(event)
