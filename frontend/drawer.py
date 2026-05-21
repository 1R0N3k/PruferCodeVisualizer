import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene,
    QVBoxLayout, QWidget, QPushButton, QLabel, QSplitter,
    QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsItem
)
from PyQt6.QtCore import Qt, QLineF, QPointF
from PyQt6.QtGui import QPen, QBrush, QPainter, QColor, QTransform

from algorithm.prufer_code import PruferAlgorithm

class VertexItem(QGraphicsEllipseItem):
    def __init__(self, pos, label):
        super().__init__(-15, -15, 30, 30)
        self.setPos(QPointF(*pos) if isinstance(pos, (tuple, list)) else pos)
        self.setBrush(QBrush(QColor("lightblue")))
        self.setPen(QPen(QColor("black"), 2))
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.label_text = label
        self.setZValue(1)

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        painter.setPen(QColor("black"))
        font = painter.font()
        font.setPointSize(8)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(self.boundingRect(), Qt.AlignmentFlag.AlignCenter, self.label_text)

    def highlight(self):
        self.setBrush(QBrush(QColor("#FFD700")))

    def unhighlight(self):
        self.setBrush(QBrush(QColor("lightblue")))


class EdgeItem(QGraphicsLineItem):
    def __init__(self, v1, v2):
        super().__init__(QLineF(v1.pos(), v2.pos()))
        self.setPen(QPen(QColor("#7f8c8d"), 3))
        self.v1 = v1
        self.v2 = v2
        self.setZValue(0)

class GraphScene(QGraphicsScene):
    def __init__(self):
        super().__init__()
        self.setSceneRect(-800, -800, 1600, 1600)
        self.vertices = []
        self.edges = []
        self.first_vertex = None
        self.vertex_count = 0
        self.status_callback = None

    def mousePressEvent(self, event):
        pos = event.scenePos()
        item = self.itemAt(pos, QTransform())

        if event.button() == Qt.MouseButton.LeftButton:
            if isinstance(item, VertexItem):
                if self.first_vertex is None:
                    self.first_vertex = item
                    item.highlight()
                    self._emit_status("✅ Вершина выбрана. Кликните по второй, чтобы создать ребро.")
                elif item != self.first_vertex:
                    self.create_edge(self.first_vertex, item)
                    self.first_vertex.unhighlight()
                    self.first_vertex = None
                    self._emit_status("🔗 Ребро создано.")
                else:
                    self.first_vertex.unhighlight()
                    self.first_vertex = None
                    self._emit_status("🖱️ Режим создания рёбер отменён.")
            elif isinstance(item, EdgeItem):
                self._emit_status("⚠️ ЛКМ по ребру игнорируется. Используйте ПКМ для удаления.")
            else:
                if self.first_vertex:
                    self.first_vertex.unhighlight()
                    self.first_vertex = None
                    self._emit_status("🖱️ Режим создания рёбер отменён.")
                self.create_vertex(pos)
                self._emit_status("🟦 Вершина создана.")
            event.accept()

        elif event.button() == Qt.MouseButton.RightButton:
            if isinstance(item, VertexItem):
                self.delete_vertex(item)
                self._emit_status("🗑️ Вершина и её рёбра удалены.")
            elif isinstance(item, EdgeItem):
                self.delete_edge(item)
                self._emit_status("🗑️ Ребро удалено.")
            else:
                self._emit_status("⚠️ ПКМ работает только по вершинам и рёбрам.")
            event.accept()
        else:
            super().mousePressEvent(event)

    def create_vertex(self, pos):
        self.vertex_count += 1
        v = VertexItem(pos, f"V{self.vertex_count}")
        self.addItem(v)
        self.vertices.append(v)

    def delete_vertex(self, vertex):
        edges_to_del = [e for e in self.edges if e.v1 == vertex or e.v2 == vertex]
        for e in edges_to_del:
            self.delete_edge(e)
        self.removeItem(vertex)
        if vertex in self.vertices:
            self.vertices.remove(vertex)
        if self.first_vertex == vertex:
            self.first_vertex = None

    def create_edge(self, v1, v2):
        for e in self.edges:
            if (e.v1 == v1 and e.v2 == v2) or (e.v1 == v2 and e.v2 == v1):
                return
        edge = EdgeItem(v1, v2)
        self.addItem(edge)
        self.edges.append(edge)

    def delete_edge(self, edge):
        self.removeItem(edge)
        if edge in self.edges:
            self.edges.remove(edge)

    def clear_all(self):
        for item in self.items():
            self.removeItem(item)
        self.vertices.clear()
        self.edges.clear()
        self.first_vertex = None
        self.vertex_count = 0
        self._emit_status("🧹 Граф полностью очищен.")

    def _emit_status(self, msg):
        if self.status_callback:
            self.status_callback(msg)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("📐 Интерактивный редактор графов")
        self.resize(950, 650)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.status_label = QLabel("ЛКМ по пустому месту: создать вершину | ЛКМ+ЛКМ: соединить | ПКМ: удалить")
        self.status_label.setStyleSheet("background: #f8f9fa; color: #333; padding: 8px; border-bottom: 2px solid #dee2e6; font-weight: bold;")
        main_layout.addWidget(self.status_label)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(15, 15, 15, 15)

        self.clear_btn = QPushButton("🗑 Удалить весь граф")
        self.clear_btn.setStyleSheet("font-size: 14px; padding: 10px; background: #ff6b6b; color: white; border: none; border-radius: 4px;")
        left_layout.addWidget(self.clear_btn)

        left_layout.addSpacing(10)

        left_panel.setMaximumWidth(240)

        self.view = QGraphicsView()
        self.scene = GraphScene()
        self.view.setScene(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.view.setStyleSheet("background: #ffffff; border: 1px solid #ccc;")




        from frontend.prufer_animator import PruferPanel
        self.prufer_panel = PruferPanel(self.scene)
        left_layout.insertWidget(1, self.prufer_panel)

        self.clear_btn.clicked.connect(self.scene.clear_all)
        self.scene.status_callback = self.status_label.setText

        splitter.addWidget(left_panel)
        splitter.addWidget(self.view)
        splitter.setSizes([240, 710])

        main_layout.addWidget(splitter)

        self.clear_btn.clicked.connect(self.scene.clear_all)


