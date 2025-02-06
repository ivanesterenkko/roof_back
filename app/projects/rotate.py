import math
from typing import List, Dict
from shapely.geometry import LineString, Point as ShapelyPoint
from shapely.affinity import rotate, translate, scale


def line_angle_with_x(line: LineString) -> float:
    x1, y1 = line.coords[0]
    x2, y2 = line.coords[-1]
    dx = x2 - x1
    dy = y2 - y1
    return math.degrees(math.atan2(dy, dx))


def move_geometry_to_point(geom, point: ShapelyPoint):
    return translate(geom, xoff=-point.x, yoff=-point.y)


def up_line(line):
    return LineString([(x, -y) for x, y in line.coords])


def right_line(line):
    return LineString([(-x, y) for x, y in line.coords])


def rotate_geometry(geom, angle_degrees: float):
    return rotate(geom, angle_degrees, origin=(0, 0))


def find_intersection(line1: LineString, line2: LineString):
    return line1.intersection(line2)


def maybe_flip_in_first_quadrant(rotated_lines: List[LineString]) -> List[LineString]:
    if not rotated_lines:
        return rotated_lines
    coords_all = []
    for ln in rotated_lines:
        coords_all.extend(ln.coords)
    avg_x = sum(pt[0] for pt in coords_all) / len(coords_all)
    avg_y = sum(pt[1] for pt in coords_all) / len(coords_all)
    flip_x = (avg_x < 0)
    flip_y = (avg_y < 0)
    if flip_x or flip_y:
        sx = -1 if flip_x else 1
        sy = -1 if flip_y else 1
        flipped = [scale(ln, xfact=sx, yfact=sy, origin=(0, 0)) for ln in rotated_lines]
        return flipped
    return rotated_lines


def transform_roof(lines_dict: Dict[str, List[LineString]]) -> Dict[str, List[LineString]]:
    eaves = lines_dict.get('карниз', [])
    gables = lines_dict.get('фронтон', [])
    valleys = lines_dict.get('ендова', [])
    ridges = lines_dict.get('конёк', [])
    dop_lines = lines_dict.get('примыкание', [])
    all_lines = eaves + gables + valleys + ridges + dop_lines
    x_max = 0
    y_max = 0
    for line in all_lines:
        if line.coords[0][0] > x_max:
            x_max = line.coords[0][0]
        if line.coords[1][0] > x_max:
            x_max = line.coords[1][0]
        if line.coords[0][1] > y_max:
            y_max = line.coords[0][1]
        if line.coords[1][1] > y_max:
            y_max = line.coords[1][1]
    result = {'карниз': [], 'фронтон': [], 'ендова': [], 'конёк': [], 'примыкание': []}
    if eaves:
        main_eave = None
        for eave in eaves:
            if eave.coords[0][0] == eave.coords[1][0]:
                main_eave = eave
                angle = 90
            elif eave.coords[0][1] == eave.coords[1][1]:
                main_eave = eave
                angle = 0
        if main_eave.coords[0][0] == main_eave.coords[1][0]:
            if main_eave.coords[0][0] == x_max:
                angle = -90
                if main_eave.coords[0][1] > main_eave.coords[1][1]:
                    anchor_x, anchor_y = main_eave.coords[0]
                else:
                    anchor_x, anchor_y = main_eave.coords[1]
            else:
                angle = 90
                if main_eave.coords[0][1] > main_eave.coords[1][1]:
                    anchor_x, anchor_y = main_eave.coords[1]
                else:
                    anchor_x, anchor_y = main_eave.coords[0]
        else:
            if main_eave.coords[0][1] == y_max:
                if main_eave.coords[0][0] < main_eave.coords[1][0]:
                    anchor_x, anchor_y = main_eave.coords[0]
                else:
                    anchor_x, anchor_y = main_eave.coords[1]
            else:
                if main_eave.coords[0][0] < main_eave.coords[1][0]:
                    anchor_x, anchor_y = main_eave.coords[1]
                else:
                    anchor_x, anchor_y = main_eave.coords[0]
        high = 1
        if angle == 0:
            for line in all_lines:
                if anchor_y > line.coords[0][1] or anchor_y > line.coords[1][1]:
                    angle = 180
        anchor_point = ShapelyPoint(anchor_x, anchor_y)
        moved_lines = [move_geometry_to_point(ln, anchor_point) for ln in all_lines]
        process_lines = moved_lines
        if angle == 0:
            rotated_lines = process_lines
        else:
            rotated_lines = [rotate_geometry(ml, angle) for ml in process_lines]
        rotated_lines = [right_line(ml) for ml in rotated_lines]
        idx = 0
        min_x = 10**9
        min_y = 10**9
        for line in rotated_lines:
            if line.coords[0][0] < min_x:
                min_x = line.coords[0][0]
            if line.coords[1][0] < min_x:
                min_x = line.coords[1][0]
            if line.coords[0][1] < min_y:
                min_y = line.coords[0][1]
            if line.coords[1][1] < min_y:
                min_y = line.coords[1][1]
        min_point = ShapelyPoint(min_x, min_y)
        rotated_lines = [move_geometry_to_point(ln, min_point) for ln in rotated_lines]
        for t in ('карниз', 'фронтон', 'ендова', 'конёк', 'примыкание'):
            n = len(lines_dict.get(t, []))
            result[t] = rotated_lines[idx: idx + n]
            idx += n
        return result
    elif gables and valleys:
        target_list = gables
        main_line = target_list[0]
        for line in valleys:
            if line.coords[0][0] == main_line.coords[0][0] and line.coords[0][1] == main_line.coords[0][1]:
                anchor_x, anchor_y = main_line.coords[0]
            if line.coords[1][0] == main_line.coords[0][0] and line.coords[1][1] == main_line.coords[0][1]:
                anchor_x, anchor_y = main_line.coords[0]
            if line.coords[0][0] == main_line.coords[1][0] and line.coords[0][1] == main_line.coords[1][1]:
                anchor_x, anchor_y = main_line.coords[1]
            if line.coords[1][0] == main_line.coords[1][0] and line.coords[1][1] == main_line.coords[1][1]:
                anchor_x, anchor_y = main_line.coords[1]
        if main_line.coords[0][0] == main_line.coords[1][0]:
                angle = 90
        elif main_line.coords[0][1] == main_line.coords[1][1]:
            angle = 0
        high = 1
        right = 1
        for line in all_lines:
            if anchor_x > line.coords[0][0] or anchor_x > line.coords[1][0]:
                right = 0
            if anchor_y > line.coords[0][1] or anchor_y > line.coords[1][1]:
                high = 0
        anchor_point = ShapelyPoint(anchor_x, anchor_y)
        moved_lines = [move_geometry_to_point(ln, anchor_point) for ln in all_lines]
        process_lines = moved_lines
        if high == 0:
            process_lines = [up_line(ml) for ml in process_lines]
        if right == 0:
            process_lines = [right_line(ml) for ml in process_lines]
        if angle == 90:
            rotated_lines = process_lines
        else:
            rotated_lines = [rotate_geometry(ml, 90) for ml in process_lines]
        idx = 0
        min_x = 10**9
        min_y = 10**9
        for line in rotated_lines:
            if line.coords[0][0] < min_x:
                min_x = line.coords[0][0]
            if line.coords[1][0] < min_x:
                min_x = line.coords[1][0]
            if line.coords[0][1] < min_y:
                min_y = line.coords[0][1]
            if line.coords[1][1] < min_y:
                min_y = line.coords[1][1]
        if min_x < 0:
            min_point = ShapelyPoint(min_x, 0)
            rotated_lines = [move_geometry_to_point(ln, min_point) for ln in rotated_lines]
        if min_y < 0:
            min_point = ShapelyPoint(0, min_y)
            rotated_lines = [move_geometry_to_point(ln, min_point) for ln in rotated_lines]
        for t in ('карниз', 'фронтон', 'ендова', 'конёк', 'примыкание'):
            n = len(lines_dict.get(t, []))
            result[t] = rotated_lines[idx: idx + n]
            idx += n
        return result
    else:
        for ridge in ridges:
            if ridge.coords[0][0] == ridge.coords[1][0]:
                main_ridge = ridge
                angle = 90
            elif ridge.coords[0][1] == ridge.coords[1][1]:
                main_ridge = ridge
                angle = 0
        if main_ridge.coords[0][0] == main_ridge.coords[1][0]:
            if main_ridge.coords[0][1] < main_ridge.coords[1][1]:
                anchor_x, anchor_y = main_ridge.coords[0]
            else:
                anchor_x, anchor_y = main_ridge.coords[1]
        else:
            if main_ridge.coords[0][0] > main_ridge.coords[1][0]:
                anchor_x, anchor_y = main_ridge.coords[0]
            else:
                anchor_x, anchor_y = main_ridge.coords[1]
        high = 0
        right = 0
        for line in all_lines:
            if anchor_x < line.coords[0][0] or anchor_x < line.coords[1][0]:
                right = 0
            if anchor_y < line.coords[0][1] or anchor_y < line.coords[1][1]:
                high = 0
        anchor_point = ShapelyPoint(anchor_x, anchor_y)
        moved_lines = [move_geometry_to_point(ln, anchor_point) for ln in all_lines]
        process_lines = moved_lines
        if high == 1:
            process_lines = [up_line(ml) for ml in process_lines]
        if right == 1:
            process_lines = [right_line(ml) for ml in process_lines]
        if angle == 0:
            rotated_lines = process_lines
        else:
            rotated_lines = [rotate_geometry(ml, angle) for ml in process_lines]
        idx = 0
        min_x = 10**9
        min_y = 10**9
        for line in rotated_lines:
            if line.coords[0][0] < min_x:
                min_x = line.coords[0][0]
            if line.coords[1][0] < min_x:
                min_x = line.coords[1][0]
            if line.coords[0][1] < min_y:
                min_y = line.coords[0][1]
            if line.coords[1][1] < min_y:
                min_y = line.coords[1][1]
        if min_x < 0:
            min_point = ShapelyPoint(min_x, 0)
            rotated_lines = [move_geometry_to_point(ln, min_point) for ln in rotated_lines]
        if min_y < 0:
            min_point = ShapelyPoint(0, min_y)
            rotated_lines = [move_geometry_to_point(ln, min_point) for ln in rotated_lines]
        for t in ('карниз', 'фронтон', 'ендова', 'конёк', 'примыкание'):
            n = len(lines_dict.get(t, []))
            result[t] = rotated_lines[idx: idx + n]
            idx += n
        return result


def rotate_roof_lines_in_memory(lines_list):
    lines_dict = {'карниз': [], 'фронтон': [], 'ендова': [], 'конёк': [], 'примыкание': []}
    lines_map = {'карниз': [], 'фронтон': [], 'ендова': [], 'конёк': [], 'примыкание': []}
    for l in lines_list:
        ls = LineString([(l.start.x, l.start.y), (l.end.x, l.end.y)])
        if l.type in lines_dict:
            lines_dict[l.type].append(ls)
            lines_map[l.type].append(l)
    transformed_lines_dict = transform_roof(lines_dict)
    for t, new_lines in transformed_lines_dict.items():
        old_objs = lines_map[t]
        for geom, old_line in zip(new_lines, old_objs):
            (x1, y1), (x2, y2) = geom.coords
            old_line.start.x = x1
            old_line.start.y = y1
            old_line.end.x = x2
            old_line.end.y = y2


def rotate_slope(lines):

    rotate_roof_lines_in_memory(lines)
    return lines
