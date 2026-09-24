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
    QSplitter, QButtonGroup, QCheckBox, QStackedWidget
)
from PySide6.QtCore import Qt, Signal, QTimer, QThread
from PySide6.QtGui import QCursor

from abraxas.core.process import run_command
from abraxas.core.semver import bump_semver
from abraxas.lumen.models.project import Project
from abraxas.ui.controls.switcher_pill import SectorSwitcherPill


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
# SECTOR 01: ORQUESTADOR PRINCIPAL (3 NODOS MAESTROS)
# =====================================================================

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

        # 1.2 Gestor de Ramas (En espera de configuración en el siguiente paso)
        self.branches_placeholder = self._create_placeholder_view(
            "🌿 SUB-SECTOR 1.2 // GESTOR DE RAMAS",
            "Visibilidad de ramas, creación, eliminación y fusión asistida (Git Merge)."
        )
        self.sub_stack.addWidget(self.branches_placeholder)

        # 1.3 Estado y Sincronización (En espera de configuración)
        self.sync_placeholder = self._create_placeholder_view(
            "🔄 SUB-SECTOR 1.3 // ESTADO & SINCRONIZACIÓN",
            "Inspección de git status, sincronización con fetch, pull y cambio de visibilidad."
        )
        self.sub_stack.addWidget(self.sync_placeholder)

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

    def update_project(self, project: Project):
        """Propaga la actualización del proyecto a las sub-vistas."""
        self.project = project
        if hasattr(self, "workflow_view"):
            self.workflow_view.update_project(project)

    def _create_placeholder_view(self, tag_title: str, description: str) -> QWidget:
        """Crea una vista reservada limpia para los sub-sectores 1.2 y 1.3."""
        card = QFrame()
        card.setProperty("class", "sector_card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignCenter)

        lbl_tag = QLabel(tag_title)
        lbl_tag.setProperty("class", "sector_micro_tag")
        lbl_tag.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_tag)

        lbl_desc = QLabel(description)
        lbl_desc.setProperty("class", "sector_desc")
        lbl_desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_desc)

        lbl_status = QLabel("● EN ESPERA DE REVISIÓN")
        lbl_status.setProperty("class", "badge_telemetry")
        lbl_status.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_status)

        return card
