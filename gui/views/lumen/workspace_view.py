#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS | LUMEN - PROJECT WORKSPACE VIEW (DASHBOARD DEL PROYECTO)
# =====================================================================

import os
import subprocess
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QScrollArea, QGridLayout,
    QTextEdit, QApplication, QStackedWidget, QSizePolicy,
    QProgressBar, QLineEdit, QComboBox, QStyledItemDelegate,
    QCheckBox, QMenu, QDialog, QRadioButton, QButtonGroup, QMessageBox,
    QInputDialog, QSplitter
)
from PySide6.QtCore import Qt, Signal, QTimer, QThread, QPoint

from core import get_version
from core.lumen_sync import get_full_project_sync
from core.github import get_repo_visibility, change_repo_visibility, publish_repo_to_github
from core.ai import get_configured_model, audit_git_diff
from core.git_workflow import (
    get_project_semver, bump_semver, get_next_commit_seq,
    generate_ia_commit_proposal, execute_commit_and_tag,
    get_git_branches_matrix, execute_git_checkout,
    execute_git_create_branch, execute_git_delete_branch,
    execute_git_deploy_branch,
    get_git_merge_status, get_mergeable_branches,
    get_merge_diff_and_commits, generate_ia_merge_proposal,
    execute_git_merge, execute_git_merge_into, execute_git_merge_abort,
    execute_git_resolve_conflicts, execute_git_complete_merge,
    get_git_sync_deep_status, execute_git_fetch, execute_git_pull,
    execute_git_stage_path, execute_git_unstage_path, execute_git_discard_path,
    execute_git_stash_pop, execute_git_stash_save, execute_git_init
)
from core.environments import (
    detect_installed_editors, get_preferred_editor, set_preferred_editor,
    launch_project_in_editor, inspect_python_venv, create_python_venv,
    install_project_dependencies, install_custom_packages,
    freeze_dependencies_to_file, list_installed_packages, delete_python_venv,
    inspect_docker_status, list_docker_containers, execute_docker_container_action,
    get_docker_container_logs, execute_docker_prune, inspect_network_ports, kill_process_by_pid,
    deep_scan_docker_files, parse_compose_file_lightweight, detect_compose_tool, execute_compose_action
)
from gui.views.lumen.git_graph_canvas import LumenHorizontalGitGraphView



class GitPushThread(QThread):
    """Hilo para ejecutar git push hacia el remoto sin congelar la GUI."""
    finished_push = Signal(bool, str, str)

    def __init__(self, project_path: str, follow_tags: bool = False):
        super().__init__()
        self.project_path = project_path
        self.follow_tags = follow_tags

    def run(self):
        try:
            # 1. Detectar rama actual
            b_proc = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.project_path, capture_output=True, text=True, timeout=6
            )
            branch = b_proc.stdout.strip()
            if not branch:
                r_proc = subprocess.run(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"], 
                    cwd=self.project_path, capture_output=True, text=True, timeout=4
                )
                branch = r_proc.stdout.strip() or "main"

            # 2. Detectar remotos configurados
            rem_proc = subprocess.run(
                ["git", "remote"],
                cwd=self.project_path, capture_output=True, text=True, timeout=5
            )
            remotes = rem_proc.stdout.strip().splitlines() if rem_proc.returncode == 0 else []
            if not remotes:
                self.finished_push.emit(False, branch, "No hay ningún repositorio remoto configurado en este proyecto ('git remote' vacío). Agrega uno con: git remote add origin <url>")
                return

            remote_target = "origin" if "origin" in remotes else remotes[0]

            # 3. Comprobar si hay commits locales pendientes de envío
            upstream_ref = f"{remote_target}/{branch}"
            pending_commits = 0
            rev_proc = subprocess.run(
                ["git", "rev-list", "--count", f"{upstream_ref}..HEAD"],
                cwd=self.project_path, capture_output=True, text=True, timeout=5
            )
            if rev_proc.returncode == 0 and rev_proc.stdout.strip().isdigit():
                pending_commits = int(rev_proc.stdout.strip())

            # 4. Construir comando git push con -u para tracking
            cmd = ["git", "push"]
            if self.follow_tags:
                cmd.append("--follow-tags")
            cmd.extend(["-u", remote_target, branch])

            p_proc = subprocess.run(
                cmd,
                cwd=self.project_path, capture_output=True, text=True, timeout=60
            )

            combined = (p_proc.stdout.strip() + "\n" + p_proc.stderr.strip()).strip()

            if p_proc.returncode == 0:
                if "Everything up-to-date" in combined or "Todo está actualizado" in combined:
                    msg = "Todo está actualizado. No había nuevos commits pendientes para enviar."
                elif pending_commits > 0:
                    msg = f"{pending_commits} commit(s) enviados exitosamente a {remote_target}/{branch}."
                else:
                    msg = combined or "Commits y etiquetas sincronizados exitosamente."
                self.finished_push.emit(True, branch, msg)
            else:
                if self.follow_tags:
                    # Intento secuencial de rescate
                    p1 = subprocess.run(["git", "push", "-u", remote_target, branch], cwd=self.project_path, capture_output=True, text=True, timeout=60)
                    p2 = subprocess.run(["git", "push", "--tags", remote_target], cwd=self.project_path, capture_output=True, text=True, timeout=60)
                    if p1.returncode == 0:
                        c2 = (p1.stdout.strip() + "\n" + p2.stdout.strip() + "\n" + p1.stderr.strip()).strip()
                        self.finished_push.emit(True, branch, c2 or "Sincronizado con éxito.")
                        return
                err_msg = combined or "Error desconocido durante git push."
                self.finished_push.emit(False, branch, err_msg)
        except Exception as e:
            self.finished_push.emit(False, "unknown", str(e))


class GitFetchThread(QThread):
    """Hilo para ejecutar git fetch hacia el remoto sin congelar la GUI."""
    finished_fetch = Signal(bool, str, dict)

    def __init__(self, project_path: str, remote: str = "", prune: bool = True):
        super().__init__()
        self.project_path = project_path
        self.remote = remote
        self.prune = prune

    def run(self):
        try:
            ok, msg, status = execute_git_fetch(self.project_path, self.remote, self.prune)
            self.finished_fetch.emit(ok, msg, status)
        except Exception as e:
            self.finished_fetch.emit(False, str(e), {})


class GitPullThread(QThread):
    """Hilo para ejecutar git pull seguro sin congelar la GUI."""
    finished_pull = Signal(bool, str)

    def __init__(self, project_path: str, strategy: str = "rebase", autostash: bool = True):
        super().__init__()
        self.project_path = project_path
        self.strategy = strategy
        self.autostash = autostash

    def run(self):
        try:
            ok, msg = execute_git_pull(self.project_path, self.strategy, self.autostash)
            self.finished_pull.emit(ok, msg)
        except Exception as e:
            self.finished_pull.emit(False, str(e))


class IACommitThread(QThread):
    """Hilo para generar la propuesta de commit con IA sin congelar la GUI."""
    finished_commit = Signal(bool, str, dict)

    def __init__(self, project_path: str, model_type: str, impact_type: str, target_ver: str):
        super().__init__()
        self.project_path = project_path
        self.model_type = model_type
        self.impact_type = impact_type
        self.target_ver = target_ver

    def run(self):
        try:
            res = generate_ia_commit_proposal(
                self.project_path,
                self.model_type,
                self.impact_type,
                self.target_ver
            )
            self.finished_commit.emit(True, "", res)
        except Exception as e:
            self.finished_commit.emit(False, str(e), {})


class IAAuditThread(QThread):
    """Hilo para analizar diff de git y consultar a Ollama sin congelar la GUI."""
    finished_audit = Signal(bool, str, dict)

    def __init__(self, project_path: str, model_type: str = "light"):
        super().__init__()
        self.project_path = project_path
        self.model_type = model_type

    def run(self):
        try:
            # 1. Obtener diff (staging primero, luego árbol de trabajo, luego último commit)
            d_cached = subprocess.run(
                ["git", "diff", "--cached"],
                cwd=self.project_path, capture_output=True, text=True, timeout=10
            )
            diff_text = d_cached.stdout.strip()

            if not diff_text:
                d_work = subprocess.run(
                    ["git", "diff", "HEAD"],
                    cwd=self.project_path, capture_output=True, text=True, timeout=10
                )
                diff_text = d_work.stdout.strip()

            if not diff_text:
                d_last = subprocess.run(
                    ["git", "diff", "HEAD~1", "HEAD"],
                    cwd=self.project_path, capture_output=True, text=True, timeout=10
                )
                diff_text = d_last.stdout.strip()

            if not diff_text:
                self.finished_audit.emit(
                    False, 
                    "No se detectaron diferencias (diff vacío) en staging, árbol de trabajo ni en el último commit.",
                    {}
                )
                return

            res = audit_git_diff(diff_text, model_type=self.model_type)
            self.finished_audit.emit(True, "", res)
        except Exception as e:
            self.finished_audit.emit(False, str(e), {})


class IAMergeThread(QThread):
    """Hilo para generar la propuesta de commit de merge con IA sin congelar la GUI."""
    finished_merge = Signal(bool, str, dict)

    def __init__(self, project_path: str, source_branch: str, target_branch: str = "", model_type: str = "light"):
        super().__init__()
        self.project_path = project_path
        self.source_branch = source_branch
        self.target_branch = target_branch
        self.model_type = model_type

    def run(self):
        try:
            res = generate_ia_merge_proposal(
                self.project_path,
                self.source_branch,
                self.model_type,
                target_branch=self.target_branch
            )
            self.finished_merge.emit(True, "", res)
        except Exception as e:
            self.finished_merge.emit(False, str(e), {})


class PythonVenvWorkerThread(QThread):
    """Hilo no bloqueante para ejecutar operaciones pesadas de entorno virtual Python."""
    finished_task = Signal(bool, str, str)

    def __init__(self, task_type: str, project_path: str, venv_path: str = "", extra_args=None):
        super().__init__()
        self.task_type = task_type
        self.project_path = project_path
        self.venv_path = venv_path
        self.extra_args = extra_args

    def run(self):
        try:
            if self.task_type == "create_venv":
                use_uv = bool(self.extra_args)
                ok, msg = create_python_venv(self.project_path, use_uv=use_uv)
                self.finished_task.emit(ok, "CREAR-VENV", msg)
            elif self.task_type == "install_deps":
                ok, msg = install_project_dependencies(self.project_path, self.venv_path)
                self.finished_task.emit(ok, "DEPS", msg)
            elif self.task_type == "install_custom":
                pkgs = self.extra_args or []
                ok, msg = install_custom_packages(self.project_path, self.venv_path, pkgs)
                self.finished_task.emit(ok, "INSTALL-PKG", msg)
            elif self.task_type == "freeze":
                ok, msg = freeze_dependencies_to_file(self.project_path, self.venv_path)
                self.finished_task.emit(ok, "FREEZE", msg)
            elif self.task_type == "delete_venv":
                ok, msg = delete_python_venv(self.venv_path)
                self.finished_task.emit(ok, "DELETE-VENV", msg)
        except Exception as e:
            self.finished_task.emit(False, self.task_type.upper(), f"Excepción en hilo de venv: {str(e)}")


class DockerWorkerThread(QThread):
    """Hilo no bloqueante para ejecutar operaciones de Docker (contenedor, compose, prune)."""
    finished_task = Signal(bool, str, str)

    def __init__(self, task_type: str, target: str = "", compose_path: str = "", service: str = ""):
        super().__init__()
        self.task_type = task_type
        self.target = target
        self.compose_path = compose_path
        self.service = service

    def run(self):
        try:
            if self.task_type == "prune":
                ok, msg = execute_docker_prune()
                self.finished_task.emit(ok, "DOCKER-PRUNE", msg)
            elif self.task_type in ["start", "stop", "restart", "rm"]:
                ok, msg = execute_docker_container_action(self.task_type, self.target)
                self.finished_task.emit(ok, f"DOCKER-{self.task_type.upper()}", msg)
            elif self.task_type.startswith("compose-"):
                action = self.task_type.replace("compose-", "")
                ok, msg = execute_compose_action(self.compose_path, action, self.service or None)
                label = f"COMPOSE-{action.upper()}"
                self.finished_task.emit(ok, label, msg)
        except Exception as e:
            self.finished_task.emit(False, self.task_type.upper(), f"Excepción en hilo de Docker: {str(e)}")


class LumenRepoVisibilityDialog(QDialog):
    """Diálogo modal ciber-ilustre para consultar y alternar la visibilidad (Público/Privado) o publicar en GitHub."""

    def __init__(self, project_path: str, project_name: str, parent=None):
        super().__init__(parent)
        self.project_path = project_path
        self.project_name = project_name
        self.setWindowTitle("Gestión de Visibilidad GitHub • Abraxas")
        self.setFixedSize(500, 420)
        self.setStyleSheet("""
            QDialog {
                background-color: #0f1117;
                color: #e5e7eb;
                border: 1px solid rgba(99, 102, 241, 0.45);
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header
        h_layout = QHBoxLayout()
        lbl_icon = QLabel("🌐")
        lbl_icon.setStyleSheet("font-size: 20px;")
        h_layout.addWidget(lbl_icon)

        lbl_head = QLabel("Gestión de Visibilidad en GitHub")
        lbl_head.setStyleSheet("font-size: 15px; font-weight: 800; color: #a5b4fc;")
        h_layout.addWidget(lbl_head)
        h_layout.addStretch()

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(26, 26)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #9ca3af;
                border: none;
                font-size: 14px;
                font-weight: 700;
            }
            QPushButton:hover { color: #f87171; }
        """)
        btn_close.clicked.connect(self.reject)
        h_layout.addWidget(btn_close)
        layout.addLayout(h_layout)

        # Separador
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: rgba(255, 255, 255, 0.08); max-height: 1px;")
        layout.addWidget(sep)

        # Consultar estado actual
        self.vis_data = get_repo_visibility(self.project_path)
        self.is_github = self.vis_data.get("is_github", False)
        self.has_remote = self.vis_data.get("has_remote", False)
        self.current_is_private = self.vis_data.get("is_private", True)

        # Información del Repositorio
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            background-color: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.07);
            border-radius: 8px;
            padding: 10px;
        """)
        info_lay = QVBoxLayout(info_frame)
        info_lay.setContentsMargins(10, 8, 10, 8)
        info_lay.setSpacing(6)

        repo_name = self.vis_data.get("repo_name") or self.project_name
        lbl_rname = QLabel(f"<b>Repositorio:</b> <span style='color:#38bdf8;'>{repo_name}</span>")
        lbl_rname.setStyleSheet("font-size: 13px; color: #d1d5db;")
        info_lay.addWidget(lbl_rname)

        if self.has_remote and self.is_github:
            status_color = "#f87171" if self.current_is_private else "#34d399"
            status_text = "🔒 PRIVADO" if self.current_is_private else "🌐 PÚBLICO"
            lbl_cur = QLabel(f"<b>Estado Actual en GitHub:</b> <span style='color:{status_color}; font-weight:800;'>{status_text}</span>")
            lbl_cur.setStyleSheet("font-size: 13px; color: #d1d5db;")
            info_lay.addWidget(lbl_cur)
        else:
            lbl_cur = QLabel("<b>Estado:</b> <span style='color:#fbbf24; font-weight:700;'>Solo Local (Sin vincular a GitHub)</span>")
            lbl_cur.setStyleSheet("font-size: 13px; color: #d1d5db;")
            info_lay.addWidget(lbl_cur)

        layout.addWidget(info_frame)

        # Opciones de configuración
        lbl_opt_title = QLabel("Selecciona la visibilidad deseada:")
        lbl_opt_title.setStyleSheet("font-size: 12.5px; font-weight: 700; color: #e5e7eb;")
        layout.addWidget(lbl_opt_title)

        self.btn_group = QButtonGroup(self)

        self.rb_private = QRadioButton("🔒 Repositorio Privado (Solo tú y colaboradores)")
        self.rb_private.setStyleSheet("font-size: 12.5px; color: #f3f4f6; padding: 4px;")
        self.rb_private.setCursor(Qt.PointingHandCursor)

        self.rb_public = QRadioButton("🌐 Repositorio Público (Acceso abierto en GitHub)")
        self.rb_public.setStyleSheet("font-size: 12.5px; color: #f3f4f6; padding: 4px;")
        self.rb_public.setCursor(Qt.PointingHandCursor)

        self.btn_group.addButton(self.rb_private)
        self.btn_group.addButton(self.rb_public)

        if self.current_is_private:
            self.rb_private.setChecked(True)
        else:
            self.rb_public.setChecked(True)

        layout.addWidget(self.rb_private)
        layout.addWidget(self.rb_public)

        # Advertencia dinámica
        self.lbl_warn = QLabel("⚠️ Atención: Al cambiar a Público, todo el código fuente, ramas e historial serán visibles por cualquier persona en internet.")
        self.lbl_warn.setWordWrap(True)
        self.lbl_warn.setStyleSheet("""
            background-color: rgba(245, 158, 11, 0.12);
            color: #fbbf24;
            border: 1px solid rgba(245, 158, 11, 0.35);
            border-radius: 6px;
            padding: 8px;
            font-size: 11.5px;
        """)
        self.lbl_warn.setVisible(not self.current_is_private)
        layout.addWidget(self.lbl_warn)

        self.rb_public.toggled.connect(lambda checked: self.lbl_warn.setVisible(checked))

        layout.addStretch()

        # Botones de acción
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)

        self.btn_apply = QPushButton("Aplicar Cambio en GitHub" if (self.has_remote and self.is_github) else "Publicar en GitHub")
        self.btn_apply.setCursor(Qt.PointingHandCursor)
        self.btn_apply.setStyleSheet("""
            QPushButton {
                background-color: #6366f1;
                color: #ffffff;
                border: 1px solid #818cf8;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12.5px;
                font-weight: 700;
            }
            QPushButton:hover { background-color: #4f46e5; }
            QPushButton:disabled { background-color: #374151; color: #9ca3af; border: none; }
        """)
        self.btn_apply.clicked.connect(self._on_apply_clicked)
        btn_box.addWidget(self.btn_apply)

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: #9ca3af;
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12.5px;
                font-weight: 600;
            }
            QPushButton:hover { color: #ffffff; }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)

        layout.addLayout(btn_box)

    def _on_apply_clicked(self):
        target_vis = "private" if self.rb_private.isChecked() else "public"
        self.btn_apply.setEnabled(False)
        self.btn_apply.setText("Procesando...")
        QApplication.processEvents()

        if self.has_remote and self.is_github:
            ok, msg = change_repo_visibility(self.project_path, target_vis)
        else:
            ok, msg = publish_repo_to_github(self.project_path, repo_name=self.project_name, visibility=target_vis)

        if ok:
            self.result_message = msg
            self.accept()
        else:
            self.btn_apply.setEnabled(True)
            self.btn_apply.setText("Reintentar")
            self.lbl_warn.setText(f"❌ Error: {msg}")
            self.lbl_warn.setStyleSheet("""
                background-color: rgba(239, 68, 68, 0.15);
                color: #f87171;
                border: 1px solid rgba(239, 68, 68, 0.35);
                border-radius: 6px;
                padding: 8px;
                font-size: 11.5px;
            """)
            self.lbl_warn.setVisible(True)


class LumenCyberActionButton(QFrame):
    """Botón interactivo de diseño ciber-ilustre con icono, título, subtítulo y efectos de hover."""
    
    clicked = Signal(str)

    def __init__(self, icon: str, title: str, subtitle: str, accent_color="#6366f1", parent=None):
        super().__init__(parent)
        self.action_title = title
        self._original_sub = subtitle
        self.is_locked = False
        self.accent_color = accent_color
        self.setCursor(Qt.PointingHandCursor)
        self.setProperty("class", "cyber_action_card")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(56)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(12)

        # Icono con contenedor estilizado
        self.lbl_icon = QLabel(icon)
        self.lbl_icon.setAlignment(Qt.AlignCenter)
        self.lbl_icon.setFixedSize(36, 36)
        self.lbl_icon.setStyleSheet(f"""
            QLabel {{
                background-color: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 8px;
                font-size: 16px;
            }}
        """)
        layout.addWidget(self.lbl_icon)

        # Textos (Título + Subtítulo)
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #f3f4f6;")

        self.lbl_sub = QLabel(subtitle)
        self.lbl_sub.setStyleSheet("font-size: 11px; color: #9ca3af;")

        text_layout.addWidget(self.lbl_title)
        text_layout.addWidget(self.lbl_sub)
        layout.addLayout(text_layout, 1)

        # Flecha indicadora derecha
        self.lbl_arrow = QLabel("›")
        self.lbl_arrow.setStyleSheet("font-size: 18px; font-weight: 800; color: #4b5563;")
        layout.addWidget(self.lbl_arrow)

        self.setStyleSheet(f"""
            QFrame.cyber_action_card {{
                background-color: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.07);
                border-radius: 8px;
            }}
            QFrame.cyber_action_card:hover {{
                background-color: rgba(99, 102, 241, 0.14);
                border: 1px solid {self.accent_color};
            }}
        """)

    def set_locked(self, locked: bool, lock_reason: str = ""):
        self.is_locked = locked
        self.setEnabled(not locked)
        self.setCursor(Qt.ForbiddenCursor if locked else Qt.PointingHandCursor)
        if locked:
            self.lbl_arrow.setText("🔒")
            self.lbl_arrow.setStyleSheet("font-size: 13px; color: #ef4444;")
            self.lbl_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #6b7280;")
            self.lbl_sub.setStyleSheet("font-size: 11px; color: #ef4444; font-weight: 600;")
            if lock_reason:
                self.lbl_sub.setText(lock_reason)
            self.setStyleSheet("""
                QFrame.cyber_action_card {
                    background-color: rgba(255, 255, 255, 0.01);
                    border: 1px dashed rgba(239, 68, 68, 0.25);
                    border-radius: 8px;
                }
            """)
        else:
            self.lbl_arrow.setText("›")
            self.lbl_arrow.setStyleSheet("font-size: 18px; font-weight: 800; color: #4b5563;")
            self.lbl_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #f3f4f6;")
            self.lbl_sub.setStyleSheet("font-size: 11px; color: #9ca3af; font-weight: normal;")
            if hasattr(self, "_original_sub"):
                self.lbl_sub.setText(self._original_sub)
            self.setStyleSheet(f"""
                QFrame.cyber_action_card {{
                    background-color: rgba(255, 255, 255, 0.02);
                    border: 1px solid rgba(255, 255, 255, 0.07);
                    border-radius: 8px;
                }}
                QFrame.cyber_action_card:hover {{
                    background-color: rgba(99, 102, 241, 0.14);
                    border: 1px solid {self.accent_color};
                }}
            """)

    def set_title(self, title: str):
        self.action_title = title
        self.lbl_title.setText(title)

    def set_subtitle(self, subtitle: str):
        self._original_sub = subtitle
        if not self.is_locked:
            self.lbl_sub.setText(subtitle)

    def mousePressEvent(self, event):
        if getattr(self, "is_locked", False) or not self.isEnabled():
            return
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.action_title)
        super().mousePressEvent(event)


class LumenTerminalDisplay(QTextEdit):
    """Visor de terminal de SOLO LECTURA con soporte de colores HTML ricos, tags ciberpunk y diseño estético."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMinimumHeight(240)
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

    def log(self, tag: str, message: str, tag_color: str = "#38bdf8", text_color: str = "#e5e7eb", prefix: str = "◈"):
        """Imprime una línea coloreada en la terminal con timestamp."""
        now = datetime.now().strftime("%H:%M:%S")
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

    def log_git(self, tag: str, message: str):
        self.log(tag, message, tag_color="#c084fc", text_color="#f3e8ff", prefix="🌿")

    def log_env(self, tag: str, message: str):
        self.log(tag, message, tag_color="#fbbf24", text_color="#fef3c7", prefix="⚡")

    def log_warn(self, tag: str, message: str):
        self.log(tag, message, tag_color="#f59e0b", text_color="#fed7aa", prefix="⚠")

    def log_error(self, tag: str, message: str):
        self.log(tag, message, tag_color="#f87171", text_color="#fecaca", prefix="✖")


class LumenDynamicStackedWidget(QStackedWidget):
    """
    QStackedWidget reactivo que sincroniza su sizeHint y minimumSizeHint en tiempo real
    con la página activa actual. Elimina el espacio muerto que dejan páginas más altas
    en vistas compactas como los 3 pilares del Sector.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.currentChanged.connect(self._on_page_changed)

    def _on_page_changed(self, index: int):
        self.updateGeometry()
        p = self.parentWidget()
        while p:
            p.updateGeometry()
            if isinstance(p, QStackedWidget):
                p.updateGeometry()
                break
            p = p.parentWidget()

    def sizeHint(self):
        cur = self.currentWidget()
        if cur:
            return cur.sizeHint()
        return super().sizeHint()

    def minimumSizeHint(self):
        cur = self.currentWidget()
        if cur:
            return cur.minimumSizeHint()
        return super().minimumSizeHint()


class LumenProjectWorkspaceView(QWidget):
    """Vista modular de control de desarrollo y HUD con navegación directa y funciones reales Git e IA."""
    
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.app_version = get_version()
        self.project_data = {}
        self.push_thread = None
        self.audit_thread = None
        self.commit_thread = None
        self.selected_impact = "GAMMA"
        self.selected_target_ver = "v0.1.0"
        self.selected_model_type = "light"
        self.current_commit_proposal = {}
        self.cur_semver_options = {}
        self.merge_thread = None
        self.selected_merge_branch = ""
        self.selected_merge_source = ""
        self.selected_merge_target = ""
        self.selected_merge_author = ""
        self.selected_merge_commits = []
        self.init_ui()

        # Temporizador para la hora en vivo
        self.clock_timer = QTimer(self)
        self.clock_timer.setInterval(1000)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start()

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(14)

        # -------------------------------------------------------------
        # 1. COMMAND BAR SUPERIOR (NAVEGACIÓN & IDENTIFICADOR)
        # -------------------------------------------------------------
        top_bar = QFrame()
        top_bar.setStyleSheet("""
            QFrame {
                background-color: rgba(17, 19, 26, 0.85);
                border: 1px solid rgba(99, 102, 241, 0.25);
                border-radius: 10px;
                padding: 4px 8px;
            }
        """)
        tb_layout = QHBoxLayout(top_bar)
        tb_layout.setContentsMargins(10, 8, 12, 8)
        tb_layout.setSpacing(14)

        self.btn_back = QPushButton("◀  Volver al Selector")
        self.btn_back.setProperty("class", "browse")
        self.btn_back.setCursor(Qt.PointingHandCursor)
        self.btn_back.setStyleSheet("""
            QPushButton {
                background-color: rgba(99, 102, 241, 0.18);
                color: #c7d2fe;
                border: 1px solid rgba(99, 102, 241, 0.40);
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 700;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(99, 102, 241, 0.35);
                border-color: #818cf8;
                color: #ffffff;
            }
        """)
        self.btn_back.clicked.connect(self.back_requested.emit)
        tb_layout.addWidget(self.btn_back)

        # Separador vertical
        sep_top = QFrame()
        sep_top.setFrameShape(QFrame.VLine)
        sep_top.setStyleSheet("background-color: rgba(255, 255, 255, 0.10); max-width: 1px;")
        tb_layout.addWidget(sep_top)

        self.lbl_app_info = QLabel(f"❖  ABRAXAS  [v{self.app_version}]  •  CONTROLADOR LUMEN")
        self.lbl_app_info.setStyleSheet("font-size: 13.5px; font-weight: 800; color: #a5b4fc; letter-spacing: 0.5px;")
        tb_layout.addWidget(self.lbl_app_info)

        tb_layout.addStretch()

        # Botón de refresco manual
        self.btn_refresh = QPushButton("🔄 Sincronizar")
        self.btn_refresh.setProperty("class", "browse")
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.04);
                color: #9ca3af;
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11.5px;
                font-weight: 600;
            }
            QPushButton:hover {
                color: #ffffff;
                border-color: #6366f1;
            }
        """)
        self.btn_refresh.clicked.connect(self.refresh_current_project)
        tb_layout.addWidget(self.btn_refresh)

        # Status Pill
        self.lbl_status_pill = QLabel("🟢 SISTEMA CONECTADO")
        self.lbl_status_pill.setStyleSheet("""
            background-color: rgba(16, 185, 129, 0.12);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.35);
            border-radius: 12px;
            padding: 4px 12px;
            font-size: 11px;
            font-weight: 800;
        """)
        tb_layout.addWidget(self.lbl_status_pill)

        # Botón Toggle Panel Lateral Terminal
        self.btn_top_toggle_term = QPushButton("📟 Terminal Lateral")
        self.btn_top_toggle_term.setToolTip("Alternar panel lateral de terminal y salida")
        self.btn_top_toggle_term.setCursor(Qt.PointingHandCursor)
        self.btn_top_toggle_term.setStyleSheet("""
            QPushButton {
                background-color: rgba(99, 102, 241, 0.15);
                color: #c7d2fe;
                border: 1px solid rgba(99, 102, 241, 0.40);
                border-radius: 8px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: rgba(99, 102, 241, 0.30);
                color: #ffffff;
                border-color: #818cf8;
            }
        """)
        self.btn_top_toggle_term.clicked.connect(self.toggle_terminal_collapsed)
        tb_layout.addWidget(self.btn_top_toggle_term)

        root_layout.addWidget(top_bar)

        # Área de Scroll General
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        scroll_content = QWidget()
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setContentsMargins(0, 0, 6, 0)
        content_layout.setSpacing(10)

        # -------------------------------------------------------------
        # 2. HUD GENERAL DEL PROYECTO (CONSERVADO EN LA PARTE SUPERIOR)
        # -------------------------------------------------------------
        self.hud_card = QFrame()
        self.hud_card.setProperty("class", "surface")
        self.hud_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.hud_card.setStyleSheet("""
            QFrame.surface {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(19, 21, 29, 0.95), stop:1 rgba(15, 17, 23, 0.95));
                border: 1px solid rgba(99, 102, 241, 0.30);
                border-left: 5px solid #818cf8;
                border-radius: 12px;
            }
        """)
        hud_layout = QVBoxLayout(self.hud_card)
        hud_layout.setContentsMargins(18, 12, 18, 12)
        hud_layout.setSpacing(8)

        # Línea 1: Proyecto | Rama | Remoto
        # Línea 1: Proyecto | Rama | Remoto
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        lbl_p_tag = QLabel("📁 Proyecto:")
        lbl_p_tag.setStyleSheet("font-weight: 700; color: #9ca3af; font-size: 13.5px;")
        self.lbl_proj_title = QLabel("Cargando...")
        self.lbl_proj_title.setStyleSheet("font-weight: 800; color: #fbbf24; font-size: 14px;")

        row1.addWidget(lbl_p_tag)
        row1.addWidget(self.lbl_proj_title)

        # Contenedor para Rama y Remoto de la fila 1 (solo se muestra con Git)
        self.row1_git_widget = QWidget()
        row1_git_lay = QHBoxLayout(self.row1_git_widget)
        row1_git_lay.setContentsMargins(0, 0, 0, 0)
        row1_git_lay.setSpacing(8)

        sep1 = QLabel(" | ")
        sep1.setStyleSheet("color: #4b5563; font-weight: 700;")

        lbl_b_tag = QLabel("🌿 Rama:")
        lbl_b_tag.setStyleSheet("font-weight: 700; color: #9ca3af; font-size: 13.5px;")
        self.lbl_proj_branch = QLabel("main")
        self.lbl_proj_branch.setStyleSheet("font-weight: 800; color: #38bdf8; font-size: 13.5px;")

        sep2 = QLabel(" | ")
        sep2.setStyleSheet("color: #4b5563; font-weight: 700;")

        lbl_r_tag = QLabel("🌐 Remoto:")
        lbl_r_tag.setStyleSheet("font-weight: 700; color: #9ca3af; font-size: 13.5px;")
        self.lbl_proj_remote = QLabel("origin/main")
        self.lbl_proj_remote.setStyleSheet("font-weight: 700; color: #c7d2fe; font-size: 13.5px;")

        self.btn_repo_vis = QPushButton("⚙️ Visibilidad")
        self.btn_repo_vis.setCursor(Qt.PointingHandCursor)
        self.btn_repo_vis.setStyleSheet("""
            QPushButton {
                background-color: rgba(99, 102, 241, 0.15);
                color: #a5b4fc;
                border: 1px solid rgba(99, 102, 241, 0.45);
                border-radius: 5px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: rgba(99, 102, 241, 0.35);
                color: #ffffff;
                border-color: #818cf8;
            }
        """)
        self.btn_repo_vis.clicked.connect(self.open_visibility_dialog)

        row1_git_lay.addWidget(sep1)
        row1_git_lay.addWidget(lbl_b_tag)
        row1_git_lay.addWidget(self.lbl_proj_branch)
        row1_git_lay.addWidget(sep2)
        row1_git_lay.addWidget(lbl_r_tag)
        row1_git_lay.addWidget(self.lbl_proj_remote)
        row1_git_lay.addWidget(self.btn_repo_vis)

        row1.addWidget(self.row1_git_widget)
        row1.addStretch()
        hud_layout.addLayout(row1)

        # Línea 2: Entorno | Docker | Hora (SIEMPRE VISIBLE)
        row2 = QHBoxLayout()
        row2.setSpacing(8)

        lbl_e_tag = QLabel("⚡ Entorno:")
        lbl_e_tag.setStyleSheet("font-weight: 700; color: #9ca3af; font-size: 13px;")
        self.lbl_env_status = QLabel("Detectando...")
        self.lbl_env_status.setStyleSheet("font-weight: 800; color: #34d399; font-size: 13px;")

        sep3 = QLabel(" | ")
        sep3.setStyleSheet("color: #4b5563; font-weight: 700;")

        lbl_d_tag = QLabel("🐳 Contenedores Docker:")
        lbl_d_tag.setStyleSheet("font-weight: 700; color: #9ca3af; font-size: 13px;")
        self.lbl_docker_status = QLabel("0 activos")
        self.lbl_docker_status.setStyleSheet("font-weight: 800; color: #60a5fa; font-size: 13px;")

        sep4 = QLabel(" | ")
        sep4.setStyleSheet("color: #4b5563; font-weight: 700;")

        lbl_h_tag = QLabel("🕒 Hora:")
        lbl_h_tag.setStyleSheet("font-weight: 700; color: #9ca3af; font-size: 13px;")
        self.lbl_current_time = QLabel("--:--:--")
        self.lbl_current_time.setStyleSheet("font-family: monospace; font-weight: 700; color: #e5e7eb; font-size: 13px;")

        row2.addWidget(lbl_e_tag)
        row2.addWidget(self.lbl_env_status)
        row2.addWidget(sep3)
        row2.addWidget(lbl_d_tag)
        row2.addWidget(self.lbl_docker_status)
        row2.addWidget(sep4)
        row2.addWidget(lbl_h_tag)
        row2.addWidget(self.lbl_current_time)
        row2.addStretch()
        hud_layout.addLayout(row2)

        # Línea 3: Git HUD: | Git Mod | Untracked | Deleted (solo se muestra con Git)
        self.hud_row3_widget = QWidget()
        row3 = QHBoxLayout(self.hud_row3_widget)
        row3.setContentsMargins(0, 0, 0, 0)
        row3.setSpacing(8)

        lbl_hud_title = QLabel("📊 Git HUD:")
        lbl_hud_title.setStyleSheet("font-weight: 800; color: #c084fc; font-size: 13px;")

        sep5 = QLabel(" | ")
        sep5.setStyleSheet("color: #4b5563; font-weight: 700;")

        lbl_m_tag = QLabel("📝 Git Mod:")
        lbl_m_tag.setStyleSheet("font-weight: 700; color: #9ca3af; font-size: 13px;")
        self.lbl_git_mod = QLabel("0 modificados")
        self.lbl_git_mod.setStyleSheet("font-weight: 700; color: #fbbf24; font-size: 13px;")

        sep6 = QLabel(" | ")
        sep6.setStyleSheet("color: #4b5563; font-weight: 700;")

        lbl_u_tag = QLabel("❓ Untracked:")
        lbl_u_tag.setStyleSheet("font-weight: 700; color: #9ca3af; font-size: 13px;")
        self.lbl_git_untracked = QLabel("0 no rastreados")
        self.lbl_git_untracked.setStyleSheet("font-weight: 700; color: #38bdf8; font-size: 13px;")

        sep7 = QLabel(" | ")
        sep7.setStyleSheet("color: #4b5563; font-weight: 700;")

        lbl_del_tag = QLabel("🗑️ Deleted:")
        lbl_del_tag.setStyleSheet("font-weight: 700; color: #9ca3af; font-size: 13px;")
        self.lbl_git_deleted = QLabel("0")
        self.lbl_git_deleted.setStyleSheet("font-weight: 700; color: #9ca3af; font-size: 13px;")

        row3.addWidget(lbl_hud_title)
        row3.addWidget(sep5)
        row3.addWidget(lbl_m_tag)
        row3.addWidget(self.lbl_git_mod)
        row3.addWidget(sep6)
        row3.addWidget(lbl_u_tag)
        row3.addWidget(self.lbl_git_untracked)
        row3.addWidget(sep7)
        row3.addWidget(lbl_del_tag)
        row3.addWidget(self.lbl_git_deleted)
        row3.addStretch()
        hud_layout.addWidget(self.hud_row3_widget)

        # Línea 4: Historial reciente de Git (solo se muestra con Git)
        self.hud_history_widget = QWidget()
        hist_layout = QVBoxLayout(self.hud_history_widget)
        hist_layout.setContentsMargins(0, 0, 0, 0)
        hist_layout.setSpacing(6)

        # Separador sutil
        sep_hud = QFrame()
        sep_hud.setFrameShape(QFrame.HLine)
        sep_hud.setStyleSheet("background-color: rgba(255, 255, 255, 0.08); max-height: 1px;")
        hist_layout.addWidget(sep_hud)

        lbl_hist_head = QLabel("📜 Historial reciente (Últimos 4 commits):")
        lbl_hist_head.setStyleSheet("font-size: 13px; font-weight: 800; color: #e5e7eb;")
        hist_layout.addWidget(lbl_hist_head)

        # Contenedor dinámico de commits
        self.history_items_container = QWidget()
        self.history_items_layout = QVBoxLayout(self.history_items_container)
        self.history_items_layout.setContentsMargins(0, 0, 0, 0)
        self.history_items_layout.setSpacing(6)
        hist_layout.addWidget(self.history_items_container)

        hud_layout.addWidget(self.hud_history_widget)

        content_layout.addWidget(self.hud_card)

        # -------------------------------------------------------------
        # 3. ZONA MODULAR DE SECTORES (QStackedWidget)
        # -------------------------------------------------------------
        self.sectors_stack = LumenDynamicStackedWidget()

        # =============================================================
        # PÁGINA 0: VISTA GENERAL DE LOS 3 SECTORES (FORMATO PILARES)
        # =============================================================
        self.page_overview = QWidget()
        self.page_overview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        overview_layout = QHBoxLayout(self.page_overview)
        overview_layout.setContentsMargins(0, 0, 0, 0)
        overview_layout.setSpacing(14)
        overview_layout.setAlignment(Qt.AlignTop)

        # Pilar 1: Sector 1 (Protocolo Git y Ciclos)
        self.card_s1 = self.create_overview_sector_card(
            title="🔄  SECTOR 1 : PROTOCOLO GIT",
            accent_color="#38bdf8",
            sector_idx=1,
            actions=[
                ("🔄", "Ciclos de Trabajo", "ADD / IA Commit / IA Audit / Push"),
                ("🌿", "Control de Ramas", "Checkout / Crear / Borrar"),
                ("🔀", "Fusión de Ramas", "git merge"),
                ("⚡", "Estado y Sincronización", "Status / Fetch / Pull"),
                ("🌐", "Visibilidad GitHub", "Alternar entre Público y Privado")
            ]
        )
        overview_layout.addWidget(self.card_s1, 1)

        # Pilar 2: Sector 2 (Entornos y Ejecución)
        self.card_s2 = self.create_overview_sector_card(
            title="🚀  SECTOR 2 : ENTORNOS & RUN",
            accent_color="#10b981",
            sector_idx=2,
            actions=[
                ("💻", "Ejecutar proyecto en editor", "Lanzar espacio de trabajo en VS Code / IDE"),
                ("🐍", "Entornos python", "Gestor de paquetes, dependencias y virtualenv"),
                ("🐳", "Docker y puertos", "Control de contenedores, compose y mapeos")
            ]
        )
        overview_layout.addWidget(self.card_s2, 1)

        # Pilar 3: Sector 3 (Herramientas & IA)
        self.card_s3 = self.create_overview_sector_card(
            title="🧠  SECTOR 3 : HERRAMIENTAS & IA",
            accent_color="#c084fc",
            sector_idx=3,
            actions=[
                ("🛡️", "Gestor de gitignore", "Plantillas inteligentes y reglas de exclusión"),
                ("📖", "Lector de documentación", "Visor interactivo de Markdown, README y APIs"),
                ("🤖", "Utilidades IA", "Asistente Ollama local, refactor y ayuda dev")
            ]
        )
        overview_layout.addWidget(self.card_s3, 1)

        self.sectors_stack.addWidget(self.page_overview)

        # =============================================================
        # PÁGINA 1: VENTANA DEDICADA DEL SECTOR 1 (CICLOS DE TRABAJO & IA AUDIT)
        # =============================================================
        self.page_sector1_view = self.create_sector1_dedicated_view()
        self.sectors_stack.addWidget(self.page_sector1_view)

        # =============================================================
        # PÁGINA 2: VENTANA DEDICADA DEL SECTOR 2 (ENTORNOS Y EJECUCIÓN)
        # =============================================================
        self.page_sector2_view = self.create_sector2_dedicated_view()
        self.sectors_stack.addWidget(self.page_sector2_view)

        # =============================================================
        # PÁGINA 3: VENTANA DEDICADA DEL SECTOR 3 (HERRAMIENTAS & IA)
        # =============================================================
        self.page_sector3_view = self.create_simple_sector_view(
            title="🧠  TERCER SECTOR : HERRAMIENTAS & IA",
            accent_color="#c084fc",
            actions=[
                ("🛡️", "Gestor de gitignore", "Plantillas inteligentes y reglas de exclusión"),
                ("📖", "Lector de documentación", "Visor interactivo de Markdown, README y APIs"),
                ("🤖", "Utilidades IA", "Asistente Ollama local, refactor y ayuda dev")
            ]
        )
        self.sectors_stack.addWidget(self.page_sector3_view)

        content_layout.addWidget(self.sectors_stack)

        # -------------------------------------------------------------
        # 4. RECUADRO INFERIOR (TERMINAL DE SALIDA DE SOLO LECTURA)
        # -------------------------------------------------------------
        self.terminal_frame = QFrame()
        self.terminal_frame.setProperty("class", "surface")
        self.terminal_frame.setStyleSheet("""
            QFrame.surface {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(20, 23, 33, 0.92), stop:1 rgba(14, 16, 23, 0.92));
                border: 1px solid rgba(99, 102, 241, 0.28);
                border-radius: 10px;
            }
        """)
        b_layout = QVBoxLayout(self.terminal_frame)
        b_layout.setContentsMargins(0, 0, 0, 0)
        b_layout.setSpacing(0)

        # Barra de título de la terminal
        term_bar = QFrame()
        term_bar.setStyleSheet("""
            background-color: rgba(255, 255, 255, 0.03);
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            border-top-left-radius: 10px;
            border-top-right-radius: 10px;
            padding: 4px 10px;
        """)
        t_bar_layout = QHBoxLayout(term_bar)
        t_bar_layout.setContentsMargins(12, 7, 12, 7)
        t_bar_layout.setSpacing(10)

        # Dots de ventana Unix
        lbl_dots = QLabel("🔴  🟡  🟢")
        lbl_dots.setStyleSheet("font-size: 9px;")
        t_bar_layout.addWidget(lbl_dots)

        self.lbl_t_title = QLabel("lumen-terminal@abraxas:~$")
        self.lbl_t_title.setStyleSheet("font-family: monospace; font-size: 12px; font-weight: 700; color: #a5b4fc;")
        t_bar_layout.addWidget(self.lbl_t_title)

        t_bar_layout.addStretch()

        # Botón Central: Alternar entre Terminal y Grafo de Ramas (GitHub Network)
        self.btn_toggle_graph_terminal = QPushButton("📊  Ver Grafo de Ramas (Network)")
        self.btn_toggle_graph_terminal.setCursor(Qt.PointingHandCursor)
        self.btn_toggle_graph_terminal.setStyleSheet("""
            QPushButton {
                background-color: rgba(56, 189, 248, 0.14);
                color: #38bdf8;
                border: 1px solid rgba(56, 189, 248, 0.45);
                border-radius: 5px;
                padding: 4px 16px;
                font-weight: 800;
                font-size: 11.5px;
                letter-spacing: 0.3px;
            }
            QPushButton:hover {
                background-color: rgba(56, 189, 248, 0.30);
                border-color: #38bdf8;
                color: #ffffff;
            }
        """)
        self.btn_toggle_graph_terminal.clicked.connect(self.toggle_terminal_graph_view)
        self.btn_toggle_graph_terminal.setVisible(False)
        t_bar_layout.addWidget(self.btn_toggle_graph_terminal)

        t_bar_layout.addStretch()

        # Botón Copiar Log
        btn_copy = QPushButton("📋 Copiar")
        btn_copy.setCursor(Qt.PointingHandCursor)
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
        btn_copy.clicked.connect(self.copy_terminal_output)
        t_bar_layout.addWidget(btn_copy)

        # Botón Limpiar Visor
        btn_clear = QPushButton("🧹 Limpiar")
        btn_clear.setCursor(Qt.PointingHandCursor)
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
        btn_clear.clicked.connect(self.clear_terminal_output)
        t_bar_layout.addWidget(btn_clear)

        self.lbl_t_status = QLabel("⚡ VISOR DE SALIDA [READ-ONLY]")
        self.lbl_t_status.setStyleSheet("font-size: 10px; font-weight: 800; color: #38bdf8; background-color: rgba(6, 182, 212, 0.12); border: 1px solid rgba(6, 182, 212, 0.35); border-radius: 4px; padding: 2px 8px; letter-spacing: 0.5px;")
        t_bar_layout.addWidget(self.lbl_t_status)

        # Botón Ocultar / Mostrar Panel Lateral Terminal
        self.btn_collapse_terminal = QPushButton("▶")
        self.btn_collapse_terminal.setToolTip("Ocultar panel lateral de terminal")
        self.btn_collapse_terminal.setCursor(Qt.PointingHandCursor)
        self.btn_collapse_terminal.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: #bae6fd;
                border: 1px solid rgba(56, 189, 248, 0.35);
                border-radius: 4px;
                padding: 2px 9px;
                font-size: 11px;
                font-weight: 800;
            }
            QPushButton:hover {
                color: #ffffff;
                border-color: #38bdf8;
                background-color: rgba(56, 189, 248, 0.25);
            }
        """)
        self.btn_collapse_terminal.clicked.connect(self.toggle_terminal_collapsed)
        t_bar_layout.addWidget(self.btn_collapse_terminal)

        b_layout.addWidget(term_bar)

        # Stack para conmutar entre Terminal y Grafo de Ramas (GitHub Network)
        self.terminal_stack = QStackedWidget()

        # Página 0: Visor de texto terminal clásico
        self.terminal_display = LumenTerminalDisplay()
        self.terminal_stack.addWidget(self.terminal_display)

        # Página 1: Vista de Grafo de Ramas estilo GitHub Network
        self.git_graph_container = self.create_git_graph_view()
        self.terminal_stack.addWidget(self.git_graph_container)

        b_layout.addWidget(self.terminal_stack)

        self.terminal_frame.setMinimumHeight(240)
        self.terminal_frame.setMaximumHeight(16777215)
        self.terminal_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Contenedor para terminal en posición inferior estándar (para toda la app)
        self.bottom_terminal_container = QWidget()
        self.bottom_terminal_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.bottom_terminal_layout = QVBoxLayout(self.bottom_terminal_container)
        self.bottom_terminal_layout.setContentsMargins(0, 4, 0, 0)
        self.bottom_terminal_layout.setSpacing(0)
        self.bottom_terminal_layout.addWidget(self.terminal_frame)
        content_layout.addWidget(self.bottom_terminal_container, 1)

        scroll_area.setWidget(scroll_content)
        root_layout.addWidget(scroll_area, 1)

    # -----------------------------------------------------------------
    # CREACIÓN DE VISTAS DE SECTORES (DISEÑO PRECISO & COMPACTO)
    # -----------------------------------------------------------------
    def create_overview_sector_card(self, title: str, accent_color: str, sector_idx: int, actions: list) -> QFrame:
        """Crea una tarjeta para la vista general que permite entrar a la ventana limpia del sector."""
        card = QFrame()
        card.setProperty("class", "surface")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        card.setStyleSheet(f"""
            QFrame.surface {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(22, 24, 34, 0.95), stop:1 rgba(16, 18, 25, 0.95));
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-top: 3px solid {accent_color};
                border-radius: 10px;
            }}
        """)
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(14, 10, 14, 10)
        c_layout.setSpacing(6)

        # Header del Sector
        h_layout = QHBoxLayout()
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(f"font-size: 12.5px; font-weight: 900; color: {accent_color}; letter-spacing: 0.5px;")
        h_layout.addWidget(lbl_title)
        h_layout.addStretch()
        c_layout.addLayout(h_layout)

        card.lbl_title = lbl_title
        card.action_buttons = []
        card.original_title = title
        card.accent_color = accent_color

        if sector_idx == 1:
            # Contenedor de acciones normales con Git inicializado
            card.git_container = QWidget()
            g_layout = QVBoxLayout(card.git_container)
            g_layout.setContentsMargins(0, 0, 0, 0)
            g_layout.setSpacing(6)
            for icon, act_title, act_sub in actions:
                btn = LumenCyberActionButton(icon, act_title, act_sub, accent_color=accent_color)
                btn.clicked.connect(lambda t=act_title, s=sector_idx, st=title: self.open_sector_and_handle(s, st, t))
                g_layout.addWidget(btn)
                card.action_buttons.append(btn)
            c_layout.addWidget(card.git_container)

            # Contenedor de acciones cuando NO está inicializado en Git
            card.nogit_container = QWidget()
            ng_layout = QVBoxLayout(card.nogit_container)
            ng_layout.setContentsMargins(0, 0, 0, 0)
            ng_layout.setSpacing(6)

            btn_init_git = LumenCyberActionButton(
                "🌱", "Iniciar Proyecto Git", "Ejecutar git init con rama principal 'main'", accent_color="#10b981"
            )
            btn_init_git.clicked.connect(lambda: self.handle_git_init(create_gitignore=False))
            ng_layout.addWidget(btn_init_git)

            btn_init_git_ign = LumenCyberActionButton(
                "🛡️", "Iniciar Git con .gitignore", "Inicializar git init y generar plantilla de exclusión", accent_color="#38bdf8"
            )
            btn_init_git_ign.clicked.connect(lambda: self.handle_git_init(create_gitignore=True))
            ng_layout.addWidget(btn_init_git_ign)

            card.nogit_actions = [btn_init_git, btn_init_git_ign]
            card.nogit_container.setVisible(False)
            c_layout.addWidget(card.nogit_container)
        else:
            for icon, act_title, act_sub in actions:
                btn = LumenCyberActionButton(icon, act_title, act_sub, accent_color=accent_color)
                btn.clicked.connect(lambda t=act_title, s=sector_idx, st=title: self.open_sector_and_handle(s, st, t))
                c_layout.addWidget(btn)
                card.action_buttons.append(btn)

        c_layout.addStretch()

        def set_git_state(is_git: bool):
            if sector_idx == 1:
                card.git_container.setVisible(is_git)
                card.nogit_container.setVisible(not is_git)
                if is_git:
                    lbl_title.setText(card.original_title)
                else:
                    lbl_title.setText("🔄  SECTOR 1 : PROTOCOLO GIT  [NO INICIALIZADO]")
            elif sector_idx == 3:
                if is_git:
                    lbl_title.setText(card.original_title)
                    for b in card.action_buttons:
                        b.set_locked(False)
                else:
                    lbl_title.setText("🧠  SECTOR 3 : HERRAMIENTAS & IA  [BLOQUEADO]")
                    for b in card.action_buttons:
                        b.set_locked(True, "Bloqueado: Requiere repositorio Git")

        card.set_git_state = set_git_state
        return card

    def create_sector1_dedicated_view(self) -> QFrame:
        """Crea la ventana del Sector 1 con sub-páginas (0: Flujo Ciclos de Trabajo, 1: Selección IA AUDIT)."""
        card = QFrame()
        card.setProperty("class", "surface")
        card.setStyleSheet("""
            QFrame.surface {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(22, 24, 34, 0.95), stop:1 rgba(16, 18, 25, 0.95));
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-top: 3px solid #38bdf8;
                border-radius: 10px;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # Sub-stack interno reactivo para alternar entre Flujo y Vista IA AUDIT
        self.sector1_sub_stack = LumenDynamicStackedWidget()

        # =============================================================
        # SUB-PÁGINA 0: FLUJO PRINCIPAL DE CICLOS DE TRABAJO
        # =============================================================
        page_work = QWidget()
        w_lay = QVBoxLayout(page_work)
        w_lay.setContentsMargins(0, 0, 0, 0)
        w_lay.setSpacing(10)

        head_w = QHBoxLayout()
        head_w.setSpacing(12)

        btn_back_to_main = QPushButton("◀  Volver al Menú de Sectores")
        btn_back_to_main.setCursor(Qt.PointingHandCursor)
        btn_back_to_main.setStyleSheet("""
            QPushButton {
                background-color: rgba(56, 189, 248, 0.15);
                color: #bae6fd;
                border: 1px solid rgba(56, 189, 248, 0.40);
                border-radius: 6px;
                padding: 5px 12px;
                font-weight: 700;
                font-size: 11.5px;
            }
            QPushButton:hover {
                background-color: rgba(56, 189, 248, 0.30);
                border-color: #38bdf8;
                color: #ffffff;
            }
        """)
        btn_back_to_main.clicked.connect(self.go_back_to_sectors_overview)
        head_w.addWidget(btn_back_to_main)

        lbl_w_title = QLabel("🔄  PRIMER SECTOR : FLUJO DE CICLOS DE TRABAJO")
        lbl_w_title.setStyleSheet("font-size: 12.5px; font-weight: 900; color: #38bdf8; letter-spacing: 0.5px;")
        head_w.addWidget(lbl_w_title)
        head_w.addStretch()

        lbl_flow_pill = QLabel("[ADD ➔ IA AUDIT ➔ IA COMMIT ➔ PUSH]")
        lbl_flow_pill.setFixedHeight(24)
        lbl_flow_pill.setAlignment(Qt.AlignCenter)
        lbl_flow_pill.setStyleSheet("font-size: 10px; font-weight: 800; color: #818cf8; background-color: rgba(99, 102, 241, 0.15); border: 1px solid rgba(99, 102, 241, 0.35); border-radius: 4px; padding: 2px 8px;")
        head_w.addWidget(lbl_flow_pill)
        w_lay.addLayout(head_w)

        # Botón 1: ADD (Preparar Cambios)
        btn_add = LumenCyberActionButton("➕", "Add (Preparar Cambios)", "git add -A / Staging completo de archivos modificados y nuevos", accent_color="#34d399")
        btn_add.clicked.connect(self.run_git_add)
        w_lay.addWidget(btn_add)

        # Botón 2: IA AUDIT (Analizar Diff)
        btn_ia_audit = LumenCyberActionButton("🔍", "IA Audit (Analizar Diff)", "Auditoría inteligente del árbol de cambios y diff con IA (Ligero / Pesado)", accent_color="#38bdf8")
        btn_ia_audit.clicked.connect(self.open_ia_audit_subview)
        w_lay.addWidget(btn_ia_audit)

        # Botón 3: IA Commit (Generar commit)
        btn_ia_commit = LumenCyberActionButton("🤖", "IA Commit (Generar commit)", "Generación semántica de mensaje de commit estructurado con SemVer", accent_color="#c084fc")
        btn_ia_commit.clicked.connect(self.start_ia_commit_workflow)
        w_lay.addWidget(btn_ia_commit)

        # Botón 4: Commit Manual
        btn_commit_man = LumenCyberActionButton("✍️", "Commit Manual", "Redactar mensaje personalizado y registrar commit en el repositorio", accent_color="#fbbf24")
        btn_commit_man.clicked.connect(self.start_manual_commit_workflow)
        w_lay.addWidget(btn_commit_man)

        # Botón 5: Push
        btn_push = LumenCyberActionButton("🚀", "Push", "Publicar commits locales confirmados a la rama remota origin", accent_color="#60a5fa")
        btn_push.clicked.connect(self.run_git_push)
        w_lay.addWidget(btn_push)

        w_lay.addStretch()
        self.sector1_sub_stack.addWidget(page_work)

        # =============================================================
        # SUB-PÁGINA 1: SELECCIÓN DE MODELO PARA IA AUDIT
        # =============================================================
        page_ia_audit = QWidget()
        ia_lay = QVBoxLayout(page_ia_audit)
        ia_lay.setContentsMargins(0, 0, 0, 0)
        ia_lay.setSpacing(10)

        head_ia = QHBoxLayout()
        head_ia.setSpacing(12)

        btn_back_to_work = QPushButton("◀  Volver a Ciclos de Trabajo")
        btn_back_to_work.setCursor(Qt.PointingHandCursor)
        btn_back_to_work.setStyleSheet("""
            QPushButton {
                background-color: rgba(56, 189, 248, 0.15);
                color: #bae6fd;
                border: 1px solid rgba(56, 189, 248, 0.40);
                border-radius: 6px;
                padding: 5px 12px;
                font-weight: 700;
                font-size: 11.5px;
            }
            QPushButton:hover {
                background-color: rgba(56, 189, 248, 0.30);
                border-color: #38bdf8;
                color: #ffffff;
            }
        """)
        btn_back_to_work.clicked.connect(self.go_back_to_work_cycles)
        head_ia.addWidget(btn_back_to_work)

        lbl_ia_title = QLabel("🔍  AUDITORÍA DE DIFF CON INTELIGENCIA ARTIFICIAL")
        lbl_ia_title.setStyleSheet("font-size: 12.5px; font-weight: 900; color: #38bdf8; letter-spacing: 0.5px;")
        head_ia.addWidget(lbl_ia_title)
        head_ia.addStretch()

        lbl_engine_pill = QLabel("[OLLAMA ENGINE]")
        lbl_engine_pill.setFixedHeight(24)
        lbl_engine_pill.setAlignment(Qt.AlignCenter)
        lbl_engine_pill.setStyleSheet("font-size: 10px; font-weight: 800; color: #34d399; background-color: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.35); border-radius: 4px; padding: 2px 8px;")
        head_ia.addWidget(lbl_engine_pill)
        ia_lay.addLayout(head_ia)

        # Opción 1: Diff IA (Modelo Ligero)
        light_name = get_configured_model("light")
        self.btn_diff_light = LumenCyberActionButton(
            "⚡", 
            "Diff IA (Modelo Ligero)", 
            f"Auditoría ágil y rápida del diff • Modelo configurado: {light_name}", 
            accent_color="#38bdf8"
        )
        self.btn_diff_light.clicked.connect(lambda: self.run_ai_diff_audit("light"))
        ia_lay.addWidget(self.btn_diff_light)

        # Opción 2: Diff IA (Modelo Pesado)
        heavy_name = get_configured_model("heavy")
        self.btn_diff_heavy = LumenCyberActionButton(
            "🧠", 
            "Diff IA (Modelo Pesado)", 
            f"Auditoría exhaustiva y análisis profundo • Modelo configurado: {heavy_name}", 
            accent_color="#c084fc"
        )
        self.btn_diff_heavy.clicked.connect(lambda: self.run_ai_diff_audit("heavy"))
        ia_lay.addWidget(self.btn_diff_heavy)

        # Botón Volver
        btn_back_audit = LumenCyberActionButton(
            "◀", 
            "Volver", 
            "Regresar a las opciones del Ciclo de Trabajo", 
            accent_color="#9ca3af"
        )
        btn_back_audit.clicked.connect(self.go_back_to_work_cycles)
        ia_lay.addWidget(btn_back_audit)

        ia_lay.addStretch()
        self.sector1_sub_stack.addWidget(page_ia_audit)

        # =============================================================
        # SUB-PÁGINA 2: CONTROL DE VERSIONES (SemVer - Protocolo Táctico)
        # =============================================================
        page_semver = QWidget()
        semver_lay = QVBoxLayout(page_semver)
        semver_lay.setContentsMargins(0, 0, 0, 0)
        semver_lay.setSpacing(10)

        head_semver = QHBoxLayout()
        head_semver.setSpacing(12)

        btn_back_semver = QPushButton("◀  Volver a Ciclos de Trabajo")
        btn_back_semver.setCursor(Qt.PointingHandCursor)
        btn_back_semver.setStyleSheet("""
            QPushButton {
                background-color: rgba(99, 102, 241, 0.15);
                color: #c7d2fe;
                border: 1px solid rgba(99, 102, 241, 0.40);
                border-radius: 6px;
                padding: 5px 12px;
                font-weight: 700;
                font-size: 11.5px;
            }
            QPushButton:hover {
                background-color: rgba(99, 102, 241, 0.30);
                border-color: #818cf8;
                color: #ffffff;
            }
        """)
        btn_back_semver.clicked.connect(self.go_back_to_work_cycles)
        head_semver.addWidget(btn_back_semver)

        self.lbl_semver_title = QLabel("❖ CONTROL DE VERSIONES (SemVer: v0.1.0) ❖")
        self.lbl_semver_title.setStyleSheet("font-size: 12.5px; font-weight: 900; color: #fbbf24; letter-spacing: 0.5px;")
        head_semver.addWidget(self.lbl_semver_title)
        head_semver.addStretch()

        lbl_step1_pill = QLabel("[PASO 1 / 3: CLASIFICACIÓN]")
        lbl_step1_pill.setFixedHeight(24)
        lbl_step1_pill.setAlignment(Qt.AlignCenter)
        lbl_step1_pill.setStyleSheet("font-size: 10px; font-weight: 800; color: #fbbf24; background-color: rgba(251, 191, 36, 0.12); border: 1px solid rgba(251, 191, 36, 0.35); border-radius: 4px; padding: 2px 8px;")
        head_semver.addWidget(lbl_step1_pill)
        semver_lay.addLayout(head_semver)

        lbl_semver_desc = QLabel("Selecciona el nivel de impacto de los cambios a registrar según los estándares SemVer:")
        lbl_semver_desc.setStyleSheet("font-size: 11.5px; color: #9ca3af; margin-bottom: 2px;")
        semver_lay.addWidget(lbl_semver_desc)

        # 1. GAMMA (Patch)
        self.btn_gamma = LumenCyberActionButton(
            "🟢", "1. GAMMA (Patch) ➔ v0.1.1", 
            "Fix, ajuste menor, corrección puntual o documentación", 
            accent_color="#34d399"
        )
        self.btn_gamma.clicked.connect(lambda: self.select_semver_impact("GAMMA"))
        semver_lay.addWidget(self.btn_gamma)

        # 2. BETA (Minor)
        self.btn_beta = LumenCyberActionButton(
            "🟡", "2. BETA (Minor) ➔ v0.2.0", 
            "Nuevo módulo, funcionalidad o capacidad agregada", 
            accent_color="#fbbf24"
        )
        self.btn_beta.clicked.connect(lambda: self.select_semver_impact("BETA"))
        semver_lay.addWidget(self.btn_beta)

        # 3. ALPHA (Major)
        self.btn_alpha = LumenCyberActionButton(
            "🔴", "3. ALPHA (Major) ➔ v1.0.0", 
            "Reestructuración masiva, cambio mayor o de arquitectura", 
            accent_color="#f87171"
        )
        self.btn_alpha.clicked.connect(lambda: self.select_semver_impact("ALPHA"))
        semver_lay.addWidget(self.btn_alpha)

        # 4. Omitir bump
        self.btn_omit = LumenCyberActionButton(
            "⚪", "4. Omitir bump ➔ v0.1.0", 
            "Mantener versión actual sin incrementar etiqueta SemVer", 
            accent_color="#9ca3af"
        )
        self.btn_omit.clicked.connect(lambda: self.select_semver_impact("OMIT"))
        semver_lay.addWidget(self.btn_omit)

        # 5. Cancelar Commit
        btn_cancel_sem = LumenCyberActionButton(
            "◀", "Cancelar Commit", 
            "Regresar al menú de Ciclos de Trabajo", 
            accent_color="#6b7280"
        )
        btn_cancel_sem.clicked.connect(self.go_back_to_work_cycles)
        semver_lay.addWidget(btn_cancel_sem)

        semver_lay.addStretch()
        self.sector1_sub_stack.addWidget(page_semver)

        # =============================================================
        # SUB-PÁGINA 3: MOTOR IA PARA PROCESAMIENTO (Protocolo Táctico)
        # =============================================================
        page_ia_model = QWidget()
        ia_mod_lay = QVBoxLayout(page_ia_model)
        ia_mod_lay.setContentsMargins(0, 0, 0, 0)
        ia_mod_lay.setSpacing(10)

        head_mod = QHBoxLayout()
        head_mod.setSpacing(12)

        btn_back_to_sem = QPushButton("◀  Volver a Selección de Versión")
        btn_back_to_sem.setCursor(Qt.PointingHandCursor)
        btn_back_to_sem.setStyleSheet("""
            QPushButton {
                background-color: rgba(99, 102, 241, 0.15);
                color: #c7d2fe;
                border: 1px solid rgba(99, 102, 241, 0.40);
                border-radius: 6px;
                padding: 5px 12px;
                font-weight: 700;
                font-size: 11.5px;
            }
            QPushButton:hover {
                background-color: rgba(99, 102, 241, 0.30);
                border-color: #818cf8;
                color: #ffffff;
            }
        """)
        btn_back_to_sem.clicked.connect(lambda: self.sector1_sub_stack.setCurrentIndex(2))
        head_mod.addWidget(btn_back_to_sem)

        lbl_mod_title = QLabel("❖ MOTOR IA PARA PROCESAMIENTO ❖")
        lbl_mod_title.setStyleSheet("font-size: 12.5px; font-weight: 900; color: #ec4899; letter-spacing: 0.5px;")
        head_mod.addWidget(lbl_mod_title)
        head_mod.addStretch()

        lbl_step2_pill = QLabel("[PASO 2 / 3: MOTOR IA]")
        lbl_step2_pill.setFixedHeight(24)
        lbl_step2_pill.setAlignment(Qt.AlignCenter)
        lbl_step2_pill.setStyleSheet("font-size: 10px; font-weight: 800; color: #ec4899; background-color: rgba(236, 72, 153, 0.12); border: 1px solid rgba(236, 72, 153, 0.35); border-radius: 4px; padding: 2px 8px;")
        head_mod.addWidget(lbl_step2_pill)
        ia_mod_lay.addLayout(head_mod)

        lbl_mod_desc = QLabel("Selecciona la red neuronal local para sintetizar el commit:")
        lbl_mod_desc.setStyleSheet("font-size: 11.5px; color: #9ca3af; margin-bottom: 2px;")
        ia_mod_lay.addWidget(lbl_mod_desc)

        # 1. HEX (Modelo Ligero - Rápido)
        self.btn_commit_hex = LumenCyberActionButton(
            "🤖", "1. HEX (Qwen 7B - Rápido)", 
            "Generación ágil y concisa de título y cuerpo semántico", 
            accent_color="#38bdf8"
        )
        self.btn_commit_hex.clicked.connect(lambda: self.start_commit_model_generation("light"))
        ia_mod_lay.addWidget(self.btn_commit_hex)

        # 2. HENDRIX (Modelo Pesado - Pesado/Inteligente)
        self.btn_commit_hen = LumenCyberActionButton(
            "🧠", "2. HENDRIX (Qwen 14B - Pesado/Inteligente)", 
            "Análisis exhaustivo del diff y redacción técnica profunda", 
            accent_color="#c084fc"
        )
        self.btn_commit_hen.clicked.connect(lambda: self.start_commit_model_generation("heavy"))
        ia_mod_lay.addWidget(self.btn_commit_hen)

        # 3. Volver
        btn_back_mod = LumenCyberActionButton(
            "◀", "Volver a Selección de Versión", 
            "Regresar para modificar el nivel de impacto SemVer", 
            accent_color="#9ca3af"
        )
        btn_back_mod.clicked.connect(lambda: self.sector1_sub_stack.setCurrentIndex(2))
        ia_mod_lay.addWidget(btn_back_mod)

        ia_mod_lay.addStretch()
        self.sector1_sub_stack.addWidget(page_ia_model)

        # =============================================================
        # SUB-PÁGINA 4: ANIMACIÓN DE CARGA Y SÍNTESIS CON IA
        # =============================================================
        page_loading = QWidget()
        load_lay = QVBoxLayout(page_loading)
        load_lay.setContentsMargins(0, 20, 0, 20)
        load_lay.setSpacing(14)
        load_lay.setAlignment(Qt.AlignCenter)

        card_loader = QFrame()
        card_loader.setProperty("class", "surface")
        card_loader.setStyleSheet("""
            QFrame.surface {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(26, 22, 38, 0.95), stop:1 rgba(15, 12, 25, 0.95));
                border: 1px solid rgba(192, 132, 252, 0.35);
                border-radius: 12px;
                padding: 24px;
            }
        """)
        c_l_lay = QVBoxLayout(card_loader)
        c_l_lay.setSpacing(12)
        c_l_lay.setAlignment(Qt.AlignCenter)

        lbl_pulse_icon = QLabel("⏳")
        lbl_pulse_icon.setAlignment(Qt.AlignCenter)
        lbl_pulse_icon.setStyleSheet("font-size: 32px;")
        c_l_lay.addWidget(lbl_pulse_icon)

        self.lbl_commit_loading_title = QLabel("GENERANDO PROPUESTA DE COMMIT CON IA...")
        self.lbl_commit_loading_title.setAlignment(Qt.AlignCenter)
        self.lbl_commit_loading_title.setStyleSheet("font-size: 14px; font-weight: 900; color: #c084fc; letter-spacing: 0.8px;")
        c_l_lay.addWidget(self.lbl_commit_loading_title)

        self.lbl_commit_loading_sub = QLabel("Analizando git diff, clasificación de impacto y directivas de IA...")
        self.lbl_commit_loading_sub.setAlignment(Qt.AlignCenter)
        self.lbl_commit_loading_sub.setStyleSheet("font-size: 12px; color: #9ca3af;")
        c_l_lay.addWidget(self.lbl_commit_loading_sub)

        # Progress bar indeterminada con estilo Cyber
        self.commit_progress_bar = QProgressBar()
        self.commit_progress_bar.setRange(0, 0)
        self.commit_progress_bar.setFixedHeight(8)
        self.commit_progress_bar.setTextVisible(False)
        self.commit_progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #0b0c13;
                border: 1px solid rgba(192, 132, 252, 0.30);
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6366f1, stop:0.5 #c084fc, stop:1 #38bdf8);
                border-radius: 4px;
            }
        """)
        c_l_lay.addWidget(self.commit_progress_bar)

        load_lay.addWidget(card_loader)
        load_lay.addStretch()
        self.sector1_sub_stack.addWidget(page_loading)

        # =============================================================
        # SUB-PÁGINA 5: CONFIRMAR REGISTRO DE COMMIT (Protocolo Táctico)
        # =============================================================
        page_confirm = QWidget()
        conf_lay = QVBoxLayout(page_confirm)
        conf_lay.setContentsMargins(0, 0, 0, 0)
        conf_lay.setSpacing(10)

        head_conf = QHBoxLayout()
        head_conf.setSpacing(12)

        lbl_conf_head = QLabel("❖ CONFIRMAR REGISTRO DE COMMIT ❖")
        lbl_conf_head.setStyleSheet("font-size: 12.5px; font-weight: 900; color: #34d399; letter-spacing: 0.5px;")
        head_conf.addWidget(lbl_conf_head)
        head_conf.addStretch()

        lbl_step3_pill = QLabel("[PASO 3 / 3: CONFIRMACIÓN]")
        lbl_step3_pill.setFixedHeight(24)
        lbl_step3_pill.setAlignment(Qt.AlignCenter)
        lbl_step3_pill.setStyleSheet("font-size: 10px; font-weight: 800; color: #34d399; background-color: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.35); border-radius: 4px; padding: 2px 8px;")
        head_conf.addWidget(lbl_step3_pill)
        conf_lay.addLayout(head_conf)

        # Tarjeta resumen de la propuesta
        card_prop = QFrame()
        card_prop.setProperty("class", "surface")
        card_prop.setStyleSheet("""
            QFrame.surface {
                background-color: rgba(15, 17, 24, 0.85);
                border: 1px solid rgba(99, 102, 241, 0.30);
                border-left: 4px solid #34d399;
                border-radius: 8px;
                padding: 10px 14px;
            }
        """)
        cp_lay = QVBoxLayout(card_prop)
        cp_lay.setSpacing(6)

        self.lbl_prop_title = QLabel("TÍTULO: HEX:0001 [v0.1.0] | Inicialización")
        self.lbl_prop_title.setStyleSheet("font-family: monospace; font-size: 12.5px; font-weight: 800; color: #fbbf24;")
        cp_lay.addWidget(self.lbl_prop_title)

        self.lbl_prop_impact = QLabel("IMPACTO: GAMMA (Versión: v0.1.0)")
        self.lbl_prop_impact.setStyleSheet("font-family: monospace; font-size: 11.5px; color: #a5b4fc;")
        cp_lay.addWidget(self.lbl_prop_impact)

        self.lbl_prop_body = QLabel("CUERPO: ...")
        self.lbl_prop_body.setWordWrap(True)
        self.lbl_prop_body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lbl_prop_body.setStyleSheet("font-size: 12px; color: #e5e7eb; line-height: 1.4;")
        cp_lay.addWidget(self.lbl_prop_body)

        conf_lay.addWidget(card_prop)

        # Botón Confirmar y Registrar Commit
        self.btn_confirm_commit = LumenCyberActionButton(
            "✅", "1. Confirmar y Registrar Commit", 
            "Escribir commit en Git y crear etiqueta SemVer en el repositorio", 
            accent_color="#34d399"
        )
        self.btn_confirm_commit.clicked.connect(self.confirm_and_record_commit)
        conf_lay.addWidget(self.btn_confirm_commit)

        # Botón Descartar / Volver
        self.btn_discard_commit = LumenCyberActionButton(
            "❌", "2. Descartar / Volver", 
            "Descartar propuesta de commit y regresar al Ciclo de Trabajo", 
            accent_color="#f87171"
        )
        self.btn_discard_commit.clicked.connect(self.discard_commit_proposal)
        conf_lay.addWidget(self.btn_discard_commit)

        conf_lay.addStretch()
        self.sector1_sub_stack.addWidget(page_confirm)

        # =============================================================
        # SUB-PÁGINA 6: POST-COMMIT (OPCIÓN A PUSH O DESCARTAR)
        # =============================================================
        page_post_push = QWidget()
        pp_lay = QVBoxLayout(page_post_push)
        pp_lay.setContentsMargins(0, 0, 0, 0)
        pp_lay.setSpacing(10)

        head_pp = QHBoxLayout()
        head_pp.setSpacing(12)

        lbl_pp_head = QLabel("❖ COMMIT REGISTRADO EXITOSAMENTE ❖")
        lbl_pp_head.setStyleSheet("font-size: 12.5px; font-weight: 900; color: #60a5fa; letter-spacing: 0.5px;")
        head_pp.addWidget(lbl_pp_head)
        head_pp.addStretch()

        lbl_sync_pill = QLabel("[SINCRONIZACIÓN REMOTA]")
        lbl_sync_pill.setFixedHeight(24)
        lbl_sync_pill.setAlignment(Qt.AlignCenter)
        lbl_sync_pill.setStyleSheet("font-size: 10px; font-weight: 800; color: #60a5fa; background-color: rgba(96, 165, 250, 0.12); border: 1px solid rgba(96, 165, 250, 0.35); border-radius: 4px; padding: 2px 8px;")
        head_pp.addWidget(lbl_sync_pill)
        pp_lay.addLayout(head_pp)

        lbl_pp_desc = QLabel("El commit y la etiqueta han sido grabados localmente en Git. ¿Deseas sincronizarlos con GitHub?")
        lbl_pp_desc.setStyleSheet("font-size: 11.5px; color: #9ca3af; margin-bottom: 2px;")
        pp_lay.addWidget(lbl_pp_desc)

        # Botón 1: Push Ahora
        self.btn_post_push = LumenCyberActionButton(
            "🚀", "1. Hacer Push Ahora (Enviar cambios y tags a GitHub)", 
            "Ejecutar git push --follow-tags hacia la rama remota origin", 
            accent_color="#60a5fa"
        )
        self.btn_post_push.clicked.connect(self.execute_post_commit_push)
        pp_lay.addWidget(self.btn_post_push)

        # Botón 2: Descartar / Finalizar
        self.btn_post_skip = LumenCyberActionButton(
            "❌", "2. Descartar / Finalizar (No hacer push)", 
            "Mantener cambios en local y regresar al menú de Ciclos de Trabajo", 
            accent_color="#9ca3af"
        )
        self.btn_post_skip.clicked.connect(self.discard_post_commit_push)
        pp_lay.addWidget(self.btn_post_skip)

        pp_lay.addStretch()
        self.sector1_sub_stack.addWidget(page_post_push)

        # =============================================================
        # SUB-PÁGINA 7: REDACCIÓN DE COMMIT MANUAL
        # =============================================================
        page_manual = QWidget()
        man_lay = QVBoxLayout(page_manual)
        man_lay.setContentsMargins(0, 0, 0, 0)
        man_lay.setSpacing(10)

        head_man = QHBoxLayout()
        head_man.setSpacing(12)

        lbl_man_head = QLabel("❖ REDACCIÓN DE COMMIT MANUAL ❖")
        lbl_man_head.setStyleSheet("font-size: 12.5px; font-weight: 900; color: #fbbf24; letter-spacing: 0.5px;")
        head_man.addWidget(lbl_man_head)
        head_man.addStretch()

        lbl_man_pill = QLabel("[COMMIT MANUAL]")
        lbl_man_pill.setFixedHeight(24)
        lbl_man_pill.setAlignment(Qt.AlignCenter)
        lbl_man_pill.setStyleSheet("font-size: 10px; font-weight: 800; color: #fbbf24; background-color: rgba(251, 191, 36, 0.12); border: 1px solid rgba(251, 191, 36, 0.35); border-radius: 4px; padding: 2px 8px;")
        head_man.addWidget(lbl_man_pill)
        man_lay.addLayout(head_man)

        card_man = QFrame()
        card_man.setProperty("class", "surface")
        card_man.setStyleSheet("""
            QFrame.surface {
                background-color: rgba(15, 17, 24, 0.85);
                border: 1px solid rgba(99, 102, 241, 0.30);
                border-left: 4px solid #fbbf24;
                border-radius: 8px;
                padding: 10px 14px;
            }
        """)
        cm_lay = QVBoxLayout(card_man)
        cm_lay.setSpacing(8)

        # 1. Título del Commit
        lbl_t_title = QLabel("Título o mensaje principal del commit (*):")
        lbl_t_title.setStyleSheet("font-size: 11.5px; font-weight: 700; color: #f3f4f6;")
        cm_lay.addWidget(lbl_t_title)

        self.txt_manual_title = QLineEdit()
        self.txt_manual_title.setPlaceholderText("ej. Corrección en rutas del sistema o actualización de módulos...")
        self.txt_manual_title.setStyleSheet("""
            QLineEdit {
                background-color: #0f1015;
                border: 1px solid #22242e;
                border-radius: 6px;
                color: #f3f4f6;
                padding: 6px 10px;
                font-size: 12.5px;
            }
            QLineEdit:focus {
                border-color: #fbbf24;
            }
        """)
        cm_lay.addWidget(self.txt_manual_title)

        # 2. Descripción / Cuerpo (Opcional)
        lbl_t_body = QLabel("Cuerpo o descripción detallada (opcional):")
        lbl_t_body.setStyleSheet("font-size: 11.5px; font-weight: 700; color: #9ca3af;")
        cm_lay.addWidget(lbl_t_body)

        self.txt_manual_body = QTextEdit()
        self.txt_manual_body.setFixedHeight(65)
        self.txt_manual_body.setPlaceholderText("Explica brevemente los motivos o detalles técnicos del cambio (opcional)...")
        self.txt_manual_body.setStyleSheet("""
            QTextEdit {
                background-color: #0f1015;
                border: 1px solid #22242e;
                border-radius: 6px;
                color: #f3f4f6;
                padding: 6px 8px;
                font-size: 12px;
            }
            QTextEdit:focus {
                border-color: #fbbf24;
            }
        """)
        cm_lay.addWidget(self.txt_manual_body)

        # 3. Etiqueta SemVer (Opcional)
        lbl_t_sem = QLabel("Impacto y Etiqueta SemVer (opcional):")
        lbl_t_sem.setStyleSheet("font-size: 11.5px; font-weight: 700; color: #9ca3af;")
        cm_lay.addWidget(lbl_t_sem)

        self.cmb_manual_semver = QComboBox()
        self.cmb_manual_semver.setItemDelegate(QStyledItemDelegate())
        self.cmb_manual_semver.setStyleSheet("""
            QComboBox {
                background-color: #0f1015;
                border: 1px solid #22242e;
                border-radius: 6px;
                color: #f3f4f6;
                padding: 6px 10px;
                font-size: 12px;
            }
        """)
        cm_lay.addWidget(self.cmb_manual_semver)

        man_lay.addWidget(card_man)

        # Botón 1: Confirmar y Grabar Commit Manual
        self.btn_confirm_manual = LumenCyberActionButton(
            "💾", "1. Confirmar y Registrar Commit", 
            "Escribir commit con tu identidad en Git y aplicar etiqueta si se especificó", 
            accent_color="#34d399"
        )
        self.btn_confirm_manual.clicked.connect(self.execute_manual_commit)
        man_lay.addWidget(self.btn_confirm_manual)

        # Botón 2: Cancelar
        self.btn_cancel_manual = LumenCyberActionButton(
            "◀", "2. Cancelar y Volver", 
            "Regresar al menú principal de Ciclos de Trabajo sin hacer commit", 
            accent_color="#f87171"
        )
        self.btn_cancel_manual.clicked.connect(lambda: self.sector1_sub_stack.setCurrentIndex(0))
        man_lay.addWidget(self.btn_cancel_manual)

        man_lay.addStretch()
        self.sector1_sub_stack.addWidget(page_manual)

        # =============================================================
        # SUB-PÁGINA 8: CONTROL DE RAMAS
        # =============================================================
        self.page_branches = self.create_sector1_branches_view()
        self.sector1_sub_stack.addWidget(self.page_branches)

        # =============================================================
        # SUB-PÁGINA 9: FUSIÓN DE RAMAS (GIT MERGE)
        # =============================================================
        self.page_merge = self.create_sector1_merge_view()
        self.sector1_sub_stack.addWidget(self.page_merge)

        # =============================================================
        # SUB-PÁGINA 10: ESTADO Y SINCRONIZACIÓN (STATUS • FETCH • PULL)
        # =============================================================
        self.page_sync = self.create_sector1_sync_view()
        self.sector1_sub_stack.addWidget(self.page_sync)

        layout.addWidget(self.sector1_sub_stack)
        return card

    def create_sector1_branches_view(self) -> QWidget:
        """Crea la sub-página dedicada para el Control y Matriz Táctica de Ramas."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 1. Cabecera
        head = QHBoxLayout()
        head.setSpacing(10)

        btn_back_main = QPushButton("◀  Volver al Menú de Sectores")
        btn_back_main.setCursor(Qt.PointingHandCursor)
        btn_back_main.setStyleSheet("""
            QPushButton {
                background-color: rgba(56, 189, 248, 0.15);
                color: #bae6fd;
                border: 1px solid rgba(56, 189, 248, 0.40);
                border-radius: 6px;
                padding: 5px 12px;
                font-weight: 700;
                font-size: 11.5px;
            }
            QPushButton:hover {
                background-color: rgba(56, 189, 248, 0.30);
                border-color: #38bdf8;
                color: #ffffff;
            }
        """)
        btn_back_main.clicked.connect(self.go_back_to_sectors_overview)
        head.addWidget(btn_back_main)

        btn_to_work = QPushButton("🔄  Ciclos de Trabajo")
        btn_to_work.setCursor(Qt.PointingHandCursor)
        btn_to_work.setStyleSheet("""
            QPushButton {
                background-color: rgba(99, 102, 241, 0.15);
                color: #c7d2fe;
                border: 1px solid rgba(99, 102, 241, 0.40);
                border-radius: 6px;
                padding: 5px 12px;
                font-weight: 700;
                font-size: 11.5px;
            }
            QPushButton:hover {
                background-color: rgba(99, 102, 241, 0.30);
                border-color: #818cf8;
                color: #ffffff;
            }
        """)
        btn_to_work.clicked.connect(self.go_back_to_work_cycles)
        head.addWidget(btn_to_work)

        btn_to_merge = QPushButton("🔀  Fusión de Ramas")
        btn_to_merge.setCursor(Qt.PointingHandCursor)
        btn_to_merge.setStyleSheet("""
            QPushButton {
                background-color: rgba(56, 189, 248, 0.15);
                color: #bae6fd;
                border: 1px solid rgba(56, 189, 248, 0.40);
                border-radius: 6px;
                padding: 5px 12px;
                font-weight: 700;
                font-size: 11.5px;
            }
            QPushButton:hover {
                background-color: rgba(56, 189, 248, 0.30);
                border-color: #38bdf8;
                color: #ffffff;
            }
        """)
        btn_to_merge.clicked.connect(self.open_merge_view)
        head.addWidget(btn_to_merge)

        btn_to_sync = QPushButton("⚡  Estado y Sync")
        btn_to_sync.setCursor(Qt.PointingHandCursor)
        btn_to_sync.setStyleSheet("""
            QPushButton {
                background-color: rgba(52, 211, 153, 0.15);
                color: #6ee7b7;
                border: 1px solid rgba(52, 211, 153, 0.40);
                border-radius: 6px;
                padding: 5px 12px;
                font-weight: 700;
                font-size: 11.5px;
            }
            QPushButton:hover {
                background-color: rgba(52, 211, 153, 0.30);
                border-color: #34d399;
                color: #ffffff;
            }
        """)
        btn_to_sync.clicked.connect(self.open_sync_view)
        head.addWidget(btn_to_sync)

        lbl_title = QLabel("🌿  CONTROL DE RAMAS")
        lbl_title.setStyleSheet("font-size: 12.5px; font-weight: 900; color: #38bdf8; letter-spacing: 0.5px;")
        head.addWidget(lbl_title)
        head.addStretch()

        lbl_pill = QLabel("[LUMEN • CONTROL DE RAMAS]")
        lbl_pill.setFixedHeight(24)
        lbl_pill.setAlignment(Qt.AlignCenter)
        lbl_pill.setStyleSheet("font-size: 10px; font-weight: 800; color: #34d399; background-color: rgba(52, 211, 153, 0.12); border: 1px solid rgba(52, 211, 153, 0.35); border-radius: 4px; padding: 2px 8px;")
        head.addWidget(lbl_pill)
        layout.addLayout(head)

        # 2. Barra de Leyenda Táctica
        legend_frame = QFrame()
        legend_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 6px;
                padding: 4px 10px;
            }
        """)
        leg_lay = QHBoxLayout(legend_frame)
        leg_lay.setContentsMargins(8, 4, 8, 4)
        leg_lay.setSpacing(14)

        leg_title = QLabel("Leyenda:")
        leg_title.setStyleSheet("font-size: 11px; font-weight: 800; color: #9ca3af;")
        leg_lay.addWidget(leg_title)

        legends = [
            ("■ Stale/Gone", "#f87171"),
            ("■ Local (Mía)", "#fde047"),
            ("■ Local", "#f3f4f6"),
            ("■ Remota (Otros)", "#4ade80"),
            ("■ Remota (Mía)", "#60a5fa")
        ]
        for leg_text, leg_color in legends:
            l_lbl = QLabel(leg_text)
            l_lbl.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {leg_color};")
            leg_lay.addWidget(l_lbl)
        leg_lay.addStretch()

        self.lbl_branch_count_info = QLabel("")
        self.lbl_branch_count_info.setStyleSheet("font-size: 11px; color: #9ca3af; font-family: monospace;")
        leg_lay.addWidget(self.lbl_branch_count_info)
        layout.addWidget(legend_frame)

        # 3. Lista de Ramas con Scroll (Limpio y Sin Recuadro Negro)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(220)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
        """)
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        self.branches_list_layout = QVBoxLayout(scroll_content)
        self.branches_list_layout.setContentsMargins(4, 4, 4, 4)
        self.branches_list_layout.setSpacing(6)
        self.branches_list_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)

        # 4. Cajón Dinámico de Acciones (Nueva Rama / Eliminar / Desplegar)
        self.branches_action_drawer = QStackedWidget()
        self.branches_action_drawer.setVisible(False)
        self.branches_action_drawer.setStyleSheet("""
            QStackedWidget {
                background-color: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(56, 189, 248, 0.25);
                border-radius: 8px;
            }
        """)

        # Panel 1: Crear Rama
        p_create = QFrame()
        p_create.setStyleSheet("background: transparent; border: none;")
        pc_lay = QVBoxLayout(p_create)
        pc_lay.setContentsMargins(12, 10, 12, 10)
        pc_lay.setSpacing(8)

        lbl_pc = QLabel("➕  CREAR NUEVA RAMA TÁCTICA (git checkout -b)")
        lbl_pc.setStyleSheet("font-size: 12px; font-weight: 800; color: #34d399;")
        pc_lay.addWidget(lbl_pc)

        row_c = QHBoxLayout()
        row_c.setSpacing(10)
        self.txt_new_branch_name = QLineEdit()
        self.txt_new_branch_name.setPlaceholderText("Nombre de la nueva rama (ej. feat/kanban, fix/auth)...")
        self.txt_new_branch_name.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                color: #f3f4f6;
                padding: 6px 10px;
                font-size: 12px;
            }
            QLineEdit:focus { border-color: #34d399; }
        """)
        self.txt_new_branch_name.returnPressed.connect(self.execute_create_branch_action)
        row_c.addWidget(self.txt_new_branch_name, 1)

        btn_confirm_create = QPushButton("Crear y Cambiar")
        btn_confirm_create.setCursor(Qt.PointingHandCursor)
        btn_confirm_create.setStyleSheet("""
            QPushButton {
                background-color: rgba(52, 211, 153, 0.20);
                color: #6ee7b7;
                border: 1px solid #34d399;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 700;
                font-size: 11.5px;
            }
            QPushButton:hover { background-color: rgba(52, 211, 153, 0.35); color: #ffffff; }
        """)
        btn_confirm_create.clicked.connect(self.execute_create_branch_action)
        row_c.addWidget(btn_confirm_create)

        btn_cancel_create = QPushButton("Cancelar")
        btn_cancel_create.setCursor(Qt.PointingHandCursor)
        btn_cancel_create.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: #9ca3af;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11.5px;
            }
            QPushButton:hover { background-color: rgba(255, 255, 255, 0.10); color: #ffffff; }
        """)
        btn_cancel_create.clicked.connect(self.hide_branches_action_drawer)
        row_c.addWidget(btn_cancel_create)
        pc_lay.addLayout(row_c)
        self.branches_action_drawer.addWidget(p_create)

        # Panel 2: Eliminar Rama
        p_delete = QFrame()
        p_delete.setStyleSheet("background: transparent; border: none;")
        pd_lay = QVBoxLayout(p_delete)
        pd_lay.setContentsMargins(12, 10, 12, 10)
        pd_lay.setSpacing(8)

        lbl_pd = QLabel("🗑️  ELIMINAR RAMA LOCAL")
        lbl_pd.setStyleSheet("font-size: 12px; font-weight: 800; color: #f87171;")
        pd_lay.addWidget(lbl_pd)

        row_d = QHBoxLayout()
        row_d.setSpacing(10)
        self.cmb_del_branch = QComboBox()
        self.cmb_del_branch.setItemDelegate(QStyledItemDelegate())
        self.cmb_del_branch.setStyleSheet("""
            QComboBox {
                background-color: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                color: #f3f4f6;
                padding: 6px 10px;
                font-size: 12px;
            }
        """)
        row_d.addWidget(self.cmb_del_branch, 1)

        self.chk_del_force = QCheckBox("Forzar eliminación (-D)")
        self.chk_del_force.setStyleSheet("color: #f87171; font-size: 11px; font-weight: 700;")
        row_d.addWidget(self.chk_del_force)

        btn_confirm_del = QPushButton("Eliminar Rama")
        btn_confirm_del.setCursor(Qt.PointingHandCursor)
        btn_confirm_del.setStyleSheet("""
            QPushButton {
                background-color: rgba(248, 113, 113, 0.20);
                color: #fca5a5;
                border: 1px solid #f87171;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 700;
                font-size: 11.5px;
            }
            QPushButton:hover { background-color: rgba(248, 113, 113, 0.35); color: #ffffff; }
        """)
        btn_confirm_del.clicked.connect(self.execute_delete_branch_action)
        row_d.addWidget(btn_confirm_del)

        btn_cancel_del = QPushButton("Cancelar")
        btn_cancel_del.setCursor(Qt.PointingHandCursor)
        btn_cancel_del.setStyleSheet(btn_cancel_create.styleSheet())
        btn_cancel_del.clicked.connect(self.hide_branches_action_drawer)
        row_d.addWidget(btn_cancel_del)
        pd_lay.addLayout(row_d)
        self.branches_action_drawer.addWidget(p_delete)

        # Panel 3: Desplegar Rama (Push upstream)
        p_deploy = QFrame()
        p_deploy.setStyleSheet("background: transparent; border: none;")
        pdp_lay = QVBoxLayout(p_deploy)
        pdp_lay.setContentsMargins(12, 10, 12, 10)
        pdp_lay.setSpacing(8)

        lbl_pdp = QLabel("🚀  DESPLEGAR RAMA LOCAL (git push -u origin <rama>)")
        lbl_pdp.setStyleSheet("font-size: 12px; font-weight: 800; color: #60a5fa;")
        pdp_lay.addWidget(lbl_pdp)

        row_dp = QHBoxLayout()
        row_dp.setSpacing(10)
        self.cmb_deploy_branch = QComboBox()
        self.cmb_deploy_branch.setItemDelegate(QStyledItemDelegate())
        self.cmb_deploy_branch.setStyleSheet(self.cmb_del_branch.styleSheet())
        row_dp.addWidget(self.cmb_deploy_branch, 1)

        btn_confirm_deploy = QPushButton("Desplegar a Origin")
        btn_confirm_deploy.setCursor(Qt.PointingHandCursor)
        btn_confirm_deploy.setStyleSheet("""
            QPushButton {
                background-color: rgba(96, 165, 250, 0.20);
                color: #93c5fd;
                border: 1px solid #60a5fa;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 700;
                font-size: 11.5px;
            }
            QPushButton:hover { background-color: rgba(96, 165, 250, 0.35); color: #ffffff; }
        """)
        btn_confirm_deploy.clicked.connect(self.execute_deploy_branch_action)
        row_dp.addWidget(btn_confirm_deploy)

        btn_cancel_deploy = QPushButton("Cancelar")
        btn_cancel_deploy.setCursor(Qt.PointingHandCursor)
        btn_cancel_deploy.setStyleSheet(btn_cancel_create.styleSheet())
        btn_cancel_deploy.clicked.connect(self.hide_branches_action_drawer)
        row_dp.addWidget(btn_cancel_deploy)
        pdp_lay.addLayout(row_dp)
        self.branches_action_drawer.addWidget(p_deploy)

        layout.addWidget(self.branches_action_drawer)

        # 5. Barra Inferior de Acciones Principales
        bot_bar = QHBoxLayout()
        bot_bar.setSpacing(10)

        btn_act_new = QPushButton("➕  Crear Rama")
        btn_act_new.setCursor(Qt.PointingHandCursor)
        btn_act_new.setStyleSheet("""
            QPushButton {
                background-color: rgba(52, 211, 153, 0.12);
                color: #6ee7b7;
                border: 1px solid rgba(52, 211, 153, 0.35);
                border-radius: 6px;
                padding: 7px 14px;
                font-weight: 700;
                font-size: 11.5px;
            }
            QPushButton:hover { background-color: rgba(52, 211, 153, 0.25); color: #ffffff; }
        """)
        btn_act_new.clicked.connect(self.show_create_branch_drawer)
        bot_bar.addWidget(btn_act_new)

        btn_act_del = QPushButton("🗑️  Eliminar Rama")
        btn_act_del.setCursor(Qt.PointingHandCursor)
        btn_act_del.setStyleSheet("""
            QPushButton {
                background-color: rgba(248, 113, 113, 0.12);
                color: #fca5a5;
                border: 1px solid rgba(248, 113, 113, 0.35);
                border-radius: 6px;
                padding: 7px 14px;
                font-weight: 700;
                font-size: 11.5px;
            }
            QPushButton:hover { background-color: rgba(248, 113, 113, 0.25); color: #ffffff; }
        """)
        btn_act_del.clicked.connect(self.show_delete_branch_drawer)
        bot_bar.addWidget(btn_act_del)

        btn_act_dep = QPushButton("🚀  Desplegar Rama")
        btn_act_dep.setCursor(Qt.PointingHandCursor)
        btn_act_dep.setStyleSheet("""
            QPushButton {
                background-color: rgba(96, 165, 250, 0.12);
                color: #93c5fd;
                border: 1px solid rgba(96, 165, 250, 0.35);
                border-radius: 6px;
                padding: 7px 14px;
                font-weight: 700;
                font-size: 11.5px;
            }
            QPushButton:hover { background-color: rgba(96, 165, 250, 0.25); color: #ffffff; }
        """)
        btn_act_dep.clicked.connect(self.show_deploy_branch_drawer)
        bot_bar.addWidget(btn_act_dep)

        btn_act_ref = QPushButton("🔄  Refrescar")
        btn_act_ref.setCursor(Qt.PointingHandCursor)
        btn_act_ref.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: #d1d5db;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                padding: 7px 14px;
                font-weight: 700;
                font-size: 11.5px;
            }
            QPushButton:hover { background-color: rgba(255, 255, 255, 0.12); color: #ffffff; }
        """)
        btn_act_ref.clicked.connect(self.refresh_branches_list)
        bot_bar.addWidget(btn_act_ref)

        bot_bar.addStretch()
        layout.addLayout(bot_bar)

        return page

    # =================================================================
    # SEGUNDO SECTOR : ENTORNOS Y EJECUCIÓN (VENV & EDITOR LAUNCHER)
    # =================================================================
    def create_sector2_dedicated_view(self) -> QFrame:
        """Crea la ventana interactiva dedicada del Sector 2 (Entornos y Ejecución)."""
        card = QFrame()
        card.setProperty("class", "surface")
        card.setStyleSheet("""
            QFrame.surface {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(22, 24, 34, 0.95), stop:1 rgba(16, 18, 25, 0.95));
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-top: 3px solid #10b981;
                border-radius: 10px;
            }
        """)
        card.setMinimumHeight(440)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        self.sector2_sub_stack = LumenDynamicStackedWidget()

        # Página 0: Lanzador y Selector de Editores
        self.page_s2_editor = self.create_sector2_editor_view()
        self.sector2_sub_stack.addWidget(self.page_s2_editor)

        # Página 1: Gestor de Entornos Virtuales Python
        self.page_s2_venv = self.create_sector2_venv_view()
        self.sector2_sub_stack.addWidget(self.page_s2_venv)

        # Página 2: Control de Docker y Compose
        self.page_s2_docker = self.create_sector2_docker_view()
        self.sector2_sub_stack.addWidget(self.page_s2_docker)

        # Página 3: Auditoría y Monitor de Puertos TCP
        self.page_s2_ports = self.create_sector2_ports_view()
        self.sector2_sub_stack.addWidget(self.page_s2_ports)

        layout.addWidget(self.sector2_sub_stack)
        return card

    def create_sector2_editor_view(self) -> QWidget:
        """Sub-página interactiva para seleccionar y lanzar editores de código."""
        page = QWidget()
        page.setMinimumHeight(340)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Barra de navegación con botón único de volver al menú global y pestañas
        nav = QHBoxLayout()
        nav.setSpacing(10)

        btn_back = QPushButton("◀  Volver al Menú de Sectores")
        btn_back.setCursor(Qt.PointingHandCursor)
        btn_back.setStyleSheet("""
            QPushButton {
                background-color: rgba(16, 185, 129, 0.15);
                color: #6ee7b7;
                border: 1px solid rgba(16, 185, 129, 0.40);
                border-radius: 6px;
                padding: 5px 12px;
                font-weight: 700;
                font-size: 11.5px;
            }
            QPushButton:hover {
                background-color: rgba(16, 185, 129, 0.30);
                border-color: #10b981;
                color: #ffffff;
            }
        """)
        btn_back.clicked.connect(self.go_back_to_sectors_overview)
        nav.addWidget(btn_back)

        lbl_title = QLabel("🚀  SECTOR 2 : ENTORNOS & RUN")
        lbl_title.setStyleSheet("font-size: 12.5px; font-weight: 900; color: #10b981; letter-spacing: 0.5px;")
        nav.addWidget(lbl_title)

        # Pestañas de Navegación Sector 2
        btn_tab_editor = QPushButton("💻  Selector de Editor")
        btn_tab_editor.setCursor(Qt.PointingHandCursor)
        btn_tab_editor.setStyleSheet("""
            QPushButton {
                background-color: rgba(16, 185, 129, 0.25);
                color: #ffffff;
                border: 1px solid #10b981;
                border-radius: 6px;
                padding: 4px 10px;
                font-weight: 800;
                font-size: 11px;
            }
        """)
        nav.addWidget(btn_tab_editor)

        btn_tab_venv = QPushButton("🐍  Entorno Python")
        btn_tab_venv.setCursor(Qt.PointingHandCursor)
        btn_tab_venv.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: #9ca3af;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 4px 10px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(52, 211, 153, 0.15);
                color: #6ee7b7;
                border-color: #34d399;
            }
        """)
        btn_tab_venv.clicked.connect(self.open_sector2_venv_view)
        nav.addWidget(btn_tab_venv)

        btn_tab_docker = QPushButton("🐳  Docker")
        btn_tab_docker.setCursor(Qt.PointingHandCursor)
        btn_tab_docker.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: #9ca3af;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 4px 10px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(56, 189, 248, 0.15);
                color: #38bdf8;
                border-color: #38bdf8;
            }
        """)
        btn_tab_docker.clicked.connect(self.open_sector2_docker_view)
        nav.addWidget(btn_tab_docker)

        btn_tab_ports = QPushButton("🔌  Puertos TCP")
        btn_tab_ports.setCursor(Qt.PointingHandCursor)
        btn_tab_ports.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: #9ca3af;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 4px 10px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(251, 191, 36, 0.15);
                color: #fbbf24;
                border-color: #fbbf24;
            }
        """)
        btn_tab_ports.clicked.connect(self.open_sector2_ports_view)
        nav.addWidget(btn_tab_ports)

        nav.addStretch()

        self.lbl_s2_pref_editor_pill = QLabel("PREFERIDO: DETECTANDO...")
        self.lbl_s2_pref_editor_pill.setFixedHeight(24)
        self.lbl_s2_pref_editor_pill.setAlignment(Qt.AlignCenter)
        self.lbl_s2_pref_editor_pill.setStyleSheet("font-size: 10px; font-weight: 800; color: #34d399; background-color: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.35); border-radius: 4px; padding: 2px 8px;")
        nav.addWidget(self.lbl_s2_pref_editor_pill)
        layout.addLayout(nav)

        # Botón de apertura rápida con el editor predeterminado
        self.btn_s2_quick_launch = QPushButton("🚀  Abrir Proyecto con Editor Predeterminado")
        self.btn_s2_quick_launch.setCursor(Qt.PointingHandCursor)
        self.btn_s2_quick_launch.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #10b981);
                color: #ffffff;
                font-size: 12.5px;
                font-weight: 800;
                border-radius: 8px;
                padding: 8px 14px;
                border: 1px solid rgba(255, 255, 255, 0.15);
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #34d399);
                border-color: #6ee7b7;
            }
        """)
        self.btn_s2_quick_launch.clicked.connect(self.quick_launch_preferred_editor)
        layout.addWidget(self.btn_s2_quick_launch)

        # Panel de lista de editores detectados con ScrollArea con altura mínima asegurada
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(180)
        scroll.setMaximumHeight(260)
        scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                background-color: rgba(0, 0, 0, 0.20);
            }
        """)

        self.editor_list_widget = QWidget()
        self.editor_list_layout = QVBoxLayout(self.editor_list_widget)
        self.editor_list_layout.setContentsMargins(6, 6, 6, 6)
        self.editor_list_layout.setSpacing(6)
        scroll.setWidget(self.editor_list_widget)

        layout.addWidget(scroll, 1)
        return page

    def create_sector2_venv_view(self) -> QWidget:
        """Sub-página interactiva para gestionar entornos virtuales Python y dependencias."""
        page = QWidget()
        page.setMinimumHeight(340)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Barra de navegación
        nav = QHBoxLayout()
        nav.setSpacing(10)

        btn_back = QPushButton("◀  Volver al Menú de Sectores")
        btn_back.setCursor(Qt.PointingHandCursor)
        btn_back.setStyleSheet("""
            QPushButton {
                background-color: rgba(52, 211, 153, 0.15);
                color: #6ee7b7;
                border: 1px solid rgba(52, 211, 153, 0.40);
                border-radius: 6px;
                padding: 5px 12px;
                font-weight: 700;
                font-size: 11.5px;
            }
            QPushButton:hover {
                background-color: rgba(52, 211, 153, 0.30);
                border-color: #34d399;
                color: #ffffff;
            }
        """)
        btn_back.clicked.connect(self.go_back_to_sectors_overview)
        nav.addWidget(btn_back)

        lbl_title = QLabel("🚀  SECTOR 2 : ENTORNOS & RUN")
        lbl_title.setStyleSheet("font-size: 12.5px; font-weight: 900; color: #10b981; letter-spacing: 0.5px;")
        nav.addWidget(lbl_title)

        # Pestañas de Navegación Sector 2
        btn_tab_editor = QPushButton("💻  Selector de Editor")
        btn_tab_editor.setCursor(Qt.PointingHandCursor)
        btn_tab_editor.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: #9ca3af;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 4px 10px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(16, 185, 129, 0.15);
                color: #6ee7b7;
                border-color: #10b981;
            }
        """)
        btn_tab_editor.clicked.connect(self.open_sector2_editor_view)
        nav.addWidget(btn_tab_editor)

        btn_tab_venv = QPushButton("🐍  Entorno Python")
        btn_tab_venv.setCursor(Qt.PointingHandCursor)
        btn_tab_venv.setStyleSheet("""
            QPushButton {
                background-color: rgba(52, 211, 153, 0.25);
                color: #ffffff;
                border: 1px solid #34d399;
                border-radius: 6px;
                padding: 4px 10px;
                font-weight: 800;
                font-size: 11px;
            }
        """)
        nav.addWidget(btn_tab_venv)

        btn_tab_docker = QPushButton("🐳  Docker")
        btn_tab_docker.setCursor(Qt.PointingHandCursor)
        btn_tab_docker.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: #9ca3af;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 4px 10px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(56, 189, 248, 0.15);
                color: #38bdf8;
                border-color: #38bdf8;
            }
        """)
        btn_tab_docker.clicked.connect(self.open_sector2_docker_view)
        nav.addWidget(btn_tab_docker)

        btn_tab_ports = QPushButton("🔌  Puertos TCP")
        btn_tab_ports.setCursor(Qt.PointingHandCursor)
        btn_tab_ports.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: #9ca3af;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 4px 10px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(251, 191, 36, 0.15);
                color: #fbbf24;
                border-color: #fbbf24;
            }
        """)
        btn_tab_ports.clicked.connect(self.open_sector2_ports_view)
        nav.addWidget(btn_tab_ports)

        nav.addStretch()

        btn_refresh = QPushButton("🔄  Refrescar Estado")
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: #e5e7eb;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                padding: 5px 10px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.12);
                color: #ffffff;
            }
        """)
        btn_refresh.clicked.connect(self.refresh_sector2_venv_view)
        nav.addWidget(btn_refresh)
        layout.addLayout(nav)

        # Panel de Telemetría del Venv
        self.frame_venv_telemetry = QFrame()
        self.frame_venv_telemetry.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 0.25);
                border: 1px solid rgba(52, 211, 153, 0.25);
                border-radius: 8px;
                padding: 8px 12px;
            }
        """)
        t_lay = QVBoxLayout(self.frame_venv_telemetry)
        t_lay.setContentsMargins(10, 8, 10, 8)
        t_lay.setSpacing(4)

        self.lbl_s2_venv_status = QLabel("Estado: Inspeccionando...")
        self.lbl_s2_venv_status.setStyleSheet("font-size: 12px; font-weight: 800; color: #f3f4f6;")
        t_lay.addWidget(self.lbl_s2_venv_status)

        self.lbl_s2_venv_details = QLabel("Intérprete: Desconocido | Paquetes: 0")
        self.lbl_s2_venv_details.setStyleSheet("font-size: 11px; color: #9ca3af;")
        t_lay.addWidget(self.lbl_s2_venv_details)

        self.lbl_s2_venv_deps = QLabel("Dependencias detectadas: Ninguna")
        self.lbl_s2_venv_deps.setStyleSheet("font-size: 11px; color: #34d399;")
        t_lay.addWidget(self.lbl_s2_venv_deps)

        layout.addWidget(self.frame_venv_telemetry)

        # Contenedor dinámico de acciones de Venv
        self.venv_actions_container = QWidget()
        self.venv_actions_layout = QVBoxLayout(self.venv_actions_container)
        self.venv_actions_layout.setContentsMargins(0, 4, 0, 4)
        self.venv_actions_layout.setSpacing(8)

        layout.addWidget(self.venv_actions_container, 1)
        return page

    def open_sector2_editor_view(self):
        """Abre la sub-página del lanzador de editores y refresca los editores detectados."""
        self.dock_terminal_at_bottom()
        self.sectors_stack.setCurrentIndex(2)
        if hasattr(self, "sector2_sub_stack"):
            self.sector2_sub_stack.setCurrentIndex(0)
            self.sector2_sub_stack.updateGeometry()
        if hasattr(self, "sectors_stack"):
            self.sectors_stack.updateGeometry()
        self.refresh_sector2_editor_view()
        p_name = self.project_data.get("name", "Proyecto")
        self.terminal_display.log("IDE", f"Panel de Lanzador de Editor abierto para <b>{p_name}</b>.", tag_color="#10b981", prefix="💻")

    def refresh_sector2_editor_view(self):
        """Detecta editores en el sistema y reconstruye la lista."""
        while self.editor_list_layout.count():
            item = self.editor_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        pref = get_preferred_editor()
        detected = detect_installed_editors()

        pref_name = pref
        for e in detected:
            if e["id"] == pref:
                pref_name = e["name"]
                break

        self.lbl_s2_pref_editor_pill.setText(f"PREFERIDO: {pref_name.upper()}")
        self.btn_s2_quick_launch.setText(f"🚀  Abrir Proyecto Ahora con {pref_name}")

        if not detected:
            lbl_none = QLabel("⚠️ No se detectaron editores conocidos en el sistema (VS Code, Cursor, Neovim, etc.).")
            lbl_none.setStyleSheet("color: #f87171; font-weight: 700; padding: 12px;")
            self.editor_list_layout.addWidget(lbl_none)
            self.btn_s2_quick_launch.setEnabled(False)
            return

        self.btn_s2_quick_launch.setEnabled(True)

        for ed in detected:
            card = QFrame()
            card.setStyleSheet("""
                QFrame {
                    background-color: rgba(255, 255, 255, 0.03);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 8px;
                }
                QFrame:hover {
                    background-color: rgba(255, 255, 255, 0.06);
                    border-color: rgba(16, 185, 129, 0.35);
                }
            """)
            c_lay = QHBoxLayout(card)
            c_lay.setContentsMargins(12, 8, 12, 8)
            c_lay.setSpacing(10)

            lbl_ic = QLabel(ed["icon"])
            lbl_ic.setStyleSheet("font-size: 18px;")
            c_lay.addWidget(lbl_ic)

            info_lay = QVBoxLayout()
            info_lay.setSpacing(1)
            lbl_name = QLabel(ed["name"])
            lbl_name.setStyleSheet("font-size: 12.5px; font-weight: 800; color: #f3f4f6;")
            info_lay.addWidget(lbl_name)

            type_label = "Aplicación Gráfica (GUI)" if ed["type"] == "gui" else "Editor de Consola (Terminal)"
            is_pref = (ed["id"] == pref)
            if is_pref:
                type_label += "  •  ⭐ Predeterminado"

            lbl_sub = QLabel(type_label)
            lbl_sub.setStyleSheet("font-size: 10.5px; color: #34d399;" if is_pref else "font-size: 10.5px; color: #9ca3af;")
            info_lay.addWidget(lbl_sub)
            c_lay.addLayout(info_lay, 1)

            if not is_pref:
                btn_set_pref = QPushButton("⭐ Establecer por Defecto")
                btn_set_pref.setCursor(Qt.PointingHandCursor)
                btn_set_pref.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(255, 255, 255, 0.05);
                        color: #d1d5db;
                        border: 1px solid rgba(255, 255, 255, 0.15);
                        border-radius: 6px;
                        padding: 5px 10px;
                        font-weight: 600;
                        font-size: 11px;
                    }
                    QPushButton:hover {
                        background-color: rgba(255, 255, 255, 0.12);
                        color: #ffffff;
                    }
                """)
                btn_set_pref.clicked.connect(lambda _, eid=ed["id"], ename=ed["name"]: self.execute_set_preferred_editor(eid, ename))
                c_lay.addWidget(btn_set_pref)

            btn_open = QPushButton(f"🚀 Abrir ({ed['id']})")
            btn_open.setCursor(Qt.PointingHandCursor)
            btn_open.setStyleSheet("""
                QPushButton {
                    background-color: rgba(16, 185, 129, 0.20);
                    color: #6ee7b7;
                    border: 1px solid rgba(16, 185, 129, 0.45);
                    border-radius: 6px;
                    padding: 5px 12px;
                    font-weight: 700;
                    font-size: 11.5px;
                }
                QPushButton:hover {
                    background-color: #10b981;
                    color: #064e3b;
                }
            """)
            btn_open.clicked.connect(lambda _, eid=ed["id"], ename=ed["name"]: self.execute_launch_editor(eid, ename))
            c_lay.addWidget(btn_open)

            self.editor_list_layout.addWidget(card)

        self.editor_list_layout.addStretch()

    def quick_launch_preferred_editor(self):
        """Lanza rápidamente el proyecto con el editor predeterminado."""
        pref = get_preferred_editor()
        detected = detect_installed_editors()
        name = pref
        for e in detected:
            if e["id"] == pref:
                name = e["name"]
                break
        self.execute_launch_editor(pref, name)

    def execute_set_preferred_editor(self, editor_id: str, editor_name: str):
        """Guarda la preferencia del editor y refresca la vista."""
        if set_preferred_editor(editor_id):
            self.terminal_display.log_success("IDE", f"Editor predeterminado actualizado a: <b>{editor_name}</b> (<code>{editor_id}</code>).")
            self.refresh_sector2_editor_view()
        else:
            self.terminal_display.log_error("IDE", "No se pudo guardar la preferencia del editor en disco.")

    def execute_launch_editor(self, editor_id: str, editor_name: str):
        """Lanza el editor apuntando a la carpeta del proyecto activo."""
        path = self.project_data.get("path")
        if not path or not os.path.exists(path):
            self.terminal_display.log_error("IDE", "Ruta de proyecto no válida.")
            return

        self.terminal_display.log("IDE", f"Lanzando <b>{editor_name}</b> en <code>{path}</code>...", tag_color="#10b981", prefix="🚀")
        ok, msg = launch_project_in_editor(editor_id, path)
        if ok:
            self.terminal_display.log_success("IDE", f"<b>{editor_name}</b> iniciado exitosamente: {msg}")
        else:
            self.terminal_display.log_error("IDE", f"Error al lanzar {editor_name}: {msg}")

    def open_sector2_venv_view(self):
        """Abre la sub-página de gestión de entornos virtuales y refresca la telemetría."""
        self.dock_terminal_at_bottom()
        self.sectors_stack.setCurrentIndex(2)
        if hasattr(self, "sector2_sub_stack"):
            self.sector2_sub_stack.setCurrentIndex(1)
            self.sector2_sub_stack.updateGeometry()
        if hasattr(self, "sectors_stack"):
            self.sectors_stack.updateGeometry()
        self.refresh_sector2_venv_view()
        p_name = self.project_data.get("name", "Proyecto")
        self.terminal_display.log("VENV", f"Gestor de Entorno Virtual cargado para <b>{p_name}</b>.", tag_color="#34d399", prefix="🐍")

    def refresh_sector2_venv_view(self):
        """Inspecciona el entorno virtual del proyecto y actualiza los widgets dinámicos."""
        path = self.project_data.get("path")
        if not path or not os.path.exists(path):
            return

        venv_info = inspect_python_venv(path)
        self.current_venv_info = venv_info

        if venv_info["has_venv"]:
            status_text = f"🟢 ACTIVO / VINCULADO ({venv_info['venv_name']})"
            self.lbl_s2_venv_status.setText(f"Entorno Virtual: <b>{venv_info['venv_name']}</b>  |  Estado: {status_text}")
            self.lbl_s2_venv_details.setText(f"Intérprete: {venv_info['python_version']}  |  Paquetes instalados: {venv_info['package_count']}")
        else:
            self.lbl_s2_venv_status.setText("Entorno Virtual: ⚠️ NO DETECTADO EN EL PROYECTO")
            self.lbl_s2_venv_details.setText("No se encontró ninguna carpeta .venv / venv / env con intérprete de Python.")

        deps_str = ", ".join(venv_info["dependency_files"]) if venv_info["dependency_files"] else "Ninguno detectado"
        self.lbl_s2_venv_deps.setText(f"Archivos de especificación: <b>{deps_str}</b>")

        while self.venv_actions_layout.count():
            item = self.venv_actions_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not venv_info["has_venv"]:
            btn_uv = LumenCyberActionButton("⚡", "Crear Entorno Rápido con uv (.venv)", "Aislamiento ultra veloz utilizando motor uv", accent_color="#10b981")
            btn_uv.clicked.connect(lambda: self.execute_create_venv(use_uv=True))
            self.venv_actions_layout.addWidget(btn_uv)

            btn_std = LumenCyberActionButton("🐍", "Crear Entorno Estándar con python venv (.venv)", "Creación nativa con módulo python3 -m venv", accent_color="#34d399")
            btn_std.clicked.connect(lambda: self.execute_create_venv(use_uv=False))
            self.venv_actions_layout.addWidget(btn_std)
        else:
            btn_sync_deps = LumenCyberActionButton("📦", "Sincronizar / Instalar Dependencias del Proyecto", "Instalar paquetes desde requirements.txt o pyproject.toml", accent_color="#10b981")
            btn_sync_deps.clicked.connect(self.execute_install_venv_dependencies)
            self.venv_actions_layout.addWidget(btn_sync_deps)

            btn_custom_pkg = LumenCyberActionButton("➕", "Instalar Paquete Individual", "Instalar librerías específicas (ej: fastapi requests numpy)", accent_color="#38bdf8")
            btn_custom_pkg.clicked.connect(self.execute_install_custom_package)
            self.venv_actions_layout.addWidget(btn_custom_pkg)

            btn_freeze = LumenCyberActionButton("📄", "Congelar Dependencias (pip freeze)", "Actualizar o generar requirements.txt con las versiones exactas", accent_color="#fbbf24")
            btn_freeze.clicked.connect(self.execute_freeze_venv_dependencies)
            self.venv_actions_layout.addWidget(btn_freeze)

            btn_list = LumenCyberActionButton("📋", "Listar Paquetes Instalados", "Mostrar en la terminal la lista de librerías y versiones instaladas", accent_color="#818cf8")
            btn_list.clicked.connect(self.execute_list_venv_packages)
            self.venv_actions_layout.addWidget(btn_list)

            btn_delete = LumenCyberActionButton("🗑️", f"Eliminar Entorno Virtual ({venv_info['venv_name']})", "Borrar permanentemente el entorno virtual del disco", accent_color="#ef4444")
            btn_delete.clicked.connect(self.execute_delete_venv)
            self.venv_actions_layout.addWidget(btn_delete)

        self.venv_actions_layout.addStretch()

    def execute_create_venv(self, use_uv: bool = False):
        """Crea el entorno virtual en segundo plano."""
        path = self.project_data.get("path")
        if not path:
            return
        engine = "uv" if use_uv else "python venv"
        self.terminal_display.log("VENV", f"Creando entorno virtual <code>.venv</code> usando <b>{engine}</b>...", tag_color="#10b981", prefix="⚡")
        self.venv_worker = PythonVenvWorkerThread("create_venv", path, extra_args=use_uv)
        self.venv_worker.finished_task.connect(self.on_venv_worker_finished)
        self.venv_worker.start()

    def execute_install_venv_dependencies(self):
        """Instala las dependencias del proyecto."""
        path = self.project_data.get("path")
        venv_path = getattr(self, "current_venv_info", {}).get("venv_path", "")
        if not path or not venv_path:
            self.terminal_display.log_error("VENV", "No se detectó la ruta del entorno virtual.")
            return

        self.terminal_display.log("VENV", "Instalando dependencias del proyecto en el entorno virtual...", tag_color="#10b981", prefix="📦")
        self.venv_worker = PythonVenvWorkerThread("install_deps", path, venv_path=venv_path)
        self.venv_worker.finished_task.connect(self.on_venv_worker_finished)
        self.venv_worker.start()

    def execute_install_custom_package(self):
        """Solicita paquetes al usuario e instala en el venv."""
        path = self.project_data.get("path")
        venv_path = getattr(self, "current_venv_info", {}).get("venv_path", "")
        if not path or not venv_path:
            return

        pkgs_str, ok = QInputDialog.getText(
            self, "Instalar Paquetes Python", 
            "Escribe los nombres de los paquetes a instalar (separados por espacio):",
            text="fastapi uvicorn"
        )
        if ok and pkgs_str.strip():
            pkgs = pkgs_str.strip().split()
            self.terminal_display.log("VENV", f"Instalando paquete(s): <b>{' '.join(pkgs)}</b>...", tag_color="#38bdf8", prefix="➕")
            self.venv_worker = PythonVenvWorkerThread("install_custom", path, venv_path=venv_path, extra_args=pkgs)
            self.venv_worker.finished_task.connect(self.on_venv_worker_finished)
            self.venv_worker.start()

    def execute_freeze_venv_dependencies(self):
        """Congela las dependencias del entorno."""
        path = self.project_data.get("path")
        venv_path = getattr(self, "current_venv_info", {}).get("venv_path", "")
        if not path or not venv_path:
            return

        self.terminal_display.log("VENV", "Congelando dependencias a <code>requirements.txt</code>...", tag_color="#fbbf24", prefix="📄")
        self.venv_worker = PythonVenvWorkerThread("freeze", path, venv_path=venv_path)
        self.venv_worker.finished_task.connect(self.on_venv_worker_finished)
        self.venv_worker.start()

    def execute_list_venv_packages(self):
        """Lista los paquetes instalados en la terminal."""
        venv_path = getattr(self, "current_venv_info", {}).get("venv_path", "")
        if not venv_path:
            return
        pkgs = list_installed_packages(venv_path)
        if not pkgs:
            self.terminal_display.log_info("VENV", "No se detectaron paquetes instalados en el venv.")
            return

        self.terminal_display.log("VENV", f"Lista de paquetes instalados en <code>{os.path.basename(venv_path)}</code> ({len(pkgs)} librerías):", tag_color="#818cf8", prefix="📋")
        for name, ver in pkgs:
            self.terminal_display.log("PKG", f"{name} == {ver}", tag_color="#9ca3af", prefix="•")

    def execute_delete_venv(self):
        """Elimina el entorno virtual con confirmación."""
        venv_path = getattr(self, "current_venv_info", {}).get("venv_path", "")
        if not venv_path:
            return

        reply = QMessageBox.question(
            self, "Confirmar Eliminación",
            f"¿Estás seguro de que deseas eliminar permanentemente la carpeta '{os.path.basename(venv_path)}'?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            path = self.project_data.get("path", "")
            self.terminal_display.log_warn("VENV", f"Eliminando entorno virtual: <code>{venv_path}</code>...")
            self.venv_worker = PythonVenvWorkerThread("delete_venv", path, venv_path=venv_path)
            self.venv_worker.finished_task.connect(self.on_venv_worker_finished)
            self.venv_worker.start()

    def on_venv_worker_finished(self, success: bool, task_name: str, message: str):
        """Callback al finalizar tareas de venv en segundo plano."""
        if success:
            self.terminal_display.log_success(task_name, message)
        else:
            self.terminal_display.log_error(task_name, message)
        self.refresh_sector2_venv_view()

    # =================================================================
    # SUB-PÁGINA 2: CONTROL DE DOCKER Y COMPOSE
    # =================================================================
    def create_sector2_docker_view(self) -> QWidget:
        """Sub-página interactiva para gestionar Docker, contenedores y Compose con Deep Discovery."""
        page = QWidget()
        page.setMinimumHeight(440)
        page.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)

        # Contenedor Izquierdo: Controles, Telemetría y Contenedores
        docker_left_widget = QWidget()
        layout = QVBoxLayout(docker_left_widget)
        layout.setContentsMargins(0, 0, 6, 0)
        layout.setSpacing(10)

        # Barra de navegación
        nav = QHBoxLayout()
        nav.setSpacing(10)

        btn_back = QPushButton("◀  Volver al Menú de Sectores")
        btn_back.setCursor(Qt.PointingHandCursor)
        btn_back.setStyleSheet("""
            QPushButton {
                background-color: rgba(56, 189, 248, 0.15);
                color: #bae6fd;
                border: 1px solid rgba(56, 189, 248, 0.40);
                border-radius: 6px;
                padding: 5px 12px;
                font-weight: 700;
                font-size: 11.5px;
            }
            QPushButton:hover {
                background-color: rgba(56, 189, 248, 0.30);
                border-color: #38bdf8;
                color: #ffffff;
            }
        """)
        btn_back.clicked.connect(self.go_back_to_sectors_overview)
        nav.addWidget(btn_back)

        lbl_title = QLabel("🚀  SECTOR 2 : ENTORNOS & RUN")
        lbl_title.setStyleSheet("font-size: 12.5px; font-weight: 900; color: #10b981; letter-spacing: 0.5px;")
        nav.addWidget(lbl_title)

        # Pestañas de Navegación Sector 2
        btn_tab_editor = QPushButton("💻  Selector de Editor")
        btn_tab_editor.setCursor(Qt.PointingHandCursor)
        btn_tab_editor.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: #9ca3af;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 4px 10px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(16, 185, 129, 0.15);
                color: #6ee7b7;
                border-color: #10b981;
            }
        """)
        btn_tab_editor.clicked.connect(self.open_sector2_editor_view)
        nav.addWidget(btn_tab_editor)

        btn_tab_venv = QPushButton("🐍  Entorno Python")
        btn_tab_venv.setCursor(Qt.PointingHandCursor)
        btn_tab_venv.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: #9ca3af;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 4px 10px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(52, 211, 153, 0.15);
                color: #6ee7b7;
                border-color: #34d399;
            }
        """)
        btn_tab_venv.clicked.connect(self.open_sector2_venv_view)
        nav.addWidget(btn_tab_venv)

        btn_tab_docker = QPushButton("🐳  Docker")
        btn_tab_docker.setCursor(Qt.PointingHandCursor)
        btn_tab_docker.setStyleSheet("""
            QPushButton {
                background-color: rgba(56, 189, 248, 0.25);
                color: #ffffff;
                border: 1px solid #38bdf8;
                border-radius: 6px;
                padding: 4px 10px;
                font-weight: 800;
                font-size: 11px;
            }
        """)
        nav.addWidget(btn_tab_docker)

        btn_tab_ports = QPushButton("🔌  Puertos TCP")
        btn_tab_ports.setCursor(Qt.PointingHandCursor)
        btn_tab_ports.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: #9ca3af;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 4px 10px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(251, 191, 36, 0.15);
                color: #fbbf24;
                border-color: #fbbf24;
            }
        """)
        btn_tab_ports.clicked.connect(self.open_sector2_ports_view)
        nav.addWidget(btn_tab_ports)

        nav.addStretch()

        btn_refresh = QPushButton("🔄  Refrescar")
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: #e5e7eb;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                padding: 5px 10px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.12);
                color: #ffffff;
            }
        """)
        btn_refresh.clicked.connect(self.refresh_sector2_docker_view)
        nav.addWidget(btn_refresh)

        btn_toggle_term = QPushButton("📟  Terminal")
        btn_toggle_term.setToolTip("Ocultar o mostrar el panel inferior de la terminal")
        btn_toggle_term.setCursor(Qt.PointingHandCursor)
        btn_toggle_term.setStyleSheet("""
            QPushButton {
                background-color: rgba(99, 102, 241, 0.15);
                color: #c7d2fe;
                border: 1px solid rgba(99, 102, 241, 0.35);
                border-radius: 6px;
                padding: 5px 10px;
                font-weight: 700;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(99, 102, 241, 0.30);
                color: #ffffff;
                border-color: #818cf8;
            }
        """)
        btn_toggle_term.clicked.connect(self.toggle_terminal_collapsed)
        nav.addWidget(btn_toggle_term)

        layout.addLayout(nav)

        # Panel de Telemetría Docker + Estado Compose Tool
        self.frame_docker_telemetry = QFrame()
        self.frame_docker_telemetry.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 0.25);
                border: 1px solid rgba(56, 189, 248, 0.25);
                border-radius: 8px;
                padding: 8px 12px;
            }
        """)
        d_lay = QVBoxLayout(self.frame_docker_telemetry)
        d_lay.setContentsMargins(10, 8, 10, 8)
        d_lay.setSpacing(4)

        self.lbl_s2_docker_status = QLabel("Docker: Inspeccionando estado...")
        self.lbl_s2_docker_status.setStyleSheet("font-size: 12px; font-weight: 800; color: #f3f4f6;")
        d_lay.addWidget(self.lbl_s2_docker_status)

        self.lbl_s2_docker_details = QLabel("Demonio: Desconocido | Archivos Compose: Ninguno")
        self.lbl_s2_docker_details.setStyleSheet("font-size: 11px; color: #9ca3af;")
        d_lay.addWidget(self.lbl_s2_docker_details)

        self.lbl_s2_compose_tool = QLabel("Compose Tool: Detectando...")
        self.lbl_s2_compose_tool.setStyleSheet("font-size: 10.5px; color: #6b7280;")
        d_lay.addWidget(self.lbl_s2_compose_tool)

        layout.addWidget(self.frame_docker_telemetry)

        # Barra de Acciones Globales Docker (Prune, etc.)
        docker_acts = QHBoxLayout()
        docker_acts.setSpacing(8)

        btn_prune = QPushButton("🧹 Purgar Recursos Inactivos (Prune)")
        btn_prune.setCursor(Qt.PointingHandCursor)
        btn_prune.setStyleSheet("""
            QPushButton {
                background-color: rgba(239, 68, 68, 0.12);
                color: #fca5a5;
                border: 1px solid rgba(239, 68, 68, 0.30);
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 700;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.25);
                color: #ffffff;
            }
        """)
        btn_prune.clicked.connect(self.execute_docker_system_prune)
        docker_acts.addWidget(btn_prune)
        docker_acts.addStretch()
        layout.addLayout(docker_acts)

        # ScrollArea con Compose Stacks + Contenedores
        scroll_docker = QScrollArea()
        scroll_docker.setWidgetResizable(True)
        scroll_docker.setMinimumHeight(280)
        scroll_docker.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        scroll_docker.setStyleSheet("""
            QScrollArea {
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                background-color: rgba(0, 0, 0, 0.20);
            }
        """)

        self.docker_containers_widget = QWidget()
        self.docker_containers_layout = QVBoxLayout(self.docker_containers_widget)
        self.docker_containers_layout.setContentsMargins(6, 6, 6, 6)
        self.docker_containers_layout.setSpacing(6)
        scroll_docker.setWidget(self.docker_containers_widget)

        layout.addWidget(scroll_docker, 1)

        # Contenedor Derecho: Panel Lateral Exclusivo para Terminal en Docker
        self.docker_side_terminal_container = QWidget()
        self.docker_side_terminal_layout = QVBoxLayout(self.docker_side_terminal_container)
        self.docker_side_terminal_layout.setContentsMargins(0, 0, 0, 0)
        self.docker_side_terminal_layout.setSpacing(0)
        self.docker_side_terminal_container.setMinimumWidth(340)
        self.docker_side_terminal_container.setVisible(False)

        # Splitter Horizontal Interno de Docker
        self.docker_splitter = QSplitter(Qt.Horizontal)
        self.docker_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: rgba(255, 255, 255, 0.08);
                width: 4px;
                border-radius: 2px;
            }
            QSplitter::handle:hover {
                background-color: #38bdf8;
            }
        """)
        self.docker_splitter.addWidget(docker_left_widget)
        self.docker_splitter.addWidget(self.docker_side_terminal_container)
        self.docker_splitter.setStretchFactor(0, 6)
        self.docker_splitter.setStretchFactor(1, 4)

        page_layout.addWidget(self.docker_splitter, 1)
        return page

    # =================================================================
    # SUB-PÁGINA 3: AUDITORÍA Y MONITOR DE PUERTOS TCP
    # =================================================================
    def create_sector2_ports_view(self) -> QWidget:
        """Sub-página interactiva para auditar puertos TCP en escucha y matar procesos."""
        page = QWidget()
        page.setMinimumHeight(350)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Barra de navegación
        nav = QHBoxLayout()
        nav.setSpacing(10)

        btn_back = QPushButton("◀  Volver al Menú de Sectores")
        btn_back.setCursor(Qt.PointingHandCursor)
        btn_back.setStyleSheet("""
            QPushButton {
                background-color: rgba(251, 191, 36, 0.15);
                color: #fde68a;
                border: 1px solid rgba(251, 191, 36, 0.40);
                border-radius: 6px;
                padding: 5px 12px;
                font-weight: 700;
                font-size: 11.5px;
            }
            QPushButton:hover {
                background-color: rgba(251, 191, 36, 0.30);
                border-color: #fbbf24;
                color: #ffffff;
            }
        """)
        btn_back.clicked.connect(self.go_back_to_sectors_overview)
        nav.addWidget(btn_back)

        lbl_title = QLabel("🚀  SECTOR 2 : ENTORNOS & RUN")
        lbl_title.setStyleSheet("font-size: 12.5px; font-weight: 900; color: #10b981; letter-spacing: 0.5px;")
        nav.addWidget(lbl_title)

        # Pestañas de Navegación Sector 2
        btn_tab_editor = QPushButton("💻  Selector de Editor")
        btn_tab_editor.setCursor(Qt.PointingHandCursor)
        btn_tab_editor.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: #9ca3af;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 4px 10px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(16, 185, 129, 0.15);
                color: #6ee7b7;
                border-color: #10b981;
            }
        """)
        btn_tab_editor.clicked.connect(self.open_sector2_editor_view)
        nav.addWidget(btn_tab_editor)

        btn_tab_venv = QPushButton("🐍  Entorno Python")
        btn_tab_venv.setCursor(Qt.PointingHandCursor)
        btn_tab_venv.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: #9ca3af;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 4px 10px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(52, 211, 153, 0.15);
                color: #6ee7b7;
                border-color: #34d399;
            }
        """)
        btn_tab_venv.clicked.connect(self.open_sector2_venv_view)
        nav.addWidget(btn_tab_venv)

        btn_tab_docker = QPushButton("🐳  Docker")
        btn_tab_docker.setCursor(Qt.PointingHandCursor)
        btn_tab_docker.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: #9ca3af;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 4px 10px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(56, 189, 248, 0.15);
                color: #38bdf8;
                border-color: #38bdf8;
            }
        """)
        btn_tab_docker.clicked.connect(self.open_sector2_docker_view)
        nav.addWidget(btn_tab_docker)

        btn_tab_ports = QPushButton("🔌  Puertos TCP")
        btn_tab_ports.setCursor(Qt.PointingHandCursor)
        btn_tab_ports.setStyleSheet("""
            QPushButton {
                background-color: rgba(251, 191, 36, 0.25);
                color: #ffffff;
                border: 1px solid #fbbf24;
                border-radius: 6px;
                padding: 4px 10px;
                font-weight: 800;
                font-size: 11px;
            }
        """)
        nav.addWidget(btn_tab_ports)

        nav.addStretch()

        btn_refresh = QPushButton("🔄  Escanear Puertos")
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: #e5e7eb;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                padding: 5px 10px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.12);
                color: #ffffff;
            }
        """)
        btn_refresh.clicked.connect(self.refresh_sector2_ports_view)
        nav.addWidget(btn_refresh)
        layout.addLayout(nav)

        # Panel de Resumen de Puertos
        self.lbl_s2_ports_summary = QLabel("Puertos TCP Activos: Escaneando...")
        self.lbl_s2_ports_summary.setStyleSheet("font-size: 11.5px; font-weight: 700; color: #fbbf24; padding: 4px 0;")
        layout.addWidget(self.lbl_s2_ports_summary)

        # ScrollArea con Lista de Puertos
        scroll_ports = QScrollArea()
        scroll_ports.setWidgetResizable(True)
        scroll_ports.setMinimumHeight(180)
        scroll_ports.setMaximumHeight(260)
        scroll_ports.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        scroll_ports.setStyleSheet("""
            QScrollArea {
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                background-color: rgba(0, 0, 0, 0.20);
            }
        """)

        self.ports_list_widget = QWidget()
        self.ports_list_layout = QVBoxLayout(self.ports_list_widget)
        self.ports_list_layout.setContentsMargins(6, 6, 6, 6)
        self.ports_list_layout.setSpacing(6)
        scroll_ports.setWidget(self.ports_list_widget)

        layout.addWidget(scroll_ports, 1)
        return page

    # =================================================================
    # MÉTODOS DE ACCIÓN Y APERTURA DE DOCKER Y PUERTOS
    # =================================================================
    def open_sector2_docker_view(self):
        """Abre la sub-página de control de Docker y refresca contenedores."""
        self.dock_terminal_in_docker()
        self.sectors_stack.setCurrentIndex(2)
        if hasattr(self, "sector2_sub_stack"):
            self.sector2_sub_stack.setCurrentIndex(2)
            self.sector2_sub_stack.updateGeometry()
        if hasattr(self, "sectors_stack"):
            self.sectors_stack.updateGeometry()
        self.refresh_sector2_docker_view()
        p_name = self.project_data.get("name", "Proyecto")
        self.terminal_display.log("DOCKER", f"Panel de Control Docker & Compose abierto para <b>{p_name}</b>.", tag_color="#38bdf8", prefix="🐳")

    def open_sector2_ports_view(self):
        """Abre la sub-página de auditoría de puertos TCP."""
        self.dock_terminal_at_bottom()
        self.sectors_stack.setCurrentIndex(2)
        if hasattr(self, "sector2_sub_stack"):
            self.sector2_sub_stack.setCurrentIndex(3)
            self.sector2_sub_stack.updateGeometry()
        if hasattr(self, "sectors_stack"):
            self.sectors_stack.updateGeometry()
        self.refresh_sector2_ports_view()
        self.terminal_display.log("PORTS", "Monitor de Puertos TCP y Procesos en Escucha abierto.", tag_color="#fbbf24", prefix="🔌")

    def refresh_sector2_docker_view(self):
        """Inspecciona Docker, descubre compose/Dockerfile recursivamente y lista contenedores."""
        path = self.project_data.get("path", "")
        status = inspect_docker_status(path)

        # --- Telemetría del Demonio ---
        if not status["installed"]:
            self.lbl_s2_docker_status.setText("Docker: ❌ No instalado en el sistema")
            self.lbl_s2_docker_details.setText("Instala 'docker' o 'docker.io' para habilitar la orquestación de contenedores.")
        elif not status["daemon_running"]:
            self.lbl_s2_docker_status.setText("Docker: 🔴 Demonio Inactivo / Sin Permisos")
            self.lbl_s2_docker_details.setText("Ejecuta 'sudo systemctl start docker' o añade tu usuario al grupo docker.")
        else:
            self.lbl_s2_docker_status.setText("Docker: 🟢 Demonio Activo y Operativo")
            deep = status.get("deep_scan", {})
            n_compose = len(deep.get("compose_files", []))
            n_docker = len(deep.get("dockerfiles", []))
            comp_str = ", ".join(status["compose_files"]) if status["compose_files"] else "Ninguno"
            self.lbl_s2_docker_details.setText(
                f"Compose: <b>{comp_str}</b>  |  "
                f"Dockerfiles: {n_docker}  |  Compose Files: {n_compose}"
            )

        # --- Estado Compose Tool ---
        _, tool_name = detect_compose_tool()
        tool_labels = {
            "docker-compose-v2": "✅ docker compose (plugin v2)",
            "docker-compose-v1": "✅ docker-compose (standalone v1)",
            "podman-compose": "✅ podman-compose",
            "none": "⚠️ No disponible (instala docker-compose o habilita el plugin compose)"
        }
        if hasattr(self, "lbl_s2_compose_tool"):
            self.lbl_s2_compose_tool.setText(f"Herramienta Compose: {tool_labels.get(tool_name, '?')}")

        # --- Limpiar contenido previo ---
        while self.docker_containers_layout.count():
            item = self.docker_containers_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not status.get("installed"):
            return

        if not status["daemon_running"]:
            lbl_warn = QLabel("⚠️ El servicio Docker no está respondiendo. Inicia el demonio para visualizar contenedores.")
            lbl_warn.setStyleSheet("color: #f87171; font-weight: 700; padding: 12px;")
            self.docker_containers_layout.addWidget(lbl_warn)
            return

        deep = status.get("deep_scan", {})

        # ===== SECCIÓN: COMPOSE STACKS DESCUBIERTOS =====
        compose_files = deep.get("compose_files", [])
        if compose_files:
            lbl_section_compose = QLabel(f"🐙  COMPOSE STACKS DESCUBIERTOS ({len(compose_files)})")
            lbl_section_compose.setStyleSheet("font-size: 12px; font-weight: 900; color: #a78bfa; padding: 6px 0 2px 4px;")
            self.docker_containers_layout.addWidget(lbl_section_compose)

            for cf in compose_files:
                compose_card = QFrame()
                compose_card.setStyleSheet("""
                    QFrame {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                            stop:0 rgba(167, 139, 250, 0.08), stop:1 rgba(56, 189, 248, 0.05));
                        border: 1px solid rgba(167, 139, 250, 0.25);
                        border-left: 3px solid #a78bfa;
                        border-radius: 8px;
                    }
                """)
                cc_lay = QVBoxLayout(compose_card)
                cc_lay.setContentsMargins(12, 10, 12, 10)
                cc_lay.setSpacing(6)

                # Header del compose file
                header_row = QHBoxLayout()
                lbl_cf_icon = QLabel("📄")
                lbl_cf_icon.setStyleSheet("font-size: 16px;")
                header_row.addWidget(lbl_cf_icon)

                lbl_cf_path = QLabel(f"<b>{cf['relative']}</b>")
                lbl_cf_path.setStyleSheet("font-size: 12px; font-weight: 800; color: #e9d5ff;")
                header_row.addWidget(lbl_cf_path)

                lbl_cf_dir = QLabel(f"<span style='color: #6b7280;'>en {cf['dir']}</span>")
                lbl_cf_dir.setStyleSheet("font-size: 10px;")
                header_row.addWidget(lbl_cf_dir)
                header_row.addStretch()
                cc_lay.addLayout(header_row)

                # Servicios detectados
                services = cf.get("services", [])
                if services:
                    parsed = parse_compose_file_lightweight(cf["path"])
                    svc_detail_parts = []
                    for svc_name in services:
                        svc_data = parsed.get("services", {}).get(svc_name, {})
                        img = svc_data.get("image") or svc_data.get("build") or "?"
                        ports = svc_data.get("ports", [])
                        port_str = ", ".join(ports[:3]) if ports else "sin puertos"
                        svc_detail_parts.append(f"<b>{svc_name}</b> ({img}) → {port_str}")

                    svc_text = "  •  ".join(svc_detail_parts) if len(svc_detail_parts) <= 4 else "  •  ".join(svc_detail_parts[:4]) + f"  (+{len(svc_detail_parts)-4} más)"
                    lbl_svcs = QLabel(f"Servicios: {svc_text}")
                    lbl_svcs.setStyleSheet("font-size: 10.5px; color: #c4b5fd; padding-left: 4px;")
                    lbl_svcs.setWordWrap(True)
                    cc_lay.addWidget(lbl_svcs)
                else:
                    lbl_no_svc = QLabel("Servicios: <i>No se pudieron parsear</i>")
                    lbl_no_svc.setStyleSheet("font-size: 10.5px; color: #6b7280; font-style: italic;")
                    cc_lay.addWidget(lbl_no_svc)

                # Botones de ciclo de vida compose
                compose_btns_row = QHBoxLayout()
                compose_btns_row.setSpacing(5)

                compose_tool_available = (tool_name != "none")

                compose_actions = [
                    ("🚀 Up",      "compose-up",      "#10b981", "#6ee7b7"),
                    ("🛑 Down",    "compose-down",    "#ef4444", "#fca5a5"),
                    ("⏸ Stop",     "compose-stop",    "#f59e0b", "#fcd34d"),
                    ("🔄 Restart", "compose-restart", "#3b82f6", "#93c5fd"),
                    ("⏯ Pause",    "compose-pause",   "#8b5cf6", "#c4b5fd"),
                    ("▶ Unpause",  "compose-unpause", "#14b8a6", "#5eead4"),
                    ("🔨 Build",   "compose-build",   "#f97316", "#fdba74"),
                    ("📋 Logs",    "compose-logs",    "#6b7280", "#d1d5db"),
                ]
                for btn_text, task_type, accent, text_color in compose_actions:
                    btn = QPushButton(btn_text)
                    btn.setCursor(Qt.PointingHandCursor)
                    btn.setEnabled(compose_tool_available)
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: rgba({self._hex_to_rgba(accent, 0.12)});
                            color: {text_color};
                            border: 1px solid rgba({self._hex_to_rgba(accent, 0.35)});
                            border-radius: 5px;
                            padding: 4px 7px;
                            font-weight: 700;
                            font-size: 10px;
                        }}
                        QPushButton:hover {{
                            background-color: rgba({self._hex_to_rgba(accent, 0.30)});
                            color: #ffffff;
                        }}
                        QPushButton:disabled {{
                            background-color: rgba(255, 255, 255, 0.03);
                            color: #4b5563;
                            border-color: rgba(255, 255, 255, 0.06);
                        }}
                    """)
                    compose_path = cf["path"]
                    if task_type == "compose-logs":
                        btn.clicked.connect(lambda _, cp=compose_path: self.show_compose_logs(cp))
                    else:
                        btn.clicked.connect(lambda _, tt=task_type, cp=compose_path: self.execute_compose_lifecycle(tt, cp))
                    compose_btns_row.addWidget(btn)

                compose_btns_row.addStretch()
                cc_lay.addLayout(compose_btns_row)

                if not compose_tool_available:
                    lbl_no_tool = QLabel("⚠️ Instala docker-compose o habilita el plugin 'compose' para usar estos controles.")
                    lbl_no_tool.setStyleSheet("font-size: 10px; color: #f87171; padding-left: 4px;")
                    cc_lay.addWidget(lbl_no_tool)

                self.docker_containers_layout.addWidget(compose_card)

        # ===== SECCIÓN: DOCKERFILES DESCUBIERTOS =====
        dockerfiles = deep.get("dockerfiles", [])
        if dockerfiles:
            lbl_section_df = QLabel(f"📦  DOCKERFILES DESCUBIERTOS ({len(dockerfiles)})")
            lbl_section_df.setStyleSheet("font-size: 12px; font-weight: 900; color: #60a5fa; padding: 10px 0 2px 4px;")
            self.docker_containers_layout.addWidget(lbl_section_df)

            for df in dockerfiles:
                df_card = QFrame()
                df_card.setStyleSheet("""
                    QFrame {
                        background-color: rgba(96, 165, 250, 0.06);
                        border: 1px solid rgba(96, 165, 250, 0.20);
                        border-radius: 6px;
                    }
                """)
                df_lay = QHBoxLayout(df_card)
                df_lay.setContentsMargins(10, 6, 10, 6)
                df_lay.setSpacing(8)

                lbl_df_ic = QLabel("🐳")
                lbl_df_ic.setStyleSheet("font-size: 14px;")
                df_lay.addWidget(lbl_df_ic)

                lbl_df_path = QLabel(f"<b>{df['relative']}</b>  <span style='color: #6b7280;'>({df['dir']})</span>")
                lbl_df_path.setStyleSheet("font-size: 11px; color: #93c5fd;")
                df_lay.addWidget(lbl_df_path, 1)

                self.docker_containers_layout.addWidget(df_card)

        # ===== SECCIÓN: CONTENEDORES DEL SISTEMA =====
        containers = list_docker_containers()
        lbl_section_ctr = QLabel(f"📦  CONTENEDORES DEL SISTEMA ({len(containers)})")
        lbl_section_ctr.setStyleSheet("font-size: 12px; font-weight: 900; color: #38bdf8; padding: 10px 0 2px 4px;")
        self.docker_containers_layout.addWidget(lbl_section_ctr)

        if not containers:
            lbl_empty = QLabel("ℹ️ No hay contenedores registrados en el sistema (activos o detenidos).")
            lbl_empty.setStyleSheet("color: #9ca3af; font-style: italic; padding: 8px 12px;")
            self.docker_containers_layout.addWidget(lbl_empty)
        else:
            for c in containers:
                card = QFrame()
                card.setStyleSheet("""
                    QFrame {
                        background-color: rgba(255, 255, 255, 0.03);
                        border: 1px solid rgba(255, 255, 255, 0.08);
                        border-radius: 8px;
                    }
                    QFrame:hover {
                        background-color: rgba(255, 255, 255, 0.06);
                        border-color: rgba(56, 189, 248, 0.35);
                    }
                """)
                c_lay = QHBoxLayout(card)
                c_lay.setContentsMargins(12, 8, 12, 8)
                c_lay.setSpacing(10)

                is_running = (c["state"] == "running")
                icon = "🟢" if is_running else "🔴"
                lbl_ic = QLabel(icon)
                lbl_ic.setStyleSheet("font-size: 14px;")
                c_lay.addWidget(lbl_ic)

                info_lay = QVBoxLayout()
                info_lay.setSpacing(1)
                lbl_cname = QLabel(f"{c['name']}  <span style='color: #9ca3af; font-size: 11px;'>({c['image']})</span>")
                lbl_cname.setStyleSheet("font-size: 12px; font-weight: 800; color: #f3f4f6;")
                info_lay.addWidget(lbl_cname)

                lbl_csub = QLabel(f"Estado: {c['status']}  •  Puertos: {c['ports']}")
                lbl_csub.setStyleSheet("font-size: 10.5px; color: #38bdf8;" if is_running else "font-size: 10.5px; color: #9ca3af;")
                info_lay.addWidget(lbl_csub)
                c_lay.addLayout(info_lay, 1)

                # Botones de Acción de Contenedor
                if is_running:
                    btn_stop = QPushButton("🛑 Detener")
                    btn_stop.setCursor(Qt.PointingHandCursor)
                    btn_stop.setStyleSheet("""
                        QPushButton {
                            background-color: rgba(239, 68, 68, 0.15);
                            color: #fca5a5;
                            border: 1px solid rgba(239, 68, 68, 0.35);
                            border-radius: 5px;
                            padding: 4px 8px;
                            font-weight: 700;
                            font-size: 10.5px;
                        }
                        QPushButton:hover { background-color: #ef4444; color: #ffffff; }
                    """)
                    btn_stop.clicked.connect(lambda _, cid=c["name"]: self.execute_docker_container_action("stop", cid))
                    c_lay.addWidget(btn_stop)

                    btn_restart = QPushButton("🔄 Reiniciar")
                    btn_restart.setCursor(Qt.PointingHandCursor)
                    btn_restart.setStyleSheet("""
                        QPushButton {
                            background-color: rgba(56, 189, 248, 0.15);
                            color: #7dd3fc;
                            border: 1px solid rgba(56, 189, 248, 0.35);
                            border-radius: 5px;
                            padding: 4px 8px;
                            font-weight: 700;
                            font-size: 10.5px;
                        }
                        QPushButton:hover { background-color: #0284c7; color: #ffffff; }
                    """)
                    btn_restart.clicked.connect(lambda _, cid=c["name"]: self.execute_docker_container_action("restart", cid))
                    c_lay.addWidget(btn_restart)
                else:
                    btn_start = QPushButton("⚡ Iniciar")
                    btn_start.setCursor(Qt.PointingHandCursor)
                    btn_start.setStyleSheet("""
                        QPushButton {
                            background-color: rgba(16, 185, 129, 0.15);
                            color: #6ee7b7;
                            border: 1px solid rgba(16, 185, 129, 0.35);
                            border-radius: 5px;
                            padding: 4px 8px;
                            font-weight: 700;
                            font-size: 10.5px;
                        }
                        QPushButton:hover { background-color: #10b981; color: #ffffff; }
                    """)
                    btn_start.clicked.connect(lambda _, cid=c["name"]: self.execute_docker_container_action("start", cid))
                    c_lay.addWidget(btn_start)

                # Ver Logs
                btn_logs = QPushButton("📋 Logs")
                btn_logs.setCursor(Qt.PointingHandCursor)
                btn_logs.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(255, 255, 255, 0.05);
                        color: #d1d5db;
                        border: 1px solid rgba(255, 255, 255, 0.15);
                        border-radius: 5px;
                        padding: 4px 8px;
                        font-weight: 600;
                        font-size: 10.5px;
                    }
                    QPushButton:hover { background-color: rgba(255, 255, 255, 0.12); color: #ffffff; }
                """)
                btn_logs.clicked.connect(lambda _, cid=c["name"]: self.show_docker_logs_dialog(cid))
                c_lay.addWidget(btn_logs)

                self.docker_containers_layout.addWidget(card)

        self.docker_containers_layout.addStretch()


    def refresh_sector2_ports_view(self):
        """Escanea los puertos TCP en escucha y actualiza la lista interactiva."""
        ports = inspect_network_ports()
        self.lbl_s2_ports_summary.setText(f"Puertos TCP en escucha detectados ({len(ports)} servicios activos):")

        while self.ports_list_layout.count():
            item = self.ports_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not ports:
            lbl_none = QLabel("ℹ️ No se detectaron puertos TCP en estado LISTEN en este momento.")
            lbl_none.setStyleSheet("color: #9ca3af; font-style: italic; padding: 12px;")
            self.ports_list_layout.addWidget(lbl_none)
            return

        for p in ports:
            card = QFrame()
            card.setStyleSheet("""
                QFrame {
                    background-color: rgba(255, 255, 255, 0.03);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 8px;
                }
                QFrame:hover {
                    background-color: rgba(255, 255, 255, 0.06);
                    border-color: rgba(251, 191, 36, 0.35);
                }
            """)
            p_lay = QHBoxLayout(card)
            p_lay.setContentsMargins(12, 7, 12, 7)
            p_lay.setSpacing(10)

            lbl_ic = QLabel("🔌")
            lbl_ic.setStyleSheet("font-size: 15px;")
            p_lay.addWidget(lbl_ic)

            info_lay = QVBoxLayout()
            info_lay.setSpacing(1)
            lbl_p_info = QLabel(f"<b style='color: #fbbf24; font-size: 12.5px;'>Puerto {p['port']}</b>  ➔  <span style='color: #f3f4f6;'>{p['command']}</span>  <span style='color: #9ca3af; font-size: 11px;'>(PID: {p['pid']})</span>")
            info_lay.addWidget(lbl_p_info)

            lbl_p_addr = QLabel(f"Dirección: {p['address']}  •  Protocolo: {p['protocol']}")
            lbl_p_addr.setStyleSheet("font-size: 10.5px; color: #9ca3af;")
            info_lay.addWidget(lbl_p_addr)
            p_lay.addLayout(info_lay, 1)

            btn_kill = QPushButton("💀 Matar Proceso")
            btn_kill.setCursor(Qt.PointingHandCursor)
            btn_kill.setStyleSheet("""
                QPushButton {
                    background-color: rgba(239, 68, 68, 0.15);
                    color: #fca5a5;
                    border: 1px solid rgba(239, 68, 68, 0.35);
                    border-radius: 5px;
                    padding: 4px 10px;
                    font-weight: 700;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #ef4444;
                    color: #ffffff;
                }
            """)
            btn_kill.clicked.connect(lambda _, pid=str(p["pid"]), cmd=p["command"], port=p["port"]: self.execute_kill_port_process(pid, cmd, port))
            p_lay.addWidget(btn_kill)

            self.ports_list_layout.addWidget(card)

        self.ports_list_layout.addStretch()

    def execute_docker_container_action(self, action: str, container_name: str):
        """Ejecuta una acción de contenedor en segundo plano."""
        act_labels = {"start": "Iniciando", "stop": "Deteniendo", "restart": "Reiniciando", "rm": "Eliminando"}
        self.terminal_display.log("DOCKER", f"{act_labels.get(action, 'Procesando')} contenedor <b>{container_name}</b>...", tag_color="#38bdf8", prefix="⚡")
        self.docker_worker = DockerWorkerThread(action, target=container_name)
        self.docker_worker.finished_task.connect(self.on_docker_worker_finished)
        self.docker_worker.start()

    def execute_docker_system_prune(self):
        """Ejecuta docker system prune en segundo plano con confirmación previa."""
        reply = QMessageBox.question(
            self, "Confirmar Limpieza Docker",
            "¿Deseas purgar contenedores detenidos, redes no usadas e imágenes huérfanas (docker system prune)?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.terminal_display.log_warn("DOCKER", "Ejecutando limpieza de recursos Docker en segundo plano...")
            self.docker_worker = DockerWorkerThread("prune")
            self.docker_worker.finished_task.connect(self.on_docker_worker_finished)
            self.docker_worker.start()

    def show_docker_logs_dialog(self, container_name: str):
        """Muestra los logs del contenedor en la terminal inferior."""
        self.terminal_display.log("DOCKER", f"Obteniendo últimos logs de <b>{container_name}</b>...", tag_color="#38bdf8", prefix="📋")
        ok, logs = get_docker_container_logs(container_name, tail_lines=100)
        if ok:
            for line in logs.splitlines():
                self.terminal_display.log("LOG", line, tag_color="#9ca3af", prefix="•")
        else:
            self.terminal_display.log_error("DOCKER", f"Error al obtener logs: {logs}")

    def execute_kill_port_process(self, pid: str, cmd: str, port: int):
        """Aniquila un proceso ocupando un puerto tras confirmación."""
        reply = QMessageBox.question(
            self, "Confirmar Aniquilación de Proceso",
            f"¿Estás seguro de que deseas aniquilar el proceso '{cmd}' (PID: {pid}) en el puerto {port}?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.terminal_display.log_warn("PORTS", f"Aniquilando proceso <b>{cmd}</b> (PID: {pid}) en puerto {port}...")
            ok, msg = kill_process_by_pid(pid)
            if ok:
                self.terminal_display.log_success("PORTS", msg)
            else:
                self.terminal_display.log_error("PORTS", msg)
            self.refresh_sector2_ports_view()

    def on_docker_worker_finished(self, success: bool, task_name: str, message: str):
        """Callback al terminar una operación de Docker en segundo plano."""
        if success:
            self.terminal_display.log_success(task_name, message)
        else:
            self.terminal_display.log_error(task_name, message)
        self.refresh_sector2_docker_view()

    def _hex_to_rgba(self, hex_code: str, alpha: float) -> str:
        """Convierte código hexadecimal '#RRGGBB' a 'r, g, b, alpha'."""
        h = hex_code.lstrip("#")
        if len(h) == 6:
            r = int(h[0:2], 16)
            g = int(h[2:4], 16)
            b = int(h[4:6], 16)
            return f"{r}, {g}, {b}, {alpha}"
        return f"255, 255, 255, {alpha}"

    def execute_compose_lifecycle(self, task_type: str, compose_path: str, service: str = ""):
        """Ejecuta una acción de ciclo de vida de Docker Compose en segundo plano."""
        action = task_type.replace("compose-", "")
        rel = os.path.basename(compose_path)
        target = f"{rel} [{service}]" if service else rel
        self.terminal_display.log("COMPOSE", f"Ejecutando <b>{action.upper()}</b> en stack <b>{target}</b>...", tag_color="#a78bfa", prefix="🚀")
        self.docker_worker = DockerWorkerThread(task_type, compose_path=compose_path, service=service)
        self.docker_worker.finished_task.connect(self.on_docker_worker_finished)
        self.docker_worker.start()

    def show_compose_logs(self, compose_path: str, service: str = ""):
        """Muestra los logs del stack de Compose en la terminal inferior."""
        rel = os.path.basename(compose_path)
        target = f"{rel} ({service})" if service else rel
        self.terminal_display.log("COMPOSE", f"Obteniendo logs recientes de <b>{target}</b>...", tag_color="#a78bfa", prefix="📋")
        ok, logs = execute_compose_action(compose_path, "logs", service or None)
        if ok:
            for line in logs.splitlines():
                self.terminal_display.log("LOG", line, tag_color="#9ca3af", prefix="•")
        else:
            self.terminal_display.log_error("COMPOSE", f"Error al obtener logs de Compose: {logs}")

    def create_simple_sector_view(self, title: str, accent_color: str, actions: list) -> QFrame:
        """Crea una ventana dedicada y limpia para un sector específico con diseño consistente."""
        card = QFrame()
        card.setProperty("class", "surface")
        card.setStyleSheet(f"""
            QFrame.surface {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(22, 24, 34, 0.95), stop:1 rgba(16, 18, 25, 0.95));
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-top: 3px solid {accent_color};
                border-radius: 10px;
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # Barra superior de navegación del Sector
        nav_bar = QHBoxLayout()
        nav_bar.setSpacing(12)

        btn_back_sec = QPushButton("◀  Volver al Menú de Sectores")
        btn_back_sec.setCursor(Qt.PointingHandCursor)
        btn_back_sec.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.04);
                color: {accent_color};
                border: 1px solid {accent_color};
                border-radius: 6px;
                padding: 5px 12px;
                font-weight: 700;
                font-size: 11.5px;
            }}
            QPushButton:hover {{
                background-color: {accent_color};
                color: #07090e;
            }}
        """)
        btn_back_sec.clicked.connect(self.go_back_to_sectors_overview)
        nav_bar.addWidget(btn_back_sec)

        lbl_sec_title = QLabel(title)
        lbl_sec_title.setStyleSheet(f"font-size: 12.5px; font-weight: 900; color: {accent_color}; letter-spacing: 0.5px;")
        nav_bar.addWidget(lbl_sec_title)

        nav_bar.addStretch()
        layout.addLayout(nav_bar)

        for icon, act_title, act_sub in actions:
            btn = LumenCyberActionButton(icon, act_title, act_sub, accent_color=accent_color)
            btn.clicked.connect(self.handle_action_click)
            layout.addWidget(btn)

        layout.addStretch()
        return card

    # -----------------------------------------------------------------
    # NAVEGACIÓN DENTRO DE SECTORES Y CICLOS DE TRABAJO
    # -----------------------------------------------------------------
    def handle_git_init(self, create_gitignore: bool = True):
        """Inicializa el repositorio Git en el proyecto actual y refresca el workspace."""
        if not self.project_data:
            self.terminal_display.log_error("GIT-INIT", "No hay ningún proyecto activo cargado.")
            return

        p_path = self.project_data.get("path", "")
        p_name = self.project_data.get("name", "Proyecto")

        self.terminal_display.log("GIT-INIT", f"Inicializando repositorio Git para <b>{p_name}</b> (rama <code>main</code>)...", tag_color="#38bdf8", prefix="🌱")

        success, msg = execute_git_init(p_path, initial_branch="main", create_gitignore=create_gitignore)
        if success:
            self.terminal_display.log_success("GIT-INIT", msg)
            if create_gitignore:
                self.terminal_display.log_info("GITIGNORE", "Archivo <code>.gitignore</code> creado con reglas de exclusión base.")
            self.refresh_current_project(reset_terminal=True)
        else:
            self.terminal_display.log_error("GIT-INIT", msg)

    def open_sector_view(self, sector_idx: int, sector_title: str):
        """Abre la ventana limpia dedicada del sector seleccionado."""
        self.dock_terminal_at_bottom()
        if not getattr(self, "is_project_git", True):
            if sector_idx == 1:
                self.terminal_display.log_warn("SECTOR-1", "El <b>Sector 1 (Protocolo Git)</b> no está disponible. Inicia el repositorio Git primero.")
                return
            elif sector_idx == 3:
                self.terminal_display.log_warn("SECTOR-3", "El <b>Sector 3 (Herramientas & IA)</b> está bloqueado. Requiere un repositorio Git inicializado.")
                return

        self.sectors_stack.setCurrentIndex(sector_idx)
        if sector_idx == 1 and hasattr(self, "sector1_sub_stack"):
            self.sector1_sub_stack.setCurrentIndex(0)
        if sector_idx == 2 and hasattr(self, "sector2_sub_stack"):
            self.sector2_sub_stack.setCurrentIndex(0)
        if hasattr(self, "btn_toggle_graph_terminal"):
            self.btn_toggle_graph_terminal.setVisible(False)
        if hasattr(self, "terminal_stack") and self.terminal_stack.currentIndex() == 1:
            self.toggle_terminal_graph_view()
        self.terminal_display.log("NAV", f"Abriendo ventana dedicada de <b>{sector_title}</b>.", tag_color="#38bdf8", prefix="📂")

    def open_sector_and_handle(self, sector_idx: int, sector_title: str, action_title: str):
        """Abre la ventana del sector o ejecuta la acción seleccionada."""
        if not getattr(self, "is_project_git", True):
            if sector_idx in (1, 3):
                self.open_sector_view(sector_idx, sector_title)
                return

        if sector_idx == 1:
            if action_title == "Ciclos de Trabajo":
                self.open_sector_view(1, "Ciclos de Trabajo")
            elif action_title == "Control de Ramas":
                self.open_branches_view()
            elif action_title == "Fusión de Ramas":
                self.open_merge_view()
            elif action_title == "Estado y Sincronización":
                self.open_sync_view()
            elif action_title == "Visibilidad GitHub":
                self.open_visibility_dialog()
            else:
                self.handle_action_click(action_title)
        elif sector_idx == 2:
            act_lower = action_title.lower()
            if "editor" in act_lower:
                self.open_sector2_editor_view()
            elif "python" in act_lower or "venv" in act_lower:
                self.open_sector2_venv_view()
            elif "puerto" in act_lower and "docker" not in act_lower:
                self.open_sector2_ports_view()
            elif "docker" in act_lower or "puerto" in act_lower:
                self.open_sector2_docker_view()
            else:
                self.open_sector_view(2, "Sector 2: Entornos & Run")
        else:
            self.open_sector_view(sector_idx, sector_title)
            self.handle_action_click(action_title)

    def open_visibility_dialog(self):
        """Abre el diálogo modal para gestionar la visibilidad (Público/Privado) o publicar en GitHub."""
        path = self.project_data.get("path")
        name = self.project_data.get("name")
        if not path or not os.path.exists(path):
            self.terminal_display.log_warn("GITHUB", "Ruta de proyecto no válida para gestionar visibilidad.")
            return

        dlg = LumenRepoVisibilityDialog(path, name, parent=self)
        if dlg.exec():
            res_msg = getattr(dlg, "result_message", "Operación de visibilidad completada.")
            self.terminal_display.log("GITHUB", f"<b>Visibilidad en GitHub:</b> {res_msg}", tag_color="#34d399", prefix="🌐")
            self.refresh_current_project(reset_terminal=False)

    def open_sync_view(self):
        """Abre la vista dedicada de Estado y Sincronización (Status / Fetch / Pull) en el Sector 1."""
        self.sectors_stack.setCurrentIndex(1)
        self.sector1_sub_stack.setCurrentWidget(self.page_sync)
        self.terminal_display.log("NAV", "Accediendo al módulo <b>Estado y Sincronización (Status • Fetch • Pull)</b>...", tag_color="#34d399", prefix="⚡")
        self.refresh_sync_view()
        self.refresh_git_graph()
        if hasattr(self, "btn_toggle_graph_terminal"):
            self.btn_toggle_graph_terminal.setVisible(True)
        if hasattr(self, "terminal_stack") and self.terminal_stack.currentIndex() == 0:
            self.toggle_terminal_graph_view()
        self.sector1_sub_stack.updateGeometry()
        self.sectors_stack.updateGeometry()

    def open_branches_view(self):
        """Abre la vista dedicada de Control de Ramas en el Sector 1."""
        self.sectors_stack.setCurrentIndex(1)
        self.sector1_sub_stack.setCurrentWidget(self.page_branches)
        self.terminal_display.log("NAV", "Accediendo al módulo <b>Control de Ramas</b>...", tag_color="#38bdf8", prefix="🌿")
        self.refresh_branches_list()
        self.refresh_git_graph()
        if hasattr(self, "btn_toggle_graph_terminal"):
            self.btn_toggle_graph_terminal.setVisible(True)
        if hasattr(self, "terminal_stack") and self.terminal_stack.currentIndex() == 0:
            self.toggle_terminal_graph_view()
        self.sector1_sub_stack.updateGeometry()
        self.sectors_stack.updateGeometry()

    def open_merge_view(self):
        """Abre la vista dedicada de Fusión de Ramas (Git Merge) en el Sector 1."""
        self.sectors_stack.setCurrentIndex(1)
        self.sector1_sub_stack.setCurrentWidget(self.page_merge)
        self.terminal_display.log("NAV", "Accediendo al módulo <b>Fusión de Ramas (Git Merge)</b>...", tag_color="#38bdf8", prefix="🔀")
        self.refresh_merge_view()
        self.refresh_git_graph()
        if hasattr(self, "btn_toggle_graph_terminal"):
            self.btn_toggle_graph_terminal.setVisible(True)
        if hasattr(self, "terminal_stack") and self.terminal_stack.currentIndex() == 0:
            self.toggle_terminal_graph_view()
        self.sector1_sub_stack.updateGeometry()
        self.sectors_stack.updateGeometry()

    def refresh_branches_list(self):
        """Consulta y renderiza en vivo la matriz de ramas."""
        path = self.project_data.get("path")
        if not path or not os.path.exists(path):
            return

        # Limpiar lista anterior
        while self.branches_list_layout.count():
            item = self.branches_list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            elif item.layout():
                sub_lay = item.layout()
                while sub_lay.count():
                    sub_item = sub_lay.takeAt(0)
                    if sub_item.widget():
                        sub_item.widget().deleteLater()

        matrix = get_git_branches_matrix(path)
        branches = matrix.get("branches", [])
        curr_b = matrix.get("current_branch", "")
        undeployed = matrix.get("undeployed", [])

        self.lbl_branch_count_info.setText(f"Ramas: {len(branches)} | Activa: {curr_b}")

        # Poblar lista de ramas
        for b in branches:
            row_frame = QFrame()
            is_active = b["is_active"]
            accent = b["color"]

            row_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {"rgba(56, 189, 248, 0.08)" if is_active else "rgba(255, 255, 255, 0.02)"};
                    border: 1px solid {"rgba(56, 189, 248, 0.40)" if is_active else "rgba(255, 255, 255, 0.06)"};
                    border-radius: 6px;
                    padding: 5px 10px;
                }}
                QFrame:hover {{
                    background-color: rgba(255, 255, 255, 0.05);
                    border-color: {accent};
                }}
            """)
            r_lay = QHBoxLayout(row_frame)
            r_lay.setContentsMargins(8, 4, 8, 4)
            r_lay.setSpacing(10)

            # Símbolo / Indicador
            lbl_dot = QLabel("★" if is_active else "◈")
            lbl_dot.setStyleSheet(f"color: {accent}; font-size: 13px; font-weight: 800; min-width: 14px;")
            r_lay.addWidget(lbl_dot)

            # Nombre de la rama
            lbl_name = QLabel(b["name"])
            lbl_name.setStyleSheet(f"font-size: 12.5px; font-weight: 800; color: {accent}; min-width: 150px;")
            r_lay.addWidget(lbl_name, 1)

            # Autor
            lbl_author = QLabel(f"👤 {b['author']}")
            lbl_author.setStyleSheet("font-size: 11.5px; color: #9ca3af; min-width: 90px;")
            r_lay.addWidget(lbl_author)

            # Fecha
            lbl_date = QLabel(f"⏱ {b['date']}")
            lbl_date.setStyleSheet("font-size: 11px; color: #6b7280; min-width: 90px;")
            r_lay.addWidget(lbl_date)

            # Etiqueta de Estado
            lbl_st = QLabel(b["status_label"])
            lbl_st.setStyleSheet(f"""
                font-size: 10.5px;
                font-weight: 700;
                color: {accent};
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid {accent};
                border-radius: 4px;
                padding: 2px 7px;
            """)
            r_lay.addWidget(lbl_st)

            # Acción
            if is_active:
                lbl_act = QLabel("✔ ACTIVA")
                lbl_act.setStyleSheet("font-size: 10.5px; font-weight: 900; color: #34d399; padding: 3px 8px;")
                r_lay.addWidget(lbl_act)
            else:
                btn_checkout = QPushButton("🔀 Checkout")
                btn_checkout.setCursor(Qt.PointingHandCursor)
                btn_checkout.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(56, 189, 248, 0.15);
                        color: #7dd3fc;
                        border: 1px solid rgba(56, 189, 248, 0.40);
                        border-radius: 4px;
                        padding: 3px 10px;
                        font-weight: 700;
                        font-size: 11px;
                    }
                    QPushButton:hover {
                        background-color: rgba(56, 189, 248, 0.35);
                        border-color: #38bdf8;
                        color: #ffffff;
                    }
                """)
                btn_checkout.clicked.connect(lambda checked=False, n=b["name"]: self.do_branch_checkout(n))
                r_lay.addWidget(btn_checkout)

            self.branches_list_layout.addWidget(row_frame)

        self.branches_list_layout.addStretch()

        # Actualizar opciones de borrado (solo locales no activas)
        self.cmb_del_branch.clear()
        local_deletable = [b["name"] for b in branches if not b["is_remote"] and not b["is_active"]]
        if local_deletable:
            for b_name in local_deletable:
                self.cmb_del_branch.addItem(b_name)
        else:
            self.cmb_del_branch.addItem("(Sin ramas para borrar)")

        # Actualizar opciones de despliegue
        self.cmb_deploy_branch.clear()
        if undeployed:
            for u in undeployed:
                self.cmb_deploy_branch.addItem(u)
        else:
            self.cmb_deploy_branch.addItem("(Sin ramas pendientes)")

    def do_branch_checkout(self, branch_name: str):
        """Ejecuta el checkout hacia la rama solicitada."""
        path = self.project_data.get("path")
        if not path:
            return

        self.terminal_display.log("BRANCH-CHECKOUT", f"Ejecutando checkout hacia <b>{branch_name}</b>...", tag_color="#38bdf8", prefix="🔀")
        ok, msg = execute_git_checkout(path, branch_name)
        if ok:
            self.terminal_display.log_success("BRANCH-CHECKOUT", f"Conmutación exitosa a la rama <b>{branch_name}</b>.")
            if msg:
                self.terminal_display.log("GIT", msg, tag_color="#38bdf8", prefix="•")
            self.refresh_current_project(reset_terminal=False)
            self.refresh_branches_list()
        else:
            self.terminal_display.log_error("BRANCH-CHECKOUT", f"Fallo al cambiar de rama: {msg}")

    def hide_branches_action_drawer(self):
        """Oculta el cajón de acciones y recalcula la geometría dinámica del stack."""
        if hasattr(self, "branches_action_drawer"):
            self.branches_action_drawer.setVisible(False)
        if hasattr(self, "sector1_sub_stack"):
            self.sector1_sub_stack.updateGeometry()
        if hasattr(self, "sectors_stack"):
            self.sectors_stack.updateGeometry()

    def show_create_branch_drawer(self):
        """Muestra el cajón de creación de nueva rama."""
        self.branches_action_drawer.setCurrentIndex(0)
        self.branches_action_drawer.setVisible(True)
        if hasattr(self, "sector1_sub_stack"):
            self.sector1_sub_stack.updateGeometry()
        if hasattr(self, "sectors_stack"):
            self.sectors_stack.updateGeometry()
        self.txt_new_branch_name.setFocus()

    def execute_create_branch_action(self):
        """Crea una nueva rama táctica y conmuta a ella."""
        path = self.project_data.get("path")
        name = self.txt_new_branch_name.text().strip()
        if not path or not name:
            self.terminal_display.log_error("BRANCH-CREATE", "El nombre de la nueva rama no puede estar vacío.")
            return

        self.terminal_display.log("BRANCH-CREATE", f"Creando y conmutando a nueva rama <b>{name}</b>...", tag_color="#34d399", prefix="➕")
        ok, msg = execute_git_create_branch(path, name)
        if ok:
            self.terminal_display.log_success("BRANCH-CREATE", f"Rama <b>{name}</b> creada y activada correctamente.")
            self.txt_new_branch_name.clear()
            self.hide_branches_action_drawer()
            self.refresh_current_project(reset_terminal=False)
            self.refresh_branches_list()
        else:
            self.terminal_display.log_error("BRANCH-CREATE", f"Fallo al crear rama: {msg}")

    def show_delete_branch_drawer(self):
        """Muestra el cajón para eliminar ramas locales."""
        cur = self.cmb_del_branch.currentText().strip()
        if not cur or cur.startswith("("):
            self.terminal_display.log("BRANCH-DELETE", "ℹ️ No hay otras ramas locales que se puedan eliminar.", tag_color="#fbbf24", prefix="⚠️")
            return
        self.branches_action_drawer.setCurrentIndex(1)
        self.branches_action_drawer.setVisible(True)
        if hasattr(self, "sector1_sub_stack"):
            self.sector1_sub_stack.updateGeometry()
        if hasattr(self, "sectors_stack"):
            self.sectors_stack.updateGeometry()

    def execute_delete_branch_action(self):
        """Elimina la rama local seleccionada."""
        path = self.project_data.get("path")
        target = self.cmb_del_branch.currentText().strip()
        if not path or not target or target.startswith("("):
            return

        force = self.chk_del_force.isChecked()
        flag_str = " (forzado -D)" if force else " (-d)"
        self.terminal_display.log("BRANCH-DELETE", f"Eliminando rama local <b>{target}</b>{flag_str}...", tag_color="#f87171", prefix="🗑️")
        ok, msg = execute_git_delete_branch(path, target, force=force)
        if ok:
            self.terminal_display.log_success("BRANCH-DELETE", f"Rama <b>{target}</b> eliminada exitosamente.")
            self.hide_branches_action_drawer()
            self.refresh_current_project(reset_terminal=False)
            self.refresh_branches_list()
        else:
            tip = "\nTip: Puedes marcar la casilla 'Forzar eliminación (-D)' si la rama no ha sido fusionada aún." if not force else ""
            self.terminal_display.log_error("BRANCH-DELETE", f"Fallo al eliminar rama '{target}':\n{msg}{tip}")

    def show_deploy_branch_drawer(self):
        """Muestra el cajón para desplegar ramas locales al remoto."""
        cur = self.cmb_deploy_branch.currentText().strip()
        if not cur or cur.startswith("("):
            self.terminal_display.log("BRANCH-DEPLOY", "✅ Todas las ramas locales ya están sincronizadas con el remoto.", tag_color="#34d399", prefix="✔")
            return
        self.branches_action_drawer.setCurrentIndex(2)
        self.branches_action_drawer.setVisible(True)
        if hasattr(self, "sector1_sub_stack"):
            self.sector1_sub_stack.updateGeometry()
        if hasattr(self, "sectors_stack"):
            self.sectors_stack.updateGeometry()

    def execute_deploy_branch_action(self):
        """Despliega la rama local seleccionada al remoto origin."""
        path = self.project_data.get("path")
        target = self.cmb_deploy_branch.currentText().strip()
        if not path or not target or target.startswith("("):
            return

        self.terminal_display.log("BRANCH-DEPLOY", f"Desplegando rama <b>{target}</b> a origin (git push -u)...", tag_color="#60a5fa", prefix="🚀")
        ok, msg = execute_git_deploy_branch(path, target)
        if ok:
            self.terminal_display.log_success("BRANCH-DEPLOY", f"Rama <b>{target}</b> desplegada con éxito en origin.")
            self.hide_branches_action_drawer()
            self.refresh_current_project(reset_terminal=False)
            self.refresh_branches_list()
        else:
            self.terminal_display.log_error("BRANCH-DEPLOY", f"Fallo al desplegar rama '{target}':\n{msg}")

    # -----------------------------------------------------------------
    # MÓDULO 3: FUSIÓN TÁCTICA DE RAMAS (GIT MERGE)
    # -----------------------------------------------------------------
    def create_sector1_merge_view(self) -> QWidget:
        """Crea la sub-página dedicada para la Fusión Táctica de Ramas (Git Merge)."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 1. Cabecera de Navegación del Módulo 3
        head = QHBoxLayout()
        head.setSpacing(10)

        btn_back_main = QPushButton("◀  Volver al Menú de Sectores")
        btn_back_main.setCursor(Qt.PointingHandCursor)
        btn_back_main.setStyleSheet("""
            QPushButton {
                background-color: rgba(56, 189, 248, 0.15);
                color: #bae6fd;
                border: 1px solid rgba(56, 189, 248, 0.40);
                border-radius: 6px;
                padding: 5px 12px;
                font-weight: 700;
                font-size: 11.5px;
            }
            QPushButton:hover {
                background-color: rgba(56, 189, 248, 0.30);
                border-color: #38bdf8;
                color: #ffffff;
            }
        """)
        btn_back_main.clicked.connect(self.go_back_to_sectors_overview)
        head.addWidget(btn_back_main)

        btn_to_work = QPushButton("🔄  Ciclos de Trabajo")
        btn_to_work.setCursor(Qt.PointingHandCursor)
        btn_to_work.setStyleSheet("""
            QPushButton {
                background-color: rgba(99, 102, 241, 0.15);
                color: #c7d2fe;
                border: 1px solid rgba(99, 102, 241, 0.40);
                border-radius: 6px;
                padding: 5px 12px;
                font-weight: 700;
                font-size: 11.5px;
            }
            QPushButton:hover {
                background-color: rgba(99, 102, 241, 0.30);
                border-color: #818cf8;
                color: #ffffff;
            }
        """)
        btn_to_work.clicked.connect(self.go_back_to_work_cycles)
        head.addWidget(btn_to_work)

        btn_to_branches = QPushButton("🌿  Control de Ramas")
        btn_to_branches.setCursor(Qt.PointingHandCursor)
        btn_to_branches.setStyleSheet("""
            QPushButton {
                background-color: rgba(52, 211, 153, 0.15);
                color: #6ee7b7;
                border: 1px solid rgba(52, 211, 153, 0.40);
                border-radius: 6px;
                padding: 5px 12px;
                font-weight: 700;
                font-size: 11.5px;
            }
            QPushButton:hover {
                background-color: rgba(52, 211, 153, 0.30);
                border-color: #34d399;
                color: #ffffff;
            }
        """)
        btn_to_branches.clicked.connect(self.open_branches_view)
        head.addWidget(btn_to_branches)

        btn_to_sync = QPushButton("⚡  Estado y Sync")
        btn_to_sync.setCursor(Qt.PointingHandCursor)
        btn_to_sync.setStyleSheet("""
            QPushButton {
                background-color: rgba(52, 211, 153, 0.15);
                color: #6ee7b7;
                border: 1px solid rgba(52, 211, 153, 0.40);
                border-radius: 6px;
                padding: 5px 12px;
                font-weight: 700;
                font-size: 11.5px;
            }
            QPushButton:hover {
                background-color: rgba(52, 211, 153, 0.30);
                border-color: #34d399;
                color: #ffffff;
            }
        """)
        btn_to_sync.clicked.connect(self.open_sync_view)
        head.addWidget(btn_to_sync)

        lbl_title = QLabel("🔀  FUSIÓN DE RAMAS (GIT MERGE)")
        lbl_title.setStyleSheet("font-size: 12.5px; font-weight: 900; color: #38bdf8; letter-spacing: 0.5px;")
        head.addWidget(lbl_title)
        head.addStretch()

        btn_toggle_graph = QPushButton("📊  Alternar Grafo / Terminal")
        btn_toggle_graph.setCursor(Qt.PointingHandCursor)
        btn_toggle_graph.setStyleSheet("""
            QPushButton {
                background-color: rgba(56, 189, 248, 0.12);
                color: #7dd3fc;
                border: 1px solid rgba(56, 189, 248, 0.35);
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: rgba(56, 189, 248, 0.25);
                color: #ffffff;
            }
        """)
        btn_toggle_graph.clicked.connect(self.toggle_terminal_graph_view)
        head.addWidget(btn_toggle_graph)

        lbl_pill = QLabel("[LUMEN • INTEGRACIÓN TÁCTICA]")
        lbl_pill.setFixedHeight(24)
        lbl_pill.setAlignment(Qt.AlignCenter)
        lbl_pill.setStyleSheet("font-size: 10px; font-weight: 800; color: #38bdf8; background-color: rgba(56, 189, 248, 0.12); border: 1px solid rgba(56, 189, 248, 0.35); border-radius: 4px; padding: 2px 8px;")
        head.addWidget(lbl_pill)
        layout.addLayout(head)

        # 2. Barra HUD de Estado de Fusión
        hud_frame = QFrame()
        hud_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.07);
                border-radius: 6px;
                padding: 6px 12px;
            }
        """)
        h_lay = QHBoxLayout(hud_frame)
        h_lay.setContentsMargins(10, 6, 10, 6)
        h_lay.setSpacing(12)

        self.lbl_merge_dest_info = QLabel("📤 Rama Activa a Integrar (Origen): main • Autor: silvynth")
        self.lbl_merge_dest_info.setStyleSheet("font-size: 11.5px; font-weight: 800; color: #f3f4f6;")
        h_lay.addWidget(self.lbl_merge_dest_info)

        self.btn_switch_dest = QPushButton("🔄 Conmutar Rama Activa")
        self.btn_switch_dest.setCursor(Qt.PointingHandCursor)
        self.btn_switch_dest.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.04);
                color: #9ca3af;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                color: #38bdf8;
                border-color: #38bdf8;
                background-color: rgba(56, 189, 248, 0.10);
            }
        """)
        self.btn_switch_dest.clicked.connect(self.toggle_switch_dest_drawer)
        h_lay.addWidget(self.btn_switch_dest)

        h_lay.addStretch()

        self.lbl_merge_status_badge = QLabel("✔ ESTADO: LISTO PARA INTEGRACIÓN")
        self.lbl_merge_status_badge.setStyleSheet("font-size: 10.5px; font-weight: 800; color: #34d399; background-color: rgba(52, 211, 153, 0.12); border: 1px solid rgba(52, 211, 153, 0.35); border-radius: 4px; padding: 2px 8px;")
        h_lay.addWidget(self.lbl_merge_status_badge)
        layout.addWidget(hud_frame)

        # Cajón desplegable para cambiar rama destino (checkout)
        self.drawer_switch_dest = QFrame()
        self.drawer_switch_dest.setVisible(False)
        self.drawer_switch_dest.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(56, 189, 248, 0.30);
                border-radius: 6px;
                padding: 8px 12px;
            }
        """)
        sw_lay = QHBoxLayout(self.drawer_switch_dest)
        sw_lay.setContentsMargins(8, 4, 8, 4)
        sw_lay.setSpacing(10)

        lbl_sw = QLabel("Seleccionar nueva rama destino (receptora):")
        lbl_sw.setStyleSheet("font-size: 11.5px; color: #9ca3af; font-weight: 700;")
        sw_lay.addWidget(lbl_sw)

        self.cmb_switch_dest = QComboBox()
        self.cmb_switch_dest.setItemDelegate(QStyledItemDelegate())
        self.cmb_switch_dest.setStyleSheet("""
            QComboBox {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 4px;
                color: #f3f4f6;
                padding: 4px 10px;
                font-size: 11.5px;
            }
        """)
        sw_lay.addWidget(self.cmb_switch_dest, 1)

        btn_confirm_switch = QPushButton("Cambiar Rama (Checkout)")
        btn_confirm_switch.setCursor(Qt.PointingHandCursor)
        btn_confirm_switch.setStyleSheet("""
            QPushButton {
                background-color: rgba(56, 189, 248, 0.20);
                color: #38bdf8;
                border: 1px solid #38bdf8;
                border-radius: 4px;
                padding: 4px 12px;
                font-weight: 700;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(56, 189, 248, 0.35);
                color: #ffffff;
            }
        """)
        btn_confirm_switch.clicked.connect(self.execute_switch_dest_checkout)
        sw_lay.addWidget(btn_confirm_switch)

        btn_cancel_sw = QPushButton("Cerrar")
        btn_cancel_sw.setCursor(Qt.PointingHandCursor)
        btn_cancel_sw.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: #9ca3af;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 11px;
            }
        """)
        btn_cancel_sw.clicked.connect(lambda: self.drawer_switch_dest.setVisible(False))
        sw_lay.addWidget(btn_cancel_sw)
        layout.addWidget(self.drawer_switch_dest)

        # 3. Dynamic Stack Interno de Fusión
        self.merge_inner_stack = LumenDynamicStackedWidget()

        # =============================================================
        # PÁGINA 0: DASHBOARD / SELECTOR DE RAMA ORIGEN
        # =============================================================
        p_select = QWidget()
        p0_lay = QVBoxLayout(p_select)
        p0_lay.setContentsMargins(0, 0, 0, 0)
        p0_lay.setSpacing(8)

        # Banner de fusión activa o de emergencia si aplica
        self.frame_active_merge_alert = QFrame()
        self.frame_active_merge_alert.setVisible(False)
        self.frame_active_merge_alert.setStyleSheet("""
            QFrame {
                background-color: rgba(248, 113, 113, 0.08);
                border: 1px solid rgba(248, 113, 113, 0.40);
                border-radius: 6px;
                padding: 8px 12px;
            }
        """)
        f_ama_lay = QVBoxLayout(self.frame_active_merge_alert)
        f_ama_lay.setContentsMargins(8, 6, 8, 6)
        f_ama_lay.setSpacing(6)

        self.lbl_active_merge_msg = QLabel("⚠️ FUSIÓN EN CURSO DETECTADA")
        self.lbl_active_merge_msg.setStyleSheet("font-size: 12px; font-weight: 800; color: #f87171;")
        f_ama_lay.addWidget(self.lbl_active_merge_msg)

        self.lbl_conflicts_list = QLabel("")
        self.lbl_conflicts_list.setStyleSheet("font-size: 11px; color: #fca5a5; font-family: monospace;")
        f_ama_lay.addWidget(self.lbl_conflicts_list)

        row_ama_btns = QHBoxLayout()
        row_ama_btns.setSpacing(8)

        btn_ama_abort = QPushButton("💥 Abortar Fusión (--abort)")
        btn_ama_abort.setCursor(Qt.PointingHandCursor)
        btn_ama_abort.setStyleSheet("""
            QPushButton {
                background-color: rgba(248, 113, 113, 0.20);
                color: #fca5a5;
                border: 1px solid #f87171;
                border-radius: 4px;
                padding: 5px 12px;
                font-weight: 700;
                font-size: 11px;
            }
            QPushButton:hover { background-color: rgba(248, 113, 113, 0.35); color: #ffffff; }
        """)
        btn_ama_abort.clicked.connect(self.do_merge_abort)
        row_ama_btns.addWidget(btn_ama_abort)

        btn_ama_ours = QPushButton("🛡️ Resolver con NUESTRAS (ours)")
        btn_ama_ours.setCursor(Qt.PointingHandCursor)
        btn_ama_ours.setStyleSheet("""
            QPushButton {
                background-color: rgba(251, 191, 36, 0.15);
                color: #fde047;
                border: 1px solid rgba(251, 191, 36, 0.40);
                border-radius: 4px;
                padding: 5px 12px;
                font-weight: 700;
                font-size: 11px;
            }
            QPushButton:hover { background-color: rgba(251, 191, 36, 0.30); color: #ffffff; }
        """)
        btn_ama_ours.clicked.connect(lambda: self.do_merge_resolve_conflicts("ours"))
        row_ama_btns.addWidget(btn_ama_ours)

        btn_ama_theirs = QPushButton("⚔️ Resolver con SUS (theirs)")
        btn_ama_theirs.setCursor(Qt.PointingHandCursor)
        btn_ama_theirs.setStyleSheet("""
            QPushButton {
                background-color: rgba(99, 102, 241, 0.15);
                color: #c7d2fe;
                border: 1px solid rgba(99, 102, 241, 0.40);
                border-radius: 4px;
                padding: 5px 12px;
                font-weight: 700;
                font-size: 11px;
            }
            QPushButton:hover { background-color: rgba(99, 102, 241, 0.30); color: #ffffff; }
        """)
        btn_ama_theirs.clicked.connect(lambda: self.do_merge_resolve_conflicts("theirs"))
        row_ama_btns.addWidget(btn_ama_theirs)

        self.btn_ama_complete = QPushButton("💾 Completar Fusión")
        self.btn_ama_complete.setCursor(Qt.PointingHandCursor)
        self.btn_ama_complete.setStyleSheet("""
            QPushButton {
                background-color: rgba(52, 211, 153, 0.20);
                color: #6ee7b7;
                border: 1px solid #34d399;
                border-radius: 4px;
                padding: 5px 12px;
                font-weight: 700;
                font-size: 11px;
            }
            QPushButton:hover { background-color: rgba(52, 211, 153, 0.35); color: #ffffff; }
        """)
        self.btn_ama_complete.clicked.connect(self.prepare_complete_active_merge)
        row_ama_btns.addWidget(self.btn_ama_complete)
        row_ama_btns.addStretch()

        f_ama_lay.addLayout(row_ama_btns)
        p0_lay.addWidget(self.frame_active_merge_alert)

        # Título de la lista
        self.lbl_p0_desc = QLabel("Selecciona la RAMA DESTINO donde deseas integrar los cambios de la rama activa:")
        self.lbl_p0_desc.setStyleSheet("font-size: 11.5px; color: #9ca3af; font-weight: 600;")
        p0_lay.addWidget(self.lbl_p0_desc)

        # Scroll de ramas mergeables
        scroll_merge = QScrollArea()
        scroll_merge.setWidgetResizable(True)
        scroll_merge.setMinimumHeight(200)
        scroll_merge.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll_merge_content = QWidget()
        scroll_merge_content.setStyleSheet("background: transparent;")
        self.merge_branches_list_layout = QVBoxLayout(scroll_merge_content)
        self.merge_branches_list_layout.setContentsMargins(4, 4, 4, 4)
        self.merge_branches_list_layout.setSpacing(6)
        self.merge_branches_list_layout.addStretch()
        scroll_merge.setWidget(scroll_merge_content)
        p0_lay.addWidget(scroll_merge, 1)

        # Barra inferior con botón de refresco
        p0_bot = QHBoxLayout()
        p0_bot.setSpacing(10)
        btn_ref_merge = QPushButton("🔄  Refrescar Ramas")
        btn_ref_merge.setCursor(Qt.PointingHandCursor)
        btn_ref_merge.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: #d1d5db;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 700;
                font-size: 11.5px;
            }
            QPushButton:hover { background-color: rgba(255, 255, 255, 0.12); color: #ffffff; }
        """)
        btn_ref_merge.clicked.connect(self.refresh_merge_view)
        p0_bot.addWidget(btn_ref_merge)
        p0_bot.addStretch()
        p0_lay.addLayout(p0_bot)

        self.merge_inner_stack.addWidget(p_select)

        # =============================================================
        # PÁGINA 1: CONFIRMACIÓN Y CONFIGURACIÓN DE FUSIÓN
        # =============================================================
        p_confirm = QWidget()
        p1_lay = QVBoxLayout(p_confirm)
        p1_lay.setContentsMargins(0, 0, 0, 0)
        p1_lay.setSpacing(10)

        # Cabecera de Confirmación Táctica
        top_c_row = QHBoxLayout()
        lbl_p1_title = QLabel("❖ CONFIRMACIÓN DE FUSIÓN TÁCTICA ❖")
        lbl_p1_title.setStyleSheet("font-size: 12px; font-weight: 900; color: #38bdf8; letter-spacing: 0.5px;")
        top_c_row.addWidget(lbl_p1_title)
        top_c_row.addStretch()

        btn_view_sim_canvas = QPushButton("👁️ Ver Simulación en Grafo")
        btn_view_sim_canvas.setCursor(Qt.PointingHandCursor)
        btn_view_sim_canvas.setToolTip("Conmuta al visor horizontal de grafo para observar el nodo interactivo simulado.")
        btn_view_sim_canvas.setStyleSheet("""
            QPushButton {
                background-color: rgba(56, 189, 248, 0.15);
                color: #bae6fd;
                border: 1px solid rgba(56, 189, 248, 0.40);
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover { background-color: rgba(56, 189, 248, 0.30); color: #ffffff; }
        """)
        btn_view_sim_canvas.clicked.connect(self.show_simulated_canvas)
        top_c_row.addWidget(btn_view_sim_canvas)
        p1_lay.addLayout(top_c_row)

        # Resumen de commits entrantes
        self.lbl_commits_preview = QLabel("Commits a integrar:")
        self.lbl_commits_preview.setStyleSheet("font-size: 11px; color: #9ca3af; font-family: monospace;")
        p1_lay.addWidget(self.lbl_commits_preview)

        # Opciones de Ejecución (git merge vs git merge --no-ff)
        opt_box = QFrame()
        opt_box.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 6px;
                padding: 8px 12px;
            }
        """)
        opt_lay = QHBoxLayout(opt_box)
        opt_lay.setContentsMargins(6, 4, 6, 4)
        opt_lay.setSpacing(14)

        lbl_opt_title = QLabel("Método:")
        lbl_opt_title.setStyleSheet("font-size: 11.5px; font-weight: 800; color: #f3f4f6;")
        opt_lay.addWidget(lbl_opt_title)

        self.chk_merge_no_ff = QCheckBox("Forzar commit de merge (--no-ff)")
        self.chk_merge_no_ff.setStyleSheet("color: #e5e7eb; font-size: 11.5px; font-weight: 600;")
        self.chk_merge_no_ff.setToolTip("Crea siempre un commit explícito de fusión incluso si es posible avanzar de forma rápida (fast-forward).")
        opt_lay.addWidget(self.chk_merge_no_ff)
        opt_lay.addStretch()
        p1_lay.addWidget(opt_box)

        # Asistente de Mensaje de Commit (con IA o Estándar)
        msg_box = QFrame()
        msg_box.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 6px;
                padding: 10px 14px;
            }
        """)
        mb_lay = QVBoxLayout(msg_box)
        mb_lay.setSpacing(8)

        mb_head = QHBoxLayout()
        lbl_mb_title = QLabel("Mensaje de Commit de Fusión:")
        lbl_mb_title.setStyleSheet("font-size: 11.5px; font-weight: 800; color: #c084fc;")
        mb_head.addWidget(lbl_mb_title)
        mb_head.addStretch()

        btn_gen_ai_light = QPushButton("🤖 IA Ligero (HEX)")
        btn_gen_ai_light.setCursor(Qt.PointingHandCursor)
        btn_gen_ai_light.setStyleSheet("""
            QPushButton {
                background-color: rgba(56, 189, 248, 0.15);
                color: #7dd3fc;
                border: 1px solid rgba(56, 189, 248, 0.40);
                border-radius: 4px;
                padding: 3px 9px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover { background-color: rgba(56, 189, 248, 0.30); color: #ffffff; }
        """)
        btn_gen_ai_light.clicked.connect(lambda: self.start_ia_merge_generation("light"))
        mb_head.addWidget(btn_gen_ai_light)

        btn_gen_ai_heavy = QPushButton("🧠 IA Pesado (HENDRIX)")
        btn_gen_ai_heavy.setCursor(Qt.PointingHandCursor)
        btn_gen_ai_heavy.setStyleSheet("""
            QPushButton {
                background-color: rgba(192, 132, 252, 0.15);
                color: #d8b4fe;
                border: 1px solid rgba(192, 132, 252, 0.40);
                border-radius: 4px;
                padding: 3px 9px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover { background-color: rgba(192, 132, 252, 0.30); color: #ffffff; }
        """)
        btn_gen_ai_heavy.clicked.connect(lambda: self.start_ia_merge_generation("heavy"))
        mb_head.addWidget(btn_gen_ai_heavy)

        btn_gen_std = QPushButton("✍️ Estándar")
        btn_gen_std.setCursor(Qt.PointingHandCursor)
        btn_gen_std.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: #d1d5db;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 4px;
                padding: 3px 9px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: rgba(255, 255, 255, 0.10); color: #ffffff; }
        """)
        btn_gen_std.clicked.connect(self.set_default_merge_message)
        mb_head.addWidget(btn_gen_std)

        mb_lay.addLayout(mb_head)

        self.txt_merge_title = QLineEdit()
        self.txt_merge_title.setPlaceholderText("Título del commit de fusión...")
        self.txt_merge_title.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                color: #f3f4f6;
                padding: 6px 10px;
                font-size: 12px;
                font-weight: 700;
            }
            QLineEdit:focus { border-color: #38bdf8; }
        """)
        mb_lay.addWidget(self.txt_merge_title)

        self.txt_merge_body = QTextEdit()
        self.txt_merge_body.setPlaceholderText("Cuerpo descriptivo del commit de fusión...")
        self.txt_merge_body.setMaximumHeight(70)
        self.txt_merge_body.setStyleSheet("""
            QTextEdit {
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 6px;
                color: #e5e7eb;
                padding: 6px 10px;
                font-size: 11.5px;
            }
            QTextEdit:focus { border-color: #38bdf8; }
        """)
        mb_lay.addWidget(self.txt_merge_body)
        p1_lay.addWidget(msg_box)

        # Botones de Acción de Fusión
        row_act1 = QHBoxLayout()
        row_act1.setSpacing(10)

        self.btn_confirm_merge = QPushButton("🔀  Confirmar e Integrar en Destino")
        self.btn_confirm_merge.setCursor(Qt.PointingHandCursor)
        self.btn_confirm_merge.setStyleSheet("""
            QPushButton {
                background-color: rgba(56, 189, 248, 0.20);
                color: #38bdf8;
                border: 1px solid #38bdf8;
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: 800;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(56, 189, 248, 0.35);
                color: #ffffff;
            }
        """)
        self.btn_confirm_merge.clicked.connect(self.execute_merge_action)
        row_act1.addWidget(self.btn_confirm_merge)

        btn_cancel_p1 = QPushButton("Cancelar y Volver")
        btn_cancel_p1.setCursor(Qt.PointingHandCursor)
        btn_cancel_p1.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: #9ca3af;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                padding: 8px 14px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: rgba(255, 255, 255, 0.10); color: #ffffff; }
        """)
        btn_cancel_p1.clicked.connect(lambda: self.merge_inner_stack.setCurrentIndex(0))
        row_act1.addWidget(btn_cancel_p1)
        row_act1.addStretch()

        p1_lay.addLayout(row_act1)
        self.merge_inner_stack.addWidget(p_confirm)

        # =============================================================
        # PÁGINA 2: CARGA / ANÁLISIS IA DE FUSIÓN
        # =============================================================
        p_loading = QWidget()
        p2_lay = QVBoxLayout(p_loading)
        p2_lay.setContentsMargins(0, 20, 0, 20)
        p2_lay.setSpacing(12)
        p2_lay.setAlignment(Qt.AlignCenter)

        c_load = QFrame()
        c_load.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(26, 22, 38, 0.95), stop:1 rgba(15, 12, 25, 0.95));
                border: 1px solid rgba(56, 189, 248, 0.35);
                border-radius: 12px;
                padding: 24px;
            }
        """)
        cl_lay = QVBoxLayout(c_load)
        cl_lay.setSpacing(12)
        cl_lay.setAlignment(Qt.AlignCenter)

        lbl_load_ico = QLabel("⏳")
        lbl_load_ico.setAlignment(Qt.AlignCenter)
        lbl_load_ico.setStyleSheet("font-size: 32px;")
        cl_lay.addWidget(lbl_load_ico)

        self.lbl_merge_loading_title = QLabel("ANALIZANDO COMMITS Y DIFF DE FUSIÓN CON IA...")
        self.lbl_merge_loading_title.setAlignment(Qt.AlignCenter)
        self.lbl_merge_loading_title.setStyleSheet("font-size: 13.5px; font-weight: 900; color: #38bdf8; letter-spacing: 0.8px;")
        cl_lay.addWidget(self.lbl_merge_loading_title)

        lbl_load_sub = QLabel("Sintetizando cambios clave para estructurar el mensaje de commit de merge...")
        lbl_load_sub.setAlignment(Qt.AlignCenter)
        lbl_load_sub.setStyleSheet("font-size: 11.5px; color: #9ca3af;")
        cl_lay.addWidget(lbl_load_sub)

        pbar = QProgressBar()
        pbar.setRange(0, 0)
        pbar.setFixedHeight(8)
        pbar.setTextVisible(False)
        pbar.setStyleSheet("""
            QProgressBar {
                background-color: #0b0c13;
                border: 1px solid rgba(56, 189, 248, 0.30);
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #38bdf8, stop:0.5 #818cf8, stop:1 #34d399);
                border-radius: 4px;
            }
        """)
        cl_lay.addWidget(pbar)

        p2_lay.addWidget(c_load)
        self.merge_inner_stack.addWidget(p_loading)

        # =============================================================
        # PÁGINA 3: MANEJO DE CONFLICTOS DE EMERGENCIA
        # =============================================================
        p_conflict = QWidget()
        p3_lay = QVBoxLayout(p_conflict)
        p3_lay.setContentsMargins(0, 0, 0, 0)
        p3_lay.setSpacing(10)

        alert_box = QFrame()
        alert_box.setStyleSheet("""
            QFrame {
                background-color: rgba(248, 113, 113, 0.10);
                border: 1px solid #f87171;
                border-radius: 8px;
                padding: 12px 16px;
            }
        """)
        ab_lay = QVBoxLayout(alert_box)
        ab_lay.setSpacing(8)

        lbl_ab_title = QLabel("⚠️ ALERTA DE CONFLICTOS DETECTADOS")
        lbl_ab_title.setStyleSheet("font-size: 13px; font-weight: 900; color: #f87171; letter-spacing: 0.5px;")
        ab_lay.addWidget(lbl_ab_title)

        lbl_ab_desc = QLabel("La fusión no pudo completarse de forma automática debido a conflictos en los siguientes archivos:")
        lbl_ab_desc.setStyleSheet("font-size: 11.5px; color: #fca5a5;")
        ab_lay.addWidget(lbl_ab_desc)

        self.lbl_conflict_files_box = QLabel("")
        self.lbl_conflict_files_box.setStyleSheet("font-size: 11.5px; font-family: monospace; color: #ffffff; background-color: rgba(0, 0, 0, 0.25); border-radius: 4px; padding: 6px 10px;")
        ab_lay.addWidget(self.lbl_conflict_files_box)

        lbl_ab_help = QLabel("Opciones de resolución táctica:")
        lbl_ab_help.setStyleSheet("font-size: 11px; font-weight: 700; color: #e5e7eb; margin-top: 4px;")
        ab_lay.addWidget(lbl_ab_help)

        row_c_acts = QHBoxLayout()
        row_c_acts.setSpacing(8)

        btn_c_abort = QPushButton("💥 Abortar Fusión (git merge --abort)")
        btn_c_abort.setCursor(Qt.PointingHandCursor)
        btn_c_abort.setStyleSheet("""
            QPushButton {
                background-color: rgba(248, 113, 113, 0.25);
                color: #fca5a5;
                border: 1px solid #f87171;
                border-radius: 5px;
                padding: 6px 12px;
                font-weight: 700;
                font-size: 11px;
            }
            QPushButton:hover { background-color: rgba(248, 113, 113, 0.40); color: #ffffff; }
        """)
        btn_c_abort.clicked.connect(self.do_merge_abort)
        row_c_acts.addWidget(btn_c_abort)

        btn_c_ours = QPushButton("🛡️ Resolver con NUESTRAS (ours)")
        btn_c_ours.setCursor(Qt.PointingHandCursor)
        btn_c_ours.setStyleSheet("""
            QPushButton {
                background-color: rgba(251, 191, 36, 0.20);
                color: #fde047;
                border: 1px solid #fbbf24;
                border-radius: 5px;
                padding: 6px 12px;
                font-weight: 700;
                font-size: 11px;
            }
            QPushButton:hover { background-color: rgba(251, 191, 36, 0.35); color: #ffffff; }
        """)
        btn_c_ours.clicked.connect(lambda: self.do_merge_resolve_conflicts("ours"))
        row_c_acts.addWidget(btn_c_ours)

        btn_c_theirs = QPushButton("⚔️ Resolver con SUS (theirs)")
        btn_c_theirs.setCursor(Qt.PointingHandCursor)
        btn_c_theirs.setStyleSheet("""
            QPushButton {
                background-color: rgba(99, 102, 241, 0.20);
                color: #c7d2fe;
                border: 1px solid #818cf8;
                border-radius: 5px;
                padding: 6px 12px;
                font-weight: 700;
                font-size: 11px;
            }
            QPushButton:hover { background-color: rgba(99, 102, 241, 0.35); color: #ffffff; }
        """)
        btn_c_theirs.clicked.connect(lambda: self.do_merge_resolve_conflicts("theirs"))
        row_c_acts.addWidget(btn_c_theirs)

        btn_c_manual = QPushButton("🚪 Resolver Manualmente en Editor")
        btn_c_manual.setCursor(Qt.PointingHandCursor)
        btn_c_manual.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: #d1d5db;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 5px;
                padding: 6px 12px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: rgba(255, 255, 255, 0.12); color: #ffffff; }
        """)
        btn_c_manual.clicked.connect(self.notice_manual_resolution)
        row_c_acts.addWidget(btn_c_manual)
        row_c_acts.addStretch()

        ab_lay.addLayout(row_c_acts)
        p3_lay.addWidget(alert_box)

        # Panel para completar el merge una vez resueltos
        self.frame_complete_conflict = QFrame()
        self.frame_complete_conflict.setStyleSheet("""
            QFrame {
                background-color: rgba(52, 211, 153, 0.06);
                border: 1px solid rgba(52, 211, 153, 0.35);
                border-radius: 8px;
                padding: 10px 14px;
            }
        """)
        fcc_lay = QHBoxLayout(self.frame_complete_conflict)
        fcc_lay.setContentsMargins(8, 6, 8, 6)
        fcc_lay.setSpacing(10)

        lbl_fcc = QLabel("Una vez resueltos los conflictos, finaliza la integración:")
        lbl_fcc.setStyleSheet("font-size: 11.5px; color: #6ee7b7; font-weight: 700;")
        fcc_lay.addWidget(lbl_fcc)
        fcc_lay.addStretch()

        btn_finish_c_merge = QPushButton("💾  Completar Fusión (Registrar Commit)")
        btn_finish_c_merge.setCursor(Qt.PointingHandCursor)
        btn_finish_c_merge.setStyleSheet("""
            QPushButton {
                background-color: rgba(52, 211, 153, 0.25);
                color: #6ee7b7;
                border: 1px solid #34d399;
                border-radius: 5px;
                padding: 6px 16px;
                font-weight: 800;
                font-size: 11.5px;
            }
            QPushButton:hover { background-color: rgba(52, 211, 153, 0.40); color: #ffffff; }
        """)
        btn_finish_c_merge.clicked.connect(self.prepare_complete_active_merge)
        fcc_lay.addWidget(btn_finish_c_merge)
        p3_lay.addWidget(self.frame_complete_conflict)

        p3_lay.addStretch()
        self.merge_inner_stack.addWidget(p_conflict)

        # =============================================================
        # PÁGINA 4: FUSIÓN COMPLETADA & DESPLIEGUE INMEDIATO (PUSH)
        # =============================================================
        p_success = QWidget()
        p4_lay = QVBoxLayout(p_success)
        p4_lay.setContentsMargins(0, 10, 0, 10)
        p4_lay.setSpacing(12)

        card_suc = QFrame()
        card_suc.setStyleSheet("""
            QFrame {
                background-color: rgba(52, 211, 153, 0.08);
                border: 1px solid rgba(52, 211, 153, 0.45);
                border-radius: 10px;
                padding: 16px 20px;
            }
        """)
        cs_lay = QVBoxLayout(card_suc)
        cs_lay.setSpacing(10)

        lbl_suc_title = QLabel("🎉  FUSIÓN COMPLETADA EXITOSAMENTE")
        lbl_suc_title.setStyleSheet("font-size: 13.5px; font-weight: 900; color: #34d399; letter-spacing: 0.5px;")
        cs_lay.addWidget(lbl_suc_title)

        self.lbl_suc_desc = QLabel("La rama ha sido integrada satisfactoriamente en la rama activa.")
        self.lbl_suc_desc.setStyleSheet("font-size: 12px; color: #e5e7eb;")
        cs_lay.addWidget(self.lbl_suc_desc)

        # Caja de Despliegue Inmediato (Push)
        push_box = QFrame()
        push_box.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                padding: 12px 14px;
            }
        """)
        pb_lay = QVBoxLayout(push_box)
        pb_lay.setSpacing(8)

        lbl_pb_title = QLabel("🚀  SECUENCIA DE DESPLIEGUE TÁCTICO (GIT PUSH)")
        lbl_pb_title.setStyleSheet("font-size: 12px; font-weight: 800; color: #60a5fa;")
        pb_lay.addWidget(lbl_pb_title)

        lbl_pb_sub = QLabel("¿Deseas desplegar (hacer git push) de los cambios integrados a origin?")
        lbl_pb_sub.setStyleSheet("font-size: 11.5px; color: #9ca3af;")
        pb_lay.addWidget(lbl_pb_sub)

        row_pb_acts = QHBoxLayout()
        row_pb_acts.setSpacing(10)

        btn_push_yes = QPushButton("🚀  Desplegar Cambios a Origin (git push)")
        btn_push_yes.setCursor(Qt.PointingHandCursor)
        btn_push_yes.setStyleSheet("""
            QPushButton {
                background-color: rgba(96, 165, 250, 0.20);
                color: #93c5fd;
                border: 1px solid #60a5fa;
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: 800;
                font-size: 12px;
            }
            QPushButton:hover { background-color: rgba(96, 165, 250, 0.35); color: #ffffff; }
        """)
        btn_push_yes.clicked.connect(self.execute_merge_push)
        row_pb_acts.addWidget(btn_push_yes)

        btn_push_no = QPushButton("✔ Finalizar sin Desplegar")
        btn_push_no.setCursor(Qt.PointingHandCursor)
        btn_push_no.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: #d1d5db;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                padding: 8px 14px;
                font-weight: 700;
                font-size: 11.5px;
            }
            QPushButton:hover { background-color: rgba(255, 255, 255, 0.12); color: #ffffff; }
        """)
        btn_push_no.clicked.connect(lambda: self.merge_inner_stack.setCurrentIndex(0))
        row_pb_acts.addWidget(btn_push_no)
        row_pb_acts.addStretch()

        pb_lay.addLayout(row_pb_acts)
        cs_lay.addWidget(push_box)

        p4_lay.addWidget(card_suc)
        p4_lay.addStretch()
        self.merge_inner_stack.addWidget(p_success)

        layout.addWidget(self.merge_inner_stack)
        return page

    def toggle_switch_dest_drawer(self):
        """Alterna el cajón para cambiar la rama destino (receptora) de la fusión."""
        cur = self.drawer_switch_dest.isVisible()
        self.drawer_switch_dest.setVisible(not cur)
        if hasattr(self, "sector1_sub_stack"):
            self.sector1_sub_stack.updateGeometry()

    def execute_switch_dest_checkout(self):
        """Cambia de rama local para usarla como destino de fusión."""
        path = self.project_data.get("path")
        target = self.cmb_switch_dest.currentText().strip()
        if not path or not target or target.startswith("("):
            return

        self.terminal_display.log("NAV", f"Cambiando rama activa (HEAD) a <b>{target}</b> para fusión...", tag_color="#38bdf8", prefix="🔄")
        ok, msg = execute_git_checkout(path, target)
        if ok:
            self.terminal_display.log_success("NAV", f"Rama activa cambiada a <b>{target}</b>.")
            self.drawer_switch_dest.setVisible(False)
            self.refresh_current_project(reset_terminal=False)
            self.refresh_merge_view()
            self.refresh_git_graph()
        else:
            self.terminal_display.log_error("NAV", f"Fallo al cambiar a la rama destino '{target}':\n{msg}")

    def refresh_merge_view(self):
        """Consulta el estado del repositorio y lista las ramas destino disponibles para recibir la rama activa."""
        path = self.project_data.get("path")
        if not path or not os.path.exists(path):
            return

        status = get_git_merge_status(path)
        cur_branch = status.get("current_branch", "HEAD")
        cur_author = status.get("current_author", "")
        self.selected_merge_source = cur_branch
        self.lbl_merge_dest_info.setText(f"📤 Rama de Trabajo Activa (Origen): <b>{cur_branch}</b> • Autor: {cur_author}")
        self.lbl_p0_desc.setText(f"Selecciona la RAMA DESTINO donde deseas volcar e integrar los cambios de <b>{cur_branch}</b>:")

        # Poblar combo de cambio rápido de rama activa
        self.cmb_switch_dest.clear()
        matrix = get_git_branches_matrix(path)
        branches_mat = matrix.get("branches", [])
        local_branches = [b["name"] for b in branches_mat if not b["is_remote"] and not b["is_active"]]
        if local_branches:
            for b_name in local_branches:
                self.cmb_switch_dest.addItem(b_name)
        else:
            self.cmb_switch_dest.addItem("(Sin otras ramas locales)")

        # Manejo de estado de merge activo / conflictos
        if status.get("is_merge_active", False):
            self.frame_active_merge_alert.setVisible(True)
            if status.get("has_conflicts", False):
                self.lbl_merge_status_badge.setText("⚠️ FUSIÓN EN PROCESO (CONFLICTOS)")
                self.lbl_merge_status_badge.setStyleSheet("font-size: 10.5px; font-weight: 800; color: #f87171; background-color: rgba(248, 113, 113, 0.12); border: 1px solid rgba(248, 113, 113, 0.35); border-radius: 4px; padding: 2px 8px;")
                self.lbl_active_merge_msg.setText("⚠️ FUSIÓN EN CURSO CON CONFLICTOS PENDIENTES")
                self.lbl_conflicts_list.setText("Archivos en conflicto: " + ", ".join(status.get("conflicts", [])))
                self.btn_ama_complete.setEnabled(False)
            else:
                self.lbl_merge_status_badge.setText("⚠️ FUSIÓN EN PROCESO (LISTO PARA COMMIT)")
                self.lbl_merge_status_badge.setStyleSheet("font-size: 10.5px; font-weight: 800; color: #fbbf24; background-color: rgba(251, 191, 36, 0.12); border: 1px solid rgba(251, 191, 36, 0.35); border-radius: 4px; padding: 2px 8px;")
                self.lbl_active_merge_msg.setText("⚠️ FUSIÓN EN CURSO (CONFLICTOS RESUELTOS)")
                self.lbl_conflicts_list.setText("Todos los conflictos están resueltos. Puedes registrar el commit de fusión.")
                self.btn_ama_complete.setEnabled(True)
        else:
            self.frame_active_merge_alert.setVisible(False)
            self.lbl_merge_status_badge.setText("✔ ESTADO: LISTO PARA INTEGRACIÓN")
            self.lbl_merge_status_badge.setStyleSheet("font-size: 10.5px; font-weight: 800; color: #34d399; background-color: rgba(52, 211, 153, 0.12); border: 1px solid rgba(52, 211, 153, 0.35); border-radius: 4px; padding: 2px 8px;")

        # Limpiar lista anterior
        while self.merge_branches_list_layout.count():
            item = self.merge_branches_list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            elif item.layout():
                sub_lay = item.layout()
                while sub_lay.count():
                    sub_item = sub_lay.takeAt(0)
                    if sub_item.widget():
                        sub_item.widget().deleteLater()

        mergeable = get_mergeable_branches(path)
        if not mergeable:
            lbl_none = QLabel("No hay otras ramas destino detectadas en este repositorio.")
            lbl_none.setStyleSheet("color: #9ca3af; font-size: 12px; padding: 12px;")
            self.merge_branches_list_layout.addWidget(lbl_none)
        else:
            for b in mergeable:
                r_frame = QFrame()
                r_frame.setStyleSheet("""
                    QFrame {
                        background-color: rgba(255, 255, 255, 0.02);
                        border: 1px solid rgba(255, 255, 255, 0.06);
                        border-radius: 6px;
                        padding: 6px 10px;
                    }
                    QFrame:hover {
                        background-color: rgba(255, 255, 255, 0.05);
                        border-color: #38bdf8;
                    }
                """)
                rf_lay = QHBoxLayout(r_frame)
                rf_lay.setContentsMargins(8, 4, 8, 4)
                rf_lay.setSpacing(10)

                icon_str = "🌐" if b["is_remote"] else "🌿"
                lbl_ico = QLabel(icon_str)
                lbl_ico.setStyleSheet("font-size: 13px;")
                rf_lay.addWidget(lbl_ico)

                lbl_bname = QLabel(b["name"])
                lbl_bname.setStyleSheet("font-size: 12.5px; font-weight: 800; color: #f3f4f6; min-width: 140px;")
                rf_lay.addWidget(lbl_bname)

                # Desfase commits: ahead indica cuántos commits de cur_branch se volcarán en esta rama destino
                ahead = b.get("ahead", 0)
                behind = b.get("behind", 0)

                if ahead > 0:
                    lbl_badge = QLabel(f"⬆️ +{ahead} commits a transferir")
                    lbl_badge.setStyleSheet("font-size: 10.5px; font-weight: 800; color: #34d399; background-color: rgba(52, 211, 153, 0.12); border: 1px solid rgba(52, 211, 153, 0.35); border-radius: 4px; padding: 2px 7px;")
                else:
                    lbl_badge = QLabel("✔ Al día (sin cambios nuevos)")
                    lbl_badge.setStyleSheet("font-size: 10.5px; font-weight: 800; color: #9ca3af; background-color: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 4px; padding: 2px 7px;")
                rf_lay.addWidget(lbl_badge)

                if behind > 0:
                    lbl_behind = QLabel(f"⚠️ +{behind} en destino")
                    lbl_behind.setStyleSheet("font-size: 10.5px; font-weight: 800; color: #fbbf24; background-color: rgba(251, 191, 36, 0.12); border: 1px solid rgba(251, 191, 36, 0.35); border-radius: 4px; padding: 2px 7px;")
                    lbl_behind.setToolTip(f"La rama destino '{b['name']}' tiene {behind} commits nuevos por delante.")
                    rf_lay.addWidget(lbl_behind)

                # Info autor y fecha
                lbl_auth = QLabel(f"👤 {b['last_commit_author']} ({b['last_commit_date']})")
                lbl_auth.setStyleSheet("font-size: 11px; color: #9ca3af; min-width: 100px;")
                rf_lay.addWidget(lbl_auth)

                # Último commit truncado
                subj = b["last_commit_subject"]
                if len(subj) > 30:
                    subj = subj[:27] + "..."
                lbl_sub = QLabel(f"\"{subj}\"")
                lbl_sub.setStyleSheet("font-size: 11px; color: #6b7280; font-style: italic;")
                rf_lay.addWidget(lbl_sub, 1)

                # Botón Inspeccionar en Grafo
                h = b["last_commit_hash"]
                btn_see_graph = QPushButton("👁️ Ver en Grafo")
                btn_see_graph.setCursor(Qt.PointingHandCursor)
                btn_see_graph.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(255, 255, 255, 0.04);
                        color: #bae6fd;
                        border: 1px solid rgba(56, 189, 248, 0.30);
                        border-radius: 4px;
                        padding: 3px 8px;
                        font-size: 10.5px;
                        font-weight: 700;
                    }
                    QPushButton:hover { background-color: rgba(56, 189, 248, 0.20); color: #ffffff; }
                """)
                btn_see_graph.clicked.connect(lambda checked=False, chash=h: self.on_graph_commit_selected(chash))
                rf_lay.addWidget(btn_see_graph)

                # Botón Seleccionar Destino e Integrar
                b_name = b["name"]
                b_author = b["last_commit_author"]
                btn_integrate = QPushButton(f"🔀 Integrar en {b_name}")
                btn_integrate.setCursor(Qt.PointingHandCursor)
                btn_integrate.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(56, 189, 248, 0.20);
                        color: #38bdf8;
                        border: 1px solid #38bdf8;
                        border-radius: 4px;
                        padding: 4px 12px;
                        font-weight: 800;
                        font-size: 11px;
                    }
                    QPushButton:hover { background-color: rgba(56, 189, 248, 0.35); color: #ffffff; }
                """)
                btn_integrate.clicked.connect(lambda checked=False, bn=b_name, ba=b_author: self.prepare_merge_into_target(bn, ba))
                rf_lay.addWidget(btn_integrate)

                self.merge_branches_list_layout.addWidget(r_frame)

        self.merge_branches_list_layout.addStretch()

    def prepare_merge_into_target(self, target_branch: str, target_author: str):
        """Prepara los datos para integrar la rama activa actual dentro de la rama destino seleccionada."""
        path = self.project_data.get("path")
        if not path:
            return
        status = get_git_merge_status(path)
        source_branch = status.get("current_branch", "HEAD")
        source_author = status.get("current_author", "")

        self.selected_merge_source = source_branch
        self.selected_merge_target = target_branch
        self.selected_merge_branch = target_branch  # compatibilidad
        self.selected_merge_author = target_author

        data = get_merge_diff_and_commits(path, source_branch=source_branch, target_branch=target_branch)
        commits = data.get("commits", [])
        self.selected_merge_commits = commits

        if commits:
            prev_str = f"<b>Commits de '{source_branch}' a transferir a '{target_branch}' ({len(commits)}):</b><br>" + "<br>".join([f"• {c}" for c in commits[:5]])
            if len(commits) > 5:
                prev_str += f"<br>• ... y {len(commits) - 5} commits más."
        else:
            prev_str = f"<i>La rama destino '{target_branch}' ya se encuentra al día con los cambios de '{source_branch}'.</i>"
        self.lbl_commits_preview.setText(prev_str)

        self.set_default_merge_message()
        self.btn_confirm_merge.setText(f"🔀  Confirmar e Integrar '{source_branch}' en '{target_branch}'")

        # Proyectar nodo fantasma en el visor de grafo (la rama activa descenderá en diagonal a la rama destino)
        self.refresh_git_graph(simulated_merge={
            "source_branch": source_branch,
            "target_branch": target_branch,
            "title": self.txt_merge_title.text()
        })

        self.merge_inner_stack.setCurrentIndex(1)

    def prepare_merge_with_branch(self, branch_name: str, author: str):
        """Alias para compatibilidad."""
        self.prepare_merge_into_target(branch_name, author)

    def set_default_merge_message(self):
        """Establece el mensaje de commit estándar correlativo para la fusión."""
        path = self.project_data.get("path")
        next_id = get_next_commit_seq(path) if path else "0001"
        src_name = self.selected_merge_source or "origen"
        tgt_name = self.selected_merge_target or "destino"
        self.txt_merge_title.setText(f"HEX:{next_id} | Integración de {src_name} en {tgt_name}")
        self.txt_merge_body.setText(f"Fusión e integración táctica de la rama '{src_name}' en la rama destino '{tgt_name}'.")

    def start_ia_merge_generation(self, model_type: str = "light"):
        """Inicia el análisis de IA para redactar la propuesta semántica de merge."""
        path = self.project_data.get("path")
        if not path or not self.selected_merge_target:
            return
        self.merge_inner_stack.setCurrentIndex(2)
        m_label = "HEX (Ligero / Qwen)" if model_type == "light" else "HENDRIX (Pesado / Qwen)"
        src = self.selected_merge_source or "origen"
        tgt = self.selected_merge_target or "destino"
        self.lbl_merge_loading_title.setText(f"ANALIZANDO FUSIÓN CON IA ({m_label})...")
        self.terminal_display.log("AI-MERGE", f"Analizando commits y diferencias de <b>{src}</b> ➔ <b>{tgt}</b> con IA ({model_type})...", tag_color="#c084fc", prefix="🤖")
        self.merge_thread = IAMergeThread(
            path,
            source_branch=src,
            target_branch=tgt,
            model_type=model_type
        )
        self.merge_thread.finished_merge.connect(self.on_ia_merge_finished)
        self.merge_thread.start()

    def on_ia_merge_finished(self, success: bool, err_msg: str, res: dict):
        """Callback al finalizar la generación de mensaje de fusión con IA."""
        if success and res:
            self.txt_merge_title.setText(res.get("full_commit_title", ""))
            self.txt_merge_body.setText(res.get("body", ""))
            self.terminal_display.log_success("AI-MERGE", "Propuesta de commit de fusión generada con IA exitosamente.")
        else:
            self.terminal_display.log_warn("AI-MERGE", f"No se pudo consultar el modelo IA: {err_msg}. Se aplicará mensaje estándar.")
            self.set_default_merge_message()
        self.merge_inner_stack.setCurrentIndex(1)

    def execute_merge_action(self):
        """Ejecuta la operación de git merge en el repositorio integrando la rama origen en destino."""
        path = self.project_data.get("path")
        if not path or not self.selected_merge_target:
            return

        no_ff = self.chk_merge_no_ff.isChecked()
        title = self.txt_merge_title.text().strip()
        body = self.txt_merge_body.toPlainText().strip()

        src = self.selected_merge_source
        tgt = self.selected_merge_target
        no_ff_str = " (forzando commit --no-ff)" if no_ff else ""
        self.terminal_display.log("GIT-MERGE", f"Iniciando secuencia de integración de <b>{src}</b> en <b>{tgt}</b>{no_ff_str}...", tag_color="#38bdf8", prefix="🔀")

        ok, out, status = execute_git_merge_into(
            project_path=path,
            target_branch=tgt,
            source_branch=src,
            no_ff=no_ff,
            commit_title=title,
            commit_body=body
        )

        if ok and not status.get("has_conflicts", False):
            self.terminal_display.log_success("GIT-MERGE", f"¡Rama <b>{src}</b> fusionada e integrada exitosamente en <b>{tgt}</b>!")
            self.lbl_suc_desc.setText(f"La rama <b>{src}</b> fue integrada con éxito en la rama destino <b>{tgt}</b>.<br><pre style='color:#a5b4fc;'>{out[:300]}</pre>")
            self.refresh_current_project(reset_terminal=False)
            self.refresh_git_graph()
            self.merge_inner_stack.setCurrentIndex(4)
        else:
            if status.get("has_conflicts", False):
                conflicts = status.get("conflicts", [])
                self.terminal_display.log_error("GIT-MERGE", f"¡Conflicto detectado durante la fusión en {tgt}!\nArchivos afectados: {', '.join(conflicts)}")
                self.lbl_conflict_files_box.setText("\n".join(conflicts))
                self.refresh_git_graph()
                self.merge_inner_stack.setCurrentIndex(3)
            else:
                self.terminal_display.log_error("GIT-MERGE", f"Fallo al ejecutar fusión en '{tgt}':\n{out}")
                self.refresh_merge_view()

    def prepare_complete_active_merge(self):
        """Prepara el paso para confirmar el commit de una fusión en proceso."""
        path = self.project_data.get("path")
        if not path:
            return
        status = get_git_merge_status(path)
        b_name = status.get("incoming_branch") or self.selected_merge_branch or "rama_externa"
        self.prepare_merge_with_branch(b_name, "silvynth")
        self.merge_inner_stack.setCurrentIndex(1)

    def do_merge_abort(self):
        """Aborta de forma segura una fusión en curso."""
        path = self.project_data.get("path")
        if not path:
            return
        self.terminal_display.log("GIT-MERGE", "Abortando fusión en curso (git merge --abort)...", tag_color="#f87171", prefix="💥")
        ok, out = execute_git_merge_abort(path)
        if ok:
            self.terminal_display.log_success("GIT-MERGE", "Fusión abortada. El árbol de trabajo fue restaurado al estado anterior.")
        else:
            self.terminal_display.log_error("GIT-MERGE", f"Error al abortar fusión:\n{out}")
        self.refresh_current_project(reset_terminal=False)
        self.refresh_merge_view()
        self.refresh_git_graph()
        self.merge_inner_stack.setCurrentIndex(0)

    def do_merge_resolve_conflicts(self, strategy: str):
        """Resuelve los archivos conflictivos con la estrategia elegida ('ours' o 'theirs')."""
        path = self.project_data.get("path")
        if not path:
            return
        strat_lbl = "NUESTRAS VERSIONES (ours)" if strategy == "ours" else "SUS VERSIONES (theirs)"
        self.terminal_display.log("GIT-MERGE", f"Resolviendo conflictos aplicando <b>{strat_lbl}</b>...", tag_color="#fbbf24", prefix="🛡️")
        ok, out = execute_git_resolve_conflicts(path, strategy)
        if ok:
            self.terminal_display.log_success("GIT-MERGE", f"Resolución completada:\n{out}\nPuedes pulsar 'Completar Fusión' para registrar el commit.")
        else:
            self.terminal_display.log_error("GIT-MERGE", f"Fallo al resolver conflictos:\n{out}")
        self.refresh_merge_view()

    def notice_manual_resolution(self):
        """Notifica cómo proceder con la resolución manual de conflictos en el editor."""
        self.terminal_display.log("GIT-MERGE", "ℹ️ Los archivos conflictivos tienen marcadores estándar (<code>&lt;&lt;&lt;&lt;&lt;&lt;&lt;</code>). Ábrelos en tu editor, resuelve las diferencias, añade los cambios con <code>git add</code> y pulsa <b>'Completar Fusión'</b>.", tag_color="#38bdf8", prefix="📝")

    def execute_merge_push(self):
        """Despliega los cambios recién integrados hacia el remoto origin."""
        self.run_git_push()
        self.merge_inner_stack.setCurrentIndex(0)

    # =================================================================
    # MÓDULO 4 DEL SECTOR 1: ESTADO Y SINCRONIZACIÓN (STATUS • FETCH • PULL)
    # =================================================================
    def create_sector1_sync_view(self) -> QWidget:
        """Crea la sub-página dedicada para el Estado y Sincronización Táctica de Red."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 1. Cabecera de Navegación del Módulo 4
        head = QHBoxLayout()
        head.setSpacing(10)

        btn_back_main = QPushButton("◀  Volver al Menú de Sectores")
        btn_back_main.setCursor(Qt.PointingHandCursor)
        btn_back_main.setStyleSheet("""
            QPushButton {
                background-color: rgba(56, 189, 248, 0.15);
                color: #bae6fd;
                border: 1px solid rgba(56, 189, 248, 0.40);
                border-radius: 6px;
                padding: 5px 12px;
                font-weight: 700;
                font-size: 11.5px;
            }
            QPushButton:hover {
                background-color: rgba(56, 189, 248, 0.30);
                border-color: #38bdf8;
                color: #ffffff;
            }
        """)
        btn_back_main.clicked.connect(self.go_back_to_sectors_overview)
        head.addWidget(btn_back_main)

        btn_to_work = QPushButton("🔄  Ciclos de Trabajo")
        btn_to_work.setCursor(Qt.PointingHandCursor)
        btn_to_work.setStyleSheet("""
            QPushButton {
                background-color: rgba(99, 102, 241, 0.15);
                color: #c7d2fe;
                border: 1px solid rgba(99, 102, 241, 0.40);
                border-radius: 6px;
                padding: 5px 12px;
                font-weight: 700;
                font-size: 11.5px;
            }
            QPushButton:hover {
                background-color: rgba(99, 102, 241, 0.30);
                border-color: #818cf8;
                color: #ffffff;
            }
        """)
        btn_to_work.clicked.connect(self.go_back_to_work_cycles)
        head.addWidget(btn_to_work)

        btn_to_branches = QPushButton("🌿  Control de Ramas")
        btn_to_branches.setCursor(Qt.PointingHandCursor)
        btn_to_branches.setStyleSheet("""
            QPushButton {
                background-color: rgba(52, 211, 153, 0.15);
                color: #6ee7b7;
                border: 1px solid rgba(52, 211, 153, 0.40);
                border-radius: 6px;
                padding: 5px 12px;
                font-weight: 700;
                font-size: 11.5px;
            }
            QPushButton:hover {
                background-color: rgba(52, 211, 153, 0.30);
                border-color: #34d399;
                color: #ffffff;
            }
        """)
        btn_to_branches.clicked.connect(self.open_branches_view)
        head.addWidget(btn_to_branches)

        btn_to_merge = QPushButton("🔀  Fusión de Ramas")
        btn_to_merge.setCursor(Qt.PointingHandCursor)
        btn_to_merge.setStyleSheet("""
            QPushButton {
                background-color: rgba(56, 189, 248, 0.15);
                color: #bae6fd;
                border: 1px solid rgba(56, 189, 248, 0.40);
                border-radius: 6px;
                padding: 5px 12px;
                font-weight: 700;
                font-size: 11.5px;
            }
            QPushButton:hover {
                background-color: rgba(56, 189, 248, 0.30);
                border-color: #38bdf8;
                color: #ffffff;
            }
        """)
        btn_to_merge.clicked.connect(self.open_merge_view)
        head.addWidget(btn_to_merge)

        lbl_title = QLabel("⚡  ESTADO Y SINCRONIZACIÓN")
        lbl_title.setStyleSheet("font-size: 12.5px; font-weight: 900; color: #34d399; letter-spacing: 0.5px;")
        head.addWidget(lbl_title)
        head.addStretch()

        btn_toggle_graph = QPushButton("📊  Alternar Grafo / Terminal")
        btn_toggle_graph.setCursor(Qt.PointingHandCursor)
        btn_toggle_graph.setStyleSheet("""
            QPushButton {
                background-color: rgba(52, 211, 153, 0.12);
                color: #6ee7b7;
                border: 1px solid rgba(52, 211, 153, 0.35);
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: rgba(52, 211, 153, 0.25);
                color: #ffffff;
            }
        """)
        btn_toggle_graph.clicked.connect(self.toggle_terminal_graph_view)
        head.addWidget(btn_toggle_graph)

        lbl_pill = QLabel("[LUMEN • PROTOCOLO SYNC]")
        lbl_pill.setFixedHeight(24)
        lbl_pill.setAlignment(Qt.AlignCenter)
        lbl_pill.setStyleSheet("font-size: 10px; font-weight: 800; color: #34d399; background-color: rgba(52, 211, 153, 0.12); border: 1px solid rgba(52, 211, 153, 0.35); border-radius: 4px; padding: 2px 8px;")
        head.addWidget(lbl_pill)
        layout.addLayout(head)

        # 2. Panel HUD de Telemetría Táctica (3 Columnas)
        telemetry_frame = QFrame()
        telemetry_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.07);
                border-radius: 8px;
            }
        """)
        t_lay = QHBoxLayout(telemetry_frame)
        t_lay.setContentsMargins(12, 10, 12, 10)
        t_lay.setSpacing(14)

        # Columna 1: Rama Activa y Tracking Upstream
        c1 = QFrame()
        c1.setStyleSheet("background: transparent; border: none;")
        v1 = QVBoxLayout(c1)
        v1.setContentsMargins(0, 0, 0, 0)
        v1.setSpacing(3)
        lbl_t1 = QLabel("🌿 RAMA ACTIVA & UPSTREAM")
        lbl_t1.setStyleSheet("font-size: 10px; font-weight: 800; color: #9ca3af; letter-spacing: 0.5px;")
        v1.addWidget(lbl_t1)
        r_b = QHBoxLayout()
        r_b.setSpacing(8)
        self.lbl_sync_branch = QLabel("HEAD")
        self.lbl_sync_branch.setStyleSheet("font-size: 13px; font-weight: 900; color: #f3f4f6;")
        r_b.addWidget(self.lbl_sync_branch)
        self.lbl_sync_state_badge = QLabel("[Verificando]")
        self.lbl_sync_state_badge.setStyleSheet("font-size: 10px; font-weight: 800; color: #38bdf8; background: rgba(56, 189, 248, 0.12); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 4px; padding: 1px 6px;")
        r_b.addWidget(self.lbl_sync_state_badge)
        r_b.addStretch()
        v1.addLayout(r_b)
        self.lbl_sync_upstream = QLabel("origin/...")
        self.lbl_sync_upstream.setStyleSheet("font-family: monospace; font-size: 11px; color: #60a5fa;")
        v1.addWidget(self.lbl_sync_upstream)
        t_lay.addWidget(c1, 1)

        # Separador vertical
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.VLine)
        sep1.setStyleSheet("color: rgba(255, 255, 255, 0.08);")
        t_lay.addWidget(sep1)

        # Columna 2: Árbol Local y Líneas (+/-)
        c2 = QFrame()
        c2.setStyleSheet("background: transparent; border: none;")
        v2 = QVBoxLayout(c2)
        v2.setContentsMargins(0, 0, 0, 0)
        v2.setSpacing(3)
        lbl_t2 = QLabel("📁 ÁRBOL LOCAL & LÍNEAS (+/-)")
        lbl_t2.setStyleSheet("font-size: 10px; font-weight: 800; color: #9ca3af; letter-spacing: 0.5px;")
        v2.addWidget(lbl_t2)
        r_w = QHBoxLayout()
        r_w.setSpacing(8)
        self.lbl_sync_worktree_badge = QLabel("0 modificaciones")
        self.lbl_sync_worktree_badge.setStyleSheet("font-size: 12.5px; font-weight: 800; color: #fbbf24;")
        r_w.addWidget(self.lbl_sync_worktree_badge)
        self.lbl_sync_lines_badge = QLabel("+0 / -0")
        self.lbl_sync_lines_badge.setStyleSheet("font-family: monospace; font-size: 11px; font-weight: 700; color: #9ca3af;")
        r_w.addWidget(self.lbl_sync_lines_badge)
        r_w.addStretch()
        v2.addLayout(r_w)
        self.lbl_sync_stash_info = QLabel("📦 0 stashes guardados")
        self.lbl_sync_stash_info.setStyleSheet("font-size: 11px; color: #9ca3af;")
        v2.addWidget(self.lbl_sync_stash_info)
        t_lay.addWidget(c2, 1)

        # Separador vertical
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.VLine)
        sep2.setStyleSheet("color: rgba(255, 255, 255, 0.08);")
        t_lay.addWidget(sep2)

        # Columna 3: Pulso de Red & Seguridad Pre-Pull
        c3 = QFrame()
        c3.setStyleSheet("background: transparent; border: none;")
        v3 = QVBoxLayout(c3)
        v3.setContentsMargins(0, 0, 0, 0)
        v3.setSpacing(3)
        lbl_t3 = QLabel("🛰️ PULSO DE RED & SEGURIDAD")
        lbl_t3.setStyleSheet("font-size: 10px; font-weight: 800; color: #9ca3af; letter-spacing: 0.5px;")
        v3.addWidget(lbl_t3)
        self.lbl_sync_last_fetch = QLabel("🕒 Último fetch: -")
        self.lbl_sync_last_fetch.setStyleSheet("font-size: 11.5px; font-weight: 700; color: #e5e7eb;")
        v3.addWidget(self.lbl_sync_last_fetch)
        self.lbl_sync_safety_badge = QLabel("[🛡️ Diagnóstico Pre-Pull]")
        self.lbl_sync_safety_badge.setStyleSheet("font-size: 10.5px; font-weight: 800; color: #34d399;")
        v3.addWidget(self.lbl_sync_safety_badge)
        t_lay.addWidget(c3, 1)

        layout.addWidget(telemetry_frame)

        # 3. Baraja de Acciones Tácticas (Status, Fetch, Pull)
        deck_frame = QFrame()
        deck_frame.setStyleSheet("background: transparent; border: none;")
        d_lay = QHBoxLayout(deck_frame)
        d_lay.setContentsMargins(0, 0, 0, 0)
        d_lay.setSpacing(10)

        self.btn_action_status = LumenCyberActionButton(
            "📋", "Inspeccionar Árbol (Status)", 
            "Audita archivos modificados, stage, deltas de líneas (+/-) y stashes", 
            accent_color="#38bdf8"
        )
        self.btn_action_status.clicked.connect(lambda _: self.execute_status_inspect())
        d_lay.addWidget(self.btn_action_status)

        self.btn_action_fetch = LumenCyberActionButton(
            "📡", "Descargar Metadatos (Fetch)", 
            "Consulta commits y ramas del remoto con poda (--prune) sin alterar código", 
            accent_color="#c084fc"
        )
        self.btn_action_fetch.clicked.connect(lambda _: self.execute_fetch_action())
        d_lay.addWidget(self.btn_action_fetch)

        self.btn_action_pull = LumenCyberActionButton(
            "📥", "Sincronizar Cambios (Pull)", 
            "Descarga e integra commits entrantes con Rebase + Autostash inteligente", 
            accent_color="#34d399"
        )
        self.btn_action_pull.clicked.connect(lambda _: self.execute_pull_action())
        d_lay.addWidget(self.btn_action_pull)

        layout.addWidget(deck_frame)

        # 4. Barra de Opciones de Pull y Controles Stash
        opts_frame = QFrame()
        opts_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 6px;
                padding: 4px 10px;
            }
        """)
        o_lay = QHBoxLayout(opts_frame)
        o_lay.setContentsMargins(8, 4, 8, 4)
        o_lay.setSpacing(12)

        lbl_strat = QLabel("Estrategia Pull:")
        lbl_strat.setStyleSheet("font-size: 11px; font-weight: 700; color: #9ca3af;")
        o_lay.addWidget(lbl_strat)

        self.cmb_pull_strategy = QComboBox()
        self.cmb_pull_strategy.setItemDelegate(QStyledItemDelegate())
        self.cmb_pull_strategy.setStyleSheet("""
            QComboBox {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 4px;
                color: #f3f4f6;
                padding: 3px 8px;
                font-size: 11px;
                min-width: 230px;
            }
        """)
        self.cmb_pull_strategy.addItem("⚡ Rebase Seguro (Recomendado • Sin merge commits)", "rebase")
        self.cmb_pull_strategy.addItem("🔀 Merge Estándar (git pull --no-rebase)", "merge")
        self.cmb_pull_strategy.addItem("⏩ Fast-Forward Únicamente (--ff-only)", "ff-only")
        o_lay.addWidget(self.cmb_pull_strategy)

        self.chk_pull_autostash = QCheckBox("Autostash automático")
        self.chk_pull_autostash.setChecked(True)
        self.chk_pull_autostash.setToolTip("Guarda tus cambios locales en un stash temporal y los re-aplica automáticamente tras el pull")
        self.chk_pull_autostash.setStyleSheet("QCheckBox { font-size: 11px; color: #9ca3af; font-weight: 600; } QCheckBox:hover { color: #f3f4f6; }")
        o_lay.addWidget(self.chk_pull_autostash)

        o_lay.addStretch()

        self.btn_toggle_stash = QPushButton("📦 Guardar Stash")
        self.btn_toggle_stash.setCursor(Qt.PointingHandCursor)
        self.btn_toggle_stash.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.04);
                color: #9ca3af;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 4px;
                padding: 3px 10px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover { color: #f3f4f6; border-color: rgba(255, 255, 255, 0.25); }
        """)
        self.btn_toggle_stash.clicked.connect(self.toggle_stash_drawer)
        o_lay.addWidget(self.btn_toggle_stash)

        self.btn_pop_stash = QPushButton("⚡ Pop Stash")
        self.btn_pop_stash.setCursor(Qt.PointingHandCursor)
        self.btn_pop_stash.setStyleSheet("""
            QPushButton {
                background-color: rgba(251, 191, 36, 0.12);
                color: #fde047;
                border: 1px solid rgba(251, 191, 36, 0.35);
                border-radius: 4px;
                padding: 3px 10px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover { background-color: rgba(251, 191, 36, 0.25); color: #ffffff; }
        """)
        self.btn_pop_stash.clicked.connect(self.execute_stash_pop_action)
        o_lay.addWidget(self.btn_pop_stash)

        layout.addWidget(opts_frame)

        # Cajón Dinámico de Stash (Guardar)
        self.drawer_stash_save = QFrame()
        self.drawer_stash_save.setVisible(False)
        self.drawer_stash_save.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(251, 191, 36, 0.35);
                border-radius: 6px;
                padding: 6px 12px;
            }
        """)
        ds_lay = QHBoxLayout(self.drawer_stash_save)
        ds_lay.setContentsMargins(6, 4, 6, 4)
        ds_lay.setSpacing(10)

        lbl_s_prompt = QLabel("Mensaje de Stash:")
        lbl_s_prompt.setStyleSheet("font-size: 11px; font-weight: 700; color: #fde047;")
        ds_lay.addWidget(lbl_s_prompt)

        self.txt_stash_msg = QLineEdit()
        self.txt_stash_msg.setPlaceholderText("Descripción del trabajo en pausa (ej. feat/auth en progreso)...")
        self.txt_stash_msg.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 4px;
                color: #f3f4f6;
                padding: 4px 8px;
                font-size: 11.5px;
            }
            QLineEdit:focus { border-color: #fde047; }
        """)
        self.txt_stash_msg.returnPressed.connect(self.execute_stash_save_action)
        ds_lay.addWidget(self.txt_stash_msg, 1)

        btn_confirm_stash = QPushButton("Confirmar Stash")
        btn_confirm_stash.setCursor(Qt.PointingHandCursor)
        btn_confirm_stash.setStyleSheet("""
            QPushButton {
                background-color: rgba(251, 191, 36, 0.20);
                color: #fde047;
                border: 1px solid #fbbf24;
                border-radius: 4px;
                padding: 4px 12px;
                font-weight: 700;
                font-size: 11px;
            }
            QPushButton:hover { background-color: rgba(251, 191, 36, 0.35); color: #ffffff; }
        """)
        btn_confirm_stash.clicked.connect(self.execute_stash_save_action)
        ds_lay.addWidget(btn_confirm_stash)

        btn_cancel_stash = QPushButton("Cancelar")
        btn_cancel_stash.setCursor(Qt.PointingHandCursor)
        btn_cancel_stash.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.04);
                color: #9ca3af;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 11px;
            }
        """)
        btn_cancel_stash.clicked.connect(lambda: self.drawer_stash_save.setVisible(False))
        ds_lay.addWidget(btn_cancel_stash)

        layout.addWidget(self.drawer_stash_save)

        # 5. Selector de Pestañas de Detalle
        tabs_bar = QFrame()
        tabs_bar.setStyleSheet("background: transparent; border: none;")
        tb_lay = QHBoxLayout(tabs_bar)
        tb_lay.setContentsMargins(0, 4, 0, 2)
        tb_lay.setSpacing(8)

        self.btn_sync_tab_tree = QPushButton("📁  Árbol Local & Líneas (+/-)")
        self.btn_sync_tab_tree.setCursor(Qt.PointingHandCursor)
        self.btn_sync_tab_tree.clicked.connect(lambda: self.switch_sync_tab(0))
        tb_lay.addWidget(self.btn_sync_tab_tree)

        self.btn_sync_tab_incoming = QPushButton("🛰️  Radar de Commits (Entrantes / Salientes)")
        self.btn_sync_tab_incoming.setCursor(Qt.PointingHandCursor)
        self.btn_sync_tab_incoming.clicked.connect(lambda: self.switch_sync_tab(1))
        tb_lay.addWidget(self.btn_sync_tab_incoming)

        tb_lay.addStretch()
        layout.addWidget(tabs_bar)

        # Sub-stack para los detalles
        self.sync_details_stack = QStackedWidget()
        self.sync_details_stack.setStyleSheet("background: transparent; border: none;")

        # --- Sub-página 0: Árbol Local & Archivos ---
        page_tree = QWidget()
        pt_lay = QVBoxLayout(page_tree)
        pt_lay.setContentsMargins(0, 0, 0, 0)
        pt_lay.setSpacing(8)

        # Filtros rápidos para el árbol
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(8)
        self.sync_filter_buttons = {}
        for f_key, f_lbl in [("ALL", "Todos"), ("UNSTAGED", "Modificados"), ("STAGED", "En Stage"), ("UNTRACKED", "Nuevos"), ("CONFLICT", "Conflictos")]:
            f_btn = QPushButton(f_lbl)
            f_btn.setCursor(Qt.PointingHandCursor)
            f_btn.clicked.connect(lambda _, k=f_key: self.filter_sync_tree(k))
            filter_bar.addWidget(f_btn)
            self.sync_filter_buttons[f_key] = f_btn
        filter_bar.addStretch()
        pt_lay.addLayout(filter_bar)

        # Scroll Area para la lista de archivos
        tree_scroll = QScrollArea()
        tree_scroll.setWidgetResizable(True)
        tree_scroll.setMinimumHeight(180)
        tree_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        tree_content = QWidget()
        tree_content.setStyleSheet("background: transparent;")
        self.sync_files_layout = QVBoxLayout(tree_content)
        self.sync_files_layout.setContentsMargins(0, 0, 0, 0)
        self.sync_files_layout.setSpacing(6)
        self.sync_files_layout.addStretch()
        tree_scroll.setWidget(tree_content)
        pt_lay.addWidget(tree_scroll, 1)

        self.sync_details_stack.addWidget(page_tree)

        # --- Sub-página 1: Radar de Commits Entrantes / Salientes ---
        page_radar = QWidget()
        pr_lay = QVBoxLayout(page_radar)
        pr_lay.setContentsMargins(0, 0, 0, 0)
        pr_lay.setSpacing(8)

        radar_scroll = QScrollArea()
        radar_scroll.setWidgetResizable(True)
        radar_scroll.setMinimumHeight(180)
        radar_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        radar_content = QWidget()
        radar_content.setStyleSheet("background: transparent;")
        self.sync_radar_layout = QVBoxLayout(radar_content)
        self.sync_radar_layout.setContentsMargins(0, 0, 0, 0)
        self.sync_radar_layout.setSpacing(6)
        self.sync_radar_layout.addStretch()
        radar_scroll.setWidget(radar_content)
        pr_lay.addWidget(radar_scroll, 1)

        self.sync_details_stack.addWidget(page_radar)

        layout.addWidget(self.sync_details_stack, 1)

        # Variables internas de estado
        self.current_sync_filter = "ALL"
        self.last_sync_status = {}
        self.switch_sync_tab(0)

        return page

    def switch_sync_tab(self, tab_idx: int):
        """Alterna visualmente entre la pestaña del Árbol Local y el Radar de Commits."""
        self.sync_details_stack.setCurrentIndex(tab_idx)
        active_style = """
            QPushButton {
                background-color: rgba(52, 211, 153, 0.20);
                color: #6ee7b7;
                border: 1px solid #34d399;
                border-radius: 6px;
                padding: 5px 14px;
                font-weight: 800;
                font-size: 11.5px;
            }
        """
        inactive_style = """
            QPushButton {
                background-color: rgba(255, 255, 255, 0.03);
                color: #9ca3af;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                padding: 5px 14px;
                font-weight: 600;
                font-size: 11.5px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.07);
                color: #f3f4f6;
            }
        """
        if tab_idx == 0:
            self.btn_sync_tab_tree.setStyleSheet(active_style)
            self.btn_sync_tab_incoming.setStyleSheet(inactive_style)
        else:
            self.btn_sync_tab_tree.setStyleSheet(inactive_style)
            self.btn_sync_tab_incoming.setStyleSheet(active_style)
        if hasattr(self, "sector1_sub_stack"):
            self.sector1_sub_stack.updateGeometry()

    def filter_sync_tree(self, filter_key: str):
        """Filtra los archivos del árbol de trabajo según su categoría."""
        self.current_sync_filter = filter_key
        self.update_filter_button_styles()
        self.render_sync_local_tree(self.last_sync_status)

    def update_filter_button_styles(self):
        """Actualiza los estilos visuales de los chips de filtrado del árbol."""
        status = self.last_sync_status
        counts = {
            "ALL": status.get("total_unstaged", 0) + status.get("total_staged", 0) + status.get("total_untracked", 0) + status.get("total_conflicts", 0),
            "UNSTAGED": status.get("total_unstaged", 0),
            "STAGED": status.get("total_staged", 0),
            "UNTRACKED": status.get("total_untracked", 0),
            "CONFLICT": status.get("total_conflicts", 0)
        }
        labels = {
            "ALL": "Todos",
            "UNSTAGED": "Modificados",
            "STAGED": "En Stage",
            "UNTRACKED": "Nuevos",
            "CONFLICT": "Conflictos"
        }
        for k, btn in self.sync_filter_buttons.items():
            cnt = counts.get(k, 0)
            btn.setText(f"{labels[k]} ({cnt})")
            if k == self.current_sync_filter:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(56, 189, 248, 0.20);
                        color: #7dd3fc;
                        border: 1px solid #38bdf8;
                        border-radius: 4px;
                        padding: 3px 10px;
                        font-weight: 700;
                        font-size: 11px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(255, 255, 255, 0.03);
                        color: #9ca3af;
                        border: 1px solid rgba(255, 255, 255, 0.08);
                        border-radius: 4px;
                        padding: 3px 10px;
                        font-size: 11px;
                    }
                    QPushButton:hover { color: #f3f4f6; background-color: rgba(255, 255, 255, 0.06); }
                """)

    def refresh_sync_view(self):
        """Consulta y renderiza en vivo el estado completo de sincronización y árbol."""
        path = self.project_data.get("path")
        if not path or not os.path.exists(path):
            return

        status = get_git_sync_deep_status(path)
        self.last_sync_status = status

        # 1. Telemetría - Rama y Upstream
        branch = status.get("branch", "HEAD")
        upstream = status.get("upstream", "")
        self.lbl_sync_branch.setText(branch)
        if upstream:
            self.lbl_sync_upstream.setText(f"↳ {upstream}")
        else:
            self.lbl_sync_upstream.setText("↳ Sin tracking remoto")

        ahead = status.get("ahead", 0)
        behind = status.get("behind", 0)
        if not status.get("has_remote"):
            self.lbl_sync_state_badge.setText("Modo Local")
            self.lbl_sync_state_badge.setStyleSheet("font-size: 10px; font-weight: 800; color: #9ca3af; background: rgba(156, 163, 175, 0.12); border: 1px solid rgba(156, 163, 175, 0.3); border-radius: 4px; padding: 1px 6px;")
        elif not status.get("has_upstream"):
            self.lbl_sync_state_badge.setText("Sin Upstream")
            self.lbl_sync_state_badge.setStyleSheet("font-size: 10px; font-weight: 800; color: #fbbf24; background: rgba(251, 191, 36, 0.12); border: 1px solid rgba(251, 191, 36, 0.3); border-radius: 4px; padding: 1px 6px;")
        elif status.get("diverged"):
            self.lbl_sync_state_badge.setText(f"▲ Ahead +{ahead} / ▼ Behind -{behind}")
            self.lbl_sync_state_badge.setStyleSheet("font-size: 10px; font-weight: 800; color: #f87171; background: rgba(248, 113, 113, 0.15); border: 1px solid rgba(248, 113, 113, 0.35); border-radius: 4px; padding: 1px 6px;")
        elif behind > 0:
            self.lbl_sync_state_badge.setText(f"▼ Behind -{behind} (Pull pendiente)")
            self.lbl_sync_state_badge.setStyleSheet("font-size: 10px; font-weight: 800; color: #c084fc; background: rgba(192, 132, 252, 0.15); border: 1px solid rgba(192, 132, 252, 0.35); border-radius: 4px; padding: 1px 6px;")
        elif ahead > 0:
            self.lbl_sync_state_badge.setText(f"▲ Ahead +{ahead} (Push pendiente)")
            self.lbl_sync_state_badge.setStyleSheet("font-size: 10px; font-weight: 800; color: #38bdf8; background: rgba(56, 189, 248, 0.15); border: 1px solid rgba(56, 189, 248, 0.35); border-radius: 4px; padding: 1px 6px;")
        else:
            self.lbl_sync_state_badge.setText("● Al Día (Sincronizado)")
            self.lbl_sync_state_badge.setStyleSheet("font-size: 10px; font-weight: 800; color: #34d399; background: rgba(52, 211, 153, 0.15); border: 1px solid rgba(52, 211, 153, 0.35); border-radius: 4px; padding: 1px 6px;")

        # 2. Telemetría - Árbol Local & Líneas
        staged_cnt = status.get("total_staged", 0)
        unstaged_cnt = status.get("total_unstaged", 0)
        untracked_cnt = status.get("total_untracked", 0)
        conflicts_cnt = status.get("total_conflicts", 0)
        tot_files = staged_cnt + unstaged_cnt + untracked_cnt + conflicts_cnt

        if status.get("is_clean"):
            self.lbl_sync_worktree_badge.setText("✨ Árbol Limpio")
            self.lbl_sync_worktree_badge.setStyleSheet("font-size: 12.5px; font-weight: 800; color: #34d399;")
        else:
            self.lbl_sync_worktree_badge.setText(f"{tot_files} archivo(s) con cambios")
            self.lbl_sync_worktree_badge.setStyleSheet("font-size: 12.5px; font-weight: 800; color: #fbbf24;")

        adds = status.get("total_lines_added", 0)
        dels = status.get("total_lines_deleted", 0)
        self.lbl_sync_lines_badge.setText(f"+{adds} / -{dels} líneas")

        scnt = status.get("stash_count", 0)
        self.lbl_sync_stash_info.setText(f"📦 {scnt} stash(es) guardados")
        self.btn_pop_stash.setEnabled(scnt > 0)
        if scnt == 0:
            self.btn_pop_stash.setStyleSheet("QPushButton { background-color: rgba(255, 255, 255, 0.03); color: #6b7280; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 4px; padding: 3px 10px; font-size: 11px; }")
        else:
            self.btn_pop_stash.setStyleSheet("QPushButton { background-color: rgba(251, 191, 36, 0.15); color: #fde047; border: 1px solid rgba(251, 191, 36, 0.40); border-radius: 4px; padding: 3px 10px; font-size: 11px; font-weight: 700; } QPushButton:hover { background-color: rgba(251, 191, 36, 0.30); color: #ffffff; }")

        # 3. Telemetría - Pulso de Red & Seguridad
        self.lbl_sync_last_fetch.setText(f"🕒 {status.get('last_fetch_str', 'Sin registro')}")
        rec = status.get("recommended_action", "Al día")
        self.lbl_sync_safety_badge.setText(f"[{rec}]")

        # 4. Actualizar Listas de Detalle
        self.update_filter_button_styles()
        self.render_sync_local_tree(status)
        self.render_sync_incoming_radar(status)

        if hasattr(self, "sector1_sub_stack"):
            self.sector1_sub_stack.updateGeometry()

    def render_sync_local_tree(self, status: dict):
        """Renderiza los archivos del árbol de trabajo con métricas de líneas y botones de acción rápida."""
        while self.sync_files_layout.count():
            item = self.sync_files_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        staged = status.get("staged_files", [])
        unstaged = status.get("unstaged_files", [])
        untracked = status.get("untracked_files", [])
        conflicts = status.get("conflict_files", [])

        items_to_show = []

        if self.current_sync_filter in ("ALL", "CONFLICT"):
            for cf in conflicts:
                items_to_show.append(("CONFLICT", cf, 0, 0))

        if self.current_sync_filter in ("ALL", "STAGED"):
            for sf in staged:
                items_to_show.append(("STAGED", sf["path"], sf.get("adds", 0), sf.get("dels", 0)))

        if self.current_sync_filter in ("ALL", "UNSTAGED"):
            for uf in unstaged:
                items_to_show.append(("UNSTAGED", uf["path"], uf.get("adds", 0), uf.get("dels", 0)))

        if self.current_sync_filter in ("ALL", "UNTRACKED"):
            for ut in untracked:
                items_to_show.append(("UNTRACKED", ut, 0, 0))

        if not items_to_show:
            empty_frame = QFrame()
            empty_frame.setStyleSheet("""
                QFrame {
                    background-color: rgba(255, 255, 255, 0.02);
                    border: 1px dashed rgba(255, 255, 255, 0.10);
                    border-radius: 8px;
                    padding: 24px;
                }
            """)
            ef_lay = QVBoxLayout(empty_frame)
            ef_lay.setAlignment(Qt.AlignCenter)
            if status.get("is_clean", True):
                msg_lbl = QLabel("✨ Árbol de trabajo 100% limpio. No hay modificaciones pendientes.")
                msg_lbl.setStyleSheet("font-size: 12.5px; font-weight: 700; color: #34d399;")
            else:
                msg_lbl = QLabel("ℹ️ No hay archivos en esta categoría.")
                msg_lbl.setStyleSheet("font-size: 12px; color: #9ca3af;")
            ef_lay.addWidget(msg_lbl)
            self.sync_files_layout.addWidget(empty_frame)
            self.sync_files_layout.addStretch()
            return

        for kind, fpath, adds, dels in items_to_show:
            row = QFrame()
            row.setStyleSheet("""
                QFrame {
                    background-color: rgba(255, 255, 255, 0.02);
                    border: 1px solid rgba(255, 255, 255, 0.06);
                    border-radius: 6px;
                    padding: 4px 8px;
                }
                QFrame:hover {
                    background-color: rgba(255, 255, 255, 0.05);
                    border-color: rgba(255, 255, 255, 0.12);
                }
            """)
            r_lay = QHBoxLayout(row)
            r_lay.setContentsMargins(8, 4, 8, 4)
            r_lay.setSpacing(10)

            badge = QLabel()
            badge.setFixedHeight(20)
            badge.setAlignment(Qt.AlignCenter)
            if kind == "STAGED":
                badge.setText("STAGE")
                badge.setStyleSheet("font-size: 9.5px; font-weight: 800; color: #34d399; background: rgba(52, 211, 153, 0.15); border: 1px solid rgba(52, 211, 153, 0.35); border-radius: 3px; padding: 1px 6px;")
            elif kind == "UNSTAGED":
                badge.setText("MOD")
                badge.setStyleSheet("font-size: 9.5px; font-weight: 800; color: #fbbf24; background: rgba(251, 191, 36, 0.15); border: 1px solid rgba(251, 191, 36, 0.35); border-radius: 3px; padding: 1px 6px;")
            elif kind == "UNTRACKED":
                badge.setText("NEW")
                badge.setStyleSheet("font-size: 9.5px; font-weight: 800; color: #38bdf8; background: rgba(56, 189, 248, 0.15); border: 1px solid rgba(56, 189, 248, 0.35); border-radius: 3px; padding: 1px 6px;")
            else:
                badge.setText("CONFLICT")
                badge.setStyleSheet("font-size: 9.5px; font-weight: 800; color: #f87171; background: rgba(248, 113, 113, 0.15); border: 1px solid rgba(248, 113, 113, 0.35); border-radius: 3px; padding: 1px 6px;")
            r_lay.addWidget(badge)

            lbl_fp = QLabel(fpath)
            lbl_fp.setStyleSheet("font-family: monospace; font-size: 11.5px; color: #f3f4f6;")
            lbl_fp.setTextInteractionFlags(Qt.TextSelectableByMouse)
            r_lay.addWidget(lbl_fp, 1)

            if adds > 0 or dels > 0:
                lbl_l = QLabel(f"<span style='color: #34d399; font-weight: 700;'>+{adds}</span>  <span style='color: #f87171; font-weight: 700;'>-{dels}</span>")
                lbl_l.setStyleSheet("font-family: monospace; font-size: 11px;")
                r_lay.addWidget(lbl_l)

            if kind == "UNSTAGED":
                btn_st = QPushButton("+ Stage")
                btn_st.setCursor(Qt.PointingHandCursor)
                btn_st.setStyleSheet("QPushButton { background-color: rgba(52, 211, 153, 0.15); color: #6ee7b7; border: 1px solid rgba(52, 211, 153, 0.35); border-radius: 4px; padding: 2px 8px; font-size: 10.5px; font-weight: 700; } QPushButton:hover { background-color: rgba(52, 211, 153, 0.30); color: #fff; }")
                btn_st.clicked.connect(lambda _, p=fpath: self.execute_stage_file(p))
                r_lay.addWidget(btn_st)

                btn_dc = QPushButton("↺ Descartar")
                btn_dc.setCursor(Qt.PointingHandCursor)
                btn_dc.setStyleSheet("QPushButton { background-color: rgba(248, 113, 113, 0.12); color: #fca5a5; border: 1px solid rgba(248, 113, 113, 0.35); border-radius: 4px; padding: 2px 8px; font-size: 10.5px; font-weight: 600; } QPushButton:hover { background-color: rgba(248, 113, 113, 0.25); color: #fff; }")
                btn_dc.clicked.connect(lambda _, p=fpath: self.execute_discard_file(p))
                r_lay.addWidget(btn_dc)
            elif kind == "STAGED":
                btn_unst = QPushButton("- Unstage")
                btn_unst.setCursor(Qt.PointingHandCursor)
                btn_unst.setStyleSheet("QPushButton { background-color: rgba(251, 191, 36, 0.15); color: #fde047; border: 1px solid rgba(251, 191, 36, 0.35); border-radius: 4px; padding: 2px 8px; font-size: 10.5px; font-weight: 700; } QPushButton:hover { background-color: rgba(251, 191, 36, 0.30); color: #fff; }")
                btn_unst.clicked.connect(lambda _, p=fpath: self.execute_unstage_file(p))
                r_lay.addWidget(btn_unst)

                btn_dc = QPushButton("↺ Descartar")
                btn_dc.setCursor(Qt.PointingHandCursor)
                btn_dc.setStyleSheet("QPushButton { background-color: rgba(248, 113, 113, 0.12); color: #fca5a5; border: 1px solid rgba(248, 113, 113, 0.35); border-radius: 4px; padding: 2px 8px; font-size: 10.5px; font-weight: 600; } QPushButton:hover { background-color: rgba(248, 113, 113, 0.25); color: #fff; }")
                btn_dc.clicked.connect(lambda _, p=fpath: self.execute_discard_file(p))
                r_lay.addWidget(btn_dc)
            elif kind == "UNTRACKED":
                btn_st = QPushButton("+ Stage")
                btn_st.setCursor(Qt.PointingHandCursor)
                btn_st.setStyleSheet("QPushButton { background-color: rgba(56, 189, 248, 0.15); color: #7dd3fc; border: 1px solid rgba(56, 189, 248, 0.35); border-radius: 4px; padding: 2px 8px; font-size: 10.5px; font-weight: 700; } QPushButton:hover { background-color: rgba(56, 189, 248, 0.30); color: #fff; }")
                btn_st.clicked.connect(lambda _, p=fpath: self.execute_stage_file(p))
                r_lay.addWidget(btn_st)

                btn_del = QPushButton("🗑️ Eliminar")
                btn_del.setCursor(Qt.PointingHandCursor)
                btn_del.setStyleSheet("QPushButton { background-color: rgba(248, 113, 113, 0.12); color: #fca5a5; border: 1px solid rgba(248, 113, 113, 0.35); border-radius: 4px; padding: 2px 8px; font-size: 10.5px; font-weight: 600; } QPushButton:hover { background-color: rgba(248, 113, 113, 0.25); color: #fff; }")
                btn_del.clicked.connect(lambda _, p=fpath: self.execute_discard_file(p))
                r_lay.addWidget(btn_del)

            self.sync_files_layout.addWidget(row)

        self.sync_files_layout.addStretch()

    def render_sync_incoming_radar(self, status: dict):
        """Renderiza la telemetría de commits entrantes y salientes (Radar de Sincronización)."""
        while self.sync_radar_layout.count():
            item = self.sync_radar_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        behind_commits = status.get("behind_commits", [])
        ahead_commits = status.get("ahead_commits", [])
        incoming_stat = status.get("incoming_files_stat", "").strip()

        has_data = False

        # 1. Commits Entrantes (Behind)
        if behind_commits:
            has_data = True
            lbl_bh_h = QLabel(f"📥  COMMITS ENTRANTES DESDE EL REMOTO ({len(behind_commits)} pendientes de pull):")
            lbl_bh_h.setStyleSheet("font-size: 11.5px; font-weight: 800; color: #c084fc; letter-spacing: 0.5px;")
            self.sync_radar_layout.addWidget(lbl_bh_h)

            for c in behind_commits:
                crow = QFrame()
                crow.setStyleSheet("""
                    QFrame {
                        background-color: rgba(192, 132, 252, 0.05);
                        border: 1px solid rgba(192, 132, 252, 0.15);
                        border-radius: 6px;
                        padding: 4px 8px;
                    }
                """)
                c_lay = QHBoxLayout(crow)
                c_lay.setContentsMargins(8, 4, 8, 4)
                c_lay.setSpacing(10)

                h_badge = QLabel(c.get("hash", ""))
                h_badge.setStyleSheet("font-family: monospace; font-size: 11px; font-weight: 800; color: #c084fc; background: rgba(192, 132, 252, 0.15); border-radius: 3px; padding: 1px 6px;")
                c_lay.addWidget(h_badge)

                s_lbl = QLabel(c.get("subject", ""))
                s_lbl.setStyleSheet("font-size: 12px; font-weight: 700; color: #f3f4f6;")
                s_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
                c_lay.addWidget(s_lbl, 1)

                a_lbl = QLabel(f"{c.get('author', '')} • {c.get('time', '')}")
                a_lbl.setStyleSheet("font-size: 10.5px; color: #9ca3af;")
                c_lay.addWidget(a_lbl)

                self.sync_radar_layout.addWidget(crow)

            if incoming_stat:
                stat_card = QFrame()
                stat_card.setStyleSheet("""
                    QFrame {
                        background-color: rgba(0, 0, 0, 0.35);
                        border: 1px solid rgba(255, 255, 255, 0.08);
                        border-radius: 6px;
                        padding: 8px;
                    }
                """)
                sc_lay = QVBoxLayout(stat_card)
                sc_lay.setContentsMargins(6, 4, 6, 4)
                sc_lay.setSpacing(4)
                lbl_st_title = QLabel("Resumen de archivos modificados en el remoto (Pre-pull diff):")
                lbl_st_title.setStyleSheet("font-size: 10.5px; font-weight: 700; color: #9ca3af;")
                sc_lay.addWidget(lbl_st_title)

                txt_st = QTextEdit()
                txt_st.setReadOnly(True)
                txt_st.setMaximumHeight(110)
                txt_st.setPlainText(incoming_stat)
                txt_st.setStyleSheet("QTextEdit { background: transparent; border: none; font-family: monospace; font-size: 11px; color: #a5b4fc; }")
                sc_lay.addWidget(txt_st)
                self.sync_radar_layout.addWidget(stat_card)

        # 2. Commits Salientes (Ahead)
        if ahead_commits:
            has_data = True
            lbl_ah_h = QLabel(f"🚀  COMMITS SALIENTES LOCALES ({len(ahead_commits)} listos para push):")
            lbl_ah_h.setStyleSheet("font-size: 11.5px; font-weight: 800; color: #38bdf8; letter-spacing: 0.5px; margin-top: 6px;")
            self.sync_radar_layout.addWidget(lbl_ah_h)

            for c in ahead_commits:
                crow = QFrame()
                crow.setStyleSheet("""
                    QFrame {
                        background-color: rgba(56, 189, 248, 0.05);
                        border: 1px solid rgba(56, 189, 248, 0.15);
                        border-radius: 6px;
                        padding: 4px 8px;
                    }
                """)
                c_lay = QHBoxLayout(crow)
                c_lay.setContentsMargins(8, 4, 8, 4)
                c_lay.setSpacing(10)

                h_badge = QLabel(c.get("hash", ""))
                h_badge.setStyleSheet("font-family: monospace; font-size: 11px; font-weight: 800; color: #38bdf8; background: rgba(56, 189, 248, 0.15); border-radius: 3px; padding: 1px 6px;")
                c_lay.addWidget(h_badge)

                s_lbl = QLabel(c.get("subject", ""))
                s_lbl.setStyleSheet("font-size: 12px; font-weight: 700; color: #f3f4f6;")
                s_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
                c_lay.addWidget(s_lbl, 1)

                a_lbl = QLabel(f"{c.get('author', '')} • {c.get('time', '')}")
                a_lbl.setStyleSheet("font-size: 10.5px; color: #9ca3af;")
                c_lay.addWidget(a_lbl)

                self.sync_radar_layout.addWidget(crow)

        # 3. Estado en Sincronía
        if not has_data:
            synced_frame = QFrame()
            synced_frame.setStyleSheet("""
                QFrame {
                    background-color: rgba(52, 211, 153, 0.03);
                    border: 1px dashed rgba(52, 211, 153, 0.25);
                    border-radius: 8px;
                    padding: 24px;
                }
            """)
            sf_lay = QVBoxLayout(synced_frame)
            sf_lay.setAlignment(Qt.AlignCenter)
            lbl_ok = QLabel("✨  Repositorio 100% Sincronizado")
            lbl_ok.setStyleSheet("font-size: 13px; font-weight: 800; color: #34d399;")
            sf_lay.addWidget(lbl_ok)
            up = status.get("upstream") or "origin"
            lbl_ok_sub = QLabel(f"Tu rama local y la rama remota '{up}' están exactamente en paridad. No hay commits pendientes.")
            lbl_ok_sub.setStyleSheet("font-size: 11.5px; color: #9ca3af;")
            sf_lay.addWidget(lbl_ok_sub)
            self.sync_radar_layout.addWidget(synced_frame)

        self.sync_radar_layout.addStretch()

    def execute_status_inspect(self):
        """Audita en profundidad el estado del repositorio y emite telemetría detallada en la terminal."""
        path = self.project_data.get("path")
        if not path:
            return
        self.terminal_display.log("GIT-STATUS", "Ejecutando inspección táctica profunda del árbol de trabajo...", tag_color="#38bdf8", prefix="📋")
        self.refresh_sync_view()
        status = self.last_sync_status
        branch = status.get("branch", "HEAD")
        remote = status.get("remote", "origin")
        upstream = status.get("upstream", "Sin tracking")
        ahead = status.get("ahead", 0)
        behind = status.get("behind", 0)
        staged = status.get("total_staged", 0)
        unstaged = status.get("total_unstaged", 0)
        untracked = status.get("total_untracked", 0)
        adds = status.get("total_lines_added", 0)
        dels = status.get("total_lines_deleted", 0)
        stashes = status.get("stash_count", 0)
        rec = status.get("recommended_action", "Al día")

        self.terminal_display.log("GIT-STATUS", f"Rama activa: <b>{branch}</b> • Remoto: <b>{remote}</b> (<code>{upstream}</code>)", tag_color="#60a5fa", prefix="🌿")
        self.terminal_display.log("GIT-STATUS", f"Árbol local: <b>{unstaged}</b> modificado(s), <b>{staged}</b> en staging, <b>{untracked}</b> nuevo(s) • Deltas: <span style='color:#34d399;'>+{adds}</span> / <span style='color:#f87171;'>-{dels}</span> líneas", tag_color="#fbbf24", prefix="📁")
        self.terminal_display.log("GIT-STATUS", f"Red: <b>+{ahead}</b> Ahead | <b>-{behind}</b> Behind • Stashes: <b>{stashes}</b> guardado(s)", tag_color="#c084fc", prefix="🛰️")
        self.terminal_display.log_success("GIT-STATUS", f"Diagnóstico de sincronización: <b>{rec}</b>")

    def execute_fetch_action(self):
        """Inicia la descarga de metadatos remotos (fetch) en segundo plano."""
        path = self.project_data.get("path")
        if not path:
            return
        self.terminal_display.log("GIT-FETCH", "Contactando remotos y descargando metadatos con poda (git fetch --all --prune)...", tag_color="#c084fc", prefix="📡")
        self.btn_action_fetch.set_subtitle("Conectando con remotos...")
        self.fetch_thread = GitFetchThread(path, remote="", prune=True)
        self.fetch_thread.finished_fetch.connect(self._on_fetch_finished)
        self.fetch_thread.start()

    def _on_fetch_finished(self, ok: bool, msg: str, status: dict):
        """Callback cuando termina el hilo de fetch."""
        self.btn_action_fetch.set_subtitle("Consulta commits y ramas del remoto con poda (--prune) sin alterar código")
        if ok:
            self.terminal_display.log_success("GIT-FETCH", f"Fetch completado exitosamente.")
            behind = status.get("behind", 0)
            if behind > 0:
                self.terminal_display.log("GIT-FETCH", f"📥 Se detectaron <b>{behind}</b> commit(s) nuevos en el remoto. Pulsa <b>'Sincronizar Cambios (Pull)'</b> para integrarlos.", tag_color="#c084fc", prefix="⚡")
            else:
                self.terminal_display.log("GIT-FETCH", "✨ El repositorio local ya cuenta con los últimos commits del remoto.", tag_color="#34d399", prefix="✔")
        else:
            self.terminal_display.log_error("GIT-FETCH", f"Fallo al ejecutar git fetch:\n{msg}")

        self.refresh_sync_view()
        self.refresh_git_graph()

    def execute_pull_action(self):
        """Ejecuta git pull aplicando la estrategia táctica seleccionada."""
        path = self.project_data.get("path")
        if not path:
            return

        strat = self.cmb_pull_strategy.currentData() or "rebase"
        autostash = self.chk_pull_autostash.isChecked()
        strat_lbl = "Rebase + Autostash" if strat == "rebase" else ("Fast-Forward Only" if strat == "ff-only" else "Merge Commit")

        self.terminal_display.log("GIT-PULL", f"Iniciando sincronización mediante <b>{strat_lbl}</b>...", tag_color="#34d399", prefix="📥")
        self.btn_action_pull.set_subtitle("Descargando e integrando commits...")

        self.pull_thread = GitPullThread(path, strategy=strat, autostash=autostash)
        self.pull_thread.finished_pull.connect(self._on_pull_finished)
        self.pull_thread.start()

    def _on_pull_finished(self, ok: bool, msg: str):
        """Callback cuando finaliza git pull."""
        self.btn_action_pull.set_subtitle("Descarga e integra commits entrantes con Rebase + Autostash inteligente")
        if ok:
            self.terminal_display.log_success("GIT-PULL", f"Git Pull completado con éxito:\n{msg}")
        else:
            self.terminal_display.log_error("GIT-PULL", f"Fallo durante la sincronización Git Pull:\n{msg}")

        self.refresh_sync_view()
        self.refresh_current_project(reset_terminal=False)
        self.refresh_git_graph()

    def execute_stage_file(self, file_path: str):
        """Agrega un archivo individual al staging."""
        path = self.project_data.get("path")
        if not path:
            return
        ok, msg = execute_git_stage_path(path, file_path)
        if ok:
            self.terminal_display.log_git("STAGE", f"Archivo añadido a staging: <b>{file_path}</b>")
            self.refresh_sync_view()
            self.refresh_current_project(reset_terminal=False)
        else:
            self.terminal_display.log_error("STAGE", f"Error al añadir '{file_path}': {msg}")

    def execute_unstage_file(self, file_path: str):
        """Quita un archivo individual del staging."""
        path = self.project_data.get("path")
        if not path:
            return
        ok, msg = execute_git_unstage_path(path, file_path)
        if ok:
            self.terminal_display.log_git("UNSTAGE", f"Archivo retirado de staging: <b>{file_path}</b>")
            self.refresh_sync_view()
            self.refresh_current_project(reset_terminal=False)
        else:
            self.terminal_display.log_error("UNSTAGE", f"Error al retirar '{file_path}': {msg}")

    def execute_discard_file(self, file_path: str):
        """Descarta cambios locales en un archivo."""
        path = self.project_data.get("path")
        if not path:
            return
        self.terminal_display.log("DISCARD", f"Descartando modificaciones en <b>{file_path}</b>...", tag_color="#f87171", prefix="↺")
        ok, msg = execute_git_discard_path(path, file_path)
        if ok:
            self.terminal_display.log_warn("DISCARD", f"Cambios descartados en <b>{file_path}</b>.")
            self.refresh_sync_view()
            self.refresh_current_project(reset_terminal=False)
        else:
            self.terminal_display.log_error("DISCARD", f"Error al descartar '{file_path}': {msg}")

    def toggle_stash_drawer(self):
        """Alterna el cajón para guardar un stash rápido."""
        vis = not self.drawer_stash_save.isVisible()
        self.drawer_stash_save.setVisible(vis)
        if vis:
            self.txt_stash_msg.setFocus()
        if hasattr(self, "sector1_sub_stack"):
            self.sector1_sub_stack.updateGeometry()

    def execute_stash_save_action(self):
        """Guarda un stash con el mensaje especificado."""
        path = self.project_data.get("path")
        msg = self.txt_stash_msg.text().strip()
        if not path:
            return
        self.terminal_display.log("STASH", f"Guardando cambios en stash ('{msg or 'WIP'}')...", tag_color="#fde047", prefix="📦")
        ok, res = execute_git_stash_save(path, msg)
        if ok:
            self.terminal_display.log_success("STASH", f"Cambios guardados en stash exitosamente.")
            self.txt_stash_msg.clear()
            self.drawer_stash_save.setVisible(False)
            self.refresh_sync_view()
            self.refresh_current_project(reset_terminal=False)
        else:
            self.terminal_display.log_error("STASH", f"Error al guardar stash: {res}")

    def execute_stash_pop_action(self):
        """Restaura el stash más reciente en el árbol de trabajo."""
        path = self.project_data.get("path")
        if not path:
            return
        self.terminal_display.log("STASH", "Restaurando último stash (git stash pop)...", tag_color="#fde047", prefix="⚡")
        ok, res = execute_git_stash_pop(path)
        if ok:
            self.terminal_display.log_success("STASH", f"Stash restaurado en el árbol de trabajo exitosamente.")
            self.refresh_sync_view()
            self.refresh_current_project(reset_terminal=False)
        else:
            self.terminal_display.log_error("STASH", f"Error al restaurar stash:\n{res}")

    # -----------------------------------------------------------------
    # VISTA DE GRAFOS DE RAMAS (ESTILO GITHUB NETWORK GRAPH)
    # -----------------------------------------------------------------
    def toggle_terminal_graph_view(self):
        """Alterna entre el visor de Terminal y el Grafo de Ramas estilo GitHub Network."""
        if self.terminal_stack.currentIndex() == 0:
            # Pasar a vista de Grafo
            self.terminal_stack.setCurrentIndex(1)
            self.btn_toggle_graph_terminal.setText("📟  Ver Terminal de Salida")
            self.btn_toggle_graph_terminal.setStyleSheet("""
                QPushButton {
                    background-color: rgba(99, 102, 241, 0.22);
                    color: #c7d2fe;
                    border: 1px solid #818cf8;
                    border-radius: 5px;
                    padding: 4px 16px;
                    font-weight: 800;
                    font-size: 11.5px;
                    letter-spacing: 0.3px;
                }
                QPushButton:hover {
                    background-color: rgba(99, 102, 241, 0.35);
                    color: #ffffff;
                }
            """)
            self.lbl_t_title.setText("lumen-git-network@abraxas:~$")
            self.lbl_t_status.setText("🌐 GRAFO DE RAMAS [GITHUB NETWORK]")
            self.refresh_git_graph()
        else:
            # Volver a Terminal de salida
            self.terminal_stack.setCurrentIndex(0)
            self.btn_toggle_graph_terminal.setText("📊  Ver Grafo de Ramas (Network)")
            self.btn_toggle_graph_terminal.setStyleSheet("""
                QPushButton {
                    background-color: rgba(56, 189, 248, 0.14);
                    color: #38bdf8;
                    border: 1px solid rgba(56, 189, 248, 0.45);
                    border-radius: 5px;
                    padding: 4px 16px;
                    font-weight: 800;
                    font-size: 11.5px;
                    letter-spacing: 0.3px;
                }
                QPushButton:hover {
                    background-color: rgba(56, 189, 248, 0.30);
                    border-color: #38bdf8;
                    color: #ffffff;
                }
            """)
            self.lbl_t_title.setText("lumen-terminal@abraxas:~$")
            self.lbl_t_status.setText("⚡ VISOR DE SALIDA [READ-ONLY]")

    def toggle_terminal_collapsed(self):
        """Alterna la visibilidad o tamaño del panel de terminal según el modo actual."""
        in_docker = hasattr(self, "docker_side_terminal_container") and self.docker_side_terminal_container.isVisible()
        if in_docker:
            # Modo columna vertical en Docker
            is_visible = self.terminal_frame.isVisible()
            self.terminal_frame.setVisible(not is_visible)
            if hasattr(self, "btn_collapse_terminal"):
                self.btn_collapse_terminal.setText("◀" if is_visible else "▶")
                self.btn_collapse_terminal.setToolTip("Expandir panel lateral" if is_visible else "Ocultar panel lateral")
            if hasattr(self, "btn_top_toggle_term"):
                self.btn_top_toggle_term.setText("📟 Abrir Terminal" if is_visible else "📟 Terminal Lateral")
        else:
            # Modo inferior clásico en el resto de la aplicación
            is_stack_vis = self.terminal_stack.isVisible()
            if is_stack_vis:
                self.terminal_stack.setVisible(False)
                self.terminal_frame.setMinimumHeight(38)
                self.terminal_frame.setMaximumHeight(42)
                self.terminal_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                if hasattr(self, "btn_collapse_terminal"):
                    self.btn_collapse_terminal.setText("▲")
                    self.btn_collapse_terminal.setToolTip("Expandir panel de terminal")
                if hasattr(self, "btn_top_toggle_term"):
                    self.btn_top_toggle_term.setText("📟 Expandir Terminal")
            else:
                self.terminal_stack.setVisible(True)
                self.terminal_frame.setMinimumHeight(240)
                self.terminal_frame.setMaximumHeight(16777215)
                self.terminal_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                if hasattr(self, "btn_collapse_terminal"):
                    self.btn_collapse_terminal.setText("▼")
                    self.btn_collapse_terminal.setToolTip("Minimizar panel de terminal")
                if hasattr(self, "btn_top_toggle_term"):
                    self.btn_top_toggle_term.setText("📟 Terminal")

    def dock_terminal_in_docker(self):
        """Acopla la terminal en vertical a la derecha exclusivamente en el módulo de Docker."""
        if not hasattr(self, "docker_side_terminal_layout") or not hasattr(self, "bottom_terminal_container"):
            return
        self.bottom_terminal_container.setVisible(False)
        self.docker_side_terminal_container.setVisible(True)
        self.terminal_frame.setMinimumWidth(320)
        self.terminal_frame.setMaximumWidth(600)
        self.terminal_frame.setMinimumHeight(280)
        self.terminal_frame.setMaximumHeight(16777215)
        self.terminal_frame.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        if hasattr(self, "btn_collapse_terminal"):
            self.btn_collapse_terminal.setText("▶")
            self.btn_collapse_terminal.setToolTip("Ocultar panel lateral de terminal")
        self.docker_side_terminal_layout.addWidget(self.terminal_frame)

    def dock_terminal_at_bottom(self):
        """Restaura la terminal en su posición estándar inferior horizontal aprovechando todo el espacio libre."""
        if not hasattr(self, "bottom_terminal_layout") or not hasattr(self, "bottom_terminal_container"):
            return
        if hasattr(self, "docker_side_terminal_container"):
            self.docker_side_terminal_container.setVisible(False)
        self.bottom_terminal_container.setVisible(True)
        self.bottom_terminal_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.terminal_stack.setVisible(True)
        self.terminal_frame.setMinimumWidth(0)
        self.terminal_frame.setMaximumWidth(16777215)
        self.terminal_frame.setMinimumHeight(240)
        self.terminal_frame.setMaximumHeight(16777215)
        self.terminal_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        if hasattr(self, "btn_collapse_terminal"):
            self.btn_collapse_terminal.setText("▼")
            self.btn_collapse_terminal.setToolTip("Minimizar o expandir terminal")
        self.bottom_terminal_layout.addWidget(self.terminal_frame)

    def create_git_graph_view(self) -> QWidget:
        """Crea la vista de Grafo Horizontal de Ramas estilo VS Code Git Graph / GitHub Network."""
        widget = QWidget()
        widget.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        # Barra de cabecera interna del grafo
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(4, 2, 4, 2)
        top_bar.setSpacing(8)

        lbl_icon = QLabel("🌐")
        lbl_icon.setStyleSheet("font-size: 13px;")
        top_bar.addWidget(lbl_icon)

        lbl_title = QLabel("RED HORIZONTAL DE RAMAS")
        lbl_title.setStyleSheet("font-size: 11.5px; font-weight: 800; color: #38bdf8; letter-spacing: 0.5px;")
        top_bar.addWidget(lbl_title)

        lbl_sub = QLabel("• Estilo VS Code / GitHub Network (carriles paralelos, quiebres a 45° y nodos interactivos)")
        lbl_sub.setStyleSheet("font-size: 10.5px; color: #9ca3af;")
        top_bar.addWidget(lbl_sub)

        top_bar.addStretch()

        btn_head = QPushButton("🎯 Ir a HEAD")
        btn_head.setCursor(Qt.PointingHandCursor)
        btn_head.setStyleSheet("""
            QPushButton {
                background-color: rgba(56, 189, 248, 0.15);
                color: #bae6fd;
                border: 1px solid rgba(56, 189, 248, 0.35);
                border-radius: 4px;
                padding: 3px 10px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: rgba(56, 189, 248, 0.30);
                color: #ffffff;
            }
        """)
        btn_head.clicked.connect(lambda: self.git_graph_view.scroll_to_head() if hasattr(self, "git_graph_view") else None)
        top_bar.addWidget(btn_head)

        btn_root = QPushButton("⏪ Raíz")
        btn_root.setCursor(Qt.PointingHandCursor)
        btn_root.setStyleSheet(btn_head.styleSheet())
        btn_root.clicked.connect(lambda: self.git_graph_view.scroll_to_root() if hasattr(self, "git_graph_view") else None)
        top_bar.addWidget(btn_root)

        btn_zin = QPushButton("➕")
        btn_zin.setCursor(Qt.PointingHandCursor)
        btn_zin.setToolTip("Aumentar Zoom")
        btn_zin.setStyleSheet(btn_head.styleSheet())
        btn_zin.clicked.connect(lambda: self.git_graph_view.zoom_in() if hasattr(self, "git_graph_view") else None)
        top_bar.addWidget(btn_zin)

        btn_zout = QPushButton("➖")
        btn_zout.setCursor(Qt.PointingHandCursor)
        btn_zout.setToolTip("Disminuir Zoom")
        btn_zout.setStyleSheet(btn_head.styleSheet())
        btn_zout.clicked.connect(lambda: self.git_graph_view.zoom_out() if hasattr(self, "git_graph_view") else None)
        top_bar.addWidget(btn_zout)

        btn_zres = QPushButton("🔍 100%")
        btn_zres.setCursor(Qt.PointingHandCursor)
        btn_zres.setToolTip("Restablecer Zoom")
        btn_zres.setStyleSheet(btn_head.styleSheet())
        btn_zres.clicked.connect(lambda: self.git_graph_view.reset_zoom() if hasattr(self, "git_graph_view") else None)
        top_bar.addWidget(btn_zres)

        btn_refresh = QPushButton("🔄 Refrescar")
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.setStyleSheet(btn_head.styleSheet())
        btn_refresh.clicked.connect(self.refresh_git_graph)
        top_bar.addWidget(btn_refresh)

        layout.addLayout(top_bar)

        # -------------------------------------------------------------
        # Barra de Control y Añadidor Dinámico de Ramas (3 ramas por defecto)
        # -------------------------------------------------------------
        branches_bar = QHBoxLayout()
        branches_bar.setContentsMargins(4, 0, 4, 2)
        branches_bar.setSpacing(8)

        lbl_b_title = QLabel("🌿 RAMAS:")
        lbl_b_title.setStyleSheet("font-size: 11px; font-weight: 800; color: #9ca3af; letter-spacing: 0.5px;")
        branches_bar.addWidget(lbl_b_title)

        # Contenedor dinámico de chips de ramas visibles
        self.branch_chips_widget = QWidget()
        self.branch_chips_layout = QHBoxLayout(self.branch_chips_widget)
        self.branch_chips_layout.setContentsMargins(0, 0, 0, 0)
        self.branch_chips_layout.setSpacing(6)
        branches_bar.addWidget(self.branch_chips_widget)

        # Botón Añadir Rama (menú desplegable)
        self.btn_add_branch = QPushButton("➕ Añadir Rama")
        self.btn_add_branch.setCursor(Qt.PointingHandCursor)
        self.btn_add_branch.setToolTip("Añadir otra rama al visor horizontal")
        self.btn_add_branch.setStyleSheet("""
            QPushButton {
                background-color: rgba(99, 102, 241, 0.16);
                color: #c7d2fe;
                border: 1px dashed rgba(99, 102, 241, 0.45);
                border-radius: 4px;
                padding: 3px 10px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: rgba(99, 102, 241, 0.32);
                border-color: #818cf8;
                color: #ffffff;
            }
        """)
        self.btn_add_branch.clicked.connect(self.show_add_branch_menu)
        branches_bar.addWidget(self.btn_add_branch)

        # Botones rápidos Más / Menos Ramas
        btn_more = QPushButton("➕ Más")
        btn_more.setCursor(Qt.PointingHandCursor)
        btn_more.setToolTip("Añadir la siguiente rama disponible")
        btn_more.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.04);
                color: #e2e8f0;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 4px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(56, 189, 248, 0.20);
                border-color: #38bdf8;
                color: #ffffff;
            }
        """)
        btn_more.clicked.connect(lambda: self.git_graph_view.increase_branches() if hasattr(self, "git_graph_view") else None)
        branches_bar.addWidget(btn_more)

        btn_less = QPushButton("➖ Menos")
        btn_less.setCursor(Qt.PointingHandCursor)
        btn_less.setToolTip("Quitar la última rama añadida (mínimo 1)")
        btn_less.setStyleSheet(btn_more.styleSheet())
        btn_less.clicked.connect(lambda: self.git_graph_view.decrease_branches() if hasattr(self, "git_graph_view") else None)
        branches_bar.addWidget(btn_less)

        branches_bar.addStretch()

        self.lbl_branch_count = QLabel("3 ramas")
        self.lbl_branch_count.setStyleSheet("""
            background-color: rgba(56, 189, 248, 0.12);
            color: #38bdf8;
            border: 1px solid rgba(56, 189, 248, 0.30);
            border-radius: 4px;
            padding: 2px 8px;
            font-size: 10.5px;
            font-weight: 700;
        """)
        branches_bar.addWidget(self.lbl_branch_count)

        layout.addLayout(branches_bar)

        # Lienzo horizontal interactivo de ramas
        self.git_graph_view = LumenHorizontalGitGraphView()
        self.git_graph_view.setMinimumHeight(260)
        self.git_graph_view.commit_selected.connect(self.on_graph_commit_selected)
        self.git_graph_view.branches_updated.connect(self.update_branch_chips)
        layout.addWidget(self.git_graph_view, 1)

        # Pie de inspección rápida
        self.lbl_graph_inspector = QLabel("💡 Haz clic en cualquier nodo para inspeccionar el commit y ver su diff o detalles.")
        self.lbl_graph_inspector.setStyleSheet("""
            font-size: 11px;
            color: #9ca3af;
            background-color: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 4px;
            padding: 4px 10px;
            font-family: 'JetBrains Mono', 'Inter', monospace;
        """)
        layout.addWidget(self.lbl_graph_inspector)

        return widget

    def update_branch_chips(self, selected_branches: list, available_branches: list):
        """Actualiza los chips interactivos de ramas activas en la barra de control del grafo."""
        if not hasattr(self, "branch_chips_layout"):
            return

        # Limpiar chips anteriores
        while self.branch_chips_layout.count():
            item = self.branch_chips_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        from gui.views.lumen.git_graph_canvas import LUMEN_BRANCH_PALETTE

        for idx, b_name in enumerate(selected_branches):
            color = LUMEN_BRANCH_PALETTE[idx % len(LUMEN_BRANCH_PALETTE)].name()
            chip = QFrame()
            chip.setStyleSheet(f"""
                QFrame {{
                    background-color: rgba(255, 255, 255, 0.07);
                    border: 1px solid {color}99;
                    border-radius: 4px;
                    padding: 2px 8px;
                }}
            """)
            c_lay = QHBoxLayout(chip)
            c_lay.setContentsMargins(5, 2, 5, 2)
            c_lay.setSpacing(6)

            lbl_dot = QLabel("●")
            lbl_dot.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: bold;")
            c_lay.addWidget(lbl_dot)

            lbl_name = QLabel(b_name)
            lbl_name.setStyleSheet("color: #ffffff; font-size: 11px; font-weight: 700;")
            c_lay.addWidget(lbl_name)

            if len(selected_branches) > 1:
                btn_del = QPushButton("✕")
                btn_del.setCursor(Qt.PointingHandCursor)
                btn_del.setToolTip(f"Ocultar rama '{b_name}'")
                btn_del.setStyleSheet("""
                    QPushButton {
                        background: transparent;
                        border: none;
                        color: #9ca3af;
                        font-size: 10px;
                        font-weight: bold;
                        padding: 0px 2px;
                    }
                    QPushButton:hover {
                        color: #ef4444;
                    }
                """)
                btn_del.clicked.connect(lambda _, b=b_name: self.git_graph_view.remove_branch(b))
                c_lay.addWidget(btn_del)

            self.branch_chips_layout.addWidget(chip)

        count_text = f"{len(selected_branches)} {'rama' if len(selected_branches) == 1 else 'ramas'}"
        if hasattr(self, "lbl_branch_count"):
            self.lbl_branch_count.setText(count_text)

        remaining = [b for b in available_branches if b not in selected_branches]
        if hasattr(self, "btn_add_branch"):
            self.btn_add_branch.setEnabled(bool(remaining))
            self.btn_add_branch.setToolTip(f"{len(remaining)} ramas disponibles para añadir" if remaining else "Todas las ramas están visibles")

    def show_add_branch_menu(self):
        """Muestra menú contextual con las ramas disponibles para añadir al grafo."""
        if not hasattr(self, "git_graph_view") or not self.git_graph_view:
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #15161c;
                border: 1px solid #22242e;
                border-radius: 6px;
                padding: 4px;
                color: #f3f4f6;
            }
            QMenu::item {
                padding: 6px 14px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: rgba(99, 102, 241, 0.25);
                color: #ffffff;
            }
        """)

        available = getattr(self.git_graph_view, "available_branches", [])
        selected = getattr(self.git_graph_view, "selected_branches", [])
        remaining = [b for b in available if b not in selected]

        if not remaining:
            act = menu.addAction("Todas las ramas están visibles")
            act.setEnabled(False)
        else:
            for b in remaining:
                act = menu.addAction(f"🌿 {b}")
                act.triggered.connect(lambda _, b_name=b: self.git_graph_view.add_branch(b_name))

        menu.exec(self.btn_add_branch.mapToGlobal(QPoint(0, self.btn_add_branch.height() + 2)))

    def refresh_git_graph(self, simulated_merge: Optional[Dict[str, Any]] = None):
        """Carga en vivo el grafo horizontal de ramas según el proyecto activo."""
        path = self.project_data.get("path")
        if not path or not os.path.exists(path):
            return

        if hasattr(self, "git_graph_view"):
            self.git_graph_view.load_project_graph(path, simulated_merge=simulated_merge)

    def show_simulated_canvas(self):
        """Conmuta al visor horizontal de grafo para observar el nodo interactivo simulado."""
        self.terminal_stack.setCurrentIndex(1)
        self.lbl_t_status.setText("🌿 VISOR DE GRAFO [SIMULACIÓN]")
        path = self.project_data.get("path")
        if not path:
            return
        status = get_git_merge_status(path)
        src_b = self.selected_merge_source or status.get("current_branch", "HEAD")
        tgt_b = self.selected_merge_target or self.selected_merge_branch or "destino"
        m_title = self.txt_merge_title.text() or f"Fusión: {src_b} ➔ {tgt_b}"
        self.refresh_git_graph(simulated_merge={
            "source_branch": src_b,
            "target_branch": tgt_b,
            "title": m_title
        })


    def on_graph_commit_selected(self, commit_hash: str):
        """Manejador al hacer clic en un nodo de commit del grafo."""
        path = self.project_data.get("path")
        if not path or not commit_hash:
            return

        if commit_hash.startswith("~"):
            self.lbl_graph_inspector.setText("📌 🧪 [SIMULACIÓN ESTÉTICA] Nodo de fusión proyectado • Sin cambios aplicados en Git.")
            self.terminal_display.log("SIMULACIÓN", "Nodo seleccionado es una proyección táctica temporal (no destructiva).", tag_color="#c084fc", prefix="🧪")
            return

        try:
            out = subprocess.check_output(
                ["git", "show", "-s", "--format=%h | %an (%cr) | %s", commit_hash],
                cwd=path, stderr=subprocess.DEVNULL, text=True
            ).strip()
            self.lbl_graph_inspector.setText(f"📌 {out}")
        except Exception:
            self.lbl_graph_inspector.setText(f"📌 Commit seleccionado: {commit_hash}")

        self.inspect_git_commit(commit_hash)

    def inspect_git_commit(self, commit_hash: str):
        """Muestra la información y diff del commit seleccionado en la terminal."""
        path = self.project_data.get("path")
        if not path or not commit_hash:
            return

        self.terminal_display.log("COMMIT-INSPECT", f"Inspeccionando detalles del commit <code>{commit_hash}</code>...", tag_color="#fbbf24", prefix="🔍")
        try:
            out = subprocess.check_output(
                ["git", "show", "--stat", "--oneline", commit_hash],
                cwd=path, stderr=subprocess.DEVNULL, text=True
            )
            for l in out.splitlines()[:12]:
                self.terminal_display.log("DETAIL", l, tag_color="#a5b4fc", prefix="•")
        except Exception as e:
            self.terminal_display.log_error("COMMIT-INSPECT", str(e))

    def open_ia_audit_subview(self):
        """Abre la sub-vista de selección de modelo de IA para Auditoría de Diff."""
        self.sector1_sub_stack.setCurrentIndex(1)
        light_name = get_configured_model("light")
        heavy_name = get_configured_model("heavy")
        self.btn_diff_light.set_subtitle(f"Auditoría ágil y rápida del diff • Modelo configurado: {light_name}")
        self.btn_diff_heavy.set_subtitle(f"Auditoría exhaustiva y análisis profundo • Modelo configurado: {heavy_name}")
        self.terminal_display.log("WORKFLOW", "Accediendo a selección de modelo para <b>IA Audit</b> (Ligero / Pesado)...", tag_color="#38bdf8", prefix="🔍")

    def go_back_to_work_cycles(self):
        """Regresa a la página principal de Ciclos de Trabajo."""
        self.sector1_sub_stack.setCurrentIndex(0)
        if hasattr(self, "btn_toggle_graph_terminal"):
            self.btn_toggle_graph_terminal.setVisible(False)
        if hasattr(self, "terminal_stack") and self.terminal_stack.currentIndex() == 1:
            self.toggle_terminal_graph_view()
        self.hide_branches_action_drawer()
        if hasattr(self, "drawer_switch_dest"):
            self.drawer_switch_dest.setVisible(False)
        if hasattr(self, "merge_inner_stack"):
            self.merge_inner_stack.setCurrentIndex(0)
        self.terminal_display.log("NAV", "Regresando al menú de Ciclos de Trabajo.", tag_color="#9ca3af", prefix="◀")

    def go_back_to_sectors_overview(self):
        """Regresa directamente al menú principal de los 3 sectores en un solo clic."""
        self.dock_terminal_at_bottom()
        self.sectors_stack.setCurrentIndex(0)
        if hasattr(self, "sector1_sub_stack"):
            self.sector1_sub_stack.setCurrentIndex(0)
        if hasattr(self, "sector2_sub_stack"):
            self.sector2_sub_stack.setCurrentIndex(0)
        if hasattr(self, "btn_toggle_graph_terminal"):
            self.btn_toggle_graph_terminal.setVisible(False)
        if hasattr(self, "terminal_stack") and self.terminal_stack.currentIndex() == 1:
            self.toggle_terminal_graph_view()
        self.hide_branches_action_drawer()
        if hasattr(self, "drawer_switch_dest"):
            self.drawer_switch_dest.setVisible(False)
        if hasattr(self, "merge_inner_stack"):
            self.merge_inner_stack.setCurrentIndex(0)
        if hasattr(self, "drawer_stash_save"):
            self.drawer_stash_save.setVisible(False)
        self.terminal_display.log("NAV", "Regresando al menú principal de Sectores.", tag_color="#9ca3af", prefix="◀")

    # -----------------------------------------------------------------
    # ACCIONES REALES: GIT ADD, GIT PUSH E IA AUDIT
    # -----------------------------------------------------------------
    def run_git_add(self):
        """Ejecuta git add -A en el proyecto activo, actualiza el staging y refresca el HUD."""
        path = self.project_data.get("path")
        if not path or not os.path.exists(path):
            self.terminal_display.log_error("GIT-ADD", "No hay un proyecto activo seleccionado.")
            return

        self.terminal_display.log("GIT-ADD", "Ejecutando staging completo de archivos (git add -A)...", tag_color="#34d399", prefix="➕")
        try:
            res = subprocess.run(["git", "add", "-A"], cwd=path, capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                st_proc = subprocess.run(["git", "status", "--short"], cwd=path, capture_output=True, text=True, timeout=5)
                st_lines = st_proc.stdout.strip().splitlines() if st_proc.stdout.strip() else []
                
                self.terminal_display.log_success("GIT-ADD", f"Staging completado con éxito. {len(st_lines)} archivo(s) preparados para commit.")
                for line in st_lines[:6]:
                    self.terminal_display.log("STAGED", line, tag_color="#34d399", prefix="•")
                if len(st_lines) > 6:
                    self.terminal_display.log("STAGED", f"... y {len(st_lines)-6} archivo(s) más.", tag_color="#9ca3af", prefix="•")
                
                # Actualizar el HUD superior inmediatamente
                self.refresh_current_project()
            else:
                self.terminal_display.log_error("GIT-ADD", f"Error al ejecutar git add: {res.stderr.strip()}")
        except Exception as e:
            self.terminal_display.log_error("GIT-ADD", f"Excepción al ejecutar git add: {e}")

    def run_git_push(self, follow_tags: bool = False):
        """Ejecuta git push origin <rama> en segundo plano y proyecta los resultados en la terminal."""
        path = self.project_data.get("path")
        if not path or not os.path.exists(path):
            self.terminal_display.log_error("GIT-PUSH", "No hay un proyecto activo seleccionado.")
            return

        if self.push_thread and self.push_thread.isRunning():
            self.terminal_display.log_warn("GIT-PUSH", "Ya hay una operación de push en curso.")
            return

        # Aviso preventivo si hay cambios en stage que no han sido confirmados
        try:
            diff_cached = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=path, capture_output=True, text=True, timeout=3).stdout.strip()
            if diff_cached:
                self.terminal_display.log("GIT-PUSH", "⚠️ <b>Aviso:</b> Tienes cambios en stage aún no confirmados. Solo se enviarán los commits registrados.", tag_color="#fbbf24", prefix="ℹ")
        except Exception:
            pass

        tag_str = " (con etiquetas --follow-tags)" if follow_tags else ""
        self.terminal_display.log("GIT-PUSH", f"Iniciando envío de commits{tag_str} hacia el repositorio remoto...", tag_color="#60a5fa", prefix="🚀")
        
        self.push_thread = GitPushThread(path, follow_tags=follow_tags)
        self.push_thread.finished_push.connect(self.on_push_finished)
        self.push_thread.start()

    def on_push_finished(self, success: bool, branch: str, msg: str):
        """Callback al finalizar git push."""
        if success:
            self.terminal_display.log_success("GIT-PUSH", f"Commits sincronizados exitosamente con origin/{branch}.")
            if msg:
                for line in msg.splitlines()[:5]:
                    self.terminal_display.log("REMOTE", line, tag_color="#60a5fa", prefix="🌐")
            self.refresh_current_project(reset_terminal=False)
        else:
            self.terminal_display.log_error("GIT-PUSH", f"Fallo al realizar push a origin/{branch}: {msg}")

    def run_ai_diff_audit(self, model_type: str):
        """Ejecuta la auditoría inteligente de Diff con el modelo seleccionado (light o heavy)."""
        path = self.project_data.get("path")
        if not path or not os.path.exists(path):
            self.terminal_display.log_error("IA-AUDIT", "No hay un proyecto activo seleccionado.")
            return

        if self.audit_thread and self.audit_thread.isRunning():
            self.terminal_display.log_warn("IA-AUDIT", "Ya hay una auditoría de IA en curso. Espera a que termine.")
            return

        model_name = get_configured_model(model_type)
        m_label = "Modelo Ligero" if model_type == "light" else "Modelo Pesado"
        color = "#38bdf8" if model_type == "light" else "#c084fc"

        self.terminal_display.log("IA-AUDIT", f"Iniciando auditoría con <b>{m_label}</b> [<code>{model_name}</code>]...", tag_color=color, prefix="🔍")
        self.terminal_display.log_info("AI-ENGINE", "Extrayendo diff y procesando telemetría con Ollama...")

        self.audit_thread = IAAuditThread(path, model_type=model_type)
        self.audit_thread.finished_audit.connect(self.on_audit_finished)
        self.audit_thread.start()

    def on_audit_finished(self, success: bool, err_msg: str, res: dict):
        """Callback al recibir el resultado de la auditoría de IA."""
        if not success:
            self.terminal_display.log_warn("IA-AUDIT", err_msg)
            return

        model_name = res.get("model_name", "Ollama")
        audit_text = res.get("audit_text", "")

        self.terminal_display.log_success("IA-AUDIT", f"Auditoría generada exitosamente por <b>{model_name}</b>:")
        
        # Formatear el reporte de auditoría en un recuadro estilizado en la terminal
        formatted_html = audit_text.replace("\n", "<br>").replace("### ", "<b>").replace("## ", "<b>").replace("**", "<b>").replace("* ", "• ")
        box_html = (
            f"<div style='background-color: rgba(99, 102, 241, 0.08); border-left: 4px solid #818cf8; "
            f"padding: 10px 14px; margin: 8px 0; border-radius: 4px; font-family: sans-serif; font-size: 12px; "
            f"color: #f3f4f6; line-height: 1.5;'>"
            f"<div style='font-weight: 800; color: #a5b4fc; margin-bottom: 6px; font-family: monospace;'>"
            f"📊 REPORTE DE AUDITORÍA DE DIFF [{model_name}]:"
            f"</div>"
            f"{formatted_html}"
            f"</div>"
        )
        self.terminal_display.append(box_html)
        self.terminal_display.verticalScrollBar().setValue(self.terminal_display.verticalScrollBar().maximum())

    # -----------------------------------------------------------------
    # FLUJO DE IA COMMIT (VERSIONS ➔ MODEL ➔ CONFIRM ➔ PUSH)
    # -----------------------------------------------------------------
    def start_ia_commit_workflow(self):
        """Inicia el flujo de commit semántico con IA según los protocolos de Abraxas."""
        path = self.project_data.get("path")
        if not path or not os.path.exists(path):
            self.terminal_display.log_error("IA-COMMIT", "No hay un proyecto activo seleccionado.")
            return

        # 1. Comprobar si hay cambios preparados (staged)
        st_proc = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=path, capture_output=True, text=True, timeout=5)
        staged_files = st_proc.stdout.strip().splitlines() if st_proc.stdout.strip() else []
        
        if not staged_files:
            # Comprobar si hay cambios sin preparar para dar mensaje orientativo
            u_proc = subprocess.run(["git", "diff", "--name-only"], cwd=path, capture_output=True, text=True, timeout=5)
            unstaged_files = u_proc.stdout.strip().splitlines() if u_proc.stdout.strip() else []
            if unstaged_files:
                self.terminal_display.log("IA-COMMIT", "❌ <b>Stage vacío</b>. Tienes archivos modificados pero no preparados. Ejecuta <b>➕ Add (Preparar Cambios)</b> primero.", tag_color="#f87171", prefix="⚠️")
            else:
                self.terminal_display.log("IA-COMMIT", "❌ <b>Árbol de trabajo limpio</b>. No hay modificaciones pendientes para confirmar en commit.", tag_color="#f87171", prefix="⚠️")
            return

        # 2. Calcular versiones SemVer
        cur_ver = get_project_semver(path)
        next_gamma = bump_semver(cur_ver, "GAMMA")
        next_beta = bump_semver(cur_ver, "BETA")
        next_alpha = bump_semver(cur_ver, "ALPHA")

        self.lbl_semver_title.setText(f"❖ CONTROL DE VERSIONES (SemVer: {cur_ver}) ❖")
        self.btn_gamma.set_title(f"1. GAMMA (Patch) ➔ {next_gamma}")
        self.btn_gamma.set_subtitle(f"Fix, ajuste menor, docs • Siguiente versión: {next_gamma}")

        self.btn_beta.set_title(f"2. BETA (Minor) ➔ {next_beta}")
        self.btn_beta.set_subtitle(f"Nuevo módulo, funcionalidad • Siguiente versión: {next_beta}")

        self.btn_alpha.set_title(f"3. ALPHA (Major) ➔ {next_alpha}")
        self.btn_alpha.set_subtitle(f"Reestructuración masiva o cambio mayor • Siguiente versión: {next_alpha}")

        self.btn_omit.set_title(f"4. Continuar versión ➔ {cur_ver}")
        self.btn_omit.set_subtitle(f"Continuar en la versión actual {cur_ver} (sin generar nuevo tag)")

        self.cur_semver_options = {
            "GAMMA": next_gamma,
            "BETA": next_beta,
            "ALPHA": next_alpha,
            "OMIT": cur_ver
        }

        self.sector1_sub_stack.setCurrentIndex(2)
        self.terminal_display.log("IA-COMMIT", f"Iniciando protocolo de commit. Versión base detectada: <b style='color:#fbbf24;'>{cur_ver}</b>.", tag_color="#c084fc", prefix="🤖")
        self.terminal_display.log("STAGE", f"{len(staged_files)} archivo(s) preparados en staging listos para sintetizar.", tag_color="#34d399", prefix="📦")

    def select_semver_impact(self, impact_type: str):
        """Maneja la selección del nivel de impacto SemVer y pasa a seleccionar el motor de IA."""
        self.selected_impact = impact_type
        self.selected_target_ver = self.cur_semver_options.get(impact_type, "v0.1.0")

        # Cargar nombres de modelos configurados
        light_name = get_configured_model("light")
        heavy_name = get_configured_model("heavy")

        self.btn_commit_hex.set_title(f"1. HEX ({light_name} - Rápido)")
        self.btn_commit_hex.set_subtitle(f"Generación ágil y concisa de título y cuerpo semántico • {light_name}")

        self.btn_commit_hen.set_title(f"2. HENDRIX ({heavy_name} - Pesado/Inteligente)")
        self.btn_commit_hen.set_subtitle(f"Análisis exhaustivo del diff y redacción técnica profunda • {heavy_name}")

        self.sector1_sub_stack.setCurrentIndex(3)
        self.terminal_display.log("SEMVER", f"Impacto seleccionado: <b style='color:#34d399;'>{impact_type}</b> ➔ <b>{self.selected_target_ver}</b>.", tag_color="#34d399", prefix="🟢")

    def start_commit_model_generation(self, model_type: str):
        """Inicia la generación de la propuesta de commit con el modelo seleccionado (HEX o HENDRIX)."""
        path = self.project_data.get("path")
        if not path:
            return

        if self.commit_thread and self.commit_thread.isRunning():
            self.terminal_display.log_warn("IA-COMMIT", "Ya hay una generación de commit en curso. Por favor espera.")
            return

        self.selected_model_type = model_type
        model_name = get_configured_model(model_type)
        id_prefix = "HEX" if model_type == "light" else "HEN"

        # Actualizar textos de carga
        self.lbl_commit_loading_title.setText(f"GENERANDO PROPUESTA DE COMMIT CON {model_name.upper()}...")
        self.lbl_commit_loading_sub.setText(f"Motor: {id_prefix} ({model_type.upper()}) | Nivel de impacto: {self.selected_impact} [{self.selected_target_ver}]")

        self.sector1_sub_stack.setCurrentIndex(4)

        self.terminal_display.log("IA-COMMIT", f"Invocando red neuronal <b>{model_name}</b> ({id_prefix}) con impacto <b style='color:#fbbf24;'>{self.selected_impact}</b>...", tag_color="#ec4899", prefix="⏳")
        self.terminal_display.log_info("AI-ENGINE", "Extrayendo git diff en staging y aplicando directivas de razonamiento de IA...")

        self.commit_thread = IACommitThread(
            project_path=path,
            model_type=model_type,
            impact_type=self.selected_impact,
            target_ver=self.selected_target_ver
        )
        self.commit_thread.finished_commit.connect(self.on_commit_proposal_generated)
        self.commit_thread.start()

    def on_commit_proposal_generated(self, success: bool, err_msg: str, res: dict):
        """Callback al recibir la propuesta de commit generada por la IA."""
        if not success:
            self.terminal_display.log_error("IA-COMMIT", f"Error al generar commit con IA: {err_msg}")
            self.sector1_sub_stack.setCurrentIndex(3)
            return

        self.current_commit_proposal = res
        model_name = res.get("model_name", "Ollama")
        id_prefix = res.get("id_prefix", "HEX")
        commit_header = res.get("commit_header", "HEX:0001")
        title = res.get("title", "")
        body = res.get("body", "")
        impact = res.get("impact_type", "GAMMA")
        ver = res.get("target_ver", "v0.1.0")

        # Proyectar en la terminal inferior el resultado
        self.terminal_display.log("IA-COMMIT", f"Propuesta de commit generada exitosamente por <b>{model_name}</b>:", tag_color="#34d399", prefix="✔")

        report_box = (
            f"<div style='background-color: rgba(16, 185, 129, 0.08); border-left: 4px solid #34d399; "
            f"padding: 10px 14px; margin: 8px 0; border-radius: 4px; font-family: monospace; font-size: 12px; "
            f"color: #f3f4f6; line-height: 1.5;'>"
            f"<div style='font-weight: 800; color: #fbbf24; margin-bottom: 4px;'>"
            f"❖ PROPUESTA DE COMMIT ABRAXAS ({id_prefix}) ❖"
            f"</div>"
            f"<div style='margin-bottom: 2px;'><b style='color: #38bdf8;'>TÍTULO:</b> {commit_header} | {title}</div>"
            f"<div style='margin-bottom: 6px;'><b style='color: #c084fc;'>IMPACTO:</b> {impact} (Versión: {ver})</div>"
            f"<div><b style='color: #34d399;'>CUERPO:</b><br>{body}</div>"
            f"</div>"
        )
        self.terminal_display.append(report_box)
        self.terminal_display.verticalScrollBar().setValue(self.terminal_display.verticalScrollBar().maximum())

        # Actualizar tarjeta de confirmación en la UI
        self.lbl_prop_title.setText(f"TÍTULO: {commit_header} | {title}")
        self.lbl_prop_impact.setText(f"IMPACTO: {impact} (Versión: {ver})")
        self.lbl_prop_body.setText(f"CUERPO:\n{body}")

        # Pasar a la pantalla de confirmación (Página 5)
        self.sector1_sub_stack.setCurrentIndex(5)

    def confirm_and_record_commit(self):
        """Confirma y graba el commit y etiqueta SemVer en Git."""
        path = self.project_data.get("path")
        if not path or not self.current_commit_proposal:
            self.terminal_display.log_error("COMMIT", "No hay una propuesta de commit válida para confirmar.")
            return

        res = self.current_commit_proposal
        commit_header = res.get("commit_header", "HEX:0001")
        title = res.get("title", "")
        body = res.get("body", "")
        impact = res.get("impact_type", "GAMMA")
        ver = res.get("target_ver", "v0.1.0")

        self.terminal_display.log("COMMIT", f"Registrando commit en Git (<code>{commit_header} | {title}</code>)...", tag_color="#34d399", prefix="💾")

        ok, output = execute_commit_and_tag(
            project_path=path,
            commit_header=commit_header,
            title=title,
            body=body,
            impact_type=impact,
            target_ver=ver
        )

        if ok:
            self.terminal_display.log_success("COMMIT", f"Commit registrado con éxito en Git: <b>{commit_header} | {title}</b>")
            if impact != "OMIT" and ver:
                self.terminal_display.log("TAG", f"Etiqueta de versión SemVer <b>{ver}</b> creada.", tag_color="#818cf8", prefix="🏷️")

            # Refrescar el HUD sin borrar la salida de la terminal
            self.refresh_current_project(reset_terminal=False)

            # Pasar a la pantalla post-commit (Página 6: Opción a Push)
            self.sector1_sub_stack.setCurrentIndex(6)
        else:
            self.terminal_display.log_error("COMMIT", f"Error al ejecutar commit: {output}")

    def discard_commit_proposal(self):
        """Descarta la propuesta de commit generada y regresa a Ciclos de Trabajo."""
        self.current_commit_proposal = {}
        self.terminal_display.log("COMMIT", "Propuesta de commit descartada por el operador. No se realizaron cambios.", tag_color="#9ca3af", prefix="❌")
        self.sector1_sub_stack.setCurrentIndex(0)

    def execute_post_commit_push(self):
        """Ejecuta git push --follow-tags hacia el repositorio remoto y vuelve al menú."""
        self.sector1_sub_stack.setCurrentIndex(0)
        self.run_git_push(follow_tags=True)

    def discard_post_commit_push(self):
        """Omite el push y regresa directamente al menú principal de Ciclos de Trabajo."""
        self.terminal_display.log("PUSH", "Push remoto omitido. Los commits y etiquetas quedan guardados localmente.", tag_color="#9ca3af", prefix="ℹ")
        self.sector1_sub_stack.setCurrentIndex(0)

    def start_manual_commit_workflow(self):
        """Inicia el formulario de redacción de commit manual comprobando primero el estado de staging."""
        path = self.project_data.get("path")
        if not path or not os.path.exists(path):
            self.terminal_display.log_error("COMMIT", "No hay un proyecto activo seleccionado.")
            return

        # 1. Comprobar si hay cambios preparados (staged)
        st_proc = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=path, capture_output=True, text=True, timeout=5)
        staged_files = st_proc.stdout.strip().splitlines() if st_proc.stdout.strip() else []
        
        if not staged_files:
            u_proc = subprocess.run(["git", "diff", "--name-only"], cwd=path, capture_output=True, text=True, timeout=5)
            unstaged_files = u_proc.stdout.strip().splitlines() if u_proc.stdout.strip() else []
            if unstaged_files:
                self.terminal_display.log("COMMIT", "❌ <b>Stage vacío</b>. Tienes archivos modificados pero no preparados. Ejecuta <b>➕ Add (Preparar Cambios)</b> primero.", tag_color="#f87171", prefix="⚠️")
            else:
                self.terminal_display.log("COMMIT", "❌ <b>Árbol de trabajo limpio</b>. No hay modificaciones pendientes para confirmar en commit.", tag_color="#f87171", prefix="⚠️")
            return

        # 2. Cargar opciones SemVer
        cur_ver = get_project_semver(path)
        next_gamma = bump_semver(cur_ver, "GAMMA")
        next_beta = bump_semver(cur_ver, "BETA")
        next_alpha = bump_semver(cur_ver, "ALPHA")

        self.cmb_manual_semver.clear()
        self.cmb_manual_semver.addItem(f"Continuar en versión actual ({cur_ver}, sin tag)", ("OMIT", cur_ver))
        self.cmb_manual_semver.addItem(f"GAMMA (Patch / Fix) ➔ {next_gamma}", ("GAMMA", next_gamma))
        self.cmb_manual_semver.addItem(f"BETA (Minor / Feat) ➔ {next_beta}", ("BETA", next_beta))
        self.cmb_manual_semver.addItem(f"ALPHA (Major / Breaking) ➔ {next_alpha}", ("ALPHA", next_alpha))

        self.txt_manual_title.clear()
        self.txt_manual_body.clear()

        # Cambiar a la sub-página 7 (Commit Manual)
        self.sector1_sub_stack.setCurrentIndex(7)
        self.txt_manual_title.setFocus()

        self.terminal_display.log("COMMIT", f"Abriendo editor de commit manual. <b>{len(staged_files)}</b> archivo(s) listos en staging.", tag_color="#fbbf24", prefix="✍️")

    def execute_manual_commit(self):
        """Ejecuta el commit manual redactado por el usuario y crea el tag si aplica."""
        path = self.project_data.get("path")
        if not path:
            self.terminal_display.log_error("COMMIT", "No hay un proyecto activo seleccionado.")
            return

        raw_title = self.txt_manual_title.text().strip()
        if not raw_title:
            self.terminal_display.log_error("COMMIT", "Debes ingresar al menos un título o mensaje para el commit.")
            self.txt_manual_title.setFocus()
            return

        body = self.txt_manual_body.toPlainText().strip()
        sem_data = self.cmb_manual_semver.currentData()
        impact_type, target_ver = sem_data if sem_data else ("OMIT", "")

        next_id = get_next_commit_seq(path)
        header = f"MAN:{next_id}"
        if target_ver:
            header = f"MAN:{next_id} [{target_ver}]"

        self.terminal_display.log("COMMIT", f"Registrando commit manual (<code>{header} | {raw_title}</code>)...", tag_color="#34d399", prefix="💾")

        ok, output = execute_commit_and_tag(
            project_path=path,
            commit_header=header,
            title=raw_title,
            body=body,
            impact_type=impact_type,
            target_ver=target_ver
        )

        if ok:
            self.terminal_display.log_success("COMMIT", f"Commit registrado con éxito en Git: <b>{header} | {raw_title}</b>")
            if impact_type != "OMIT" and target_ver:
                self.terminal_display.log("TAG", f"Etiqueta de versión SemVer <b>{target_ver}</b> creada.", tag_color="#818cf8", prefix="🏷️")

            self.refresh_current_project(reset_terminal=False)
            # Pasar a la pantalla post-commit (Página 6: Opción a Push)
            self.sector1_sub_stack.setCurrentIndex(6)
        else:
            self.terminal_display.log_error("COMMIT", f"Error al ejecutar commit: {output}")

    # -----------------------------------------------------------------
    # MÉTODOS DE RELOJ, LOGS Y ACCIONES GENÉRICAS
    # -----------------------------------------------------------------
    def update_clock(self):
        """Actualiza la hora actual en tiempo real."""
        now_str = datetime.now().strftime("%H:%M:%S")
        self.lbl_current_time.setText(now_str)

    def copy_terminal_output(self):
        """Copia el texto plano actual del visor al portapapeles del sistema."""
        text = self.terminal_display.toPlainText()
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            self.terminal_display.log_info("CLIPBOARD", "Contenido del visor copiado al portapapeles.")

    def clear_terminal_output(self):
        """Limpia el contenido del visor terminal."""
        self.terminal_display.clear()
        p_name = self.project_data.get("name", "Proyecto")
        self.terminal_display.log(
            "READY", 
            f"Terminal lista para <b>{p_name}</b>.", 
            tag_color="#34d399", 
            prefix="❯"
        )

    def handle_action_click(self, action_title: str):
        """Maneja el clic interactivo en las acciones y proyecta el log coloreado en la terminal."""
        p_name = self.project_data.get("name", "Proyecto")
        
        actions_map = {
            "Ciclos de Trabajo": ("WORKFLOW", f"Accediendo al menú de <b>Ciclos de Trabajo</b> para <b>{p_name}</b>...", "#38bdf8", "🔄"),
            "IA Commit (Generar commit)": ("IA-COMMIT", f"Analizando cambios en staging para generar propuesta semántica de commit...", "#c084fc", "🤖"),
            "Commit Manual": ("COMMIT", f"Abriendo formulario para redacción de commit manual...", "#fbbf24", "✍️"),
            "Control de Ramas": ("GIT-BRANCH", f"Consultando matriz de ramas para <b>{p_name}</b>... (git branch -a)", "#c084fc", "🌿"),
            "Fusión de Ramas": ("GIT-MERGE", f"Preparando interfaz de fusión (merge) para <b>{p_name}</b>...", "#38bdf8", "🔀"),
            "Estado y Sincronización": ("GIT-SYNC", f"Verificando estado del árbol de trabajo (Status / Fetch / Pull)...", "#34d399", "⚡"),
            "Ejecutar proyecto en editor": ("IDE", f"Lanzando espacio de trabajo de <b>{p_name}</b> en editor externo...", "#38bdf8", "💻"),
            "Entornos python": ("VENV", f"Inspeccionando dependencias y entorno virtual de <b>{p_name}</b>...", "#fbbf24", "🐍"),
            "Docker y puertos": ("DOCKER", f"Verificando servicios Docker y mapeo de puertos para <b>{p_name}</b>...", "#60a5fa", "🐳"),
            "Gestor de gitignore": ("GITIGNORE", f"Analizando reglas y plantillas de exclusión en <code>.gitignore</code>...", "#c084fc", "🛡️"),
            "Lector de documentación": ("DOCS", f"Cargando lector de documentación y archivos README...", "#818cf8", "📖"),
            "Utilidades IA": ("AI-COPILOT", f"Iniciando puente de telemetría con modelo de IA local (Ollama)...", "#ec4899", "🤖"),
            "Usuario Git": ("USER", f"Consultando perfil de autor, correo y llaves de firma Git...", "#fbbf24", "👤")
        }

        if action_title in actions_map:
            tag, msg, color, prefix = actions_map[action_title]
            self.terminal_display.log(tag, msg, tag_color=color, prefix=prefix)
        else:
            self.terminal_display.log_info("ACTION", f"Ejecutando acción: <b>{action_title}</b>...")

    def set_project(self, folder_data: dict, reset_terminal: bool = True):
        """Sincroniza y carga en tiempo real la información del proyecto seleccionado en el HUD y terminal coloreada."""
        self.project_data = folder_data
        sync = get_full_project_sync(folder_data)
        is_git = sync.get("git_info", {}).get("is_git", False)
        self.is_project_git = is_git

        # 0. El panel superior SIEMPRE se muestra (contiene Proyecto, Entorno Python, Docker y Hora)
        self.hud_card.setVisible(True)

        # Ocultar exclusivamente los elementos dependientes de Git en el panel superior
        if hasattr(self, "row1_git_widget"):
            self.row1_git_widget.setVisible(is_git)
        if hasattr(self, "hud_row3_widget"):
            self.hud_row3_widget.setVisible(is_git)
        if hasattr(self, "hud_history_widget"):
            self.hud_history_widget.setVisible(is_git)

        if hasattr(self, "lbl_status_pill"):
            if is_git:
                self.lbl_status_pill.setText("🟢 SISTEMA CONECTADO")
                self.lbl_status_pill.setStyleSheet("""
                    background-color: rgba(16, 185, 129, 0.12);
                    color: #34d399;
                    border: 1px solid rgba(16, 185, 129, 0.35);
                    border-radius: 12px;
                    padding: 4px 12px;
                    font-size: 11px;
                    font-weight: 800;
                """)
            else:
                self.lbl_status_pill.setText("⚡ ENTORNOS ACTIVOS (SIN GIT)")
                self.lbl_status_pill.setStyleSheet("""
                    background-color: rgba(99, 102, 241, 0.15);
                    color: #a5b4fc;
                    border: 1px solid rgba(99, 102, 241, 0.35);
                    border-radius: 12px;
                    padding: 4px 12px;
                    font-size: 11px;
                    font-weight: 800;
                """)

        # Actualizar estado reactivo de los sectores 1 y 3
        if hasattr(self, "card_s1") and hasattr(self.card_s1, "set_git_state"):
            self.card_s1.set_git_state(is_git)
        if hasattr(self, "card_s3") and hasattr(self.card_s3, "set_git_state"):
            self.card_s3.set_git_state(is_git)

        # 1. Proyecto, Versión, Rama, Remoto
        self.lbl_proj_title.setText(f"{sync['name']} ({sync['version']})")
        self.lbl_proj_branch.setText(sync['git_info']['branch'])
        self.lbl_proj_remote.setText(sync['git_info']['remote'])

        if hasattr(self, "btn_repo_vis"):
            vis = sync.get('git_info', {}).get('visibility_info', {})
            if vis.get('has_remote') and vis.get('is_github'):
                is_priv = vis.get('is_private', True)
                btn_txt = "🔒 Privado (Cambiar)" if is_priv else "🌐 Público (Cambiar)"
                btn_color = "#f87171" if is_priv else "#34d399"
                self.btn_repo_vis.setText(btn_txt)
                self.btn_repo_vis.setToolTip("Click para cambiar la visibilidad entre Público y Privado en GitHub")
                self.btn_repo_vis.setStyleSheet(f"""
                    QPushButton {{
                        background-color: rgba(255, 255, 255, 0.04);
                        color: {btn_color};
                        border: 1px solid {btn_color}66;
                        border-radius: 5px;
                        padding: 2px 8px;
                        font-size: 11px;
                        font-weight: 700;
                    }}
                    QPushButton:hover {{
                        background-color: {btn_color}22;
                        border-color: {btn_color};
                    }}
                """)
                self.btn_repo_vis.setVisible(True)
            elif vis.get('has_remote'):
                self.btn_repo_vis.setText("🌐 Remoto")
                self.btn_repo_vis.setStyleSheet("""
                    QPushButton {{
                        background-color: rgba(255, 255, 255, 0.04);
                        color: #c7d2fe;
                        border: 1px solid rgba(199, 210, 254, 0.4);
                        border-radius: 5px;
                        padding: 2px 8px;
                        font-size: 11px;
                        font-weight: 700;
                    }}
                """)
                self.btn_repo_vis.setVisible(True)
            else:
                self.btn_repo_vis.setText("☁️ Publicar en GitHub")
                self.btn_repo_vis.setToolTip("Publicar este repositorio local en GitHub")
                self.btn_repo_vis.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(56, 189, 248, 0.15);
                        color: #38bdf8;
                        border: 1px solid rgba(56, 189, 248, 0.4);
                        border-radius: 5px;
                        padding: 2px 8px;
                        font-size: 11px;
                        font-weight: 700;
                    }
                    QPushButton:hover {
                        background-color: rgba(56, 189, 248, 0.3);
                        color: #ffffff;
                    }
                """)
                self.btn_repo_vis.setVisible(True)

        # 2. Entorno, Docker, Hora
        env_text = sync['env_info']['text']
        self.lbl_env_status.setText(env_text)
        if sync['env_info']['is_active']:
            self.lbl_env_status.setStyleSheet("font-weight: 800; color: #34d399; font-size: 13px;")
        else:
            self.lbl_env_status.setStyleSheet("font-weight: 700; color: #9ca3af; font-size: 13px;")

        self.lbl_docker_status.setText(sync['docker_info']['text'])
        self.lbl_current_time.setText(sync['timestamp'])

        # 3. Git HUD
        self.lbl_git_mod.setText(sync['git_hud']['mod_str'])
        self.lbl_git_untracked.setText(sync['git_hud']['untracked_str'])
        self.lbl_git_deleted.setText(sync['git_hud']['deleted_str'])

        # 4. Historial reciente (Commits en tiempo real)
        while self.history_items_layout.count():
            item = self.history_items_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            elif item.layout():
                sub_lay = item.layout()
                while sub_lay.count():
                    sub_item = sub_lay.takeAt(0)
                    if sub_item.widget():
                        sub_item.widget().deleteLater()

        commits = sync.get("commits", [])
        if commits:
            for c in commits:
                row_c = QHBoxLayout()
                row_c.setSpacing(8)

                lbl_dot = QLabel("◈")
                lbl_dot.setStyleSheet(f"color: {c.get('color', '#38bdf8')}; font-size: 12px;")
                row_c.addWidget(lbl_dot)

                lbl_time = QLabel(c['time'])
                lbl_time.setStyleSheet("font-family: monospace; font-size: 12px; color: #9ca3af; font-weight: 600; min-width: 85px;")
                row_c.addWidget(lbl_time)

                lbl_c_title = QLabel(c['title'])
                lbl_c_title.setStyleSheet("font-size: 12.5px; color: #f3f4f6; font-weight: 600;")
                row_c.addWidget(lbl_c_title, 1)

                lbl_author = QLabel(f"👤 {c['author']}")
                lbl_author.setStyleSheet("font-size: 12px; color: #9ca3af;")
                row_c.addWidget(lbl_author)

                lbl_br = QLabel(f"[{c['branch']}]")
                lbl_br.setStyleSheet("font-family: monospace; font-size: 11.5px; color: #818cf8; font-weight: 700;")
                row_c.addWidget(lbl_br)

                self.history_items_layout.addLayout(row_c)
        else:
            lbl_empty = QLabel("  • (No hay historial de commits registrado para este proyecto)")
            lbl_empty.setStyleSheet("font-family: monospace; font-size: 12px; color: #6b7280; font-style: italic;")
            self.history_items_layout.addWidget(lbl_empty)

        # 5. Visor de terminal coloreado con HTML y diseño ciber-ilustre
        p_name_clean = sync['name'].lower().replace(" ", "-")
        self.lbl_t_title.setText(f"lumen-terminal@{p_name_clean}:~$")

        if reset_terminal:
            # SIEMPRE resetear al panel general de los sectores al abrir un proyecto desde cero
            if hasattr(self, "sectors_stack"):
                self.sectors_stack.setCurrentIndex(0)
            if hasattr(self, "sector1_sub_stack"):
                self.sector1_sub_stack.setCurrentIndex(0)
            if hasattr(self, "sector2_sub_stack"):
                self.sector2_sub_stack.setCurrentIndex(0)

            self.terminal_display.clear()
            if is_git:
                self.terminal_display.log(
                    "KERNEL", 
                    f"Conectado a <b style='color:#fbbf24;'>{sync['name']}</b> <span style='color:#a5b4fc;'>[{sync['version']}]</span> en rama <b style='color:#38bdf8;'>{sync['git_info']['branch']}</b>",
                    tag_color="#818cf8",
                    prefix="❖"
                )
                self.terminal_display.log(
                    "READY",
                    "Esperando acciones...",
                    tag_color="#34d399",
                    prefix="❯"
                )
            else:
                self.terminal_display.log(
                    "KERNEL", 
                    f"Conectado a <b style='color:#fbbf24;'>{sync['name']}</b> <span style='color:#a5b4fc;'>[{sync['version']}]</span> • <span style='color:#f87171;'>Sin Repositorio Git</span>",
                    tag_color="#f87171",
                    prefix="⚠"
                )
                self.terminal_display.log_warn(
                    "GIT",
                    "Este proyecto no posee un repositorio Git inicializado. Los sectores 1 y 3 están restringidos. Pulsa <b>'Iniciar Proyecto Git'</b> en el Sector 1 para activarlo."
                )

        # 6. Sincronización y refresco automático del visor de grafo y terminal
        self.refresh_git_graph()

        if hasattr(self, "terminal_stack") and self.terminal_stack.currentIndex() == 1:
            self.lbl_t_title.setText(f"lumen-git-network@{p_name_clean}:~$")
            self.lbl_t_status.setText("🌐 GRAFO DE RAMAS [GITHUB NETWORK]")

    def refresh_current_project(self, reset_terminal: bool = False):
        """Re-sincroniza el proyecto actual con el disco."""
        if self.project_data:
            self.set_project(self.project_data, reset_terminal=reset_terminal)
            if hasattr(self, "sector1_sub_stack") and hasattr(self, "page_sync"):
                if self.sector1_sub_stack.currentWidget() == self.page_sync:
                    self.refresh_sync_view()
            self.terminal_display.log_success("SYNC", "HUD y estado del repositorio actualizados.")
