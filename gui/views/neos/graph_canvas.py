#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS | NEOS - HORIZONTAL GITHUB GRID GRAPH (ESTRUCTURADO & FIJO)
# =====================================================================

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QGraphicsView, QGraphicsScene, 
    QGraphicsItem, QGraphicsPathItem
)
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QColor, QPainterPath, 
    QFont, QCursor
)
from PySide6.QtCore import Qt, QPointF, QRectF

# Paletas de carriles según el tema activo (Sincronización con Primario, Secundario o Monocromo)
MONOCHROME_LANE_COLORS = [
    QColor("#ffffff"),  # Blanco puro (Root / Nivel 0)
    QColor("#e2e8f0"),  # Platino
    QColor("#cbd5e1"),  # Plata
    QColor("#94a3b8"),  # Pizarra claro
    QColor("#64748b"),  # Titanio medio
    QColor("#9ca3af"),  # Gris neutro
    QColor("#f1f5f9"),  # Nieve
    QColor("#78716c"),  # Piedra
]

def get_theme_lane_colors(theme_key="monochrome"):
    """Resuelve la paleta de colores para los carriles del grafo sincronizada con el tema."""
    if theme_key == "monochrome":
        return MONOCHROME_LANE_COLORS
    try:
        from gui.theme import get_system_theme_palette, THEMES
        pal = get_system_theme_palette() or THEMES.get(theme_key, THEMES.get("noctalia", {}))
        return [
            QColor(pal.get("ACCENT", "#6366f1")),
            QColor(pal.get("CYAN", "#06b6d4")),
            QColor(pal.get("SUCCESS", "#10b981")),
            QColor(pal.get("WARNING", "#f59e0b")),
            QColor(pal.get("ACCENT_HOVER", "#4f46e5")),
            QColor(pal.get("ACCENT_LIGHT", "#e0e7ff")),
            QColor(pal.get("TEXT_PRIMARY", "#ffffff")),
            QColor(pal.get("TEXT_SECONDARY", "#9ca3af")),
        ]
    except Exception:
        return MONOCHROME_LANE_COLORS

LANE_COLORS = MONOCHROME_LANE_COLORS

def get_file_icon(name, is_dir):
    if is_dir:
        return "📁"
    lower = name.lower()
    if lower.endswith(".py"):
        return "🐍"
    if lower.endswith(".toml") or lower.endswith(".json") or lower.endswith(".yaml") or lower.endswith(".yml"):
        return "⚙️"
    if lower.endswith(".sh") or lower.endswith(".bash"):
        return "⚡"
    if lower.endswith(".md") or lower.endswith(".txt"):
        return "📝"
    if lower.endswith(".pdf"):
        return "📕"
    if lower.endswith(".png") or lower.endswith(".jpg") or lower.endswith(".svg"):
        return "🖼️"
    return "📄"


class FixedGridGraphEdge(QGraphicsPathItem):
    """Rama con líneas rectas y diagonales a 45° estilo Git Graph / Circuito técnico."""
    
    def __init__(self, source_node, target_node, color, parent=None):
        super().__init__(parent)
        self.source = source_node
        self.target = target_node
        self.color = color
        self.setZValue(1)
        self.update_path()

    def update_path(self, orientation="horizontal"):
        if not self.source or not self.target:
            return

        path = QPainterPath()
        if orientation == "horizontal":
            p1 = self.source.get_right_anchor()
            p2 = self.target.get_left_anchor()
            path.moveTo(p1)

            dx = p2.x() - p1.x()
            dy = p2.y() - p1.y()

            if abs(dy) < 2:
                path.lineTo(p2)
            else:
                diag_span = min(abs(dy), 22)
                mid_x = p1.x() + 24
                path.lineTo(mid_x, p1.y())
                path.lineTo(mid_x + diag_span, p2.y())
                path.lineTo(p2)
        else: # "vertical"
            p1 = self.source.get_bottom_anchor()
            p2 = self.target.get_top_anchor()
            path.moveTo(p1)

            dx = p2.x() - p1.x()
            dy = p2.y() - p1.y()

            if abs(dx) < 2:
                path.lineTo(p2)
            else:
                mid_y = p1.y() + 16
                diag_span = min(abs(dx), 16)
                path.lineTo(p1.x(), mid_y)
                sign = 1 if dx > 0 else -1
                path.lineTo(p1.x() + sign * diag_span, mid_y + diag_span)
                path.lineTo(p2.x(), mid_y + diag_span)
                path.lineTo(p2)

        self.setPath(path)
        
        edge_color = QColor(self.color)
        edge_color.setAlpha(175)
        pen = QPen(edge_color, 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        self.setPen(pen)


class FixedGridGraphNode(QGraphicsItem):
    """Nodo estructurado y fijo en cuadrícula con punto de carril Git."""
    
    def __init__(self, name, path, is_dir=True, is_root=False, level=0, lane_color=None, on_toggle_cb=None, parent=None):
        super().__init__(parent)
        self.name = name
        self.full_path = path
        self.is_dir = is_dir
        self.is_root = is_root
        self.level = level
        self.lane_color = lane_color or LANE_COLORS[level % len(LANE_COLORS)]
        self.on_toggle_cb = on_toggle_cb

        self.edges = []
        self.children_nodes = []
        self.is_expanded = True
        self.is_hovered = False

        # Posición fija en cuadrícula (sin arrastre manual libre para mantener orden impecable)
        self.setFlags(QGraphicsItem.ItemIsSelectable)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.PointingHandCursor if is_dir else Qt.ArrowCursor)
        self.setZValue(10)

        # Dimensiones estandarizadas a cuadrícula
        self.icon = get_file_icon(name, is_dir)
        self.dot_radius = 5.5 if not is_root else 7.5
        self.card_width = max(115, len(name) * 7.6 + 46)
        self.card_height = 30 if not is_root else 36

    def get_left_anchor(self):
        """Punto de entrada izquierdo (en el centro del punto Git)."""
        pos = self.scenePos()
        return QPointF(pos.x() - self.card_width / 2, pos.y())

    def get_right_anchor(self):
        """Punto de salida derecho (hacia las ramas hijas)."""
        pos = self.scenePos()
        return QPointF(pos.x() + self.card_width / 2, pos.y())

    def get_top_anchor(self):
        """Punto de entrada superior (orientación vertical)."""
        pos = self.scenePos()
        return QPointF(pos.x(), pos.y() - self.card_height / 2)

    def get_bottom_anchor(self):
        """Punto de salida inferior (orientación vertical)."""
        pos = self.scenePos()
        return QPointF(pos.x(), pos.y() + self.card_height / 2)

    def boundingRect(self):
        return QRectF(
            -self.card_width / 2 - 10, 
            -self.card_height / 2 - 6, 
            self.card_width + 20, 
            self.card_height + 12
        )

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        rect = QRectF(-self.card_width / 2, -self.card_height / 2, self.card_width, self.card_height)

        # 1. Punto de carril Git (Dot en el lado izquierdo)
        dot_center = QPointF(rect.left(), rect.center().y())

        # Halo del punto
        painter.setPen(Qt.NoPen)
        halo_color = QColor(self.lane_color)
        halo_color.setAlpha(60 if not self.is_hovered else 150)
        painter.setBrush(QBrush(halo_color))
        painter.drawEllipse(dot_center, self.dot_radius + 4, self.dot_radius + 4)

        # Centro del punto Git
        painter.setBrush(QBrush(self.lane_color))
        painter.drawEllipse(dot_center, self.dot_radius, self.dot_radius)

        # Núcleo interior blanco
        painter.setBrush(QBrush(QColor(255, 255, 255, 230)))
        painter.drawEllipse(dot_center, self.dot_radius * 0.4, self.dot_radius * 0.4)

        # 2. Tarjeta del Nodo
        card_rect = rect.adjusted(6, 0, 0, 0)
        
        if self.is_root:
            bg_color = QColor(25, 27, 38, 240)
            border_color = self.lane_color
            text_color = QColor(255, 255, 255)
        elif self.is_dir:
            bg_color = QColor(18, 19, 26, 230) if not self.is_hovered else QColor(28, 30, 42, 245)
            border_color = self.lane_color if self.is_hovered else QColor(36, 38, 50)
            text_color = QColor(243, 244, 246)
        else:
            bg_color = QColor(13, 14, 19, 210) if not self.is_hovered else QColor(22, 24, 34, 235)
            border_color = QColor(30, 32, 42) if not self.is_hovered else self.lane_color
            text_color = QColor(156, 163, 175) if not self.is_hovered else QColor(224, 247, 250)

        # Borde y fondo de la tarjeta
        painter.setPen(QPen(border_color, 1.2 if not self.is_hovered else 1.8))
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(card_rect, 6, 6)

        # Indicador de carril en el borde izquierdo
        ind_rect = QRectF(card_rect.left(), card_rect.top() + 4, 3, card_rect.height() - 8)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self.lane_color))
        painter.drawRoundedRect(ind_rect, 1.5, 1.5)

        # 3. Icono y Texto
        font = QFont("Inter", 8.5 if not self.is_root else 9.5)
        font.setBold(self.is_root or self.is_dir)
        painter.setFont(font)
        painter.setPen(text_color)

        label_rect = card_rect.adjusted(10, 0, -8, 0)
        label_text = f"{self.icon} {self.name}"
        if len(label_text) > 20:
            label_text = label_text[:18] + "…"

        painter.drawText(label_rect, Qt.AlignVCenter | Qt.AlignLeft, label_text)

        # Indicador (+) o (−) para carpetas
        if self.is_dir and self.children_nodes:
            exp_text = "−" if self.is_expanded else "+"
            painter.setFont(QFont("Inter", 8, QFont.Bold))
            painter.setPen(self.lane_color)
            painter.drawText(card_rect.adjusted(0, 0, -6, 0), Qt.AlignVCenter | Qt.AlignRight, exp_text)

    def hoverEnterEvent(self, event):
        self.is_hovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.is_hovered = False
        self.update()
        super().hoverLeaveEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self.is_dir and self.children_nodes and self.on_toggle_cb:
            self.on_toggle_cb(self)
        super().mouseDoubleClickEvent(event)

    def add_edge(self, edge):
        self.edges.append(edge)


class ProjectGraphCanvas(QGraphicsView):
    """Lienzo del Grafo Horizontal con Cuadrícula Fija y Control de Profundidad (+1 / -1)."""
    
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
        self.setStyleSheet("background-color: #0a0b0e; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px;")

        self.current_path = ""
        self.depth_level = 2
        self.max_files_per_dir = 8
        self.orientation = "horizontal"
        self.theme_key = "monochrome"
        self.lane_colors = get_theme_lane_colors(self.theme_key)

        self.root_node = None
        self.nodes = []
        self.edges = []
        self.zoom_level = 1.0

    def set_theme(self, theme_key="monochrome"):
        """Actualiza la paleta de colores del grafo según el tema."""
        self.theme_key = theme_key
        self.lane_colors = get_theme_lane_colors(theme_key)
        if self.current_path:
            self.build_graph_from_directory(self.current_path, depth=self.depth_level)

    def toggle_orientation(self) -> str:
        """Alterna entre orientación 'horizontal' (izq a der) y 'vertical' (arriba a abajo)."""
        self.orientation = "vertical" if getattr(self, "orientation", "horizontal") == "horizontal" else "horizontal"
        self._layout_fixed_grid()
        self.center_graph()
        return self.orientation

    def drawBackground(self, painter, rect):
        """Fondo con líneas fijas de cuadrícula y carriles de alineación."""
        super().drawBackground(painter, rect)
        painter.fillRect(rect, QColor("#0a0b0e"))

        # Líneas de cuadrícula horizontal
        pen_line = QPen(QColor(255, 255, 255, 7), 1, Qt.DashLine)
        painter.setPen(pen_line)
        y_step = 48
        start_y = int(rect.top()) - (int(rect.top()) % y_step)
        curr_y = start_y
        while curr_y < rect.bottom():
            painter.drawLine(int(rect.left()), curr_y, int(rect.right()), curr_y)
            curr_y += y_step

        # Cuadrícula de puntos ortogonales
        pen_dot = QPen(QColor(255, 255, 255, 18), 1.2)
        painter.setPen(pen_dot)
        grid_size = 24
        left = int(rect.left()) - (int(rect.left()) % grid_size)
        top = int(rect.top()) - (int(rect.top()) % grid_size)

        x = left
        while x < rect.right():
            y = top
            while y < rect.bottom():
                painter.drawPoint(QPointF(x, y))
                y += grid_size
            x += grid_size

    def build_graph_from_directory(self, root_path, depth=None, max_files=None):
        """Construye y posiciona el árbol de forma fija y estructurada en la cuadrícula."""
        if depth is not None:
            self.depth_level = depth
        if max_files is not None:
            self.max_files_per_dir = max_files

        self.current_path = root_path
        self.scene.clear()
        self.nodes = []
        self.edges = []
        self.zoom_level = 1.0
        self.resetTransform()

        if not root_path or not os.path.isdir(root_path):
            lbl_empty = self.scene.addText("⚠️ Selecciona una carpeta para proyectar su grafo", QFont("Inter", 12))
            lbl_empty.setDefaultTextColor(QColor("#9ca3af"))
            lbl_empty.setPos(-160, -10)
            return

        root_name = os.path.basename(root_path) or root_path
        self.root_node = FixedGridGraphNode(
            root_name, root_path, is_dir=True, is_root=True, level=0, 
            lane_color=self.lane_colors[0], on_toggle_cb=self.toggle_node_expansion
        )
        self.scene.addItem(self.root_node)
        self.nodes.append(self.root_node)

        # Escaneo en profundidad según depth_level
        self._populate_fixed_grid_tree(
            self.root_node, root_path, current_depth=1, 
            max_depth=self.depth_level, max_files=self.max_files_per_dir
        )

        # Posicionamiento matemático fijo en la cuadrícula
        self._layout_fixed_grid()
        self.center_graph()

    def _populate_fixed_grid_tree(self, parent_node, current_path, current_depth, max_depth, max_files):
        if current_depth > max_depth:
            return

        try:
            entries = sorted(os.listdir(current_path))
        except Exception:
            return

        dirs = []
        files = []

        ignore_list = {".git", ".venv", "__pycache__", "venv", ".idea", ".vscode", "node_modules", ".cache"}
        for entry in entries:
            if entry.startswith(".") or entry in ignore_list:
                continue
            full_p = os.path.join(current_path, entry)
            if os.path.isdir(full_p):
                dirs.append((entry, full_p))
            else:
                files.append((entry, full_p))

        selected_items = [(name, p, True) for name, p in dirs]
        selected_items += [(name, p, False) for name, p in files[:max_files]]

        if len(files) > max_files:
            extra = len(files) - max_files
            selected_items.append((f"+ {extra} archivos", current_path, False))

        colors = getattr(self, "lane_colors", LANE_COLORS)
        for i, (name, p, is_dir) in enumerate(selected_items):
            lane_idx = (parent_node.level + i + 1) % len(colors)
            lane_col = colors[lane_idx]

            child_node = FixedGridGraphNode(
                name, p, is_dir=is_dir, level=current_depth, 
                lane_color=lane_col, on_toggle_cb=self.toggle_node_expansion
            )
            self.scene.addItem(child_node)
            self.nodes.append(child_node)
            parent_node.children_nodes.append(child_node)

            # Conexión recta y diagonal ortogonal
            edge = FixedGridGraphEdge(parent_node, child_node, lane_col)
            self.scene.addItem(edge)
            self.edges.append(edge)
            parent_node.add_edge(edge)
            child_node.add_edge(edge)

            # Profundizar en subcarpetas
            if is_dir and current_depth < max_depth and os.path.isdir(p):
                self._populate_fixed_grid_tree(
                    child_node, p, current_depth + 1, 
                    max_depth, max_files=max(3, max_files - 3)
                )

    def _layout_fixed_grid(self):
        """Alinea los nodos en la cuadrícula fija según la orientación activa."""
        if not self.root_node:
            return

        if getattr(self, "orientation", "horizontal") == "horizontal":
            def layout_node_h(node, depth=0, start_y=0, x_step=250, y_step=48):
                node.x_grid = depth * x_step

                if not node.is_expanded or not node.children_nodes:
                    node.y_grid = start_y
                    node.setPos(node.x_grid, node.y_grid)
                    return start_y + y_step

                curr_y = start_y
                for child in node.children_nodes:
                    curr_y = layout_node_h(child, depth + 1, curr_y, x_step, y_step)

                first_child = node.children_nodes[0]
                last_child = node.children_nodes[-1]
                node.y_grid = (first_child.y_grid + last_child.y_grid) / 2.0
                node.setPos(node.x_grid, node.y_grid)
                return curr_y

            total_height = layout_node_h(self.root_node, depth=0, start_y=0)
            offset_y = total_height / 2.0
            for node in self.nodes:
                node.setPos(node.x_grid - 180, node.y_grid - offset_y)
        else:
            def layout_node_v(node, depth=0, start_x=0, y_step=75, x_spacing=18):
                node.y_grid = depth * y_step
                my_w = max(node.card_width, 140)

                if not node.is_expanded or not node.children_nodes:
                    node.x_grid = start_x + my_w / 2.0
                    node.setPos(node.x_grid, node.y_grid)
                    return start_x + my_w + x_spacing

                curr_x = start_x
                for child in node.children_nodes:
                    curr_x = layout_node_v(child, depth + 1, curr_x, y_step, x_spacing)

                first_child = node.children_nodes[0]
                last_child = node.children_nodes[-1]
                node.x_grid = (first_child.x_grid + last_child.x_grid) / 2.0
                node.setPos(node.x_grid, node.y_grid)
                return max(curr_x, start_x + my_w + x_spacing)

            total_width = layout_node_v(self.root_node, depth=0, start_x=0)
            offset_x = total_width / 2.0
            for node in self.nodes:
                node.setPos(node.x_grid - offset_x, node.y_grid - 100)

        # Actualizar aristas ortogonales según la orientación
        for edge in self.edges:
            edge.update_path(orientation=self.orientation)

    def change_depth(self, delta):
        """Aumenta (+1) o disminuye (-1) la profundidad de visualización."""
        new_depth = max(1, min(6, self.depth_level + delta))
        if new_depth != self.depth_level:
            self.depth_level = new_depth
            if self.current_path:
                self.build_graph_from_directory(self.current_path, depth=new_depth)
        return self.depth_level

    def toggle_node_expansion(self, node):
        """Oculta o muestra las ramas hijas del nodo."""
        node.is_expanded = not node.is_expanded
        self._set_children_visibility(node, node.is_expanded)
        self._layout_fixed_grid()
        self.center_graph()

    def _set_children_visibility(self, node, visible):
        for child in node.children_nodes:
            child.setVisible(visible)
            for edge in child.edges:
                if edge.source == node and edge.target == child:
                    edge.setVisible(visible)
            if child.is_dir and child.children_nodes:
                self._set_children_visibility(child, visible and child.is_expanded)

    def center_graph(self):
        """Centra la vista en el origen según la orientación activa."""
        if self.root_node:
            if getattr(self, "orientation", "horizontal") == "horizontal":
                self.centerOn(self.root_node.scenePos().x() + 200, 0)
            else:
                self.centerOn(self.root_node.scenePos().x(), self.root_node.scenePos().y() + 150)

    def wheelEvent(self, event):
        """Zoom suave."""
        zoom_in_factor = 1.12
        zoom_out_factor = 1 / zoom_in_factor

        if event.angleDelta().y() > 0:
            if self.zoom_level < 3.0:
                self.scale(zoom_in_factor, zoom_in_factor)
                self.zoom_level *= zoom_in_factor
        else:
            if self.zoom_level > 0.35:
                self.scale(zoom_out_factor, zoom_out_factor)
                self.zoom_level *= zoom_out_factor
