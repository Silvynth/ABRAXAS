"""
❖ ABRAXAS 2.0 | Lumen UI: Sector 01 - Protocolo GitOps & Ciclos de Versión
Estructura modular en 3 Nodos Maestros (Sub-sectores):
- Sub-sector 1.1: Ciclo de trabajo (Columna 1: git add, workspace files, git push | Columna 2: IA commit)
- Sub-sector 1.2: Gestor de ramas (visibilidad, creación, eliminación, fusión)
- Sub-sector 1.3: Estado y sincronización (status, fetch, pull, visibilidad)

Gobierno 100% por clases desde abraxas.core.theme (Cero CSS inline redundante).
Redactor asistido conectado a IA local (Ollama) con skills calibradas según impacto SemVer
(Parche = ultra rápido, Minor = medio, Major = profundo), sin testamentos y con bloqueo reactivo.
"""

from pathlib import Path
from typing import Optional
import json
import re
import urllib.request
import urllib.error

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QLineEdit, QTextEdit, QScrollArea,
    QSplitter, QButtonGroup, QCheckBox, QStackedWidget, QSizePolicy, QDialog,
    QTabWidget, QRadioButton
)
from PySide6.QtCore import Qt, Signal, QTimer, QThread
from PySide6.QtGui import QCursor
import datetime

from abraxas.core.process import run_command
from abraxas.core.semver import bump_semver
from abraxas.lumen.models.project import Project
from abraxas.ui.controls.switcher_pill import SectorSwitcherPill
from gui.views.lumen.git_graph_canvas import LumenHorizontalGitGraphView
from core.github import get_repo_visibility, change_repo_visibility, publish_repo_to_github


# =====================================================================
# HILO DE INFERENCIA DE IA PARA COMMITS (OLLAMA + SKILLS CONCISAS)
# =====================================================================

class AICommitWorkerThread(QThread):
    """
    Hilo de ejecución asíncrono para generar propuestas de commit con Ollama
    utilizando las directivas de concisión de las skills (light_skill.txt / heavy_skill.txt).
    Previene bloqueos de la interfaz y regula la longitud según el impacto SemVer:
    - Patch: Muy rápido y puntual (máx 2 viñetas breves).
    - Minor: Medio rápido (máx 3-4 viñetas).
    - Major: Profundo / Arquitectura (máx 4-5 viñetas estructuradas).
    """
    finished_generation = Signal(bool, str, str, str)  # ok, title, body, info

    def __init__(self, project_path: Path, model_type: str, impact_type: str, target_ver: str, parent=None):
        super().__init__(parent)
        self.project_path = project_path
        self.model_type = model_type  # "light" | "heavy"
        self.impact_type = impact_type  # "PATCH" | "MINOR" | "MAJOR" | "NONE"
        self.target_ver = target_ver

    def run(self):
        # 1. Extraer diff (staged primero, luego working tree)
        res_cached = run_command(["git", "diff", "--cached"], cwd=self.project_path)
        diff = res_cached.stdout.strip()
        if not diff:
            res_head = run_command(["git", "diff", "HEAD"], cwd=self.project_path)
            diff = res_head.stdout.strip()
        if not diff:
            res_stat = run_command(["git", "status", "--porcelain"], cwd=self.project_path)
            diff = res_stat.stdout.strip()

        if not diff:
            self.finished_generation.emit(False, "", "", "No hay cambios staged ni pendientes para analizar.")
            return

        # 2. Cargar skill calibrada (prioridad: skill privada del usuario -> plantilla example)
        skill_base = "light_skill" if self.model_type == "light" else "heavy_skill"
        skills_dir = Path("/home/silvynth/Development/Abraxas/skills")
        private_path = skills_dir / f"{skill_base}.txt"
        example_path = skills_dir / f"{skill_base}.example.txt"

        system_skill = ""
        for path in (private_path, example_path):
            if path.exists():
                try:
                    content = path.read_text(encoding="utf-8").strip()
                    if content:
                        system_skill = content
                        break
                except Exception:
                    pass

        # 3. Determinar prefijo, número correlativo y calibrar tokens
        prefix = "HEX" if self.model_type == "light" else "HEN"
        next_num_str = self._detect_next_commit_number()
        # En 'Sin salto' no se agrega versión entre corchetes al título
        target_ver_str = f" [{self.target_ver}]" if self.target_ver and self.impact_type != "NONE" else ""
        expected_header = f"{prefix}:{next_num_str}{target_ver_str}"

        # Si el usuario eligió 'Sin salto' (NONE), la redacción y tokens se calibran como MINOR
        effective_impact = "MINOR" if self.impact_type == "NONE" else self.impact_type

        if self.model_type == "light":
            model_name = "qwen2.5-coder:7b"
            if effective_impact == "PATCH":
                max_tokens = 220
                temp = 0.20
            elif effective_impact == "MINOR":
                max_tokens = 340
                temp = 0.25
            else:
                max_tokens = 480
                temp = 0.30
        else:
            model_name = "deepseek-r1:8b"
            if effective_impact == "PATCH":
                max_tokens = 380
                temp = 0.25
            elif effective_impact == "MINOR":
                max_tokens = 550
                temp = 0.30
            else:
                max_tokens = 750
                temp = 0.35

        semver_info_str = f"{self.impact_type} ({self.target_ver})" if self.impact_type != "NONE" else f"Sin salto (calibrar como MINOR con tag actual {self.target_ver})"

        user_prompt = f"""Analiza este git diff y genera la propuesta conforme a tu skill calibrada.
INSTRUCCIÓN ESTRICTA DE TÍTULO:
El título DEBE comenzar obligatoriamente con el identificador correlativo exacto: '{expected_header} | ' seguido del resumen.
Ejemplo:
TITULO: {expected_header} | <resumen del cambio>
CUERPO:
<viñetas explicativas>

Impacto SemVer: {semver_info_str}

--- INICIO DIFF ---
{diff[:8000]}
--- FIN DIFF ---
"""

        payload = {
            "model": model_name,
            "prompt": user_prompt,
            "system": system_skill,
            "stream": False,
            "options": {
                "temperature": temp,
                "num_predict": max_tokens
            }
        }

        # 4. Inferencia con Ollama
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:11434/api/generate",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=35) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                raw_response = resp_data.get("response", "").strip()

            title, body = self._parse_ai_response(raw_response)
            if title:
                # Asegurar prefijo correlativo si el LLM lo omitió
                if not re.match(r"^[A-Z]{3}:\d{4}", title):
                    title = f"{expected_header} | {title.lstrip('|').strip()}"
                self.finished_generation.emit(True, title, body, f"Motor {model_name} [{self.impact_type}]")
                return
        except Exception:
            pass  # Fallback a síntesis estructurada local si Ollama no responde

        # 5. Fallback heurístico conciso (anti-bloqueo)
        fallback_title, fallback_body = self._heuristic_fallback(diff, expected_header)
        self.finished_generation.emit(True, fallback_title, fallback_body, "Síntesis estructurada local (Ollama offline)")

    def _parse_ai_response(self, text: str) -> tuple[str, str]:
        """Extrae de forma limpia el Título y el Cuerpo eliminando etiquetas de pensamiento."""
        clean = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
        lines = [l.strip() for l in clean.splitlines() if l.strip()]
        title = ""
        body_lines = []
        is_body = False

        for line in lines:
            if line.upper().startswith("TITULO:") or line.upper().startswith("TÍTULO:"):
                title = line.split(":", 1)[1].strip()
            elif line.upper().startswith("CUERPO:"):
                is_body = True
                content = line.split(":", 1)[1].strip()
                if content:
                    body_lines.append(content)
            elif is_body:
                body_lines.append(line)
            elif not title and not line.startswith("-") and not line.startswith("*"):
                title = line

        if not title and lines:
            title = lines[0].lstrip("#*- ").strip()
            body_lines = lines[1:]

        return title, "\n".join(body_lines)

    def _detect_next_commit_number(self) -> str:
        """Escanea el historial de Git para obtener el último correlativo numérico y calcular el siguiente."""
        res = run_command(["git", "log", "--format=%s"], cwd=self.project_path)
        nums = []
        if res.success and res.stdout.strip():
            for line in res.stdout.splitlines():
                m = re.match(r"^[A-Z]{3}:(\d{4})", line.strip())
                if m:
                    nums.append(int(m.group(1)))
        next_num = (max(nums) + 1) if nums else 1
        return f"{next_num:04d}"

    def _heuristic_fallback(self, diff: str, expected_header: str) -> tuple[str, str]:
        """Síntesis de respaldo instantánea con formato oficial Abraxas."""
        files = re.findall(r"diff --git a/(.*?) b/", diff)
        if not files:
            files = [line.split()[-1] for line in diff.splitlines() if line.strip()]

        scope = "workspace"
        if any("lumen" in f for f in files):
            scope = "lumen"
        elif any("umbra" in f for f in files):
            scope = "umbra"
        elif any("core" in f for f in files):
            scope = "core"
        elif any("test" in f for f in files):
            scope = "tests"

        if self.impact_type == "PATCH":
            title = f"{expected_header} | Corrección puntual de estabilidad y ajustes en {scope}"
            body = f"- Corrección puntual en {len(files)} archivo(s) del módulo {scope}.\n- Ajuste técnico directo y validación de ejecución."
        elif self.impact_type == "MINOR":
            title = f"{expected_header} | Implementación de capacidades modulares en {scope}"
            body = f"- Implementación de nuevas capacidades operacionales en {len(files)} módulos.\n- Integración de interfaz y consistencia temática.\n- Validación en suite de pruebas."
        else:
            title = f"{expected_header} | Refactorización de arquitectura y sincronización reactiva"
            body = f"- Módulos clave: {', '.join(files[:4])}\n- Arquitectura: Aislamiento desacoplado de vistas y gobierno centralizado por clases.\n- Impacto: Cero interferencia de hilos y prevención de clipping tipográfico."

        return title, body


# =====================================================================
# FILA DE ARCHIVO DEL WORKSPACE (ESTILO SECTOR 0 GOBERNADO POR CLASES)
# =====================================================================

class WorkspaceFileRow(QFrame):
    """
    Fila para un archivo en el visor del workspace estilo Sector 0.
    Gobernado puramente por clases del sistema de temas:
    - workspace_file_row (contenedor)
    - badge_staged / badge_pending (estado)
    - file_path_label (tipografía)
    - cyber_btn_icon / cyber_btn_icon_active (acción)
    """
    toggle_stage_requested = Signal(str, bool)  # file_path, current_is_staged

    def __init__(self, file_path: str, is_staged: bool, status_tag: str = "M", parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.is_staged = is_staged

        self.setProperty("class", "workspace_file_row")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(8)

        # Badge Staged / Pendiente
        lbl_status = QLabel("STAGED" if is_staged else "PENDIENTE")
        lbl_status.setProperty("class", "badge_staged" if is_staged else "badge_pending")
        layout.addWidget(lbl_status)

        # Ruta del archivo
        p = Path(file_path)
        lbl_name = QLabel(p.name)
        lbl_name.setToolTip(file_path)
        lbl_name.setProperty("class", "file_path_label")
        layout.addWidget(lbl_name, 1)

        # Botón interactivo de preparación/deshacer
        self.btn_toggle = QPushButton("↩" if is_staged else "＋")
        self.btn_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_toggle.setToolTip("Quitar de staging" if is_staged else "Añadir a staging (git add)")
        self.btn_toggle.setProperty("class", "cyber_btn_icon_active" if is_staged else "cyber_btn_icon")
        self.btn_toggle.clicked.connect(lambda: self.toggle_stage_requested.emit(self.file_path, self.is_staged))
        layout.addWidget(self.btn_toggle)

    def set_locked(self, locked: bool):
        self.btn_toggle.setEnabled(not locked)


# =====================================================================
# SUB-SECTOR 1.1: CICLO DE TRABAJO (COLUMNA 1: ADD + WORKSPACE + PUSH)
# =====================================================================

class Sector11WorkflowView(QWidget):
    """
    Sub-sector 1.1: Ciclo Operativo de Trabajo.
    - Columna 1 (Izquierda Vertical):
      1. Arriba: git add (Stage All, Unstage All, contadores).
      2. Centro: Estado del workspace del Sector 0 para visibilizar archivos.
      3. Abajo: git push (Push Directo y con Tags hacia upstream).
    - Columna 2 (Derecha):
      IA commit (Redactor asistido, botones SemVer, modos Ligero/Pesado y generación animada).
    """

    action_requested = Signal(str, dict)
    log_emitted = Signal(str)

    def __init__(self, project: Project = None, parent=None):
        super().__init__(parent)
        self.project = project
        self._file_rows: list[WorkspaceFileRow] = []
        self._commit_worker: Optional[AICommitWorkerThread] = None
        self.init_ui()

        if self.project:
            self.update_project(self.project)

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(8)

        # Splitter principal: Columna 1 (Izquierda) y Columna 2 (Derecha)
        self.main_splitter = QSplitter(Qt.Horizontal)

        # =============================================================
        # COLUMNA 1 (IZQUIERDA VERTICAL): ADD + WORKSPACE STATUS + PUSH
        # =============================================================
        left_column = QWidget()
        left_layout = QVBoxLayout(left_column)
        left_layout.setContentsMargins(0, 0, 4, 0)
        left_layout.setSpacing(8)

        # -------------------------------------------------------------
        # 1. ARRIBA: CONTROL DE GIT ADD
        # -------------------------------------------------------------
        card_add = QFrame()
        card_add.setProperty("class", "sector_card")
        add_layout = QHBoxLayout(card_add)
        add_layout.setContentsMargins(14, 10, 14, 10)
        add_layout.setSpacing(12)

        add_info = QVBoxLayout()
        add_info.setSpacing(2)
        tag_add = QLabel("CONTROL DE STAGING // GIT ADD")
        tag_add.setProperty("class", "sector_micro_tag")
        lbl_add_title = QLabel("📌 Área de Preparación de Cambios")
        lbl_add_title.setProperty("class", "sector_title")
        add_info.addWidget(tag_add)
        add_info.addWidget(lbl_add_title)
        add_layout.addLayout(add_info)

        # Conteo de archivos
        self.lbl_stage_counts = QLabel("Staged: 0 | Unstaged: 0")
        self.lbl_stage_counts.setProperty("class", "badge_telemetry")
        add_layout.addWidget(self.lbl_stage_counts)
        add_layout.addStretch()

        # Botones masivos compactos
        self.btn_stage_all = QPushButton("📌 Stage All")
        self.btn_stage_all.setProperty("class", "cyber_btn_compact")
        self.btn_stage_all.setCursor(Qt.PointingHandCursor)
        self.btn_stage_all.setToolTip("Añade todos los archivos al staging (git add -A)")
        self.btn_stage_all.clicked.connect(self._stage_all)
        add_layout.addWidget(self.btn_stage_all)

        self.btn_unstage_all = QPushButton("↩ Unstage All")
        self.btn_unstage_all.setProperty("class", "cyber_btn_compact")
        self.btn_unstage_all.setCursor(Qt.PointingHandCursor)
        self.btn_unstage_all.setToolTip("Retira todos los archivos de staging (git restore --staged .)")
        self.btn_unstage_all.clicked.connect(self._unstage_all)
        add_layout.addWidget(self.btn_unstage_all)

        left_layout.addWidget(card_add)

        # -------------------------------------------------------------
        # 2. CENTRO: ESTADO DEL WORKSPACE (ESTILO SECTOR 0)
        # -------------------------------------------------------------
        card_workspace = QFrame()
        card_workspace.setProperty("class", "sector_card")
        ws_layout = QVBoxLayout(card_workspace)
        ws_layout.setContentsMargins(14, 12, 14, 12)
        ws_layout.setSpacing(10)

        # Cabecera del visor de archivos
        ws_head = QHBoxLayout()
        ws_info = QVBoxLayout()
        ws_info.setSpacing(2)
        tag_ws = QLabel("ESTADO DEL WORKSPACE // ARQUITECTURA SECTOR 0")
        tag_ws.setProperty("class", "sector_micro_tag")
        lbl_ws_title = QLabel("📁 Archivos Modificados, Añadidos y Eliminados")
        lbl_ws_title.setProperty("class", "sector_title")
        ws_info.addWidget(tag_ws)
        ws_info.addWidget(lbl_ws_title)
        ws_head.addLayout(ws_info)
        ws_head.addStretch()

        self.lbl_files_summary = QLabel("0 cambios activos")
        self.lbl_files_summary.setProperty("class", "badge_telemetry")
        ws_head.addWidget(self.lbl_files_summary)
        ws_layout.addLayout(ws_head)

        # 3 Columnas estilo Sector 0
        files_cols_layout = QHBoxLayout()
        files_cols_layout.setSpacing(10)

        # Sub-columna 1: Modificados
        col_mod = QVBoxLayout()
        col_mod.setSpacing(4)
        lbl_col_m = QLabel("◆ Modificados")
        lbl_col_m.setProperty("class", "sector_desc")
        col_mod.addWidget(lbl_col_m)

        scroll_m = QScrollArea()
        scroll_m.setProperty("class", "clean_scroll")
        scroll_m.setWidgetResizable(True)
        self.mod_list_widget = QWidget()
        self.mod_list_layout = QVBoxLayout(self.mod_list_widget)
        self.mod_list_layout.setContentsMargins(0, 0, 2, 0)
        self.mod_list_layout.setSpacing(3)
        self.mod_list_layout.setAlignment(Qt.AlignTop)
        scroll_m.setWidget(self.mod_list_widget)
        col_mod.addWidget(scroll_m, 1)
        files_cols_layout.addLayout(col_mod, 1)

        # Sub-columna 2: Añadidos / Nuevos
        col_add = QVBoxLayout()
        col_add.setSpacing(4)
        lbl_col_a = QLabel("▲ Añadidos / Untracked")
        lbl_col_a.setProperty("class", "sector_desc")
        col_add.addWidget(lbl_col_a)

        scroll_add = QScrollArea()
        scroll_add.setProperty("class", "clean_scroll")
        scroll_add.setWidgetResizable(True)
        self.add_list_widget = QWidget()
        self.add_list_layout = QVBoxLayout(self.add_list_widget)
        self.add_list_layout.setContentsMargins(0, 0, 2, 0)
        self.add_list_layout.setSpacing(3)
        self.add_list_layout.setAlignment(Qt.AlignTop)
        scroll_add.setWidget(self.add_list_widget)
        col_add.addWidget(scroll_add, 1)
        files_cols_layout.addLayout(col_add, 1)

        # Sub-columna 3: Eliminados
        col_del = QVBoxLayout()
        col_del.setSpacing(4)
        lbl_col_d = QLabel("▼ Eliminados")
        lbl_col_d.setProperty("class", "sector_desc")
        col_del.addWidget(lbl_col_d)

        scroll_del = QScrollArea()
        scroll_del.setProperty("class", "clean_scroll")
        scroll_del.setWidgetResizable(True)
        self.del_list_widget = QWidget()
        self.del_list_layout = QVBoxLayout(self.del_list_widget)
        self.del_list_layout.setContentsMargins(0, 0, 2, 0)
        self.del_list_layout.setSpacing(3)
        self.del_list_layout.setAlignment(Qt.AlignTop)
        scroll_del.setWidget(self.del_list_widget)
        col_del.addWidget(scroll_del, 1)
        files_cols_layout.addLayout(col_del, 1)

        ws_layout.addLayout(files_cols_layout, 1)
        left_layout.addWidget(card_workspace, 1)

        # -------------------------------------------------------------
        # 3. ABAJO: CONTROL DE GIT PUSH
        # -------------------------------------------------------------
        card_push = QFrame()
        card_push.setProperty("class", "sector_card")
        push_layout = QHBoxLayout(card_push)
        push_layout.setContentsMargins(14, 10, 14, 10)
        push_layout.setSpacing(12)

        push_info = QVBoxLayout()
        push_info.setSpacing(2)
        tag_push = QLabel("PUBLICACIÓN REMOTA // GIT PUSH")
        tag_push.setProperty("class", "sector_micro_tag")
        lbl_push_title = QLabel("⬆ Enviar Commits al Repositorio Remoto")
        lbl_push_title.setProperty("class", "sector_title")
        push_info.addWidget(tag_push)
        push_info.addWidget(lbl_push_title)
        push_layout.addLayout(push_info)

        self.lbl_push_target = QLabel("Destino: origin")
        self.lbl_push_target.setProperty("class", "badge_telemetry")
        push_layout.addWidget(self.lbl_push_target)
        push_layout.addStretch()

        self.btn_push_direct = QPushButton("⬆ Push Directo")
        self.btn_push_direct.setProperty("class", "cyber_btn")
        self.btn_push_direct.setCursor(Qt.PointingHandCursor)
        self.btn_push_direct.setToolTip("Ejecuta git push sobre la rama activa")
        self.btn_push_direct.clicked.connect(lambda: self._execute_git_push(with_tags=False))
        push_layout.addWidget(self.btn_push_direct)

        self.btn_push_tags = QPushButton("🏷 Push con Tags")
        self.btn_push_tags.setProperty("class", "cyber_btn_primary")
        self.btn_push_tags.setCursor(Qt.PointingHandCursor)
        self.btn_push_tags.setToolTip("Ejecuta git push --follow-tags")
        self.btn_push_tags.clicked.connect(lambda: self._execute_git_push(with_tags=True))
        push_layout.addWidget(self.btn_push_tags)

        left_layout.addWidget(card_push)
        self.main_splitter.addWidget(left_column)

        # =============================================================
        # COLUMNA 2 (DERECHA): IA COMMIT
        # =============================================================
        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)
        right_layout.setContentsMargins(4, 0, 0, 0)
        right_layout.setSpacing(8)

        card_ia_commit = QFrame()
        card_ia_commit.setProperty("class", "sector_card")
        cm_layout = QVBoxLayout(card_ia_commit)
        cm_layout.setContentsMargins(14, 12, 14, 12)
        cm_layout.setSpacing(10)

        # Cabecera de IA Commit
        cm_head = QHBoxLayout()
        cm_info = QVBoxLayout()
        cm_info.setSpacing(2)
        tag_cm = QLabel("REDACTOR ASISTIDO // GIT COMMIT")
        tag_cm.setProperty("class", "sector_micro_tag")
        lbl_cm_title = QLabel("🤖 IA Commit & Ciclos de Versión")
        lbl_cm_title.setProperty("class", "sector_title")
        cm_info.addWidget(tag_cm)
        cm_info.addWidget(lbl_cm_title)
        cm_head.addLayout(cm_info)
        cm_head.addStretch()
        cm_layout.addLayout(cm_head)

        # Campo Asunto (Header)
        lbl_sub_hint = QLabel("Título o Asunto del Commit:")
        lbl_sub_hint.setProperty("class", "sector_desc")
        cm_layout.addWidget(lbl_sub_hint)

        self.txt_commit_subject = QLineEdit()
        self.txt_commit_subject.setPlaceholderText("ej. feat(lumen): integrar visor de archivos del sector 0 en ciclo de trabajo...")
        self.txt_commit_subject.setProperty("class", "cyber_input")
        cm_layout.addWidget(self.txt_commit_subject)

        # Campo Cuerpo (Body)
        lbl_body_hint = QLabel("Descripción Técnica y Notas Operativas:")
        lbl_body_hint.setProperty("class", "sector_desc")
        cm_layout.addWidget(lbl_body_hint)

        self.txt_commit_body = QTextEdit()
        self.txt_commit_body.setPlaceholderText("Detalles de implementación, módulos modificados, justificación técnica...")
        self.txt_commit_body.setProperty("class", "cyber_input")
        cm_layout.addWidget(self.txt_commit_body, 1)

        # Fila 1: Selector SemVer (Botones Píldora)
        semver_row = QHBoxLayout()
        semver_row.setSpacing(6)

        lbl_sem = QLabel("Impacto SemVer:")
        lbl_sem.setProperty("class", "sector_desc")
        semver_row.addWidget(lbl_sem)

        self.semver_btn_group = QButtonGroup(self)
        self.semver_btn_group.setExclusive(True)

        self.btn_sem_none = QPushButton("Sin salto")
        self.btn_sem_patch = QPushButton("Patch (+0.0.1)")
        self.btn_sem_minor = QPushButton("Minor (+0.1.0)")
        self.btn_sem_major = QPushButton("Major (+1.0.0)")

        for i, btn in enumerate([self.btn_sem_none, self.btn_sem_patch, self.btn_sem_minor, self.btn_sem_major]):
            btn.setCheckable(True)
            btn.setProperty("class", "cyber_btn_toggle")
            btn.setCursor(Qt.PointingHandCursor)
            self.semver_btn_group.addButton(btn, i)
            btn.clicked.connect(self._update_semver_preview)
            semver_row.addWidget(btn)

        self.btn_sem_none.setChecked(True)

        self.lbl_semver_preview = QLabel("v0.0.0")
        self.lbl_semver_preview.setProperty("class", "badge_telemetry")
        semver_row.addWidget(self.lbl_semver_preview)
        semver_row.addStretch()

        self.chk_create_tag = QCheckBox("Crear Tag Git")
        semver_row.addWidget(self.chk_create_tag)
        cm_layout.addLayout(semver_row)

        # Fila 2: Selector de Modo IA (Ligero vs Pesado)
        mode_row = QHBoxLayout()
        mode_row.setSpacing(6)

        lbl_mode = QLabel("Modo de Síntesis:")
        lbl_mode.setProperty("class", "sector_desc")
        mode_row.addWidget(lbl_mode)

        self.mode_btn_group = QButtonGroup(self)
        self.mode_btn_group.setExclusive(True)

        self.btn_mode_light = QPushButton("⚡ Ligero")
        self.btn_mode_light.setCheckable(True)
        self.btn_mode_light.setChecked(True)
        self.btn_mode_light.setProperty("class", "cyber_btn_toggle")
        self.btn_mode_light.setCursor(Qt.PointingHandCursor)
        self.btn_mode_light.setToolTip("Motor HEX: Síntesis ágil y concisa del diff (Parche rápido)")

        self.btn_mode_heavy = QPushButton("🧠 Pesado")
        self.btn_mode_heavy.setCheckable(True)
        self.btn_mode_heavy.setProperty("class", "cyber_btn_toggle")
        self.btn_mode_heavy.setCursor(Qt.PointingHandCursor)
        self.btn_mode_heavy.setToolTip("Motor HENDRIX: Análisis exhaustivo, estructurado y profundo")

        self.mode_btn_group.addButton(self.btn_mode_light, 0)
        self.mode_btn_group.addButton(self.btn_mode_heavy, 1)

        mode_row.addWidget(self.btn_mode_light)
        mode_row.addWidget(self.btn_mode_heavy)
        mode_row.addStretch()
        cm_layout.addLayout(mode_row)

        # Fila 3 (Inferior): Botón Generar a la izquierda + Botón Confirmar a la derecha
        cm_btn_row = QHBoxLayout()
        cm_btn_row.setSpacing(8)

        self.btn_ai_generate = QPushButton("✨ Generar con IA")
        self.btn_ai_generate.setProperty("class", "cyber_btn")
        self.btn_ai_generate.setCursor(Qt.PointingHandCursor)
        self.btn_ai_generate.setToolTip("Inicia la auditoría y síntesis inteligente del diff con la IA local")
        self.btn_ai_generate.clicked.connect(self._start_ai_generation)
        cm_btn_row.addWidget(self.btn_ai_generate)

        cm_btn_row.addStretch()

        self.btn_commit = QPushButton("🚀 Confirmar Commit & Grabar")
        self.btn_commit.setProperty("class", "cyber_btn_primary")
        self.btn_commit.setCursor(Qt.PointingHandCursor)
        self.btn_commit.clicked.connect(self._submit_commit)
        cm_btn_row.addWidget(self.btn_commit)
        cm_layout.addLayout(cm_btn_row)

        right_layout.addWidget(card_ia_commit)
        self.main_splitter.addWidget(right_column)

        # Proporción: 58% Columna Izquierda, 42% Columna Derecha
        self.main_splitter.setSizes([560, 440])
        root_layout.addWidget(self.main_splitter, 1)

    # =============================================================
    # LÓGICA DE CARGA Y ACTUALIZACIÓN
    # =============================================================
    def update_project(self, project: Project):
        """Recarga el estado de archivos del workspace y telemetría de push."""
        self.project = project
        if not project or not project.path or not Path(project.path).is_dir():
            return

        p_path = Path(project.path)
        is_git = (p_path / ".git").is_dir()
        if not is_git:
            self.lbl_files_summary.setText("No es repositorio Git")
            return

        # 1. Telemetría de Rama y Upstream para Git Push
        branch_name = project.current_branch or "HEAD"
        res_upstream = run_command(["git", "rev-parse", "--abbrev-ref", "@{u}"], cwd=p_path)
        if res_upstream.success and res_upstream.stdout.strip():
            upstream = res_upstream.stdout.strip()
            self.lbl_push_target.setText(f"Destino: {upstream}")
        else:
            self.lbl_push_target.setText(f"Destino: origin/{branch_name} (local)")

        # 2. Cargar Archivos del Workspace (Estilo Sector 0 con estado Staged)
        self._load_files_status(p_path)

        # 3. Actualizar Preview SemVer
        self._update_semver_preview()

    def _load_files_status(self, p_path: Path):
        """Carga y clasifica los archivos en Modificados, Añadidos y Eliminados."""
        self._file_rows.clear()
        for layout in (self.mod_list_layout, self.add_list_layout, self.del_list_layout):
            while layout.count() > 0:
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

        res = run_command(["git", "status", "--porcelain=v1"], cwd=p_path)
        if not res.success:
            return

        lines = [l for l in res.stdout.splitlines() if l.strip()]
        mod_files = []
        add_files = []
        del_files = []
        staged_count = 0
        unstaged_count = 0

        for line in lines:
            if len(line) < 3:
                continue
            index_code = line[0]
            work_code = line[1]
            filename = line[3:].strip()

            is_staged = index_code not in (" ", "?")
            if is_staged:
                staged_count += 1
            if work_code != " " or index_code == "?":
                unstaged_count += 1

            status_pair = line[:2]
            if "M" in status_pair:
                mod_files.append((filename, is_staged))
            elif "?" in status_pair or "A" in status_pair:
                add_files.append((filename, is_staged))
            elif "D" in status_pair:
                del_files.append((filename, is_staged))

        total_changes = len(mod_files) + len(add_files) + len(del_files)
        self.lbl_files_summary.setText(f"{total_changes} cambios activos")
        self.lbl_stage_counts.setText(f"Staged: {staged_count} | Unstaged: {unstaged_count}")

        def populate_col(files: list, target_layout: QVBoxLayout, empty_msg: str, tag: str):
            if not files:
                lbl_e = QLabel(empty_msg)
                lbl_e.setProperty("class", "sector_desc")
                target_layout.addWidget(lbl_e)
                return
            for fpath, staged in files:
                row = WorkspaceFileRow(fpath, staged, status_tag=tag)
                row.toggle_stage_requested.connect(self._toggle_file_stage)
                self._file_rows.append(row)
                target_layout.addWidget(row)

        populate_col(mod_files, self.mod_list_layout, "Ninguno modificado", "M")
        populate_col(add_files, self.add_list_layout, "Ninguno añadido", "A")
        populate_col(del_files, self.del_list_layout, "Ninguno eliminado", "D")

    def _toggle_file_stage(self, file_path: str, is_currently_staged: bool):
        """Alterna el estado de staging de un archivo individual."""
        if not self.project or not self.project.path:
            return

        if is_currently_staged:
            res = run_command(["git", "restore", "--staged", file_path], cwd=self.project.path)
            if res.success:
                self.log_emitted.emit(f"Archivo quitado de staging: <code>{file_path}</code>")
        else:
            res = run_command(["git", "add", file_path], cwd=self.project.path)
            if res.success:
                self.log_emitted.emit(f"Archivo añadido a staging: <code>{file_path}</code>")

        self.update_project(self.project)

    def _update_semver_preview(self):
        """Calcula la siguiente versión SemVer según el botón seleccionado."""
        base_ver = self.project.semver if self.project and self.project.semver else "0.1.0"
        btn_id = self.semver_btn_group.checkedId()

        if btn_id == 1:
            next_ver = bump_semver(base_ver, "patch")
        elif btn_id == 2:
            next_ver = bump_semver(base_ver, "minor")
        elif btn_id == 3:
            next_ver = bump_semver(base_ver, "major")
        else:
            next_ver = f"v{base_ver.lstrip('vV')}"

        self.lbl_semver_preview.setText(next_ver)
        if btn_id != 0:
            self.chk_create_tag.setChecked(True)
        else:
            self.chk_create_tag.setChecked(False)

    # =============================================================
    # ACCIONES: GIT ADD
    # =============================================================
    def _stage_all(self):
        if not self.project:
            return
        res = run_command(["git", "add", "-A"], cwd=self.project.path)
        if res.success:
            self.log_emitted.emit("Todos los archivos fueron preparados en staging (<code>git add -A</code>).")
            self.update_project(self.project)

    def _unstage_all(self):
        if not self.project:
            return
        res = run_command(["git", "restore", "--staged", "."], cwd=self.project.path)
        if res.success:
            self.log_emitted.emit("Todos los archivos fueron removidos de staging (<code>git restore --staged .</code>).")
            self.update_project(self.project)

    # =============================================================
    # ACCIONES: GIT PUSH
    # =============================================================
    def _execute_git_push(self, with_tags: bool = False):
        if not self.project:
            return
        cmd = ["git", "push"]
        if with_tags:
            cmd.append("--follow-tags")
        self.log_emitted.emit(f"Ejecutando: <code>{' '.join(cmd)}</code>...")
        res = run_command(cmd, cwd=self.project.path)
        if res.success:
            self.log_emitted.emit("Push remoto completado con éxito.")
            self.update_project(self.project)
            self.action_requested.emit("git_push_completed", {"with_tags": with_tags})
        else:
            self.log_emitted.emit(f"Push falló: {res.output}")

    # =============================================================
    # ACCIONES: IA COMMIT & ANIMACIÓN DE CARGA CON BLOQUEO
    # =============================================================
    def _start_ai_generation(self):
        """Inicia la animación de carga, bloquea los botones del sector y lanza el hilo de inferencia."""
        if not self.project or not self.project.path:
            return

        # 1. Bloquear todos los botones en Sector 1.1
        self._set_sector_locked(True)

        # 2. Configurar botón en estado de carga
        self.btn_ai_generate.setProperty("class", "cyber_btn_loading")
        self.btn_ai_generate.style().unpolish(self.btn_ai_generate)
        self.btn_ai_generate.style().polish(self.btn_ai_generate)

        # 3. Iniciar animación de spinner táctico
        self._spinner_frames = [
            "⠋ Sintetizando...", "⠙ Sintetizando...", "⠹ Sintetizando...", 
            "⠸ Sintetizando...", "⠼ Sintetizando...", "⠴ Sintetizando...", 
            "⠦ Sintetizando...", "⠧ Sintetizando...", "⠇ Sintetizando...", "⠏ Sintetizando..."
        ]
        self._spinner_idx = 0
        if not hasattr(self, "loading_spinner_timer"):
            self.loading_spinner_timer = QTimer(self)
            self.loading_spinner_timer.timeout.connect(self._cycle_spinner_frame)
        self.loading_spinner_timer.start(80)

        # 4. Determinar modelo e impacto
        model_type = "heavy" if self.btn_mode_heavy.isChecked() else "light"
        btn_id = self.semver_btn_group.checkedId()
        impact_map = {1: "PATCH", 2: "MINOR", 3: "MAJOR"}
        impact_type = impact_map.get(btn_id, "NONE")
        target_ver = self.lbl_semver_preview.text().strip()

        # 5. Iniciar Worker Thread asíncrono
        self._commit_worker = AICommitWorkerThread(
            project_path=Path(self.project.path),
            model_type=model_type,
            impact_type=impact_type,
            target_ver=target_ver,
            parent=self
        )
        self._commit_worker.finished_generation.connect(self._on_ai_generation_finished)
        self._commit_worker.start()

    def _cycle_spinner_frame(self):
        self._spinner_idx = (self._spinner_idx + 1) % len(self._spinner_frames)
        self.btn_ai_generate.setText(self._spinner_frames[self._spinner_idx])

    def _on_ai_generation_finished(self, success: bool, title: str, body: str, info: str):
        """Callback al recibir la propuesta del modelo: restaura el botón y desbloquea el sector."""
        if hasattr(self, "loading_spinner_timer"):
            self.loading_spinner_timer.stop()

        if success and title:
            self.txt_commit_subject.setText(title)
            self.txt_commit_body.setPlainText(body)
            self.log_emitted.emit(f"✨ Propuesta generada con éxito ({info}): <b>{title}</b>")
        else:
            self.log_emitted.emit(f"<span style='color: #94a3b8;'>Aviso de síntesis: {info}</span>")

        # Restaurar botón de generar
        self.btn_ai_generate.setText("✨ Generar con IA")
        self.btn_ai_generate.setProperty("class", "cyber_btn")
        self.btn_ai_generate.style().unpolish(self.btn_ai_generate)
        self.btn_ai_generate.style().polish(self.btn_ai_generate)

        # Desbloquear botones de Sector 1.1
        self._set_sector_locked(False)

    def _set_sector_locked(self, locked: bool):
        """Bloquea o desbloquea todos los controles interactivos del Sector 1.1."""
        self.btn_stage_all.setEnabled(not locked)
        self.btn_unstage_all.setEnabled(not locked)
        self.btn_push_direct.setEnabled(not locked)
        self.btn_push_tags.setEnabled(not locked)
        self.btn_commit.setEnabled(not locked)
        self.btn_ai_generate.setEnabled(not locked)
        self.btn_mode_light.setEnabled(not locked)
        self.btn_mode_heavy.setEnabled(not locked)
        for btn in self.semver_btn_group.buttons():
            btn.setEnabled(not locked)
        self.chk_create_tag.setEnabled(not locked)
        self.txt_commit_subject.setEnabled(not locked)
        self.txt_commit_body.setEnabled(not locked)
        for row in self._file_rows:
            row.set_locked(locked)

    def _submit_commit(self):
        """Valida y ejecuta el commit en Git, aplicando opcionalmente tag SemVer."""
        if not self.project or not self.project.path:
            return

        subject = self.txt_commit_subject.text().strip()
        body = self.txt_commit_body.toPlainText().strip()

        if not subject:
            self.log_emitted.emit("Error: El commit requiere un título o asunto.")
            return

        chk_res = run_command(["git", "diff", "--cached", "--quiet"], cwd=self.project.path)
        if chk_res.returncode == 0:
            u_chk = run_command(["git", "status", "--porcelain"], cwd=self.project.path)
            if not u_chk.stdout.strip():
                self.log_emitted.emit("Error: No hay cambios para confirmar en este repositorio.")
                return
            self.log_emitted.emit("Añadiendo cambios pendientes al staging antes de confirmar...")
            run_command(["git", "add", "-A"], cwd=self.project.path)

        full_msg = subject
        if body:
            full_msg = f"{subject}\n\n{body}"

        res = run_command(["git", "commit", "-m", full_msg], cwd=self.project.path)
        if not res.success:
            self.log_emitted.emit(f"Commit falló: {res.output}")
            return

        self.log_emitted.emit(f"🚀 Commit registrado con éxito: <b>{subject}</b>")
        self.txt_commit_subject.clear()
        self.txt_commit_body.clear()

        if self.chk_create_tag.isChecked():
            tag_name = self.lbl_semver_preview.text().strip()
            if tag_name:
                t_res = run_command(["git", "tag", "-a", tag_name, "-m", subject], cwd=self.project.path)
                if t_res.success:
                    self.log_emitted.emit(f"🏷 Etiqueta SemVer creada: <b>{tag_name}</b>")
                else:
                    self.log_emitted.emit(f"Error al crear etiqueta: {t_res.output}")

        self.update_project(self.project)
        self.action_requested.emit("git_commit_completed", {"subject": subject})


# =====================================================================
# SUB-SECTOR 1.2: GESTOR DE RAMAS (VISOR, CONTROL Y FUSIÓN ASISTIDA)
# =====================================================================

class BranchListItemWidget(QFrame):
    """
    Fila compacta para listar ramas en el Sub-sector 1.2.
    Permite:
    - Ver el nombre y estado de la rama.
    - Clic en la fila: Selecciona la rama bidireccionalmente y proyecta en el grafo.
    - Botón Cambiar: Realiza git checkout a la rama.
    - Botón Desplegar: Sube / publica la rama al repositorio remoto (git push origin <rama>).
    - Botón 🗑: Abre diálogo de confirmación crítica que exige escribir el nombre de la rama para borrarla.
    """
    clicked = Signal(str)
    checkout_requested = Signal(str)
    push_requested = Signal(str)
    delete_requested = Signal(str)

    def __init__(
        self,
        branch_name: str,
        is_active: bool = False,
        is_selected: bool = False,
        is_published: bool = False,
        is_merge_mode: bool = False,
        parent=None
    ):
        super().__init__(parent)
        self.branch_name = branch_name
        self.is_active = is_active
        self.is_selected = is_selected
        self.is_published = is_published
        self.is_merge_mode = is_merge_mode
        self.setCursor(Qt.PointingHandCursor)

        self._apply_style()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        # Icono / Badge de estado
        lbl_icon = QLabel("● HEAD" if is_active else ("🔀" if is_merge_mode else "🌿"))
        lbl_icon.setProperty("class", "badge_staged" if is_active else "badge_pending")
        layout.addWidget(lbl_icon)

        # Nombre de la rama
        lbl_name = QLabel(branch_name)
        lbl_name.setProperty("class", "file_path_label")
        layout.addWidget(lbl_name, 1)

        if is_merge_mode:
            # En modo fusión (Ventana 3: Integración), solo mostramos el indicador de selección
            if is_active:
                lbl_tag = QLabel("ACTIVA (DESTINO)")
                lbl_tag.setProperty("class", "badge_telemetry")
                layout.addWidget(lbl_tag)
            else:
                self.lbl_merge_action = QLabel("● SELECCIONADA" if is_selected else "Seleccionar")
                self.lbl_merge_action.setProperty("class", "badge_staged" if is_selected else "badge_telemetry")
                layout.addWidget(self.lbl_merge_action)
        else:
            # En modo control (Ventana 2): Ver, Cambiar, Desplegar (solo si no publicada), Eliminar
            if is_active:
                lbl_tag = QLabel("ACTIVA")
                lbl_tag.setProperty("class", "badge_telemetry")
                layout.addWidget(lbl_tag)

                # Desplegar SOLO para ramas no publicadas
                if not self.is_published:
                    btn_push = QPushButton("Desplegar")
                    btn_push.setProperty("class", "cyber_btn_compact")
                    btn_push.setCursor(Qt.PointingHandCursor)
                    btn_push.setToolTip(f"Subir / publicar rama actual '{branch_name}' al repositorio remoto")
                    btn_push.clicked.connect(lambda: self.push_requested.emit(self.branch_name))
                    layout.addWidget(btn_push)
            else:
                # Botón Cambiar (Checkout)
                btn_switch = QPushButton("Cambiar")
                btn_switch.setProperty("class", "cyber_btn_compact")
                btn_switch.setCursor(Qt.PointingHandCursor)
                btn_switch.setToolTip(f"Cambiarse a la rama '{branch_name}' (git checkout)")
                btn_switch.clicked.connect(lambda: self.checkout_requested.emit(self.branch_name))
                layout.addWidget(btn_switch)

                # Desplegar SOLO para ramas no publicadas
                if not self.is_published:
                    btn_push = QPushButton("Desplegar")
                    btn_push.setProperty("class", "cyber_btn_compact")
                    btn_push.setCursor(Qt.PointingHandCursor)
                    btn_push.setToolTip(f"Subir / publicar rama local '{branch_name}' al repositorio remoto")
                    btn_push.clicked.connect(lambda: self.push_requested.emit(self.branch_name))
                    layout.addWidget(btn_push)

                # Botón rápido para eliminar con confirmación crítica escrita
                btn_del = QPushButton("🗑")
                btn_del.setProperty("class", "cyber_btn_danger_compact")
                btn_del.setCursor(Qt.PointingHandCursor)
                btn_del.setToolTip(f"Eliminar rama local '{branch_name}'")
                btn_del.clicked.connect(lambda: self.delete_requested.emit(self.branch_name))
                layout.addWidget(btn_del)

    def _apply_style(self):
        if self.is_selected:
            self.setProperty("class", "branch_item_row_selected")
        elif self.is_active:
            self.setProperty("class", "branch_item_row_active")
        else:
            self.setProperty("class", "branch_item_row")
        self.style().unpolish(self)
        self.style().polish(self)

    def set_selected(self, selected: bool):
        self.is_selected = selected
        if self.is_merge_mode and hasattr(self, 'lbl_merge_action'):
            if not self.is_active:
                self.lbl_merge_action.setText("● SELECCIONADA" if selected else "Seleccionar")
                self.lbl_merge_action.setProperty("class", "badge_staged" if selected else "badge_telemetry")
                self.lbl_merge_action.style().unpolish(self.lbl_merge_action)
                self.lbl_merge_action.style().polish(self.lbl_merge_action)
        self._apply_style()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.branch_name)
        super().mousePressEvent(event)


class Sector12BranchesView(QWidget):
    """
    Sub-sector 1.2: Control Táctico de Ramas y Fusión Asistida.
    Estructura en 3 Paneles:
    - Izquierda: Visor del Grafo de Ramas (el mismo del Sector 0, interactivo y en vertical).
    - Derecha Superior: Control de ramas (Crear, Eliminar, Desplegar / Checkout y Refrescar).
    - Derecha Inferior: Módulo de Fusión (Merge), con selección interactiva que proyecta en vivo
      el merge en el grafo, con inputs de Título y Descripción estructurada, y confirmación segura.
    """
    log_emitted = Signal(str)
    action_requested = Signal(str, dict)

    def __init__(self, project: Project = None, parent=None):
        super().__init__(parent)
        self.project = project
        self.selected_merge_branch: Optional[str] = None
        self._ctrl_branch_widgets: dict[str, BranchListItemWidget] = {}
        self._merge_branch_widgets: dict[str, BranchListItemWidget] = {}
        self.init_ui()

        if self.project:
            self.update_project(self.project)

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Splitter principal horizontal: Grafo a la izquierda (50%), Paneles de control a la derecha (50%)
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setChildrenCollapsible(False)

        # =============================================================
        # 1. PANEL IZQUIERDO: VISOR DE GRAFO DE RAMAS (SECTOR 0)
        # =============================================================
        left_card = QFrame()
        left_card.setProperty("class", "sector_card")
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(14, 12, 14, 12)
        left_layout.setSpacing(8)

        # Encabezado del visor de grafo
        g_header = QHBoxLayout()
        g_header.setSpacing(8)

        g_title_box = QVBoxLayout()
        g_title_box.setSpacing(2)
        lbl_g_tag = QLabel("SECTOR 1.2 // TOPOLOGÍA VISUAL")
        lbl_g_tag.setProperty("class", "sector_micro_tag")
        lbl_g_title = QLabel("🌿 Grafo Topológico & Proyección")
        lbl_g_title.setProperty("class", "sector_title")
        g_title_box.addWidget(lbl_g_tag)
        g_title_box.addWidget(lbl_g_title)
        g_header.addLayout(g_title_box)

        g_header.addStretch()

        # Botones de navegación y zoom
        self.btn_orient = QPushButton("↕ Vertical")
        self.btn_orient.setProperty("class", "cyber_btn_compact")
        self.btn_orient.setToolTip("Alternar orientación: Vertical / Horizontal")
        self.btn_orient.clicked.connect(self._toggle_orientation)
        g_header.addWidget(self.btn_orient)

        btn_zoom_in = QPushButton("➕")
        btn_zoom_in.setProperty("class", "cyber_btn_compact")
        btn_zoom_in.setFixedSize(28, 28)
        btn_zoom_in.setToolTip("Acercar Grafo")
        btn_zoom_in.clicked.connect(self._zoom_in)
        g_header.addWidget(btn_zoom_in)

        btn_zoom_out = QPushButton("➖")
        btn_zoom_out.setProperty("class", "cyber_btn_compact")
        btn_zoom_out.setFixedSize(28, 28)
        btn_zoom_out.setToolTip("Alejar Grafo")
        btn_zoom_out.clicked.connect(self._zoom_out)
        g_header.addWidget(btn_zoom_out)

        btn_zoom_reset = QPushButton("↺")
        btn_zoom_reset.setProperty("class", "cyber_btn_compact")
        btn_zoom_reset.setFixedSize(28, 28)
        btn_zoom_reset.setToolTip("Restablecer Vista")
        btn_zoom_reset.clicked.connect(self._zoom_reset)
        g_header.addWidget(btn_zoom_reset)

        left_layout.addLayout(g_header)

        # Lienzo del grafo Lumen
        self.git_graph = LumenHorizontalGitGraphView(left_card)
        self.git_graph.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left_layout.addWidget(self.git_graph, 1)

        self.main_splitter.addWidget(left_card)

        # =============================================================
        # 2. PANEL DERECHO: SPLITTER VERTICAL (ARRIBA: CONTROL | ABAJO: MERGE)
        # =============================================================
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.right_splitter = QSplitter(Qt.Vertical)
        self.right_splitter.setChildrenCollapsible(False)

        # -------------------------------------------------------------
        # 2.1 VENTANA SUPERIOR DERECHA: CONTROL DE RAMAS (LISTA COMPACTA)
        # -------------------------------------------------------------
        card_control = QFrame()
        card_control.setProperty("class", "sector_card")
        ctrl_layout = QVBoxLayout(card_control)
        ctrl_layout.setContentsMargins(14, 12, 14, 12)
        ctrl_layout.setSpacing(8)

        # Encabezado
        ctrl_header = QHBoxLayout()
        ctrl_box = QVBoxLayout()
        ctrl_box.setSpacing(2)
        lbl_c_tag = QLabel("CONTROL DE RAMAS")
        lbl_c_tag.setProperty("class", "sector_micro_tag")
        lbl_c_title = QLabel("⚡ Ramas del Repositorio")
        lbl_c_title.setProperty("class", "sector_title")
        ctrl_box.addWidget(lbl_c_tag)
        ctrl_box.addWidget(lbl_c_title)
        ctrl_header.addLayout(ctrl_box)

        ctrl_header.addStretch()

        self.lbl_branch_status = QLabel("HEAD: -")
        self.lbl_branch_status.setProperty("class", "badge_telemetry")
        ctrl_header.addWidget(self.lbl_branch_status)

        self.btn_refresh = QPushButton("🔄")
        self.btn_refresh.setProperty("class", "cyber_btn_compact")
        self.btn_refresh.setFixedSize(28, 28)
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.setToolTip("Refrescar ramas y topología del repositorio")
        self.btn_refresh.clicked.connect(self._refresh_branches)
        ctrl_header.addWidget(self.btn_refresh)
        ctrl_layout.addLayout(ctrl_header)

        # Fila de Creación Rápida de Ramas
        create_row = QHBoxLayout()
        create_row.setSpacing(6)
        self.txt_new_branch = QLineEdit()
        self.txt_new_branch.setProperty("class", "cyber_input")
        self.txt_new_branch.setPlaceholderText("Nueva rama (ej. feature/tactical-view)...")
        self.txt_new_branch.returnPressed.connect(self._create_branch)
        create_row.addWidget(self.txt_new_branch, 1)

        self.btn_create_branch = QPushButton("✨ Crear")
        self.btn_create_branch.setProperty("class", "cyber_btn_compact")
        self.btn_create_branch.setCursor(Qt.PointingHandCursor)
        self.btn_create_branch.clicked.connect(self._create_branch)
        create_row.addWidget(self.btn_create_branch)
        ctrl_layout.addLayout(create_row)

        # Lista scrolleable compacta de ramas (Ventana 2)
        scroll_ctrl_branches = QScrollArea()
        scroll_ctrl_branches.setProperty("class", "clean_scroll")
        scroll_ctrl_branches.setWidgetResizable(True)
        scroll_ctrl_branches.setMinimumHeight(100)

        self.ctrl_branch_container = QWidget()
        self.ctrl_branch_layout = QVBoxLayout(self.ctrl_branch_container)
        self.ctrl_branch_layout.setContentsMargins(0, 0, 0, 0)
        self.ctrl_branch_layout.setSpacing(4)
        scroll_ctrl_branches.setWidget(self.ctrl_branch_container)
        ctrl_layout.addWidget(scroll_ctrl_branches, 1)

        self.right_splitter.addWidget(card_control)

        # -------------------------------------------------------------
        # 2.2 VENTANA INFERIOR DERECHA: FUSIÓN DE RAMAS (GIT MERGE)
        # -------------------------------------------------------------
        card_merge = QFrame()
        card_merge.setProperty("class", "sector_card")
        merge_layout = QVBoxLayout(card_merge)
        merge_layout.setContentsMargins(14, 12, 14, 12)
        merge_layout.setSpacing(10)

        # Encabezado
        m_header = QHBoxLayout()
        m_box = QVBoxLayout()
        m_box.setSpacing(2)
        lbl_m_tag = QLabel("INTEGRACIÓN & FUSIÓN")
        lbl_m_tag.setProperty("class", "sector_micro_tag")
        lbl_m_title = QLabel("🔀 Fusión de Ramas (Git Merge)")
        lbl_m_title.setProperty("class", "sector_title")
        m_box.addWidget(lbl_m_tag)
        m_box.addWidget(lbl_m_title)
        m_header.addLayout(m_box)

        m_header.addStretch()

        self.lbl_merge_target = QLabel("Destino: HEAD")
        self.lbl_merge_target.setProperty("class", "badge_telemetry")
        m_header.addWidget(self.lbl_merge_target)
        merge_layout.addLayout(m_header)

        # Subtítulo explicativo
        lbl_m_hint = QLabel("Selecciona la rama de origen que deseas fusionar en la rama activa. El grafo simulará la unión en tiempo real:")
        lbl_m_hint.setProperty("class", "sector_desc")
        lbl_m_hint.setWordWrap(True)
        merge_layout.addWidget(lbl_m_hint)

        # Lista scrolleable de ramas disponibles para fusionar
        scroll_branches = QScrollArea()
        scroll_branches.setProperty("class", "clean_scroll")
        scroll_branches.setWidgetResizable(True)
        scroll_branches.setMinimumHeight(110)

        self.branch_list_container = QWidget()
        self.branch_list_layout = QVBoxLayout(self.branch_list_container)
        self.branch_list_layout.setContentsMargins(0, 0, 0, 0)
        self.branch_list_layout.setSpacing(4)
        scroll_branches.setWidget(self.branch_list_container)
        merge_layout.addWidget(scroll_branches, 1)

        # Campos de Título y Descripción del Merge
        self.txt_merge_title = QLineEdit()
        self.txt_merge_title.setProperty("class", "cyber_input")
        self.txt_merge_title.setPlaceholderText("Título del Merge (ej. HEX:0053 | Integración de feature en main)...")
        merge_layout.addWidget(self.txt_merge_title)

        self.txt_merge_desc = QTextEdit()
        self.txt_merge_desc.setProperty("class", "cyber_input")
        self.txt_merge_desc.setPlaceholderText("Descripción técnica de la fusión (viñetas de cambios, módulos fusionados)...")
        self.txt_merge_desc.setMaximumHeight(70)
        merge_layout.addWidget(self.txt_merge_desc)

        # Fila de botón de confirmación
        m_btn_row = QHBoxLayout()
        m_btn_row.addStretch()

        self.btn_confirm_merge = QPushButton("🚀 Confirmar Fusión & Grabar")
        self.btn_confirm_merge.setProperty("class", "cyber_btn_primary")
        self.btn_confirm_merge.setCursor(Qt.PointingHandCursor)
        self.btn_confirm_merge.setEnabled(False)  # Se habilita al seleccionar una rama de la lista
        self.btn_confirm_merge.clicked.connect(self._execute_merge)
        m_btn_row.addWidget(self.btn_confirm_merge)
        merge_layout.addLayout(m_btn_row)

        self.right_splitter.addWidget(card_merge)

        # Configurar proporción vertical del panel derecho (45% control, 55% merge)
        self.right_splitter.setSizes([260, 360])
        right_layout.addWidget(self.right_splitter, 1)

        self.main_splitter.addWidget(right_container)

        # Proporción horizontal: 48% Grafo a la izquierda, 52% Controles a la derecha
        self.main_splitter.setSizes([500, 540])
        root_layout.addWidget(self.main_splitter, 1)

    # =============================================================
    # LÓGICA DE ACTUALIZACIÓN Y SINCRONIZACIÓN
    # =============================================================
    def update_project(self, project: Project):
        """Carga el grafo del proyecto y la lista de ramas operacionales."""
        self.project = project
        if not project or not project.path or not Path(project.path).is_dir():
            return

        p_path = Path(project.path)
        if not (p_path / ".git").is_dir():
            self.lbl_branch_status.setText("No es un repositorio Git válido")
            return

        # 1. Obtener rama activa
        res_active = run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=p_path)
        active_branch = res_active.stdout.strip() if res_active.success else "main"
        self.lbl_branch_status.setText(f"Rama activa actual: <b>{active_branch}</b>")
        self.lbl_merge_target.setText(f"Destino: {active_branch}")

        # 2. Cargar Grafo de Ramas (en modo vertical por defecto)
        self.git_graph.load_project_graph(str(p_path))

        # 3. Poblar lista de ramas para fusión y control
        self._populate_branch_list(p_path, active_branch)

    def _populate_branch_list(self, p_path: Path, active_branch: str):
        """Llena la lista de ramas locales compacta (Ventana 2) y la lista de fusión (Ventana 3)."""
        # 1. Limpiar lista de la Ventana 2 (Control)
        while self.ctrl_branch_layout.count():
            item = self.ctrl_branch_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 2. Limpiar lista de la Ventana 3 (Merge)
        while self.branch_list_layout.count():
            item = self.branch_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._ctrl_branch_widgets.clear()
        self._merge_branch_widgets.clear()

        # 1. Obtener ramas locales y su upstream tracking
        res_upstream = run_command(["git", "for-each-ref", "--format=%(refname:short)|%(upstream:short)", "refs/heads/"], cwd=p_path)
        upstream_map = {}
        branch_names = []
        if res_upstream.success and res_upstream.stdout.strip():
            for line in res_upstream.stdout.splitlines():
                parts = line.strip().split("|", 1)
                b = parts[0].strip()
                if b:
                    branch_names.append(b)
                    upstream_map[b] = parts[1].strip() if len(parts) > 1 else ""

        # 2. Obtener nombres de ramas remotas existentes para verificar publicación
        res_remotes = run_command(["git", "branch", "-r", "--format=%(refname:short)"], cwd=p_path)
        remote_branches = set()
        if res_remotes.success and res_remotes.stdout.strip():
            for line in res_remotes.stdout.splitlines():
                b = line.strip()
                if b:
                    remote_branches.add(b)
                    if b.startswith("origin/"):
                        remote_branches.add(b[7:])

        def _check_published(name: str) -> bool:
            if upstream_map.get(name):
                return True
            if name in remote_branches or f"origin/{name}" in remote_branches:
                return True
            return False

        if not branch_names:
            lbl_empty1 = QLabel("No hay ramas locales.")
            lbl_empty1.setProperty("class", "sector_desc")
            self.ctrl_branch_layout.addWidget(lbl_empty1)

            lbl_empty2 = QLabel("No hay ramas disponibles para fusión.")
            lbl_empty2.setProperty("class", "sector_desc")
            self.branch_list_layout.addWidget(lbl_empty2)
            return

        for b_name in branch_names:
            is_active = (b_name == active_branch)
            is_pub = _check_published(b_name)

            # Item para Ventana 2 (Control: Ver, Cambiar, Desplegar si no publicada, Eliminar)
            ctrl_item = BranchListItemWidget(b_name, is_active=is_active, is_published=is_pub, is_merge_mode=False)
            ctrl_item.clicked.connect(self._on_ctrl_branch_clicked)
            ctrl_item.checkout_requested.connect(self._checkout_branch)
            ctrl_item.push_requested.connect(self._push_branch)
            ctrl_item.delete_requested.connect(self._delete_branch)
            self._ctrl_branch_widgets[b_name] = ctrl_item
            self.ctrl_branch_layout.addWidget(ctrl_item)

            # Item para Ventana 3 (Merge: Selección para fusionar)
            merge_item = BranchListItemWidget(b_name, is_active=is_active, is_published=is_pub, is_merge_mode=True)
            merge_item.clicked.connect(self._on_merge_branch_clicked)
            self._merge_branch_widgets[b_name] = merge_item
            self.branch_list_layout.addWidget(merge_item)

        self.ctrl_branch_layout.addStretch()
        self.branch_list_layout.addStretch()

    def _on_ctrl_branch_clicked(self, branch_name: str):
        """Clic en Ventana 2 (Control): selecciona en Control Y en Integración, y proyecta simulación."""
        for name, w in self._ctrl_branch_widgets.items():
            w.set_selected(name == branch_name)
        for name, w in self._merge_branch_widgets.items():
            w.set_selected(name == branch_name)
        self._apply_merge_preview(branch_name)

    def _on_merge_branch_clicked(self, branch_name: str):
        """Clic en Ventana 3 (Integración): selecciona SOLO en Integración (no viceversa) y proyecta simulación."""
        for name, w in self._merge_branch_widgets.items():
            w.set_selected(name == branch_name)
        self._apply_merge_preview(branch_name)

    def _apply_merge_preview(self, branch_name: str):
        """Actualiza el formulario de fusión y proyecta el nodo de unión simulado en el grafo."""
        if not self.project:
            return

        self.selected_merge_branch = branch_name

        # Rama activa actual
        res_active = run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=self.project.path)
        active_branch = res_active.stdout.strip() if res_active.success else "main"

        if branch_name == active_branch:
            self.btn_confirm_merge.setEnabled(False)
            self.txt_merge_title.clear()
            self.txt_merge_desc.clear()
            # Restaurar grafo sin simulación
            self.git_graph.load_project_graph(str(self.project.path))
            self.log_emitted.emit(f"Rama seleccionada: <b>{branch_name}</b> (es la rama activa actual).")
            return

        # Habilitar fusión y proyectar simulación en el Grafo
        self.btn_confirm_merge.setEnabled(True)
        default_title = f"HEX:0053 | Fusión de rama '{branch_name}' en '{active_branch}'"
        self.txt_merge_title.setText(default_title)
        self.txt_merge_desc.setPlainText(f"- Integración táctica de cambios desde {branch_name}.\n- Validación de consistencia y convergencia de código.")

        # Disparar simulación visual en el Grafo
        sim_data = {
            "source_branch": branch_name,
            "target_branch": active_branch,
            "title": f"Fusión: {branch_name} ➔ {active_branch}"
        }
        self.git_graph.load_project_graph(str(self.project.path), simulated_merge=sim_data)
        self.log_emitted.emit(f"Proyectando simulación de fusión: <b>{branch_name}</b> ➔ <b>{active_branch}</b>.")

    # =============================================================
    # ACCIONES: CONTROL DE RAMAS (CREAR, CAMBIAR, DESPLEGAR, ELIMINAR, REFRESCAR)
    # =============================================================
    def _create_branch(self):
        """Crea una nueva rama y conmuta a ella inmediatamente (git checkout -b)."""
        if not self.project or not self.project.path:
            return

        b_name = self.txt_new_branch.text().strip()
        if not b_name:
            self.log_emitted.emit("Error: Ingresa un nombre válido para la nueva rama.")
            return

        res = run_command(["git", "checkout", "-b", b_name], cwd=self.project.path)
        if res.success:
            self.log_emitted.emit(f"🌿 Nueva rama creada: <b>{b_name}</b> (ahora activa).")
            self.txt_new_branch.clear()
            self.update_project(self.project)
            self.action_requested.emit("git_branch_created", {"branch": b_name})
        else:
            self.log_emitted.emit(f"Error al crear rama: {res.output}")

    def _checkout_branch(self, branch_name: str):
        """Conmuta (cambiar de rama / git checkout) a la rama especificada."""
        if not self.project or not self.project.path or not branch_name:
            return

        res = run_command(["git", "checkout", branch_name], cwd=self.project.path)
        if res.success:
            self.log_emitted.emit(f"🔀 Cambio de rama exitoso: Ahora estás en <b>{branch_name}</b>")
            self.update_project(self.project)
            self.action_requested.emit("git_branch_switched", {"branch": branch_name})
        else:
            self.log_emitted.emit(f"Error al cambiar a la rama: {res.output}")

    def _push_branch(self, branch_name: str):
        """Despliega / sube la rama al repositorio remoto (git push -u origin <branch_name>)."""
        if not self.project or not self.project.path or not branch_name:
            return

        self.log_emitted.emit(f"🚀 Desplegando rama <b>{branch_name}</b> al repositorio remoto...")
        res = run_command(["git", "push", "-u", "origin", branch_name], cwd=self.project.path)
        if res.success:
            self.log_emitted.emit(f"✨ Rama <b>{branch_name}</b> desplegada con éxito en el remoto.")
            self.update_project(self.project)
            self.action_requested.emit("git_branch_pushed", {"branch": branch_name})
        else:
            self.log_emitted.emit(f"Alerta al desplegar rama: {res.output}")

    def _delete_branch(self, branch_name: str):
        """
        Elimina una rama local requiriendo una doble confirmación estricta:
        El usuario DEBE escribir exactamente el nombre de la rama para confirmar.
        """
        if not self.project or not self.project.path or not branch_name:
            return

        # Prevenir eliminar la rama activa
        res_active = run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=self.project.path)
        active_b = res_active.stdout.strip() if res_active.success else ""
        if branch_name == active_b:
            self.log_emitted.emit(f"Operación denegada: No puedes eliminar la rama activa actual (<b>{branch_name}</b>).")
            return

        # Diálogo modal de confirmación crítica
        dialog = QDialog(self)
        dialog.setWindowTitle("Confirmación Crítica de Eliminación")
        dialog.setModal(True)
        dialog.setFixedWidth(440)
        dialog.setProperty("class", "cyber_dialog")

        d_layout = QVBoxLayout(dialog)
        d_layout.setContentsMargins(20, 18, 20, 18)
        d_layout.setSpacing(12)

        lbl_tag = QLabel("ACCION DESTRUCTIVA // ELIMINACION DE RAMA")
        lbl_tag.setProperty("class", "sector_micro_tag")
        d_layout.addWidget(lbl_tag)

        lbl_msg = QLabel(
            f"¿Estás seguro de que deseas eliminar permanentemente la rama <b>{branch_name}</b>?<br><br>"
            f"Para confirmar, escribe exactamente el nombre de la rama a continuación:"
        )
        lbl_msg.setProperty("class", "sector_desc")
        lbl_msg.setWordWrap(True)
        d_layout.addWidget(lbl_msg)

        txt_confirm = QLineEdit()
        txt_confirm.setProperty("class", "cyber_input")
        txt_confirm.setPlaceholderText(f"Escribe '{branch_name}' para confirmar...")
        d_layout.addWidget(txt_confirm)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setProperty("class", "cyber_btn")
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.clicked.connect(dialog.reject)
        btn_row.addWidget(btn_cancel)

        btn_confirm = QPushButton("🗑 Confirmar Eliminación")
        btn_confirm.setProperty("class", "cyber_btn_danger")
        btn_confirm.setCursor(Qt.PointingHandCursor)
        btn_confirm.setEnabled(False)  # Solo se habilita si el texto coincide exactamente

        def _check_text_match(text: str):
            btn_confirm.setEnabled(text.strip() == branch_name)

        txt_confirm.textChanged.connect(_check_text_match)
        btn_confirm.clicked.connect(dialog.accept)
        btn_row.addWidget(btn_confirm)
        d_layout.addLayout(btn_row)

        if dialog.exec() != QDialog.Accepted:
            self.log_emitted.emit(f"Eliminación de rama <b>{branch_name}</b> cancelada por el usuario.")
            return

        # Ejecutar eliminación segura (-d) primero
        res = run_command(["git", "branch", "-d", branch_name], cwd=self.project.path)
        if res.success:
            self.log_emitted.emit(f"🗑 Rama eliminada con éxito: <b>{branch_name}</b>")
            self.update_project(self.project)
            self.action_requested.emit("git_branch_deleted", {"branch": branch_name})
        else:
            # Si tiene commits no fusionados, forzar con -D
            self.log_emitted.emit(f"Aviso: La rama tiene commits no fusionados. Aplicando eliminación forzada confirmada...")
            res_force = run_command(["git", "branch", "-D", branch_name], cwd=self.project.path)
            if res_force.success:
                self.log_emitted.emit(f"🗑 Rama eliminada definitivamente (forzada): <b>{branch_name}</b>")
                self.update_project(self.project)
                self.action_requested.emit("git_branch_deleted", {"branch": branch_name})
            else:
                self.log_emitted.emit(f"Error al eliminar rama: {res_force.output}")

    def _refresh_branches(self):
        """Recarga manualmente el estado de las ramas y el grafo."""
        if self.project:
            self.update_project(self.project)
            self.log_emitted.emit("Topología de ramas y grafo actualizados.")

    # =============================================================
    # ACCIONES: FUSIÓN DE RAMAS (GIT MERGE)
    # =============================================================
    def _execute_merge(self):
        """Ejecuta git merge de la rama seleccionada sobre la rama activa con mensaje estructurado."""
        if not self.project or not self.project.path or not self.selected_merge_branch:
            return

        src_branch = self.selected_merge_branch
        title = self.txt_merge_title.text().strip() or f"Merge branch '{src_branch}'"
        desc = self.txt_merge_desc.toPlainText().strip()
        full_msg = f"{title}\n\n{desc}" if desc else title

        self.log_emitted.emit(f"Iniciando fusión de <b>{src_branch}</b> con mensaje estructurado...")

        res = run_command(["git", "merge", "--no-ff", "-m", full_msg, src_branch], cwd=self.project.path)
        if res.success:
            self.log_emitted.emit(f"🎉 Fusión completada con éxito: <b>{src_branch}</b> integrada.")
            self.txt_merge_title.clear()
            self.txt_merge_desc.clear()
            self.btn_confirm_merge.setEnabled(False)
            self.selected_merge_branch = None
            self.update_project(self.project)
            self.action_requested.emit("git_merge_completed", {"source": src_branch})
        else:
            self.log_emitted.emit(f"Alerta en fusión: {res.output}")
            self.log_emitted.emit("Es posible que existan conflictos. Resuelve los conflictos en tus archivos o cancela con <code>git merge --abort</code>.")

    # =============================================================
    # CONTROLES DEL GRAFO (ORIENTACIÓN Y ZOOM)
    # =============================================================
    def _toggle_orientation(self):
        new_orient = self.git_graph.toggle_orientation()
        self.btn_orient.setText("↕ Vertical" if new_orient == "vertical" else "↔ Horizontal")

    def _zoom_in(self):
        self.git_graph.zoom_in()

    def _zoom_out(self):
        self.git_graph.zoom_out()

    def _zoom_reset(self):
        self.git_graph.zoom_reset()




# =====================================================================
# SUB-SECTOR 1.3: ESTADO & SINCRONIZACIÓN (SUPER GIT STATUS)
# =====================================================================

class WorkingTreeFileRowWidget(QFrame):
    """Fila visual compacta para un archivo en el árbol de trabajo (Super Git Status)."""
    def __init__(self, file_path: str, status_code: str, parent=None):
        super().__init__(parent)
        self.setProperty("class", "commit_traffic_row")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        # Determinar badge
        badge_text = "MODIFIED"
        badge_class = "badge_pending"
        code = status_code.strip()
        if code.startswith("?") or "??" in code:
            badge_text = "NEW"
            badge_class = "badge_pending"
        elif code.startswith("A") or (len(code) > 0 and code[0] in "MADRC"):
            badge_text = "STAGED"
            badge_class = "badge_staged"
        elif "D" in code:
            badge_text = "DELETED"
            badge_class = "badge_pending"
        elif "M" in code:
            badge_text = "MODIFIED"
            badge_class = "badge_pending"

        lbl_badge = QLabel(badge_text)
        lbl_badge.setProperty("class", badge_class)
        layout.addWidget(lbl_badge)

        lbl_path = QLabel(file_path)
        lbl_path.setProperty("class", "file_path_label")
        layout.addWidget(lbl_path, 1)


class CommitTrafficRowWidget(QFrame):
    """Fila visual compacta para un commit en tránsito (Saliente o Entrante)."""
    def __init__(self, commit_hash: str, subject: str, meta: str = "", parent=None):
        super().__init__(parent)
        self.setProperty("class", "commit_traffic_row")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        lbl_hash = QLabel(commit_hash)
        lbl_hash.setProperty("class", "badge_pending")
        layout.addWidget(lbl_hash)

        lbl_subj = QLabel(subject)
        lbl_subj.setProperty("class", "file_path_label")
        layout.addWidget(lbl_subj, 1)

        if meta:
            lbl_meta = QLabel(meta)
            lbl_meta.setProperty("class", "sector_desc")
            layout.addWidget(lbl_meta)


class Sector13SyncView(QWidget):
    """
    Sub-sector 1.3: Super Git Status & Topología de Sincronización.
    Diseño Táctico Dividido:
    - Izquierda: Grafo Topológico de Estado (simula ramas no integradas/descargadas, posición de HEAD y atraso visual).
    - Derecha Superior: Identidad, Conmutador de Visibilidad GitHub y Maniobras de Red (Fetch, Pull, Push, Sync).
    - Derecha Inferior: Radiografía del Estado (Árbol de trabajo con Staged/Modified/Untracked, Stashes, Commits en Desfase y Terminal).
    """
    log_emitted = Signal(str)
    action_requested = Signal(str, dict)

    def __init__(self, project: Project = None, parent=None):
        super().__init__(parent)
        self.project = project
        self.init_ui()
        if self.project:
            self.update_project(self.project)

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setChildrenCollapsible(False)

        # =============================================================
        # 1. PANEL IZQUIERDO: GRAFO DE ESTADO & RAMAS NO INTEGRADAS (50%)
        # =============================================================
        left_card = QFrame()
        left_card.setProperty("class", "sector_card")
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(14, 12, 14, 12)
        left_layout.setSpacing(8)

        # Encabezado con HUD de posición y atraso
        g_header = QHBoxLayout()
        g_header.setSpacing(8)

        g_title_box = QVBoxLayout()
        g_title_box.setSpacing(2)
        lbl_g_tag = QLabel("SECTOR 1.3 // TOPOLOGÍA DE DIVERGENCIA")
        lbl_g_tag.setProperty("class", "sector_micro_tag")
        lbl_g_title = QLabel("🌿 Grafo de Estado & Ramas No Integradas")
        lbl_g_title.setProperty("class", "sector_title")
        g_title_box.addWidget(lbl_g_tag)
        g_title_box.addWidget(lbl_g_title)
        g_header.addLayout(g_title_box)

        g_header.addStretch()

        # Botones de orientación y zoom
        self.btn_orient = QPushButton("↕ Vertical")
        self.btn_orient.setProperty("class", "cyber_btn_compact")
        self.btn_orient.setToolTip("Alternar orientación: Vertical / Horizontal")
        self.btn_orient.clicked.connect(self._toggle_orientation)
        g_header.addWidget(self.btn_orient)

        btn_zoom_in = QPushButton("➕")
        btn_zoom_in.setProperty("class", "cyber_btn_compact")
        btn_zoom_in.setFixedSize(28, 28)
        btn_zoom_in.clicked.connect(self._zoom_in)
        g_header.addWidget(btn_zoom_in)

        btn_zoom_out = QPushButton("➖")
        btn_zoom_out.setProperty("class", "cyber_btn_compact")
        btn_zoom_out.setFixedSize(28, 28)
        btn_zoom_out.clicked.connect(self._zoom_out)
        g_header.addWidget(btn_zoom_out)

        btn_zoom_reset = QPushButton("↺")
        btn_zoom_reset.setProperty("class", "cyber_btn_compact")
        btn_zoom_reset.setFixedSize(28, 28)
        btn_zoom_reset.clicked.connect(self._zoom_reset)
        g_header.addWidget(btn_zoom_reset)

        left_layout.addLayout(g_header)

        # HUD Strip de Diagnóstico Topológico
        hud_row = QHBoxLayout()
        hud_row.setSpacing(6)

        self.lbl_hud_head = QLabel("📍 HEAD: -")
        self.lbl_hud_head.setProperty("class", "badge_staged")
        hud_row.addWidget(self.lbl_hud_head)

        self.lbl_hud_delay = QLabel("⏳ Desfase: 0 Ahead / 0 Behind")
        self.lbl_hud_delay.setProperty("class", "badge_telemetry")
        hud_row.addWidget(self.lbl_hud_delay)

        self.lbl_hud_unmerged = QLabel("⚠️ 0 sin integrar")
        self.lbl_hud_unmerged.setProperty("class", "badge_pending")
        hud_row.addWidget(self.lbl_hud_unmerged)

        hud_row.addStretch()
        left_layout.addLayout(hud_row)

        # Lienzo del Grafo Lumen
        self.git_graph = LumenHorizontalGitGraphView(left_card)
        self.git_graph.set_orientation("vertical")
        self.git_graph.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left_layout.addWidget(self.git_graph, 1)

        self.main_splitter.addWidget(left_card)

        # =============================================================
        # 2. PANEL DERECHO: SUPER GIT STATUS & MANIOBRAS (50%)
        # =============================================================
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.right_splitter = QSplitter(Qt.Vertical)
        self.right_splitter.setChildrenCollapsible(False)

        # -------------------------------------------------------------
        # 2.1 VENTANA SUPERIOR DERECHA: IDENTIDAD, VISIBILIDAD & RED (~42%)
        # -------------------------------------------------------------
        card_ops = QFrame()
        card_ops.setProperty("class", "sector_card")
        ops_layout = QVBoxLayout(card_ops)
        ops_layout.setContentsMargins(14, 12, 14, 12)
        ops_layout.setSpacing(8)

        ops_h = QHBoxLayout()
        ops_box = QVBoxLayout()
        ops_box.setSpacing(2)
        lbl_op_tag = QLabel("SUPER GIT STATUS // CONTROL REMOTO")
        lbl_op_tag.setProperty("class", "sector_micro_tag")
        lbl_op_title = QLabel("🛡️ Identidad, Visibilidad & Maniobras")
        lbl_op_title.setProperty("class", "sector_title")
        ops_box.addWidget(lbl_op_tag)
        ops_box.addWidget(lbl_op_title)
        ops_h.addLayout(ops_box)
        ops_h.addStretch()

        self.btn_refresh = QPushButton("🔄")
        self.btn_refresh.setProperty("class", "cyber_btn_compact")
        self.btn_refresh.setFixedSize(28, 28)
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.setToolTip("Refrescar status, topología y GitHub")
        self.btn_refresh.clicked.connect(self._refresh_telemetry)
        ops_h.addWidget(self.btn_refresh)
        ops_layout.addLayout(ops_h)

        # Fila de Visibilidad & Identidad GitHub
        vis_row = QHBoxLayout()
        vis_row.setSpacing(8)

        self.lbl_repo_name = QLabel("Repositorio: -")
        self.lbl_repo_name.setProperty("class", "file_path_label")
        vis_row.addWidget(self.lbl_repo_name, 1)

        self.lbl_visibility_badge = QLabel("Consultando...")
        self.lbl_visibility_badge.setProperty("class", "badge_pending")
        vis_row.addWidget(self.lbl_visibility_badge)

        self.btn_toggle_visibility = QPushButton("Cambiar")
        self.btn_toggle_visibility.setProperty("class", "cyber_btn_compact")
        self.btn_toggle_visibility.setCursor(Qt.PointingHandCursor)
        self.btn_toggle_visibility.clicked.connect(self._toggle_visibility_action)
        vis_row.addWidget(self.btn_toggle_visibility)
        ops_layout.addLayout(vis_row)

        self.lbl_remote_url = QLabel("URL: -")
        self.lbl_remote_url.setProperty("class", "sector_desc")
        self.lbl_remote_url.setWordWrap(True)
        ops_layout.addWidget(self.lbl_remote_url)

        # Botonera de Red
        btn_row1 = QHBoxLayout()
        btn_row1.setSpacing(8)
        self.btn_fetch = QPushButton("🔄 Fetch & Prune")
        self.btn_fetch.setProperty("class", "cyber_btn")
        self.btn_fetch.setCursor(Qt.PointingHandCursor)
        self.btn_fetch.setToolTip("Descargar metadatos remotos y podar ramas borradas (git fetch --all --prune)")
        self.btn_fetch.clicked.connect(self._fetch_action)
        btn_row1.addWidget(self.btn_fetch)

        self.btn_pull = QPushButton("⬇️ Pull")
        self.btn_pull.setProperty("class", "cyber_btn")
        self.btn_pull.setCursor(Qt.PointingHandCursor)
        self.btn_pull.setToolTip("Integrar cambios remotos en tu rama activa (git pull)")
        self.btn_pull.clicked.connect(self._pull_action)
        btn_row1.addWidget(self.btn_pull)
        ops_layout.addLayout(btn_row1)

        btn_row2 = QHBoxLayout()
        btn_row2.setSpacing(8)
        self.btn_push = QPushButton("⬆️ Push")
        self.btn_push.setProperty("class", "cyber_btn_primary")
        self.btn_push.setCursor(Qt.PointingHandCursor)
        self.btn_push.setToolTip("Subir commits locales al repositorio remoto (git push)")
        self.btn_push.clicked.connect(self._push_action)
        btn_row2.addWidget(self.btn_push)

        self.btn_sync = QPushButton("⚡ Sync Rápido")
        self.btn_sync.setProperty("class", "cyber_btn")
        self.btn_sync.setCursor(Qt.PointingHandCursor)
        self.btn_sync.setToolTip("Secuencia automática de sincronización: Fetch ➔ Pull ➔ Push")
        self.btn_sync.clicked.connect(self._sync_quick_action)
        btn_row2.addWidget(self.btn_sync)
        ops_layout.addLayout(btn_row2)

        self.right_splitter.addWidget(card_ops)

        # -------------------------------------------------------------
        # 2.2 VENTANA INFERIOR DERECHA: RADIOGRAFÍA DE ESTADO (~58%)
        # -------------------------------------------------------------
        card_diag = QFrame()
        card_diag.setProperty("class", "sector_card")
        diag_layout = QVBoxLayout(card_diag)
        diag_layout.setContentsMargins(14, 12, 14, 12)
        diag_layout.setSpacing(8)

        self.tabs = QTabWidget()
        self.tabs.setProperty("class", "cyber_tab_widget")

        # Tab 1: 📁 Archivos (Working Tree Status)
        tab_files = QWidget()
        layout_f = QVBoxLayout(tab_files)
        layout_f.setContentsMargins(4, 6, 4, 4)
        layout_f.setSpacing(4)

        scroll_f = QScrollArea()
        scroll_f.setProperty("class", "clean_scroll")
        scroll_f.setWidgetResizable(True)
        self.files_container = QWidget()
        self.files_layout = QVBoxLayout(self.files_container)
        self.files_layout.setContentsMargins(0, 0, 0, 0)
        self.files_layout.setSpacing(4)
        scroll_f.setWidget(self.files_container)
        layout_f.addWidget(scroll_f, 1)

        # Barra inferior de Stash dentro del tab de archivos
        stash_row = QHBoxLayout()
        stash_row.setSpacing(6)
        self.lbl_stash_count = QLabel("Stashes: 0")
        self.lbl_stash_count.setProperty("class", "badge_telemetry")
        stash_row.addWidget(self.lbl_stash_count)

        self.btn_stash_save = QPushButton("📦 Guardar Stash")
        self.btn_stash_save.setProperty("class", "cyber_btn_compact")
        self.btn_stash_save.setCursor(Qt.PointingHandCursor)
        self.btn_stash_save.clicked.connect(self._save_stash_action)
        stash_row.addWidget(self.btn_stash_save)

        self.btn_stash_pop = QPushButton("📤 Restaurar Stash")
        self.btn_stash_pop.setProperty("class", "cyber_btn_compact")
        self.btn_stash_pop.setCursor(Qt.PointingHandCursor)
        self.btn_stash_pop.clicked.connect(self._pop_stash_action)
        stash_row.addWidget(self.btn_stash_pop)
        stash_row.addStretch()
        layout_f.addLayout(stash_row)

        self.tabs.addTab(tab_files, "📁 Archivos (Status)")

        # Tab 2: ⬆️ Salientes (Ahead)
        tab_out = QWidget()
        layout_out = QVBoxLayout(tab_out)
        layout_out.setContentsMargins(4, 6, 4, 4)
        scroll_out = QScrollArea()
        scroll_out.setProperty("class", "clean_scroll")
        scroll_out.setWidgetResizable(True)
        self.outgoing_container = QWidget()
        self.outgoing_layout = QVBoxLayout(self.outgoing_container)
        self.outgoing_layout.setContentsMargins(0, 0, 0, 0)
        self.outgoing_layout.setSpacing(4)
        scroll_out.setWidget(self.outgoing_container)
        layout_out.addWidget(scroll_out)
        self.tabs.addTab(tab_out, "⬆️ Salientes (Ahead)")

        # Tab 3: ⬇️ Entrantes (Behind)
        tab_in = QWidget()
        layout_in = QVBoxLayout(tab_in)
        layout_in.setContentsMargins(4, 6, 4, 4)
        scroll_in = QScrollArea()
        scroll_in.setProperty("class", "clean_scroll")
        scroll_in.setWidgetResizable(True)
        self.incoming_container = QWidget()
        self.incoming_layout = QVBoxLayout(self.incoming_container)
        self.incoming_layout.setContentsMargins(0, 0, 0, 0)
        self.incoming_layout.setSpacing(4)
        scroll_in.setWidget(self.incoming_container)
        layout_in.addWidget(scroll_in)
        self.tabs.addTab(tab_in, "⬇️ Entrantes (Behind)")

        # Tab 4: 📜 Bitácora / Consola
        tab_con = QWidget()
        layout_con = QVBoxLayout(tab_con)
        layout_con.setContentsMargins(4, 6, 4, 4)
        self.txt_console = QTextEdit()
        self.txt_console.setProperty("class", "cyber_terminal")
        self.txt_console.setReadOnly(True)
        layout_con.addWidget(self.txt_console)
        self.tabs.addTab(tab_con, "📜 Consola de Red")

        diag_layout.addWidget(self.tabs, 1)
        self.right_splitter.addWidget(card_diag)

        self.right_splitter.setSizes([230, 390])
        right_layout.addWidget(self.right_splitter, 1)

        self.main_splitter.addWidget(right_container)
        self.main_splitter.setSizes([520, 520])
        root_layout.addWidget(self.main_splitter, 1)

    # =============================================================
    # LÓGICA DE ACTUALIZACIÓN & TELEMETRÍA
    # =============================================================
    def update_project(self, project: Project):
        """Carga y actualiza toda la telemetría del proyecto, grafo y estado de red."""
        self.project = project
        if not project or not project.path or not Path(project.path).is_dir():
            return

        p_path = Path(project.path)
        if not (p_path / ".git").is_dir():
            self._log_console("Alerta: El directorio del proyecto no contiene un repositorio Git.")
            return

        self._refresh_all_telemetry(p_path)

    def _refresh_telemetry(self):
        """Disparador manual de refresco."""
        if self.project and self.project.path:
            self._refresh_all_telemetry(Path(self.project.path))
            self.log_emitted.emit("Super Git Status y topología actualizados.")

    def _refresh_all_telemetry(self, p_path: Path):
        """Calcula el estado de Git, divergencia, stashes, visibilidad en GitHub y proyecta el grafo."""
        # 1. Visibilidad en GitHub & Datos de Identidad
        vis_data = get_repo_visibility(str(p_path), force_refresh=True)

        res_url = run_command(["git", "config", "--get", "remote.origin.url"], cwd=p_path)
        remote_url = res_url.stdout.strip() if res_url.success else "Sin remoto configurado"
        self.lbl_remote_url.setText(f"URL: {remote_url}")

        repo_name = vis_data.get("repo_name", "") or (remote_url.split("/")[-1].replace(".git", "") if "/" in remote_url else p_path.name)
        self.lbl_repo_name.setText(f"Repositorio: <b>{repo_name}</b>")

        is_priv = vis_data.get("is_private")
        vis_type = vis_data.get("visibility", "")

        can_admin = vis_data.get("can_admin", True)
        if is_priv is True:
            self.lbl_visibility_badge.setText("🔒 PRIVADO")
            self.lbl_visibility_badge.setProperty("class", "badge_private")
            self.btn_toggle_visibility.setText("🌐 Cambiar a Público")
        elif vis_type == "public" or is_priv is False:
            self.lbl_visibility_badge.setText("🌐 PÚBLICO")
            self.lbl_visibility_badge.setProperty("class", "badge_public")
            self.btn_toggle_visibility.setText("🔒 Cambiar a Privado")
        else:
            self.lbl_visibility_badge.setText("⚪ SOLO LOCAL")
            self.lbl_visibility_badge.setProperty("class", "badge_pending")
            self.btn_toggle_visibility.setText("🚀 Publicar en GitHub")

        # Control de permisos administrativos (Solo el dueño/admin puede cambiar la visibilidad)
        is_github = vis_data.get("is_github", False)
        if is_github and not can_admin:
            self.btn_toggle_visibility.setEnabled(False)
            self.btn_toggle_visibility.setToolTip("Requiere permisos de Administrador o Dueño en GitHub para alterar la visibilidad.")
            self.btn_toggle_visibility.setText("🔒 Sin Permisos Admin")
        else:
            self.btn_toggle_visibility.setEnabled(True)
            self.btn_toggle_visibility.setToolTip("Modificar la visibilidad del repositorio en GitHub")

        self.lbl_visibility_badge.style().unpolish(self.lbl_visibility_badge)
        self.lbl_visibility_badge.style().polish(self.lbl_visibility_badge)

        # 2. Rama activa y posición del usuario
        res_active = run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=p_path)
        active_branch = res_active.stdout.strip() if res_active.success else "main"
        self.lbl_hud_head.setText(f"📍 HEAD: {active_branch}")

        # 3. Detectar ramas no integradas (locales y remotas no integradas en HEAD)
        res_unmerged = run_command(["git", "branch", "-a", "--no-merged", "HEAD"], cwd=p_path)
        unmerged_branches = []
        if res_unmerged.success and res_unmerged.stdout.strip():
            for line in res_unmerged.stdout.splitlines():
                l = line.strip()
                if "->" in l:
                    continue
                if l.startswith("*"):
                    l = l[1:].strip()
                if l.startswith("remotes/"):
                    l = l[8:].strip()
                if l and l not in unmerged_branches and l != active_branch:
                    unmerged_branches.append(l)

        unmerged_count = len(unmerged_branches)
        if unmerged_count > 0:
            self.lbl_hud_unmerged.setText(f"⚠️ {unmerged_count} rama(s) sin integrar")
            self.lbl_hud_unmerged.setProperty("class", "badge_pending")
        else:
            self.lbl_hud_unmerged.setText("● Todas las ramas integradas")
            self.lbl_hud_unmerged.setProperty("class", "badge_telemetry")
        self.lbl_hud_unmerged.style().unpolish(self.lbl_hud_unmerged)
        self.lbl_hud_unmerged.style().polish(self.lbl_hud_unmerged)

        # 4. Detectar Upstream y calcular retraso/desfase
        res_upstream = run_command(["git", "rev-parse", "--abbrev-ref", "@{upstream}"], cwd=p_path)
        upstream = res_upstream.stdout.strip() if res_upstream.success else ""

        ahead = 0
        behind = 0
        if upstream:
            res_counts = run_command(["git", "rev-list", "--left-right", "--count", f"HEAD...{upstream}"], cwd=p_path)
            if res_counts.success and res_counts.stdout.strip():
                parts = res_counts.stdout.strip().split()
                if len(parts) >= 2:
                    ahead = int(parts[0])
                    behind = int(parts[1])
            self.lbl_hud_delay.setText(f"⏳ Desfase: +{ahead} Ahead / -{behind} Behind")
            if behind > 0:
                self.lbl_hud_delay.setProperty("class", "badge_pending")
            elif ahead > 0:
                self.lbl_hud_delay.setProperty("class", "badge_staged")
            else:
                self.lbl_hud_delay.setProperty("class", "badge_telemetry")
        else:
            res_local_c = run_command(["git", "rev-list", "--count", "HEAD"], cwd=p_path)
            lc = res_local_c.stdout.strip() if res_local_c.success else "0"
            self.lbl_hud_delay.setText(f"⏳ +{lc} commits locales (sin upstream)")
            self.lbl_hud_delay.setProperty("class", "badge_telemetry")

        self.lbl_hud_delay.style().unpolish(self.lbl_hud_delay)
        self.lbl_hud_delay.style().polish(self.lbl_hud_delay)

        # 5. Cargar Grafo de Estado (tal cual como en el Sector 0)
        self.git_graph.load_project_graph(str(p_path))

        # 6. Poblar pestañas de Archivos, Stashes y Commits en tránsito
        self._populate_working_tree_files(p_path)
        self._populate_outgoing_commits(p_path, upstream)
        self._populate_incoming_commits(p_path, upstream)

    def _populate_working_tree_files(self, p_path: Path):
        """Puebla la lista de archivos modificados, staged y nuevos del working tree."""
        while self.files_layout.count():
            item = self.files_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        res = run_command(["git", "status", "--porcelain"], cwd=p_path)
        lines = [l for l in res.stdout.splitlines() if l.strip()] if res.success else []

        if not lines:
            lbl_clean = QLabel("✨ Árbol de trabajo completamente limpio (Clean working tree).")
            lbl_clean.setProperty("class", "sector_desc")
            self.files_layout.addWidget(lbl_clean)
        else:
            for l in lines:
                status_code = l[:2]
                fpath = l[3:].strip()
                row = WorkingTreeFileRowWidget(fpath, status_code)
                self.files_layout.addWidget(row)

        self.files_layout.addStretch()

        # Contador de stashes
        res_stash = run_command(["git", "stash", "list"], cwd=p_path)
        stash_lines = res_stash.stdout.splitlines() if res_stash.success and res_stash.stdout.strip() else []
        self.lbl_stash_count.setText(f"Stashes: {len(stash_lines)}")

    def _populate_outgoing_commits(self, p_path: Path, upstream: str):
        """Puebla la lista de commits salientes hacia el remoto."""
        while self.outgoing_layout.count():
            item = self.outgoing_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if upstream:
            cmd = ["git", "log", f"{upstream}..HEAD", "--format=%h|%s|%an|%cr", "-n", "30"]
        else:
            cmd = ["git", "log", "-n", "15", "--format=%h|%s|%an|%cr"]

        res = run_command(cmd, cwd=p_path)
        commits = [c.strip() for c in res.stdout.splitlines() if c.strip()] if res.success else []

        if not commits:
            lbl_empty = QLabel("No hay commits pendientes por subir al remoto (Al día).")
            lbl_empty.setProperty("class", "sector_desc")
            self.outgoing_layout.addWidget(lbl_empty)
        else:
            for line in commits:
                parts = line.split("|", 3)
                chash = parts[0] if len(parts) > 0 else "-"
                subj = parts[1] if len(parts) > 1 else ""
                author = parts[2] if len(parts) > 2 else ""
                date = parts[3] if len(parts) > 3 else ""
                meta = f"{author} ({date})" if author else ""
                row = CommitTrafficRowWidget(chash, subj, meta)
                self.outgoing_layout.addWidget(row)

        self.outgoing_layout.addStretch()

    def _populate_incoming_commits(self, p_path: Path, upstream: str):
        """Puebla la lista de commits entrantes desde el remoto."""
        while self.incoming_layout.count():
            item = self.incoming_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not upstream:
            lbl_empty = QLabel("Sin upstream remoto configurado para comparar commits entrantes.")
            lbl_empty.setProperty("class", "sector_desc")
            self.incoming_layout.addWidget(lbl_empty)
            self.incoming_layout.addStretch()
            return

        cmd = ["git", "log", f"HEAD..{upstream}", "--format=%h|%s|%an|%cr", "-n", "30"]
        res = run_command(cmd, cwd=p_path)
        commits = [c.strip() for c in res.stdout.splitlines() if c.strip()] if res.success else []

        if not commits:
            lbl_empty = QLabel("No hay commits pendientes por descargar desde el remoto (Al día).")
            lbl_empty.setProperty("class", "sector_desc")
            self.incoming_layout.addWidget(lbl_empty)
        else:
            for line in commits:
                parts = line.split("|", 3)
                chash = parts[0] if len(parts) > 0 else "-"
                subj = parts[1] if len(parts) > 1 else ""
                author = parts[2] if len(parts) > 2 else ""
                date = parts[3] if len(parts) > 3 else ""
                meta = f"{author} ({date})" if author else ""
                row = CommitTrafficRowWidget(chash, subj, meta)
                self.incoming_layout.addWidget(row)

        self.incoming_layout.addStretch()

    def _log_console(self, text: str):
        """Registra un mensaje con marca temporal en la consola táctica de red."""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.txt_console.append(f"[{timestamp}] {text}")

    # =============================================================
    # ACCIONES: CONTROLES DEL GRAFO (ORIENTACIÓN Y ZOOM)
    # =============================================================
    def _toggle_orientation(self):
        new_orient = self.git_graph.toggle_orientation()
        self.btn_orient.setText("↕ Vertical" if new_orient == "vertical" else "↔ Horizontal")

    def _zoom_in(self):
        self.git_graph.zoom_in()

    def _zoom_out(self):
        self.git_graph.zoom_out()

    def _zoom_reset(self):
        self.git_graph.zoom_reset()

    # =============================================================
    # ACCIONES: CAMBIO DE VISIBILIDAD (PÚBLICO / PRIVADO / PUBLICAR)
    # =============================================================
    def _toggle_visibility_action(self):
        """Cambia la visibilidad en GitHub con validación y confirmación preventiva."""
        if not self.project or not self.project.path:
            return

        p_path = str(self.project.path)
        vis_data = get_repo_visibility(p_path)

        if not vis_data.get("has_remote") or not vis_data.get("is_github"):
            self._show_publish_dialog(p_path)
            return

        if not vis_data.get("can_admin", True):
            QMessageBox.warning(
                self,
                "Acceso Denegado",
                "No dispones de privilegios de Administrador o Propietario sobre este repositorio en GitHub.\n\n"
                "Solo los dueños u administradores de la organización pueden alterar la visibilidad pública/privada."
            )
            return

        is_priv = vis_data.get("is_private", False)
        target = "public" if is_priv else "private"

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Cambiar Visibilidad a {target.upper()}")
        dialog.setModal(True)
        dialog.setFixedWidth(460)
        dialog.setProperty("class", "cyber_dialog")

        d_layout = QVBoxLayout(dialog)
        d_layout.setContentsMargins(20, 18, 20, 18)
        d_layout.setSpacing(12)

        lbl_tag = QLabel("SEGURIDAD // VISIBILIDAD GITHUB")
        lbl_tag.setProperty("class", "sector_micro_tag")
        d_layout.addWidget(lbl_tag)

        if target == "public":
            msg = (
                "⚠️ <b>ADVERTENCIA DE SEGURIDAD CRÍTICA:</b><br><br>"
                "Estás a punto de hacer este repositorio <b>PÚBLICO</b> en GitHub.<br>"
                "Cualquier persona en el mundo podrá ver el código, descargar el proyecto, "
                "inspeccionar el historial de commits y ramas.<br><br>"
                "Asegúrate de no tener API keys, tokens o archivos sensibles expuestos."
            )
        else:
            msg = (
                "🔒 <b>CONFIRMACIÓN DE PRIVACIDAD:</b><br><br>"
                "El repositorio pasará a ser <b>PRIVADO</b> en GitHub.<br>"
                "Solo tú y los colaboradores que invites expresamente tendrán acceso al código."
            )

        lbl_msg = QLabel(msg)
        lbl_msg.setProperty("class", "sector_desc")
        lbl_msg.setWordWrap(True)
        d_layout.addWidget(lbl_msg)

        chk_confirm = None
        if target == "public":
            chk_confirm = QCheckBox("Entiendo las consecuencias de hacer público este repositorio")
            chk_confirm.setProperty("class", "cyber_checkbox")
            d_layout.addWidget(chk_confirm)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setProperty("class", "cyber_btn")
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.clicked.connect(dialog.reject)
        btn_row.addWidget(btn_cancel)

        btn_confirm = QPushButton("🌐 Confirmar Cambio a Público" if target == "public" else "🔒 Confirmar Cambio a Privado")
        btn_confirm.setProperty("class", "cyber_btn_danger" if target == "public" else "cyber_btn_primary")
        btn_confirm.setCursor(Qt.PointingHandCursor)
        if target == "public" and chk_confirm:
            btn_confirm.setEnabled(False)
            chk_confirm.toggled.connect(btn_confirm.setEnabled)

        btn_confirm.clicked.connect(dialog.accept)
        btn_row.addWidget(btn_confirm)
        d_layout.addLayout(btn_row)

        if dialog.exec() == QDialog.Accepted:
            self._log_console(f"Modificando visibilidad a {target.upper()} con GitHub CLI...")
            ok, resp_msg = change_repo_visibility(p_path, target)
            self._log_console(f"Resultado: {resp_msg}")
            self.log_emitted.emit(resp_msg)
            self.update_project(self.project)
            self.action_requested.emit("git_visibility_changed", {"target": target, "success": ok})

    def _show_publish_dialog(self, p_path: str):
        """Muestra diálogo para publicar repositorio local en GitHub."""
        default_name = Path(p_path).name
        dialog = QDialog(self)
        dialog.setWindowTitle("Publicar Repositorio en GitHub")
        dialog.setModal(True)
        dialog.setFixedWidth(460)
        dialog.setProperty("class", "cyber_dialog")

        d_layout = QVBoxLayout(dialog)
        d_layout.setContentsMargins(20, 18, 20, 18)
        d_layout.setSpacing(12)

        lbl_tag = QLabel("DESPLIEGUE REMOTO // GITHUB CLI")
        lbl_tag.setProperty("class", "sector_micro_tag")
        d_layout.addWidget(lbl_tag)

        lbl_msg = QLabel("Crea un nuevo repositorio en tu cuenta de GitHub y vincula este proyecto local como remoto:")
        lbl_msg.setProperty("class", "sector_desc")
        lbl_msg.setWordWrap(True)
        d_layout.addWidget(lbl_msg)

        txt_name = QLineEdit(default_name)
        txt_name.setProperty("class", "cyber_input")
        txt_name.setPlaceholderText("Nombre del repositorio (ej. MiProyecto)...")
        d_layout.addWidget(txt_name)

        vis_row = QHBoxLayout()
        rad_private = QRadioButton("🔒 Privado (Recomendado)")
        rad_private.setChecked(True)
        rad_public = QRadioButton("🌐 Público")
        vis_row.addWidget(rad_private)
        vis_row.addWidget(rad_public)
        d_layout.addLayout(vis_row)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setProperty("class", "cyber_btn")
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.clicked.connect(dialog.reject)
        btn_row.addWidget(btn_cancel)

        btn_publish = QPushButton("🚀 Crear & Publicar")
        btn_publish.setProperty("class", "cyber_btn_primary")
        btn_publish.setCursor(Qt.PointingHandCursor)
        btn_publish.clicked.connect(dialog.accept)
        btn_row.addWidget(btn_publish)
        d_layout.addLayout(btn_row)

        if dialog.exec() == QDialog.Accepted:
            repo_name = txt_name.text().strip() or default_name
            vis_mode = "private" if rad_private.isChecked() else "public"
            self._log_console(f"Publicando repositorio '{repo_name}' en GitHub ({vis_mode})...")
            ok, resp_msg = publish_repo_to_github(p_path, repo_name=repo_name, visibility=vis_mode)
            self._log_console(f"Resultado: {resp_msg}")
            self.log_emitted.emit(resp_msg)
            self.update_project(self.project)
            self.action_requested.emit("git_repo_published", {"repo_name": repo_name, "visibility": vis_mode})

    # =============================================================
    # ACCIONES: SINCRONIZACIÓN DE RED (FETCH, PULL, PUSH, SYNC)
    # =============================================================
    def _fetch_action(self):
        """Descarga referencias y poda ramas remotas borradas (git fetch --all --prune)."""
        if not self.project or not self.project.path:
            return
        self._log_console("Ejecutando git fetch --all --prune...")
        res = run_command(["git", "fetch", "--all", "--prune"], cwd=self.project.path)
        self._log_console(res.output.strip() or "Metadatos remotos actualizados.")
        self.log_emitted.emit("Metadatos remotos actualizados (Fetch & Prune).")
        self.update_project(self.project)

    def _pull_action(self):
        """Descarga e integra cambios del upstream en la rama activa (git pull)."""
        if not self.project or not self.project.path:
            return
        self._log_console("Ejecutando git pull...")
        res = run_command(["git", "pull"], cwd=self.project.path)
        self._log_console(res.output.strip())
        if res.success:
            self.log_emitted.emit("Pull completado con éxito.")
        else:
            self.log_emitted.emit(f"Alerta en pull: {res.output}")
        self.update_project(self.project)

    def _push_action(self):
        """Empuja los commits locales al repositorio remoto (git push)."""
        if not self.project or not self.project.path:
            return

        res_active = run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=self.project.path)
        active_branch = res_active.stdout.strip() if res_active.success else "main"

        res_up = run_command(["git", "rev-parse", "--abbrev-ref", "@{upstream}"], cwd=self.project.path)
        if res_up.success and res_up.stdout.strip():
            cmd = ["git", "push"]
        else:
            cmd = ["git", "push", "-u", "origin", active_branch]

        self._log_console(f"Ejecutando {' '.join(cmd)}...")
        res = run_command(cmd, cwd=self.project.path)
        self._log_console(res.output.strip() or "Commits locales subidos con éxito.")
        if res.success:
            self.log_emitted.emit("Push completado con éxito.")
        else:
            self.log_emitted.emit(f"Alerta en push: {res.output}")
        self.update_project(self.project)

    def _sync_quick_action(self):
        """Secuencia segura de sincronización completa: Fetch ➔ Pull ➔ Push."""
        if not self.project or not self.project.path:
            return

        self._log_console("Iniciando secuencia segura de sincronización rápida...")

        # 1. Fetch
        self._log_console("[1/3] Ejecutando fetch --all --prune...")
        res_fetch = run_command(["git", "fetch", "--all", "--prune"], cwd=self.project.path)
        self._log_console(res_fetch.output.strip() or "Fetch completado.")

        # 2. Pull
        self._log_console("[2/3] Ejecutando git pull...")
        res_pull = run_command(["git", "pull"], cwd=self.project.path)
        self._log_console(res_pull.output.strip())
        if not res_pull.success:
            self.log_emitted.emit("Alerta: El Pull reportó advertencias o conflictos. Se detuvo la sincronización antes del Push.")
            self.update_project(self.project)
            return

        # 3. Push
        self._log_console("[3/3] Ejecutando git push...")
        self._push_action()

    # =============================================================
    # ACCIONES: CAJÓN DE STASH
    # =============================================================
    def _save_stash_action(self):
        """Guarda los cambios no comprometidos en un stash temporal."""
        if not self.project or not self.project.path:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Guardar Mesa de Trabajo en Stash")
        dialog.setModal(True)
        dialog.setFixedWidth(420)
        dialog.setProperty("class", "cyber_dialog")

        d_layout = QVBoxLayout(dialog)
        d_layout.setContentsMargins(20, 18, 20, 18)
        d_layout.setSpacing(10)

        lbl_tag = QLabel("GIT STASH // CONGELAR CAMBIOS")
        lbl_tag.setProperty("class", "sector_micro_tag")
        d_layout.addWidget(lbl_tag)

        lbl_hint = QLabel("Ingresa una descripción para identificar este stash:")
        lbl_hint.setProperty("class", "sector_desc")
        d_layout.addWidget(lbl_hint)

        txt_msg = QLineEdit()
        txt_msg.setProperty("class", "cyber_input")
        txt_msg.setPlaceholderText("Ej. Cambios provisionales antes de sincronizar...")
        d_layout.addWidget(txt_msg)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setProperty("class", "cyber_btn")
        btn_cancel.clicked.connect(dialog.reject)
        btn_row.addWidget(btn_cancel)

        btn_confirm = QPushButton("📦 Guardar en Stash")
        btn_confirm.setProperty("class", "cyber_btn_primary")
        btn_confirm.clicked.connect(dialog.accept)
        btn_row.addWidget(btn_confirm)
        d_layout.addLayout(btn_row)

        if dialog.exec() == QDialog.Accepted:
            msg = txt_msg.text().strip() or "Stash temporal Abraxas"
            res = run_command(["git", "stash", "push", "-m", msg], cwd=self.project.path)
            self._log_console(f"git stash push: {res.output.strip()}")
            self.log_emitted.emit(f"📦 Stash guardado: {msg}")
            self.update_project(self.project)

    def _pop_stash_action(self):
        """Restaura el último stash en la mesa de trabajo."""
        if not self.project or not self.project.path:
            return
        res = run_command(["git", "stash", "pop"], cwd=self.project.path)
        self._log_console(f"git stash pop: {res.output.strip()}")
        if res.success:
            self.log_emitted.emit("📤 Stash restaurado en la mesa de trabajo.")
        else:
            self.log_emitted.emit(f"Alerta al restaurar stash: {res.output}")
        self.update_project(self.project)


# =============================================================
# SECTOR 01: ORQUESTADOR PRINCIPAL (3 NODOS MAESTROS)
# =============================================================

class Sector1GitView(QWidget):
    """
    Sector 01: Protocolo GitOps y Control de Versiones.
    Orquestador de los 3 Nodos Maestros con navegación por píldora:
    - 1.1 Ciclo de trabajo (git add, git commit, git push)
    - 1.2 Gestor de ramas (visibilidad, creación, eliminación, fusión)
    - 1.3 Estado y sincronización (status, fetch, pull, visibilidad)
    """

    action_requested = Signal(str, dict)
    log_emitted = Signal(str)

    def __init__(self, project: Project = None, parent=None):
        super().__init__(parent)
        self.project = project
        self.init_ui()

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(8)

        # -------------------------------------------------------------
        # BARRA DE NAVEGACIÓN DE SUB-SECTORES (SUB-PILL TÁCTICA)
        # -------------------------------------------------------------
        sub_sectors = [
            ("⚡  1.1 CICLO DE TRABAJO", "Flujo operativo: git add, archivos del workspace, git push y redactor IA"),
            ("🌿  1.2 GESTOR DE RAMAS", "Control de bifurcaciones, visibilidad, creación, eliminación y fusión"),
            ("🔄  1.3 ESTADO & SINCRONIZACIÓN", "Status del árbol de trabajo, fetch, pull y visibilidad del repositorio")
        ]
        self.sub_pill = SectorSwitcherPill(sectors=sub_sectors)
        self.sub_pill.sector_changed.connect(self.switch_sub_sector)
        root_layout.addWidget(self.sub_pill)

        # -------------------------------------------------------------
        # CONTENEDOR DINÁMICO DE SUB-SECTORES (QStackedWidget)
        # -------------------------------------------------------------
        self.sub_stack = QStackedWidget()

        # 1.1 Ciclo de Trabajo
        self.workflow_view = Sector11WorkflowView(self.project)
        self.workflow_view.log_emitted.connect(self.log_emitted.emit)
        self.workflow_view.action_requested.connect(self.action_requested.emit)
        self.sub_stack.addWidget(self.workflow_view)

        # 1.2 Gestor de Ramas
        self.branches_view = Sector12BranchesView(self.project)
        self.branches_view.log_emitted.connect(self.log_emitted.emit)
        self.branches_view.action_requested.connect(self.action_requested.emit)
        self.sub_stack.addWidget(self.branches_view)

        # 1.3 Estado y Sincronización
        self.sync_view = Sector13SyncView(self.project)
        self.sync_view.log_emitted.connect(self.log_emitted.emit)
        self.sync_view.action_requested.connect(self.action_requested.emit)
        self.sub_stack.addWidget(self.sync_view)

        root_layout.addWidget(self.sub_stack, 1)

        # Por defecto abre el Sub-sector 1.1
        self.sub_stack.setCurrentIndex(0)
        self.sub_pill.select_sector(0)

    def switch_sub_sector(self, index: int):
        """Cambia fluidamente entre los 3 sub-sectores tácticos."""
        self.sub_stack.setCurrentIndex(index)
        names = ["1.1 Ciclo de Trabajo", "1.2 Gestor de Ramas", "1.3 Estado & Sincronización"]
        if 0 <= index < len(names):
            self.log_emitted.emit(f"Sub-sector activo: <b>{names[index]}</b>")
        if index == 0 and hasattr(self, "workflow_view"):
            self.workflow_view.update_project(self.project)
        elif index == 1 and hasattr(self, "branches_view"):
            self.branches_view.update_project(self.project)
        elif index == 2 and hasattr(self, "sync_view"):
            self.sync_view.update_project(self.project)

    def update_project(self, project: Project):
        """Propaga la actualización del proyecto a las sub-vistas."""
        self.project = project
        if hasattr(self, "workflow_view"):
            self.workflow_view.update_project(project)
        if hasattr(self, "branches_view"):
            self.branches_view.update_project(project)
        if hasattr(self, "sync_view"):
            self.sync_view.update_project(project)

