from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QTextEdit, QGroupBox, QLabel, QInputDialog, QMessageBox
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QBrush, QPen, QColor

from algorithm.prufer_code import PruferAlgorithm
from frontend.drawer import GraphScene, EdgeItem

class PruferAnimator:
    def __init__(self, scene: GraphScene, log_widget: QTextEdit):
        self.scene = scene
        self.log = log_widget
        self.timer = QTimer()
        self.timer.timeout.connect(self._next_step)
        self.steps = []
        self.idx = 0
        self.running = False
        self.delay = 700

    def _log(self, msg: str, color: str = "#333"):
        self.log.append(f'<span style="color:{color}; font-weight:bold;">{msg}</span>')
        self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

    def _find_vertex(self, label: str):
        return next((v for v in self.scene.vertices if v.label_text == label), None)

    def _find_edge(self, u: str, v: str):
        key = tuple(sorted([u, v]))
        return next((e for e in self.scene.edges if tuple(sorted([e.v1.label_text, e.v2.label_text])) == key), None)

    def encode(self):
        if self.running: return
        self.log.clear()
        algo = PruferAlgorithm(
            [v.label_text for v in self.scene.vertices],
            [(e.v1.label_text, e.v2.label_text) for e in self.scene.edges]
        )
        ok, msg = algo.is_valid_tree()
        if not ok:
            QMessageBox.warning(None, "Валидация", msg)
            return
        self._log(msg, "#27ae60")
        _, self.steps = algo.encode()
        self._start()

    def decode(self):
        if self.running: return
        text, ok = QInputDialog.getText(None, "Декодирование", "Введите код Прюфера через запятую (напр.: V3,V1,V4):")
        if not ok or not text.strip(): return

        seq = [s.strip() for s in text.split(",") if s.strip()]
        self.log.clear()
        self._log(f"🔓 Декодирование: {seq}", "#8e44ad")

        algo = PruferAlgorithm([], [])
        labels, self.steps = algo.decode(seq)

        # Подготовка сцены
        self.scene.clear_all()
        for i, lbl in enumerate(labels):
            self.scene.create_vertex((i * 70 + 50, 300))
            self.scene.vertices[-1].label_text = lbl  # переопределяем метку
            self.scene.vertices[-1].update()

        self._start()

    def _start(self):
        self.idx = 0
        self.running = True
        self.timer.start(self.delay)

    def stop(self):
        self.timer.stop()
        self.running = False
        self._log("⏹ Анимация остановлена.", "#e74c3c")

    def _next_step(self):
        if self.idx >= len(self.steps):
            self.stop()
            self._log("🏁 Готово.", "#2ecc71")
            return

        step = self.steps[self.idx]
        self.idx += 1
        t = step["type"]

        if t == "highlight_v":
            v = self._find_vertex(step["label"])
            if v: v.setBrush(QBrush(QColor(step["color"])))
        elif t == "highlight_e":
            e = self._find_edge(step["u"], step["v"])
            if e: e.setPen(QPen(QColor(step["color"]), 4))
        elif t == "remove_v":
            v = self._find_vertex(step["label"])
            if v:
                self.scene.removeItem(v)
                if v in self.scene.vertices: self.scene.vertices.remove(v)
        elif t == "remove_e":
            e = self._find_edge(step["u"], step["v"])
            if e:
                self.scene.removeItem(e)
                if e in self.scene.edges: self.scene.edges.remove(e)
        elif t == "add_e":
            v1, v2 = self._find_vertex(step["u"]), self._find_vertex(step["v"])
            if v1 and v2:
                edge = EdgeItem(v1, v2)
                self.scene.addItem(edge)
                self.scene.edges.append(edge)
        elif t == "reset_colors":
            for v in self.scene.vertices: v.unhighlight()
            for e in self.scene.edges: e.setPen(QPen(QColor("#7f8c8d"), 3))
        elif t == "log":
            self._log(step["message"])
        elif t == "finish":
            self._log(f"📦 Результат: {step['sequence']}", "#d35400")


class PruferPanel(QWidget):
    """Виджет панели управления"""
    def __init__(self, scene: GraphScene):
        super().__init__()
        self.log_widget = QTextEdit()
        self.animator = PruferAnimator(scene, self.log_widget)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 0)

        grp = QGroupBox("📐 Код Прюфера")
        g_layout = QVBoxLayout(grp)

        self.encode_btn = QPushButton("▶️ Кодирование")
        self.decode_btn = QPushButton("🔓 Декодирование")
        self.stop_btn = QPushButton("🛑 Стоп")

        self.log_widget.setReadOnly(True)
        self.log_widget.setMaximumHeight(220)
        self.log_widget.setStyleSheet("background: #f8f9fa; font-family: monospace; font-size: 11px;")

        for b in [self.encode_btn, self.decode_btn, self.stop_btn]:
            b.setFixedHeight(32)
            g_layout.addWidget(b)

        g_layout.addWidget(QLabel("📜 Лог выполнения:"))
        g_layout.addWidget(self.log_widget)
        layout.addWidget(grp)

        self.encode_btn.clicked.connect(self.animator.encode)
        self.decode_btn.clicked.connect(self.animator.decode)
        self.stop_btn.clicked.connect(self.animator.stop)