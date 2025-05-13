from collections import defaultdict
from itertools import product
import math
from typing import Dict, List

from pydantic import UUID4
from shapely import Point
from shapely.geometry import Polygon
from shapely.prepared import prep

from app.base.models import AccessoriesBD
from app.projects.models import  LinesSlope, PointSlope


def create_sheets(figure, roof, is_left, overhang):
    sheets = []
    overall_width = roof.overall_width
    delta_width = roof.overall_width - roof.useful_width
    length_max = roof.max_length
    overlap = roof.overlap
    length_min = roof.min_length
    sizes = roof.imp_sizes
    left = is_left
    x_min, y_min, x_max, y_max = figure.bounds
    prepared_figure = prep(figure)
    x_positions = []
    x = x_min
    if abs(x) >= overall_width:
        m = x // abs(x)
        x = m * abs(x) % overall_width
    if left:
        while x < x_max:
            x_positions.append(x)
            x += overall_width
            x -= delta_width
    else:
        while x_max >= x:
            x_max -= overall_width
            x_positions.append(x_max)
            x_max += delta_width
    if not overhang:
        overhang = 0
    y_positions = []
    y = y_min - overhang
    y_levels = []
    y_min_l = y_min - overhang
    while y_min_l <= y_max:
        y_levels.append(y_min_l)
        y_min_l += overlap
    while y < y_max:
        y_positions.append(y)
        y += length_max
        y -= overlap

    for x_start in x_positions:
        x_start_use = x_start + delta_width
        x_end = x_start + roof.useful_width
        for y_start in y_positions:
            y_end = y_start + length_max

            sheet_polygon = Polygon([
                (x_start_use, y_start),
                (x_end, y_start),
                (x_end, y_end),
                (x_start_use, y_end)
            ])

            if not prepared_figure.intersects(sheet_polygon):
                continue

            intersection = figure.intersection(sheet_polygon)
            if intersection.is_empty:
                continue

            coords = list(intersection.bounds)
            if coords[1] == 0:
                coords[1] -= overhang
            for y_level in y_levels:
                if coords[1] >= y_level and coords[1] < y_level + overlap:
                    coords[1] = y_level
                    break
            sheet_height = coords[3] - coords[1]
            sheet_width = coords[2] - coords[0]

            if sheet_height < overlap or sheet_width < delta_width:
                continue
            elif sheet_height < length_min:
                coords[3] = coords[1] + length_min
            elif sizes:
                for size in sizes:
                    if sheet_height > size[0] and sheet_height < size[1]:
                        coords[3] = coords[1] + size[1]
                        break
            length = round(coords[3] - coords[1], 2)
            sheets.append([
                round(x_start, 2),
                round(coords[1], 2),
                length,
                round(overall_width*length, 2),
                round(roof.useful_width*length, 2)
            ])

    return sheets


def sheet_offset(x_start, y_start, length, figure, roof, y_levels, overhang):
    overall_width = roof.overall_width
    delta_width = roof.overall_width - roof.useful_width
    length_max = roof.max_length
    overlap = roof.overlap
    length_min = roof.min_length
    sizes = roof.imp_sizes
    prepared_figure = prep(figure)
    x_start_use = x_start + delta_width
    x_end = x_start + roof.useful_width
    y_end = y_start + length_max
    sheet_polygon = Polygon([
        (x_start_use, y_start),
        (x_end, y_start),
        (x_end, y_end),
        (x_start_use, y_end)
    ])
    if not overhang:
        overhang = 0
    if not prepared_figure.intersects(sheet_polygon):
        length = -1
    intersection = figure.intersection(sheet_polygon)
    if intersection.is_empty:
        length = -1
    coords = list(intersection.bounds)
    if coords[1] == 0:
        coords[1] -= overhang
    for y_level in y_levels:
        if coords[1] >= y_level and coords[1] < y_level + overlap:
            coords[1] = y_level
            break
    sheet_height = coords[3] - coords[1]
    sheet_width = coords[2] - coords[0]
    if sheet_height < overlap or sheet_width < delta_width:
        length = -1
    elif sheet_height < length_min:
        coords[3] = coords[1] + length_min
    elif sizes:
        for size in sizes:
            if sheet_height > size[0] and sheet_height < size[1]:
                coords[3] = coords[1] + size[1]
                break
    if length == -1:
        length = 0
    else:
        length = round(coords[3] - coords[1], 2)
    return ([
        round(x_start, 2),
        round(coords[1], 2),
        length,
        round(overall_width*length, 2),
        round(roof.useful_width*length, 2)
            ])


def get_next_name(existing_names: List[str]) -> str:
    alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

    def generate_names():
        for length in range(1, 3):
            for letters in product(alphabet, repeat=length):
                yield ''.join(letters)

    name_generator = generate_names()

    for name in name_generator:
        if name not in existing_names:
            return name


def get_next_length_name(existing_names: List[str]) -> str:

    def generate_names():
        for i in range(1, 101):
            yield 'L'+str(i)

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


def create_hole(figure, points):
    hole_polygon = Polygon(points)
    return figure.difference(hole_polygon)


def create_figure(lines, cutouts):
    points = {}
    for line in lines:
        if line.start_id not in points:
            points[line.start_id] = (line.start.x, line.start.y)
        if line.end_id not in points:
            points[line.end_id] = (line.end.x, line.end.y)
    builder = GraphBuilder(lines, points)
    cycles = builder.find_all_cycles()
    figure = builder._build_polygon(cycles[0])
    if cutouts:
        for cutout in cutouts:
            figure = create_hole(figure, cutout)
    return figure


def generate_slopes_length(lines: List[LinesSlope], points: List[PointSlope]):
    dif_y = []
    points_on_y: Dict[float, List[UUID4]] = {}
    lines_on_y: Dict[float, List[UUID4]] = {}
    slope_lines = []
    for point in points:
        if point.y not in dif_y:
            dif_y.append(point.y)
            points_on_y[point.y] = []
            lines_on_y[point.y] = []
        points_on_y[point.y].append(point.id)
    for line in lines:
        if line.start.y == line.end.y:
            lines_on_y[line.start.y].append(line.id)
            if line.start_id in points_on_y[line.start.y]:
                points_on_y[line.start.y].remove(line.start_id)
            if line.end_id in points_on_y[line.start.y]:
                points_on_y[line.start.y].remove(line.end_id)
    if len(lines_on_y[0]) == 0:
        point_o = points_on_y[0][0]
        k = 0
    else:
        line_o = lines_on_y[0][0]
        k = 1
    dif_y.remove(0)
    for y in dif_y:
        if k == 1:
            if len(points_on_y[y]) == 1:
                slope_lines.append([1, line_o, points_on_y[y][0]])
            else:
                for line in lines_on_y[y]:
                    slope_lines.append([0, line_o, line])
        else:
            if len(points_on_y[y]) == 1:
                slope_lines.append([2, point_o, points_on_y[y][0]])
            else:
                for line in lines_on_y[y]:
                    slope_lines.append([1, line, point_o])
    for line in lines:
        if line.start.x == line.end.x:
            for s_line in slope_lines:
                c = 0
                if s_line[0] == 2:
                    if line.start_id == s_line[1] or line.start_id == s_line[2]:
                        c += 1
                    if line.end_id == s_line[1] or line.end_id == s_line[2]:
                         c += 1
                elif s_line[0] == 1:
                    n_line = None
                    for l in lines:
                        if s_line[1] == l.id:
                            n_line = l
                    if line.start_id == s_line[2]:
                        c += 1
                        if line.end_id == n_line.start_id or line.end_id == n_line.end_id:
                            c += 1
                    elif line.end_id == s_line[2]:
                        c += 1
                        if line.start_id == n_line.start_id or line.start_id == n_line.end_id:
                            c += 1
                else:
                    line_1 = None
                    line_2 = None
                    for l in lines:
                        if s_line[1] == l.id:
                            line_1 = l
                        if s_line[2] == l.id:
                            line_2 = l
                    if line.end_id == line_1.start_id or line.end_id == line_1.end_id:
                        c += 1
                        if line.start_id == line_2.start_id or line.start_id == line_2.end_id:
                            c += 1
                    elif line.start_id == line_1.start_id or line.start_id == line_1.end_id:
                        c += 1
                        if line.end_id == line_2.start_id or line.end_id == line_2.end_id:
                            c += 1
                if c == 2:
                    slope_lines.remove(s_line)
                    break
    return slope_lines


def calculate_count_accessory(length: float, accessory: AccessoriesBD) -> int:
    length_acc = accessory.length
    overlap = accessory.overlap
    delit = length_acc - overlap
    modulo = accessory.modulo
    count = length / delit
    rounded_count = math.ceil(count)
    if modulo:
        if count - int(count) > modulo:
            rounded_count += 1

    return rounded_count
