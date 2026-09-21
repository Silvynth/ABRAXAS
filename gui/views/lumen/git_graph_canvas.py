#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS | LUMEN - HORIZONTAL GIT BRANCH & NETWORK GRAPH
# =====================================================================
#  Lienzo de Grafo Horizontal de Ramas estilo extensiones de VS Code
#  (Git Graph / GitLens) y GitHub Network Graph.
#  - Carriles horizontales dedicados por rama con colores distintivos.
#  - Conectores diagonales ortogonales a 45° para divergencias/bifurcaciones.
#  - Nodos interactivos de commit con halos, hash, autor, fecha y badges.
#  - Pills visuales para HEAD, ramas locales, remotas y tags SemVer.
#  - Fondo limpio, translúcido e integrado con la estética glass de Lumen.
# =====================================================================

import os
import re
import subprocess
from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGraphicsView, QGraphicsScene, QGraphicsItem, QGraphicsPathItem,
    QFrame, QToolTip, QScrollBar
)
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QColor, QPainterPath,
    QFont, QCursor, QLinearGradient, QRadialGradient
)
from PySide6.QtCore import Qt, QPointF, QRectF, Signal, Slot


# Paleta cromática de carriles tácticos (Lumen Cyberpunk)
LUMEN_BRANCH_PALETTE = [
    QColor("#38bdf8"),  # 0: Sky Cyan (Lumen / Active HEAD)
    QColor("#818cf8"),  # 1: Indigo (NEOS / Core)
    QColor("#34d399"),  # 2: Emerald (Proyectos / Mainline)
    QColor("#fbbf24"),  # 3: Amber (Feature Branches)
    QColor("#f43f5e"),  # 4: Rose (Bugfixes / Stale)
    QColor("#c084fc"),  # 5: Purple (Hotfixes)
    QColor("#2dd4bf"),  # 6: Teal
    QColor("#fb923c"),  # 7: Orange
]


class GitGraphConnectorEdge(QGraphicsPathItem):
    """
    Arista de conexión entre commits con tramos horizontales
    y quiebres diagonales a 45° estilo circuito técnico / Git Graph.
    """

    def __init__(self, source_node, target_node, color: QColor, parent=None):
        super().__init__(parent)
        self.source = source_node
        self.target = target_node
        self.color = color
        self.setZValue(2)
        self.update_path()

    def update_path(self):
        if not self.source or not self.target:
            return

        p1 = self.source.get_center_pos()
        p2 = self.target.get_center_pos()

        # p1 es el commit padre (a la izquierda), p2 es el hijo (a la derecha)
        # o viceversa si el flujo es horizontal
        if p1.x() > p2.x():
            p1, p2 = p2, p1

        path = QPainterPath()
        path.moveTo(p1)

        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()

        if abs(dy) < 3:
            # Misma línea horizontal de rama
            path.lineTo(p2)
        else:
            # Bifurcación / Merge con quiebre diagonal a 45°
            diag_span = min(abs(dy), max(18.0, dx * 0.35))
            mid_x = p1.x() + (dx - diag_span) / 2.0

            path.lineTo(mid_x, p1.y())
            path.lineTo(mid_x + diag_span, p2.y())
            path.lineTo(p2)

        self.setPath(path)

        edge_color = QColor(self.color)
        edge_color.setAlpha(175)
        pen = QPen(edge_color, 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        self.setPen(pen)


class GitGraphCommitNode(QGraphicsItem):
    """
    Nodo interactivo de Commit en el carril horizontal de la rama.
    Incluye halo brillante, dot central, short hash, mensaje y badges (HEAD, Tags, Ramas).
    """

    def __init__(
        self,
        commit_data: Dict[str, Any],
        lane_idx: int,
        lane_color: QColor,
        is_head: bool = False,
        on_click_cb = None,
        parent = None
    ):
        super().__init__(parent)
        self.data = commit_data
        self.lane_idx = lane_idx
        self.lane_color = lane_color
        self.is_head = is_head
        self.on_click_cb = on_click_cb

        self.hash = commit_data.get("hash", "")
        self.subject = commit_data.get("subject", "")
        self.author = commit_data.get("author", "")
        self.date = commit_data.get("date", "")
        self.refs = commit_data.get("refs", [])

        self.is_hovered = False
        self.is_selected = False
        self.dot_radius = 7.0 if not is_head else 8.5

        self.setFlags(QGraphicsItem.ItemIsSelectable)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setZValue(10 if not is_head else 15)

    def get_center_pos(self) -> QPointF:
        return self.scenePos()

    def boundingRect(self) -> QRectF:
        # Espacio para el nodo, halo, texto superior (hash/badges) y texto inferior (subject)
        return QRectF(-70, -42, 140, 85)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        # 1. Halo reactivo de carril
        is_sim = bool(self.data.get("is_simulation", False))
        halo_r = self.dot_radius + (7.0 if self.is_hovered else (4.5 if (self.is_head or is_sim) else 2.5))
        halo_color = QColor(self.lane_color)
        halo_color.setAlpha(160 if self.is_hovered else (90 if (self.is_head or is_sim) else 45))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(halo_color))
        painter.drawEllipse(QPointF(0, 0), halo_r, halo_r)

        # Anillo pulsante si es HEAD o SIMULACIÓN
        if is_sim:
            painter.setPen(QPen(QColor("#c084fc"), 1.8, Qt.DashDotLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QPointF(0, 0), halo_r + 3.5, halo_r + 3.5)
        elif self.is_head:
            painter.setPen(QPen(QColor("#38bdf8"), 1.6, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QPointF(0, 0), halo_r + 3.0, halo_r + 3.0)

        # 2. Cuerpo del punto Git
        painter.setPen(QPen(QColor(255, 255, 255, 220 if self.is_hovered else 140), 1.2))
        painter.setBrush(QBrush(self.lane_color))
        painter.drawEllipse(QPointF(0, 0), self.dot_radius, self.dot_radius)

        # 3. Núcleo central brillante
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(255, 255, 255, 240)))
        painter.drawEllipse(QPointF(0, 0), self.dot_radius * 0.38, self.dot_radius * 0.38)

        # 4. Hash del commit (Encima del nodo)
        f_hash = QFont("JetBrains Mono, monospace", 8.2)
        f_hash.setBold(True)
        painter.setFont(f_hash)
        if is_sim:
            painter.setPen(QColor("#c084fc"))
        else:
            painter.setPen(QColor("#fbbf24") if self.is_hovered else QColor("#bae6fd"))
        painter.drawText(QRectF(-45, -22, 90, 14), Qt.AlignCenter, self.hash)

        # 5. Badges de Ramas o Tags si existen en este commit (Por encima del hash)
        if is_sim:
            b_rect = QRectF(-55, -38, 110, 14)
            badge_color = QColor("#c084fc")
            painter.setPen(QPen(badge_color, 1))
            bg_b = QColor(badge_color)
            bg_b.setAlpha(55)
            painter.setBrush(QBrush(bg_b))
            painter.drawRoundedRect(b_rect, 3, 3)

            f_b = QFont("Inter, sans-serif", 7.5)
            f_b.setBold(True)
            painter.setFont(f_b)
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(b_rect, Qt.AlignCenter, "🧪 SIMULACIÓN")
        elif self.refs:
            top_ref = self.refs[0]
            badge_text = top_ref
            badge_color = self.lane_color
            if "HEAD" in top_ref:
                badge_text = "🌿 " + top_ref.replace("HEAD ->", "").strip()
                badge_color = QColor("#38bdf8")
            elif "tag:" in top_ref:
                badge_text = "🏷 " + top_ref.replace("tag:", "").strip()
                badge_color = QColor("#34d399")
            elif "origin/" in top_ref:
                badge_text = "🌐 " + top_ref.replace("origin/", "").strip()
                badge_color = QColor("#60a5fa")

            if len(badge_text) > 16:
                badge_text = badge_text[:14] + "…"

            b_rect = QRectF(-48, -38, 96, 14)
            painter.setPen(QPen(badge_color, 1))
            bg_b = QColor(badge_color)
            bg_b.setAlpha(45)
            painter.setBrush(QBrush(bg_b))
            painter.drawRoundedRect(b_rect, 3, 3)

            f_b = QFont("Inter, sans-serif", 7.5)
            f_b.setBold(True)
            painter.setFont(f_b)
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(b_rect, Qt.AlignCenter, badge_text)

        # 6. Título resumido del commit (Debajo del nodo)
        subj_clean = self.subject
        # Quitar prefijos tipo HEX:0024 | para ahorrar espacio en la vista miniatura
        subj_clean = re.sub(r"^(?:HEX|SIL|HEN|AGY|MAN):\d{4}(?:\s*\[v?[0-9.]+\])?\s*\|\s*", "", subj_clean).strip()
        if len(subj_clean) > 15:
            subj_clean = subj_clean[:14] + "…"

        f_subj = QFont("Inter, sans-serif", 7.8)
        painter.setFont(f_subj)
        painter.setPen(QColor("#f3f4f6") if self.is_hovered else QColor("#9ca3af"))
        painter.drawText(QRectF(-60, 10, 120, 15), Qt.AlignCenter, subj_clean)

        # 7. Autor y fecha muy compacto
        f_sub = QFont("Inter, sans-serif", 6.8)
        painter.setFont(f_sub)
        painter.setPen(QColor("#6b7280"))
        painter.drawText(QRectF(-60, 24, 120, 13), Qt.AlignCenter, f"{self.author} • {self.date}")

    def hoverEnterEvent(self, event):
        self.is_hovered = True
        self.update()
        # Tooltip enriquecido estilo VS Code
        tt = (
            f"<b>Commit {self.hash}</b><br>"
            f"<b>Autor:</b> {self.author} ({self.date})<br>"
            f"<b>Mensaje:</b> {self.subject}"
        )
        if self.refs:
            tt += f"<br><b>Refs:</b> {', '.join(self.refs)}"
        QToolTip.showText(event.screenPos(), tt)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.is_hovered = False
        self.update()
        QToolTip.hideText()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        if self.on_click_cb:
            self.on_click_cb(self.hash)
        super().mousePressEvent(event)


class LumenHorizontalGitGraphView(QGraphicsView):
    """
    Lienzo horizontal de Grafo de Ramas estilo VS Code Git Graph / GitHub Network.
    - Desplazamiento horizontal fluido (Drag hand y rueda del ratón).
    - Fondo translúcido integrado con la estética glass de Lumen.
    - Marcadores de carril y líneas guía sutiles.
    """

    commit_selected = Signal(str)      # Emite el hash corto del commit seleccionado
    checkout_requested = Signal(str)   # Emite el nombre de la rama o hash para checkout
    branches_updated = Signal(list, list) # Emite (selected_branches, available_branches)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.TextAntialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Diseño limpio y translúcido sin recuadro negro ni sombras duras
        self.setStyleSheet("""
            QGraphicsView {
                background: transparent;
                border: none;
            }
            QScrollBar:horizontal, QScrollBar:vertical {
                background: rgba(255, 255, 255, 0.02);
                height: 8px;
                width: 8px;
                border-radius: 4px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal, QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.12);
                border-radius: 4px;
                min-width: 24px;
                min-height: 24px;
            }
            QScrollBar::handle:horizontal:hover, QScrollBar::handle:vertical:hover {
                background: #38bdf8;
            }
            QScrollBar::add-line, QScrollBar::sub-line {
                width: 0px;
                height: 0px;
            }
        """)

        self.current_project_path = ""
        self.zoom_level = 1.0
        self.nodes = []
        self.edges = []
        self.head_node = None
        self.branches_detected = []
        self.selected_branches = []
        self.available_branches = []

        # Encabezado fijado de ramas (Freeze Header estilo Excel / VS Code)
        self.used_lanes = []
        self.lane_mapping = {}
        self.base_y = 50.0
        self.y_step = 70.0
        self.pinned_header_width = 145.0
        self.hovered_lane = None

        self.setMouseTracking(True)
        self.horizontalScrollBar().valueChanged.connect(self.viewport().update)
        self.verticalScrollBar().valueChanged.connect(self.viewport().update)

    def drawBackground(self, painter: QPainter, rect: QRectF):
        """Cuadrícula de puntos limpia sobre fondo transparente integrado con el tema."""
        super().drawBackground(painter, rect)

        grid_size = 28
        left = int(rect.left()) - (int(rect.left()) % grid_size)
        top = int(rect.top()) - (int(rect.top()) % grid_size)

        painter.setPen(QPen(QColor(255, 255, 255, 12), 1.0))
        x = left
        while x < rect.right():
            y = top
            while y < rect.bottom():
                painter.drawPoint(QPointF(x, y))
                y += grid_size
            x += grid_size

    def set_selected_branches(self, branches: List[str]):
        """Configura explícitamente la lista de ramas a mostrar y recarga el grafo."""
        self.selected_branches = [b.strip() for b in branches if b and b.strip()]
        if self.current_project_path:
            self.load_project_graph(self.current_project_path)

    def add_branch(self, branch_name: str):
        """Añade una rama adicional al visor de ramas (ver más ramas)."""
        clean = branch_name.strip()
        if clean and clean not in self.selected_branches:
            self.selected_branches.append(clean)
            if self.current_project_path:
                self.load_project_graph(self.current_project_path)

    def remove_branch(self, branch_name: str):
        """Remueve una rama del visor de ramas (ver menos ramas, mínimo 1)."""
        clean = branch_name.strip()
        if clean in self.selected_branches and len(self.selected_branches) > 1:
            self.selected_branches.remove(clean)
            if self.current_project_path:
                self.load_project_graph(self.current_project_path)

    def increase_branches(self):
        """Añade la siguiente rama disponible que no esté en pantalla."""
        for b in self.available_branches:
            if b not in self.selected_branches:
                self.add_branch(b)
                return

    def decrease_branches(self):
        """Reduce en 1 la cantidad de ramas en pantalla (manteniendo al menos 1)."""
        if len(self.selected_branches) > 1:
            self.remove_branch(self.selected_branches[-1])

    def load_project_graph(self, project_path: str, max_commits: int = 50, simulated_merge: Optional[Dict[str, Any]] = None):
        """Carga y genera el grafo horizontal de ramas a partir del historial git del proyecto."""
        if self.current_project_path != project_path:
            self.selected_branches = []
        self.current_project_path = project_path
        self.scene.clear()
        self.nodes.clear()
        self.edges.clear()
        self.head_node = None
        self.branches_detected.clear()
        self.used_lanes = []
        self.lane_mapping = {}
        self.hovered_lane = None

        if not project_path or not os.path.exists(project_path):
            self._render_empty_state("⚠️ No hay un proyecto Git activo seleccionado")
            return

        # 1. Obtener ramas y sus hashes de referencia
        branch_info = self._get_git_branches(project_path)
        self.branches_detected = branch_info

        # Detectar la rama activa actual (HEAD)
        active_branch = "main"
        try:
            active_branch = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=project_path, stderr=subprocess.DEVNULL, text=True
            ).strip() or "main"
        except Exception:
            pass

        # Lista unificada de nombres de ramas disponibles
        all_names = []
        if active_branch and active_branch != "HEAD":
            all_names.append(active_branch)
        for b in branch_info:
            bname = b.get("name", "")
            if bname and bname not in all_names and bname != "HEAD":
                all_names.append(bname)

        self.available_branches = all_names

        # Configurar 3 ramas por defecto si no hay selección previa válida
        if not self.selected_branches or not any(b in all_names for b in self.selected_branches):
            # Priorizar: 1) Activa actual, 2) y 3) Primeras ramas disponibles
            picked = [active_branch] if active_branch in all_names else []
            for b in all_names:
                if b not in picked:
                    picked.append(b)
                if len(picked) >= 3:
                    break
            self.selected_branches = picked if picked else [active_branch]
        else:
            # Mantener la selección válida
            self.selected_branches = [b for b in self.selected_branches if b in all_names]
            if not self.selected_branches:
                self.selected_branches = all_names[:3] if all_names else [active_branch]

        # Notificar a la UI sobre las ramas actualizadas
        self.branches_updated.emit(self.selected_branches, self.available_branches)

        # 2. Obtener historial cronológico / topológico de commits para las ramas seleccionadas
        commits = self._get_git_commits(project_path, max_commits, self.selected_branches)
        if not commits:
            self._render_empty_state("⚠️ No se encontraron commits en las ramas seleccionadas")
            return

        # 3. Asignación de carriles horizontales para las ramas seleccionadas
        lane_mapping, commit_lanes = self._calculate_branch_lanes(
            commits, branch_info, self.selected_branches, active_branch
        )

        # Ahora sí, ordenamos de más antiguo (izquierda) a más reciente (derecha) para el eje temporal
        commits.reverse()

        # 4. Dimensiones de la cuadrícula horizontal
        x_step = 100.0   # Espacio horizontal entre commits consecutivos
        y_step = 70.0    # Altura de carril de cada rama
        base_x = 180.0   # Margen izquierdo para dar espacio al encabezado fijado (pinned header)
        base_y = 50.0

        self.base_y = base_y
        self.y_step = y_step
        self.used_lanes = sorted(set(commit_lanes.values())) if commit_lanes else [0]
        self.lane_mapping = lane_mapping

        # Dibujar guías de carril solo para los carriles que realmente contienen commits
        total_guide_width = base_x + (len(commits) + (2 if simulated_merge else 1)) * x_step + 60

        for lane_idx in self.used_lanes:
            color = LUMEN_BRANCH_PALETTE[lane_idx % len(LUMEN_BRANCH_PALETTE)]
            lane_y = base_y + lane_idx * y_step

            # Línea guía horizontal continua y sutil
            guide_path = QPainterPath()
            guide_path.moveTo(0, lane_y)
            guide_path.lineTo(total_guide_width, lane_y)
            guide_item = QGraphicsPathItem(guide_path)
            guide_pen = QPen(QColor(color.red(), color.green(), color.blue(), 35), 1.0, Qt.DashLine)
            guide_item.setPen(guide_pen)
            guide_item.setZValue(0)
            self.scene.addItem(guide_item)

        # 5. Instanciar Nodos de Commit
        node_by_hash = {}
        for idx, c in enumerate(commits):
            chash = c["hash"]
            lane = commit_lanes.get(chash, 0)
            color = LUMEN_BRANCH_PALETTE[lane % len(LUMEN_BRANCH_PALETTE)]
            is_head = any("HEAD" in r for r in c.get("refs", []))

            x = base_x + idx * x_step
            y = base_y + lane * y_step

            node = GitGraphCommitNode(
                commit_data=c,
                lane_idx=lane,
                lane_color=color,
                is_head=is_head,
                on_click_cb=self._on_node_clicked
            )
            node.setPos(x, y)
            self.scene.addItem(node)
            self.nodes.append(node)
            node_by_hash[chash] = node

            if is_head or idx == len(commits) - 1:
                self.head_node = node

        # 6. Instanciar Aristas Conectoras (Líneas horizontales y quiebres a 45°)
        for c in commits:
            child_node = node_by_hash.get(c["hash"])
            if not child_node:
                continue

            for parent_hash in c.get("parents", []):
                parent_node = node_by_hash.get(parent_hash)
                if parent_node:
                    edge = GitGraphConnectorEdge(parent_node, child_node, child_node.lane_color)
                    self.scene.addItem(edge)
                    self.edges.append(edge)

        # 6.5. Simulación Estética de Fusión (Nodo Fantasma interactivo)
        if simulated_merge and self.nodes:
            src_b = simulated_merge.get("source_branch", "").strip()
            tgt_b = simulated_merge.get("target_branch", "").strip()
            m_title = simulated_merge.get("title", f"Fusión: {src_b} ➔ {tgt_b}").strip()

            tgt_node = self.head_node
            if tgt_b:
                clean_tgt = tgt_b.replace("origin/", "").strip()
                for n in reversed(self.nodes):
                    if any(tgt_b in r or clean_tgt in r for r in n.refs):
                        tgt_node = n
                        break

            src_node = None
            if src_b:
                clean_src = src_b.replace("origin/", "").strip()
                for n in reversed(self.nodes):
                    if any(src_b in r or clean_src in r for r in n.refs):
                        src_node = n
                        break

            if tgt_node:
                max_x = max([n.x() for n in self.nodes])
                sim_x = max_x + x_step
                sim_y = tgt_node.y()
                sim_lane = tgt_node.lane_idx
                sim_color = QColor("#c084fc")

                sim_commit_data = {
                    "hash": "~merge",
                    "subject": m_title,
                    "author": "Simulación",
                    "date": "proyección",
                    "refs": ["🧪 SIMULACIÓN"],
                    "parents": [tgt_node.hash] + ([src_node.hash] if src_node and src_node != tgt_node else []),
                    "is_simulation": True
                }

                sim_node = GitGraphCommitNode(
                    commit_data=sim_commit_data,
                    lane_idx=sim_lane,
                    lane_color=sim_color,
                    is_head=False,
                    on_click_cb=self._on_node_clicked
                )
                sim_node.setPos(sim_x, sim_y)
                self.scene.addItem(sim_node)
                self.nodes.append(sim_node)

                # Arista horizontal desde la rama receptora
                edge_tgt = GitGraphConnectorEdge(tgt_node, sim_node, tgt_node.lane_color)
                self.scene.addItem(edge_tgt)
                self.edges.append(edge_tgt)

                # Arista diagonal desde la rama entrante
                if src_node and src_node != tgt_node:
                    edge_src = GitGraphConnectorEdge(src_node, sim_node, src_node.lane_color)
                    self.scene.addItem(edge_src)
                    self.edges.append(edge_src)

                self.head_node = sim_node

        # 7. Ajustar el rectángulo de escena y posicionar la vista hacia HEAD (derecha)
        rect = self.scene.itemsBoundingRect()
        self.scene.setSceneRect(QRectF(0, rect.top() - 35, max(rect.right() + 80, 500.0), rect.height() + 70))
        self.scroll_to_head()

    def _get_git_branches(self, path: str) -> List[Dict[str, str]]:
        """Extrae la lista de ramas y sus commits correspondientes."""
        branches = []
        try:
            cmd = ["git", "for-each-ref", "--format=%(refname:short)|%(objectname:short)", "refs/heads/", "refs/remotes/origin/"]
            raw = subprocess.check_output(cmd, cwd=path, stderr=subprocess.DEVNULL, text=True)
            seen = set()
            for line in raw.splitlines():
                if not line.strip() or "HEAD" in line:
                    continue
                parts = line.split("|")
                name = parts[0].strip()
                h = parts[1].strip() if len(parts) > 1 else ""
                clean_name = name.replace("origin/", "")
                if clean_name == "origin" or not clean_name:
                    continue
                if clean_name not in seen:
                    seen.add(clean_name)
                    branches.append({"name": clean_name, "ref": name, "hash": h})
        except Exception:
            pass
        return branches

    def _get_git_commits(self, path: str, limit: int, branches: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Obtiene la lista estructurada de commits mediante git log para las ramas especificadas."""
        commits = []
        SEP = "@@LUMEN_GRAPH_SEP@@"
        branch_targets = []
        if branches:
            for b in branches:
                clean_b = b.strip()
                if clean_b:
                    branch_targets.append(clean_b)
        if not branch_targets:
            branch_targets = ["--all"]

        cmd = [
            "git", "log", *branch_targets, "--topo-order",
            f"--format=%h{SEP}%p{SEP}%d{SEP}%s{SEP}%an{SEP}%cr",
            "-n", str(limit)
        ]
        try:
            raw = subprocess.check_output(cmd, cwd=path, stderr=subprocess.DEVNULL, text=True)
            for line in raw.splitlines():
                line = line.strip()
                if not line:
                    continue
                parts = line.split(SEP)
                h = parts[0].strip() if len(parts) > 0 else ""
                parents = parts[1].strip().split() if len(parts) > 1 and parts[1].strip() else []
                raw_ref = parts[2].strip() if len(parts) > 2 else ""
                subject = parts[3].strip() if len(parts) > 3 else ""
                author = parts[4].strip() if len(parts) > 4 else ""
                date = parts[5].strip() if len(parts) > 5 else ""

                refs = []
                if raw_ref:
                    clean_refs = raw_ref.strip("()")
                    refs = [r.strip() for r in clean_refs.split(",") if r.strip()]

                commits.append({
                    "hash": h,
                    "parents": parents,
                    "refs": refs,
                    "subject": subject,
                    "author": author,
                    "date": date
                })
        except Exception:
            pass
        return commits

    def _calculate_branch_lanes(
        self, 
        commits: List[Dict[str, Any]], 
        branches: List[Dict[str, str]], 
        selected_branches: Optional[List[str]] = None,
        active_branch: Optional[str] = None
    ):
        """
        Asigna a cada commit un carril horizontal persistente según su linaje y rama.
        Los carriles 0, 1, 2... se asocian de manera fija a las ramas seleccionadas.
        """
        lane_mapping = {}  # lane_idx -> branch_name
        commit_lanes = {}  # hash -> lane_idx

        # Si no se pasó active_branch, detectarlo
        if not active_branch:
            try:
                active_branch = subprocess.check_output(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    cwd=self.current_project_path, stderr=subprocess.DEVNULL, text=True
                ).strip() or "main"
            except Exception:
                active_branch = "main"

        # Establecer asignación fija de carriles según selected_branches
        if selected_branches:
            for idx, b_name in enumerate(selected_branches):
                lane_mapping[idx] = b_name
        else:
            lane_mapping[0] = active_branch

        # Identificar ramas conocidas secundarias
        known_branch_names = [
            b["name"] for b in branches
            if b.get("name") and b["name"] not in lane_mapping.values() and b["name"] != "HEAD"
        ]

        # 1. Pre-mapeo directo por refs de commit
        for c in commits:
            for lane_idx, b_name in lane_mapping.items():
                clean_b = b_name.replace("origin/", "").strip()
                if any(clean_b in r or f"/{clean_b}" in r for r in c.get("refs", [])):
                    commit_lanes[c["hash"]] = lane_idx
                    break

        # 2. Algoritmo de propagación por linaje topológico
        num_lanes = max(len(lane_mapping), 1)
        active_lanes = [None] * num_lanes

        for c in commits:
            chash = c["hash"]

            # Si ya se asignó por refs, respetarlo
            if chash in commit_lanes:
                lane = commit_lanes[chash]
            # Continuar carril activo existente
            elif chash in active_lanes:
                lane = active_lanes.index(chash)
                for idx in range(len(active_lanes)):
                    if active_lanes[idx] == chash:
                        active_lanes[idx] = None
            else:
                # Asignar a un carril libre de las ramas seleccionadas si existe
                if None in active_lanes:
                    lane = active_lanes.index(None)
                elif len(active_lanes) < len(lane_mapping):
                    lane = len(active_lanes)
                else:
                    lane = 0

            while len(active_lanes) <= lane:
                active_lanes.append(None)

            active_lanes[lane] = chash
            commit_lanes[chash] = lane

            if lane not in lane_mapping:
                found_name = None
                for r in c.get("refs", []):
                    clean = r.replace("HEAD ->", "").replace("origin/", "").strip()
                    if clean and "tag:" not in clean:
                        found_name = clean
                        break
                if not found_name and known_branch_names:
                    found_name = known_branch_names.pop(0)
                lane_mapping[lane] = found_name or f"Rama #{lane}"

            # 3. Propagar padres hacia los carriles
            parents = c.get("parents", [])
            if not parents:
                active_lanes[lane] = None
            else:
                active_lanes[lane] = parents[0]
                for p_extra in parents[1:]:
                    if p_extra not in active_lanes:
                        if None in active_lanes:
                            active_lanes[active_lanes.index(None)] = p_extra
                        else:
                            active_lanes.append(p_extra)

        return lane_mapping, commit_lanes

    def _render_empty_state(self, message: str):
        """Muestra un mensaje cuando no hay grafo disponible."""
        lbl = self.scene.addText(message, QFont("Inter", 11, QFont.Bold))
        lbl.setDefaultTextColor(QColor("#9ca3af"))
        lbl.setPos(20, 20)

    def _on_node_clicked(self, commit_hash: str):
        """Notifica la selección de un commit para inspección detallada."""
        self.commit_selected.emit(commit_hash)

    def scroll_to_head(self):
        """Desplaza suavemente el lienzo hacia el commit HEAD (el extremo derecho)."""
        if self.head_node:
            self.centerOn(self.head_node.scenePos().x() - 150, self.head_node.scenePos().y())
        else:
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().maximum())

    def scroll_to_root(self):
        """Desplaza el lienzo hacia los commits más antiguos (extremo izquierdo)."""
        self.horizontalScrollBar().setValue(self.horizontalScrollBar().minimum())

    def drawForeground(self, painter: QPainter, rect: QRectF):
        """Dibuja el panel de encabezado de ramas fijado a la izquierda (Freeze Header estilo Excel)."""
        super().drawForeground(painter, rect)
        if not self.used_lanes or not self.current_project_path or not self.nodes:
            return

        painter.save()
        painter.resetTransform()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        vp = self.viewport().rect()
        pw = self.pinned_header_width

        # 1. Fondo translúcido glass oscuro
        bg_rect = QRectF(0, 0, pw, vp.height())
        painter.fillRect(bg_rect, QColor(9, 13, 24, 240))

        # 2. Sombra difuminada a la derecha del panel
        shadow_rect = QRectF(pw, 0, 18, vp.height())
        shadow_grad = QLinearGradient(pw, 0, pw + 18, 0)
        shadow_grad.setColorAt(0.0, QColor(0, 0, 0, 120))
        shadow_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.fillRect(shadow_rect, shadow_grad)

        # 3. Borde divisor vertical sutil
        border_pen = QPen(QColor(56, 189, 248, 60), 1.2)
        painter.setPen(border_pen)
        painter.drawLine(QPointF(pw, 0), QPointF(pw, vp.height()))

        # 4. Etiqueta superior del encabezado
        f_header = QFont("Inter, sans-serif", 7, QFont.Bold)
        f_header.setLetterSpacing(QFont.AbsoluteSpacing, 0.6)
        painter.setFont(f_header)
        painter.setPen(QColor("#64748b"))
        painter.drawText(QRectF(10, 8, pw - 20, 16), Qt.AlignLeft | Qt.AlignVCenter, "📌 RAMAS FIJAS")

        # 5. Píldoras fijadas para cada carril visible
        for lane_idx in self.used_lanes:
            scene_y = self.base_y + lane_idx * self.y_step
            vp_pt = self.mapFromScene(QPointF(0, scene_y))
            lane_vp_y = vp_pt.y()

            # Pintar si intersecta el área visible vertical
            if -30 < lane_vp_y < vp.height() + 30:
                b_name = self.lane_mapping.get(lane_idx, f"Rama #{lane_idx}")
                color = LUMEN_BRANCH_PALETTE[lane_idx % len(LUMEN_BRANCH_PALETTE)]
                is_hovered = (self.hovered_lane == lane_idx)

                pill_rect = QRectF(8, lane_vp_y - 13, pw - 16, 26)

                # Fondo reactivo
                bg_alpha = 50 if is_hovered else 22
                pill_bg = QColor(color.red(), color.green(), color.blue(), bg_alpha)
                painter.setBrush(QBrush(pill_bg))

                # Contorno
                border_alpha = 230 if is_hovered else 115
                pill_pen = QPen(QColor(color.red(), color.green(), color.blue(), border_alpha), 1.2 if is_hovered else 1.0)
                painter.setPen(pill_pen)
                painter.drawRoundedRect(pill_rect, 6, 6)

                # Punto luminoso indicador
                dot_x = 16
                dot_y = lane_vp_y
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(color))
                painter.drawEllipse(QPointF(dot_x, dot_y), 3.5, 3.5)

                # Nombre de la rama con texto elidido
                f_branch = QFont("JetBrains Mono, monospace", 8, QFont.Bold)
                painter.setFont(f_branch)
                painter.setPen(color if is_hovered else QColor("#f1f5f9"))

                text_rect = QRectF(25, lane_vp_y - 11, pw - 38, 22)
                fm = painter.fontMetrics()
                elided_name = fm.elidedText(b_name, Qt.ElideRight, int(pw - 40))
                painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, elided_name)

        painter.restore()

    def mouseMoveEvent(self, event):
        pos = event.pos()
        if pos.x() < self.pinned_header_width:
            prev_hover = self.hovered_lane
            self.hovered_lane = None
            for lane_idx in self.used_lanes:
                scene_y = self.base_y + lane_idx * self.y_step
                vp_pt = self.mapFromScene(QPointF(0, scene_y))
                if abs(pos.y() - vp_pt.y()) <= 13:
                    self.hovered_lane = lane_idx
                    self.setCursor(Qt.PointingHandCursor)
                    break
            if self.hovered_lane is None:
                self.setCursor(Qt.ArrowCursor)

            if self.hovered_lane != prev_hover:
                self.viewport().update()
            event.accept()
            return
        else:
            if self.hovered_lane is not None:
                self.hovered_lane = None
                self.viewport().update()

        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        pos = event.pos()
        if pos.x() < self.pinned_header_width:
            # Clic interactivo en una píldora: centrar la vista en el último commit de esa rama
            for lane_idx in self.used_lanes:
                scene_y = self.base_y + lane_idx * self.y_step
                vp_pt = self.mapFromScene(QPointF(0, scene_y))
                if abs(pos.y() - vp_pt.y()) <= 13:
                    lane_nodes = [n for n in self.nodes if n.lane_idx == lane_idx]
                    if lane_nodes:
                        target_node = lane_nodes[-1]
                        self.centerOn(target_node.scenePos().x(), target_node.scenePos().y())
                    break
            event.accept()
            return

        super().mousePressEvent(event)

    def leaveEvent(self, event):
        if self.hovered_lane is not None:
            self.hovered_lane = None
            self.viewport().update()
        super().leaveEvent(event)

    def zoom_in(self):
        """Aumenta el nivel de zoom."""
        if self.zoom_level < 2.5:
            self.scale(1.15, 1.15)
            self.zoom_level *= 1.15

    def zoom_out(self):
        """Disminuye el nivel de zoom."""
        if self.zoom_level > 0.4:
            self.scale(1 / 1.15, 1 / 1.15)
            self.zoom_level /= 1.15

    def reset_zoom(self):
        """Restablece el zoom original."""
        self.resetTransform()
        self.zoom_level = 1.0
        self.scroll_to_head()

    def wheelEvent(self, event):
        """Rueda del ratón: Desplazamiento horizontal fluido o zoom con Ctrl."""
        if event.modifiers() & Qt.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
        else:
            # Desplazamiento horizontal natural con la rueda
            delta = event.angleDelta().y() or event.angleDelta().x()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta)
        event.accept()
