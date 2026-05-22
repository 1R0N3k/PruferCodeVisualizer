from typing import List, Tuple, Dict, Any

class PruferAlgorithm:
    def __init__(self, vertices: List[str], edges: List[Tuple[str, str]]):
        self.vertices = list(vertices)
        self.edges = [tuple(sorted(e)) for e in edges]

    def _parse_label(self, label: str) -> int:
        """Позволяет корректно сортировать V1, V2, ..., V10"""
        try:
            return int(label.replace("V", "").replace("v", ""))
        except ValueError:
            return label

    def is_valid_tree(self) -> Tuple[bool, str]:
        if len(self.vertices) < 2:
            return False, "Дерево должно содержать минимум 2 вершины."
        if len(self.edges) != len(self.vertices) - 1:
            return False, f"Количество рёбер ({len(self.edges)}) ≠ n-1. Граф не является деревом."

        adj = {v: set() for v in self.vertices}
        for u, v in self.edges:
            adj[u].add(v)
            adj[v].add(u)

        visited = set()
        queue = [self.vertices[0]]
        visited.add(self.vertices[0])
        while queue:
            curr = queue.pop(0)
            for nb in adj[curr]:
                if nb not in visited:
                    visited.add(nb)
                    queue.append(nb)

        if len(visited) != len(self.vertices):
            return False, "Граф несвязный. Код Прюфера применим только к деревьям."
        return True, "Граф валиден. Это дерево."

    def encode(self) -> Tuple[List[str], List[Dict[str, Any]]]:
        adj = {v: set() for v in self.vertices}
        for u, v in self.edges:
            adj[u].add(v)
            adj[v].add(u)

        steps = []
        sequence = []

        while len(adj) > 2:
            leaves = [v for v in adj if len(adj[v]) == 1]
            min_leaf = min(leaves, key=self._parse_label)
            neighbor = next(iter(adj[min_leaf]))

            steps.append({"type": "highlight_v", "label": min_leaf, "color": "#f1c40f"})
            steps.append({"type": "highlight_e", "u": min_leaf, "v": neighbor, "color": "#e74c3c"})
            steps.append({"type": "log", "message": f"Лист '{min_leaf}' -> родитель '{neighbor}'"})
            sequence.append(neighbor)

            steps.append({"type": "remove_e", "u": min_leaf, "v": neighbor})
            steps.append({"type": "remove_v", "label": min_leaf})
            steps.append({"type": "reset_colors"})

            adj[neighbor].remove(min_leaf)
            del adj[min_leaf]

        remaining = sorted(adj.keys(), key=self._parse_label)
        steps.append({"type": "log", "message": f"Остались вершины {remaining}. Кодирование завершено."})
        steps.append({"type": "finish", "sequence": sequence})
        return sequence, steps

    def decode(self, sequence: List[str]) -> Tuple[List[str], List[Dict[str, Any]]]:
        n = len(sequence) + 2
        steps = []

        all_labels = set(sequence)
        i = 1
        while len(all_labels) < n:
            lbl = f"V{i}"
            if lbl not in all_labels:
                all_labels.add(lbl)
            i += 1
        all_labels = sorted(all_labels, key=self._parse_label)

        degree = {v: 1 for v in all_labels}
        for s in sequence:
            degree[s] += 1

        for s in sequence:
            leaves = [v for v in degree if degree[v] == 1]
            min_leaf = min(leaves, key=self._parse_label)

            steps.append({"type": "highlight_v", "label": min_leaf, "color": "#3498db"})
            steps.append({"type": "highlight_v", "label": s, "color": "#e67e22"})
            steps.append({"type": "log", "message": f"Соединяем '{min_leaf}' (лист) и '{s}' (из кода)"})
            steps.append({"type": "add_e", "u": min_leaf, "v": s})
            steps.append({"type": "reset_colors"})

            degree[min_leaf] -= 1
            degree[s] -= 1

        remaining = [v for v in degree if degree[v] == 1]
        if len(remaining) == 2:
            steps.append({"type": "log", "message": f"Финальное ребро: '{remaining[0]}' - '{remaining[1]}'"})
            steps.append({"type": "add_e", "u": remaining[0], "v": remaining[1]})

        steps.append({"type": "finish", "sequence": sequence})
        return all_labels, steps