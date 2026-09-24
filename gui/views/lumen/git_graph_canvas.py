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
    QFrame, QToolTip, QScrollBar, QGraphicsDropShadowEffect
)
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QColor, QPainterPath,
    QFont, QCursor, QLinearGradient, QRadialGradient
)
from PySide6.QtCore import Qt, QPointF, QRectF, Signal, Slot, QTimer


# Paletas de colores establecidas de Abraxas
MONOCHROME_LANE_COLORS = [
    QColor("#e2e8f0"),  # Platinum
    QColor("#94a3b8"),  # Slate / Titanium
    QColor("#64748b"),  # Medium Titanium
    QColor("#cbd5e1"),  # Light Platinum
    QColor("#475569"),  # Deep Titanium
    QColor("#334155"),  # Dark Steel
]

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
    Arista de conexión entre commits con tramos ortogonales
    y quiebres diagonales a 45° estilo circuito técnico / Git Graph (Horizontal o Vertical).
    """

    def __init__(self, source_node, target_node, color: QColor, orientation: str = "vertical", is_dashed: bool = False, parent=None):
        super().__init__(parent)
        self.source = source_node
        self.target = target_node
        self.color = color
        self.orientation = orientation
        self.is_dashed = is_dashed
        self.setZValue(2)
        self.update_path()

    def update_path(self):
        if not self.source or not self.target:
            return

        p1 = self.source.get_center_pos()
        p2 = self.target.get_center_pos()

        path = QPainterPath()

        if self.orientation == "vertical":
            # Modo Vertical (Estilo Git Graph VS Code):
            # p1 es el commit superior, p2 el inferior (o viceversa)
            if p1.y() > p2.y():
                p1, p2 = p2, p1

            path.moveTo(p1)
            dx = p2.x() - p1.x()
            dy = p2.y() - p1.y()

            if abs(dx) < 3:
                # Mismo carril vertical
                path.lineTo(p2)
            else:
                # Bifurcación o Fusión con quiebre diagonal a 45°
                diag_span = min(abs(dx), max(12.0, dy * 0.35))
                mid_y = p1.y() + (dy - diag_span) / 2.0

                path.lineTo(p1.x(), mid_y)
                path.lineTo(p2.x(), mid_y + diag_span)
                path.lineTo(p2)
        else:
            # Modo Horizontal
            if p1.x() > p2.x():
                p1, p2 = p2, p1

            path.moveTo(p1)
            dx = p2.x() - p1.x()
            dy = p2.y() - p1.y()

            if abs(dy) < 3:
                path.lineTo(p2)
            else:
                diag_span = min(abs(dy), max(18.0, dx * 0.35))
                mid_x = p1.x() + (dx - diag_span) / 2.0

                path.lineTo(mid_x, p1.y())
                path.lineTo(mid_x + diag_span, p2.y())
                path.lineTo(p2)

        self.setPath(path)

        edge_color = QColor(self.color)
        edge_color.setAlpha(175)
        pen_style = Qt.DashLine if self.is_dashed else Qt.SolidLine
        pen = QPen(edge_color, 2.0 if self.is_dashed else 2.2, pen_style, Qt.RoundCap, Qt.RoundJoin)
        self.setPen(pen)


class GitGraphCommitNode(QGraphicsItem):
    """
    Nodo interactivo de Commit en el carril de la rama (Horizontal o Vertical estilo VS Code).
    Incluye halo brillante, dot central, short hash, mensaje y badges (HEAD, Tags, Ramas).
    """

    def __init__(
        self,
        commit_data: Dict[str, Any],
        lane_idx: int,
        lane_color: QColor,
        is_head: bool = False,
        orientation: str = "vertical",
        details_x: float = 0.0,
        on_click_cb = None,
        graph_view = None,
        parent = None
    ):
        super().__init__(parent)
        self.data = commit_data
        self.lane_idx = lane_idx
        self.lane_color = lane_color
        self.is_head = is_head
        self.orientation = orientation
        self.details_x = details_x
        self.on_click_cb = on_click_cb
        self.graph_view = graph_view

        self.hash = commit_data.get("hash", "")
        self.subject = commit_data.get("subject", "")
        self.author = commit_data.get("author", "")
        self.date = commit_data.get("date", "")
        self.refs = commit_data.get("refs", [])

        self.is_hovered = False
        self.is_selected = False
        self.dot_radius = 5.5 if not is_head else 7.0

        self.setFlags(QGraphicsItem.ItemIsSelectable)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setZValue(10 if not is_head else 15)

    def get_center_pos(self) -> QPointF:
        return self.scenePos()

    def boundingRect(self) -> QRectF:
        if self.orientation == "vertical":
            return QRectF(-14, -18, max(520.0, self.details_x + 420.0), 36)
        return QRectF(-70, -42, 140, 85)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        if self.orientation == "vertical":
            # -------------------------------------------------------------
            # MODO VERTICAL: ESTILO VS CODE GIT GRAPH
            # -------------------------------------------------------------
            is_sim = bool(self.data.get("is_simulation", False))
            halo_r = self.dot_radius + (4.5 if self.is_hovered else (3.0 if (self.is_head or is_sim) else 1.5))
            halo_color = QColor(self.lane_color)
            halo_color.setAlpha(160 if self.is_hovered else (90 if (self.is_head or is_sim) else 35))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(halo_color))
            painter.drawEllipse(QPointF(0, 0), halo_r, halo_r)

            if is_sim:
                painter.setPen(QPen(QColor("#c084fc"), 1.6, Qt.DashDotLine))
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(QPointF(0, 0), halo_r + 2.5, halo_r + 2.5)
            elif self.is_head:
                painter.setPen(QPen(QColor("#38bdf8"), 1.4, Qt.DashLine))
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(QPointF(0, 0), halo_r + 2.0, halo_r + 2.0)

            # Punto Git central
            painter.setPen(QPen(QColor(255, 255, 255, 220 if self.is_hovered else 140), 1.2))
            painter.setBrush(QBrush(self.lane_color))
            painter.drawEllipse(QPointF(0, 0), self.dot_radius, self.dot_radius)

            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(255, 255, 255, 240)))
            painter.drawEllipse(QPointF(0, 0), self.dot_radius * 0.38, self.dot_radius * 0.38)

            # Información de la fila inline a la derecha de los carriles
            cur_x = max(18.0, self.details_x)

            # Badges de Ramas o Tags si existen
            if is_sim:
                b_text = "🧪 SIMULACIÓN"
                b_color = QColor("#c084fc")
                f_b = QFont("Inter, sans-serif", 7.5, QFont.Bold)
                painter.setFont(f_b)
                tw = painter.fontMetrics().horizontalAdvance(b_text) + 10
                rect_b = QRectF(cur_x, -9, tw, 18)
                bg_b = QColor(b_color)
                bg_b.setAlpha(40)
                painter.setPen(QPen(b_color, 1))
                painter.setBrush(QBrush(bg_b))
                painter.drawRoundedRect(rect_b, 4, 4)
                painter.setPen(QColor("#ffffff"))
                painter.drawText(rect_b, Qt.AlignCenter, b_text)
                cur_x += tw + 6.0
            elif self.refs:
                for ref in self.refs[:2]:
                    b_text = ref
                    b_color = self.lane_color
                    if "HEAD" in ref:
                        b_text = "🌿 " + ref.replace("HEAD ->", "").strip()
                        b_color = QColor("#38bdf8")
                    elif "tag:" in ref:
                        b_text = "🏷 " + ref.replace("tag:", "").strip()
                        b_color = QColor("#34d399")
                    elif "origin/" in ref:
                        b_text = "🌐 " + ref.replace("origin/", "").strip()
                        b_color = QColor("#60a5fa")

                    f_b = QFont("Inter, sans-serif", 7.5, QFont.Bold)
                    painter.setFont(f_b)
                    tw = painter.fontMetrics().horizontalAdvance(b_text) + 10
                    rect_b = QRectF(cur_x, -9, tw, 18)
                    bg_b = QColor(b_color)
                    bg_b.setAlpha(40)
                    painter.setPen(QPen(b_color, 1))
                    painter.setBrush(QBrush(bg_b))
                    painter.drawRoundedRect(rect_b, 4, 4)
                    painter.setPen(QColor("#ffffff"))
                    painter.drawText(rect_b, Qt.AlignCenter, b_text)
                    cur_x += tw + 6.0

            # Hash del commit
            f_hash = QFont("JetBrains Mono, monospace", 8.2, QFont.Bold)
            painter.setFont(f_hash)
            hw = painter.fontMetrics().horizontalAdvance(self.hash) + 8
            rect_h = QRectF(cur_x, -8, hw, 16)
            painter.setPen(QPen(QColor(255, 255, 255, 25), 1))
            painter.setBrush(QBrush(QColor(255, 255, 255, 10)))
            painter.drawRoundedRect(rect_h, 3, 3)
            painter.setPen(QColor("#fbbf24") if self.is_hovered else QColor("#cbd5e1"))
            painter.drawText(rect_h, Qt.AlignCenter, self.hash)
            cur_x += hw + 8.0

            # Asunto del commit (Subject)
            subj_clean = re.sub(r"^(?:HEX|SIL|HEN|AGY|MAN):\d{4}(?:\s*\[v?[0-9.]+\])?\s*\|\s*", "", self.subject).strip()
            f_subj = QFont("Inter, sans-serif", 8.2)
            painter.setFont(f_subj)
            painter.setPen(QColor("#ffffff") if self.is_hovered else QColor("#e2e8f0"))
            avail_w = 260.0
            elided = painter.fontMetrics().elidedText(subj_clean, Qt.ElideRight, int(avail_w))
            painter.drawText(QRectF(cur_x, -9, avail_w, 18), Qt.AlignVCenter | Qt.AlignLeft, elided)
            cur_x += painter.fontMetrics().horizontalAdvance(elided) + 12.0

            # Autor y fecha relativa
            f_meta = QFont("Inter, sans-serif", 7.2)
            painter.setFont(f_meta)
            painter.setPen(QColor("#64748b"))
            meta_str = f"👤 {self.author} • {self.date}"
            painter.drawText(QRectF(cur_x, -9, 200, 18), Qt.AlignVCenter | Qt.AlignLeft, meta_str)

        else:
            # -------------------------------------------------------------
            # MODO HORIZONTAL (CLÁSICO LUMEN)
            # -------------------------------------------------------------
            is_sim = bool(self.data.get("is_simulation", False))
            halo_r = self.dot_radius + (7.0 if self.is_hovered else (4.5 if (self.is_head or is_sim) else 2.5))
            halo_color = QColor(self.lane_color)
            halo_color.setAlpha(160 if self.is_hovered else (90 if (self.is_head or is_sim) else 45))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(halo_color))
            painter.drawEllipse(QPointF(0, 0), halo_r, halo_r)

            if is_sim:
                painter.setPen(QPen(QColor("#c084fc"), 1.8, Qt.DashDotLine))
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(QPointF(0, 0), halo_r + 3.5, halo_r + 3.5)
            elif self.is_head:
                painter.setPen(QPen(QColor("#38bdf8"), 1.6, Qt.DashLine))
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(QPointF(0, 0), halo_r + 3.0, halo_r + 3.0)

            # Punto Git
            painter.setPen(QPen(QColor(255, 255, 255, 220 if self.is_hovered else 140), 1.2))
            painter.setBrush(QBrush(self.lane_color))
            painter.drawEllipse(QPointF(0, 0), self.dot_radius, self.dot_radius)

            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(255, 255, 255, 240)))
            painter.drawEllipse(QPointF(0, 0), self.dot_radius * 0.38, self.dot_radius * 0.38)

            # Hash del commit
            f_hash = QFont("JetBrains Mono, monospace", 8.2)
            f_hash.setBold(True)
            painter.setFont(f_hash)
            if is_sim:
                painter.setPen(QColor("#c084fc"))
            else:
                painter.setPen(QColor("#fbbf24") if self.is_hovered else QColor("#bae6fd"))
            painter.drawText(QRectF(-45, -22, 90, 14), Qt.AlignCenter, self.hash)

            # Badges de Ramas o Tags
            if is_sim:
                b_rect = QRectF(-55, -38, 110, 14)
                badge_color = QColor("#c084fc")
                painter.setPen(QPen(badge_color, 1))
                bg_b = QColor(badge_color)
                bg_b.setAlpha(55)
                painter.setBrush(QBrush(bg_b))
                painter.drawRoundedRect(b_rect, 3, 3)

                f_b = QFont("Inter, sans-serif", 7.5, QFont.Bold)
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

                f_b = QFont("Inter, sans-serif", 7.5, QFont.Bold)
                painter.setFont(f_b)
                painter.setPen(QColor(255, 255, 255))
                painter.drawText(b_rect, Qt.AlignCenter, badge_text)

            # Título resumido
            subj_clean = self.subject
            subj_clean = re.sub(r"^(?:HEX|SIL|HEN|AGY|MAN):\d{4}(?:\s*\[v?[0-9.]+\])?\s*\|\s*", "", subj_clean).strip()
            if len(subj_clean) > 15:
                subj_clean = subj_clean[:14] + "…"

            f_subj = QFont("Inter, sans-serif", 7.8)
            painter.setFont(f_subj)
            painter.setPen(QColor("#f3f4f6") if self.is_hovered else QColor("#9ca3af"))
            painter.drawText(QRectF(-60, 10, 120, 15), Qt.AlignCenter, subj_clean)

            # Autor y fecha
            f_sub = QFont("Inter, sans-serif", 6.8)
            painter.setFont(f_sub)
            painter.setPen(QColor("#6b7280"))
            painter.drawText(QRectF(-60, 24, 120, 13), Qt.AlignCenter, f"{self.author} • {self.date}")

    def _resolve_graph_view(self):
        if hasattr(self, "graph_view") and self.graph_view:
            return self.graph_view
        if self.scene() and self.scene().views():
            return self.scene().views()[0]
        return None

    def hoverEnterEvent(self, event):
        self.is_hovered = True
        self.update()
        gv = self._resolve_graph_view()
        if gv and hasattr(gv, "show_commit_hover"):
            gv.show_commit_hover(self)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.is_hovered = False
        self.update()
        gv = self._resolve_graph_view()
        if gv and hasattr(gv, "hide_commit_hover"):
            gv.hide_commit_hover(self)
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        gv = self._resolve_graph_view()
        if gv and hasattr(gv, "hide_commit_hover_immediately"):
            gv.hide_commit_hover_immediately()
        if self.on_click_cb:
            self.on_click_cb(self.hash)
        super().mousePressEvent(event)


class CommitHoverCard(QFrame):
    """
    Tarjeta emergente flotante con estética Haute Horlogerie / Cristal Obsidiana.
    Permanente durante la inspección del usuario (sin desaparecer por timeout arbitrario).
    """
    def __init__(self, graph_view=None, parent=None):
        super().__init__(parent)
        self.graph_view = graph_view
        self.setVisible(False)
        self.setObjectName("CommitHoverCard")
        self.setStyleSheet("""
            QFrame#CommitHoverCard {
                background-color: rgba(12, 13, 16, 0.96);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
            }
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 200))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(5)

        # 1. Fila de Cabecera (Dot de color + Hash + Badges)
        self.header_row = QHBoxLayout()
        self.header_row.setContentsMargins(0, 0, 0, 0)
        self.header_row.setSpacing(6)

        self.lbl_dot = QLabel("●")
        self.lbl_dot.setStyleSheet("font-size: 11px;")
        self.header_row.addWidget(self.lbl_dot)

        self.lbl_hash = QLabel("")
        self.lbl_hash.setStyleSheet("""
            color: #38bdf8;
            font-family: 'JetBrains Mono', monospace;
            font-size: 10.5px;
            font-weight: 700;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.09);
            border-radius: 3px;
            padding: 1px 5px;
        """)
        self.header_row.addWidget(self.lbl_hash)

        self.badges_container = QWidget()
        self.badges_layout = QHBoxLayout(self.badges_container)
        self.badges_layout.setContentsMargins(0, 0, 0, 0)
        self.badges_layout.setSpacing(4)
        self.header_row.addWidget(self.badges_container)

        self.header_row.addStretch()
        layout.addLayout(self.header_row)

        # 2. Asunto / Mensaje
        self.lbl_subject = QLabel("")
        self.lbl_subject.setWordWrap(True)
        self.lbl_subject.setMaximumWidth(320)
        self.lbl_subject.setStyleSheet("""
            color: #ffffff;
            font-size: 11px;
            font-weight: 600;
            line-height: 1.35;
        """)
        layout.addWidget(self.lbl_subject)

        # 3. Metadatos (Autor y Fecha)
        meta_row = QHBoxLayout()
        meta_row.setContentsMargins(0, 0, 0, 0)
        meta_row.setSpacing(6)

        self.lbl_author = QLabel("")
        self.lbl_author.setStyleSheet("color: #94a3b8; font-size: 9.5px; font-weight: 500;")
        meta_row.addWidget(self.lbl_author)

        lbl_sep = QLabel("•")
        lbl_sep.setStyleSheet("color: #475569; font-size: 9.5px;")
        meta_row.addWidget(lbl_sep)

        self.lbl_date = QLabel("")
        self.lbl_date.setStyleSheet("color: #64748b; font-size: 9.5px;")
        meta_row.addWidget(self.lbl_date)

        meta_row.addStretch()
        layout.addLayout(meta_row)

    def set_commit(self, node):
        self.lbl_dot.setStyleSheet(f"color: {node.lane_color.name()}; font-size: 11px;")
        self.lbl_hash.setText(node.hash)

        # Limpiar badges previos
        while self.badges_layout.count() > 0:
            item = self.badges_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        is_sim = bool(node.data.get("is_simulation", False))
        if is_sim:
            b_sim = QLabel("🧪 SIMULACIÓN")
            b_sim.setStyleSheet("""
                color: #c084fc;
                font-size: 8px;
                font-weight: 800;
                background: rgba(192, 132, 252, 0.15);
                border: 1px solid rgba(192, 132, 252, 0.40);
                border-radius: 3px;
                padding: 1px 4px;
            """)
            self.badges_layout.addWidget(b_sim)
        elif node.refs:
            for ref in node.refs[:2]:
                text = ref
                color = "#38bdf8"
                if "HEAD" in ref:
                    text = "🌿 " + ref.replace("HEAD ->", "").strip()
                    color = "#38bdf8"
                elif "tag:" in ref:
                    text = "🏷 " + ref.replace("tag:", "").strip()
                    color = "#34d399"
                elif "origin/" in ref:
                    text = "🌐 " + ref.replace("origin/", "").strip()
                    color = "#60a5fa"

                b_lbl = QLabel(text)
                b_lbl.setStyleSheet(f"""
                    color: {color};
                    font-size: 8px;
                    font-weight: 700;
                    background: rgba(255, 255, 255, 0.05);
                    border: 1px solid rgba(255, 255, 255, 0.10);
                    border-radius: 3px;
                    padding: 1px 4px;
                """)
                self.badges_layout.addWidget(b_lbl)

        self.lbl_subject.setText(node.subject)
        self.lbl_author.setText(f"👤 {node.author}")
        self.lbl_date.setText(f"🕒 {node.date}")
        self.adjustSize()

    def enterEvent(self, event):
        if self.graph_view and hasattr(self.graph_view, "hide_timer"):
            self.graph_view.hide_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.graph_view and hasattr(self.graph_view, "hide_timer"):
            self.graph_view.hide_timer.start(120)
        super().leaveEvent(event)


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

        # Orientación y paleta establecida
        self.orientation = "vertical"
        self.theme_mode = "monochrome"

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

        # Tarjeta flotante Haute Horlogerie para detalles del commit (permanente durante la inspección)
        self.hover_card = CommitHoverCard(self, parent=self.viewport())
        self.hovered_node = None
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.setInterval(120)
        self.hide_timer.timeout.connect(self._do_hide_hover_card)

        self.horizontalScrollBar().valueChanged.connect(self._on_scroll_hover_update)
        self.verticalScrollBar().valueChanged.connect(self._on_scroll_hover_update)

    def show_commit_hover(self, node):
        """Muestra la tarjeta de inspección de commit con diseño unificado."""
        if not node:
            return
        self.hide_timer.stop()
        self.hovered_node = node
        self.hover_card.set_commit(node)
        self._update_hover_card_pos(node)

    def _update_hover_card_pos(self, node):
        if not node:
            return
        node_pt = self.mapFromScene(node.scenePos())
        self.hover_card.adjustSize()
        card_w = self.hover_card.sizeHint().width()
        card_h = self.hover_card.sizeHint().height()
        vp_w = self.viewport().width()
        vp_h = self.viewport().height()

        if self.orientation == "vertical":
            x = node_pt.x() + 25
            y = node_pt.y() - 15
        else:
            x = node_pt.x() - card_w // 2
            y = node_pt.y() - card_h - 22

        if x + card_w > vp_w - 12:
            x = max(12, node_pt.x() - card_w - 20)
        if x < 12:
            x = 12
        if y + card_h > vp_h - 12:
            y = max(12, vp_h - card_h - 12)
        if y < 12:
            y = 12

        self.hover_card.move(int(x), int(y))
        self.hover_card.show()
        self.hover_card.raise_()

    def hide_commit_hover(self, node):
        """Inicia el temporizador de cierre suave si el cursor sale del nodo."""
        if self.hovered_node == node:
            self.hide_timer.start(120)

    def hide_commit_hover_immediately(self):
        """Oculta inmediatamente la tarjeta ante clics u otras acciones."""
        self.hide_timer.stop()
        if hasattr(self, "hover_card"):
            self.hover_card.hide()
        self.hovered_node = None

    def _do_hide_hover_card(self):
        cursor_pos = self.viewport().mapFromGlobal(QCursor.pos())
        if self.hover_card.isVisible() and self.hover_card.geometry().contains(cursor_pos):
            return
        self.hover_card.hide()
        self.hovered_node = None

    def _on_scroll_hover_update(self):
        if self.hovered_node and self.hover_card.isVisible():
            node_pt = self.mapFromScene(self.hovered_node.scenePos())
            if (node_pt.x() < -80 or node_pt.y() < -80 or 
                node_pt.x() > self.viewport().width() + 80 or 
                node_pt.y() > self.viewport().height() + 80):
                self.hover_card.hide()
                self.hovered_node = None
            else:
                self._update_hover_card_pos(self.hovered_node)

    def get_palette(self) -> List[QColor]:
        """Retorna la paleta de colores establecida según el tema activo."""
        if getattr(self, "theme_mode", "monochrome") == "monochrome":
            return MONOCHROME_LANE_COLORS
        return LUMEN_BRANCH_PALETTE

    def set_theme(self, theme_mode: str):
        """Aplica la paleta de color establecida (monochrome o lumen)."""
        self.theme_mode = theme_mode
        if self.current_project_path:
            self.load_project_graph(self.current_project_path)

    def set_orientation(self, orientation: str):
        """Configura la orientación ('vertical' estilo Git Graph o 'horizontal')."""
        self.orientation = orientation
        if self.current_project_path:
            self.load_project_graph(self.current_project_path)

    def toggle_orientation(self) -> str:
        """Alterna entre orientación vertical y horizontal."""
        self.orientation = "horizontal" if self.orientation == "vertical" else "vertical"
        if self.current_project_path:
            self.load_project_graph(self.current_project_path)
        return self.orientation

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
        """Remueve una rama del visor de ramas (la rama main siempre se conserva visible)."""
        clean = branch_name.strip()
        main_b = self._detect_main_branch(self.current_project_path, self.available_branches)
        if clean == main_b:
            return  # La rama principal nunca se elimina
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
        """Reduce en 1 la cantidad de ramas en pantalla (manteniendo main siempre)."""
        main_b = self._detect_main_branch(self.current_project_path, self.available_branches)
        candidates = [b for b in self.selected_branches if b != main_b]
        if candidates:
            self.remove_branch(candidates[-1])

    def load_project_graph(self, project_path: str, max_commits: int = 50, simulated_merge: Optional[Dict[str, Any]] = None):
        """Carga y genera el grafo de ramas a partir del historial git del proyecto."""
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
        self.hide_commit_hover_immediately()

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

        # Detectar la rama principal troncal (main, master o la indicada por origin/HEAD)
        main_branch = self._detect_main_branch(project_path, all_names)

        # Configuración de ramas seleccionadas (Ilimitadas: sin corte de 3 ramas)
        # Prioridad estricta: 1) main (troncal fija), 2) activa actual, 3) demás ramas
        picked = []
        if main_branch in all_names:
            picked.append(main_branch)
        if active_branch and active_branch != main_branch and active_branch in all_names:
            picked.append(active_branch)
        for b in all_names:
            if b not in picked:
                picked.append(b)

        if not self.selected_branches or not any(b in all_names for b in self.selected_branches):
            self.selected_branches = picked
        else:
            # Mantener la selección válida pero asegurando SIEMPRE que main esté visible
            self.selected_branches = [b for b in self.selected_branches if b in all_names]
            if main_branch in all_names and main_branch not in self.selected_branches:
                self.selected_branches.insert(0, main_branch)
            if active_branch in all_names and active_branch not in self.selected_branches:
                self.selected_branches.append(active_branch)

        # Notificar a la UI sobre las ramas actualizadas
        self.branches_updated.emit(self.selected_branches, self.available_branches)

        # 2. Obtener historial cronológico / topológico de commits para las ramas seleccionadas
        commits = self._get_git_commits(project_path, max_commits, self.selected_branches)
        if not commits:
            self._render_empty_state("⚠️ No se encontraron commits en las ramas seleccionadas")
            return

        # 3. Asignación de carriles para las ramas seleccionadas (main garantizada en Carril 0)
        lane_mapping, commit_lanes = self._calculate_branch_lanes(
            commits, branch_info, self.selected_branches, active_branch
        )

        palette = self.get_palette()
        self.lane_mapping = lane_mapping

        # 4. Detección de rama nueva sin publicar: Proyección en modo Simulación
        is_unpublished = self._is_branch_unpublished(project_path, active_branch)
        sim_branch_node_data = None
        if is_unpublished and active_branch != main_branch:
            base_parent = self._get_branch_base_commit(project_path, active_branch, main_branch)
            sim_lane = 1
            for l_idx, l_name in lane_mapping.items():
                if l_name == active_branch:
                    sim_lane = l_idx
                    break
            else:
                sim_lane = max(lane_mapping.keys(), default=0) + 1
                lane_mapping[sim_lane] = active_branch

            # Padre: si la rama ya tiene commits en el log tomamos el más reciente; si no, el base
            branch_commits = [c for c in commits if commit_lanes.get(c["hash"]) == sim_lane]
            parent_hash = branch_commits[0]["hash"] if branch_commits else base_parent

            sim_branch_node_data = {
                "hash": "~local",
                "subject": f"Rama local '{active_branch}' (Sin publicar en remoto)",
                "author": "Simulación Local",
                "date": "proyección activa",
                "refs": ["🧪 SIMULACIÓN", f"🌿 {active_branch} (Local)"],
                "parents": [parent_hash] if parent_hash else [],
                "is_simulation": True,
                "lane_idx": sim_lane
            }

        self.used_lanes = sorted(set(commit_lanes.values())) if commit_lanes else [0]
        if sim_branch_node_data and sim_branch_node_data["lane_idx"] not in self.used_lanes:
            self.used_lanes.append(sim_branch_node_data["lane_idx"])
            self.used_lanes.sort()

        if self.orientation == "vertical":
            # =============================================================
            # MODO VERTICAL: ESTILO VS CODE GIT GRAPH (ÁRBOL HACIA ARRIBA/ABAJO)
            # =============================================================
            lane_step = 22.0
            y_step = 36.0
            base_x = 22.0
            base_y = 28.0

            self.base_x = base_x
            self.base_y = base_y
            self.y_step = y_step

            # Inyectar nodo de proyección de simulación si la rama no está publicada
            if sim_branch_node_data:
                commits.insert(0, sim_branch_node_data)
                commit_lanes[sim_branch_node_data["hash"]] = sim_branch_node_data["lane_idx"]

            max_lane = max(self.used_lanes) if self.used_lanes else 0
            details_offset = base_x + (max_lane + 1) * lane_step + 12.0
            total_height = base_y + len(commits) * y_step + 60.0

            # Líneas guía verticales para cada carril activo
            for lane_idx in self.used_lanes:
                color = palette[lane_idx % len(palette)]
                lane_x = base_x + lane_idx * lane_step

                guide_path = QPainterPath()
                guide_path.moveTo(lane_x, 0)
                guide_path.lineTo(lane_x, total_height)
                guide_item = QGraphicsPathItem(guide_path)
                guide_pen = QPen(QColor(color.red(), color.green(), color.blue(), 35), 1.0, Qt.DashLine)
                guide_item.setPen(guide_pen)
                guide_item.setZValue(0)
                self.scene.addItem(guide_item)

            # Instanciar Nodos de Commit
            node_by_hash = {}
            for idx, c in enumerate(commits):
                chash = c["hash"]
                lane = commit_lanes.get(chash, 0)
                color = palette[lane % len(palette)]
                is_head = any("HEAD" in r for r in c.get("refs", [])) or c.get("is_simulation", False)

                x = base_x + lane * lane_step
                y = base_y + idx * y_step
                details_x = details_offset - x

                node = GitGraphCommitNode(
                    commit_data=c,
                    lane_idx=lane,
                    lane_color=color,
                    is_head=is_head,
                    orientation="vertical",
                    details_x=details_x,
                    on_click_cb=self._on_node_clicked,
                    graph_view=self
                )
                node.setPos(x, y)
                self.scene.addItem(node)
                self.nodes.append(node)
                node_by_hash[chash] = node

                if is_head or idx == 0:
                    self.head_node = node

            # Instanciar Aristas Conectoras (Líneas verticales y quiebres a 45°)
            for c in commits:
                child_node = node_by_hash.get(c["hash"])
                if not child_node:
                    continue

                is_dashed = bool(c.get("is_simulation", False))
                for parent_hash in c.get("parents", []):
                    parent_node = node_by_hash.get(parent_hash)
                    if parent_node:
                        edge = GitGraphConnectorEdge(
                            parent_node, child_node, child_node.lane_color,
                            orientation="vertical", is_dashed=is_dashed
                        )
                        self.scene.addItem(edge)
                        self.edges.append(edge)

            rect = self.scene.itemsBoundingRect()
            self.scene.setSceneRect(QRectF(0, 0, max(rect.right() + 40, details_offset + 380.0), total_height))
            self.scroll_to_head()

        else:
            # =============================================================
            # MODO HORIZONTAL (CLÁSICO LUMEN DERECHA)
            # =============================================================
            commits.reverse()
            # Inyectar nodo de simulación al final (extremo derecho) si la rama no está publicada
            if sim_branch_node_data:
                commits.append(sim_branch_node_data)
                commit_lanes[sim_branch_node_data["hash"]] = sim_branch_node_data["lane_idx"]

            x_step = 100.0   # Espacio horizontal entre commits consecutivos
            y_step = 70.0    # Altura de carril de cada rama
            base_x = 180.0   # Margen izquierdo para dar espacio al encabezado fijado (pinned header)
            base_y = 50.0

            self.base_y = base_y
            self.y_step = y_step

            total_guide_width = base_x + (len(commits) + (2 if simulated_merge else 1)) * x_step + 60

            for lane_idx in self.used_lanes:
                color = palette[lane_idx % len(palette)]
                lane_y = base_y + lane_idx * y_step

                guide_path = QPainterPath()
                guide_path.moveTo(0, lane_y)
                guide_path.lineTo(total_guide_width, lane_y)
                guide_item = QGraphicsPathItem(guide_path)
                guide_pen = QPen(QColor(color.red(), color.green(), color.blue(), 35), 1.0, Qt.DashLine)
                guide_item.setPen(guide_pen)
                guide_item.setZValue(0)
                self.scene.addItem(guide_item)

            node_by_hash = {}
            for idx, c in enumerate(commits):
                chash = c["hash"]
                lane = commit_lanes.get(chash, 0)
                color = palette[lane % len(palette)]
                is_head = any("HEAD" in r for r in c.get("refs", [])) or c.get("is_simulation", False)

                x = base_x + idx * x_step
                y = base_y + lane * y_step

                node = GitGraphCommitNode(
                    commit_data=c,
                    lane_idx=lane,
                    lane_color=color,
                    is_head=is_head,
                    orientation="horizontal",
                    on_click_cb=self._on_node_clicked,
                    graph_view=self
                )
                node.setPos(x, y)
                self.scene.addItem(node)
                self.nodes.append(node)
                node_by_hash[chash] = node

                if is_head or idx == len(commits) - 1:
                    self.head_node = node

            for c in commits:
                child_node = node_by_hash.get(c["hash"])
                if not child_node:
                    continue

                is_dashed = bool(c.get("is_simulation", False))
                for parent_hash in c.get("parents", []):
                    parent_node = node_by_hash.get(parent_hash)
                    if parent_node:
                        edge = GitGraphConnectorEdge(
                            parent_node, child_node, child_node.lane_color,
                            orientation="horizontal", is_dashed=is_dashed
                        )
                        self.scene.addItem(edge)
                        self.edges.append(edge)

            # Simulación Estética de Fusión (Merge preview)
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
                        orientation="horizontal",
                        on_click_cb=self._on_node_clicked,
                        graph_view=self
                    )
                    sim_node.setPos(sim_x, sim_y)
                    self.scene.addItem(sim_node)
                    self.nodes.append(sim_node)

                    edge_tgt = GitGraphConnectorEdge(tgt_node, sim_node, tgt_node.lane_color, orientation="horizontal", is_dashed=True)
                    self.scene.addItem(edge_tgt)
                    self.edges.append(edge_tgt)

                    if src_node and src_node != tgt_node:
                        edge_src = GitGraphConnectorEdge(src_node, sim_node, src_node.lane_color, orientation="horizontal", is_dashed=True)
                        self.scene.addItem(edge_src)
                        self.edges.append(edge_src)

                    self.head_node = sim_node

            rect = self.scene.itemsBoundingRect()
            self.scene.setSceneRect(QRectF(0, rect.top() - 35, max(rect.right() + 80, 500.0), rect.height() + 70))
            self.scroll_to_head()

    def _detect_main_branch(self, path: str, branch_names: List[str]) -> str:
        """Detecta la rama principal troncal del proyecto (main, master o la indicada por origin/HEAD)."""
        if path and os.path.exists(path):
            try:
                head_ref = subprocess.check_output(
                    ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
                    cwd=path, stderr=subprocess.DEVNULL, text=True
                ).strip()
                clean_ref = head_ref.split("/")[-1].strip()
                if clean_ref in branch_names:
                    return clean_ref
            except Exception:
                pass

        for candidate in ["main", "master", "NEOS", "develop", "trunk"]:
            if candidate in branch_names:
                return candidate
        return branch_names[0] if branch_names else "main"

    def _is_branch_unpublished(self, path: str, branch_name: str) -> bool:
        """Verifica si la rama actual es local y aún no ha sido publicada en el repositorio remoto."""
        if not branch_name or branch_name in ("HEAD",):
            return False
        if not path or not os.path.exists(path):
            return False
        try:
            remotes = subprocess.check_output(
                ["git", "remote"], cwd=path, stderr=subprocess.DEVNULL, text=True
            ).strip()
            if not remotes:
                return True

            try:
                subprocess.check_output(
                    ["git", "rev-parse", "--verify", f"refs/remotes/origin/{branch_name}"],
                    cwd=path, stderr=subprocess.DEVNULL, text=True
                )
                return False
            except Exception:
                pass

            try:
                up = subprocess.check_output(
                    ["git", "rev-parse", "--abbrev-ref", f"{branch_name}@{{upstream}}"],
                    cwd=path, stderr=subprocess.DEVNULL, text=True
                ).strip()
                if up:
                    return False
            except Exception:
                pass

            return True
        except Exception:
            return False

    def _get_branch_base_commit(self, path: str, branch_name: str, main_branch: str) -> Optional[str]:
        """Obtiene el hash del commit base desde donde se bifurcó la rama local."""
        if not path or not os.path.exists(path):
            return None
        try:
            base = subprocess.check_output(
                ["git", "merge-base", branch_name, main_branch],
                cwd=path, stderr=subprocess.DEVNULL, text=True
            ).strip()
            if base:
                return base[:7]
        except Exception:
            pass
        try:
            head = subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=path, stderr=subprocess.DEVNULL, text=True
            ).strip()
            return head
        except Exception:
            return None

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
                if not clean_b:
                    continue
                # Validar si existe localmente
                try:
                    subprocess.check_output(
                        ["git", "rev-parse", "--verify", "--quiet", clean_b],
                        cwd=path, stderr=subprocess.DEVNULL
                    )
                    branch_targets.append(clean_b)
                except Exception:
                    # Validar si existe como rama remota origin/
                    try:
                        subprocess.check_output(
                            ["git", "rev-parse", "--verify", "--quiet", f"origin/{clean_b}"],
                            cwd=path, stderr=subprocess.DEVNULL
                        )
                        branch_targets.append(f"origin/{clean_b}")
                    except Exception:
                        pass
        if not branch_targets:
            branch_targets = ["--all"]

        cmd = [
            "git", "log", *branch_targets, "--topo-order",
            f"--format=%h{SEP}%p{SEP}%d{SEP}%s{SEP}%an{SEP}%cr",
            "-n", str(limit), "--"
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
        # Garantizando que la rama principal troncal (main/master) se ubique SIEMPRE en el Carril 0
        main_b = self._detect_main_branch(self.current_project_path, selected_branches or [active_branch])
        ordered = list(selected_branches) if selected_branches else [active_branch]
        if main_b in ordered:
            ordered.remove(main_b)
            ordered.insert(0, main_b)

        for idx, b_name in enumerate(ordered):
            lane_mapping[idx] = b_name

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
        if self.orientation == "vertical":
            return
        if not self.used_lanes or not self.current_project_path or not self.nodes:
            return

        painter.save()
        painter.resetTransform()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        vp = self.viewport().rect()
        pw = self.pinned_header_width
        palette = self.get_palette()

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
                color = palette[lane_idx % len(palette)]
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
        if self.orientation == "vertical":
            super().mouseMoveEvent(event)
            return

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
        if self.orientation == "vertical":
            super().mousePressEvent(event)
            return

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
        """Rueda del ratón: Desplazamiento fluido o zoom con Ctrl."""
        if event.modifiers() & Qt.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
        else:
            if self.orientation == "vertical":
                delta = event.angleDelta().y()
                self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta)
            else:
                delta = event.angleDelta().y() or event.angleDelta().x()
                self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta)
        event.accept()
