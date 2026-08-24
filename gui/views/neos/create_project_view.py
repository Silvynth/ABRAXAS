#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS | NEOS - FORMULARIO DE CREACIÓN DE PROYECTO CON IA
# =====================================================================

import os
import subprocess
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QLineEdit, QPlainTextEdit, QFrame, 
    QCheckBox, QRadioButton, QButtonGroup, QScrollArea,
    QProgressBar
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer

from core.projects import get_projects_dir
from core.engine import AbraxasConfig
from core.ai import generate_with_chat_model

class AIReadmeWorker(QThread):
    """Hilo de fondo para no bloquear la interfaz mientras el modelo conversacional responde."""
    success = Signal(str)
    error = Signal(str)

    def __init__(self, prompt: str, system_prompt: str, config_target: str, parent=None):
        super().__init__(parent)
        self.prompt = prompt
        self.system_prompt = system_prompt
        self.config_target = config_target

    def run(self):
        try:
            result = generate_with_chat_model(self.prompt, self.system_prompt, self.config_target)
            self.success.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class CreateProjectView(QWidget):
    """Formulario interactivo para crear proyectos, configurar Git/GitHub y redactar README con el modelo conversacional."""
    
    project_created = Signal(str)    # Emite la ruta del proyecto creado
    cancel_requested = Signal()      # Emite cuando se cancela la creación

    def __init__(self, config_target, parent=None):
        super().__init__(parent)
        self.config_target = config_target
        self.base_dir = get_projects_dir(self.config_target)
        self.ai_mode_active = False
        self.ai_worker = None

        self.init_ui()

    def refresh_base_dir(self):
        self.base_dir = get_projects_dir(self.config_target)
        self.update_path_preview()
        cfg = AbraxasConfig(self.config_target)
        chat_model = cfg.get("ai.chat_model", "gemma2:9b")
        self.btn_ai_prompt.setText(f"🤖 Redactar con IA ({chat_model})")

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        form_layout = QVBoxLayout(container)
        form_layout.setContentsMargins(4, 4, 12, 12)
        form_layout.setSpacing(16)

        # -------------------------------------------------------------
        # 1. INFORMACIÓN BÁSICA DEL PROYECTO
        # -------------------------------------------------------------
        card_basic = QFrame()
        card_basic.setProperty("class", "surface")
        l_basic = QVBoxLayout(card_basic)
        l_basic.setContentsMargins(18, 16, 18, 16)
        l_basic.setSpacing(10)

        lbl_sec1 = QLabel("📦 Información del Proyecto")
        lbl_sec1.setProperty("class", "section_title")
        l_basic.addWidget(lbl_sec1)

        l_basic.addWidget(QLabel("Nombre de la carpeta / repositorio:"))
        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("ej: mi-nuevo-proyecto")
        self.txt_name.textChanged.connect(self.update_path_preview)
        l_basic.addWidget(self.txt_name)

        self.lbl_path_preview = QLabel(f"📁 Ruta de destino: {self.base_dir}/...")
        self.lbl_path_preview.setStyleSheet("font-family: monospace; font-size: 11.5px; color: #9ca3af;")
        l_basic.addWidget(self.lbl_path_preview)

        l_basic.addWidget(QLabel("Descripción corta (opcional):"))
        self.txt_desc = QLineEdit()
        self.txt_desc.setPlaceholderText("ej: Sistema de automatización para flujos de trabajo")
        l_basic.addWidget(self.txt_desc)

        form_layout.addWidget(card_basic)

        # -------------------------------------------------------------
        # 2. CONFIGURACIÓN DE GIT Y GITHUB
        # -------------------------------------------------------------
        card_git = QFrame()
        card_git.setProperty("class", "surface")
        l_git = QVBoxLayout(card_git)
        l_git.setContentsMargins(18, 16, 18, 16)
        l_git.setSpacing(12)

        lbl_sec2 = QLabel("🐙 Control de Versiones & GitHub")
        lbl_sec2.setProperty("class", "section_title")
        l_git.addWidget(lbl_sec2)

        self.chk_git = QCheckBox("Inicializar repositorio Git local")
        self.chk_git.setChecked(True)
        self.chk_git.setCursor(Qt.PointingHandCursor)
        l_git.addWidget(self.chk_git)

        self.chk_github = QCheckBox("Sincronizar y publicar en GitHub")
        self.chk_github.setCursor(Qt.PointingHandCursor)
        self.chk_github.toggled.connect(self.toggle_github_options)
        l_git.addWidget(self.chk_github)

        self.box_github_opts = QFrame()
        self.box_github_opts.setStyleSheet("background-color: rgba(0, 0, 0, 0.2); border: 1px dashed #374151; border-radius: 8px; padding: 10px;")
        self.box_github_opts.setVisible(False)
        l_opts = QVBoxLayout(self.box_github_opts)
        l_opts.setSpacing(8)

        lbl_vis = QLabel("Visibilidad del Repositorio Remoto:")
        lbl_vis.setStyleSheet("font-weight: 600; font-size: 12px; color: #d1d5db;")
        l_opts.addWidget(lbl_vis)

        r_radios = QHBoxLayout()
        self.rb_public = QRadioButton("🌐 Público (Cualquiera puede verlo)")
        self.rb_public.setChecked(True)
        self.rb_public.setCursor(Qt.PointingHandCursor)

        self.rb_private = QRadioButton("🔒 Privado (Solo tú y colaboradores)")
        self.rb_private.setCursor(Qt.PointingHandCursor)

        self.btn_group_vis = QButtonGroup(self)
        self.btn_group_vis.addButton(self.rb_public)
        self.btn_group_vis.addButton(self.rb_private)

        r_radios.addWidget(self.rb_public)
        r_radios.addWidget(self.rb_private)
        r_radios.addStretch()
        l_opts.addLayout(r_radios)

        l_git.addWidget(self.box_github_opts)
        form_layout.addWidget(card_git)

        # -------------------------------------------------------------
        # 3. DOCUMENTACIÓN README.MD & ASISTENTE IA
        # -------------------------------------------------------------
        card_readme = QFrame()
        card_readme.setProperty("class", "surface")
        l_readme = QVBoxLayout(card_readme)
        l_readme.setContentsMargins(18, 16, 18, 16)
        l_readme.setSpacing(10)

        cfg = AbraxasConfig(self.config_target)
        self.current_chat_model = cfg.get("ai.chat_model", "gemma2:9b")

        r_readme_head = QHBoxLayout()
        lbl_sec3 = QLabel("📝 Documentación README.md")
        lbl_sec3.setProperty("class", "section_title")
        r_readme_head.addWidget(lbl_sec3, 1)

        self.btn_ai_prompt = QPushButton(f"🤖 Redactar con IA ({self.current_chat_model})")
        self.btn_ai_prompt.setProperty("class", "btn_mode_purple")
        self.btn_ai_prompt.setCursor(Qt.PointingHandCursor)
        self.btn_ai_prompt.setToolTip("Bloquear editor y abrir panel de contexto para el modelo conversacional")
        self.btn_ai_prompt.clicked.connect(self.open_ai_panel)
        r_readme_head.addWidget(self.btn_ai_prompt)

        l_readme.addLayout(r_readme_head)

        # Panel desplegable de Contexto para la IA
        self.box_ai_context = QFrame()
        self.box_ai_context.setStyleSheet("background-color: rgba(168, 85, 247, 0.08); border: 1px solid rgba(168, 85, 247, 0.4); border-radius: 8px; padding: 14px;")
        self.box_ai_context.setVisible(False)
        l_ai_ctx = QVBoxLayout(self.box_ai_context)
        l_ai_ctx.setSpacing(10)

        self.lbl_ai_title = QLabel(f"🪄 Contexto / Instrucciones para el Modelo ({self.current_chat_model}):")
        self.lbl_ai_title.setStyleSheet("font-weight: 700; font-size: 12px; color: #c084fc;")
        l_ai_ctx.addWidget(self.lbl_ai_title)

        self.txt_ai_prompt = QPlainTextEdit()
        self.txt_ai_prompt.setPlaceholderText("Describe qué hace tu proyecto, tecnologías, arquitectura, dependencias y ejemplos que quieras que el modelo conversacional redacte...")
        self.txt_ai_prompt.setFixedHeight(75)
        l_ai_ctx.addWidget(self.txt_ai_prompt)

        # Barra de estado de generación IA
        self.lbl_ai_status = QLabel("")
        self.lbl_ai_status.setWordWrap(True)
        self.lbl_ai_status.setStyleSheet("font-size: 12px; font-weight: 600; color: #a855f7;")
        l_ai_ctx.addWidget(self.lbl_ai_status)

        # Barra de progreso animada (estilo barra de carga)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        l_ai_ctx.addWidget(self.progress_bar)

        r_ai_btns = QHBoxLayout()
        self.btn_ai_generate = QPushButton("🚀 Generar con IA")
        self.btn_ai_generate.setProperty("class", "btn_mode_purple")
        self.btn_ai_generate.setCursor(Qt.PointingHandCursor)
        self.btn_ai_generate.clicked.connect(self.generate_readme_with_ai)

        self.btn_ai_fallback = QPushButton("📝 Usar Plantilla Base")
        self.btn_ai_fallback.setProperty("class", "browse")
        self.btn_ai_fallback.setCursor(Qt.PointingHandCursor)
        self.btn_ai_fallback.setVisible(False)
        self.btn_ai_fallback.clicked.connect(self.apply_fallback_template)

        self.btn_ai_cancel = QPushButton("❌ Desbloquear / Cancelar")
        self.btn_ai_cancel.setProperty("class", "browse")
        self.btn_ai_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_ai_cancel.clicked.connect(self.close_ai_panel)

        r_ai_btns.addWidget(self.btn_ai_generate)
        r_ai_btns.addWidget(self.btn_ai_fallback)
        r_ai_btns.addWidget(self.btn_ai_cancel)
        r_ai_btns.addStretch()
        l_ai_ctx.addLayout(r_ai_btns)

        l_readme.addWidget(self.box_ai_context)

        # Editor de README
        self.txt_readme = QPlainTextEdit()
        self.txt_readme.setMinimumHeight(180)
        self.txt_readme.setPlaceholderText("# Nombre del Proyecto\n\nDescripción del proyecto...")
        self.txt_readme.setPlainText("# Nuevo Proyecto\n\nDescripción general del proyecto.\n\n## Instalación\n```bash\n# Instrucciones de instalación\n```\n\n## Uso\n```bash\n# Ejemplo de ejecución\n```\n")
        l_readme.addWidget(self.txt_readme)

        form_layout.addWidget(card_readme)

        # -------------------------------------------------------------
        # 4. BOTONES DE ACCIÓN FINAL
        # -------------------------------------------------------------
        r_final = QHBoxLayout()
        r_final.setSpacing(10)

        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("font-weight: 600; font-size: 12px; color: #ef4444;")
        r_final.addWidget(self.lbl_status, 1)

        btn_cancel = QPushButton("❌ Cancelar")
        btn_cancel.setProperty("class", "browse")
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.clicked.connect(self.cancel_requested.emit)
        r_final.addWidget(btn_cancel)

        btn_create = QPushButton("✨ Crear Proyecto")
        btn_create.setProperty("class", "primary")
        btn_create.setCursor(Qt.PointingHandCursor)
        btn_create.clicked.connect(self.create_project)
        r_final.addWidget(btn_create)

        form_layout.addLayout(r_final)

        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def update_path_preview(self):
        name = self.txt_name.text().strip()
        if not name:
            self.lbl_path_preview.setText(f"📁 Ruta de destino: {self.base_dir}/...")
        else:
            self.lbl_path_preview.setText(f"📁 Ruta de destino: {os.path.join(self.base_dir, name)}")

    def toggle_github_options(self, checked):
        self.box_github_opts.setVisible(checked)

    def open_ai_panel(self):
        self.ai_mode_active = True
        self.box_ai_context.setVisible(True)
        self.btn_ai_fallback.setVisible(False)
        self.progress_bar.setVisible(False)
        self.lbl_ai_status.setText("")

        cfg = AbraxasConfig(self.config_target)
        self.current_chat_model = cfg.get("ai.chat_model", "gemma2:9b")
        self.lbl_ai_title.setText(f"🪄 Contexto / Instrucciones para el Modelo ({self.current_chat_model}):")

        # Bloquear editor
        self.txt_readme.setReadOnly(True)
        self.txt_readme.setStyleSheet("background-color: rgba(20, 21, 28, 0.7); color: #6b7280; border: 1px dashed #4b5563;")
        self.btn_ai_prompt.setEnabled(False)

    def close_ai_panel(self):
        self.ai_mode_active = False
        self.box_ai_context.setVisible(False)
        self.lbl_ai_status.setText("")
        self.progress_bar.setVisible(False)
        self.btn_ai_fallback.setVisible(False)
        # Desbloquear editor
        self.txt_readme.setReadOnly(False)
        self.txt_readme.setStyleSheet("")
        self.btn_ai_prompt.setEnabled(True)

    def generate_readme_with_ai(self):
        context_prompt = self.txt_ai_prompt.toPlainText().strip()
        name = self.txt_name.text().strip() or "Nuevo Proyecto"
        desc = self.txt_desc.text().strip()

        cfg = AbraxasConfig(self.config_target)
        chat_model = cfg.get("ai.chat_model", "gemma2:9b")

        self.lbl_ai_status.setText(f"⏳ Conectando con Ollama ({chat_model})... Generando contenido...")
        self.lbl_ai_status.setStyleSheet("font-size: 12px; font-weight: 600; color: #a855f7;")
        self.btn_ai_generate.setEnabled(False)
        self.btn_ai_fallback.setVisible(False)

        # Iniciar animación de barra de progreso continua
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(True)

        # Prompt directo y flexible: envía exactamente la instrucción del usuario
        if context_prompt:
            full_prompt = context_prompt
        else:
            full_prompt = f"Genera un README.md en Markdown para el proyecto '{name}'{f': {desc}' if desc else ''}."

        system_prompt = "Escribe exactamente lo que pide el usuario en formato Markdown, sin introducciones ni saludos ni despedidas."

        # Iniciar worker en hilo de fondo
        self.ai_worker = AIReadmeWorker(full_prompt, system_prompt, self.config_target)
        self.ai_worker.success.connect(self.on_ai_generate_success)
        self.ai_worker.error.connect(self.on_ai_generate_error)
        self.ai_worker.start()

    def on_ai_generate_success(self, generated_markdown: str):
        self.btn_ai_generate.setEnabled(True)
        # Completar barra al 100%
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.lbl_ai_status.setText("✨ ¡README generado con éxito por el modelo!")
        self.lbl_ai_status.setStyleSheet("font-size: 12px; font-weight: 600; color: #10b981;")

        content = generated_markdown.strip()
        if content.startswith("```markdown"):
            content = content[len("```markdown"):].strip()
        elif content.startswith("```"):
            content = content[3:].strip()
        if content.endswith("```"):
            content = content[:-3].strip()

        self.txt_readme.setPlainText(content)

        # Cerrar el panel tras breve retraso para disfrutar de la animación completa
        QTimer.singleShot(600, self.close_ai_panel)

    def on_ai_generate_error(self, error_msg: str):
        self.btn_ai_generate.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.btn_ai_fallback.setVisible(True)
        self.lbl_ai_status.setText(f"⚠️ {error_msg}")
        self.lbl_ai_status.setStyleSheet("font-size: 12px; font-weight: 600; color: #ef4444;")

    def apply_fallback_template(self):
        name = self.txt_name.text().strip() or "Nuevo Proyecto"
        desc = self.txt_desc.text().strip() or "Descripción del sistema y módulos."
        prompt = self.txt_ai_prompt.toPlainText().strip()
        fallback_md = f"""# {name}

> {desc}

## 📋 Resumen del Proyecto
{prompt if prompt else "Entorno modular y estructurado para desarrollo y automatización."}

## 🚀 Requisitos e Instalación
```bash
git clone https://github.com/usuario/{name}.git
cd {name}
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 🛠️ Tecnologías y Arquitectura
- **Python 3.12+** / **PySide6**
- Arquitectura modular desacoplada

## 📖 Guía de Uso
```bash
python3 main.py
```

## 📄 Licencia
Distribuido bajo la Licencia MIT.
"""
        self.txt_readme.setPlainText(fallback_md)
        self.close_ai_panel()

    def create_project(self):
        self.lbl_status.setText("")
        name = self.txt_name.text().strip()

        if not name:
            self.lbl_status.setText("⚠️ Por favor ingresa el nombre del proyecto.")
            return

        if not self.base_dir or not os.path.exists(self.base_dir):
            self.lbl_status.setText(f"⚠️ La ruta base de proyectos no existe: {self.base_dir}")
            return

        target_dir = os.path.join(self.base_dir, name)
        if os.path.exists(target_dir):
            self.lbl_status.setText("⚠️ Ya existe una carpeta con este nombre.")
            return

        try:
            # 1. Crear carpeta física
            os.makedirs(target_dir, exist_ok=True)

            # 2. Guardar README.md
            readme_content = self.txt_readme.toPlainText()
            readme_path = os.path.join(target_dir, "README.md")
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(readme_content)

            # 3. Inicializar Git si está marcado
            if self.chk_git.isChecked():
                subprocess.run(["git", "init"], cwd=target_dir, capture_output=True)
                subprocess.run(["git", "add", "."], cwd=target_dir, capture_output=True)
                subprocess.run(["git", "commit", "-m", "Initial commit from Abraxas"], cwd=target_dir, capture_output=True)

            # Notificar creación exitosa
            self.project_created.emit(target_dir)

        except Exception as e:
            self.lbl_status.setText(f"❌ Error al crear proyecto: {e}")
