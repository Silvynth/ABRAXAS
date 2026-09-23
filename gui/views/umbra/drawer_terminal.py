#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS | UMBRA - SLIDING DRAWER TERMINAL (CINEMATIC CONSOLE)
# =====================================================================

import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
    QTextEdit, QPushButton, QGraphicsDropShadowEffect, QApplication
)
from PySide6.QtCore import Qt, Signal, QVariantAnimation, QEasingCurve
from PySide6.QtGui import QColor, QCursor, QFont

class UmbraTerminalDisplay(QTextEdit):
    """Visor de consola con formato HTML, timestamps precisos y estilo ciber-operador idéntico a Lumen."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setCursor(Qt.IBeamCursor)
        self.setLineWrapMode(QTextEdit.WidgetWidth)
        self.setStyleSheet("""
            QTextEdit {
                background-color: transparent;
                color: #e5e7eb;
                font-family: 'JetBrains Mono', 'Fira Code', 'DejaVu Sans Mono', 'Consolas', monospace;
                font-size: 12.5px;
                line-height: 1.5;
                border: none;
                padding: 14px 18px;
                selection-background-color: rgba(99, 102, 241, 0.40);
                selection-color: #ffffff;
            }
            QScrollBar:vertical {
                background: rgba(255, 255, 255, 0.02);
                width: 8px;
                margin: 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.12);
                min-height: 24px;
                border-radius: 4px;
                border: none;
            }
            QScrollBar::handle:vertical:hover {
                background: #6366f1;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

    def log(self, tag: str, message: str, tag_color: str = "#818cf8", text_color: str = "#e5e7eb", prefix: str = "◈"):
        """Inserta una línea estilizada con timestamp en la consola."""
        now = datetime.datetime.now().strftime("%H:%M:%S")
        html = (
            f"<div style='margin-bottom: 4px; font-family: monospace;'>"
            f"<span style='color: #6b7280; font-weight: 500;'>[{now}]</span> "
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

    def log_btrfs(self, tag: str, message: str):
        self.log(tag, message, tag_color="#34d399", text_color="#a7f3d0", prefix="🛡️")

    def log_kernel(self, tag: str, message: str):
        self.log(tag, message, tag_color="#c084fc", text_color="#f3e8ff", prefix="🐧")

    def log_purge(self, tag: str, message: str):
        self.log(tag, message, tag_color="#fbbf24", text_color="#fef3c7", prefix="🧹")

    def log_warn(self, tag: str, message: str):
        self.log(tag, message, tag_color="#f59e0b", text_color="#fed7aa", prefix="⚠")

    def log_error(self, tag: str, message: str):
        self.log(tag, message, tag_color="#f87171", text_color="#fecaca", prefix="✖")


class HandleBarPill(QFrame):
    """Pill / Barra táctil interactiva ubicada en el centro superior de la terminal."""
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedHeight(18)
        self.setMinimumWidth(160)
        self.setMaximumWidth(220)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)

        # Micro-barrita estilo handle _
        self.pill_indicator = QFrame()
        self.pill_indicator.setFixedHeight(4)
        self.pill_indicator.setFixedWidth(56)
        self.pill_indicator.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.35);
                border-radius: 2px;
            }
        """)
        layout.addWidget(self.pill_indicator)

        self.setStyleSheet("""
            HandleBarPill {
                background-color: transparent;
            }
            HandleBarPill:hover QFrame {
                background-color: #818cf8;
            }
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def set_glow(self, active: bool):
        color = "#a855f7" if active else "rgba(255, 255, 255, 0.35)"
        self.pill_indicator.setStyleSheet(f"""
            QFrame {{
                background-color: {color};
                border-radius: 2px;
            }}
        """)


class UmbraDrawerTerminal(QFrame):
    """
    Consola táctica deslizante de UMBRA:
    - Estado Contraído (Docked 42px): Manija central, prompt pasivo, no estorba los sectores.
    - Estado Expandido (Max Workspace ~420px): Sube con animación OutCubic cubriendo los sectores.
    - Manija central superior interactiva (_) para alternar estados con un clic.
    """
    state_changed = Signal(bool)  # True: Expandido, False: Contraído

    COLLAPSED_HEIGHT = 42
    DEFAULT_EXPANDED_HEIGHT = 380

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_expanded = False
        self.expanded_height = self.DEFAULT_EXPANDED_HEIGHT
        self.init_ui()
        self.init_animation()

    def init_ui(self):
        self.setObjectName("umbra_drawer_terminal")
        self.setStyleSheet("""
            QFrame#umbra_drawer_terminal {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(20, 23, 33, 0.95), stop:1 rgba(14, 16, 23, 0.95));
                border: 1px solid rgba(99, 102, 241, 0.28);
                border-radius: 12px 12px 0px 0px;
            }
        """)

        # Sombra sutil para efecto de panel flotante superior
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, -4)
        self.setGraphicsEffect(shadow)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # -------------------------------------------------------------
        # CABECERA SUPERIOR: Prompt Izquierda, Manija Centro, Acciones Derecha (Estilo Lumen)
        # -------------------------------------------------------------
        self.header_bar = QWidget()
        self.header_bar.setObjectName("umbra_terminal_header")
        self.header_bar.setFixedHeight(38)
        self.header_bar.setStyleSheet("""
            QWidget#umbra_terminal_header {
                background-color: rgba(255, 255, 255, 0.03);
                border-bottom: 1px solid rgba(255, 255, 255, 0.08);
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
                padding: 4px 10px;
            }
        """)
        h_layout = QHBoxLayout(self.header_bar)
        h_layout.setContentsMargins(12, 6, 12, 6)
        h_layout.setSpacing(10)

        # Left: Dots Unix + Prompt & Estado
        lbl_dots = QLabel("🔴  🟡  🟢")
        lbl_dots.setStyleSheet("font-size: 9px;")
        h_layout.addWidget(lbl_dots)

        self.lbl_prompt = QLabel("umbra-terminal@cachyos:~$")
        self.lbl_prompt.setStyleSheet("""
            color: #a5b4fc;
            font-size: 12px;
            font-weight: 700;
            font-family: 'JetBrains Mono', 'Fira Code', 'DejaVu Sans Mono', monospace;
        """)
        h_layout.addWidget(self.lbl_prompt)

        # Center: Manija central superior interactiva (_)
        h_layout.addStretch()
        self.handle_pill = HandleBarPill(self)
        self.handle_pill.clicked.connect(self.toggle_drawer)
        h_layout.addWidget(self.handle_pill)
        h_layout.addStretch()

        # Right: Acciones idénticas a Lumen + Toggle Drawer
        right_box = QHBoxLayout()
        right_box.setSpacing(6)

        btn_copy = QPushButton("📋 Copiar")
        btn_copy.setCursor(QCursor(Qt.PointingHandCursor))
        btn_copy.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.04);
                color: #9ca3af;
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 4px;
                padding: 3px 9px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                color: #ffffff;
                border-color: #6366f1;
                background-color: rgba(99, 102, 241, 0.20);
            }
        """)
        btn_copy.clicked.connect(self.copy_output)
        right_box.addWidget(btn_copy)

        btn_clear = QPushButton("🧹 Limpiar")
        btn_clear.setCursor(QCursor(Qt.PointingHandCursor))
        btn_clear.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.04);
                color: #9ca3af;
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 4px;
                padding: 3px 9px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                color: #f87171;
                border-color: #ef4444;
                background-color: rgba(239, 68, 68, 0.15);
            }
        """)
        btn_clear.clicked.connect(self.clear_output)
        right_box.addWidget(btn_clear)

        self.btn_toggle = QPushButton("▲ Expandir")
        self.btn_toggle.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_toggle.setStyleSheet("""
            QPushButton {
                background: rgba(99, 102, 241, 0.18);
                border: 1px solid rgba(99, 102, 241, 0.40);
                border-radius: 4px;
                color: #c7d2fe;
                font-size: 11px;
                font-weight: 700;
                padding: 3px 10px;
            }
            QPushButton:hover {
                background: rgba(99, 102, 241, 0.35);
                border-color: #818cf8;
                color: #ffffff;
            }
        """)
        self.btn_toggle.clicked.connect(self.toggle_drawer)
        right_box.addWidget(self.btn_toggle)

        self.lbl_t_status = QLabel("⚡ VISOR DE SALIDA [READ-ONLY]")
        self.lbl_t_status.setStyleSheet("""
            font-size: 10px;
            font-weight: 800;
            color: #38bdf8;
            background-color: rgba(6, 182, 212, 0.12);
            border: 1px solid rgba(6, 182, 212, 0.35);
            border-radius: 4px;
            padding: 2px 8px;
            letter-spacing: 0.5px;
        """)
        right_box.addWidget(self.lbl_t_status)

        h_layout.addLayout(right_box)
        self.main_layout.addWidget(self.header_bar)

        # -------------------------------------------------------------
        # CUERPO DE LA TERMINAL: Visor de texto enriquecido idéntico a Lumen
        # -------------------------------------------------------------
        self.display = UmbraTerminalDisplay(self)
        self.main_layout.addWidget(self.display, 1)

        # Estado inicial contraído
        self.setFixedHeight(self.COLLAPSED_HEIGHT)
        self.display.setVisible(False)

        # Log inicial de bienvenida
        self.display.log_info("UMBRA", "Consola táctica del operador inicializada. Sistema listo.")
        self.display.log("SYS", "Núcleo CachyOS Linux · Resiliencia Btrfs & Gestor de Infraestructura", tag_color="#38bdf8")

    def init_animation(self):
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(320)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.valueChanged.connect(self._on_anim_frame)
        self.anim.finished.connect(self._on_anim_finished)

    def _on_anim_frame(self, val):
        self.setFixedHeight(int(val))

    def _on_anim_finished(self):
        if not self.is_expanded:
            self.display.setVisible(False)
            self.btn_toggle.setText("▲ Expandir")
            self.handle_pill.set_glow(False)
            self.setFixedHeight(self.COLLAPSED_HEIGHT)
        else:
            self.btn_toggle.setText("▼ Contraer")
            self.handle_pill.set_glow(True)
            self.setMinimumHeight(self.COLLAPSED_HEIGHT)
            self.setMaximumHeight(16777215)
        self.state_changed.emit(self.is_expanded)

    def toggle_drawer(self):
        """Alterna el estado entre contraído abajo y expandido máximo."""
        if self.is_expanded:
            self.collapse()
        else:
            self.expand()

    def expand(self, target_height: int = None):
        """Despliega la terminal hacia arriba sin desbordar el contenedor."""
        if self.anim.state() == QVariantAnimation.Running:
            self.anim.stop()

        self.display.setVisible(True)
        # Limitar estrictamente la altura para no empujar los paneles fijos superiores
        parent_h = self.parent().height() if self.parent() else 400
        h_target = min(target_height or self.expanded_height, parent_h)
        if h_target < 180 and parent_h > 200:
            h_target = parent_h

        self.anim.setStartValue(self.height())
        self.anim.setEndValue(h_target)
        self.is_expanded = True
        self.btn_toggle.setText("▼ Contraer")
        self.handle_pill.set_glow(True)
        self.anim.start()

    def collapse(self):
        """Contrae la terminal a su barra mínima en la base (42px)."""
        if self.anim.state() == QVariantAnimation.Running:
            self.anim.stop()

        self.anim.setStartValue(self.height())
        self.anim.setEndValue(self.COLLAPSED_HEIGHT)
        self.is_expanded = False
        self.btn_toggle.setText("▲ Expandir")
        self.handle_pill.set_glow(False)
        self.anim.start()

    def copy_output(self):
        text = self.display.toPlainText()
        if text.strip():
            QApplication.clipboard().setText(text)
            self.display.log_info("CLIPBOARD", "Contenido de la consola copiado al portapapeles.")

    def clear_output(self):
        self.display.clear()
        self.display.log("CONSOLE", "Consola reiniciada por el operador.", tag_color="#94a3b8")
