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

        if not ok or not text.strip(): 
            QMessageBox.warning(None, "Валидация кода", "Пустая строка! Введите код Прюфера по примеру.")
            return

        seq = [s.strip() for s in text.split(",") if s.strip()]
        self.log.clear()
        self._log(f"Декодирование: {seq}", "#8e44ad")

        algo = PruferAlgorithm([], [])
        try:
            labels, steps = algo.decode(seq)
        except TypeError:
            QMessageBox.warning(None, "Валидация кода", "Ошибка декодирования!")
            return
        # 1. Извлекаем будущие рёбра из шагов анимации, чтобы понять структуру дерева
        # Ищем все шаги типа 'add_e', где указаны вершины u и v
        future_edges = [(s["u"], s["v"]) for s in steps if s.get("type") == "add_e"]

        # 2. Вычисляем древовидную раскладку координат
        pos_map = self._calculate_tree_layout(labels, future_edges)

        # 3. Создаём вершины сразу на правильных местах
        self.scene.clear_all()
        for lbl in labels:
            # drawer.py сам преобразует кортеж в QPointF, если мы сделали фикс из прошлого шага
            self.scene.create_vertex(pos_map[lbl])
            
            # Переопределяем метку (create_vertex создает V1, V2...)
            v = self.scene.vertices[-1]
            v.label_text = lbl  
            v.update()

        self.steps = steps
        self._start()
    
    def _calculate_tree_layout(self, labels, edges):
        """
        Вычисляет координаты (x, y) для вершин, чтобы образовать дерево.
        """
        # Строим граф смежности
        adj = {v: [] for v in labels}
        for u, v in edges:
            adj[u].append(v)
            adj[v].append(u)

        # Выбираем корень (вершина с максимальным числом связей)
        root = max(adj, key=lambda x: len(adj[x]))

        # Преобразуем в ориентированное дерево (Родитель -> Дети)
        tree_adj = {v: [] for v in labels}
        visited = {root}
        queue = [root]
        
        while queue:
            node = queue.pop(0)
            for nb in adj[node]:
                if nb not in visited:
                    visited.add(nb)
                    tree_adj[node].append(nb)
                    queue.append(nb)

        positions = {}
        tree_width = 50  # Базовая ширина листа
        vertical_spacing = 80

        # Рекурсивная функция раскладки
        def dfs(node, depth, start_x):
            children = tree_adj[node]
            
            # Если лист
            if not children:
                positions[node] = (start_x, depth * vertical_spacing)
                return start_x + tree_width

            # Если есть дети, рекурсивно раскладываем их
            current_x = start_x
            child_xs = []
            for child in children:
                child_right_edge = dfs(child, depth + 1, current_x)
                child_center_x = (current_x + child_right_edge) / 2
                child_xs.append(child_center_x)
                current_x = child_right_edge

            # Родитель центрируется между первым и последним ребенком
            parent_x = (child_xs[0] + child_xs[-1]) / 2
            positions[node] = (parent_x, depth * vertical_spacing)
            
            return current_x

        # Запускаем раскладку
        total_width = dfs(root, 0, 50)

        # Масштабируем дерево, чтобы оно влезало в экран (по центру)
        scene_width = 800 
        scale = (scene_width - 100) / total_width if total_width > 0 else 1
        
        # Центрируем по X (400 - середина сцены)
        offset_x = 400 - (total_width * scale) / 2
        
        # Итоговые координаты
        final_pos = {}
        for lbl, (x, y) in positions.items():
            final_pos[lbl] = (x * scale + offset_x, y + 50)
            
        return final_pos

    def _start(self):
        self.idx = 0
        self.running = True
        self.timer.start(self.delay)

    def stop(self):
        self.timer.stop()
        self.running = False
        self._log("Анимация остановлена.", "#e74c3c")

    def _next_step(self):
        if self.idx >= len(self.steps):
            self.stop()
            self._log("Готово.", "#2ecc71")
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
            result_code_string = step['sequence']
            self._log(f"Результат: {result_code_string}", "#d35400")

    

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

        grp = QGroupBox("Код Прюфера")
        g_layout = QVBoxLayout(grp)

        self.encode_btn = QPushButton("Кодирование")
        self.decode_btn = QPushButton("Декодирование")
        self.stop_btn = QPushButton("Стоп")

        self.log_widget.setReadOnly(True)
        self.log_widget.setMaximumHeight(220)
        self.log_widget.setStyleSheet("background: #f8f9fa; font-family: monospace; font-size: 11px;")

        for b in [self.encode_btn, self.decode_btn, self.stop_btn]:
            b.setFixedHeight(32)
            g_layout.addWidget(b)

        g_layout.addWidget(QLabel("Лог выполнения:"))
        g_layout.addWidget(self.log_widget)
        layout.addWidget(grp)

        self.encode_btn.clicked.connect(self.animator.encode)
        self.decode_btn.clicked.connect(self.animator.decode)
        self.stop_btn.clicked.connect(self.animator.stop)