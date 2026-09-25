#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS | NEOS - CONFIGURATION VIEW (config.toml CRUD)
# =====================================================================

import os
import json
import urllib.request
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QLineEdit, QFileDialog, 
    QCheckBox, QFrame, QScrollArea,
    QComboBox, QStyledItemDelegate, QTextEdit, QDoubleSpinBox
)
from PySide6.QtCore import Qt, Signal

from abraxas.core.setup import write_toml_dict, read_toml_dict, detect_git_identity, sync_global_gitconfig
from abraxas.core.ai import get_model_skill, SKILLS_DIR

class ConfigView(QWidget):
    """Vista de administración y edición activa de config.toml en NEOS."""
    
    theme_changed = Signal(str)
    config_saved = Signal(dict)

    def __init__(self, config_target, parent=None):
        super().__init__(parent)
        self.config_target = config_target
        self.cfg = read_toml_dict(self.config_target)

        self.init_ui()

    def _fetch_local_ollama_models(self):
        """Consulta modelos locales disponibles en el servidor Ollama."""
        try:
            req = urllib.request.Request("http://localhost:11434/api/tags")
            with urllib.request.urlopen(req, timeout=1.2) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                return [m.get('name') for m in data.get('models', []) if m.get('name')]
        except Exception:
            return []

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
        self.txt_cfg_proj = QLineEdit(self.cfg.get("paths", {}).get("projects_dir", ""))
        self.txt_cfg_proj.setPlaceholderText("ej. /home/usuario/Development")
        btn_proj = QPushButton("Examinar")
        btn_proj.setProperty("class", "browse")
        btn_proj.clicked.connect(lambda: self.browse_folder(self.txt_cfg_proj))
        r_proj.addWidget(self.txt_cfg_proj)
        r_proj.addWidget(btn_proj)
        l_paths.addLayout(r_proj)

        # Vault Dir
        l_paths.addWidget(QLabel("Bóveda de notas / Obsidian:"))
        r_vault = QHBoxLayout()
        self.txt_cfg_vault = QLineEdit(self.cfg.get("paths", {}).get("vault_dir", ""))
        self.txt_cfg_vault.setPlaceholderText("ej. /home/usuario/Vault/01_Obsidian")
        btn_vault = QPushButton("Examinar")
        btn_vault.setProperty("class", "browse")
        btn_vault.clicked.connect(lambda: self.browse_folder(self.txt_cfg_vault))
        r_vault.addWidget(self.txt_cfg_vault)
        r_vault.addWidget(btn_vault)
        l_paths.addLayout(r_vault)

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

        self.chk_cfg_ai = QCheckBox("Habilitar Asistencia con IA Local en ABRAXAS")
        self.chk_cfg_ai.setChecked(self.cfg.get("ai", {}).get("enabled", False))
        l_ai.addWidget(self.chk_cfg_ai)

        row_ai1 = QHBoxLayout()
        row_ai1.addWidget(QLabel("Proveedor / Motor:"))
        self.cmb_cfg_provider = QComboBox()
        self.cmb_cfg_provider.setItemDelegate(QStyledItemDelegate())
        self.cmb_cfg_provider.addItems(["ollama", "openai-compatible"])
        row_ai1.addWidget(self.cmb_cfg_provider, 1)
        l_ai.addLayout(row_ai1)

        # Detectar modelos de Ollama
        detected_models = self._fetch_local_ollama_models()

        # 1. Conversational Model
        l_ai.addWidget(QLabel("Modelo Conversacional (Chatbox & Obsidian):"))
        row_ai_chat = QHBoxLayout()
        row_ai_chat.setSpacing(10)
        self.cmb_cfg_chat_model = QComboBox()
        self.cmb_cfg_chat_model.setItemDelegate(QStyledItemDelegate())
        chat_default = self.cfg.get("ai", {}).get("chat_model", "")
        presets_chat = list(detected_models) if detected_models else ["deepseek-r1:8b", "qwen2.5:7b", "llama3.1:8b"]
        if chat_default and chat_default not in presets_chat:
            presets_chat.insert(0, chat_default)
        if "Personalizado..." not in presets_chat:
            presets_chat.append("Personalizado...")
        self.cmb_cfg_chat_model.addItems(presets_chat)
        if chat_default and chat_default in presets_chat:
            self.cmb_cfg_chat_model.setCurrentText(chat_default)

        self.txt_cfg_chat_model = QLineEdit(chat_default)
        self.txt_cfg_chat_model.setPlaceholderText("Nombre del modelo...")
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
        heavy_default = self.cfg.get("ai", {}).get("heavy_model", "")
        presets_heavy = list(detected_models) if detected_models else ["deepseek-r1:8b", "qwen2.5-coder:14b"]
        if heavy_default and heavy_default not in presets_heavy:
            presets_heavy.insert(0, heavy_default)
        if "Personalizado..." not in presets_heavy:
            presets_heavy.append("Personalizado...")
        self.cmb_cfg_heavy_model.addItems(presets_heavy)
        if heavy_default and heavy_default in presets_heavy:
            self.cmb_cfg_heavy_model.setCurrentText(heavy_default)

        self.txt_cfg_heavy_model = QLineEdit(heavy_default)
        self.txt_cfg_heavy_model.setPlaceholderText("Nombre del modelo pesado...")
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
        light_default = self.cfg.get("ai", {}).get("light_model", "")
        presets_light = list(detected_models) if detected_models else ["qwen2.5-coder:7b", "llama3.2:3b"]
        if light_default and light_default not in presets_light:
            presets_light.insert(0, light_default)
        if "Personalizado..." not in presets_light:
            presets_light.append("Personalizado...")
        self.cmb_cfg_light_model.addItems(presets_light)
        if light_default and light_default in presets_light:
            self.cmb_cfg_light_model.setCurrentText(light_default)

        self.txt_cfg_light_model = QLineEdit(light_default)
        self.txt_cfg_light_model.setPlaceholderText("Nombre del modelo ligero...")
        self.cmb_cfg_light_model.currentTextChanged.connect(
            lambda t: self.txt_cfg_light_model.setText(t) if t != "Personalizado..." else None
        )
        row_ai_light.addWidget(self.cmb_cfg_light_model, 1)
        row_ai_light.addWidget(self.txt_cfg_light_model, 1)
        l_ai.addLayout(row_ai_light)

        # Endpoint
        row_ai3 = QHBoxLayout()
        row_ai3.addWidget(QLabel("Endpoint Servidor:"))
        self.txt_cfg_endpoint = QLineEdit(self.cfg.get("ai", {}).get("endpoint", "http://localhost:11434"))
        row_ai3.addWidget(self.txt_cfg_endpoint, 1)
        l_ai.addLayout(row_ai3)

        # Temperature
        row_temp = QHBoxLayout()
        row_temp.addWidget(QLabel("Temperatura (Creatividad / Precisión):"))
        self.spn_cfg_temp = QDoubleSpinBox()
        self.spn_cfg_temp.setRange(0.0, 1.0)
        self.spn_cfg_temp.setSingleStep(0.05)
        self.spn_cfg_temp.setDecimals(2)
        try:
            curr_temp = float(self.cfg.get("ai", {}).get("temperature", 0.2))
        except (ValueError, TypeError):
            curr_temp = 0.2
        self.spn_cfg_temp.setValue(curr_temp)
        row_temp.addWidget(self.spn_cfg_temp, 1)
        l_ai.addLayout(row_temp)

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

        btn_clear_skills = QPushButton("🧹 Limpiar Skills")
        btn_clear_skills.setCursor(Qt.PointingHandCursor)
        btn_clear_skills.setStyleSheet("""
            QPushButton {
                background-color: rgba(239, 68, 68, 0.15);
                color: #fca5a5;
                border: 1px solid rgba(239, 68, 68, 0.35);
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.30);
                border-color: #f87171;
                color: #ffffff;
            }
        """)
        btn_clear_skills.clicked.connect(self.clear_skills)
        h_sk_title.addWidget(btn_clear_skills)
        l_sk.addLayout(h_sk_title)

        lbl_sk_sub = QLabel(
            "Define el prompt de comportamiento del sistema para cada modelo. Puedes dejarlos vacíos para usar el comportamiento base del modelo."
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
        self.txt_sk_chat.setPlaceholderText("Instrucciones personalizadas del sistema (opcional)...")
        self.txt_sk_chat.setPlainText(get_model_skill("chat", self.config_target))
        l_sk.addWidget(self.txt_sk_chat)

        # 2. Skill Modelo Pesado
        lbl_sk_heavy = QLabel("🧠 Skill: Modelo Pesado Dev (Auditoría Profunda & Refactor):")
        lbl_sk_heavy.setStyleSheet("font-weight: 700; color: #c084fc; font-size: 12px;")
        l_sk.addWidget(lbl_sk_heavy)

        self.txt_sk_heavy = QTextEdit()
        self.txt_sk_heavy.setMinimumHeight(80)
        self.txt_sk_heavy.setMaximumHeight(115)
        self.txt_sk_heavy.setPlaceholderText("Protocolo estricto de auditoría (opcional)...")
        self.txt_sk_heavy.setPlainText(get_model_skill("heavy", self.config_target))
        l_sk.addWidget(self.txt_sk_heavy)

        # 3. Skill Modelo Ligero
        lbl_sk_light = QLabel("⚡ Skill: Modelo Ligero Dev (Git Rápido & Mensajes de Commit):")
        lbl_sk_light.setStyleSheet("font-weight: 700; color: #38bdf8; font-size: 12px;")
        l_sk.addWidget(lbl_sk_light)

        self.txt_sk_light = QTextEdit()
        self.txt_sk_light.setMinimumHeight(80)
        self.txt_sk_light.setMaximumHeight(115)
        self.txt_sk_light.setPlaceholderText("Formato conciso para análisis y commits (opcional)...")
        self.txt_sk_light.setPlainText(get_model_skill("light", self.config_target))
        l_sk.addWidget(self.txt_sk_light)

        s_layout.addWidget(card_skills)

        # -------------------------------------------------------------
        # Section 3: Identidad Git & GitHub ([git])
        # -------------------------------------------------------------
        card_git = QFrame()
        card_git.setProperty("class", "surface")
        l_git = QVBoxLayout(card_git)
        l_git.setSpacing(10)

        lbl_sec_git = QLabel("🐙 Identidad Git & GitHub ([git])")
        lbl_sec_git.setProperty("class", "section_title")
        l_git.addWidget(lbl_sec_git)

        lbl_git_sub = QLabel(
            "Configura la identidad de autoría para los commits automáticos generados en LUMEN."
        )
        lbl_git_sub.setProperty("class", "card_desc")
        lbl_git_sub.setWordWrap(True)
        l_git.addWidget(lbl_git_sub)

        l_git.addWidget(QLabel("Nombre de usuario Git (user.name):"))
        self.txt_cfg_git_user = QLineEdit(self.cfg.get("git", {}).get("user_name", ""))
        self.txt_cfg_git_user.setPlaceholderText("ej. Tu Nombre o Usuario")
        l_git.addWidget(self.txt_cfg_git_user)

        l_git.addWidget(QLabel("Correo electrónico Git (user.email):"))
        self.txt_cfg_git_email = QLineEdit(self.cfg.get("git", {}).get("user_email", ""))
        self.txt_cfg_git_email.setPlaceholderText("ej. correo@ejemplo.com")
        l_git.addWidget(self.txt_cfg_git_email)

        row_git_act = QHBoxLayout()
        btn_detect_git = QPushButton("📥 Detectar desde GitHub / gitconfig")
        btn_detect_git.setProperty("class", "browse")
        btn_detect_git.setCursor(Qt.PointingHandCursor)
        btn_detect_git.clicked.connect(self.auto_detect_git_identity)
        row_git_act.addWidget(btn_detect_git)

        self.lbl_git_status = QLabel("")
        row_git_act.addWidget(self.lbl_git_status, 1)
        l_git.addLayout(row_git_act)

        self.chk_cfg_git_sync = QCheckBox("Sincronizar automáticamente con ~/.gitconfig global al guardar")
        self.chk_cfg_git_sync.setChecked(self.cfg.get("git", {}).get("auto_sync_global", True))
        l_git.addWidget(self.chk_cfg_git_sync)

        s_layout.addWidget(card_git)

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
        self.chk_cfg_btrfs.setChecked(self.cfg.get("system", {}).get("btrfs_snapshots", False))
        l_sys.addWidget(self.chk_cfg_btrfs)

        row_snapper = QHBoxLayout()
        row_snapper.addWidget(QLabel("Configuración / Perfil de Snapper:"))
        self.txt_cfg_snapper = QLineEdit(self.cfg.get("system", {}).get("snapper_config", "root"))
        row_snapper.addWidget(self.txt_cfg_snapper, 1)
        l_sys.addLayout(row_snapper)

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
        curr_th = self.cfg.get("abraxas", {}).get("theme", "dark_cyberpunk")
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

    def clear_skills(self):
        """Limpia el contenido de los campos de texto de skills."""
        self.txt_sk_heavy.clear()
        self.txt_sk_light.clear()
        self.txt_sk_chat.clear()
        self.lbl_cfg_status.setText("ℹ Directivas de skills vaciadas (presiona Guardar para aplicar).")

    def save_config_file(self):
        # 1. Paths
        if "paths" not in self.cfg: self.cfg["paths"] = {}
        self.cfg["paths"]["projects_dir"] = self.txt_cfg_proj.text().strip()
        self.cfg["paths"]["vault_dir"] = self.txt_cfg_vault.text().strip()

        # 2. AI
        if "ai" not in self.cfg: self.cfg["ai"] = {}
        self.cfg["ai"]["enabled"] = self.chk_cfg_ai.isChecked()
        self.cfg["ai"]["provider"] = self.cmb_cfg_provider.currentText().split()[0]
        
        chat_final = self.txt_cfg_chat_model.text().strip() or self.cmb_cfg_chat_model.currentText()
        if chat_final == "Personalizado...": chat_final = ""
        self.cfg["ai"]["chat_model"] = chat_final

        heavy_final = self.txt_cfg_heavy_model.text().strip() or self.cmb_cfg_heavy_model.currentText()
        if heavy_final == "Personalizado...": heavy_final = ""
        self.cfg["ai"]["heavy_model"] = heavy_final

        light_final = self.txt_cfg_light_model.text().strip() or self.cmb_cfg_light_model.currentText()
        if light_final == "Personalizado...": light_final = ""
        self.cfg["ai"]["light_model"] = light_final

        self.cfg["ai"]["endpoint"] = self.txt_cfg_endpoint.text().strip()
        self.cfg["ai"]["temperature"] = round(self.spn_cfg_temp.value(), 2)

        # 2.1 AI Skills (Persistencia en archivos y config)
        os.makedirs(SKILLS_DIR, exist_ok=True)
        sk_chat_path = os.path.join(SKILLS_DIR, "chat_skill.txt")
        sk_heavy_path = os.path.join(SKILLS_DIR, "heavy_skill.txt")
        sk_light_path = os.path.join(SKILLS_DIR, "light_skill.txt")

        try:
            with open(sk_chat_path, "w", encoding="utf-8") as f:
                f.write(self.txt_sk_chat.toPlainText().strip())
            with open(sk_heavy_path, "w", encoding="utf-8") as f:
                f.write(self.txt_sk_heavy.toPlainText().strip())
            with open(sk_light_path, "w", encoding="utf-8") as f:
                f.write(self.txt_sk_light.toPlainText().strip())
        except Exception as e:
            print(f"Error al guardar archivos de skills: {e}")

        if "skills" not in self.cfg["ai"]: self.cfg["ai"]["skills"] = {}
        self.cfg["ai"]["skills"]["chat_skill_path"] = "skills/chat_skill.txt"
        self.cfg["ai"]["skills"]["heavy_skill_path"] = "skills/heavy_skill.txt"
        self.cfg["ai"]["skills"]["light_skill_path"] = "skills/light_skill.txt"

        # 3. Git Identity
        if "git" not in self.cfg: self.cfg["git"] = {}
        git_u = self.txt_cfg_git_user.text().strip()
        git_e = self.txt_cfg_git_email.text().strip()
        git_sync = self.chk_cfg_git_sync.isChecked()
        self.cfg["git"]["user_name"] = git_u
        self.cfg["git"]["user_email"] = git_e
        self.cfg["git"]["auto_sync_global"] = git_sync

        if git_sync and (git_u or git_e):
            sync_global_gitconfig(git_u, git_e)

        # 4. System
        if "system" not in self.cfg: self.cfg["system"] = {}
        self.cfg["system"]["btrfs_snapshots"] = self.chk_cfg_btrfs.isChecked()
        self.cfg["system"]["snapper_config"] = self.txt_cfg_snapper.text().strip()

        # 5. Abraxas Theme
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

        write_toml_dict(self.config_target, self.cfg)
        self.lbl_cfg_status.setText(f"✔ Configuración actualizada con éxito en {self.config_target}")

        self.theme_changed.emit(theme_key)
        self.config_saved.emit(self.cfg)

    def auto_detect_git_identity(self):
        name, email = detect_git_identity()
        if name:
            self.txt_cfg_git_user.setText(name)
        if email:
            self.txt_cfg_git_email.setText(email)
        if name or email:
            self.lbl_git_status.setText(f"✔ Detectado: {name} <{email}>")
            self.lbl_git_status.setStyleSheet("color: #10b981; font-size: 11px;")
        else:
            self.lbl_git_status.setText("ℹ No se encontró identidad en Git ni gh CLI.")
            self.lbl_git_status.setStyleSheet("color: #f59e0b; font-size: 11px;")
