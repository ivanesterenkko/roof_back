from fastapi import APIRouter, Depends
from typing import Dict, List
from fastapi.responses import StreamingResponse
from pydantic import UUID4
from shapely.geometry import Polygon
from app.base.dao import Accessory_baseDAO, RoofsDAO
from app.base.schemas import AccessoryBDResponse, RoofResponse
from app.exceptions import CutoutNotFound, ProjectAlreadyExists, ProjectNotFound, ProjectStepLimit, RoofNotFound, SlopeNotFound, WrongSizes
from app.projects.draw import create_excel, draw_plan
from app.projects.rotate import rotate_slope
from app.projects.schemas import AboutResponse, AccessoriesEstimateResponse, AccessoriesRequest, AccessoriesResponse, CutoutResponse, EstimateRequest, EstimateResponse, LengthSlopeResponse, LineRequest, LineResponse, LineSlopeResponse, MaterialEstimateResponse, MaterialRequest, NodeRequest, PointCutoutResponse, PointData, PointSlopeResponse, ProjectRequest, ProjectResponse, RoofEstimateResponse, ScrewsEstimateResponse, SheetResponse, SlopeEstimateResponse, SlopeResponse, SlopeSizesRequest, SofitsEstimateResponce
from app.projects.dao import AccessoriesDAO, CutoutsDAO, LengthSlopeDAO, LinesDAO, LinesSlopeDAO, MaterialsDAO, PointsCutoutsDAO, PointsDAO, PointsSlopeDAO, ProjectsDAO, SheetsDAO, SlopesDAO
from app.projects.slope import create_figure, create_hole, create_sheets, find_slope, generate_slopes_length, get_next_length_name, get_next_name
from app.users.dependencies import get_current_user
from app.users.models import Users
import asyncio
from collections import Counter

router = APIRouter(prefix="/roofs", tags=["Roofs"])


@router.get("/projects", description="Get list of projects")
async def get_projects(user: Users = Depends(get_current_user)) -> List[AboutResponse]:
    projects = await ProjectsDAO.find_all(user_id=user.id)
    projects_response = []
    for project in projects:
        roof = await RoofsDAO.find_by_id(model_id=project.roof_id)
        projects_response.append(
            AboutResponse(
                id=project.id,
                name=project.name,
                address=project.address,
                step=project.step,
                datetime_created=project.datetime_created,
                roof=RoofResponse(
                    id=roof.id,
                    name=roof.name,
                    type=roof.type,
                    overall_width=roof.overall_width,
                    useful_width=roof.useful_width,
                    overlap=roof.overlap,
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
    user: Users = Depends(get_current_user)
) -> ProjectResponse:
    project = await ProjectsDAO.find_by_id(model_id=project_id)
    if not project:
        raise ProjectNotFound
    roof = await RoofsDAO.find_by_id(model_id=project.roof_id)
    if not roof:
        raise RoofNotFound
    lines = await LinesDAO.find_all(project_id=project_id)
    if lines:
        lines_response = [
            LineResponse(
                id=line.id,
                is_perimeter=line.is_perimeter,
                type=line.type,
                name=line.name,
                start=PointData(
                    x=line.start.x,
                    y=line.start.y
                    ),
                end=PointData(
                    x=line.end.x,
                    y=line.end.y
                    ),
                length=line.length
            ) for line in lines
        ]
    else:
        lines_response = None
    slopes = await SlopesDAO.find_all(project_id=project_id)
    if slopes:
        slope_response = []
        for slope in slopes:
            points_slope = await PointsSlopeDAO.find_all(slope_id=slope.id)
            points_response = [
                PointSlopeResponse(
                    id=point.id,
                    x=point.x,
                    y=point.y
                ) for point in points_slope
            ]
            lines_slope = await LinesSlopeDAO.find_all(slope_id=slope.id)
            lines_slope_response = [
                LineSlopeResponse(
                    id=line_slope.id,
                    parent_id=line_slope.parent_id,
                    name=line_slope.name,
                    number=line_slope.number,
                    start_id=line_slope.start_id,
                    start=PointData(
                        x=line_slope.start.x,
                        y=line_slope.start.y
                    ),
                    end_id=line_slope.end_id,
                    end=PointData(
                        x=line_slope.end.x,
                        y=line_slope.end.y
                    ),
                    length=line_slope.length
                ) for line_slope in lines_slope
            ]
            lines_length = await LengthSlopeDAO.find_all(slope_id=slope.id)
            length_slope_response = []
            for line_length in lines_length:
                if line_length.type == 0:
                    line_1 = await LinesDAO.find_by_id(line_length.line_slope_1.parent_id)
                    line_2 = await LinesDAO.find_by_id(line_length.line_slope_2.parent_id)
                    if line_1.start.x == line_1.end.x:
                        y_ar = abs(line_1.start.y - line_1.end.y)/2
                        if line_1.start.y > line_1.end.y:
                            y_ar = line_1.end.y + y_ar
                        else:
                             y_ar = line_1.start.y + y_ar
                        length_slope_response.append(
                            LengthSlopeResponse(
                                id=line_length.id,
                                name=line_length.name,
                                start=PointData(
                                    x=line_1.start.x,
                                    y=y_ar
                                ),
                                end=PointData(
                                    x=line_2.start.x,
                                    y=y_ar
                                ),
                                type=line_length.type,
                                point_1_id=line_length.point_1_id,
                                point_2_id=line_length.point_2_id,
                                line_slope_1_id=line_length.line_slope_1_id,
                                line_slope_2_id=line_length.line_slope_2_id,
                                length=line_length.length
                            )
                        )
                    else:
                        x_ar = abs(line_1.start.x - line_1.end.x)/2
                        if line_1.start.x > line_1.end.x:
                            x_ar = line_1.end.x + x_ar
                        else:
                             x_ar = line_1.start.x + x_ar
                        length_slope_response.append(
                            LengthSlopeResponse(
                                id=line_length.id,
                                name=line_length.name,
                                start=PointData(
                                    x=x_ar,
                                    y=line_1.start.y
                                ),
                                end=PointData(
                                    x=x_ar,
                                    y=line_2.start.y
                                ),
                                type=line_length.type,
                                point_1_id=line_length.point_1_id,
                                point_2_id=line_length.point_2_id,
                                line_slope_1_id=line_length.line_slope_1_id,
                                line_slope_2_id=line_length.line_slope_2_id,
                                length=line_length.length
                            )
                        )
                elif line_length.type == 1:
                    line = await LinesDAO.find_by_id(line_length.line_slope_1.parent_id)
                    point = await PointsDAO.find_by_id(line_length.point_1.parent_id)
                    if line.start.x == line.end.x:
                        length_slope_response.append(
                            LengthSlopeResponse(
                                id=line_length.id,
                                name=line_length.name,
                                start=PointData(
                                    x=line.start.x,
                                    y=point.y
                                ),
                                end=PointData(
                                    x=point.x,
                                    y=point.y
                                ),
                                type=line_length.type,
                                point_1_id=line_length.point_1_id,
                                point_2_id=line_length.point_2_id,
                                line_slope_1_id=line_length.line_slope_1_id,
                                line_slope_2_id=line_length.line_slope_2_id,
                                length=line_length.length
                            )
                        )
                    else:
                        length_slope_response.append(
                            LengthSlopeResponse(
                                id=line_length.id,
                                name=line_length.name,
                                start=PointData(
                                    x=point.x,
                                    y=line.start.y
                                ),
                                end=PointData(
                                    x=point.x,
                                    y=point.y
                                ),
                                type=line_length.type,
                                point_1_id=line_length.point_1_id,
                                point_2_id=line_length.point_2_id,
                                line_slope_1_id=line_length.line_slope_1_id,
                                line_slope_2_id=line_length.line_slope_2_id,
                                length=line_length.length
                            )
                        )
                else:
                    point_1 = await PointsDAO.find_by_id(line_length.point_1.parent_id)
                    point_2 = await PointsDAO.find_by_id(line_length.point_2.parent_id)
                    length_slope_response.append(
                        LengthSlopeResponse(
                            id=line_length.id,
                            name=line_length.name,
                            start=PointData(
                                x=point_1.x,
                                y=point_1.y
                            ),
                            end=PointData(
                                x=point_2.x,
                                y=point_2.y
                            ),
                            type=line_length.type,
                            point_1_id=line_length.point_1_id,
                            point_2_id=line_length.point_2_id,
                            line_slope_1_id=line_length.line_slope_1_id,
                            line_slope_2_id=line_length.line_slope_2_id,
                            length=line_length.length
                        )
                    )
            cutouts = await CutoutsDAO.find_all(slope_id=slope.id)
            if cutouts:
                cutouts_response = []
                for cutout in cutouts:
                    points_cutout = await PointsCutoutsDAO.find_all(cutout_id=cutout.id)
                    points_cutout_response = [
                        PointCutoutResponse(
                            id=point.id,
                            x=point.x,
                            y=point.y,
                            number=point.number
                        ) for point in points_cutout
                    ]
                    cutouts_response.append(
                        CutoutResponse(
                            id=cutout.id,
                            points=points_cutout_response
                        )
                    )
            else:
                cutouts_response = None
            sheets = await SheetsDAO.find_all(slope_id=slope.id)
            if sheets:
                sheets_response = [
                    SheetResponse(
                        id=sheet.id,
                        x_start=sheet.x_start,
                        y_start=sheet.y_start,
                        length=sheet.length,
                        area_overall=sheet.area_overall,
                        area_usefull=sheet.area_usefull
                        ) for sheet in sheets
                    ]
            else:
                sheets_response = None
            slope_response.append(SlopeResponse(
                id=slope.id,
                name=slope.name,
                area=slope.area,
                points=points_response,
                lines=lines_slope_response,
                length_line=length_slope_response,
                cutouts=cutouts_response,
                sheets=sheets_response
            ))
    else:
        slope_response = None
    accessories = await AccessoriesDAO.find_all(project_id=project_id)
    if accessories:
        accessories_response = []
        for accessory in accessories:
            accessory_base = await Accessory_baseDAO.find_by_id(accessory.accessory_base_id)
            accessories_response.append(
                AccessoriesResponse(
                    id=accessory.id,
                    accessory_base=AccessoryBDResponse(
                        id=accessory_base.id,
                        name=accessory_base.name,
                        type=accessory_base.type,
                        parent_type=accessory_base.parent_type,
                        price=accessory_base.price,
                        overlap=accessory_base.overlap,
                        length=accessory_base.length
                    ),
                    lines_id=accessory.lines_id,
                    lines_length=accessory.lines_length,
                    quantity=accessory.quantity
                )
            )
    else:
        accessories_response = None
    return ProjectResponse(
        id=project.id,
        name=project.name,
        address=project.address,
        step=project.step,
        datetime_created=project.datetime_created,
        roof=RoofResponse(
            id=roof.id,
            name=roof.name,
            type=roof.type,
            overall_width=roof.overall_width,
            useful_width=roof.useful_width,
            overlap=roof.overlap,
            max_length=roof.max_length,
            min_length=roof.min_length,
            imp_sizes=roof.imp_sizes
        ),
        lines=lines_response,
        slopes=slope_response,
        accessories=accessories_response
    )


@router.delete("/projects/{project_id}", description="Delete a roofing project")
async def delete_project(
    project_id: UUID4,
    user: Users = Depends(get_current_user)
) -> None:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    await ProjectsDAO.delete_(model_id=project_id)


@router.post("/projects", description="Create a roofing project")
async def add_project(
    project: ProjectRequest,
    user: Users = Depends(get_current_user)
) -> None:
    existing_project = await ProjectsDAO.find_one_or_none(name=project.name, user_id=user.id)
    if existing_project:
        raise ProjectAlreadyExists
    roof = await RoofsDAO.find_by_id(model_id=project.roof_id)
    if not roof:
        raise RoofNotFound
    project = await ProjectsDAO.add(
        name=project.name,
        address=project.address,
        roof_id=project.roof_id,
        user_id=user.id
    )
    return {"project_id": project.id}


@router.patch("/projects/{project_id}/step", description="Create a roofing project")
async def next_step(
    project_id: UUID4,
    user: Users = Depends(get_current_user)
) -> None:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    if project.step + 1 > 8:
        raise ProjectStepLimit
    await ProjectsDAO.update_(model_id=project_id, step=project.step+1)


@router.post("/projects/{project_id}/add_lines", description="Add lines of sketch")
async def add_lines(
    project_id: UUID4,
    lines: List[LineRequest],
    user: Users = Depends(get_current_user)
) -> None:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    existing_lines = await LinesDAO.find_all(project_id=project.id)
    existing_names = [line.name for line in existing_lines]
    existing_points = {}
    ex_points = await PointsDAO.find_all(project_id=project_id)
    for point in ex_points:
        if PointData(x=point.x, y=point.y) not in existing_points:
            existing_points[PointData(x=point.x, y=point.y)] = point.id
    for line in lines:
        line_name = get_next_name(existing_names)

        if line.start in existing_points:
            start_id = existing_points[line.start]
        else:
            point = await PointsDAO.add(
                x=line.start.x,
                y=line.start.y,
                project_id=project_id
            )
            start_id = point.id
            existing_points[line.start] = start_id

        if line.end in existing_points:
            end_id = existing_points[line.end]
        else:
            point = await PointsDAO.add(
                x=line.end.x,
                y=line.end.y,
                project_id=project_id
            )
            end_id = point.id
            existing_points[line.end] = end_id

        await LinesDAO.add(
            project_id=project_id,
            name=line_name,
            is_perimeter=line.is_perimeter,
            start_id=start_id,
            end_id=end_id,
        )
        existing_names.append(line_name)


@router.get("/projects/{project_id}/get_lines", description="Get lines")
async def get_lines(
      project_id: UUID4,
      user: Users = Depends(get_current_user)
      ) -> List[LineResponse]:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    lines = await LinesDAO.find_all(project_id=project_id)
    lines_response = []
    for line in lines:
        lines_response.append(LineResponse(
            id=line.id,
            is_perimeter=line.is_perimeter,
            type=line.type,
            name=line.name,
            start=PointData(x=line.start.x,
                            y=line.start.y),
            end=PointData(x=line.end.x,
                          y=line.end.y)
        ))
    return lines_response


@router.patch("/projects/{project_id}/lines/node_line", description="Add roof nodes")
async def add_node(
    project_id: UUID4,
    node_data: NodeRequest,
    user: Users = Depends(get_current_user)
) -> None:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    for line_id in node_data.lines_id:
        await LinesDAO.update_(model_id=line_id, type=node_data.type)


@router.patch("/projects/{project_id}/slopes/{slope_id}/add_sizes")
async def add_sizes(
    project_id: UUID4,
    slope_id: UUID4,
    data: SlopeSizesRequest,
    user: Users = Depends(get_current_user)
) -> None:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    slope = await SlopesDAO.find_by_id(slope_id)
    if not slope or slope.project_id != project_id:
        raise SlopeNotFound
    lines_data = {}
    lines_data_or = {}
    points_old = await PointsSlopeDAO.find_all(slope_id=slope_id)
    for line_d in data.lines:
        lines_data[line_d.id] = line_d.length
        lines_data_or[line_d.id] = line_d.length
    for length_line_d in data.length_line:
        id = length_line_d.id
        length = length_line_d.length
        await LengthSlopeDAO.update_(
            model_id=id,
            length=length
            )
        length_slope = await LengthSlopeDAO.find_by_id(id)
        if length_slope.type == 0:
            line = await LinesSlopeDAO.find_by_id(length_slope.line_slope_2_id)
            await PointsSlopeDAO.update_(
                model_id=line.start_id,
                y=length
            )
            await PointsSlopeDAO.update_(
                model_id=line.end_id,
                y=length
            )
        elif length_slope.type == 1:
            await PointsSlopeDAO.update_(
                model_id=length_slope.point_1_id,
                y=length
            )
        else:
            await PointsSlopeDAO.update_(
                model_id=length_slope.point_2_id,
                y=length
            )

    points = await PointsSlopeDAO.find_all(slope_id=slope_id)
    points_y = sorted(points, key=lambda point: point.y)
    points_x = sorted(points, key=lambda point: point.x)
    points_id = [point.id for point in points_x]
    points_y_id = [point.id for point in points_y]
    lines_v = []
    lines_g = []
    lines_n = []
    lines = await LinesSlopeDAO.find_all(slope_id=slope_id)
    lines_on_point: Dict[UUID4, List[UUID4]] = {}
    lines_v_on_point: Dict[UUID4, List[UUID4]] = {}
    lines_g_on_point: Dict[UUID4, List[UUID4]] = {}
    lines_n_on_point: Dict[UUID4, List[UUID4]] = {}
    for line in lines:
        if line.start.x == line.end.x:
            lines_v.append(line)
            if line.start_id not in lines_v_on_point:
                lines_v_on_point[line.start_id] = []
            if line.end_id not in lines_v_on_point:
                lines_v_on_point[line.end_id] = []
            lines_v_on_point[line.end_id].append(line.id)
            lines_v_on_point[line.start_id].append(line.id)
        elif line.start.y == line.end.y:
            lines_g.append(line)
            if line.start_id not in lines_g_on_point:
                lines_g_on_point[line.start_id] = []
            if line.end_id not in lines_g_on_point:
                lines_g_on_point[line.end_id] = []
            lines_g_on_point[line.end_id].append(line.id)
            lines_g_on_point[line.start_id].append(line.id)
        else:
            lines_n.append(line)
            if line.start_id not in lines_n_on_point:
                lines_n_on_point[line.start_id] = []
            if line.end_id not in lines_n_on_point:
                lines_n_on_point[line.end_id] = []
            lines_n_on_point[line.end_id].append(line.id)
            lines_n_on_point[line.start_id].append(line.id)
        if line.start_id not in lines_on_point:
            lines_on_point[line.start_id] = []
        if line.end_id not in lines_on_point:
            lines_on_point[line.end_id] = []
        lines_on_point[line.end_id].append(line.id)
        lines_on_point[line.start_id].append(line.id)
    for point_id in points_y_id:
        if point_id in lines_v_on_point:
            for line_id in lines_v_on_point[point_id]:
                if line_id in lines_data:
                    length = lines_data.pop(line_id, None)
                else:
                    continue
                line = await LinesSlopeDAO.find_by_id(line_id)
                if line.start.y < line.end.y:
                    point_n_id = line.end_id
                    if point_n_id in lines_g_on_point:
                        line_g = await LinesSlopeDAO.find_by_id(lines_g_on_point[point_n_id][0])
                        await PointsSlopeDAO.update_(
                                    model_id=line_g.end_id,
                                    y=round(line.start.y+length, 3)
                                )
                        await PointsSlopeDAO.update_(
                            model_id=line_g.start_id,
                            y=round(line.start.y+length, 3)
                        )
                    if point_n_id in lines_n_on_point:
                        line_n = await LinesSlopeDAO.find_by_id(lines_n_on_point[point_n_id][0])
                        if line_n.end_id < line_n.start_id:
                            await PointsSlopeDAO.update_(
                                        model_id=line_n.end_id,
                                        y=round(line.start.y+length, 3)
                                    )
                        else:
                            await PointsSlopeDAO.update_(
                                model_id=line_n.start_id,
                                y=round(line.start.y+length, 3)
                            )
                else:
                    point_n_id = line.start_id
                    if point_n_id in lines_g_on_point:
                        line_g = await LinesSlopeDAO.find_by_id(lines_g_on_point[point_n_id][0])
                        await PointsSlopeDAO.update_(
                                    model_id=line_g.end_id,
                                    y=round(line.end.y+length, 3)
                                )
                        await PointsSlopeDAO.update_(
                            model_id=line_g.start_id,
                            y=round(line.end.y+length, 3)
                        )
                    if point_n_id in lines_n_on_point:
                        line_n = await LinesSlopeDAO.find_by_id(lines_n_on_point[point_n_id][0])
                        if line_n.end_id < line_n.start_id:
                            await PointsSlopeDAO.update_(
                                        model_id=line_n.end_id,
                                        y=round(line.end.y+length, 3)
                                    )
                        else:
                            await PointsSlopeDAO.update_(
                                model_id=line_n.start_id,
                                y=round(line.end.y+length, 3)
                            )
    # for line in lines_g:
    #     if line.id in lines_data:
    #         length = lines_data.pop(line.id, None)
    #     else:
    #         continue
    #     if line.start.x < line.end.x:
    #         point_id = line.end_id
    #         await PointsSlopeDAO.update_(
    #             model_id=line.end_id,
    #             x=round(line.start.x+length, 3)
    #         )
    #     else:
    #         await PointsSlopeDAO.update_(
    #             model_id=line.start_id,
    #             x=round(line.end.x+length, 3)
    #         )
    # for line in lines_n:
    #     if line.id in lines_data:
    #         length = lines_data[line.id]
    #     else:
    #         continue
    #     if line.start.x < line.end.x:
    #         start = await PointsSlopeDAO.find_by_id(line.start_id)
    #         end = await PointsSlopeDAO.find_by_id(line.end_id)
    #         if start.y > end.y:
    #             hight = start.y - end.y
    #         else:
    #             hight = end.y - start.y
    #         new_x = round(((length)**2-(hight)**2)**0.5, 2)
    #         await PointsSlopeDAO.update_(
    #             model_id=end.id,
    #             x=start.x+new_x
    #         )
    #         update_id = end.id
    #     else:
    #         start = await PointsSlopeDAO.find_by_id(line.end_id)
    #         end = await PointsSlopeDAO.find_by_id(line.start_id)
    #         if start.y > end.y:
    #             hight = start.y - end.y
    #         else:
    #             hight = end.y - start.y
    #         new_x = round(((length)**2-(hight)**2)**0.5, 2)
    #         await PointsSlopeDAO.update_(
    #             model_id=start.id,
    #             x=start.x+new_x
    #         )
    #         update_id = start.id
    #     for line_id in lines_on_point[update_id]:
    #         if line_id == line.id:
    #             continue
    #         else:
    #             l = await LinesSlopeDAO.find_by_id(line_id)
    #             l_length = lines_data[l.id]
    #             if l.angle == 2:


    #     if point.id == line.end_id:
    #         if point.y > line.start.y:
    #             hight = point.y  - line.start.y
    #         else:
    #             hight = line.start.y - point.y
    #         new_x = round(((length)**2-(hight)**2)**0.5, 2)
    #         await PointsSlopeDAO.update_(
    #             model_id=line.start_id,
    #             x=point.x+new_x
    #         )
    for point_id in points_id:
        for line_id in lines_on_point[point_id]:
            line = await LinesSlopeDAO.find_by_id(line_id)
            if len(lines_data) == 0:
                point_max = point_id
            if line_id in lines_data:
                length = lines_data.pop(line_id, None)
            else:
                continue
            point = await PointsSlopeDAO.find_by_id(point_id)
            if line.angle == 2:
                if point.id == line.start_id:
                    await PointsSlopeDAO.update_(
                        model_id=line.end_id,
                        x=round(point.x+length, 3)
                    )
                else:
                    await PointsSlopeDAO.update_(
                        model_id=line.start_id,
                        x=round(point.x+length, 3)
                    )
            elif line.angle == 1:
                continue
            else:
                if point.id == line.start_id:
                    if point.y > line.end.y:
                        hight = point.y - line.end.y
                    else:
                        hight = line.end.y - point.y
                    new_x = round(((length)**2-(hight)**2)**0.5, 3)
                    await PointsSlopeDAO.update_(
                        model_id=line.end_id,
                        x=round(point.x+new_x, 3)
                    )
                if point.id == line.end_id:
                    if point.y > line.start.y:
                        hight = point.y  - line.start.y
                    else:
                        hight = line.start.y - point.y
                    new_x = round(((length)**2-(hight)**2)**0.5, 3)
                    await PointsSlopeDAO.update_(
                        model_id=line.start_id,
                        x=round(point.x+new_x, 3)
                    )
    for line_id in lines_on_point[point_max]:
        length = lines_data_or[line_id]
        line = await LinesSlopeDAO.find_by_id(line_id)
        if line.angle == 2:
            line_length = abs(line.start.x - line.end.x)
            if abs(line_length - length) > 0:
                point_stack = []
                if len(lines_n) == 0:
                    break
                div_x = round((line_length - length)/len(lines_n), 3)
                if line.start.x < line.end.x:
                    point_1_id = line.end_id
                    for line_id in lines_on_point[point_1_id]:
                        if line_id == line.id:
                            continue
                        l = await LinesSlopeDAO.find_by_id(line_id)
                        if l.angle == 1:
                            point_1 = await PointsSlopeDAO.update_(
                                model_id=l.end_id,
                                x=round(line.start.x+length, 3)
                            )
                            point_2 = await PointsSlopeDAO.update_(
                                model_id=l.start_id,
                                x=round(line.start.x+length, 3)
                            )
                            point_stack.append(point_1.id)
                            point_stack.append(point_2.id)
                        else:
                            point_1 = await PointsSlopeDAO.update_(
                                model_id=point_1_id,
                                x=round(line.start.x+length, 3)
                            )
                            point_stack.append(point_1.id)
                            point_stack.append(line.start_id)
                else:
                    point_1_id = line.start_id
                    for line_id in lines_on_point[point_1_id]:
                        if line_id == line.id:
                            continue
                        l = await LinesSlopeDAO.find_by_id(line_id)
                        if l.angle == 1:
                            point_1 = await PointsSlopeDAO.update_(
                                model_id=l.end_id,
                                x=round(line.end.x+length, 3)
                            )
                            point_2 = await PointsSlopeDAO.update_(
                                model_id=l.start_id,
                                x=round(line.end.x+length, 3)
                            )
                            point_stack.append(point_1.id)
                            point_stack.append(point_2.id)
                        else:
                            point_1 = await PointsSlopeDAO.update_(
                                model_id=point_1_id,
                                x=round(line.end.x+length, 3)
                            )
                            point_stack.append(point_1.id)
                            point_stack.append(line.end_id)
                x_max = point_1.x
                for point_id in points_id:
                    if point_id in point_stack:
                        continue
                    point = await PointsSlopeDAO.find_by_id(point_id)
                    q = 0
                    for line_id in lines_on_point[point_id]:
                        line = await LinesSlopeDAO.find_by_id(line_id)
                        if line.type == 'ендова':
                            q += 1
                        if line.type == 'карниз':
                            q += 1
                    if point.y == 0 or q == 2 or point.x == x_max:
                        point_stack.append(point.id)
                        continue
                    else:
                        await PointsSlopeDAO.update_(
                            model_id=point.id,
                            x=round(point.x - div_x, 3)
                        )
                break
    lines_slope = await LinesSlopeDAO.find_all(slope_id=slope_id)
    length_slopes = await LengthSlopeDAO.find_all(slope_id=slope_id)
    for line_slope in lines_slope:
        line = await LinesSlopeDAO.update_(
            model_id=line_slope.id,
            length=round(((line_slope.start.x - line_slope.end.x) ** 2 + (line_slope.start.y - line_slope.end.y) ** 2) ** 0.5, 3)
        )
        # if abs(line.length - lines_data_or[line.id]) > 3:
        #     for line in lines_slope:
        #         await LinesSlopeDAO.update_(
        #             model_id=line_slope.id,
        #             length=None
        #             )
        #         await LinesDAO.update_(
        #             model_id=line.parent_id,
        #             length=None
        #         )
        #     for point in points_old:
        #         await PointsSlopeDAO.update_(
        #             model_id=point.id,
        #             x=point.x,
        #             y=point.y
        #         )
        #     for length_slope in length_slopes:
        #         await LengthSlopeDAO.update_(
        #             model_id=length_slope.id,
        #             length=None
        #         )
        #     raise WrongSizes
        await LinesDAO.update_(
            model_id=line.parent_id,
            length=line.length
        )


@router.delete("/projects/{project_id}/slopes", description="Delete roof slopes")
async def delete_slope(
    project_id: UUID4,
    user: Users = Depends(get_current_user)
):
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    slopes = await SlopesDAO.find_all(project_id=project_id)
    for slope in slopes:
        await SlopesDAO.delete_(model_id=slope.id)


@router.post("/projects/{project_id}/slopes", description="Add roof slopes")
async def add_slope(
    project_id: UUID4,
    user: Users = Depends(get_current_user)
) -> None:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound

    lines = await LinesDAO.find_all(project_id=project.id)
    existing_names = []
    slopes = find_slope(lines)
    for slope in slopes:
        lines = []
        for line_id in slope:
            lines.append(
                await LinesDAO.find_by_id(line_id)
            )
        existing_points = {}
        slope_name = get_next_name(existing_names)
        existing_names.append(slope_name)
        new_slope = await SlopesDAO.add(
            name=slope_name,
            project_id=project.id
        )
        new_lines = rotate_slope(lines)
        count = 1
        for line in new_lines:
            if line.start.id in existing_points:
                start_id = existing_points[line.start.id]
                start = await PointsSlopeDAO.find_by_id(start_id)
            else:
                point = await PointsSlopeDAO.add(
                    x=line.start.x,
                    y=line.start.y,
                    parent_id=line.start.id,
                    slope_id=new_slope.id
                )
                start = point
                start_id = point.id
                existing_points[line.start.id] = start_id

            if line.end.id in existing_points:
                end_id = existing_points[line.end.id]
                end = await PointsSlopeDAO.find_by_id(end_id)
            else:
                point = await PointsSlopeDAO.add(
                    x=line.end.x,
                    y=line.end.y,
                    parent_id=line.end.id,
                    slope_id=new_slope.id
                )
                end = point
                end_id = point.id
                existing_points[line.end.id] = end_id
            angle = 0
            if end.x == start.x:
                angle = 1
            if end.y == start.y:
                angle = 2
            await LinesSlopeDAO.add(
                name=line.name,
                parent_id=line.id,
                type=line.type,
                start_id=start_id,
                end_id=end_id,
                slope_id=new_slope.id,
                number=count,
                angle=angle
            )
            count += 1
        lines_slope = await LinesSlopeDAO.find_all(
            slope_id=new_slope.id
        )
        points_slope = await PointsSlopeDAO.find_all(
            slope_id=new_slope.id
        )
        lengths_slope = generate_slopes_length(
            lines=lines_slope,
            points=points_slope
            )
        existing_names_length = []
        for length_slope in lengths_slope:
            name = get_next_length_name(existing_names_length)
            existing_names_length.append(name)
            if length_slope[0] == 0:
                await LengthSlopeDAO.add(
                    name=name,
                    type=length_slope[0],
                    line_slope_1_id=length_slope[1],
                    line_slope_2_id=length_slope[2],
                    slope_id=new_slope.id
                )
            elif length_slope[0] == 1:
                await LengthSlopeDAO.add(
                    name=name,
                    type=length_slope[0],
                    line_slope_1_id=length_slope[1],
                    point_1_id=length_slope[2],
                    slope_id=new_slope.id
                )
            else:
                await LengthSlopeDAO.add(
                    name=name,
                    type=length_slope[0],
                    point_2_id=length_slope[1],
                    point_1_id=length_slope[2],
                    slope_id=new_slope.id
                )



@router.patch("/projects/{project_id}/slopes/{slope_id}/lines_slope/{line_slope_id}", description="Update length of line for slope")
async def update_line_slope(
    project_id: UUID4,
    slope_id: UUID4,
    line_slope_id: UUID4,
    length: float,
    user: Users = Depends(get_current_user)
) -> None:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    slope = await SlopesDAO.find_by_id(slope_id)
    if not slope or slope.project_id != project_id:
        raise SlopeNotFound
    line = await LinesSlopeDAO.find_by_id(line_slope_id)
    await LinesDAO.update_(
        model_id=line.parent_id,
        length=length
    )
    if line.start.x < line.end.x and line.start.y < line.end.y:
        point_id = line.start_id
    else:
        point_id = line.end_id
    point = await PointsSlopeDAO.find_by_id(point_id)
    if line.start.y == line.end.y:
        if point.id == line.start_id:
            await PointsSlopeDAO.update_(
                model_id=line.end_id,
                x=point.x+length
            )
        else:
            await PointsSlopeDAO.update_(
                model_id=line.start_id,
                x=point.x+length
            )
    elif line.start.x == line.end.x:
        if point.id == line.start_id:
            await PointsSlopeDAO.update_(
                model_id=line.end_id,
                y=point.y+length
            )
        else:
            await PointsSlopeDAO.update_(
                model_id=line.start_id,
                y=point.y+length
            )
    else:
        if point.id == line.start_id:
            if point.y > line.end.y:
                hight = point.y - line.end.y
            else:
                hight = line.end.y - point.y
            new_x = round(((length)**2-(hight)**2)**0.5, 2)
            await PointsSlopeDAO.update_(
                model_id=line.end_id,
                x=point.x+new_x
            )
        if point.id == line.end_id:
            if point.y > line.start.y:
                hight = point.y  - line.end.y
            else:
                hight = line.start.y - point.y
            new_x = round(((length)**2-(hight)**2)**0.5, 2)
            await PointsSlopeDAO.update_(
                model_id=line.start_id,
                x=point.x+new_x
            )
    lines_slope = await LinesSlopeDAO.find_all(slope_id=slope_id)
    for line_slope in lines_slope:
        line = await LinesSlopeDAO.update_(
            model_id=line_slope.id,
            length=round(((line_slope.start.x - line_slope.end.x) ** 2 + (line_slope.start.y - line_slope.end.y) ** 2) ** 0.5, 2)
        )
        await LinesDAO.update_(
            model_id=line.parent_id,
            length=line.length
        )
    length_lines = await LengthSlopeDAO.find_all(slope_id=slope_id)
    for length_slope in length_lines:
        if length_slope.type == 0:
            line_1 = await LinesSlopeDAO.find_by_id(length_slope.line_slope_1_id)
            line_2 = await LinesSlopeDAO.find_by_id(length_slope.line_slope_2_id)
            await LengthSlopeDAO.update_(
                model_id=line.id,
                length=round(abs(line_1.start.y - line_2.start.y), 2)
            )
        elif length_slope.type == 1:
            point = await PointsSlopeDAO.find_by_id(length_slope.point_1_id)
            line = await LinesSlopeDAO.find_by_id(length_slope.line_slope_1_id)
            await LengthSlopeDAO.update_(
                model_id=line.id,
                length=round(abs(line.start.y - point.y), 2)
            )
        else:
            point_1 = await PointsSlopeDAO.find_by_id(length_slope.point_1_id)
            point_2 = await PointsSlopeDAO.find_by_id(length_slope.point_2_id)
            await LengthSlopeDAO.update_(
                model_id=line.id,
                length=round(abs(point_1.y - point_2.y), 2)
            )


@router.patch("/projects/{project_id}/slopes/{slope_id}/lengths_slope/{length_slope_id}", description="Update length of line for slope")
async def update_length_slope(
    project_id: UUID4,
    slope_id: UUID4,
    length_slope_id: UUID4,
    length: float,
    user: Users = Depends(get_current_user)
) -> None:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    slope = await SlopesDAO.find_by_id(slope_id)
    if not slope or slope.project_id != project_id:
        raise SlopeNotFound
    length_slope = await LengthSlopeDAO.find_by_id(length_slope_id)
    await LengthSlopeDAO.update_(
        model_id=length_slope.id,
        length=length
        )
    if length_slope.type == 0:
        line = await LinesSlopeDAO.find_by_id(length_slope.line_slope_2_id)
        await PointsSlopeDAO.update_(
            model_id=line.start_id,
            y=length
        )
        await PointsSlopeDAO.update_(
            model_id=line.end_id,
            y=length
        )
    elif length_slope.type == 1:
        await PointsSlopeDAO.update_(
            model_id=length_slope.point_1_id,
            y=length
        )
    else:
        await PointsSlopeDAO.update_(
            model_id=length_slope.point_2_id,
            y=length
        )
    lines_slope = await LinesSlopeDAO.find_all(slope_id=slope_id)
    for line_slope in lines_slope:
        line = await LinesSlopeDAO.update_(
            model_id=line_slope.id,
            length=round(((line_slope.start.x - line_slope.end.x) ** 2 + (line_slope.start.y - line_slope.end.y) ** 2) ** 0.5, 2)
        )
        await LinesDAO.update_(
            model_id=line.parent_id,
            length=line.length
        )
    length_lines = await LengthSlopeDAO.find_all(slope_id=slope_id)
    for length_slope in length_lines:
        if length_slope.type == 0:
            line_1 = await LinesSlopeDAO.find_by_id(length_slope.line_slope_1_id)
            line_2 = await LinesSlopeDAO.find_by_id(length_slope.line_slope_2_id)
            await LengthSlopeDAO.update_(
                model_id=line.id,
                length=round(abs(line_1.start.y - line_2.start.y), 2)
            )
        elif length_slope.type == 1:
            point = await PointsSlopeDAO.find_by_id(length_slope.point_1_id)
            line = await LinesSlopeDAO.find_by_id(length_slope.line_slope_1_id)
            await LengthSlopeDAO.update_(
                model_id=line.id,
                length=round(abs(line.start.y - point.y), 2)
            )
        else:
            point_1 = await PointsSlopeDAO.find_by_id(length_slope.point_1_id)
            point_2 = await PointsSlopeDAO.find_by_id(length_slope.point_2_id)
            await LengthSlopeDAO.update_(
                model_id=line.id,
                length=round(abs(point_1.y - point_2.y), 2)
            )


@router.patch("/projects/{project_id}/slopes/{slope_id}/points_slope/{point_slope_id}", description="Update coords point for slope")
async def update_point_slope(
    project_id: UUID4,
    slope_id: UUID4,
    point_slope_id: UUID4,
    point: PointData,
    user: Users = Depends(get_current_user)
) -> None:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    slope = await SlopesDAO.find_by_id(slope_id)
    if not slope or slope.project_id != project_id:
        raise SlopeNotFound
    await PointsSlopeDAO.update_(
        model_id=point_slope_id,
        x=point.x,
        y=point.y
    )
    lines_slope = await LinesSlopeDAO.find_all(slope_id=slope_id)
    for line_slope in lines_slope:
        line = await LinesSlopeDAO.update_(
            model_id=line_slope.id,
            length=round(((line_slope.start.x - line_slope.end.x) ** 2 + (line_slope.start.y - line_slope.end.y) ** 2) ** 0.5, 2)
        )
        await LinesDAO.update_(
            model_id=line.parent_id,
            length=line.length
        )
    length_lines = await LengthSlopeDAO.find_all(slope_id=slope_id)
    for length_slope in length_lines:
        if length_slope.type == 0:
            line_1 = await LinesSlopeDAO.find_by_id(length_slope.line_slope_1_id)
            line_2 = await LinesSlopeDAO.find_by_id(length_slope.line_slope_2_id)
            await LengthSlopeDAO.update_(
                model_id=line.id,
                length=round(abs(line_1.start.y - line_2.start.y), 2)
            )
        elif length_slope.type == 1:
            point = await PointsSlopeDAO.find_by_id(length_slope.point_1_id)
            line = await LinesSlopeDAO.find_by_id(length_slope.line_slope_1_id)
            await LengthSlopeDAO.update_(
                model_id=line.id,
                length=round(abs(line.start.y - point.y), 2)
            )
        else:
            point_1 = await PointsSlopeDAO.find_by_id(length_slope.point_1_id)
            point_2 = await PointsSlopeDAO.find_by_id(length_slope.point_2_id)
            await LengthSlopeDAO.update_(
                model_id=line.id,
                length=round(abs(point_1.y - point_2.y), 2)
            )


@router.delete("/projects/{project_id}/add_line/slopes/{slope_id}/cutounts/{cutout_id}", description="Delete cutout")
async def delete_cutout(
    slope_id: UUID4,
    cutout_id: UUID4,
    user: Users = Depends(get_current_user)
) -> None:
    cutout = await CutoutsDAO.find_by_id(cutout_id)
    if not cutout or cutout.slope_id != slope_id:
        raise SlopeNotFound
    await CutoutsDAO.delete_(model_id=cutout_id)


@router.post("/projects/{project_id}/slopes/{slope_id}/cutouts", description="Add cutout")
async def add_cutout(
    project_id: UUID4,
    slope_id: UUID4,
    points: List[PointData],
    user: Users = Depends(get_current_user)
) -> None:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    slope = await SlopesDAO.find_by_id(slope_id)
    if not slope or slope.project_id != project_id:
        raise SlopeNotFound
    cutout = await CutoutsDAO.add(slope_id=slope_id)
    count = 1
    for point in points:
        await PointsCutoutsDAO.add(
            x=point.x,
            y=point.y,
            number=count,
            cutout_id=cutout.id
        )
        count += 1


@router.patch("/projects/{project_id}/slopes/{slope_id}/cutouts/{cutout_id}", description="Update cutout")
async def update_cutout(
    project_id: UUID4,
    slope_id: UUID4,
    cutout_id: UUID4,
    points_cutout: List[PointCutoutResponse],
    user: Users = Depends(get_current_user)
) -> None:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    slope = await SlopesDAO.find_by_id(slope_id)
    if not slope or slope.project_id != project_id:
        raise SlopeNotFound
    cutout = await CutoutsDAO.find_by_id(cutout_id)
    if not cutout:
        raise CutoutNotFound
    for point in points_cutout:
        await PointsCutoutsDAO.update_(
            model_id=point.id,
            x=point.x,
            y=point.y
        )



# @router.get("/projects/{project_id}/slopes/{slope_id}/sheets", description="View sheets for slope")
# async def get_sheets(
#     project_id: UUID4,
#     slope_id: UUID4,
#     user: Users = Depends(get_current_user)
# ) -> List[SheetResponse]:
#     project = await ProjectsDAO.find_by_id(project_id)
#     if not project or project.user_id != user.id:
#         raise ProjectNotFound

#     slope = await SlopesDAO.find_by_id(slope_id)
#     if not slope or slope.project_id != project_id:
#         raise SlopeNotFound
#     sheets = await SheetsDAO.find_all(slope_id=slope_id)
#     return [SheetResponse(
#         id=sheet.id,
#         sheet_x_start=sheet.x_start,
#         sheet_y_start=sheet.y_start,
#         sheet_length=sheet.length,
#         sheet_area_overall=sheet.area_overall,
#         sheet_area_usefull=sheet.area_usefull
#         ) for sheet in sheets]


@router.delete("/projects/{project_id}/add_line/slopes/{slope_id}/sheets/{sheet_id}", description="Delete sheet")
async def delete_sheet(
    slope_id: UUID4,
    project_id: UUID4,
    sheet_id: UUID4,
    user: Users = Depends(get_current_user)
) -> None:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound

    slope = await SlopesDAO.find_by_id(slope_id)
    if not slope or slope.project_id != project_id:
        raise SlopeNotFound
    await SheetsDAO.delete_(model_id=sheet_id)


@router.delete("/projects/{project_id}/add_line/slopes/{slope_id}/sheets", description="Delete sheets")
async def delete_sheets(
    slope_id: UUID4,
    project_id: UUID4,
    user: Users = Depends(get_current_user)
) -> None:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    slope = await SlopesDAO.find_by_id(slope_id)
    if not slope or slope.project_id != project_id:
        raise SlopeNotFound
    sheets_old = await SheetsDAO.find_all(slope_id=slope_id)
    for sheet in sheets_old:
        await SheetsDAO.delete_(sheet.id)


@router.patch("/projects/{project_id}/slopes/{slope_id}/sheet/{sheet_id}", description="Add roof sheet for slope")
async def add_sheet(
    project_id: UUID4,
    slope_id: UUID4,
    sheet_id: UUID4,
    is_down: bool,
    user: Users = Depends(get_current_user)
) -> None:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    roof = await RoofsDAO.find_by_id(project.roof_id)
    slope = await SlopesDAO.find_by_id(slope_id)
    if not slope or slope.project_id != project_id:
        raise SlopeNotFound
    sheet = await SheetsDAO.find_by_id(sheet_id)
    if sheet.length <= roof.max_length:
        new_length_1 = roof.overlap + roof.overlap
        new_length_2 = sheet.length - roof.overlap
    if is_down:
        await SheetsDAO.add(
            x_start=sheet.x_start,
            y_start=sheet.y_start,
            length=new_length_1,
            area_overall=new_length_1*roof.overall_width,
            area_usefull=new_length_1*roof.useful_width,
            slope_id=slope_id
        )
        await SheetsDAO.update_(
            model_id=sheet.id,
            y_start=sheet.length - new_length_2,
            length=new_length_2,
        )
    else:
        await SheetsDAO.add(
            x_start=sheet.x_start,
            y_start=sheet.length - new_length_1,
            length=new_length_1,
            area_overall=new_length_1*roof.overall_width,
            area_usefull=new_length_1*roof.useful_width,
            slope_id=slope_id
        )
        await SheetsDAO.update_(
            model_id=sheet.id,
            length=new_length_2,
        )


@router.post("/projects/{project_id}/slopes/{slope_id}/sheets", description="Calculate roof sheets for slope")
async def add_sheets(
    project_id: UUID4,
    slope_id: UUID4,
    user: Users = Depends(get_current_user)
) -> None:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound

    slope = await SlopesDAO.find_by_id(slope_id)
    if not slope or slope.project_id != project_id:
        raise SlopeNotFound
    cutouts_slope = await CutoutsDAO.find_all(slope_id=slope_id)
    lines = await LinesSlopeDAO.find_all(slope_id=slope_id)
    lines = sorted(lines, key=lambda line: line.number)
    cutouts = []
    for cutout in cutouts_slope:
        points_cutout_slope = await PointsCutoutsDAO.find_all(cutout_id=cutout.id)
        points_cutout_slope = sorted(points_cutout_slope, key=lambda point: point.number)
        points_cutout = [
            (point.x, point.y) for point in points_cutout_slope
        ]
        cutouts.append(points_cutout)
    figure = create_figure(lines, cutouts)
    area = figure.area
    slope = await SlopesDAO.update_(model_id=slope_id, area=area)
    roof = await RoofsDAO.find_by_id(project.roof_id)
    sheets = await create_sheets(figure, roof, 0, 0)
    for sheet in sheets:
        await SheetsDAO.add(
            x_start=sheet[0],
            y_start=sheet[1],
            length=sheet[2],
            area_overall=sheet[3],
            area_usefull=sheet[4],
            slope_id=slope_id
        )


@router.patch("/projects/{project_id}/slopes/{slope_id}/update_length_sheets", description="Calculate roof sheets for slope")
async def update_length_sheets(
    project_id: UUID4,
    slope_id: UUID4,
    sheets_id: List[UUID4],
    length: float,
    user: Users = Depends(get_current_user)
) -> None:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    roof = await RoofsDAO.find_by_id(project.roof_id)
    slope = await SlopesDAO.find_by_id(slope_id)
    if not slope or slope.project_id != project_id:
        raise SlopeNotFound
    sheets = [await SheetsDAO.find_by_id(sheet_id) for sheet_id in sheets_id]
    for sheet in sheets:
        new_length = sheet.length + length
        if new_length <= roof.max_length:
            await SheetsDAO.update_(
                model_id=sheet.id,
                length=new_length,
                area_overall=new_length*roof.overall_width,
                area_usefull=new_length*roof.useful_width
            )


@router.patch("/projects/{project_id}/slopes/{slope_id}/offset_sheets")
async def offset_sheets(
    project_id: UUID4,
    slope_id: UUID4,
    data: PointData,
    user: Users = Depends(get_current_user)
) -> None:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    slope = await SlopesDAO.find_by_id(slope_id)
    if not slope or slope.project_id != project_id:
        raise SlopeNotFound
    sheets_old = await SheetsDAO.find_all(slope_id=slope_id)
    for sheet in sheets_old:
        await SheetsDAO.delete_(sheet.id)
    cutouts_slope = await CutoutsDAO.find_all(slope_id=slope_id)
    lines = await LinesSlopeDAO.find_all(slope_id=slope_id)
    lines = sorted(lines, key=lambda line: line.number)
    cutouts = []
    for cutout in cutouts_slope:
        points_cutout_slope = await PointsCutoutsDAO.find_all(cutout_id=cutout.id)
        points_cutout_slope = sorted(points_cutout_slope, key=lambda point: point.number)
        points_cutout = [
            (point.x, point.y) for point in points_cutout_slope
        ]
        cutouts.append(points_cutout)
    figure = create_figure(lines, cutouts)
    area = figure.area
    slope = await SlopesDAO.update_(model_id=slope_id, area=area)
    roof = await RoofsDAO.find_by_id(project.roof_id)
    sheets = await create_sheets(
        figure=figure,
        roof=roof,
        del_x=data.x,
        del_y=data.y
        )
    for sheet in sheets:
        await SheetsDAO.add(
            x_start=sheet[0],
            y_start=sheet[1],
            length=sheet[2],
            area_overall=sheet[3],
            area_usefull=sheet[4],
            slope_id=slope_id
        )


@router.patch("/projects/{project_id}/slopes/{slope_id}/overlay", description="Calculate roof sheets for slope")
async def update_sheets_overlay(
    project_id: UUID4,
    slope_id: UUID4,
    user: Users = Depends(get_current_user)
) -> None:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    slope = await SlopesDAO.find_by_id(slope_id)
    if not slope or slope.project_id != project_id:
        raise SlopeNotFound
    roof = await RoofsDAO.find_by_id(project.roof_id)
    sheets = await SheetsDAO.find_all(slope_id=slope_id)
    previous_sheet = None
    for sheet in sheets:
        result = None
        if previous_sheet is None:
            previous_sheet = sheet
        elif previous_sheet.x_start == sheet.x_start and previous_sheet.y_start + previous_sheet.length > sheet.y_start:
            new_length = previous_sheet.length + sheet.length - roof.overlap
            if new_length <= roof.max_length:
                result = await SheetsDAO.update_(model_id=previous_sheet.id, length=new_length)
                await SheetsDAO.delete_(model_id=sheet.id)
        if result is None:
            previous_sheet = sheet
        else:
            previous_sheet = result


@router.delete("/projects/{project_id}/accessories/{accessory_id}", description="Delete accessory")
async def delete_accessory(
    accessory_id: UUID4,
    project_id: UUID4,
    user: Users = Depends(get_current_user)
) -> None:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    accessory = await AccessoriesDAO.find_by_id(accessory_id)
    if not accessory or accessory.project_id != project_id:
        raise ProjectNotFound
    await AccessoriesDAO.delete_(model_id=accessory_id)


@router.post("/projects/{project_id}/accessories", description="Calculate roof sheets for slope")
async def add_accessory(
    project_id: UUID4,
    accessory: AccessoriesRequest,
    user: Users = Depends(get_current_user)
) -> None:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    lines = await asyncio.gather(*[LinesDAO.find_by_id(line_id) for line_id in accessory.lines_id])
    lines_length = 0
    for line in lines:
        lines_length += line.length
    accessory_base = await Accessory_baseDAO.find_by_id(accessory.accessory_id)
    quantity = lines_length // accessory_base.length
    if lines_length % accessory_base.length > accessory_base.overlap:
        quantity += 1
    await AccessoriesDAO.add(
        lines_id=accessory.lines_id,
        lines_length=lines_length,
        quantity=quantity,
        accessory_base_id=accessory.accessory_id,
        project_id=project_id
    )


@router.patch("/projects/{project_id}/accessories/{accessory_id}", description="Calculate roof sheets for slope")
async def update_accessory(
    project_id: UUID4,
    accessory_id: UUID4,
    accessory: AccessoriesRequest,
    user: Users = Depends(get_current_user)
) -> None:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    lines = await asyncio.gather(*[LinesDAO.find_by_id(line_id) for line_id in accessory.lines_id])
    lines_length = 0
    for line in lines:
        lines_length += line.length
    accessory_base = await Accessory_baseDAO.find_by_id(accessory.accessory_id)
    quantity = lines_length // accessory_base.length
    if lines_length % accessory_base.length > accessory_base.overlap:
        quantity += 1
    await AccessoriesDAO.update_(
        model_id=accessory_id,
        lines_id=accessory.lines_id,
        lines_length=lines_length,
        quantity=quantity,
        accessory_base_id=accessory.accessory_id,
        project_id=project_id
    )


@router.post("/projects/{project_id}/materials")
async def add_material(
    project_id: UUID4,
    materials: MaterialRequest,
    user: Users = Depends(get_current_user)
) -> None:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    await MaterialsDAO.add(
        project_id=project_id,
        name=materials.name,
        material=materials.material,
        color=materials.color
        )


@router.get("/projects/{project_id}/estimate", description="View accessories")
async def get_estimate(
    project_id: UUID4,
    user: Users = Depends(get_current_user)
) -> EstimateResponse:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    slopes = await SlopesDAO.find_all(project_id=project_id)
    roof = await RoofsDAO.find_by_id(project.roof_id)
    slopes_area = 0
    all_sheets = []
    overall = 0
    if slopes:
        slopes_estimate = []
        for slope in slopes:
            area_overall = 0
            area_usefull = 0
            slopes_area += slope.area
            sheets = await SheetsDAO.find_all(slope_id=slope.id)
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
    length_counts = Counter(all_sheets)
    accessories = await AccessoriesDAO.find_all(project_id=project_id)
    if accessories:
        accessories_estimate = []
        for accessory in accessories:
            accessory_base = await Accessory_baseDAO.find_by_id(accessory.accessory_base_id)
            accessories_estimate.append(
                AccessoriesResponse(
                    id=accessory.id,
                    accessory_base=AccessoryBDResponse(
                        id=accessory_base.id,
                        name=accessory_base.name,
                        type=accessory_base.type,
                        parent_type=accessory_base.parent_type,
                        price=accessory_base.price,
                        overlap=accessory_base.overlap,
                        length=accessory_base.length
                    ),
                    lines_id=accessory.lines_id,
                    lines_length=accessory.lines_length,
                    quantity=accessory.quantity,
                    ral=None,
                    color=None
                )
            )
    else:
        accessories_estimate = None
    screws_estimate = [
        ScrewsEstimateResponse(
            id="69ad6260-9310-4245-92bb-d0c8728954f2",
            name='Саморез 4,8х35',
            amount=int(overall*6),
            packege_amount=250,
            price=1500,
            ral=None
        )
    ]
    sheets_amount_dict = dict(length_counts)
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
            max_length=roof.max_length,
            min_length=roof.min_length,
            imp_sizes=roof.imp_sizes,
            price=None
        ),
        sheets_amount=sheets_amount_dict,
        slopes=slopes_estimate,
        accessories=accessories_estimate,
        screws=screws_estimate,
    )


@router.post("/projects/{project_id}/estimate/excel")
async def generate_excel_endpoint(
      project_id: UUID4,
      data: EstimateRequest,
      user: Users = Depends(get_current_user)):
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound

    excel_file = await create_excel(data)
    headers = {
        "Content-Disposition": "attachment; filename=specification.xlsx"
    }
    return StreamingResponse(excel_file, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)



# @router.get("/projects/{project_id}/step")
# async def get_project_on_step(
#     project_id: UUID4,
#     user: Users = Depends(get_current_user)
# ):
#     project = await ProjectsDAO.find_by_id(project_id)
#     if not project or project.user_id != user.id:
#         raise ProjectNotFound
#     match project.step:
#         case 1:
#             return Step1Response(
#                 id=project.id,
#                 project_name=project.name,
#                 project_address=project.address,
#                 roof_id=project.roof_id
#             )
#         case 2:
#             lines = await LinesDAO.find_all(project_id=project_id)
#             filtered_lines = [line for line in lines if line.type in ['Perimeter', 'Карниз']]
#             if not filtered_lines:
#                 return None
#             else:
#                 return [
#                     LineResponse(
#                         id=line.id,
#                         line_type=line.type,
#                         line_name=line.name,
#                         line_length=line.length,
#                         coords=LineData(start=PointData(x=line.x_start, y=line.y_start),
#                                         end=PointData(x=line.x_end, y=line.y_end))
#                     ) for line in filtered_lines
#                 ]
#         case 3:
#             slopes = await SlopesDAO.find_all(project_id=project_id)
#             lines = await LinesDAO.find_all(project_id=project_id)
#             lines_plan = [
#                 LineResponse(
#                     id=line.id,
#                     line_type=line.type,
#                     line_name=line.name,
#                     line_length=line.length,
#                     coords=LineData(start=PointData(x=line.x_start, y=line.y_start),
#                                     end=PointData(x=line.x_end, y=line.y_end))
#                 ) for line in lines
#                 ]
#             slopes_data = []
#             for slope in slopes:
#                 lines = await LinesSlopeDAO.find_all(slope_id=slope.id)
#                 lines_data = [LineSlopeResponse(
#                     id=line.id,
#                     line_id=line.line_id,
#                     line_name=line.name,
#                     line_length=line.length,
#                     coords=LineData(start=PointData(x=line.x_start, y=line.y_start),
#                                     end=PointData(x=line.x_end, y=line.y_end)
#                                     )
#                     ) for line in lines
#                 ]
#                 slopes_data.append(SlopeResponse(
#                     id=slope.id,
#                     slope_length=slope.length,
#                     slope_name=slope.name,
#                     slope_area=slope.area if slope.area is not None else None,
#                     lines=lines_data
#                     )
#                 )
#             return Step3Response(
#                 general_plan=lines_plan,
#                 slopes=slopes_data
#             )
#         case 4:
#             lines = await LinesDAO.find_all(project_id=project_id)
#             return [LineResponse(
#                 id=line.id,
#                 line_type=line.type,
#                 line_name=line.name,
#                 line_length=line.length,
#                 coords=LineData(start=PointData(x=line.x_start, y=line.y_start),
#                                 end=PointData(x=line.x_end, y=line.y_end))
#             ) for line in lines
#             ]
#         case 5:
#             lines = await LinesDAO.find_all(project_id=project_id)
#             lines_data = [LineResponse(
#                 id=line.id,
#                 line_type=line.type,
#                 line_name=line.name,
#                 line_length=line.length,
#                 coords=LineData(start=PointData(x=line.x_start, y=line.y_start),
#                                 end=PointData(x=line.x_end, y=line.y_end))
#             ) for line in lines
#             ]
#             slopes = await SlopesDAO.find_all(project_id=project_id)
#             slopes_data = []
#             for slope in slopes:
#                 lines_slope = await LinesSlopeDAO.find_all(slope_id=slope.id)
#                 cutouts = await CutoutsDAO.find_all(slope_id=slope.id)
#                 cutouts_data = [CutoutResponse(
#                     id=cutout.id,
#                     cutout_name=cutout.name,
#                     cutout_points=[PointData(x=x, y=y) for x, y in zip(cutout.x_coords, cutout.y_coords)]
#                 ) for cutout in cutouts]
#                 lines_slope_data = [LineSlopeResponse(
#                     id=line.id,
#                     line_id=line.line_id,
#                     line_name=line.name,
#                     line_length=line.length,
#                     coords=LineData(start=PointData(x=line.x_start, y=line.y_start),
#                                     end=PointData(x=line.x_end, y=line.y_end))
#                     ) for line in lines_slope]
#                 sheets = await SheetsDAO.find_all(slope_id=slope.id)
#                 sheets_data = [SheetResponse(
#                     id=sheet.id,
#                     sheet_x_start=sheet.x_start,
#                     sheet_y_start=sheet.y_start,
#                     sheet_length=sheet.length,
#                     sheet_area_overall=sheet.area_overall,
#                     sheet_area_usefull=sheet.area_usefull
#                 ) for sheet in sheets]
#                 slopes_data.append(SlopeSheetsResponse(
#                     id=slope.id,
#                     slope_name=slope.name,
#                     slope_length=slope.length,
#                     slope_area=slope.area,
#                     lines=lines_slope_data,
#                     sheets=sheets_data,
#                     cutouts=cutouts_data
#                 ))
#             return Step5Response(
#                 general_plan=lines_data,
#                 slopes=slopes_data
#             )
#         case 6:
#             lines = await LinesDAO.find_all(project_id=project_id)
#             accessories = await AccessoriesDAO.find_all(project_id=project_id)

#             return Step6Response(
#                 lines=[
#                     LineResponse(
#                         id=line.id,
#                         line_type=line.type,
#                         line_name=line.name,
#                         line_length=line.length,
#                         coords=LineData(start=PointData(x=line.x_start, y=line.y_start),
#                                         end=PointData(x=line.x_end, y=line.y_end))
#                     ) for line in lines],
#                 accessories=[
#                     AccessoriesResponse(
#                         id=accessory.id,
#                         type=accessory.type,
#                         accessory_name=accessory.name,
#                         lines_id=accessory.lines_id,
#                         lines_length=accessory.lines_length,
#                         length=accessory.length,
#                         width=accessory.width if accessory.width is not None else None,
#                         amount=accessory.quantity
#                         ) for accessory in accessories
#                 ]
#             )
#         case 7:
#             materials = await MaterialsDAO.find_all(project_id=project_id)
#             return [
#                 MaterialEstimateResponse(
#                     name=material.name,
#                     material=material.material,
#                     color=material.color
#                 ) for material in materials
#             ]
#         case 8:
#             slopes = await SlopesDAO.find_all(project_id=project_id)
#             materials = await MaterialsDAO.find_all(project_id=project_id)
#             roof = await RoofsDAO.find_by_id(project.roof_id)
#             materials_estimate = [
#                 MaterialEstimateResponse(
#                     name=material.name,
#                     material=material.material,
#                     color=material.color
#                 ) for material in materials
#             ]
#             slopes_estimate = []
#             slopes_area = 0
#             all_sheets = []
#             overall = 0
#             plans_data = []
#             for slope in slopes:
#                 lines = await LinesSlopeDAO.find_all(slope_id=slope.id)
#                 area_overall = 0
#                 area_usefull = 0
#                 slopes_area += slope.area
#                 sheets = await SheetsDAO.find_all(slope_id=slope.id)
#                 plans_data.append(draw_plan(lines, sheets, roof.overall_width))
#                 for sheet in sheets:
#                     area_overall += sheet.area_overall
#                     area_usefull += sheet.area_usefull
#                     all_sheets.append(sheet.length)
#                 overall += area_overall
#                 slopes_estimate.append(
#                     SlopeEstimateResponse(
#                         slope_name=slope.name,
#                         slope_length=slope.length,
#                         slope_area=slope.area,
#                         area_overall=area_overall,
#                         area_usefull=area_usefull
#                     )
#                 )
#             length_counts = Counter(all_sheets)
#             accessories = await AccessoriesDAO.find_all(project_id=project_id)
#             accessories_estimate = []
#             sofits_estimate = []
#             for accessory in accessories:
#                 if 'Софит' in accessory.name or 'профиль' in accessory.name:
#                     sofits_estimate.append(
#                         SofitsEstimateResponce(
#                             name=accessory.name,
#                             type=accessory.type,
#                             length=accessory.length,
#                             width=accessory.width,
#                             overall_length=accessory.lines_length,
#                             amount=accessory.quantity,
#                             price=700
#                         ))
#                 else:
#                     accessories_estimate.append(
#                         AccessoriesEstimateResponse(
#                             name=accessory.name,
#                             type=accessory.type,
#                             length=accessory.length,
#                             overall_length=accessory.lines_length,
#                             amount=accessory.quantity,
#                             price=300
#                         ))
#             screws_estimate = [
#                 ScrewsEstimateResponse(
#                     name='Саморез 4,8х35',
#                     amount=int(overall*6),
#                     packege_amount=250,
#                     price=1500
#                 )
#             ]
#             sheets_amount_dict = dict(length_counts)

#             return EstimateResponse(
#                 project_name=project.name,
#                 project_address=project.address,
#                 materials=materials_estimate,
#                 roof_base=RoofEstimateResponse(
#                     roof_name=roof.name,
#                     roof_type=roof.type,
#                     price=650,
#                     roof_overall_width=roof.overall_width,
#                     roof_useful_width=roof.useful_width,
#                     roof_overlap=roof.overlap,
#                     roof_max_length=roof.max_length,
#                     roof_max_length_standart=roof.max_length-roof.overlap),
#                 sheets_amount=sheets_amount_dict,
#                 slopes=slopes_estimate,
#                 accessories=accessories_estimate,
#                 sofits=sofits_estimate,
#                 screws=screws_estimate,
#                 sheets_extended=plans_data
#             )


# @router.get("/projects/{project_id}/step_number")
# async def get_project_in_step(
#     project_id: UUID4,
#     step_number: int,
#     user: Users = Depends(get_current_user)
# ):
#     project = await ProjectsDAO.find_by_id(project_id)
#     if not project or project.user_id != user.id:
#         raise ProjectNotFound
#     if step_number > 8:
#         raise ProjectStepLimit
#     elif step_number > project.step:
#         raise ProjectStepError
#     match step_number:
#         case 1:
#             return Step1Response(
#                 id=project.id,
#                 project_name=project.name,
#                 project_address=project.address,
#                 roof_id=project.roof_id
#             )
#         case 2:
#             lines = await LinesDAO.find_all(project_id=project_id)
#             filtered_lines = [line for line in lines if line.type in ['Perimeter', 'Карниз']]
#             if not filtered_lines:
#                 return None
#             else:
#                 return [
#                     LineResponse(
#                         id=line.id,
#                         line_type=line.type,
#                         line_name=line.name,
#                         line_length=line.length,
#                         coords=LineData(start=PointData(x=line.x_start, y=line.y_start),
#                                         end=PointData(x=line.x_end, y=line.y_end))
#                     ) for line in filtered_lines
#                 ]
#         case 3:
#             slopes = await SlopesDAO.find_all(project_id=project_id)
#             lines = await LinesDAO.find_all(project_id=project_id)
#             lines_plan = [
#                 LineResponse(
#                     id=line.id,
#                     line_type=line.type,
#                     line_name=line.name,
#                     line_length=line.length,
#                     coords=LineData(start=PointData(x=line.x_start, y=line.y_start),
#                                     end=PointData(x=line.x_end, y=line.y_end))
#                 ) for line in lines
#                 ]
#             slopes_data = []
#             for slope in slopes:
#                 lines = await LinesSlopeDAO.find_all(slope_id=slope.id)
#                 lines_data = [LineSlopeResponse(
#                     id=line.id,
#                     line_id=line.line_id,
#                     line_name=line.name,
#                     line_length=line.length,
#                     coords=LineData(start=PointData(x=line.x_start, y=line.y_start),
#                                     end=PointData(x=line.x_end, y=line.y_end)
#                                     )
#                     ) for line in lines
#                 ]
#                 slopes_data.append(SlopeResponse(
#                     id=slope.id,
#                     slope_name=slope.name,
#                     slope_length=slope.length,
#                     slope_area=slope.area if slope.area is not None else None,
#                     lines=lines_data
#                     )
#                 )
#             return Step3Response(
#                 general_plan=lines_plan,
#                 slopes=slopes_data
#             )
#         case 4:
#             lines = await LinesDAO.find_all(project_id=project_id)
#             return [LineResponse(
#                 id=line.id,
#                 line_type=line.type,
#                 line_name=line.name,
#                 line_length=line.length,
#                 coords=LineData(start=PointData(x=line.x_start, y=line.y_start),
#                                 end=PointData(x=line.x_end, y=line.y_end))
#             ) for line in lines
#             ]
#         case 5:
#             lines = await LinesDAO.find_all(project_id=project_id)
#             lines_data = [LineResponse(
#                 id=line.id,
#                 line_type=line.type,
#                 line_name=line.name,
#                 line_length=line.length,
#                 coords=LineData(start=PointData(x=line.x_start, y=line.y_start),
#                                 end=PointData(x=line.x_end, y=line.y_end))
#             ) for line in lines
#             ]
#             slopes = await SlopesDAO.find_all(project_id=project_id)
#             slopes_data = []
#             for slope in slopes:
#                 lines_slope = await LinesSlopeDAO.find_all(slope_id=slope.id)
#                 cutouts = await CutoutsDAO.find_all(slope_id=slope.id)
#                 cutouts_data = [CutoutResponse(
#                     id=cutout.id,
#                     cutout_name=cutout.name,
#                     cutout_points=[PointData(x=x, y=y) for x, y in zip(cutout.x_coords, cutout.y_coords)]
#                 ) for cutout in cutouts]
#                 lines_slope_data = [LineSlopeResponse(
#                     id=line.id,
#                     line_id=line.line_id,
#                     line_name=line.name,
#                     line_length=line.length,
#                     coords=LineData(start=PointData(x=line.x_start, y=line.y_start),
#                                     end=PointData(x=line.x_end, y=line.y_end))
#                     ) for line in lines_slope]
#                 sheets = await SheetsDAO.find_all(slope_id=slope.id)
#                 sheets_data = [SheetResponse(
#                     id=sheet.id,
#                     sheet_x_start=sheet.x_start,
#                     sheet_y_start=sheet.y_start,
#                     sheet_length=sheet.length,
#                     sheet_area_overall=sheet.area_overall,
#                     sheet_area_usefull=sheet.area_usefull
#                 ) for sheet in sheets]
#                 slopes_data.append(SlopeSheetsResponse(
#                     id=slope.id,
#                     slope_length=slope.length,
#                     slope_name=slope.name,
#                     slope_area=slope.area,
#                     lines=lines_slope_data,
#                     sheets=sheets_data,
#                     cutouts=cutouts_data
#                 ))
#             return Step5Response(
#                 general_plan=lines_data,
#                 slopes=slopes_data
#             )
#         case 6:
#             lines = await LinesDAO.find_all(project_id=project_id)
#             accessories = await AccessoriesDAO.find_all(project_id=project_id)

#             return Step6Response(
#                 lines=[
#                     LineResponse(
#                         id=line.id,
#                         line_type=line.type,
#                         line_name=line.name,
#                         line_length=line.length,
#                         coords=LineData(start=PointData(x=line.x_start, y=line.y_start),
#                                         end=PointData(x=line.x_end, y=line.y_end))
#                     ) for line in lines],
#                 accessories=[
#                     AccessoriesResponse(
#                         id=accessory.id,
#                         type=accessory.type,
#                         accessory_name=accessory.name,
#                         lines_id=accessory.lines_id,
#                         lines_length=accessory.lines_length,
#                         length=accessory.length,
#                         width=accessory.width if accessory.width is not None else None,
#                         amount=accessory.quantity
#                         ) for accessory in accessories]
#             )
#         case 7:
#             materials = await MaterialsDAO.find_all(project_id=project_id)
#             return [
#                 MaterialEstimateResponse(
#                     name=material.name,
#                     material=material.material,
#                     color=material.color
#                 ) for material in materials
#             ]
#         case 8:
#             slopes = await SlopesDAO.find_all(project_id=project_id)
#             materials = await MaterialsDAO.find_all(project_id=project_id)
#             roof = await RoofsDAO.find_by_id(project.roof_id)
#             materials_estimate = [
#                 MaterialEstimateResponse(
#                     name=material.name,
#                     material=material.material,
#                     color=material.color
#                 ) for material in materials
#             ]
#             slopes_estimate = []
#             slopes_area = 0
#             all_sheets = []
#             overall = 0
#             plans_data = []
#             for slope in slopes:
#                 lines = await LinesSlopeDAO.find_all(slope_id=slope.id)
#                 area_overall = 0
#                 area_usefull = 0
#                 slopes_area += slope.area
#                 sheets = await SheetsDAO.find_all(slope_id=slope.id)
#                 plans_data.append(draw_plan(lines, sheets, roof.overall_width))
#                 for sheet in sheets:
#                     area_overall += sheet.area_overall
#                     area_usefull += sheet.area_usefull
#                     all_sheets.append(sheet.length)
#                 overall += area_overall
#                 slopes_estimate.append(
#                     SlopeEstimateResponse(
#                         slope_name=slope.name,
#                         slope_length=slope.length,
#                         slope_area=slope.area,
#                         area_overall=area_overall,
#                         area_usefull=area_usefull
#                     )
#                 )
#             length_counts = Counter(all_sheets)
#             accessories = await AccessoriesDAO.find_all(project_id=project_id)
#             accessories_estimate = []
#             sofits_estimate = []
#             for accessory in accessories:
#                 if 'Софит' in accessory.name or 'профиль' in accessory.name:
#                     sofits_estimate.append(
#                         SofitsEstimateResponce(
#                             name=accessory.name,
#                             type=accessory.type,
#                             length=accessory.length,
#                             width=accessory.width,
#                             overall_length=accessory.lines_length,
#                             amount=accessory.quantity,
#                             price=700
#                         ))
#                 else:
#                     accessories_estimate.append(
#                         AccessoriesEstimateResponse(
#                             name=accessory.name,
#                             type=accessory.type,
#                             length=accessory.length,
#                             overall_length=accessory.lines_length,
#                             amount=accessory.quantity,
#                             price=300
#                         ))
#             screws_estimate = [
#                 ScrewsEstimateResponse(
#                     name='Саморез 4,8х35',
#                     amount=int(overall*6),
#                     packege_amount=250,
#                     price=1500
#                 )
#             ]
#             sheets_amount_dict = dict(length_counts)

#             return EstimateResponse(
#                 project_name=project.name,
#                 project_address=project.address,
#                 materials=materials_estimate,
#                 roof_base=RoofEstimateResponse(
#                     roof_name=roof.name,
#                     roof_type=roof.type,
#                     price=650,
#                     roof_overall_width=roof.overall_width,
#                     roof_useful_width=roof.useful_width,
#                     roof_overlap=roof.overlap,
#                     roof_max_length=roof.max_length,
#                     roof_max_length_standart=roof.max_length-roof.overlap),
#                 sheets_amount=sheets_amount_dict,
#                 slopes=slopes_estimate,
#                 accessories=accessories_estimate,
#                 sofits=sofits_estimate,
#                 screws=screws_estimate,
#                 sheets_extended=plans_data
# )
