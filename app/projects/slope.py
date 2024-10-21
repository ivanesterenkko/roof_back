from collections import defaultdict
from itertools import product
from typing import List

import numpy as np
from shapely.geometry import Polygon

from app.projects.schemas import PointData


class SlopeExtractor:
    def __init__(self, lines):
        self.lines = lines
        self.graph = defaultdict(list)
        self.line_set = set()
        self.lines_id = {}

    def build_graph(self):
        """Построение графа точек, соединённых линиями."""
        for line in self.lines:
            line_id, line_obj = line
            start, end = line_obj.start, line_obj.end
            edge = tuple(sorted((start, end)))
            self.graph[start].append(end)
            self.graph[end].append(start)
            self.line_set.add(edge)
            self.lines_id[edge] = line_id

    def find_cycles(self):
        """Поиск всех циклов в графе."""
        self.build_graph()
        cycles = []
        for start_node in self.graph:
            stack = [(start_node, [start_node])]
            while stack:
                current_node, path = stack.pop()
                for neighbor in self.graph[current_node]:
                    if neighbor == path[0] and len(path) > 2:
                        cycle = tuple(sorted(path))
                        if self.is_valid_cycle(path) and cycle not in cycles:
                            cycles.append(path)
                    elif neighbor not in path:
                        stack.append((neighbor, path + [neighbor]))
        return cycles

    def filter_cycles(self, cycles):
        """Фильтрует циклы, исключая составные фигуры и дубликаты."""
        unique_cycles = []
        for cycle in cycles:
            cycle_coords = [(point.x, point.y) for point in cycle]
            polygon = Polygon(cycle_coords)
            is_unique = True
            remove_cycles = []
            for idx, other_cycle in enumerate(unique_cycles):
                other_coords = [(point.x, point.y) for point in other_cycle]
                other_polygon = Polygon(other_coords)
                if polygon.contains(other_polygon) or polygon.equals(other_polygon):
                    is_unique = False
                    break
                elif other_polygon.contains(polygon):
                    remove_cycles.append(idx)
            # Удаляем более крупные циклы, которые содержат текущий полигон
            for idx in sorted(remove_cycles, reverse=True):
                del unique_cycles[idx]
            if is_unique:
                unique_cycles.append(cycle)
        return unique_cycles

    def is_valid_cycle(self, cycle):
        """Проверка, что все рёбра цикла присутствуют в исходных линиях."""
        for i in range(len(cycle)):
            p1 = cycle[i]
            p2 = cycle[(i + 1) % len(cycle)]
            edge = tuple(sorted((p1, p2)))
            if edge not in self.line_set:
                return False
        return True

    def extract_slopes(self):
        """Извлечение всех фигур из точек и линий."""
        cycles = self.find_cycles()
        cycles = self.filter_cycles(cycles)
        slopes = []
        for cycle in cycles:
            slope_lines = []
            for i in range(len(cycle)):
                start = cycle[i]
                end = cycle[(i + 1) % len(cycle)]
                edge = tuple(sorted((start, end)))
                line_id = self.lines_id.get(edge)
                if line_id:
                    slope_lines.append(line_id)
            slopes.append(slope_lines)
        return slopes


async def create_sheets(figure, roof):
    """Создание листов для покрытия полигона."""
    sheets = []
    overall_width = roof.overall_width
    delta_width = roof.overall_width - roof.useful_width
    length_max = roof.max_length
    length_min = roof.min_length
    overlap = roof.overlap

    x_min, y_min, x_max, y_max = figure.bounds
    x = x_min

    while x < x_max:
        x_start = x
        x += overall_width
        y = y_min

        while y < y_max:
            y_start = y
            y += length_max
            sheet = Polygon([
                (x_start, y_start),
                (x, y_start),
                (x, y),
                (x_start, y)
            ])
            intersection = figure.intersection(sheet)

            if not intersection.is_empty:
                coords = list(intersection.bounds)
                sheet_height = coords[3] - coords[1]
                sheet_width = coords[2] - coords[0]

                if sheet_height < overlap or sheet_width < delta_width:
                    continue
                elif sheet_height < length_min:
                    coords[3] = coords[1] + length_min

                sheets.append([
                    round(x_start, 2),
                    round(y_start, 2),
                    round(coords[3] - coords[1], 2),
                    round(overall_width * (coords[3] - coords[1]), 2)
                ])
            if y + length_min - overlap < y_max:
                y -= overlap

        if x < x_max:
            x -= delta_width

    return sheets


def create_hole(figure, hole_points):
    """Создает отверстие в фигуре, вырезая полигон из заданных точек."""
    coordinates = [(point.x, point.y) for point in hole_points]
    hole_polygon = Polygon(coordinates)
    return figure.difference(hole_polygon)


def get_next_name(existing_names: List[str]) -> str:
    """Генерирует следующее имя для линии в формате Excel-стиля."""
    alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

    def generate_names():
        for length in range(1, 3):
            for letters in product(alphabet, repeat=length):
                yield ''.join(letters)

    name_generator = generate_names()

    for name in name_generator:
        if name not in existing_names:
            return name


class LineRotate:
    def __init__(self, line_id, start, end, line_type):
        self.id = line_id
        self.start = np.array(start) 
        self.end = np.array(end)      
        self.line_type = line_type    

    def rotate(self, angle, origin=(0, 0)):
        """Поворачивает линию на заданный угол относительно точки origin."""
        rotation_matrix = np.array([
            [np.cos(angle), -np.sin(angle)],
            [np.sin(angle),  np.cos(angle)]
        ])
        origin = np.array(origin)

        # Поворот начала и конца линии
        self.start = np.dot(rotation_matrix, self.start - origin) + origin
        self.end = np.dot(rotation_matrix, self.end - origin) + origin

    def translate(self, offset):
        """Сдвигает линию на заданное смещение."""
        self.start += offset
        self.end += offset

    def reflect_over_line(self, line):
        """Отражает линию относительно заданной линии."""
        # Представляем линию для отражения как вектор
        line_vec = line.end - line.start
        line_vec_norm = line_vec / np.linalg.norm(line_vec)

        def reflect_point(point):
            point_vec = point - line.start
            projection_length = np.dot(point_vec, line_vec_norm)
            projection = projection_length * line_vec_norm
            perpendicular = point_vec - projection
            reflected_point = line.start + projection - perpendicular
            return reflected_point

        self.start = reflect_point(self.start)
        self.end = reflect_point(self.end)

    def __repr__(self):
        return f"Line(start={self.start}, end={self.end}, type={self.line_type})"


def align_figure(lines):
    """
    Разворачивает фигуру так, чтобы линия с типом 'Perimeter' была параллельна оси OX
    и находилась в первой четверти, начиная с точки (0, 0).
    """
    cornice_line = next((line for line in lines if line.line_type == 'Perimeter'), None)
    if cornice_line is None:
        raise ValueError("Линия не найдена")

    dx = cornice_line.end[0] - cornice_line.start[0]
    dy = cornice_line.end[1] - cornice_line.start[1]
    angle = -np.arctan2(dy, dx)  # Угол поворота для выравнивания по оси OX

    for line in lines:
        line.rotate(angle)

    translation_vector = -cornice_line.start  # Сдвиг для начала координат
    for line in lines:
        line.translate(translation_vector)

    for line in lines:
        if line.line_type != 'Perimeter':
            # Проверяем, если хотя бы одна из точек линии ниже карниза
            if line.start[1] < cornice_line.start[1] or line.end[1] < cornice_line.start[1]:
                line.reflect_over_line(cornice_line)

    if cornice_line.end[0] < 0 or cornice_line.end[1] < 0:
        raise ValueError("После трансформации 'Perimeter' не находится в первой четверти")

    return lines
