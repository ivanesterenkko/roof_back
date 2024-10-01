from collections import defaultdict
from shapely.geometry import Polygon

from app.projects.schemas import PointData

class SlopeExtractor:
    def __init__(self, lines):
        self.lines = lines
        self.graph = defaultdict(list)
        self.line_set = set()

    def build_graph(self):
        """Построение графа точек, соединённых линиями."""
        for line in self.lines:
            self.graph[line.start].append(line.end)
            self.graph[line.end].append(line.start)
            self.line_set.add(tuple(sorted((line.start, line.end))))

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
            cycle_coordinates = [(point.x, point.y) for point in cycle]
            polygon = Polygon(cycle_coordinates)
            is_unique = True
            for other_cycle in unique_cycles:
                other_coordinates = [(point.x, point.y) for point in other_cycle]
                other_polygon = Polygon(other_coordinates)
                if polygon.contains(other_polygon) or polygon.equals(other_polygon):
                    is_unique = False
                    break
                elif other_polygon.contains(polygon):
                    unique_cycles.remove(other_cycle)
            if is_unique:
                unique_cycles.append(cycle)
        return unique_cycles

    def is_valid_cycle(self, cycle):
        """Проверка, что все рёбра цикла присутствуют в исходных линиях."""
        for i in range(len(cycle)):
            p1 = cycle[i]
            p2 = cycle[(i + 1) % len(cycle)]
            if tuple(sorted((p1, p2))) not in self.line_set:
                return False
        return True
    
    def extract_slopes(self):
        """Извлечение всех фигур из точек и линий."""
        cycles = self.find_cycles()
        return self.filter_cycles(cycles)

async def create_roofs(figure):
    """Создание листов для покрытия полигона."""
    sheets = []
    width_full = 0.9  # Ширина листа
    overlap_horizontal = 0.06  # Горизонтальный перехлест
    length_max = 2.0  # Максимальная длина листа
    length_min = 0.5  # Минимальная длина листа
    overlap_vertical = 0.15  # Вертикальный перехлест

    x_min, y_min, x_max, y_max = figure.bounds
    x = x_min

    while x < x_max:
        x_ls = x
        x += width_full
        y = y_min

        while y < y_max:
            y_ls = y
            y += length_max
            sheet = Polygon([(x_ls, y_ls), (x, y_ls), (x, y), (x_ls, y)])
            intersection = figure.intersection(sheet)

            if not intersection.is_empty:
                coords = list(intersection.bounds)
                sheet_height = coords[3] - coords[1]
                sheet_width = coords[2] - coords[0]

                if sheet_height < overlap_vertical or sheet_width < overlap_horizontal:
                    continue
                elif sheet_height < length_min:
                    coords[3] = coords[1] + length_min
                
                sheets.append([
    PointData(x=round(x_ls, 2), y=round(coords[1], 2)), 
    PointData(x=round(x, 2), y=round(coords[1], 2)), 
    PointData(x=round(x, 2), y=round(coords[3], 2)), 
    PointData(x=round(x_ls, 2), y=round(coords[3], 2))
])
            if y + length_min - overlap_vertical < y_max:
                y -= overlap_vertical

        x -= overlap_horizontal

    return sheets

def create_hole(figure, hole_points):
    coordinates = [(point.x, point.y) for point in hole_points]
    figure2 = Polygon(coordinates)
    return figure.difference(figure2)