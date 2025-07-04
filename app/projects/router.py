import copy
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List
from pydantic import UUID4
from collections import Counter
from shapely import Point
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio


# Импорт схем, исключений и утилит
from app.base.dao import Accessory_baseDAO, RoofsDAO
from app.base.schemas import (
    AccessoryBDResponse, RoofResponse
)
from app.exceptions import (
    AccessoryBaseNotFound, AccessoryNotFound, CutoutNotFound, MaterialAlreadyExist, MaterialNotFound, ProjectAlreadyExists, ProjectNotFound, ProjectStepLimit,
    RoofNotFound, SheetNotFound, SheetTooShortNotFound, SlopeNotFound
)
from app.projects.draw import create_excel
from app.projects.models import DeletedSheets
from app.projects.rotate import rotate_slope
from app.projects.schemas import (
    AboutResponse, AccessoriesRequest, AccessoriesResponse, AccessoriesUpdateRequest, ChangeSheetRequest,
    CutoutResponse, DeletedSheetResponse, EstimateRequest, EstimateResponse, LengthSlopeResponse,
    LineRequest, LineResponse, LineSlopeResponse, MaterialEstimateResponse, MaterialRequest,
    NodeRequest, PointCutoutResponse, PointData, PointSlopeResponse,
    ProjectRequest, ProjectResponse, RoofEstimateResponse,
    ScrewsEstimateResponse, SheetResponse,
    SlopeEstimateResponse, SlopeResponse,
    SlopeSizesRequest
)
from app.projects.dao import (
    AccessoriesDAO, CutoutsDAO, DeletedSheetsDAO, LengthSlopeDAO, LinesDAO, LinesSlopeDAO,
    MaterialsDAO, PointsCutoutsDAO, PointsDAO, PointsSlopeDAO,
    ProjectsDAO, SheetsDAO, SlopesDAO
)
from app.projects.slope import (
    calculate_count_accessory, create_figure, create_sheets, find_slope, generate_slopes_length,
    get_next_length_name, get_next_name, get_next_sheet_name, get_next_slope_name, sheet_offset
)
from app.users.dependencies import get_current_user
from app.users.models import Users
from app.db import get_session  # Зависимость для получения AsyncSession

router = APIRouter(prefix="/roofs", tags=["Roofs"])


@router.get("/projects", description="Get list of projects")
async def get_projects(
    user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> List[AboutResponse]:
    """
    Возвращает список проектов для текущего пользователя.
    """
    projects = await ProjectsDAO.find_all(session, user_id=user.id)
    projects_response = []
    for project in projects:
        roof = await RoofsDAO.find_by_id(session, model_id=project.roof_id)
        projects_response.append(
            AboutResponse(
                id=project.id,
                name=project.name,
                address=project.address,
                step=project.step,
                overhang=project.overhang,
                datetime_created=project.datetime_created,
                roof=RoofResponse(
                    id=roof.id,
                    name=roof.name,
                    type=roof.type,
                    overall_width=roof.overall_width,
                    useful_width=roof.useful_width,
                    overlap=roof.overlap,
                    len_wave=roof.len_wave,
                    max_length=roof.max_length,
                    min_length=roof.min_length,
                    imp_sizes=roof.imp_sizes
                )
            )
        )
    return projects_response


@router.get("/projects/{project_id}", description="Get info about project")
async def get_project(
    project_id: UUID4,
    user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> ProjectResponse:
    """
    Возвращает подробную информацию по проекту.
    """
    project = await ProjectsDAO.find_by_id(session, model_id=project_id)
    if not project:
        raise ProjectNotFound
    roof = await RoofsDAO.find_by_id(session, model_id=project.roof_id)
    if not roof:
        raise RoofNotFound

    lines = await LinesDAO.find_all(session, project_id=project_id)
    lines_response = [
        LineResponse(
            id=line.id,
            is_perimeter=line.is_perimeter,
            type=line.type,
            name=line.name,
            start=PointData(x=line.start.x, y=line.start.y),
            end=PointData(x=line.end.x, y=line.end.y),
            length=line.length
        )
        for line in lines
    ] if lines else None

    slopes = await SlopesDAO.find_all(session, project_id=project_id)
    if slopes:
        slope_response = []
        for slope_obj in slopes:
            points_slope = await PointsSlopeDAO.find_all(session, slope_id=slope_obj.id)
            points_response = [
                PointSlopeResponse(id=point.id, x=point.x, y=point.y)
                for point in points_slope
            ]
            lines_slope = await LinesSlopeDAO.find_all(session, slope_id=slope_obj.id)
            lines_slope_response = [
                LineSlopeResponse(
                    id=line_slope.id,
                    parent_id=line_slope.parent_id,
                    name=line_slope.name,
                    number=line_slope.number,
                    start_id=line_slope.start_id,
                    start=PointData(x=line_slope.start.x, y=line_slope.start.y),
                    end_id=line_slope.end_id,
                    end=PointData(x=line_slope.end.x, y=line_slope.end.y),
                    length=line_slope.length
                )
                for line_slope in lines_slope
            ]
            lines_length = await LengthSlopeDAO.find_all(session, slope_id=slope_obj.id)
            length_slope_response = []
            for length_line in lines_length:
                if length_line.type == 0:
                    line_1 = await LinesDAO.find_by_id(session, model_id=length_line.line_slope_1.parent_id)
                    line_2 = await LinesDAO.find_by_id(session, model_id=length_line.line_slope_2.parent_id)
                    if line_1.start.x == line_1.end.x:
                        y_ar = abs(line_2.start.y - line_2.end.y) / 2
                        y_ar = line_2.end.y + y_ar if line_2.start.y > line_2.end.y else line_2.start.y + y_ar
                        length_slope_response.append(
                            LengthSlopeResponse(
                                id=length_line.id,
                                name=length_line.name,
                                start=PointData(x=line_2.start.x, y=y_ar),
                                end=PointData(x=line_1.start.x, y=y_ar),
                                type=length_line.type,
                                point_1_id=length_line.point_1_id,
                                point_2_id=length_line.point_2_id,
                                line_slope_1_id=length_line.line_slope_1_id,
                                line_slope_2_id=length_line.line_slope_2_id,
                                length=length_line.length
                            )
                        )
                    else:
                        x_ar = abs(line_2.start.x - line_2.end.x) / 2
                        x_ar = line_2.end.x + x_ar if line_2.start.x > line_2.end.x else line_2.start.x + x_ar
                        length_slope_response.append(
                            LengthSlopeResponse(
                                id=length_line.id,
                                name=length_line.name,
                                start=PointData(x=x_ar, y=line_2.start.y),
                                end=PointData(x=x_ar, y=line_1.start.y),
                                type=length_line.type,
                                point_1_id=length_line.point_1_id,
                                point_2_id=length_line.point_2_id,
                                line_slope_1_id=length_line.line_slope_1_id,
                                line_slope_2_id=length_line.line_slope_2_id,
                                length=length_line.length
                            )
                        )
                elif length_line.type == 1:
                    line = await LinesDAO.find_by_id(session, model_id=length_line.line_slope_1.parent_id)
                    point = await PointsDAO.find_by_id(session, model_id=length_line.point_1.parent_id)
                    if line.start.x == line.end.x:
                        length_slope_response.append(
                            LengthSlopeResponse(
                                id=length_line.id,
                                name=length_line.name,
                                start=PointData(x=line.start.x, y=point.y),
                                end=PointData(x=point.x, y=point.y),
                                type=length_line.type,
                                point_1_id=length_line.point_1_id,
                                point_2_id=length_line.point_2_id,
                                line_slope_1_id=length_line.line_slope_1_id,
                                line_slope_2_id=length_line.line_slope_2_id,
                                length=length_line.length
                            )
                        )
                    else:
                        length_slope_response.append(
                            LengthSlopeResponse(
                                id=length_line.id,
                                name=length_line.name,
                                start=PointData(x=point.x, y=line.start.y),
                                end=PointData(x=point.x, y=point.y),
                                type=length_line.type,
                                point_1_id=length_line.point_1_id,
                                point_2_id=length_line.point_2_id,
                                line_slope_1_id=length_line.line_slope_1_id,
                                line_slope_2_id=length_line.line_slope_2_id,
                                length=length_line.length
                            )
                        )
                else:
                    point_1 = await PointsDAO.find_by_id(session, model_id=length_line.point_1.parent_id)
                    point_2 = await PointsDAO.find_by_id(session, model_id=length_line.point_2.parent_id)
                    length_slope_response.append(
                        LengthSlopeResponse(
                            id=length_line.id,
                            name=length_line.name,
                            start=PointData(x=point_1.x, y=point_1.y),
                            end=PointData(x=point_2.x, y=point_2.y),
                            type=length_line.type,
                            point_1_id=length_line.point_1_id,
                            point_2_id=length_line.point_2_id,
                            line_slope_1_id=length_line.line_slope_1_id,
                            line_slope_2_id=length_line.line_slope_2_id,
                            length=length_line.length
                        )
                    )
            cutouts = await CutoutsDAO.find_all(session, slope_id=slope_obj.id)
            if cutouts:
                cutouts_response = []
                for cutout in cutouts:
                    points_cutout = await PointsCutoutsDAO.find_all(session, cutout_id=cutout.id)
                    points_cutout_response = [
                        PointCutoutResponse(id=pt.id, x=pt.x, y=pt.y, number=pt.number)
                        for pt in points_cutout
                    ]
                    cutouts_response.append(
                        CutoutResponse(id=cutout.id, points=points_cutout_response)
                    )
            else:
                cutouts_response = None
            sheets = await SheetsDAO.find_all(session, slope_id=slope_obj.id)
            sheets_response = [
                SheetResponse(
                    id=sheet.id,
                    x_start=sheet.x_start,
                    y_start=sheet.y_start,
                    length=sheet.length,
                    area_overall=sheet.area_overall,
                    area_usefull=sheet.area_usefull,
                    is_deleted=sheet.is_deleted
                ) for sheet in sheets
            ] if sheets else None
            slope_response.append(
                SlopeResponse(
                    id=slope_obj.id,
                    name=slope_obj.name,
                    area=slope_obj.area,
                    is_left=slope_obj.is_left,
                    points=points_response,
                    lines=lines_slope_response,
                    length_line=length_slope_response,
                    cutouts=cutouts_response,
                    sheets=sheets_response
                )
            )
    else:
        slope_response = None
    accessories = await AccessoriesDAO.find_all(session, project_id=project_id)
    if accessories:
        accessories_response = []
        for accessory in accessories:
            accessory_base = await Accessory_baseDAO.find_by_id(session, model_id=accessory.accessory_base_id)
            accessories_response.append(
                AccessoriesResponse(
                    id=accessory.id,
                    accessory_base=AccessoryBDResponse(
                        id=accessory_base.id,
                        name=accessory_base.name,
                        type=accessory_base.type,
                        parent_type=accessory_base.parent_type,
                        material=accessory_base.material,
                        length=accessory_base.length,
                        overlap=accessory_base.overlap,
                        price=accessory_base.price,
                        modulo=accessory_base.modulo
                    ),
                    lines_id=accessory.lines_id,
                    lines_length=accessory.lines_length,
                    quantity=accessory.quantity,
                    color=accessory.color
                )
            )
    else:
        accessories_response = None
    delete_sheets = await DeletedSheetsDAO.find_all(session, project_id=project_id)
    if delete_sheets:
        deleted_sheets_response = [
            DeletedSheetResponse(
                id=sheet.id,
                number=sheet.number,
                deleted_sheet_id=sheet.deleted_sheet_id,
                change_sheet_id=sheet.change_sheet_id
            ) for sheet in delete_sheets
        ]
    else:
        deleted_sheets_response = None
    return ProjectResponse(
        id=project.id,
        name=project.name,
        address=project.address,
        step=project.step,
        overhang=project.overhang,
        datetime_created=project.datetime_created,
        roof=RoofResponse(
            id=roof.id,
            name=roof.name,
            type=roof.type,
            overall_width=roof.overall_width,
            useful_width=roof.useful_width,
            overlap=roof.overlap,
            len_wave=roof.len_wave,
            max_length=roof.max_length,
            min_length=roof.min_length,
            imp_sizes=roof.imp_sizes
        ),
        lines=lines_response,
        slopes=slope_response,
        accessories=accessories_response,
        deleted_sheets=deleted_sheets_response
    )


@router.delete("/projects/{project_id}", description="Delete a roofing project")
async def delete_project(
    project_id: UUID4,
    user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> None:
    project = await ProjectsDAO.find_by_id(session, model_id=project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    await ProjectsDAO.delete_(session, model_id=project_id)


@router.post("/projects", description="Create a roofing project")
async def add_project(
    project: ProjectRequest,
    user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> dict:
    existing_project = await ProjectsDAO.find_one_or_none(session, name=project.name, user_id=user.id)
    if existing_project:
        raise ProjectAlreadyExists
    roof = await RoofsDAO.find_by_id(session, model_id=project.roof_id)
    if not roof:
        raise RoofNotFound
    project = await ProjectsDAO.add(
        session,
        name=project.name,
        address=project.address,
        roof_id=project.roof_id,
        user_id=user.id
    )
    return {"project_id": project.id}


@router.patch("/projects/{project_id}/step", description="Advance project step")
async def next_step(
    project_id: UUID4,
    user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> None:
    project = await ProjectsDAO.find_by_id(session, model_id=project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    if project.step + 1 > 8:
        raise ProjectStepLimit
    await ProjectsDAO.update_(session, model_id=project_id, step=project.step + 1)


@router.patch("/projects/{project_id}/overhang", description="Overhang")
async def create_overhang(
    project_id: UUID4,
    overhang: float,
    user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> None:
    project = await ProjectsDAO.find_by_id(session, model_id=project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    await ProjectsDAO.update_(session, model_id=project_id, overhang=overhang)
    slopes = await SlopesDAO.find_all(session, project_id=project.id)
    roof = await RoofsDAO.find_by_id(session, model_id=project.roof_id)
    if slopes:
        for slope in slopes:
            sheets = await SheetsDAO.find_all(session, slope_id=slope.id)
            if sheets:
                for sheet in sheets:
                    await SheetsDAO.delete_(session, model_id=sheet.id)
            cutouts_slope = await CutoutsDAO.find_all(session, slope_id=slope.id)
            lines = await LinesSlopeDAO.find_all(session, slope_id=slope.id)
            lines = sorted(lines, key=lambda line: line.number)
            cutouts = []
            for cutout in cutouts_slope:
                pts = await PointsCutoutsDAO.find_all(session, cutout_id=cutout.id)
                pts = sorted(pts, key=lambda p: p.number)
                cutout_coords = [(p.x, p.y) for p in pts]
                cutouts.append(cutout_coords)
            figure = create_figure(lines, cutouts)
            sheets = create_sheets(figure=figure, roof=roof, is_left=slope.is_left, overhang=project.overhang)
            for sh in sheets:
                await SheetsDAO.add(
                    session,
                    x_start=sh[0],
                    y_start=sh[1],
                    length=sh[2],
                    area_overall=sh[3],
                    area_usefull=sh[4],
                    slope_id=slope.id
                )



@router.patch("/projects/{project_id}/slopes/{slope_id}/direction", description="Change direction of sheets")
async def change_direction(
    project_id: UUID4,
    slope_id: UUID4,
    user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> None:
    project = await ProjectsDAO.find_by_id(session, model_id=project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    slope = await SlopesDAO.find_by_id(session, model_id=slope_id)
    if not slope or slope.project_id != project_id:
        raise SlopeNotFound
    await SlopesDAO.update_(session, model_id=slope_id, is_left=not(slope.is_left))
    sheets_old = await SheetsDAO.find_all(session, slope_id=slope.id)
    for sheet_old in sheets_old:
        await SheetsDAO.delete_(session, model_id=sheet_old.id)
    cutouts_slope = await CutoutsDAO.find_all(session, slope_id=slope_id)
    lines = await LinesSlopeDAO.find_all(session, slope_id=slope_id)
    lines = sorted(lines, key=lambda line: line.number)
    cutouts = []
    for cutout in cutouts_slope:
        pts = await PointsCutoutsDAO.find_all(session, cutout_id=cutout.id)
        pts = sorted(pts, key=lambda p: p.number)
        cutout_coords = [(p.x, p.y) for p in pts]
        cutouts.append(cutout_coords)
    figure = create_figure(lines, cutouts)
    area = figure.area
    await SlopesDAO.update_(session, model_id=slope_id, area=area)
    roof = await RoofsDAO.find_by_id(session, model_id=project.roof_id)
    sheets = create_sheets(figure=figure, roof=roof, is_left=slope.is_left, overhang=project.overhang)
    for sh in sheets:
        await SheetsDAO.add(
            session,
            x_start=sh[0],
            y_start=sh[1],
            length=sh[2],
            area_overall=sh[3],
            area_usefull=sh[4],
            slope_id=slope_id
        )


@router.post("/projects/{project_id}/add_lines", description="Add lines of sketch")
async def add_lines(
    project_id: UUID4,
    lines: List[LineRequest],
    user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> None:
    project = await ProjectsDAO.find_by_id(session, model_id=project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    existing_lines = await LinesDAO.find_all(session, project_id=project.id)
    existing_names = [line.name for line in existing_lines]
    existing_points: Dict[PointData, UUID4] = {}
    ex_points = await PointsDAO.find_all(session, project_id=project_id)
    for point in ex_points:
        pt = PointData(x=point.x, y=point.y)
        if pt not in existing_points:
            existing_points[pt] = point.id
    for line in lines:
        line_name = get_next_name(existing_names)
        if line.start in existing_points:
            start_id = existing_points[line.start]
        else:
            point = await PointsDAO.add(session, x=line.start.x, y=line.start.y, project_id=project_id)
            start_id = point.id
            existing_points[line.start] = start_id
        if line.end in existing_points:
            end_id = existing_points[line.end]
        else:
            point = await PointsDAO.add(session, x=line.end.x, y=line.end.y, project_id=project_id)
            end_id = point.id
            existing_points[line.end] = end_id
        await LinesDAO.add(session, project_id=project_id, name=line_name, is_perimeter=line.is_perimeter, start_id=start_id, end_id=end_id)
        existing_names.append(line_name)


@router.get("/projects/{project_id}/get_lines", description="Get lines")
async def get_lines(
    project_id: UUID4,
    user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> List[LineResponse]:
    project = await ProjectsDAO.find_by_id(session, model_id=project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    lines = await LinesDAO.find_all(session, project_id=project_id)
    return [
        LineResponse(
            id=line.id,
            is_perimeter=line.is_perimeter,
            type=line.type,
            name=line.name,
            start=PointData(x=line.start.x, y=line.start.y),
            end=PointData(x=line.end.x, y=line.end.y)
        ) for line in lines
    ]


@router.patch("/projects/{project_id}/lines/node_line", description="Add roof nodes")
async def add_node(
    project_id: UUID4,
    node_data: NodeRequest,
    user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> None:
    project = await ProjectsDAO.find_by_id(session, model_id=project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    for line_id in node_data.lines_id:
        await LinesDAO.update_(session, model_id=line_id, type=node_data.type)


@router.patch("/projects/{project_id}/slopes/{slope_id}/add_sizes")
async def add_sizes(
    project_id: UUID4,
    slope_id: UUID4,
    data: SlopeSizesRequest,
    user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> None:
    print(f"▶▶▶ add_sizes called: project={project_id}, slope={slope_id}")

    # Проверка прав
    project = await ProjectsDAO.find_by_id(session, model_id=project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    slope = await SlopesDAO.find_by_id(session, model_id=slope_id)
    if not slope or slope.project_id != project_id:
        raise SlopeNotFound
    print("▶▶▶ Permissions validated")

    # 1) Сбор входных длин
    lines_data = {ln.id: ln.length for ln in data.lines}
    lines_data_or = lines_data.copy()
    print(f"▶▶▶ Initial lines_data: {lines_data}")

    # 2) Обновление LengthSlope и начальные Y-сдвиги
    for length_line_d in data.length_line:
        length_id = length_line_d.id
        length = length_line_d.length
        print(f"▶ Updating LengthSlope {length_id} -> {length}")
        await LengthSlopeDAO.update_(session, model_id=length_id, length=length)
        ls = await LengthSlopeDAO.find_by_id(session, model_id=length_id)
        print(f"   type={ls.type}")
        if ls.type == 0:
            print(f"   vertical shift for line {ls.line_slope_2_id}")
            line = await LinesSlopeDAO.find_by_id(session, model_id=ls.line_slope_2_id)
            for pid in (line.start_id, line.end_id):
                await PointsSlopeDAO.update_(session, model_id=pid, y=length)
                p = await PointsSlopeDAO.find_by_id(session, model_id=pid)
                print(f"   {p.id}: {p.x} {p.y}")
        elif ls.type == 1:
            print(f"   diagonal shift for pt {ls.point_1_id}")
            await PointsSlopeDAO.update_(session, model_id=ls.point_1_id, y=length)
            p = await PointsSlopeDAO.find_by_id(session, model_id=ls.point_1_id)
            print(f"   {p.id}: {p.x} {p.y}")
        else:
            print(f"   horizontal shift for pt {ls.point_2_id}")
            await PointsSlopeDAO.update_(session, model_id=ls.point_2_id, y=length)
            p = await PointsSlopeDAO.find_by_id(session, model_id=ls.point_2_id)
            print(f"   {p.id}: {p.x} {p.y}")

    # 3) Загрузка текущих точек и линий
    points = await PointsSlopeDAO.find_all(session, slope_id=slope_id)
    print("▶ Loaded points:")
    for pt in points:
        print(f"   {pt.id}: {pt.x} {pt.y}")
    points_y = sorted(points, key=lambda p: p.y)
    points_x = sorted(points, key=lambda p: p.x)
    points_id = [p.id for p in points_x]
    points_y_id = [p.id for p in points_y]

    lines = await LinesSlopeDAO.find_all(session, slope_id=slope_id)
    print(f"▶ Loaded lines: {[l.id for l in lines]}")
    lines_on_point = {}
    lines_v_on_point = {}
    lines_g_on_point = {}
    lines_n_on_point = {}
    lines_n = 0
    for ln in lines:
        if ln.start.x == ln.end.x:
            lines_v_on_point.setdefault(ln.start_id, []).append(ln.id)
            lines_v_on_point.setdefault(ln.end_id, []).append(ln.id)
        elif ln.start.y == ln.end.y:
            lines_g_on_point.setdefault(ln.start_id, []).append(ln.id)
            lines_g_on_point.setdefault(ln.end_id, []).append(ln.id)
        else:
            lines_n_on_point.setdefault(ln.start_id, []).append(ln.id)
            lines_n_on_point.setdefault(ln.end_id, []).append(ln.id)
        lines_on_point.setdefault(ln.start_id, []).append(ln.id)
        lines_on_point.setdefault(ln.end_id, []).append(ln.id)
    print(f"▶ Classification: V={list(lines_v_on_point.keys())}, G={list(lines_g_on_point.keys())}, N={list(lines_n_on_point.keys())}")

    # 4) Вертикальные сдвиги
    for pt_id in points_y_id:
        print(f"▶ Vertical shift at point {pt_id}")
        for line_id in lines_v_on_point.get(pt_id, []):
            if line_id not in lines_data:
                continue
            length = lines_data.pop(line_id)
            line = await LinesSlopeDAO.find_by_id(session, model_id=line_id)
            base_y = min(line.start.y, line.end.y)
            point_n_id = line.end_id if line.start.y < line.end.y else line.start_id
            # Горизонтальные смежные
            if point_n_id in lines_g_on_point:
                line_g = await LinesSlopeDAO.find_by_id(session, model_id=lines_g_on_point[point_n_id][0])
                for pid in (line_g.start_id, line_g.end_id):
                    await PointsSlopeDAO.update_(session, model_id=pid, y=round(base_y + length, 3))
                    p = await PointsSlopeDAO.find_by_id(session, model_id=pid)
                    print(f"   G {p.id}: {p.x} {p.y}")
            # Диагональные смежные
            if point_n_id in lines_n_on_point:
                line_n = await LinesSlopeDAO.find_by_id(session, model_id=lines_n_on_point[point_n_id][0])
                target = line_n.end_id if line_n.end_id < line_n.start_id else line_n.start_id
                await PointsSlopeDAO.update_(session, model_id=target, y=round(base_y + length, 3))
                p = await PointsSlopeDAO.find_by_id(session, model_id=target)
                print(f"   N {p.id}: {p.x} {p.y}")

    # 5) Горизонтальные и диагональные сдвиги по X
    point_max = None
    for pt_id in points_id:
        print(f"▶ X-shift at point {pt_id}")
        for line_id in lines_on_point.get(pt_id, []):
            if line_id not in lines_data:
                continue
            length = lines_data.pop(line_id)
            ln = await LinesSlopeDAO.find_by_id(session, model_id=line_id)
            pt = await PointsSlopeDAO.find_by_id(session, model_id=pt_id)
            print(f"   Recalc {ln.id} angle={ln.angle} pivot {pt.id}: {pt.x} {pt.y}")
            if ln.angle == 2:
                # Горизонталь
                target_id = ln.end_id if pt.id == ln.start_id else ln.start_id
                await PointsSlopeDAO.update_(session, model_id=target_id, x=round(pt.x + length, 3))
                p = await PointsSlopeDAO.find_by_id(session, model_id=target_id)
                print(f"   H {p.id}: {p.x} {p.y}")
            elif ln.angle == 1:
                print(f"   Skip diagonal angle=1 for {ln.id}")
                continue
            else:
                # Диагональ
                lines_n += 1
                if pt.id == ln.start_id:
                    h = abs(pt.y - ln.end.y)
                    dx = (length**2 - h**2)**0.5
                    await PointsSlopeDAO.update_(session, model_id=ln.end_id, x=round(pt.x + dx, 3))
                    p = await PointsSlopeDAO.find_by_id(session, model_id=ln.end_id)
                if pt.id == ln.end_id:
                    h = abs(pt.y - ln.start.y)
                    dx = (length**2 - h**2)**0.5
                    await PointsSlopeDAO.update_(session, model_id=ln.start_id, x=round(pt.x + dx, 3))
                    p = await PointsSlopeDAO.find_by_id(session, model_id=ln.start_id)
                print(f"   D {p.id}: {p.x} {p.y}")
            if len(lines_v_on_point.get(p.id, [])) > 0:
                    line_v = await LinesSlopeDAO.find_by_id(session, model_id=lines_v_on_point[p.id][0])
                    if p.id == line_v.start_id:
                        await PointsSlopeDAO.update_(session, model_id=line_v.end_id, x=p.x)
                        p = await PointsSlopeDAO.find_by_id(session, model_id=line_v.end_id)
                    else:
                        await PointsSlopeDAO.update_(session, model_id=line_v.start_id, x=p.x)
                        p = await PointsSlopeDAO.find_by_id(session, model_id=line_v.start_id)
                    print(f"   V {p.id}: {p.x} {p.y}")
            if p is not None:
                point_max = p.id

    # 6) Логика конька (ridge)
    if point_max is not None:
        print(f"▶ Ridge logic at point_max={point_max}")
        for line_id in lines_on_point.get(point_max, []):
            orig_len = lines_data_or.get(line_id)
            line = await LinesSlopeDAO.find_by_id(session, model_id=line_id)
            if line.angle != 2 or orig_len is None:
                continue
            line_length = abs(line.start.x - line.end.x)
            if abs(line_length - orig_len) < 1e-6:
                continue
            point_stack = []
            if lines_n == 0:
                break
            div_x = round((line_length - orig_len) / lines_n, 3)
            print(f"   div_x={div_x}, actual={line_length}, target={orig_len}")
            # Определяем базовую точку конька
            if line.start.x < line.end.x:
                ridge_pt = line.end_id
                base_x = line.start.x
            else:
                ridge_pt = line.start_id
                base_x = line.end.x
            # Перебираем смежные линии
            for lid in lines_on_point.get(ridge_pt, []):
                if lid == line_id:
                    continue
                l = await LinesSlopeDAO.find_by_id(session, model_id=lid)
                if l.angle == 1:
                    p1 = await PointsSlopeDAO.update_(session, model_id=l.start_id, x=round(base_x + orig_len, 3))
                    print(f"   N1 {p1.id}: {p1.x} {p1.y}")
                    p2 = await PointsSlopeDAO.update_(session, model_id=l.end_id, x=round(base_x + orig_len, 3))
                    print(f"   N2 {p2.id}: {p2.x} {p2.y}")
                    point_stack.extend([p1.id, p2.id])
                else:
                    p = await PointsSlopeDAO.update_(session, model_id=ridge_pt, x=round(base_x + orig_len, 3))
                    print(f"   H1 {p.id}: {p.x} {p.y}")
                    point_stack.append(p.id)
            # Смещаем остальные точки
            # x_max = p1.x
            for pid in points_id:
                if pid in point_stack:
                    continue
                pt = await PointsSlopeDAO.find_by_id(session, model_id=pid)
                q = 0
                f = False
                for lid in lines_on_point[pid]:
                    l = await LinesSlopeDAO.find_by_id(session, model_id=lid)
                    if l.type == 'ендова':
                        q += 1
                    if l.type == 'карниз':
                        q += 1
                    if l.angle == 2:
                        line_length = abs(l.start.x - l.end.x)
                        orig_len = lines_data_or.get(l.id)
                        print(f"  actual={line_length}, target={orig_len}")
                        if abs(line_length - orig_len) > 1e-6:
                            f = True
                if f:
                    p = await PointsSlopeDAO.update_(session, model_id=pid, x=round(pt.x - div_x, 3))
                    print(f"   R {p.id}: {p.x} {p.y}")
                    point_stack.append(pid)
                    continue
                elif pt.y == 0 or q == 2 or pt.x == 0:
                    point_stack.append(pid)
                    continue
                p = await PointsSlopeDAO.update_(session, model_id=pid, x=round(pt.x - div_x, 3))
                point_stack.append(pid)
                print(f"   R {p.id}: {p.x} {p.y}")
            break

    # 7) Финальное обновление длин линий и удаление листов
    for ls in await LinesSlopeDAO.find_all(session, slope_id=slope_id):
        new_len = round(((ls.start.x - ls.end.x)**2 + (ls.start.y - ls.end.y)**2)**0.5, 3)
        updated = await LinesSlopeDAO.update_(session, model_id=ls.id, length=new_len)
        await LinesDAO.update_(session, model_id=updated.parent_id, length=updated.length)
    for sheet in await SheetsDAO.find_all(session, slope_id=slope.id):
        await SheetsDAO.delete_(session, model_id=sheet.id)
    print("▶▶▶ add_sizes completed")


@router.delete("/projects/{project_id}/slopes", description="Delete roof slopes")
async def delete_slope(
    project_id: UUID4,
    user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    project = await ProjectsDAO.find_by_id(session, model_id=project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    slopes = await SlopesDAO.find_all(session, project_id=project_id)
    for slope in slopes:
        await SlopesDAO.delete_(session, model_id=slope.id)


@router.post("/projects/{project_id}/slopes", description="Add roof slopes")
async def add_slope(
    project_id: UUID4,
    user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> None:
    project = await ProjectsDAO.find_by_id(session, model_id=project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    lines = await LinesDAO.find_all(session, project_id=project.id)
    existing_names = []
    slopes_list = find_slope(lines)
    for slope_ids in slopes_list:
        line_objs = [await LinesDAO.find_by_id(session, model_id=lid) for lid in slope_ids]
        line_objs_copy = copy.deepcopy(line_objs)
        existing_points = {}
        slope_name = get_next_slope_name(existing_names)
        existing_names.append(slope_name)
        new_slope = await SlopesDAO.add(session, name=slope_name, project_id=project.id)
        new_lines = rotate_slope(line_objs_copy)
        count = 1
        for line in new_lines:
            if line.start.id in existing_points:
                start_id = existing_points[line.start.id]
                start = await PointsSlopeDAO.find_by_id(session, model_id=start_id)
            else:
                point = await PointsSlopeDAO.add(session, x=line.start.x, y=line.start.y, parent_id=line.start.id, slope_id=new_slope.id)
                start_id = point.id
                start = point
                existing_points[line.start.id] = start_id
            if line.end.id in existing_points:
                end_id = existing_points[line.end.id]
                end = await PointsSlopeDAO.find_by_id(session, model_id=end_id)
            else:
                point = await PointsSlopeDAO.add(session, x=line.end.x, y=line.end.y, parent_id=line.end.id, slope_id=new_slope.id)
                end_id = point.id
                end = point
                existing_points[line.end.id] = end_id
            angle = 1 if end.x == start.x else 2 if end.y == start.y else 0
            await LinesSlopeDAO.add(session, name=line.name, parent_id=line.id, type=line.type, start_id=start_id, end_id=end_id, slope_id=new_slope.id, number=count, angle=angle)
            count += 1
        lines_slope = await LinesSlopeDAO.find_all(session, slope_id=new_slope.id)
        points_slope = await PointsSlopeDAO.find_all(session, slope_id=new_slope.id)
        lines = sorted(lines_slope, key=lambda line: line.number)
        figure = create_figure(lines, [])
        x_min, y_min, x_max, y_max = figure.bounds
        point = Point(x_max, 0)
        is_left = True
        if figure.covers(point):
            is_left = False
        await SlopesDAO.update_(session, model_id=new_slope.id, is_left=is_left)
        lengths_slope = generate_slopes_length(lines=lines_slope, points=points_slope)
        existing_names_length = []
        for ls_tuple in lengths_slope:
            name = get_next_length_name(existing_names_length)
            existing_names_length.append(name)
            if ls_tuple[0] == 0:
                await LengthSlopeDAO.add(session, name=name, type=ls_tuple[0], line_slope_1_id=ls_tuple[1], line_slope_2_id=ls_tuple[2], slope_id=new_slope.id)
            elif ls_tuple[0] == 1:
                await LengthSlopeDAO.add(session, name=name, type=ls_tuple[0], line_slope_1_id=ls_tuple[1], point_1_id=ls_tuple[2], slope_id=new_slope.id)
            else:
                await LengthSlopeDAO.add(session, name=name, type=ls_tuple[0], point_2_id=ls_tuple[1], point_1_id=ls_tuple[2], slope_id=new_slope.id)


@router.patch(
    "/projects/{project_id}/slopes/{slope_id}/lines_slope/{line_slope_id}",
    description="Update length of line for slope"
)
async def update_line_slope(
    project_id: UUID4,
    slope_id: UUID4,
    line_slope_id: UUID4,
    length: float,
    user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> None:
    """
    Обновляет длину линии на склоне и корректирует координаты связанных точек.

    :param project_id: Идентификатор проекта.
    :param slope_id: Идентификатор склона.
    :param line_slope_id: Идентификатор линии склона.
    :param length: Новая длина линии.
    :param user: Текущий пользователь.
    :param session: Асинхронная сессия для работы с базой данных.
    :raises ProjectNotFound: Если проект не найден или не принадлежит пользователю.
    :raises SlopeNotFound: Если склон не найден или не принадлежит проекту.
    """
    # Проверяем проект и склон
    project = await ProjectsDAO.find_by_id(session, model_id=project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound

    slope = await SlopesDAO.find_by_id(session, model_id=slope_id)
    if not slope or slope.project_id != project_id:
        raise SlopeNotFound

    # Получаем линию склона и обновляем длину родительской линии
    line_slope = await LinesSlopeDAO.find_by_id(session, model_id=line_slope_id)
    lines = await LinesSlopeDAO.find_all(session, slope_id=slope.id)
    if not line_slope:
        raise HTTPException(status_code=404, detail="Line slope not found.")
    parent_line = await LinesDAO.find_by_id(session, model_id=line_slope.parent_id)
    if parent_line:
        parent_line.length = length

    # Выбираем точку для корректировки координат:
    # Если линия имеет возрастающие координаты (по x и y), берем точку начала, иначе - конца.
    if line_slope.start.x <= line_slope.end.x and line_slope.start.y <= line_slope.end.y:
        point = line_slope.start
        other = line_slope.end
    else:
        point = line_slope.end
        other = line_slope.start

    if line_slope.start.y == line_slope.end.y:
        # Горизонтальная линия
        other.x = point.x + length
    elif line_slope.start.x == line_slope.end.x:
        # Вертикальная линия
        other.y = point.y + length
    else:
        # Наклонная линия
        height = abs(point.y - other.y)
        new_x = round(((length ** 2) - (height ** 2)) ** 0.5, 2)
        other.x = point.x + new_x

    for line in lines:
        calc_length = round(
            ((line.start.x - line.end.x) ** 2 +
             (line.start.y - line.end.y) ** 2) ** 0.5, 2
        )
        line.length = calc_length
    # Обновляем длины измерительных линий (LengthSlope)
    length_lines = await LengthSlopeDAO.find_all(session, slope_id=slope_id)
    for length_slope in length_lines:
        if length_slope.type == 0:
            line_1 = length_slope.line_slope_1
            line_2 = length_slope.line_slope_2
            length_slope.length = round(abs(line_2.start.y - line_1.start.y), 2)
        elif length_slope.type == 1:
            line = length_slope.line_slope_1
            point = length_slope.point_1
            length_slope.length = round(abs(line.start.y - point.y), 2)
        else:
            point_1 = length_slope.point_1
            point_2 = length_slope.point_2
            length_slope.length = round(abs(point_1.y - point_2.y), 2)

    # Удаляем все старые листы (Sheets) для данного склона
    sheets_old = await SheetsDAO.find_all(session, slope_id=slope.id)
    for sheet_old in sheets_old:
        await SheetsDAO.delete_(session, model_id=sheet_old.id)


@router.patch(
    "/projects/{project_id}/slopes/{slope_id}/lengths_slope/{length_slope_id}",
    description="Update length of line for slope"
)
async def update_length_slope(
    project_id: UUID4,
    slope_id: UUID4,
    length_slope_id: UUID4,
    length: float,
    user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> None:
    """
    Обновляет длину измерительной линии (LengthSlope) на склоне и пересчитывает связанные элементы:
      - Корректирует координаты точек, связанные с измерительной линией, в зависимости от её типа.
      - Пересчитывает длины всех линий склона и обновляет родительские линии.
      - Пересчитывает измерительные линии для склона.
      - Удаляет старые листы (Sheets), пересчитывает вырезы (cutouts) и обновляет площадь склона.
      - Пересчитывает листы покрытия на основании полученной фигуры.

    :param project_id: Идентификатор проекта.
    :param slope_id: Идентификатор склона.
    :param length_slope_id: Идентификатор измерительной линии.
    :param length: Новая длина измерительной линии.
    :param user: Текущий пользователь.
    :param session: Асинхронная сессия для работы с базой данных.
    :raises ProjectNotFound: Если проект не найден или не принадлежит пользователю.
    :raises SlopeNotFound: Если склон не найден или не принадлежит проекту.
    """
    # Проверка проекта
    project = await ProjectsDAO.find_by_id(session, model_id=project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound

    # Проверка склона
    slope = await SlopesDAO.find_by_id(session, model_id=slope_id)
    if not slope or slope.project_id != project_id:
        raise SlopeNotFound

    # Обновляем измерительную линию (LengthSlope)
    length_slope = await LengthSlopeDAO.find_by_id(session, model_id=length_slope_id)
    await LengthSlopeDAO.update_(session, model_id=length_slope.id, length=length)

    # Корректировка координат точек в зависимости от типа измерительной линии
    if length_slope.type == 0:
        # Для типа 0 обновляем y у обеих точек родительской линии (через LinesSlope)
        line = await LinesSlopeDAO.find_by_id(session, model_id=length_slope.line_slope_2_id)
        await PointsSlopeDAO.update_(session, model_id=line.start_id, y=length)
        await PointsSlopeDAO.update_(session, model_id=line.end_id, y=length)
    elif length_slope.type == 1:
        await PointsSlopeDAO.update_(session, model_id=length_slope.point_1_id, y=length)
    else:
        await PointsSlopeDAO.update_(session, model_id=length_slope.point_2_id, y=length)

    # Пересчёт длин всех линий склона и обновление родительских линий
    lines_slope = await LinesSlopeDAO.find_all(session, slope_id=slope_id)
    for ls in lines_slope:
        calc_length = round(
            ((ls.start.x - ls.end.x) ** 2 + (ls.start.y - ls.end.y) ** 2) ** 0.5, 2
        )
        updated_ls = await LinesSlopeDAO.update_(session, model_id=ls.id, length=calc_length)
        await LinesDAO.update_(session, model_id=updated_ls.parent_id, length=updated_ls.length)

    # Пересчёт измерительных линий (LengthSlope) для склона
    length_lines = await LengthSlopeDAO.find_all(session, slope_id=slope_id)
    for ls in length_lines:
        if ls.type == 0:
            line_1 = await LinesSlopeDAO.find_by_id(session, model_id=ls.line_slope_1_id)
            line_2 = await LinesSlopeDAO.find_by_id(session, model_id=ls.line_slope_2_id)
            new_length = round(abs(line_1.start.y - line_2.start.y), 2)
            await LengthSlopeDAO.update_(session, model_id=ls.id, length=new_length)
        elif ls.type == 1:
            pt = await PointsSlopeDAO.find_by_id(session, model_id=ls.point_1_id)
            ln = await LinesSlopeDAO.find_by_id(session, model_id=ls.line_slope_1_id)
            new_length = round(abs(ln.start.y - pt.y), 2)
            await LengthSlopeDAO.update_(session, model_id=ls.id, length=new_length)
        else:
            pt1 = await PointsSlopeDAO.find_by_id(session, model_id=ls.point_1_id)
            pt2 = await PointsSlopeDAO.find_by_id(session, model_id=ls.point_2_id)
            new_length = round(abs(pt1.y - pt2.y), 2)
            await LengthSlopeDAO.update_(session, model_id=ls.id, length=new_length)

    # Удаляем все старые листы (Sheets) для данного склона
    sheets_old = await SheetsDAO.find_all(session, slope_id=slope.id)
    for sheet in sheets_old:
        await SheetsDAO.delete_(session, model_id=sheet.id)

    # Пересчитываем вырезы (cutouts) и формируем список координат точек вырезов
    cutouts_slope = await CutoutsDAO.find_all(session, slope_id=slope_id)
    lines = await LinesSlopeDAO.find_all(session, slope_id=slope_id)
    lines = sorted(lines, key=lambda line: line.number)
    cutouts = []
    for cutout in cutouts_slope:
        points_cutout = await PointsCutoutsDAO.find_all(session, cutout_id=cutout.id)
        points_cutout = sorted(points_cutout, key=lambda pt: pt.number)
        cutout_coords = [(pt.x, pt.y) for pt in points_cutout]
        cutouts.append(cutout_coords)

    # Создаем фигуру на основании линий и вырезов
    figure = create_figure(lines, cutouts)
    area = figure.area
    await SlopesDAO.update_(session, model_id=slope_id, area=area)

    # Получаем покрытие проекта и создаем листы покрытия на основе фигуры
    roof = await RoofsDAO.find_by_id(session, model_id=project.roof_id)
    sheets = create_sheets(figure=figure, roof=roof, is_left=slope.is_left, overhang=project.overhang)
    for sh in sheets:
        await SheetsDAO.add(
            session,
            x_start=sh[0],
            y_start=sh[1],
            length=sh[2],
            area_overall=sh[3],
            area_usefull=sh[4],
            slope_id=slope_id
        )


@router.patch(
    "/projects/{project_id}/slopes/{slope_id}/points_slope/{point_slope_id}",
    description="Update coords point for slope"
)
async def update_point_slope(
    project_id: UUID4,
    slope_id: UUID4,
    point_slope_id: UUID4,
    point: PointData,
    user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> None:
    """
    Обновляет координаты указанной точки на склоне и пересчитывает связанные линии,
    измерительные линии, вырезы и листы покрытия.

    :param project_id: Идентификатор проекта.
    :param slope_id: Идентификатор склона.
    :param point_slope_id: Идентификатор точки на склоне.
    :param point: Новые координаты точки.
    :param user: Текущий пользователь.
    :param session: Асинхронная сессия для работы с БД.
    """
    project = await ProjectsDAO.find_by_id(session, model_id=project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound

    slope = await SlopesDAO.find_by_id(session, model_id=slope_id)
    if not slope or slope.project_id != project_id:
        raise SlopeNotFound

    # Обновляем координаты точки
    await PointsSlopeDAO.update_(session, model_id=point_slope_id, x=point.x, y=point.y)

    # Пересчитываем длины линий склона, связанные с измененной точкой
    lines_slope = await LinesSlopeDAO.find_all(session, slope_id=slope_id)
    for ls in lines_slope:
        calc_length = round(
            ((ls.start.x - ls.end.x) ** 2 + (ls.start.y - ls.end.y) ** 2) ** 0.5, 2
        )
        updated_ls = await LinesSlopeDAO.update_(session, model_id=ls.id, length=calc_length)
        await LinesDAO.update_(session, model_id=updated_ls.parent_id, length=updated_ls.length)

    # Пересчитываем измерительные линии (LengthSlope)
    length_lines = await LengthSlopeDAO.find_all(session, slope_id=slope_id)
    for ls in length_lines:
        if ls.type == 0:
            line_1 = await LinesSlopeDAO.find_by_id(session, model_id=ls.line_slope_1_id)
            line_2 = await LinesSlopeDAO.find_by_id(session, model_id=ls.line_slope_2_id)
            new_length = round(abs(line_1.start.y - line_2.start.y), 2)
            await LengthSlopeDAO.update_(session, model_id=ls.id, length=new_length)
        elif ls.type == 1:
            pt = await PointsSlopeDAO.find_by_id(session, model_id=ls.point_1_id)
            ln = await LinesSlopeDAO.find_by_id(session, model_id=ls.line_slope_1_id)
            new_length = round(abs(ln.start.y - pt.y), 2)
            await LengthSlopeDAO.update_(session, model_id=ls.id, length=new_length)
        else:
            pt1 = await PointsSlopeDAO.find_by_id(session, model_id=ls.point_1_id)
            pt2 = await PointsSlopeDAO.find_by_id(session, model_id=ls.point_2_id)
            new_length = round(abs(pt1.y - pt2.y), 2)
            await LengthSlopeDAO.update_(session, model_id=ls.id, length=new_length)

    # Удаляем старые листы (Sheets) для склона
    sheets_old = await SheetsDAO.find_all(session, slope_id=slope.id)
    for sheet in sheets_old:
        await SheetsDAO.delete_(session, model_id=sheet.id)

    # Пересчитываем вырезы (cutouts) и обновляем план
    cutouts_slope = await CutoutsDAO.find_all(session, slope_id=slope_id)
    lines = await LinesSlopeDAO.find_all(session, slope_id=slope_id)
    lines = sorted(lines, key=lambda l: l.number)
    cutouts = []
    for cutout in cutouts_slope:
        pts = await PointsCutoutsDAO.find_all(session, cutout_id=cutout.id)
        pts = sorted(pts, key=lambda p: p.number)
        cutout_coords = [(p.x, p.y) for p in pts]
        cutouts.append(cutout_coords)

    figure = create_figure(lines, cutouts)
    area = figure.area
    await SlopesDAO.update_(session, model_id=slope_id, area=area)

    roof = await RoofsDAO.find_by_id(session, model_id=project.roof_id)
    sheets = create_sheets(figure=figure, roof=roof, is_left=slope.is_left, overhang=project.overhang)
    for sh in sheets:
        await SheetsDAO.add(
            session,
            x_start=sh[0],
            y_start=sh[1],
            length=sh[2],
            area_overall=sh[3],
            area_usefull=sh[4],
            slope_id=slope_id
        )


# -------------------- Cutout Endpoints --------------------

@router.delete(
    "/projects/{project_id}/add_line/slopes/{slope_id}/cutouts/{cutout_id}",
    description="Delete cutout"
)
async def delete_cutout(
    project_id: UUID4,
    slope_id: UUID4,
    cutout_id: UUID4,
    user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> None:
    """
    Удаляет вырез (cutout) для заданного склона.
    """
    # Здесь можно также проверить, что проект принадлежит пользователю,
    # если это требуется.
    cutout = await CutoutsDAO.find_by_id(session, model_id=cutout_id)
    if not cutout or cutout.slope_id != slope_id:
        raise SlopeNotFound
    await CutoutsDAO.delete_(session, model_id=cutout_id)


@router.post(
    "/projects/{project_id}/slopes/{slope_id}/cutouts",
    description="Add cutout"
)
async def add_cutout(
    project_id: UUID4,
    slope_id: UUID4,
    points: List[PointData],
    user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> None:
    """
    Создает вырез (cutout) на склоне, добавляя заданные точки.
    """
    project = await ProjectsDAO.find_by_id(session, model_id=project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    slope = await SlopesDAO.find_by_id(session, model_id=slope_id)
    if not slope or slope.project_id != project_id:
        raise SlopeNotFound
    cutout = await CutoutsDAO.add(session, slope_id=slope_id)
    count = 1
    for pt in points:
        await PointsCutoutsDAO.add(session, x=pt.x, y=pt.y, number=count, cutout_id=cutout.id)
        count += 1


@router.patch(
    "/projects/{project_id}/slopes/{slope_id}/cutouts/{cutout_id}",
    description="Update cutout"
)
async def update_cutout(
    project_id: UUID4,
    slope_id: UUID4,
    cutout_id: UUID4,
    points_cutout: List[PointCutoutResponse],
    user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> None:
    """
    Обновляет координаты точек выреза (cutout) на склоне.
    """
    project = await ProjectsDAO.find_by_id(session, model_id=project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    slope = await SlopesDAO.find_by_id(session, model_id=slope_id)
    if not slope or slope.project_id != project_id:
        raise SlopeNotFound
    cutout = await CutoutsDAO.find_by_id(session, model_id=cutout_id)
    if not cutout:
        raise CutoutNotFound
    for pt in points_cutout:
        await PointsCutoutsDAO.update_(session, model_id=pt.id, x=pt.x, y=pt.y)


# -------------------- Sheets Endpoints --------------------

@router.patch(
    "/projects/{project_id}/slopes/{slope_id}/sheets/{sheet_id}/delete_sheet",
    description="Delete sheet"
)
async def delete_sheet(
    project_id: UUID4,
    slope_id: UUID4,
    sheet_id: UUID4,
    user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> None:
    """
    Удаляет лист покрытия (sheet) с заданным идентификатором.
    """
    project = await ProjectsDAO.find_by_id(session, model_id=project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    slope = await SlopesDAO.find_by_id(session, model_id=slope_id)
    if not slope or slope.project_id != project_id:
        raise SlopeNotFound
    sheet = await SheetsDAO.find_by_id(session, model_id=sheet_id)
    if sheet is None or sheet.slope_id != slope_id:
        raise SheetNotFound
    if sheet.is_deleted is True:
        raise HTTPException(status_code=400, detail="Sheet is already deleted.")
    if sheet.change_sheets:
        raise HTTPException(status_code=400, detail="Sheet is already changed.")
    await SheetsDAO.update_(session, model_id=sheet_id, is_deleted=True)
    sheets = await DeletedSheetsDAO.find_all(session, project_id=project_id)
    existing_names = [sheet.number for sheet in sheets]
    number = get_next_sheet_name(existing_names)
    await DeletedSheetsDAO.add(
        session, 
        deleted_sheet_id=sheet_id,
        project_id=project.id,
        number=number,
        )


@router.patch(
    "/projects/{project_id}/slopes/{slope_id}/sheets/{sheet_id}/return_sheet",
    description="Return sheet"
)
async def return_sheet(
    project_id: UUID4,
    slope_id: UUID4,
    sheet_id: UUID4,
    user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> None:
    """
    Восстанавливает лист покрытия (sheet) с заданным идентификатором.
    """
    project = await ProjectsDAO.find_by_id(session, model_id=project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    slope = await SlopesDAO.find_by_id(session, model_id=slope_id)
    if not slope or slope.project_id != project_id:
        raise SlopeNotFound
    sheet = await SheetsDAO.find_by_id(session, model_id=sheet_id)
    if not sheet or sheet.slope_id != slope_id:
        raise SheetNotFound
    if sheet.is_deleted is False or not sheet.deleted_sheets:
        raise HTTPException(status_code=400, detail="Sheet is not deleted.")
    await SheetsDAO.update_(session, model_id=sheet_id, is_deleted=False)
    await DeletedSheetsDAO.delete_(session, model_id=sheet.deleted_sheets.id)


@router.patch(
    "/projects/{project_id}/slopes/sheets/{delete_sheet_id}/change_sheet",
    description="Change deleted sheet"
)
async def change_sheet(
    project_id: UUID4,
    change_sheet_data: ChangeSheetRequest,
    delete_sheet_id: UUID4,
    user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> None:
    project = await ProjectsDAO.find_by_id(session, model_id=project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    del_sheet = await SheetsDAO.find_by_id(session, model_id=delete_sheet_id)
    if not del_sheet:
        raise SheetNotFound
    change_sheet = await SheetsDAO.find_by_id(session, model_id=change_sheet_data.change_sheet_id)
    if change_sheet_data.change_sheet_id == delete_sheet_id:
        raise HTTPException(status_code=400, detail="Sheet is deleted.")
    if (not change_sheet and change_sheet_data.change_sheet_id is not None):
        raise SheetNotFound
    if change_sheet_data.change_sheet_id is None:
        delete_sheet = await DeletedSheetsDAO.find_one_or_none(session, deleted_sheet_id=del_sheet.id)
        await DeletedSheetsDAO.update_(
        session, 
        model_id=delete_sheet.id,
        change_sheet_id=change_sheet_data.change_sheet_id,
        )
    else:
        if del_sheet.is_deleted is False or not del_sheet.deleted_sheets:
            raise HTTPException(status_code=400, detail="Sheet is not deleted.")
        if change_sheet.is_deleted is True:
            raise HTTPException(status_code=400, detail="Sheet is deleted.")
        if change_sheet.change_sheets:
            raise HTTPException(status_code=400, detail="Sheet is already changed.")
        delete_sheet = await DeletedSheetsDAO.find_one_or_none(session, deleted_sheet_id=del_sheet.id)
        if delete_sheet.change_sheet_id:
            raise HTTPException(status_code=400, detail="Sheet is already changed.")
        await DeletedSheetsDAO.update_(
            session, 
            model_id=delete_sheet.id,
            change_sheet_id=change_sheet.id,
            )


@router.delete(
    "/projects/{project_id}/add_line/slopes/{slope_id}/sheets",
    description="Delete sheets"
)
async def delete_sheets(
    project_id: UUID4,
    slope_id: UUID4,
    user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> None:
    """
    Удаляет все листы покрытия для указанного склона.
    """
    project = await ProjectsDAO.find_by_id(session, model_id=project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    slope = await SlopesDAO.find_by_id(session, model_id=slope_id)
    if not slope or slope.project_id != project_id:
        raise SlopeNotFound
    sheets_old = await SheetsDAO.find_all(session, slope_id=slope_id)
    for sheet in sheets_old:
        await SheetsDAO.delete_(session, model_id=sheet.id)


@router.patch(
    "/projects/{project_id}/slopes/{slope_id}/sheet/{sheet_id}",
    description="Add roof sheet for slope"
)
async def add_sheet(
    project_id: UUID4,
    slope_id: UUID4,
    sheet_id: UUID4,
    is_down: bool,
    user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> None:
    """
    Добавляет дополнительный лист покрытия для склона.
    В зависимости от параметра is_down лист разбивается на два с разными размерами.
    """
    project = await ProjectsDAO.find_by_id(session, model_id=project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    roof = await RoofsDAO.find_by_id(session, model_id=project.roof_id)
    slope = await SlopesDAO.find_by_id(session, model_id=slope_id)
    if not slope or slope.project_id != project_id:
        raise SlopeNotFound
    sheet = await SheetsDAO.find_by_id(session, model_id=sheet_id)
    if sheet.length - roof.overlap < roof.min_length:
        raise SheetTooShortNotFound
    if sheet.length <= roof.max_length or sheet.length >= roof.min_length:
        new_length_1 = roof.overlap + roof.overlap
        new_length_2 = sheet.length - roof.overlap
    if is_down:
        await SheetsDAO.add(
            session,
            x_start=sheet.x_start,
            y_start=sheet.y_start,
            length=new_length_1,
            area_overall=new_length_1 * roof.overall_width,
            area_usefull=new_length_1 * roof.useful_width,
            slope_id=slope_id
        )
        await SheetsDAO.update_(
            session,
            model_id=sheet.id,
            y_start=sheet.y_start + sheet.length - new_length_2,
            length=new_length_2
        )
    else:
        await SheetsDAO.add(
            session,
            x_start=sheet.x_start,
            y_start=sheet.y_start + sheet.length - new_length_1,
            length=new_length_1,
            area_overall=new_length_1 * roof.overall_width,
            area_usefull=new_length_1 * roof.useful_width,
            slope_id=slope_id
        )
        await SheetsDAO.update_(
            session,
            model_id=sheet.id,
            length=new_length_2
        )


@router.post(
    "/projects/{project_id}/slopes/{slope_id}/sheets",
    description="Calculate roof sheets for slope"
)
async def add_sheets(
    project_id: UUID4,
    slope_id: UUID4,
    user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> None:
    """
    Пересчитывает и создает листы покрытия для склона:
      - Удаляет старые листы.
      - Получает вырезы (cutouts) и линии склона.
      - Создает фигуру покрытия и обновляет площадь склона.
      - Создает новые листы покрытия на основании фигуры.
    """
    project = await ProjectsDAO.find_by_id(session, model_id=project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    slope = await SlopesDAO.find_by_id(session, model_id=slope_id)
    if not slope or slope.project_id != project_id:
        raise SlopeNotFound
    sheets_old = await SheetsDAO.find_all(session, slope_id=slope.id)
    if sheets_old:
        for sheet_old in sheets_old:
            await SheetsDAO.delete_(session, model_id=sheet_old.id)
    cutouts_slope = await CutoutsDAO.find_all(session, slope_id=slope_id)
    lines = await LinesSlopeDAO.find_all(session, slope_id=slope_id)
    lines = sorted(lines, key=lambda line: line.number)
    cutouts = []
    for cutout in cutouts_slope:
        pts = await PointsCutoutsDAO.find_all(session, cutout_id=cutout.id)
        pts = sorted(pts, key=lambda p: p.number)
        cutout_coords = [(p.x, p.y) for p in pts]
        cutouts.append(cutout_coords)
    figure = create_figure(lines, cutouts)
    area = figure.area
    await SlopesDAO.update_(session, model_id=slope_id, area=area)
    roof = await RoofsDAO.find_by_id(session, model_id=project.roof_id)
    sheets = create_sheets(figure=figure, roof=roof, is_left=slope.is_left, overhang=project.overhang)
    for sh in sheets:
        await SheetsDAO.add(
            session,
            x_start=sh[0],
            y_start=sh[1],
            length=sh[2],
            area_overall=sh[3],
            area_usefull=sh[4],
            slope_id=slope_id
        )


@router.patch(
    "/projects/{project_id}/slopes/{slope_id}/update_length_sheets",
    description="Calculate roof sheets for slope"
)
async def update_length_sheets(
    project_id: UUID4,
    slope_id: UUID4,
    sheets_id: List[UUID4],
    length: float,
    up: bool,
    user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> None:
    """
    Обновляет длину указанных листов покрытия.
    Если новая длина не превышает максимально допустимую для крыши, обновляет параметры листа.
    """
    project = await ProjectsDAO.find_by_id(session, model_id=project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    roof = await RoofsDAO.find_by_id(session, model_id=project.roof_id)
    slope = await SlopesDAO.find_by_id(session, model_id=slope_id)
    if not slope or slope.project_id != project_id:
        raise SlopeNotFound
    sheets = [await SheetsDAO.find_by_id(session, model_id=sheet_id) for sheet_id in sheets_id]
    for sheet in sheets:
        if sheet.length + length > roof.max_length or sheet.length + length < roof.min_length:
            continue
        if up:
            sheet.length += length
        else:
            sheet.y_start -= length
            sheet.length += length
        sheet.area_overall = sheet.length * roof.overall_width
        sheet.area_usefull = sheet.length * roof.useful_width


@router.patch("/projects/{project_id}/slopes/{slope_id}/offset_sheets")
async def offset_sheets(
    project_id: UUID4,
    slope_id: UUID4,
    data: PointData,
    user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> None:
    """
    Пересчитывает листы покрытия с учетом смещения.
    Удаляет старые листы, пересчитывает вырезы, строит новую фигуру и создает новые листы покрытия.
    """
    project = await ProjectsDAO.find_by_id(session, model_id=project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    slope = await SlopesDAO.find_by_id(session, model_id=slope_id)
    if not slope or slope.project_id != project_id:
        raise SlopeNotFound
    sheets = await SheetsDAO.find_all(session, slope_id=slope_id)
    sheets = sorted(
        sheets,
        key=lambda s: (s.x_start, s.y_start)
    )
    cutouts_slope = await CutoutsDAO.find_all(session, slope_id=slope_id)
    lines = await LinesSlopeDAO.find_all(session, slope_id=slope_id)
    lines = sorted(lines, key=lambda line: line.number)
    cutouts = []
    for cutout in cutouts_slope:
        pts = await PointsCutoutsDAO.find_all(session, cutout_id=cutout.id)
        pts = sorted(pts, key=lambda p: p.number)
        cutout_coords = [(p.x, p.y) for p in pts]
        cutouts.append(cutout_coords)
    figure = create_figure(lines, cutouts)
    area = figure.area
    await SlopesDAO.update_(session, model_id=slope_id, area=area)
    roof = await RoofsDAO.find_by_id(session, model_id=project.roof_id)
    x_min, y_min, x_max, y_max = figure.bounds
    x_left = sheets[0].x_start + data.x - x_min
    x_right = x_max - sheets[-1].x_start - data.x
    if not project.overhang:
        overhang = 0
    else:
        overhang = project.overhang
    y_levels = []
    y_min_l = y_min - overhang
    while y_min_l <= y_max:
        y_levels.append(y_min_l)
        y_min_l += roof.overlap
    prev_position = None
    for sheet in sheets:
        if prev_position is None:
            prev_position = [sheet.x_start + data.x, sheet.y_start + data.y]
        elif prev_position[0] != round(sheet.x_start + data.y, 3):
            prev_position[0] = round(sheet.x_start + data.x, 3)
            prev_position[1] = round(sheet.y_start + data.y, 3)
        print(prev_position)
        print(sheet.x_start, sheet.y_start)
        y_start = round(prev_position[1] - roof.overlap, 3)
        x_start = prev_position[0]
        length = sheet.length
        new_sheet = sheet_offset(
            x_start=x_start, y_start=y_start, length=length,
            figure=figure, roof=roof, y_levels=y_levels, overhang=overhang)
        print(y_start, x_start, length, new_sheet[2])
        if new_sheet[2] == 0:
            await SheetsDAO.delete_(session, model_id=sheet.id)
        else:
            sheet.x_start = round(new_sheet[0], 3)
            sheet.y_start = round(new_sheet[1], 3)
            sheet.length = round(new_sheet[2], 3)
            sheet.area_overall = round(new_sheet[3], 3)
            sheet.area_usefull = round(new_sheet[4], 3)
            prev_position[1] = round(new_sheet[1] + new_sheet[2] - roof.overlap, 3)
            prev_position[0] = round(new_sheet[0], 3)
    sheets = await SheetsDAO.find_all(session, slope_id=slope_id)
    sheets = sorted(
        sheets,
        key=lambda s: (s.x_start, s.y_start)
    )
    if x_left >= roof.overall_width - roof.useful_width:
        y_start = y_min
        x_start = sheets[0].x_start - roof.useful_width
        length = 0
        new_sheet = sheet_offset(
            x_start=x_start, y_start=y_start, length=length,
            figure=figure, roof=roof, y_levels=y_levels, overhang=overhang)
        if new_sheet[2] > 0:
            await SheetsDAO.add(
                session,
                x_start=round(new_sheet[0], 3),
                y_start=round(new_sheet[1], 3),
                length=round(new_sheet[2], 3),
                area_overall=round(new_sheet[3], 3),
                area_usefull=round(new_sheet[4], 3),
                slope_id=slope_id
            )
    if x_right >= roof.overall_width - roof.useful_width:
        y_start = y_min
        x_start = sheets[-1].x_start + roof.useful_width
        length = 0
        new_sheet = sheet_offset(
            x_start=x_start, y_start=y_start, length=length,
            figure=figure, roof=roof, y_levels=y_levels, overhang=overhang)
        if new_sheet[2] > 0:
            await SheetsDAO.add(
                session,
                x_start=round(new_sheet[0], 3),
                y_start=round(new_sheet[1], 3),
                length=round(new_sheet[2], 3),
                area_overall=round(new_sheet[3], 3),
                area_usefull=round(new_sheet[4], 3),
                slope_id=slope_id
            )


@router.patch("/projects/{project_id}/slopes/{slope_id}/overlay", description="Calculate roof sheets for slope")
async def update_sheets_overlay(
    project_id: UUID4,
    slope_id: UUID4,
    user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> None:
    """
    Объединяет и пересчитывает листы покрытия склона.
    Если два листа имеют общие начальные координаты и перекрываются, их длины объединяются с учетом перекрытия.
    """
    project = await ProjectsDAO.find_by_id(session, model_id=project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    slope = await SlopesDAO.find_by_id(session, model_id=slope_id)
    if not slope or slope.project_id != project_id:
        raise SlopeNotFound
    roof = await RoofsDAO.find_by_id(session, model_id=project.roof_id)
    sheets = await SheetsDAO.find_all(session, slope_id=slope_id)
    sheets = sorted(
        sheets,
        key=lambda s: (s.x_start, s.y_start)
    )
    previous_sheet = None
    for sheet in sheets:
        if previous_sheet is None:
            previous_sheet = sheet
            continue
        # оба листа начинаются в одной точке по X
        if previous_sheet.x_start == sheet.x_start:
            # пересекаются ли они по Y?
            overlap_amount = max(
                0,
                (previous_sheet.y_start + previous_sheet.length) - sheet.y_start
            )
            # если есть перекрытие, объединяем длины, убирая зону overlap
            new_length = previous_sheet.length + sheet.length - overlap_amount
            # не превышаем лимит по длине листа
            if new_length <= roof.max_length:
                # обновляем предыдущий лист, удаляем текущий
                await SheetsDAO.update_(session, model_id=previous_sheet.id, length=new_length)
                await SheetsDAO.delete_(session, model_id=sheet.id)
                # previous_sheet остаётся тем же — но с удлинённой длиной
                continue

        # если не объединили, двигаем previous_sheet на текущий
        previous_sheet = sheet


# -------------------- Accessories, Materials and Estimate --------------------

@router.delete(
    "/projects/{project_id}/accessories/{accessory_id}",
    description="Delete accessory"
)
async def delete_accessory(
    accessory_id: UUID4,
    project_id: UUID4,
    user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> None:
    """
    Удаляет аксессуар из проекта.
    """
    project = await ProjectsDAO.find_by_id(session, model_id=project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    accessory = await AccessoriesDAO.find_by_id(session, model_id=accessory_id)
    if not accessory or accessory.project_id != project_id:
        raise ProjectNotFound
    await AccessoriesDAO.delete_(session, model_id=accessory_id)


@router.post(
    "/projects/{project_id}/accessories",
    description="Calculate roof sheets for slope"
)
async def add_accessory(
    project_id: UUID4,
    accessory: AccessoriesRequest,
    user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> None:
    """
    Добавляет аксессуар в проект, вычисляя общую длину линий и количество на основе базовых параметров.
    """
    project = await ProjectsDAO.find_by_id(session, model_id=project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    lines = await asyncio.gather(*[LinesDAO.find_by_id(session, model_id=line_id) for line_id in accessory.lines_id])
    lines_length = sum(line.length for line in lines)
    accessory_base = await Accessory_baseDAO.find_by_id(session, model_id=accessory.accessory_bd_id)
    quantity = calculate_count_accessory(lines_length, accessory_base)
    await AccessoriesDAO.add(
        session,
        lines_id=accessory.lines_id,
        lines_length=lines_length,
        quantity=quantity,
        accessory_base_id=accessory_base.id,
        project_id=project_id,
    )


@router.patch(
    "/projects/{project_id}/accessories/{accessory_id}",
    description="Calculate roof sheets for slope"
)
async def update_accessory(
    project_id: UUID4,
    accessory_data: AccessoriesUpdateRequest,
    user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> None:
    """
    Обновляет данные аксессуара в проекте, пересчитывая общую длину линий и количество.
    """
    project = await ProjectsDAO.find_by_id(session, model_id=project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    lines = await asyncio.gather(*[LinesDAO.find_by_id(session, model_id=line_id) for line_id in accessory_data.lines_id])
    lines_length = sum(line.length for line in lines)
    accessory = await AccessoriesDAO.find_by_id(session, model_id=accessory_data.accessory_id)
    if not accessory or accessory.project_id != project.id:
        raise AccessoryNotFound
    accessory_base = await Accessory_baseDAO.find_by_id(session, model_id=accessory.accessory_base_id)
    if not accessory_base:
        raise AccessoryBaseNotFound
    quantity = calculate_count_accessory(lines_length, accessory_base)
    await AccessoriesDAO.update_(
        session,
        model_id=accessory.id,
        lines_id=accessory_data.lines_id,
        lines_length=lines_length,
        quantity=quantity
    )


@router.patch("/projects/{project_id}/accessories/{accessory_id}/color")
async def add_color_accessory(
    project_id: UUID4,
    accessory_id: UUID4,
    color: str | None,
    user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> None:
    """
    Добавляет материал в проект.
    """
    project = await ProjectsDAO.find_by_id(session, model_id=project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    accessory = await AccessoriesDAO.find_by_id(session, model_id=accessory_id)
    if not accessory or accessory.project_id != project_id:
        raise ProjectNotFound
    await AccessoriesDAO.update_(
        session,
        model_id=accessory.id,
        color=color
    )


@router.post("/projects/{project_id}/materials")
async def add_material(
    project_id: UUID4,
    materials: MaterialRequest,
    user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> None:
    """
    Добавляет материал в проект.
    """
    project = await ProjectsDAO.find_by_id(session, model_id=project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    material = await MaterialsDAO.find_one_or_none(session, project_id=project.id)
    if material:
        raise MaterialAlreadyExist
    await MaterialsDAO.add(
        session,
        project_id=project_id,
        name=materials.name,
        material=materials.material,
        color=materials.color
    )


@router.patch("/projects/{project_id}/materials")
async def update_material(
    project_id: UUID4,
    materials: MaterialRequest,
    user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> None:
    """
    Изменить материал в проект.
    """
    project = await ProjectsDAO.find_by_id(session, model_id=project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    material = await MaterialsDAO.find_one_or_none(session, project_id=project.id)
    if not material:
        raise MaterialNotFound
    await MaterialsDAO.update_(
        session,
        model_id=material.id,
        name=materials.name,
        material=materials.material,
        color=materials.color
    )


@router.delete("/projects/{project_id}/materials/delete_material")
async def delete_material(
    project_id: UUID4,
    materials: MaterialRequest,
    user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> None:
    """
    Удаляет материал из проекта.
    """
    project = await ProjectsDAO.find_by_id(session, model_id=project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    material = await MaterialsDAO.find_one_or_none(session, project_id=project.id)
    if not material:
        raise MaterialNotFound
    await MaterialsDAO.delete_(
        session,
        model_id=material.id,
    )


@router.get(
    "/projects/{project_id}/estimate",
    description="View accessories"
)
async def get_estimate(
    project_id: UUID4,
    user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> EstimateResponse:
    """
    Формирует оценку проекта с учетом данных по покрытию, склонам, аксессуарам и крепежу.
    """
    project = await ProjectsDAO.find_by_id(session, model_id=project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    slopes = await SlopesDAO.find_all(session, project_id=project_id)
    roof = await RoofsDAO.find_by_id(session, model_id=project.roof_id)
    slopes_area = 0
    all_sheets = []
    overall = 0
    if slopes:
        slopes_estimate = []
        for slope in slopes:
            area_overall = 0
            area_usefull = 0
            if slope.area is not None:
                slopes_area += slope.area
            sheets = await SheetsDAO.find_all(session, slope_id=slope.id)
            for sheet in sheets:
                area_overall += sheet.area_overall
                area_usefull += sheet.area_usefull
                all_sheets.append(sheet.length)
            overall += area_overall
            slopes_estimate.append(
                SlopeEstimateResponse(
                    name=slope.name,
                    area_full=slope.area,
                    area_overall=area_overall,
                    area_usefull=area_usefull
                )
            )
    else:
        slopes_estimate = None
    length_counts = dict(Counter(all_sheets))
    accessories = await AccessoriesDAO.find_all(session, project_id=project_id)
    if accessories:
        accessories_estimate = []
        for accessory in accessories:
            accessory_base = await Accessory_baseDAO.find_by_id(session, model_id=accessory.accessory_base_id)
            accessories_estimate.append(
                AccessoriesResponse(
                    id=accessory.id,
                    accessory_base=AccessoryBDResponse(
                        id=accessory_base.id,
                        name=accessory_base.name,
                        type=accessory_base.type,
                        parent_type=accessory_base.parent_type,
                        material=accessory_base.material,
                        length=accessory_base.length,
                        overlap=accessory_base.overlap,
                        price=accessory_base.price,
                        modulo=accessory_base.modulo
                    ),
                    lines_id=accessory.lines_id,
                    lines_length=accessory.lines_length,
                    quantity=accessory.quantity,
                    color=accessory.color
                )
            )
    else:
        accessories_estimate = None
    screws_estimate = [
        ScrewsEstimateResponse(
            id="69ad6260-9310-4245-92bb-d0c8728954f2",
            name='Саморез 4,8х35',
            amount=int(overall * 6),
            packege_amount=250,
            price=1500,
            ral=None
        )
    ]
    material = await MaterialsDAO.find_one_or_none(session, project_id=project.id)
    if material:
        material_estimate = MaterialEstimateResponse(
            name=material.name,
            material=material.material,
            color=material.color
        )
    else:
        material_estimate = None
    return EstimateResponse(
        id=project.id,
        name=project.name,
        address=project.address,
        step=project.step,
        datetime_created=project.datetime_created,
        roof=RoofEstimateResponse(
            id=roof.id,
            name=roof.name,
            type=roof.type,
            overall_width=roof.overall_width,
            useful_width=roof.useful_width,
            overlap=roof.overlap,
            len_wave=roof.len_wave,
            max_length=roof.max_length,
            min_length=roof.min_length,
            imp_sizes=roof.imp_sizes,
            price=None
        ),
        sheets_amount=length_counts,
        slopes=slopes_estimate,
        accessories=accessories_estimate,
        screws=screws_estimate,
        materials=material_estimate
    )


# @router.post(
#     "/projects/{project_id}/estimate/excel"
# )
# async def generate_excel_endpoint(
#     project_id: UUID4,
#     data: EstimateRequest,
#     user: Users = Depends(get_current_user),
#     session: AsyncSession = Depends(get_session)
# ):
#     """
#     Генерирует Excel-файл спецификации по оценке проекта.
#     """
#     project = await ProjectsDAO.find_by_id(session, model_id=project_id)
#     if not project or project.user_id != user.id:
#         raise ProjectNotFound

#     excel_file = await create_excel(data)
#     headers = {"Content-Disposition": "attachment; filename=specification.xlsx"}
#     return StreamingResponse(
#         excel_file,
#         media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#         headers=headers
#     )
