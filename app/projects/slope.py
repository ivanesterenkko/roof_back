from collections import defaultdict
from itertools import product
from typing import Dict, List

from pydantic import UUID4
from shapely.geometry import Polygon
from shapely.prepared import prep

from app.projects.models import  LinesSlope, Point


async def create_sheets(figure, roof, del_x, del_y):
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


def create_hole(figure, points):
    """Создает отверстие в фигуре, вырезая полигон из заданных точек."""
    hole_polygon = Polygon(points)
    return figure.difference(hole_polygon)


def create_figure(points, cutouts):
    figure = Polygon(points)
    for cutout in cutouts:
        figure = create_hole(figure, cutout)
    return figure
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
