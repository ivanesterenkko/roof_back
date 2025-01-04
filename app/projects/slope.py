from collections import defaultdict
from itertools import product
import math
from typing import Dict, List

import numpy as np
from pydantic import UUID4
from shapely.geometry import Polygon
from shapely.prepared import prep
import time

from app.projects.models import Lines, LinesSlope, Point


async def create_sheets(figure, roof, del_x, del_y):
    """Создание листов для ската."""
    sheets = []
    overall_width = roof.overall_width
    delta_width = roof.overall_width - roof.useful_width
    length_max = roof.max_length
    overlap = roof.overlap

    x_min, y_min, x_max, y_max = figure.bounds
    prepared_figure = prep(figure)

    x_positions = []
    x = x_min + del_x
    while x < x_max:
        x_positions.append(x)
        x += overall_width
        x -= delta_width

    y_positions = []
    y = y_min + del_y
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
            # elif sheet_height < length_min:
            #     coords[3] = coords[1] + length_min
            length = round(coords[3] - coords[1], 2)
            sheets.append([
                round(x_start, 2),
                round(coords[1], 2),
                length,
                round(overall_width*length, 2),
                round(roof.useful_width*length, 2)
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


# class Point:
#     def __init__(self, x, y):
#         self.x = round(x, 2)
#         self.y = round(y, 2)
#         self.lines = []  # Связанные линии

#     def move(self, x, y, moved_lines=None, moved_points=None):
#         x = round(x, 2)
#         y = round(y, 2)
#         if self.x == x and self.y == y:
#             return

#         if moved_points is None:
#             moved_points = set()
#         if self in moved_points:
#             return
#         moved_points.add(self)

#         self.x = x
#         self.y = y

#         if moved_lines is None:
#             moved_lines = set()
#         for line in self.lines:
#             if line in moved_lines:
#                 continue
#             moved_lines.add(line)
#             line.point_moved(self, moved_lines, moved_points)


# class PointFactory:
#     def __init__(self):
#         self.points = {}

#     def get_or_create_point(self, x, y):
#         # Округляем координаты для согласованности
#         x = round(x, 2)
#         y = round(y, 2)
#         # Проверяем, существует ли уже точка с такими координатами
#         if (x, y) not in self.points:
#             self.points[(x, y)] = Point(x, y)
#         return self.points[(x, y)]


# class Line:
#     def __init__(self, point1, point2, id, parent_id):
#         self.point1 = point1
#         self.point2 = point2
#         self.line_id = id
#         self.parent_id = parent_id
#         self.update_length()

#         # Регистрируем линию у точек
#         point1.lines.append(self)
#         point2.lines.append(self)

#     def update_length(self):
#         dx = self.point2.x - self.point1.x
#         dy = self.point2.y - self.point1.y
#         self.length = round(math.hypot(dx, dy), 2)

#     def point_moved(self, moved_point, moved_lines, moved_points):
#         other_point = self.point2 if moved_point == self.point1 else self.point1

#         # Пересчитываем длину, не учитывая угол
#         self.update_length()

#         # Перемещаем другую точку для сохранения длины линии
#         dx = other_point.x - moved_point.x
#         dy = other_point.y - moved_point.y
#         distance = math.hypot(dx, dy)

#         if distance > 1e-9:
#             scaling_factor = self.length / distance
#             new_x = moved_point.x + dx * scaling_factor
#             new_y = moved_point.y + dy * scaling_factor

#             # Перемещаем другую точку
#             other_point.move(new_x, new_y, moved_lines, moved_points)

#     def change_length(self, new_length, moved_lines=None, moved_points=None):
#         if moved_lines is None:
#             moved_lines = set()
#         if moved_points is None:
#             moved_points = set()

#         self.length = round(new_length, 2)

#         # Перемещаем конечную точку, чтобы сохранить новую длину без учета угла
#         dx = self.point2.x - self.point1.x
#         dy = self.point2.y - self.point1.y
#         distance = math.hypot(dx, dy)

#         if distance > 1e-9:
#             scaling_factor = self.length / distance
#             new_x = self.point1.x + dx * scaling_factor
#             new_y = self.point1.y + dy * scaling_factor
#             self.point2.move(new_x, new_y, moved_lines, moved_points)

#         # Обновляем длину линии
#         self.update_length()


# class SlopeUpdate:
#     def __init__(self, lines_s):
#         point_factory = PointFactory()
#         lines = []
#         for line_s in lines_s:
#             # Получаем существующую точку или создаем новую, если её еще нет
#             point1 = point_factory.get_or_create_point(line_s.x_start, line_s.y_start)
#             point2 = point_factory.get_or_create_point(line_s.x_end, line_s.y_end)
#             lines.append(Line(point1, point2, line_s.id, line_s.line_id))
#         self.lines = lines

#     def get_min_max_y(self):
#         min_y = min(min(line.point1.y, line.point2.y) for line in self.lines)
#         max_y = max(max(line.point1.y, line.point2.y) for line in self.lines)
#         return min_y, max_y

#     def change_line_length(self, line_id, new_line_length):

#         for line_s in self.lines:
#             if line_s.line_id == line_id:
#                 line_s.change_length(new_line_length)

#         return self.lines

#     def change_slope_length(self, new_slope_length):
#         min_y, max_y = self.get_min_max_y()
#         current_slope_length = max_y - min_y
#         if current_slope_length <= 0:
#             return

#         # scaling_factor = new_slope_length / current_slope_length
#         for line in self.lines:
#             if line.point1.y == max_y or line.point2.y == max_y:
#                 # Находим точку с наибольшим y и перемещаем её
#                 top_point = line.point1 if line.point1.y == max_y else line.point2
#                 # fixed_point = line.point2 if top_point == line.point1 else line.point1

#                 # Пересчитываем y верхней точки для новой длины ската
#                 new_top_y = min_y + new_slope_length
#                 top_point.move(top_point.x, new_top_y)

#                 # Обновляем длину линии
#                 line.update_length()
#         return self.lines


# def update_coords(x1, y1, x2, y2, length, new_length):
#     k = new_length / length
#     x2_new = x1 + (x2 - x1) * k
#     y2_new = y1 + (y2 - y1) * k

#     return (x1, y1, x2_new, y2_new)


class GraphBuilder:
    def __init__(self, lines, point_coords):
        self.lines = lines
        self.point_coords = point_coords
        self.graph = defaultdict(list)
        self.line_edges = set()
        self._polygon_cache = {}
        self.line_map = {}
        for line in lines:
            e = tuple(sorted((line.start_id, line.end_id)))
            self.line_map[e] = line.id

    def build_graph(self):
        for line in self.lines:
            start_id = line.start_id
            end_id = line.end_id
            edge = tuple(sorted((start_id, end_id)))
            self.graph[start_id].append(end_id)
            self.graph[end_id].append(start_id)
            self.line_edges.add(edge)

    def _canonical_cycle(self, cycle_path):
        cycle = cycle_path[:-1]
        min_idx = min(range(len(cycle)), key=lambda i: cycle[i])
        cycle = cycle[min_idx:] + cycle[:min_idx]
        cycle_reversed = list(reversed(cycle))
        if cycle_reversed < cycle:
            cycle = cycle_reversed
        cycle.append(cycle[0])
        return tuple(cycle)

    def find_all_cycles(self):
        self.build_graph()
        all_cycles = []
        visited = set()
        for start_node in self.graph:
            stack = [(start_node, [start_node])]
            while stack:
                current_node, path = stack.pop()
                for neighbor in self.graph[current_node]:
                    if neighbor == path[0] and len(path) > 2:
                        if self.is_valid_cycle(path):
                            cycle_path = path + [neighbor]
                            can_cycle = self._canonical_cycle(cycle_path)
                            if can_cycle not in visited:
                                visited.add(can_cycle)
                                all_cycles.append(cycle_path)
                    elif neighbor not in path:
                        stack.append((neighbor, path + [neighbor]))
        return all_cycles

    def is_valid_cycle(self, path):
        for i in range(len(path) - 1):
            e = tuple(sorted((path[i], path[i+1])))
            if e not in self.line_edges:
                return False
        return True

    def _build_polygon(self, cycle_path):
        key = tuple(cycle_path)
        if key in self._polygon_cache:
            return self._polygon_cache[key]
        coords = [self.point_coords[v] for v in cycle_path]
        if len(set(coords)) < 3:
            self._polygon_cache[key] = None
            return None
        try:
            poly = Polygon(coords)
            if poly.is_empty or not poly.is_valid:
                self._polygon_cache[key] = None
                return None
            self._polygon_cache[key] = poly
            return poly
        except Exception as e:
            print(f"Не удалось построить Polygon для пути {cycle_path}: {e}")
            self._polygon_cache[key] = None
            return None

    def filter_by_contains(self, cycles):
        unique_cycles = []
        for cycle_path in cycles:
            polyC = self._build_polygon(cycle_path)
            if polyC is None:
                continue
            is_contained = False
            to_remove = []
            for idx, other_cycle in enumerate(unique_cycles):
                polyO = self._build_polygon(other_cycle)
                if polyO is None:
                    continue
                if polyC.contains(polyO):
                    is_contained = True
                    break
                elif polyO.contains(polyC):
                    to_remove.append(idx)
            if is_contained:
                continue
            for idx in reversed(to_remove):
                del unique_cycles[idx]
            unique_cycles.append(cycle_path)
        return unique_cycles

    def find_minimal_cycles_by_geometry(self):
        allc = self.find_all_cycles()
        filtered = self.filter_by_contains(allc)
        line_cycles = []
        for cycle_path in filtered:
            ids = []
            for i in range(len(cycle_path) - 1):
                e = tuple(sorted((cycle_path[i], cycle_path[i+1])))
                ids.append(self.line_map[e])
            line_cycles.append(ids)
        return line_cycles


def find_slope(lines):
    points = {}
    for line in lines:
        if line.start_id not in points:
            points[line.start_id] = (line.start.x, line.start.y)
        if line.end_id not in points:
            points[line.end_id] = (line.end.x, line.end.y)
    builder = GraphBuilder(lines, points)
    minimal_cycles = builder.find_minimal_cycles_by_geometry()
    return minimal_cycles


def process_lines_and_generate_slopes(lines: List[LinesSlope]):
    point_to_lines: Dict[Point, List[LinesSlope]] = {}
    point_k = []
    point_p = []
    slope_lines = []
    line_k: Dict[float, List[UUID4]] = defaultdict(list)
    line_p: Dict[float, List[UUID4]] = defaultdict(list)
    for line in lines:
        for point in [line.start, line.end]:
            if point not in point_to_lines:
                point_to_lines[point] = []
            point_to_lines[point].append(line)
    for point, connected_lines in point_to_lines.items():
        if point.y == 0 or point.x == 0:
            continue
        if connected_lines[0].type == connected_lines[1].type and connected_lines[0].type=="конёк":
            point_k.append(point)
        else:
            point_p.append(point)
    for point in point_k:
        f = 0
        for line in lines:
            if line.type == "конёк":
                continue
            if line.start.x == line.end.x:
                length = abs(line.start.x - point.x)
            elif line.start.y == line.end.y:
                length = abs(line.start.y - point.y)
            else:
                continue
            if f == 0 and length not in line_k[length]:
                line_k[length].append(line.id)
                slope_lines.append([point.id, line.id])
                f = 1

    for point in point_p:
        f = 0
        for line in lines:
            if line.type != "конёк":
                continue
            if line.start.x == line.end.x:
                length = abs(line.start.x - point.x)
            elif line.start.y == line.end.y:
                length = abs(line.start.y - point.y)
            else:
                continue
            if f == 0 and length not in line_p[length]:
                line_p[length].append(line.id)
                slope_lines.append([point.id, line.id])
                f = 1
        # if f == 0:
        #     for point_n in point_k:
        #         if point.x == point_n.x:
        #             length = abs(point.y - point_n.y)
        #         elif point.y == point_n.y:
        #             length = abs(point.x - point_n.x)
        #         else:
        #             continue
        #         if f == 0 and length not in line_p[length]:
        #             line_p[length].append(point_n.id)
        #             slope_lines.append([point, point_n])
        #             f = 1

    return slope_lines
