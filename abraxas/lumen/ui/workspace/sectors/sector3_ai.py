"""
❖ ABRAXAS 2.0 | Lumen UI: Sector 03 - Herramientas, Documentación & IA Local
Auditoría semántica de diffs con Ollama, generación de changelogs y explorador de markdown.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QTextEdit
)
from PySide6.QtCore import Qt, Signal

from abraxas.lumen.models.project import Project

class Sector3AiView(QWidget):
    """Sector táctico 03: Agentes IA locales, análisis de seguridad y documentación."""
    
    action_requested = Signal(str, dict)
    log_emitted = Signal(str)

    def __init__(self, project: Project = None, parent=None):
        super().__init__(parent)
        self.project = project
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # 1. Cabecera del sector
        card_header = QFrame()
        card_header.setProperty("class", "sector_card")
        ch_layout = QVBoxLayout(card_header)
        ch_layout.setContentsMargins(20, 14, 20, 14)
        ch_layout.setSpacing(4)

        tag = QLabel("SECTOR 03 // HERRAMIENTAS, DOCUMENTACIÓN & IA LOCAL")
        tag.setProperty("class", "sector_micro_tag")
        title = QLabel("❖ Copiloto Local & Análisis de Código")
        title.setProperty("class", "sector_title")
        
        ch_layout.addWidget(tag)
        ch_layout.addWidget(title)
        layout.addWidget(card_header)

        # 2. Barra de acciones de IA
        ai_actions = QFrame()
        ai_actions.setProperty("class", "sector_card")
        act_layout = QHBoxLayout(ai_actions)
        act_layout.setContentsMargins(14, 10, 14, 10)
        act_layout.setSpacing(8)

        self.btn_audit = QPushButton("🛡️ Auditar Diff con IA")
        self.btn_audit.setProperty("class", "cyber_btn_primary")
        self.btn_audit.clicked.connect(lambda: self._emit_action("ai_audit_diff"))

        self.btn_changelog = QPushButton("📝 Generar AI Changelog")
        self.btn_changelog.setProperty("class", "cyber_btn")
        self.btn_changelog.clicked.connect(lambda: self._emit_action("ai_generate_changelog"))

        self.btn_readme = QPushButton("📖 Inspeccionar README")
        self.btn_readme.setProperty("class", "cyber_btn")
        self.btn_readme.clicked.connect(lambda: self._emit_action("view_readme"))

        act_layout.addWidget(self.btn_audit)
        act_layout.addWidget(self.btn_changelog)
        act_layout.addWidget(self.btn_readme)
        act_layout.addStretch()
        layout.addWidget(ai_actions)

        # 3. Visor de resultados / documentación
        viewer_box = QFrame()
        viewer_box.setProperty("class", "sector_card")
        vb_layout = QVBoxLayout(viewer_box)
        vb_layout.setContentsMargins(16, 14, 16, 14)
        vb_layout.setSpacing(8)

        self.lbl_viewer_title = QLabel("📄 Salida de Análisis / Documentación")
        self.lbl_viewer_title.setStyleSheet("color: #ffffff; font-weight: 700; font-size: 13px;")
        vb_layout.addWidget(self.lbl_viewer_title)

        self.txt_display = QTextEdit()
        self.txt_display.setReadOnly(True)
        self.txt_display.setPlaceholderText("Presiona cualquiera de los botones de arriba para consultar o auditar con IA local...")
        self.txt_display.setStyleSheet(
            "background-color: #0c0d10; border: 1px solid rgba(255, 255, 255, 0.08); "
            "border-radius: 6px; padding: 10px; color: #cbd5e1; font-family: 'JetBrains Mono', monospace; font-size: 12px;"
        )
        vb_layout.addWidget(self.txt_display)
        layout.addWidget(viewer_box, 1)

    def update_project(self, project: Project):
        self.project = project
        if project:
            readme_path = project.path / "README.md"
            if readme_path.is_file():
                try:
                    self.txt_display.setPlainText(readme_path.read_text(encoding="utf-8")[:1500] + "\n\n[...]")
                except Exception:
                    pass

    def _emit_action(self, action_name: str):
        self.action_requested.emit(action_name, {})
        self.log_emitted.emit(f"Acción invocada: [{action_name}] en {self.project.name if self.project else 'desconocido'}")
