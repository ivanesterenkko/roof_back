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


def rotate_geometry(geom, angle_degrees: float):
    return rotate(geom, -angle_degrees, origin=(0, 0))


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
    eaves   = lines_dict.get('карниз', [])
    gables  = lines_dict.get('фронтон', [])
    valleys = lines_dict.get('ендова', [])
    ridges  = lines_dict.get('конёк', [])
    all_lines = eaves + gables + valleys + ridges
    result = {'карниз': [], 'фронтон': [], 'ендова': [], 'конёк': []}
    if eaves:
        main_eave = eaves[0]
        angle_eave = line_angle_with_x(main_eave)
        anchor_x, anchor_y = main_eave.coords[0]
        anchor_point = ShapelyPoint(anchor_x, anchor_y)
        moved_lines = [move_geometry_to_point(ln, anchor_point) for ln in all_lines]
        rotated_lines = [rotate_geometry(ml, angle_eave) for ml in moved_lines]
        rotated_lines = maybe_flip_in_first_quadrant(rotated_lines)
        idx = 0
        for t in ('карниз', 'фронтон', 'ендова', 'конёк'):
            n = len(lines_dict.get(t, []))
            result[t] = rotated_lines[idx: idx + n]
            idx += n
        return result
    elif gables or valleys:
        target_list = gables if gables else valleys
        main_line = target_list[0]
        intersection_point = None
        for ln in (gables + valleys + ridges + eaves):
            if ln is main_line:
                continue
            inter = find_intersection(main_line, ln)
            if not inter.is_empty:
                if inter.geom_type == 'Point':
                    intersection_point = inter
                    break
                elif inter.geom_type == 'MultiPoint':
                    intersection_point = list(inter)[0]
                    break
        if intersection_point is None:
            intersection_point = ShapelyPoint(*main_line.coords[0])
        moved_lines = [move_geometry_to_point(ln, intersection_point) for ln in all_lines]
        angle_main = line_angle_with_x(move_geometry_to_point(main_line, intersection_point))
        rotate_angle = 90 - angle_main
        rotated_lines = [rotate_geometry(ml, rotate_angle) for ml in moved_lines]
        rotated_lines = maybe_flip_in_first_quadrant(rotated_lines)
        idx = 0
        for t in ('карниз','фронтон','ендова','конёк'):
            n = len(lines_dict.get(t, []))
            result[t] = rotated_lines[idx: idx + n]
            idx += n
        return result
    elif ridges or valleys:
        main_ridge = ridges[0] if ridges else valleys[0]
        intersection_point = None
        for ln in (valleys + ridges):
            if ln is main_ridge:
                continue
            inter = find_intersection(main_ridge, ln)
            if not inter.is_empty:
                if inter.geom_type == 'Point':
                    intersection_point = inter
                    break
                elif inter.geom_type == 'MultiPoint':
                    intersection_point = list(inter)[0]
                    break
        if intersection_point is None:
            intersection_point = ShapelyPoint(*main_ridge.coords[0])
        moved_lines = [move_geometry_to_point(ln, intersection_point) for ln in all_lines]
        angle_ridge = line_angle_with_x(move_geometry_to_point(main_ridge, intersection_point))
        rotated_lines = [rotate_geometry(ml, angle_ridge) for ml in moved_lines]
        rotated_lines = maybe_flip_in_first_quadrant(rotated_lines)
        idx = 0
        for t in ('карниз','фронтон','ендова','конёк'):
            n = len(lines_dict.get(t, []))
            result[t] = rotated_lines[idx: idx + n]
            idx += n
        return result
    else:
        return lines_dict


def rotate_roof_lines_in_memory(lines_list):
    lines_dict = {'карниз': [], 'фронтон': [], 'ендова': [], 'конёк': []}
    lines_map = {'карниз': [], 'фронтон': [], 'ендова': [], 'конёк': []}
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
