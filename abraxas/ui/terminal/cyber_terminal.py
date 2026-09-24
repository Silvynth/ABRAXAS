"""
❖ ABRAXAS 2.0 | Shared UI: CyberTerminal Engine
Terminal interactiva compartida con estética Haute Horlogerie, buffers limpios,
puntos Unix, control de 3 estados (Colapsado / Normal / Maximizado) y API de logs tácticos.
Unificada para dominios UMBRA y LUMEN.
"""

import os
import re
import html
from pathlib import Path
from datetime import datetime
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, 
    QPushButton, QApplication, QSizePolicy, QWidget, QLineEdit
)
from PySide6.QtCore import Qt, Signal, QProcess, QTimer
from PySide6.QtGui import QCursor

class HandleBarPill(QFrame):
    """Manija interactiva central para ciclar el estado de la terminal."""
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedSize(54, 8)
        self.setToolTip("Clic para alternar altura de terminal")
        self.set_glow(True)

    def set_glow(self, active: bool):
        if active:
            self.setStyleSheet("""
                QFrame {
                    background-color: #64748b;
                    border-radius: 4px;
                }
                QFrame:hover {
                    background-color: #f1f5f9;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: #334155;
                    border-radius: 4px;
                }
                QFrame:hover {
                    background-color: #64748b;
                }
            """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class TerminalCommandInput(QLineEdit):
    """Línea de comando interactiva con navegación de historial y atajos de teclado Unix."""
    def __init__(self, terminal, parent=None):
        super().__init__(parent)
        self.terminal = terminal
        self.history: list[str] = []
        self.history_index: int = -1
        self.current_draft: str = ""

        self.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: #ffffff;
                font-family: 'JetBrains Mono', 'Fira Code', 'DejaVu Sans Mono', monospace;
                font-size: 11px;
                padding: 2px 4px;
                selection-background-color: rgba(56, 189, 248, 0.35);
                selection-color: #ffffff;
            }
        """)

    def add_history(self, cmd: str):
        cmd = cmd.strip()
        if cmd and (not self.history or self.history[-1] != cmd):
            self.history.append(cmd)
        self.history_index = -1
        self.current_draft = ""

    def keyPressEvent(self, event):
        # Atajos con Control
        if event.modifiers() & Qt.ControlModifier:
            if event.key() == Qt.Key_C:
                if self.terminal.is_running():
                    self.terminal.terminate_process()
                else:
                    self.clear()
                return
            elif event.key() == Qt.Key_L:
                self.terminal.clear()
                return

        # Navegación del historial con Flechas Arriba/Abajo
        if event.key() == Qt.Key_Up:
            if not self.history:
                return
            if self.history_index == -1:
                self.current_draft = self.text()
                self.history_index = len(self.history) - 1
            elif self.history_index > 0:
                self.history_index -= 1
            self.setText(self.history[self.history_index])
            return

        elif event.key() == Qt.Key_Down:
            if self.history_index == -1:
                return
            if self.history_index < len(self.history) - 1:
                self.history_index += 1
                self.setText(self.history[self.history_index])
            else:
                self.history_index = -1
                self.setText(self.current_draft)
            return

        super().keyPressEvent(event)


class CyberTerminal(QFrame):
    """Terminal gráfica táctica unificada para Umbra y Lumen."""
    
    # Emite "collapsed", "normal", o "maximized"
    state_changed = Signal(str)
    command_submitted = Signal(str)
    process_finished = Signal(int)
    sync_requested = Signal()

    def __init__(self, prompt: str = "abraxas@cachyos:~$", working_dir: str = None, parent=None):
        super().__init__(parent)
        self.prompt_text = prompt
        self.working_dir = working_dir or os.getcwd()
        self.current_state = 1  # 0: Collapsed, 1: Normal, 2: Maximized
        self.default_height = 200

        # Motor de procesos asíncrono
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self._on_stdout_ready)
        self.process.readyReadStandardError.connect(self._on_stderr_ready)
        self.process.finished.connect(self._on_process_finished)

        self.setProperty("class", "sector_card")
        self.setObjectName("cyber_terminal")
        self.init_ui()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # -------------------------------------------------------------
        # CABECERA SUPERIOR: Prompt, Handle Central y Acciones
        # -------------------------------------------------------------
        self.header_bar = QWidget()
        self.header_bar.setFixedHeight(38)
        self.header_bar.setStyleSheet("""
            QWidget {
                background-color: #0c0d10;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            }
        """)
        h_layout = QHBoxLayout(self.header_bar)
        h_layout.setContentsMargins(14, 6, 14, 6)
        h_layout.setSpacing(10)

        # Izquierda: Dots Unix + Prompt
        lbl_dots = QLabel("🔴 🟡 🟢")
        lbl_dots.setStyleSheet("font-size: 8px;")
        h_layout.addWidget(lbl_dots)

        self.lbl_prompt = QLabel(self.prompt_text)
        self.lbl_prompt.setStyleSheet(
            "color: #94a3b8; font-family: 'JetBrains Mono', monospace; "
            "font-size: 11px; font-weight: 700; letter-spacing: 0.5px;"
        )
        h_layout.addWidget(self.lbl_prompt)

        # Centro: Manija táctica interactiva
        h_layout.addStretch()
        self.handle_pill = HandleBarPill(self)
        self.handle_pill.clicked.connect(self.cycle_state)
        h_layout.addWidget(self.handle_pill)
        h_layout.addStretch()

        # Derecha: Botones de control
        self.btn_copy = QPushButton("📋 Copiar")
        self.btn_copy.setProperty("class", "cyber_btn")
        self.btn_copy.setFixedHeight(24)
        self.btn_copy.setStyleSheet("font-size: 10.5px; padding: 2px 8px;")
        self.btn_copy.clicked.connect(self.copy_output)
        h_layout.addWidget(self.btn_copy)

        self.btn_clear = QPushButton("🧹 Limpiar")
        self.btn_clear.setProperty("class", "cyber_btn")
        self.btn_clear.setFixedHeight(24)
        self.btn_clear.setStyleSheet("font-size: 10.5px; padding: 2px 8px;")
        self.btn_clear.clicked.connect(self.clear)
        h_layout.addWidget(self.btn_clear)

        self.btn_toggle = QPushButton("▼ Minimizar")
        self.btn_toggle.setProperty("class", "cyber_btn")
        self.btn_toggle.setFixedHeight(24)
        self.btn_toggle.setStyleSheet("font-size: 10.5px; padding: 2px 8px;")
        self.btn_toggle.clicked.connect(self.toggle_open_minimize)
        h_layout.addWidget(self.btn_toggle)

        self.btn_maximize = QPushButton("⛶ Maximizar")
        self.btn_maximize.setProperty("class", "cyber_btn")
        self.btn_maximize.setFixedHeight(24)
        self.btn_maximize.setStyleSheet("font-size: 10.5px; padding: 2px 8px;")
        self.btn_maximize.clicked.connect(self.toggle_maximize)
        h_layout.addWidget(self.btn_maximize)

        self.main_layout.addWidget(self.header_bar)

        # -------------------------------------------------------------
        # CUERPO DE LA CONSOLA (Visor HTML)
        # -------------------------------------------------------------
        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        self.text_display.setProperty("class", "cyber_terminal")
        self.text_display.setStyleSheet("""
            QTextEdit {
                background-color: #08090b;
                color: #e2e8f0;
                font-family: 'JetBrains Mono', 'Fira Code', 'DejaVu Sans Mono', monospace;
                font-size: 11.5px;
                line-height: 1.5;
                border: none;
                padding: 10px 14px;
                selection-background-color: rgba(255, 255, 255, 0.20);
                selection-color: #ffffff;
            }
            QScrollBar:vertical {
                background: #08090b;
                width: 6px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background: #334155;
                min-height: 20px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: #64748b;
            }
        """)
        self.main_layout.addWidget(self.text_display)

        # -------------------------------------------------------------
        # BARRA DE ENTRADA INTERACTIVA (PROMPT + INPUT + ACCIÓN)
        # -------------------------------------------------------------
        self.input_bar = QWidget()
        self.input_bar.setFixedHeight(34)
        self.input_bar.setStyleSheet("""
            QWidget {
                background-color: #0c0d10;
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
                border-top: 1px solid rgba(255, 255, 255, 0.08);
            }
        """)
        in_layout = QHBoxLayout(self.input_bar)
        in_layout.setContentsMargins(12, 4, 12, 4)
        in_layout.setSpacing(8)

        self.lbl_in_prompt = QLabel("❯")
        self.lbl_in_prompt.setStyleSheet("color: #38bdf8; font-family: 'JetBrains Mono', monospace; font-size: 13px; font-weight: 900;")
        in_layout.addWidget(self.lbl_in_prompt)

        self.cmd_input = TerminalCommandInput(self)
        self.cmd_input.setPlaceholderText("Escribe un comando... (ej: git status, ls, btrfs, cargo, help)")
        self.cmd_input.returnPressed.connect(self.execute_current_input)
        in_layout.addWidget(self.cmd_input, 1)

        self.btn_stop = QPushButton("⏹ Detener")
        self.btn_stop.setVisible(False)
        self.btn_stop.setFixedHeight(22)
        self.btn_stop.setStyleSheet("""
            QPushButton {
                background: rgba(239, 68, 68, 0.20);
                color: #fca5a5;
                border: 1px solid rgba(239, 68, 68, 0.40);
                border-radius: 3px;
                font-size: 10px;
                font-weight: 700;
                padding: 1px 8px;
            }
            QPushButton:hover {
                background: rgba(239, 68, 68, 0.35);
                color: #ffffff;
            }
        """)
        self.btn_stop.clicked.connect(self.terminate_process)
        in_layout.addWidget(self.btn_stop)

        self.btn_run = QPushButton("↵")
        self.btn_run.setToolTip("Ejecutar comando (Enter)")
        self.btn_run.setFixedHeight(22)
        self.btn_run.setFixedWidth(26)
        self.btn_run.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.05);
                color: #cbd5e1;
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 3px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: rgba(56, 189, 248, 0.20);
                color: #38bdf8;
                border-color: rgba(56, 189, 248, 0.40);
            }
        """)
        self.btn_run.clicked.connect(self.execute_current_input)
        in_layout.addWidget(self.btn_run)

        self.main_layout.addWidget(self.input_bar)

        # Aplicar altura normal inicial
        self.setFixedHeight(self.default_height)

    # -------------------------------------------------------------
    # GESTIÓN DE ESTADOS (Colapsado 38px / Normal 200px / Maximizado)
    # -------------------------------------------------------------
    def set_prompt(self, prompt: str):
        """Actualiza el texto del prompt en la barra superior."""
        self.prompt_text = prompt
        self.lbl_prompt.setText(prompt)

    def set_terminal_state(self, state: int):
        """
        0: Collapsed (38px, barra compacta, visor oculto)
        1: Normal (default_height ~200px)
        2: Maximized (expansión completa)
        """
        self.current_state = state

        if state == 0:  # Colapsado
            self.text_display.setVisible(False)
            self.input_bar.setVisible(False)
            self.setMinimumHeight(38)
            self.setMaximumHeight(38)
            self.setFixedHeight(38)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.btn_toggle.setText("▲ Abrir")
            self.btn_maximize.setText("⛶ Maximizar")
            self.handle_pill.set_glow(False)
            self.state_changed.emit("collapsed")

        elif state == 1:  # Normal
            self.text_display.setVisible(True)
            self.input_bar.setVisible(True)
            self.setMinimumHeight(self.default_height)
            self.setMaximumHeight(self.default_height)
            self.setFixedHeight(self.default_height)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.btn_toggle.setText("▼ Minimizar")
            self.btn_maximize.setText("⛶ Maximizar")
            self.handle_pill.set_glow(True)
            self.cmd_input.setFocus()
            self.state_changed.emit("normal")

        elif state == 2:  # Maximizado
            self.text_display.setVisible(True)
            self.input_bar.setVisible(True)
            self.setMinimumHeight(350)
            self.setMaximumHeight(16777215)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.btn_toggle.setText("▼ Minimizar")
            self.btn_maximize.setText("❐ Restaurar")
            self.handle_pill.set_glow(True)
            self.cmd_input.setFocus()
            self.state_changed.emit("maximized")

        self.updateGeometry()

    def toggle_open_minimize(self):
        """Alterna entre colapsado y normal (o minimiza si estaba maximizado)."""
        new_state = 1 if self.current_state == 0 else 0
        self.set_terminal_state(new_state)

    def toggle_maximize(self):
        """Alterna entre maximizado y normal."""
        new_state = 1 if self.current_state == 2 else 2
        self.set_terminal_state(new_state)

    def cycle_state(self):
        """Cicla interactivamente: 0 (colapsado) -> 1 (normal) -> 2 (máximo) -> 0."""
        next_state = (self.current_state + 1) % 3
        self.set_terminal_state(next_state)

    # -------------------------------------------------------------
    # REGISTRO Y FORMATO DE LOGS (Haute Horlogerie & Monocromo)
    # -------------------------------------------------------------
    def append_log(self, text: str):
        """Agrega una línea formateada con timestamp al visor."""
        now = datetime.now().strftime("%H:%M:%S")
        formatted = f"<span style='color: #64748b;'>[{now}]</span> <span style='color: #e2e8f0;'>{text}</span>"
        self.text_display.append(formatted)
        self._scroll_to_bottom()

    def log(self, tag: str, message: str, tag_color: str = "#94a3b8", text_color: str = "#e2e8f0", prefix: str = "◈"):
        """Inserta un registro con etiqueta categorizada y timestamp."""
        now = datetime.now().strftime("%H:%M:%S")
        html = (
            f"<div style='margin-bottom: 2px;'>"
            f"<span style='color: #475569;'>[{now}]</span> "
            f"<span style='color: {tag_color}; font-weight: bold;'>{prefix} [{tag}]</span> "
            f"<span style='color: {text_color};'>{message}</span>"
            f"</div>"
        )
        self.text_display.append(html)
        self._scroll_to_bottom()

    def log_info(self, tag: str, message: str):
        self.log(tag, message, tag_color="#94a3b8", text_color="#cbd5e1", prefix="ℹ")

    def log_success(self, tag: str, message: str):
        self.log(tag, message, tag_color="#e2e8f0", text_color="#f8fafc", prefix="✔")

    def log_warn(self, tag: str, message: str):
        self.log(tag, message, tag_color="#cbd5e1", text_color="#f1f5f9", prefix="⚠")

    def log_error(self, tag: str, message: str):
        self.log(tag, message, tag_color="#f87171", text_color="#fca5a5", prefix="✖")

    def log_git(self, tag: str, message: str):
        self.log(tag, message, tag_color="#94a3b8", text_color="#e2e8f0", prefix="🌿")

    def log_btrfs(self, tag: str, message: str):
        self.log(tag, message, tag_color="#cbd5e1", text_color="#e2e8f0", prefix="🛡")

    def log_kernel(self, tag: str, message: str):
        self.log(tag, message, tag_color="#94a3b8", text_color="#e2e8f0", prefix="⚡")

    def _scroll_to_bottom(self):
        sb = self.text_display.verticalScrollBar()
        sb.setValue(sb.maximum())

    def copy_output(self):
        """Copia todo el contenido de la terminal al portapapeles."""
        text = self.text_display.toPlainText()
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            self.btn_copy.setText("✓ Copiado")
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1500, lambda: self.btn_copy.setText("📋 Copiar"))

    def clear(self):
        """Limpia el buffer de la terminal."""
        self.text_display.clear()

    def clear_output(self):
        """Compatibilidad con métodos heredados de Umbra."""
        self.clear()

    # -------------------------------------------------------------
    # EJECUCIÓN INTERACTIVA & MOTOR DE PROCESOS
    # -------------------------------------------------------------
    def set_working_directory(self, path: str):
        """Configura el directorio de trabajo donde se ejecutan los comandos."""
        if path and os.path.isdir(path):
            self.working_dir = str(path)

    def get_working_directory(self) -> str:
        return self.working_dir

    def is_running(self) -> bool:
        """Indica si hay un proceso en ejecución en segundo plano."""
        return self.process.state() != QProcess.NotRunning

    def terminate_process(self):
        """Interrumpe el proceso en ejecución (^C)."""
        if self.is_running():
            self.log_warn("TERM", "Enviando señal de interrupción (^C)...")
            self.process.terminate()
            QTimer.singleShot(800, lambda: self.process.kill() if self.is_running() else None)

    def execute_current_input(self):
        """Ejecuta el texto actual de la línea de comandos."""
        cmd = self.cmd_input.text().strip()
        if not cmd:
            return
        self.cmd_input.add_history(cmd)
        self.cmd_input.clear()
        self.execute_command(cmd)

    def execute_command(self, cmd_text: str):
        """Ejecuta un comando interno o del sistema en la terminal."""
        cmd = cmd_text.strip()
        if not cmd:
            return

        self.command_submitted.emit(cmd)

        now = datetime.now().strftime("%H:%M:%S")
        prompt_label = self.lbl_prompt.text()
        header_html = (
            f"<div style='margin-top: 6px; margin-bottom: 2px;'>"
            f"<span style='color: #475569;'>[{now}]</span> "
            f"<span style='color: #38bdf8; font-weight: bold;'>{html.escape(prompt_label)}</span> "
            f"<span style='color: #ffffff; font-weight: 700;'>{html.escape(cmd)}</span>"
            f"</div>"
        )
        self.text_display.append(header_html)
        self._scroll_to_bottom()

        # Comandos internos
        tokens = cmd.split()
        first_token = tokens[0].lower() if tokens else ""

        if first_token in ("clear", "cls"):
            self.clear()
            return

        if first_token == "pwd":
            self.append_raw_line(self.working_dir)
            return

        if first_token == "cd":
            target = tokens[1] if len(tokens) > 1 else os.path.expanduser("~")
            resolved = Path(self.working_dir) / target
            try:
                resolved = resolved.resolve()
                if resolved.is_dir():
                    self.working_dir = str(resolved)
                    self.append_raw_line(f"📂 Directorio activo: {self.working_dir}")
                    self.sync_requested.emit()
                else:
                    self.log_error("CD", f"El directorio no existe: {target}")
            except Exception as e:
                self.log_error("CD", str(e))
            return

        if first_token == "exit":
            self.set_terminal_state(0)
            return

        if first_token in ("help", "--help", "-h") and len(tokens) == 1:
            help_text = (
                "<div style='color: #cbd5e1; font-family: monospace; font-size: 10.5px; padding: 4px; line-height: 1.4;'>"
                "<b>❖ CYBERTERMINAL // COMANDOS RÁPIDOS & AYUDA:</b><br>"
                "• <b>clear</b> / <b>cls</b>: Limpiar buffer de la terminal<br>"
                "• <b>cd &lt;ruta&gt;</b>: Cambiar directorio de trabajo<br>"
                "• <b>pwd</b>: Mostrar directorio de trabajo actual<br>"
                "• <b>exit</b>: Minimizar la consola<br>"
                "• <b>Comandos Shell:</b> Ejecución nativa de git, pacman, btrfs, cargo, python, etc.<br>"
                "• <b>Atajos de teclado:</b> ↑/↓ (Historial de comandos) | Ctrl+C (Interrumpir) | Ctrl+L (Limpiar)"
                "</div>"
            )
            self.text_display.append(help_text)
            self._scroll_to_bottom()
            return

        # Ejecución de comando asíncrono en Shell
        if self.is_running():
            self.log_warn("TERM", "Ya hay un proceso en ejecución. Usa '⏹ Detener' o Ctrl+C para interrumpirlo.")
            return

        self.btn_stop.setVisible(True)
        self.process.setWorkingDirectory(self.working_dir)
        self.process.start("/usr/bin/bash", ["-c", cmd])

    def _on_stdout_ready(self):
        data = self.process.readAllStandardOutput().data().decode("utf-8", errors="replace")
        if data:
            self._append_formatted_output(data, is_error=False)

    def _on_stderr_ready(self):
        data = self.process.readAllStandardError().data().decode("utf-8", errors="replace")
        if data:
            self._append_formatted_output(data, is_error=True)

    def _append_formatted_output(self, raw_text: str, is_error: bool = False):
        formatted = self._ansi_to_html(raw_text)
        color = "#fca5a5" if is_error else "#cbd5e1"
        html_block = f"<div style='color: {color}; white-space: pre-wrap; font-family: monospace; font-size: 11px;'>{formatted}</div>"
        self.text_display.append(html_block)
        self._scroll_to_bottom()

    def _on_process_finished(self, exit_code: int, exit_status):
        self.btn_stop.setVisible(False)
        self.process_finished.emit(exit_code)
        self.sync_requested.emit()
        if exit_code != 0:
            self.log_error("PROCESO", f"Finalizado con código de salida: {exit_code}")
        else:
            self._scroll_to_bottom()

    def append_raw_line(self, line: str):
        html_line = f"<div style='color: #cbd5e1; font-family: monospace; font-size: 11px;'>{html.escape(line)}</div>"
        self.text_display.append(html_line)
        self._scroll_to_bottom()

    @staticmethod
    def _ansi_to_html(text: str) -> str:
        escaped = html.escape(text)
        ansi_replacements = [
            (r'\033\[30m', '<span style="color:#64748b;">'),
            (r'\033\[31m', '<span style="color:#f87171;">'),
            (r'\033\[32m', '<span style="color:#34d399;">'),
            (r'\033\[33m', '<span style="color:#fbbf24;">'),
            (r'\033\[34m', '<span style="color:#60a5fa;">'),
            (r'\033\[35m', '<span style="color:#c084fc;">'),
            (r'\033\[36m', '<span style="color:#38bdf8;">'),
            (r'\033\[37m', '<span style="color:#f1f5f9;">'),
            (r'\033\[90m', '<span style="color:#94a3b8;">'),
            (r'\033\[91m', '<span style="color:#fca5a5;">'),
            (r'\033\[92m', '<span style="color:#6ee7b7;">'),
            (r'\033\[93m', '<span style="color:#fde047;">'),
            (r'\033\[94m', '<span style="color:#93c5fd;">'),
            (r'\033\[1m', '<b>'),
            (r'\033\[22m', '</b>'),
            (r'\033\[0m', '</span>'),
        ]
        for pattern, tag in ansi_replacements:
            escaped = re.sub(pattern, tag, escaped)
        escaped = re.sub(r'\033\[[0-9;]*[a-zA-Z]', '', escaped)
        return escaped
