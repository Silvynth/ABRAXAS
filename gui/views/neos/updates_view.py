#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS | NEOS - ACTUALIZACIÓN VIEW (CENTRO DE ACTUALIZACIONES)
# =====================================================================

import os
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QScrollArea, QTextEdit, 
    QApplication, QProgressBar
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal

from core import get_version
from core.updater import (
    get_current_repo_info, check_for_app_updates, 
    execute_app_update, restart_abraxas_app
)


class UpdateWorkerThread(QThread):
    """Hilo de trabajo en segundo plano para verificar o ejecutar actualizaciones sin congelar la GUI."""
    
    finished_check = Signal(dict)
    finished_update = Signal(dict)

    def __init__(self, mode="check"):
        super().__init__()
        self.mode = mode

    def run(self):
        if self.mode == "check":
            res = check_for_app_updates()
            self.finished_check.emit(res)
        elif self.mode == "update":
            res = execute_app_update(stash_dirty=True)
            self.finished_update.emit(res)


class UpdatesTerminalDisplay(QTextEdit):
    """Visor de logs coloreado de la consola de actualización (Solo lectura)."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMinimumHeight(150)
        self.setCursor(Qt.IBeamCursor)
        self.setLineWrapMode(QTextEdit.WidgetWidth)
        self.setStyleSheet("""
            QTextEdit {
                background-color: #07090e;
                color: #e5e7eb;
                font-family: 'JetBrains Mono', 'Fira Code', 'DejaVu Sans Mono', 'Consolas', monospace;
                font-size: 12px;
                line-height: 1.45;
                border: none;
                padding: 12px 16px;
                selection-background-color: #4f46e5;
                selection-color: #ffffff;
            }
            QScrollBar:vertical {
                background: #090b10;
                width: 10px;
                margin: 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #1f2430;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #6366f1;
            }
        """)

    def log(self, tag: str, message: str, tag_color: str = "#38bdf8", text_color: str = "#e5e7eb", prefix: str = "◈"):
        now = datetime.now().strftime("%H:%M:%S")
        html = (
            f"<div style='margin-bottom: 3px; font-family: monospace;'>"
            f"<span style='color: #6b7280;'>[{now}]</span> "
            f"<span style='color: {tag_color}; font-weight: 800;'>{prefix} [{tag}]</span> "
            f"<span style='color: {text_color};'>{message}</span>"
            f"</div>"
        )
        self.append(html)
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())

    def log_success(self, tag: str, message: str):
        self.log(tag, message, tag_color="#34d399", text_color="#a7f3d0", prefix="✔")

    def log_info(self, tag: str, message: str):
        self.log(tag, message, tag_color="#38bdf8", text_color="#e0e7ff", prefix="ℹ")

    def log_warn(self, tag: str, message: str):
        self.log(tag, message, tag_color="#f59e0b", text_color="#fed7aa", prefix="⚠")

    def log_error(self, tag: str, message: str):
        self.log(tag, message, tag_color="#f87171", text_color="#fecaca", prefix="✖")


class UpdatesView(QWidget):
    """Centro de Actualizaciones y Mantenimiento de ABRAXAS."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.app_version = get_version()
        self.repo_info = get_current_repo_info()
        self.worker = None
        self.init_ui()

        # Comprobar actualizaciones automáticamente después de 800ms
        QTimer.singleShot(800, self.start_check_updates)

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(14)

        # -------------------------------------------------------------
        # 1. ENCABEZADO PRINCIPAL
        # -------------------------------------------------------------
        header_bar = QHBoxLayout()
        header_bar.setSpacing(12)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        
        lbl_t = QLabel("🔄  CENTRO DE ACTUALIZACIÓN")
        lbl_t.setProperty("class", "page_title")
        lbl_t.setStyleSheet("font-size: 18px; font-weight: 900; color: #f3f4f6; letter-spacing: 0.5px;")

        lbl_sub = QLabel("Gestor de versiones, sincronización con GitHub y mantenimiento de ABRAXAS")
        lbl_sub.setProperty("class", "page_subtitle")
        lbl_sub.setStyleSheet("font-size: 12px; color: #9ca3af;")

        title_layout.addWidget(lbl_t)
        title_layout.addWidget(lbl_sub)
        header_bar.addLayout(title_layout)

        header_bar.addStretch()

        # Status Pill
        self.lbl_status_pill = QLabel("🟢 SISTEMA AL DÍA")
        self.lbl_status_pill.setStyleSheet("""
            background-color: rgba(16, 185, 129, 0.12);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.35);
            border-radius: 12px;
            padding: 5px 14px;
            font-size: 11px;
            font-weight: 800;
        """)
        header_bar.addWidget(self.lbl_status_pill)

        root_layout.addLayout(header_bar)

        # -------------------------------------------------------------
        # 2. HERO DASHBOARD (ESTADO ACTUAL & BOTÓN DE ACTUALIZACIÓN)
        # -------------------------------------------------------------
        hero_card = QFrame()
        hero_card.setProperty("class", "surface")
        hero_card.setStyleSheet("""
            QFrame.surface {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(22, 24, 34, 0.95), stop:1 rgba(16, 18, 25, 0.95));
                border: 1px solid rgba(99, 102, 241, 0.30);
                border-left: 5px solid #6366f1;
                border-radius: 12px;
            }
        """)
        hero_layout = QHBoxLayout(hero_card)
        hero_layout.setContentsMargins(20, 18, 20, 18)
        hero_layout.setSpacing(20)

        # Información izquierda
        info_col = QVBoxLayout()
        info_col.setSpacing(6)

        lbl_app_name = QLabel(f"❖  ABRAXAS  [v{self.app_version}]")
        lbl_app_name.setStyleSheet("font-size: 16px; font-weight: 900; color: #fbbf24;")
        info_col.addWidget(lbl_app_name)

        self.lbl_branch = QLabel(f"🌿 Rama activa: {self.repo_info['branch']}  •  🌐 Remoto: {self.repo_info['remote_url']}")
        self.lbl_branch.setStyleSheet("font-size: 12.5px; color: #c7d2fe; font-weight: 600;")
        info_col.addWidget(self.lbl_branch)

        self.lbl_commit = QLabel(f"◈ Último commit: {self.repo_info['current_commit']}")
        self.lbl_commit.setStyleSheet("font-family: monospace; font-size: 11.5px; color: #9ca3af;")
        info_col.addWidget(self.lbl_commit)

        hero_layout.addLayout(info_col, 1)

        # Botones de Acción Derecha
        btn_col = QVBoxLayout()
        btn_col.setSpacing(8)

        # Botón Actualizar Ahora
        self.btn_update_now = QPushButton("🚀  Actualizar ABRAXAS")
        self.btn_update_now.setCursor(Qt.PointingHandCursor)
        self.btn_update_now.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6366f1, stop:1 #8b5cf6);
                color: #ffffff;
                border: 1px solid #a78bfa;
                border-radius: 8px;
                padding: 10px 18px;
                font-weight: 800;
                font-size: 12.5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4f46e5, stop:1 #7c3aed);
                border-color: #c4b5fd;
            }
            QPushButton:disabled {
                background-color: rgba(255, 255, 255, 0.05);
                color: #6b7280;
                border-color: rgba(255, 255, 255, 0.10);
            }
        """)
        self.btn_update_now.clicked.connect(self.start_app_update)
        btn_col.addWidget(self.btn_update_now)

        # Botón Comprobar
        self.btn_check = QPushButton("🔍  Comprobar Actualizaciones")
        self.btn_check.setCursor(Qt.PointingHandCursor)
        self.btn_check.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.04);
                color: #bae6fd;
                border: 1px solid rgba(56, 189, 248, 0.35);
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 700;
                font-size: 11.5px;
            }
            QPushButton:hover {
                background-color: rgba(56, 189, 248, 0.15);
                border-color: #38bdf8;
                color: #ffffff;
            }
        """)
        self.btn_check.clicked.connect(self.start_check_updates)
        btn_col.addWidget(self.btn_check)

        # Botón Reiniciar (Oculto inicialmente, aparece al actualizar)
        self.btn_restart = QPushButton("🔄  Reiniciar Aplicación")
        self.btn_restart.setCursor(Qt.PointingHandCursor)
        self.btn_restart.setVisible(False)
        self.btn_restart.setStyleSheet("""
            QPushButton {
                background-color: rgba(16, 185, 129, 0.20);
                color: #34d399;
                border: 1px solid #10b981;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 800;
                font-size: 11.5px;
            }
            QPushButton:hover {
                background-color: #10b981;
                color: #07090e;
            }
        """)
        self.btn_restart.clicked.connect(restart_abraxas_app)
        btn_col.addWidget(self.btn_restart)

        hero_layout.addLayout(btn_col)
        root_layout.addWidget(hero_card)

        # -------------------------------------------------------------
        # 3. LISTA DE CAMBIOS / ESTADO DE PAQUETES
        # -------------------------------------------------------------
        self.changes_card = QFrame()
        self.changes_card.setProperty("class", "surface")
        self.changes_card.setStyleSheet("""
            QFrame.surface {
                background-color: #0c0e14;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
            }
        """)
        ch_layout = QVBoxLayout(self.changes_card)
        ch_layout.setContentsMargins(16, 14, 16, 14)
        ch_layout.setSpacing(8)

        self.lbl_changes_head = QLabel("📋  Registro de Cambios y Commits:")
        self.lbl_changes_head.setStyleSheet("font-size: 13px; font-weight: 800; color: #e5e7eb;")
        ch_layout.addWidget(self.lbl_changes_head)

        self.lbl_changes_content = QLabel("Consultando estado con el repositorio remoto en GitHub...")
        self.lbl_changes_content.setStyleSheet("font-family: monospace; font-size: 12px; color: #9ca3af;")
        self.lbl_changes_content.setWordWrap(True)
        ch_layout.addWidget(self.lbl_changes_content)

        root_layout.addWidget(self.changes_card)

        # -------------------------------------------------------------
        # 4. CONSOLA DE ACTUALIZACIÓN EN TIEMPO REAL
        # -------------------------------------------------------------
        terminal_frame = QFrame()
        terminal_frame.setProperty("class", "surface")
        terminal_frame.setStyleSheet("""
            QFrame.surface {
                background-color: #07090e;
                border: 1px solid rgba(99, 102, 241, 0.25);
                border-radius: 10px;
            }
        """)
        t_box = QVBoxLayout(terminal_frame)
        t_box.setContentsMargins(0, 0, 0, 0)
        t_box.setSpacing(0)

        term_bar = QFrame()
        term_bar.setStyleSheet("""
            background-color: rgba(255, 255, 255, 0.03);
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            border-top-left-radius: 10px;
            border-top-right-radius: 10px;
            padding: 4px 10px;
        """)
        tb_layout = QHBoxLayout(term_bar)
        tb_layout.setContentsMargins(12, 7, 12, 7)
        tb_layout.setSpacing(10)

        lbl_dots = QLabel("🔴  🟡  🟢")
        lbl_dots.setStyleSheet("font-size: 9px;")
        tb_layout.addWidget(lbl_dots)

        lbl_t_title = QLabel("abraxas-updater@system:~$")
        lbl_t_title.setStyleSheet("font-family: monospace; font-size: 12px; font-weight: 700; color: #a5b4fc;")
        tb_layout.addWidget(lbl_t_title)

        tb_layout.addStretch()

        lbl_t_status = QLabel("⚡ TERMINAL DE ACTUALIZACIÓN")
        lbl_t_status.setStyleSheet("font-size: 10px; font-weight: 800; color: #38bdf8; background-color: rgba(6, 182, 212, 0.12); border: 1px solid rgba(6, 182, 212, 0.35); border-radius: 4px; padding: 2px 8px;")
        tb_layout.addWidget(lbl_t_status)

        t_box.addWidget(term_bar)

        self.terminal = UpdatesTerminalDisplay()
        t_box.addWidget(self.terminal)

        root_layout.addWidget(terminal_frame, 1)

        # Log inicial
        self.terminal.log("INIT", f"Centro de actualización inicializado para ABRAXAS v{self.app_version}.", tag_color="#818cf8")

    # -----------------------------------------------------------------
    # LÓGICA DE COMPROBACIÓN Y ACTUALIZACIÓN
    # -----------------------------------------------------------------
    def start_check_updates(self):
        """Inicia la comprobación de actualizaciones en segundo plano."""
        if self.worker and self.worker.isRunning():
            return
        self.btn_check.setEnabled(False)
        self.lbl_status_pill.setText("🔵 COMPROBANDO...")
        self.lbl_status_pill.setStyleSheet("""
            background-color: rgba(56, 189, 248, 0.12);
            color: #38bdf8;
            border: 1px solid rgba(56, 189, 248, 0.35);
            border-radius: 12px;
            padding: 5px 14px;
            font-size: 11px;
            font-weight: 800;
        """)
        self.terminal.log_info("FETCH", f"Consultando estado con origin/{self.repo_info['branch']}...")

        self.worker = UpdateWorkerThread(mode="check")
        self.worker.finished_check.connect(self.on_check_finished)
        self.worker.start()

    def on_check_finished(self, res: dict):
        """Callback tras finalizar la comprobación remota."""
        self.btn_check.setEnabled(True)
        if self.worker:
            self.worker.wait(50)
            self.worker = None
        if not res.get("success", False):
            self.lbl_status_pill.setText("🔴 ERROR DE CONEXIÓN")
            self.lbl_status_pill.setStyleSheet("""
                background-color: rgba(239, 68, 68, 0.12);
                color: #f87171;
                border: 1px solid rgba(239, 68, 68, 0.35);
                border-radius: 12px;
                padding: 5px 14px;
                font-size: 11px;
                font-weight: 800;
            """)
            self.terminal.log_error("ERROR", res.get("message", "Error al comprobar actualizaciones."))
            self.lbl_changes_content.setText(f"⚠ {res.get('message', 'No se pudo conectar con el servidor remoto.')}")
            return

        if res.get("has_updates", False):
            count = res.get("pending_count", 1)
            self.lbl_status_pill.setText(f"🟡 {count} ACTUALIZACIÓN(ES) DISPONIBLE(S)")
            self.lbl_status_pill.setStyleSheet("""
                background-color: rgba(251, 191, 36, 0.15);
                color: #fbbf24;
                border: 1px solid rgba(251, 191, 36, 0.40);
                border-radius: 12px;
                padding: 5px 14px;
                font-size: 11px;
                font-weight: 800;
            """)
            self.terminal.log_warn("UPDATE", f"Hay {count} nuevo(s) commit(s) disponible(s) en origin/{self.repo_info['branch']}.")
            
            # Listar commits en la tarjeta de cambios
            commits_text = []
            for c in res.get("commits", []):
                commits_text.append(f"• <b>{c['hash']}</b> — {c['title']} <span style='color:#9ca3af;'>({c['author']}, {c['time']})</span>")
                self.terminal.log("COMMIT", f"{c['hash']}: {c['title']} ({c['author']})", tag_color="#c084fc")

            self.lbl_changes_content.setText("<br>".join(commits_text) if commits_text else "Nuevas mejoras listas para descargar.")
        else:
            self.lbl_status_pill.setText("🟢 SISTEMA AL DÍA")
            self.lbl_status_pill.setStyleSheet("""
                background-color: rgba(16, 185, 129, 0.12);
                color: #34d399;
                border: 1px solid rgba(16, 185, 129, 0.35);
                border-radius: 12px;
                padding: 5px 14px;
                font-size: 11px;
                font-weight: 800;
            """)
            self.terminal.log_success("OK", "ABRAXAS se encuentra en la versión más reciente.")
            self.lbl_changes_content.setText(f"✔ Todo el código está sincronizado con <b>origin/{self.repo_info['branch']}</b>. No hay actualizaciones pendientes.")

    def start_app_update(self):
        """Inicia el proceso de actualización en segundo plano."""
        if self.worker and self.worker.isRunning():
            return
        self.btn_update_now.setEnabled(False)
        self.btn_check.setEnabled(False)
        self.lbl_status_pill.setText("⚡ ACTUALIZANDO...")
        self.lbl_status_pill.setStyleSheet("""
            background-color: rgba(99, 102, 241, 0.20);
            color: #818cf8;
            border: 1px solid #818cf8;
            border-radius: 12px;
            padding: 5px 14px;
            font-size: 11px;
            font-weight: 800;
        """)
        self.terminal.log_info("UPDATE", "Ejecutando git pull y sincronización del sistema...")

        self.worker = UpdateWorkerThread(mode="update")
        self.worker.finished_update.connect(self.on_update_finished)
        self.worker.start()

    def on_update_finished(self, res: dict):
        """Callback tras completar la actualización."""
        self.btn_update_now.setEnabled(True)
        self.btn_check.setEnabled(True)
        if self.worker:
            self.worker.wait(50)
            self.worker = None

        for log_line in res.get("logs", []):
            self.terminal.log("PULL", log_line, tag_color="#38bdf8")

        if res.get("success", False):
            self.lbl_status_pill.setText("🟢 ACTUALIZADO CON ÉXITO")
            self.lbl_status_pill.setStyleSheet("""
                background-color: rgba(16, 185, 129, 0.20);
                color: #34d399;
                border: 1px solid #10b981;
                border-radius: 12px;
                padding: 5px 14px;
                font-size: 11px;
                font-weight: 800;
            """)
            self.terminal.log_success("READY", "Actualización completada exitosamente.")
            self.btn_restart.setVisible(True)
            self.lbl_changes_content.setText("✔ La aplicación ha sido actualizada. Presiona 'Reiniciar Aplicación' para aplicar los cambios.")
        else:
            self.lbl_status_pill.setText("🔴 ERROR EN ACTUALIZACIÓN")
            self.lbl_status_pill.setStyleSheet("""
                background-color: rgba(239, 68, 68, 0.12);
                color: #f87171;
                border: 1px solid rgba(239, 68, 68, 0.35);
                border-radius: 12px;
                padding: 5px 14px;
                font-size: 11px;
                font-weight: 800;
            """)
            self.terminal.log_error("FAIL", res.get("message", "Error al actualizar."))

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.wait(500)
        super().closeEvent(event)
