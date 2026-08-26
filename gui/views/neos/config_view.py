#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS | NEOS - CONFIGURATION VIEW (config.toml CRUD)
# =====================================================================

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QLineEdit, QFileDialog, 
    QCheckBox, QFrame, QScrollArea,
    QComboBox, QStyledItemDelegate, QTextEdit
)
from PySide6.QtCore import Qt, Signal

from core.setup import write_toml_dict, read_toml_dict
from core.ai import get_model_skill, SKILLS_DIR

class ConfigView(QWidget):
    """Vista de administración y edición activa de config.toml en NEOS."""
    
    theme_changed = Signal(str)
    config_saved = Signal(dict)

    def __init__(self, config_target, parent=None):
        super().__init__(parent)
        self.config_target = config_target
        self.cfg = read_toml_dict(self.config_target)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # Header Title
        lbl_t = QLabel("🛠 CONFIG")
        lbl_t.setProperty("class", "page_title")
        lbl_sub = QLabel(f"Gestor de Configuración Activa ({self.config_target})")
        lbl_sub.setProperty("class", "page_subtitle")
        layout.addWidget(lbl_t)
        layout.addWidget(lbl_sub)

        # Scroll Area for all config sections
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        scroll_widget = QWidget()
        s_layout = QVBoxLayout(scroll_widget)
        s_layout.setContentsMargins(0, 0, 10, 0)
        s_layout.setSpacing(14)

        # -------------------------------------------------------------
        # Section 1: Rutas de Trabajo ([paths])
        # -------------------------------------------------------------
        card_paths = QFrame()
        card_paths.setProperty("class", "surface")
        l_paths = QVBoxLayout(card_paths)
        l_paths.setSpacing(10)

        lbl_sec1 = QLabel("📁 Rutas del Sistema ([paths])")
        lbl_sec1.setProperty("class", "section_title")
        l_paths.addWidget(lbl_sec1)

        # Projects Dir
        l_paths.addWidget(QLabel("Directorio raíz de proyectos:"))
        r_proj = QHBoxLayout()
        self.txt_cfg_proj = QLineEdit(self.cfg.get("paths", {}).get("projects_dir", "~/Proyectos"))
        btn_proj = QPushButton("Examinar")
        btn_proj.setProperty("class", "browse")
        btn_proj.clicked.connect(lambda: self.browse_folder(self.txt_cfg_proj))
        r_proj.addWidget(self.txt_cfg_proj)
        r_proj.addWidget(btn_proj)
        l_paths.addLayout(r_proj)

        # Vault Dir
        l_paths.addWidget(QLabel("Bóveda de notas / Obsidian:"))
        r_vault = QHBoxLayout()
        self.txt_cfg_vault = QLineEdit(self.cfg.get("paths", {}).get("vault_dir", "~/Vault"))
        btn_vault = QPushButton("Examinar")
        btn_vault.setProperty("class", "browse")
        btn_vault.clicked.connect(lambda: self.browse_folder(self.txt_cfg_vault))
        r_vault.addWidget(self.txt_cfg_vault)
        r_vault.addWidget(btn_vault)
        l_paths.addLayout(r_vault)

        # Snapshots Dir
        l_paths.addWidget(QLabel("Subvolumen de instantáneas Btrfs / Snapper:"))
        self.txt_cfg_snap = QLineEdit(self.cfg.get("paths", {}).get("snapshots_dir", "/.snapshots"))
        l_paths.addWidget(self.txt_cfg_snap)

        s_layout.addWidget(card_paths)

        # -------------------------------------------------------------
        # Section 2: Motor de Inteligencia Artificial ([ai])
        # -------------------------------------------------------------
        card_ai = QFrame()
        card_ai.setProperty("class", "surface")
        l_ai = QVBoxLayout(card_ai)
        l_ai.setSpacing(10)

        lbl_sec2 = QLabel("🧠 Motor de Asistencia IA Local ([ai])")
        lbl_sec2.setProperty("class", "section_title")
        l_ai.addWidget(lbl_sec2)

        self.chk_cfg_ai = QCheckBox("Habilitar Invocación de IA en ABRAXAS (bajo demanda)")
        self.chk_cfg_ai.setChecked(self.cfg.get("ai", {}).get("enabled", True))
        l_ai.addWidget(self.chk_cfg_ai)

        row_ai1 = QHBoxLayout()
        row_ai1.addWidget(QLabel("Proveedor / Motor:"))
        self.cmb_cfg_provider = QComboBox()
        self.cmb_cfg_provider.setItemDelegate(QStyledItemDelegate())
        self.cmb_cfg_provider.addItems(["ollama", "openai-compatible"])
        row_ai1.addWidget(self.cmb_cfg_provider, 1)
        l_ai.addLayout(row_ai1)

        # 1. Conversational Model
        l_ai.addWidget(QLabel("Modelo Conversacional (Chatbox & Obsidian):"))
        row_ai_chat = QHBoxLayout()
        row_ai_chat.setSpacing(10)
        self.cmb_cfg_chat_model = QComboBox()
        self.cmb_cfg_chat_model.setItemDelegate(QStyledItemDelegate())
        chat_default = self.cfg.get("ai", {}).get("chat_model", "llama3.1:8b")
        presets_chat = ["llama3.1:8b", "mistral:7b", "gemma2:9b", "qwen2.5:7b", "Personalizado..."]
        if chat_default not in presets_chat:
            presets_chat.insert(0, chat_default)
        self.cmb_cfg_chat_model.addItems(presets_chat)
        if chat_default in presets_chat:
            self.cmb_cfg_chat_model.setCurrentText(chat_default)

        self.txt_cfg_chat_model = QLineEdit(chat_default)
        self.txt_cfg_chat_model.setPlaceholderText("Nombre / modelo personalizado...")
        self.txt_cfg_chat_model.setToolTip("Introduce un nombre o tag personalizado de modelo para el chat")
        self.cmb_cfg_chat_model.currentTextChanged.connect(
            lambda t: self.txt_cfg_chat_model.setText(t) if t != "Personalizado..." else None
        )
        row_ai_chat.addWidget(self.cmb_cfg_chat_model, 1)
        row_ai_chat.addWidget(self.txt_cfg_chat_model, 1)
        l_ai.addLayout(row_ai_chat)

        # 2. Heavy Dev Model
        l_ai.addWidget(QLabel("Modelo Pesado Dev (Refactor & Auditoría Profunda):"))
        row_ai_heavy = QHBoxLayout()
        row_ai_heavy.setSpacing(10)
        self.cmb_cfg_heavy_model = QComboBox()
        self.cmb_cfg_heavy_model.setItemDelegate(QStyledItemDelegate())
        heavy_default = self.cfg.get("ai", {}).get("heavy_model", "qwen2.5-coder:14b")
        presets_heavy = ["qwen2.5-coder:14b", "deepseek-coder:14b", "llama3.1:8b", "Personalizado..."]
        if heavy_default not in presets_heavy:
            presets_heavy.insert(0, heavy_default)
        self.cmb_cfg_heavy_model.addItems(presets_heavy)
        if heavy_default in presets_heavy:
            self.cmb_cfg_heavy_model.setCurrentText(heavy_default)

        self.txt_cfg_heavy_model = QLineEdit(heavy_default)
        self.txt_cfg_heavy_model.setPlaceholderText("Nombre / modelo personalizado...")
        self.txt_cfg_heavy_model.setToolTip("Introduce un nombre o tag personalizado para el modelo pesado de desarrollo")
        self.cmb_cfg_heavy_model.currentTextChanged.connect(
            lambda t: self.txt_cfg_heavy_model.setText(t) if t != "Personalizado..." else None
        )
        row_ai_heavy.addWidget(self.cmb_cfg_heavy_model, 1)
        row_ai_heavy.addWidget(self.txt_cfg_heavy_model, 1)
        l_ai.addLayout(row_ai_heavy)

        # 3. Light Dev Model
        l_ai.addWidget(QLabel("Modelo Ligero Dev (Git Rápido & Auditoría Ágil):"))
        row_ai_light = QHBoxLayout()
        row_ai_light.setSpacing(10)
        self.cmb_cfg_light_model = QComboBox()
        self.cmb_cfg_light_model.setItemDelegate(QStyledItemDelegate())
        light_default = self.cfg.get("ai", {}).get("light_model", "qwen2.5-coder:7b")
        presets_light = ["qwen2.5-coder:7b", "llama3.2:3b", "gemma2:2b", "Personalizado..."]
        if light_default not in presets_light:
            presets_light.insert(0, light_default)
        self.cmb_cfg_light_model.addItems(presets_light)
        if light_default in presets_light:
            self.cmb_cfg_light_model.setCurrentText(light_default)

        self.txt_cfg_light_model = QLineEdit(light_default)
        self.txt_cfg_light_model.setPlaceholderText("Nombre / modelo personalizado...")
        self.txt_cfg_light_model.setToolTip("Introduce un nombre o tag personalizado para el modelo ligero de desarrollo")
        self.cmb_cfg_light_model.currentTextChanged.connect(
            lambda t: self.txt_cfg_light_model.setText(t) if t != "Personalizado..." else None
        )
        row_ai_light.addWidget(self.cmb_cfg_light_model, 1)
        row_ai_light.addWidget(self.txt_cfg_light_model, 1)
        l_ai.addLayout(row_ai_light)

        row_ai3 = QHBoxLayout()
        row_ai3.addWidget(QLabel("Endpoint Servidor:"))
        self.txt_cfg_endpoint = QLineEdit(self.cfg.get("ai", {}).get("endpoint", "http://localhost:11434"))
        row_ai3.addWidget(self.txt_cfg_endpoint, 1)
        l_ai.addLayout(row_ai3)

        s_layout.addWidget(card_ai)

        # -------------------------------------------------------------
        # Section 2.1: Skills & Directivas de Comportamiento IA ([ai.skills])
        # -------------------------------------------------------------
        card_skills = QFrame()
        card_skills.setProperty("class", "surface")
        l_sk = QVBoxLayout(card_skills)
        l_sk.setSpacing(10)

        h_sk_title = QHBoxLayout()
        lbl_sec_sk = QLabel("📜 Skills & Directivas de Comportamiento IA ([ai.skills])")
        lbl_sec_sk.setProperty("class", "section_title")
        h_sk_title.addWidget(lbl_sec_sk)
        h_sk_title.addStretch()

        btn_reset_skills = QPushButton("🔄 Cargar Estándar Artemis")
        btn_reset_skills.setCursor(Qt.PointingHandCursor)
        btn_reset_skills.setStyleSheet("""
            QPushButton {
                background-color: rgba(99, 102, 241, 0.15);
                color: #c7d2fe;
                border: 1px solid rgba(99, 102, 241, 0.35);
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: rgba(99, 102, 241, 0.30);
                border-color: #818cf8;
                color: #ffffff;
            }
        """)
        btn_reset_skills.clicked.connect(self.load_artemis_skills_presets)
        h_sk_title.addWidget(btn_reset_skills)
        l_sk.addLayout(h_sk_title)

        lbl_sk_sub = QLabel(
            "Define el comportamiento, tono y protocolo técnico de razonamiento para cada uno de los 3 modelos de IA "
            "(Referencia: Protocolos de Auditoría y Git de Artemis)."
        )
        lbl_sk_sub.setProperty("class", "card_desc")
        lbl_sk_sub.setWordWrap(True)
        l_sk.addWidget(lbl_sk_sub)

        # 1. Skill Conversacional
        lbl_sk_chat = QLabel("💬 Skill: Modelo Conversacional (Chatbox & Obsidian):")
        lbl_sk_chat.setStyleSheet("font-weight: 700; color: #fbbf24; font-size: 12px;")
        l_sk.addWidget(lbl_sk_chat)

        self.txt_sk_chat = QTextEdit()
        self.txt_sk_chat.setMinimumHeight(65)
        self.txt_sk_chat.setMaximumHeight(85)
        self.txt_sk_chat.setPlainText(get_model_skill("chat", self.config_target))
        l_sk.addWidget(self.txt_sk_chat)

        # 2. Skill Modelo Pesado
        lbl_sk_heavy = QLabel("🧠 Skill: Modelo Pesado Dev (Auditoría Profunda & Refactor — Protocolo audit.txt):")
        lbl_sk_heavy.setStyleSheet("font-weight: 700; color: #c084fc; font-size: 12px;")
        l_sk.addWidget(lbl_sk_heavy)

        self.txt_sk_heavy = QTextEdit()
        self.txt_sk_heavy.setMinimumHeight(80)
        self.txt_sk_heavy.setMaximumHeight(115)
        self.txt_sk_heavy.setPlainText(get_model_skill("heavy", self.config_target))
        l_sk.addWidget(self.txt_sk_heavy)

        # 3. Skill Modelo Ligero
        lbl_sk_light = QLabel("⚡ Skill: Modelo Ligero Dev (Git Rápido, Commits & Diff — Protocolo commit_hex.txt):")
        lbl_sk_light.setStyleSheet("font-weight: 700; color: #38bdf8; font-size: 12px;")
        l_sk.addWidget(lbl_sk_light)

        self.txt_sk_light = QTextEdit()
        self.txt_sk_light.setMinimumHeight(80)
        self.txt_sk_light.setMaximumHeight(115)
        self.txt_sk_light.setPlainText(get_model_skill("light", self.config_target))
        l_sk.addWidget(self.txt_sk_light)

        s_layout.addWidget(card_skills)

        # -------------------------------------------------------------
        # Section 3: Entorno de Desarrollo ([development])
        # -------------------------------------------------------------
        card_dev = QFrame()
        card_dev.setProperty("class", "surface")
        l_dev = QVBoxLayout(card_dev)
        l_dev.setSpacing(10)

        lbl_sec_dev = QLabel("⚙️ Entornos de Desarrollo ([development])")
        lbl_sec_dev.setProperty("class", "section_title")
        l_dev.addWidget(lbl_sec_dev)

        self.chk_cfg_venv = QCheckBox("Detección automática de entornos virtuales Python (.venv)")
        self.chk_cfg_venv.setChecked(self.cfg.get("development", {}).get("venv_auto_detect", True))
        l_dev.addWidget(self.chk_cfg_venv)

        self.chk_cfg_docker = QCheckBox("Monitoreo de contenedores Docker activos")
        self.chk_cfg_docker.setChecked(self.cfg.get("development", {}).get("docker_monitor", True))
        l_dev.addWidget(self.chk_cfg_docker)

        s_layout.addWidget(card_dev)

        # -------------------------------------------------------------
        # Section 4: Mantenimiento y Sistema Operativo ([system])
        # -------------------------------------------------------------
        card_sys = QFrame()
        card_sys.setProperty("class", "surface")
        l_sys = QVBoxLayout(card_sys)
        l_sys.setSpacing(10)

        lbl_sec_sys = QLabel("🛡️ Mantenimiento y Sistema Operativo ([system])")
        lbl_sec_sys.setProperty("class", "section_title")
        l_sys.addWidget(lbl_sec_sys)

        self.chk_cfg_btrfs = QCheckBox("Habilitar Instantáneas Atómicas Btrfs (Snapshots antes de cambios)")
        self.chk_cfg_btrfs.setChecked(self.cfg.get("system", {}).get("btrfs_snapshots", True))
        l_sys.addWidget(self.chk_cfg_btrfs)

        row_snapper = QHBoxLayout()
        row_snapper.addWidget(QLabel("Configuración / Perfil de Snapper:"))
        self.txt_cfg_snapper = QLineEdit(self.cfg.get("system", {}).get("snapper_config", "root"))
        row_snapper.addWidget(self.txt_cfg_snapper, 1)
        l_sys.addLayout(row_snapper)

        self.chk_cfg_safe_upd = QCheckBox("Actualizaciones seguras con verificación previa de integridad")
        self.chk_cfg_safe_upd.setChecked(self.cfg.get("system", {}).get("safe_updates", True))
        l_sys.addWidget(self.chk_cfg_safe_upd)

        self.chk_cfg_arch_news = QCheckBox("Comprobar noticias y alertas críticas de Arch Linux antes de actualizar")
        self.chk_cfg_arch_news.setChecked(self.cfg.get("system", {}).get("check_arch_news", True))
        l_sys.addWidget(self.chk_cfg_arch_news)

        s_layout.addWidget(card_sys)

        # -------------------------------------------------------------
        # Section 5: Apariencia & Interfaz ([abraxas])
        # -------------------------------------------------------------
        card_app = QFrame()
        card_app.setProperty("class", "surface")
        l_app = QVBoxLayout(card_app)
        l_app.setSpacing(10)

        lbl_sec3 = QLabel("🎨 Apariencia y Sistema ([abraxas])")
        lbl_sec3.setProperty("class", "section_title")
        l_app.addWidget(lbl_sec3)

        row_app1 = QHBoxLayout()
        row_app1.addWidget(QLabel("Tema Visual:"))
        self.cmb_cfg_theme = QComboBox()
        self.cmb_cfg_theme.setItemDelegate(QStyledItemDelegate())
        self.cmb_cfg_theme.addItems([
            "🔄 Sincronizar con Sistema (Auto / Noctalia)",
            "Noctalia Minimal", 
            "Dark Cyberpunk", 
            "Monocromo Puro"
        ])
        curr_th = self.cfg.get("abraxas", {}).get("theme", "system_sync")
        if curr_th == "system_sync" or "sync" in curr_th or "auto" in curr_th:
            self.cmb_cfg_theme.setCurrentIndex(0)
        elif "cyberpunk" in curr_th:
            self.cmb_cfg_theme.setCurrentIndex(2)
        elif "monochrome" in curr_th:
            self.cmb_cfg_theme.setCurrentIndex(3)
        else:
            self.cmb_cfg_theme.setCurrentIndex(1)
        row_app1.addWidget(self.cmb_cfg_theme, 1)
        l_app.addLayout(row_app1)

        row_app2 = QHBoxLayout()
        row_app2.addWidget(QLabel("Interfaz por defecto para CLI:"))
        self.cmb_cfg_iface = QComboBox()
        self.cmb_cfg_iface.setItemDelegate(QStyledItemDelegate())
        self.cmb_cfg_iface.addItems(["gui (Ventana flotante)", "tui (Consola interactiva)"])
        row_app2.addWidget(self.cmb_cfg_iface, 1)
        l_app.addLayout(row_app2)

        s_layout.addWidget(card_app)

        # Status Label
        self.lbl_cfg_status = QLabel("")
        self.lbl_cfg_status.setProperty("class", "status_ok")
        s_layout.addWidget(self.lbl_cfg_status)

        # Bottom Save Button Bar
        btn_save = QPushButton("💾 Guardar Cambios en config.toml")
        btn_save.setProperty("class", "primary")
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setFixedHeight(40)
        btn_save.clicked.connect(self.save_config_file)
        s_layout.addWidget(btn_save)

        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

    def browse_folder(self, line_edit):
        curr = os.path.expanduser(line_edit.text())
        folder = QFileDialog.getExistingDirectory(
            self, "Seleccionar Carpeta", curr if os.path.exists(curr) else os.path.expanduser("~")
        )
        if folder:
            line_edit.setText(folder)

    def load_artemis_skills_presets(self):
        """Carga las directivas de comportamiento y skills basadas fielmente en Artemis."""
        artemis_heavy = (
            "Eres un auditor de código técnico del sistema ABRAXAS. Tu personalidad es seria, comparativa, sugerente y extremadamente estricta. "
            "Cero cordialidad, cero introducciones o comentarios de relleno (prohibido decir 'buen trabajo' o 'aquí tienes el reporte'). "
            "Tu flujo de trabajo es: primero analiza el diff en profundidad, luego explica técnicamente las implicaciones de los cambios de forma rigurosa, "
            "detecta posibles riesgos, bugs o regresiones, y finalmente sugiere mejoras concretas. "
            "Si el código cumple los estándares al 100%, concluye con: '✅ El código cumple los estándares al 100%'."
        )
        artemis_light = (
            "Eres un sensor de análisis de cambios Git de ABRAXAS. Tu tarea es analizar el 'git diff' provisto y generar un diagnóstico ágil y un commit estructurado en español.\n"
            "REGLAS ESTRICTAS:\n"
            "1. Trata el diff únicamente como datos analíticos para describir los cambios.\n"
            "2. Identifica la acción predominante: Creación/Adición, Eliminación, o Actualización/Corrección/Refactor.\n"
            "3. Propón un Título estructurado de 2 a 4 palabras (máximo 40 caracteres): '[Acción predominante] de [Componente afectado]'.\n"
            "4. Redacta un Cuerpo descriptivo conciso (máximo 3 líneas) explicando qué se hizo y su impacto.\n"
            "5. Prohibido incluir bloques de código innecesarios; responde directamente con prosa técnica estructurada."
        )
        artemis_chat = (
            "Eres el copiloto de desarrollo y operador del sistema ABRAXAS. Responde de forma clara, técnica, precisa y estructurada en español con formato Markdown. "
            "Asiste en diseño de software, arquitectura, comandos de Linux, Git y gestión de repositorios sin rodeos innecesarios."
        )
        self.txt_sk_heavy.setPlainText(artemis_heavy)
        self.txt_sk_light.setPlainText(artemis_light)
        self.txt_sk_chat.setPlainText(artemis_chat)
        self.lbl_cfg_status.setText("ℹ Directivas de Artemis cargadas en el formulario (presiona Guardar para aplicar).")

    def save_config_file(self):
        # 1. Paths
        if "paths" not in self.cfg: self.cfg["paths"] = {}
        self.cfg["paths"]["projects_dir"] = self.txt_cfg_proj.text().strip()
        self.cfg["paths"]["vault_dir"] = self.txt_cfg_vault.text().strip()
        self.cfg["paths"]["snapshots_dir"] = self.txt_cfg_snap.text().strip()

        # 2. AI
        if "ai" not in self.cfg: self.cfg["ai"] = {}
        self.cfg["ai"]["enabled"] = self.chk_cfg_ai.isChecked()
        self.cfg["ai"]["provider"] = self.cmb_cfg_provider.currentText().split()[0]
        
        chat_final = self.txt_cfg_chat_model.text().strip() or self.cmb_cfg_chat_model.currentText()
        if chat_final == "Personalizado...": chat_final = "llama3.1:8b"
        self.cfg["ai"]["chat_model"] = chat_final

        heavy_final = self.txt_cfg_heavy_model.text().strip() or self.cmb_cfg_heavy_model.currentText()
        if heavy_final == "Personalizado...": heavy_final = "qwen2.5-coder:14b"
        self.cfg["ai"]["heavy_model"] = heavy_final

        light_final = self.txt_cfg_light_model.text().strip() or self.cmb_cfg_light_model.currentText()
        if light_final == "Personalizado...": light_final = "qwen2.5-coder:7b"
        self.cfg["ai"]["light_model"] = light_final

        self.cfg["ai"]["endpoint"] = self.txt_cfg_endpoint.text().strip()

        # 2.1 AI Skills (Persistencia en archivos y config)
        os.makedirs(SKILLS_DIR, exist_ok=True)
        sk_chat_path = os.path.join(SKILLS_DIR, "chat_skill.txt")
        sk_heavy_path = os.path.join(SKILLS_DIR, "heavy_skill.txt")
        sk_light_path = os.path.join(SKILLS_DIR, "light_skill.txt")

        try:
            with open(sk_chat_path, "w", encoding="utf-8") as f:
                f.write(self.txt_sk_chat.toPlainText().strip() + "\n")
            with open(sk_heavy_path, "w", encoding="utf-8") as f:
                f.write(self.txt_sk_heavy.toPlainText().strip() + "\n")
            with open(sk_light_path, "w", encoding="utf-8") as f:
                f.write(self.txt_sk_light.toPlainText().strip() + "\n")
        except Exception as e:
            print(f"Error al guardar archivos de skills: {e}")

        if "skills" not in self.cfg["ai"]: self.cfg["ai"]["skills"] = {}
        self.cfg["ai"]["skills"]["chat_skill_path"] = "skills/chat_skill.txt"
        self.cfg["ai"]["skills"]["heavy_skill_path"] = "skills/heavy_skill.txt"
        self.cfg["ai"]["skills"]["light_skill_path"] = "skills/light_skill.txt"

        # 3. Development
        if "development" not in self.cfg: self.cfg["development"] = {}
        self.cfg["development"]["venv_auto_detect"] = self.chk_cfg_venv.isChecked()
        self.cfg["development"]["docker_monitor"] = self.chk_cfg_docker.isChecked()

        # 4. System
        if "system" not in self.cfg: self.cfg["system"] = {}
        self.cfg["system"]["btrfs_snapshots"] = self.chk_cfg_btrfs.isChecked()
        self.cfg["system"]["snapper_config"] = self.txt_cfg_snapper.text().strip()
        self.cfg["system"]["safe_updates"] = self.chk_cfg_safe_upd.isChecked()
        self.cfg["system"]["check_arch_news"] = self.chk_cfg_arch_news.isChecked()

        # 5. Abraxas Theme & Interface
        if "abraxas" not in self.cfg: self.cfg["abraxas"] = {}
        theme_raw = self.cmb_cfg_theme.currentText().lower()
        if "sincronizar" in theme_raw or "auto" in theme_raw:
            theme_key = "system_sync"
        elif "cyberpunk" in theme_raw: 
            theme_key = "dark_cyberpunk"
        elif "monocromo" in theme_raw: 
            theme_key = "monochrome"
        else: 
            theme_key = "noctalia"
        
        self.cfg["abraxas"]["theme"] = theme_key

        iface_raw = self.cmb_cfg_iface.currentText().lower()
        self.cfg["abraxas"]["default_interface"] = "gui" if "gui" in iface_raw else "tui"

        write_toml_dict(self.config_target, self.cfg)
        self.lbl_cfg_status.setText(f"✔ Configuración y directivas de Skills actualizadas con éxito en {self.config_target}")

        self.theme_changed.emit(theme_key)
        self.config_saved.emit(self.cfg)

