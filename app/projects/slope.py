from collections import defaultdict
from itertools import product
from typing import List

import numpy as np
from shapely.geometry import Polygon
from shapely.prepared import prep

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
    """Создание листов для ската."""
    sheets = []
    overall_width = roof.overall_width
    delta_width = roof.overall_width - roof.useful_width
    length_max = roof.max_length
    length_min = roof.min_length
    overlap = roof.overlap

    x_min, y_min, x_max, y_max = figure.bounds
    prepared_figure = prep(figure)

    x_positions = []
    x = x_min
    while x < x_max:
        x_positions.append(x)
        x += overall_width
        x -= delta_width

    y_positions = []
    y = y_min
    while y < y_max:
        y_positions.append(y)
        y += length_max
        y -= overlap

    for x_start in x_positions:
        x_end = x_start + overall_width
        for y_start in y_positions:
            y_end = y_start + length_max

            sheet_polygon = Polygon([
                (x_start, y_start),
                (x_end, y_start),
                (x_end, y_end),
                (x_start, y_end)
            ])

            if not prepared_figure.intersects(sheet_polygon):
                continue

            intersection = figure.intersection(sheet_polygon)
            if intersection.is_empty:
                continue

            coords = list(intersection.bounds)
            sheet_height = coords[3] - coords[1]
            sheet_width = coords[2] - coords[0]

            if sheet_height < overlap or sheet_width < delta_width:
                continue
            elif sheet_height < length_min:
                coords[3] = coords[1] + length_min

            sheets.append([
                round(x_start, 2),
                round(coords[1], 2),
                round(coords[3] - coords[1], 2)
            ])

    return sheets


def create_hole(figure, hole_points):
    """Создает отверстие в фигуре, вырезая полигон из заданных точек."""
    coordinates = [(point[0], point[1]) for point in hole_points]
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
    def __init__(self, line_id, line_name, start, end, line_type):
        self.id = line_id
        self.name = line_name
        self.start = np.array(start, dtype=float)
        self.end = np.array(end, dtype=float)
        self.line_type = line_type

    def __repr__(self):
        return f"Line(id={self.id}, start={self.start}, end={self.end}, type={self.line_type})"

def align_figure(lines):
    """
    Разворачивает фигуру так, чтобы линия с типом 'Perimeter' была параллельна оси OX
    и вся фигура находилась в первой четверти (без отрицательных координат).
    Все координаты округляются до 2 знаков после запятой.
    """
    # Поиск линии типа 'Perimeter'
    cornice_line = next((line for line in lines if line.line_type == 'Perimeter'), None)
    if cornice_line is None:
        raise ValueError("Линия с типом 'Perimeter' не найдена")

    # Вычисление угла поворота для выравнивания по оси OX
    dx = cornice_line.end[0] - cornice_line.start[0]
    dy = cornice_line.end[1] - cornice_line.start[1]
    angle = -np.arctan2(dy, dx)

    # Создание массива всех стартовых и конечных точек
    starts = np.array([line.start for line in lines])
    ends = np.array([line.end for line in lines])

    # Центр вращения — точка начала cornice_line
    origin = cornice_line.start

    # Создание матрицы поворота
    cos_angle = np.cos(angle)
    sin_angle = np.sin(angle)
    rotation_matrix = np.array([[cos_angle, -sin_angle],
                                [sin_angle,  cos_angle]])

    # Поворот всех точек вокруг origin
    starts_rotated = np.dot(starts - origin, rotation_matrix.T) + origin
    ends_rotated = np.dot(ends - origin, rotation_matrix.T) + origin

    # Обновление координат линий после поворота
    for i, line in enumerate(lines):
        line.start = starts_rotated[i]
        line.end = ends_rotated[i]

    # Получение обновленного cornice_line после поворота
    cornice_line = next((line for line in lines if line.line_type == 'Perimeter'), None)

    # Вычисляем среднее по Y для cornice_line
    cornice_y = (cornice_line.start[1] + cornice_line.end[1]) / 2

    # Собираем индексы линий, которые нужно отразить
    lines_to_reflect = []
    for i, line in enumerate(lines):
        if line.line_type != 'Perimeter':
            if line.start[1] < cornice_y or line.end[1] < cornice_y:
                lines_to_reflect.append(i)

    # Отражение линий
    if lines_to_reflect:
        # Вектор нормали к cornice_line
        line_vec = cornice_line.end - cornice_line.start
        line_vec_norm = line_vec / np.linalg.norm(line_vec)
        normal_vec = np.array([-line_vec_norm[1], line_vec_norm[0]])

        # Функция отражения точек
        def reflect_points(points):
            point_vecs = points - cornice_line.start
            distances = np.dot(point_vecs, normal_vec)
            reflected_points = points - 2 * np.outer(distances, normal_vec)
            return reflected_points

        # Отражаем стартовые и конечные точки выбранных линий
        starts_to_reflect = np.array([lines[i].start for i in lines_to_reflect])
        ends_to_reflect = np.array([lines[i].end for i in lines_to_reflect])

        starts_reflected = reflect_points(starts_to_reflect)
        ends_reflected = reflect_points(ends_to_reflect)

        # Обновляем координаты отраженных линий
        for idx, i in enumerate(lines_to_reflect):
            lines[i].start = starts_reflected[idx]
            lines[i].end = ends_reflected[idx]

    # После поворота и отражения находим минимальные координаты
    all_points = np.vstack(([line.start for line in lines], [line.end for line in lines]))
    min_x = np.min(all_points[:, 0])
    min_y = np.min(all_points[:, 1])

    # Сдвигаем все точки так, чтобы минимальные координаты стали нулевыми
    translation_vector = np.array([-min_x, -min_y])
    for line in lines:
        line.start += translation_vector
        line.end += translation_vector

    # Округление координат до 2 знаков после запятой
    for line in lines:
        line.start = np.round(line.start, 2)
        line.end = np.round(line.end, 2)

    # Проверка на отрицательные координаты с учетом допустимой погрешности
    epsilon = 1e-10  # Допустимая погрешность
    for line in lines:
        if np.any(line.start < -epsilon) or np.any(line.end < -epsilon):
            raise ValueError("После трансформации некоторые координаты отрицательны")

    return lines
