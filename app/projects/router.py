from fastapi import APIRouter, Depends, Request
from typing import List
from fastapi.responses import StreamingResponse
from pydantic import UUID4
from shapely.geometry import Polygon
from app.base.dao import RoofsDAO
from app.exceptions import ProjectAlreadyExists, ProjectNotFound, ProjectStepError, ProjectStepLimit, SlopeNotFound
from app.projects.draw import create_excel, draw_plan
from app.projects.rotate import rotate_slope
from app.projects.schemas import AccessoriesEstimateResponse, AccessoriesRequest, AccessoriesResponse, CutoutResponse, EstimateRequest, EstimateResponse, GenPlanResponse, LengthSlopeResponse, LineData, LineResponse, LineSlopeGenPlanResponse, LineSlopeResponse, LinesData, MaterialEstimateResponse, MaterialRequest, MaterialResponse, NewSheetRequest, NodeRequest, PointData, ProjectRequest, ProjectResponse, RoofEstimateResponse, ScrewsEstimateResponse, SheetResponse, SlopeEstimateResponse, SlopeGenPlanResponse, SlopeResponse, SlopeSheetsResponse, SlopeSizesRequest, SofitsEstimateResponce, Step1Response, Step3Response, Step6Response, Step5Response
from app.projects.dao import AccessoriesDAO, CutoutsDAO, LengthSlopeDAO, LinesDAO, LinesSlopeDAO, MaterialsDAO, PointsDAO, PointsSlopeDAO, ProjectsDAO, SheetsDAO, SlopesDAO
from app.projects.slope import create_hole, create_sheets, find_slope, get_next_name, process_lines_and_generate_slopes
from app.users.dependencies import get_current_user
from app.users.models import Users
import asyncio
from collections import Counter

router = APIRouter(prefix="/roofs", tags=["Roofs"])


@router.get("/projects", description="Get list of projects")
async def get_projects(user: Users = Depends(get_current_user)) -> List[ProjectResponse]:
    projects = await ProjectsDAO.find_all(user_id=user.id)
    return [
        ProjectResponse(
            id=project.id,
            project_name=project.name,
            project_step=project.step,
            datetime_created=project.datetime_created
        ) for project in projects
    ]


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
) -> ProjectResponse:
    existing_project = await ProjectsDAO.find_one_or_none(name=project.name, user_id=user.id)
    if existing_project:
        raise ProjectAlreadyExists

    new_project = await ProjectsDAO.add(
        name=project.name,
        address=project.address,
        roof_id=project.roof_id,
        user_id=user.id
    )
    return ProjectResponse(
        id=new_project.id,
        project_name=new_project.name,
        project_step=new_project.step,
        datetime_created=new_project.datetime_created
    )


@router.patch("/projects/{project_id}/step", description="Create a roofing project")
async def next_step(
    project_id: UUID4,
    user: Users = Depends(get_current_user)
) -> ProjectResponse:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    if project.step + 1 > 8:
        raise ProjectStepLimit
    new_project = await ProjectsDAO.update_(model_id=project_id, step=project.step+1)
    return ProjectResponse(
        id=new_project.id,
        project_name=new_project.name,
        project_step=new_project.step,
        datetime_created=new_project.datetime_created
    )


@router.get("/projects/{project_id}/step")
async def get_project_on_step(
    project_id: UUID4,
    user: Users = Depends(get_current_user)
):
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    match project.step:
        case 1:
            return Step1Response(
                id=project.id,
                project_name=project.name,
                project_address=project.address,
                roof_id=project.roof_id
            )
        case 2:
            lines = await LinesDAO.find_all(project_id=project_id)
            filtered_lines = [line for line in lines if line.type in ['Perimeter', 'Карниз']]
            if not filtered_lines:
                return None
            else:
                return [
                    LineResponse(
                        id=line.id,
                        line_type=line.type,
                        line_name=line.name,
                        line_length=line.length,
                        coords=LineData(start=PointData(x=line.x_start, y=line.y_start),
                                        end=PointData(x=line.x_end, y=line.y_end))
                    ) for line in filtered_lines
                ]
        case 3:
            slopes = await SlopesDAO.find_all(project_id=project_id)
            lines = await LinesDAO.find_all(project_id=project_id)
            lines_plan = [
                LineResponse(
                    id=line.id,
                    line_type=line.type,
                    line_name=line.name,
                    line_length=line.length,
                    coords=LineData(start=PointData(x=line.x_start, y=line.y_start),
                                    end=PointData(x=line.x_end, y=line.y_end))
                ) for line in lines
                ]
            slopes_data = []
            for slope in slopes:
                lines = await LinesSlopeDAO.find_all(slope_id=slope.id)
                lines_data = [LineSlopeResponse(
                    id=line.id,
                    line_id=line.line_id,
                    line_name=line.name,
                    line_length=line.length,
                    coords=LineData(start=PointData(x=line.x_start, y=line.y_start),
                                    end=PointData(x=line.x_end, y=line.y_end)
                                    )
                    ) for line in lines
                ]
                slopes_data.append(SlopeResponse(
                    id=slope.id,
                    slope_length=slope.length,
                    slope_name=slope.name,
                    slope_area=slope.area if slope.area is not None else None,
                    lines=lines_data
                    )
                )
            return Step3Response(
                general_plan=lines_plan,
                slopes=slopes_data
            )
        case 4:
            lines = await LinesDAO.find_all(project_id=project_id)
            return [LineResponse(
                id=line.id,
                line_type=line.type,
                line_name=line.name,
                line_length=line.length,
                coords=LineData(start=PointData(x=line.x_start, y=line.y_start),
                                end=PointData(x=line.x_end, y=line.y_end))
            ) for line in lines
            ]
        case 5:
            lines = await LinesDAO.find_all(project_id=project_id)
            lines_data = [LineResponse(
                id=line.id,
                line_type=line.type,
                line_name=line.name,
                line_length=line.length,
                coords=LineData(start=PointData(x=line.x_start, y=line.y_start),
                                end=PointData(x=line.x_end, y=line.y_end))
            ) for line in lines
            ]
            slopes = await SlopesDAO.find_all(project_id=project_id)
            slopes_data = []
            for slope in slopes:
                lines_slope = await LinesSlopeDAO.find_all(slope_id=slope.id)
                cutouts = await CutoutsDAO.find_all(slope_id=slope.id)
                cutouts_data = [CutoutResponse(
                    id=cutout.id,
                    cutout_name=cutout.name,
                    cutout_points=[PointData(x=x, y=y) for x, y in zip(cutout.x_coords, cutout.y_coords)]
                ) for cutout in cutouts]
                lines_slope_data = [LineSlopeResponse(
                    id=line.id,
                    line_id=line.line_id,
                    line_name=line.name,
                    line_length=line.length,
                    coords=LineData(start=PointData(x=line.x_start, y=line.y_start),
                                    end=PointData(x=line.x_end, y=line.y_end))
                    ) for line in lines_slope]
                sheets = await SheetsDAO.find_all(slope_id=slope.id)
                sheets_data = [SheetResponse(
                    id=sheet.id,
                    sheet_x_start=sheet.x_start,
                    sheet_y_start=sheet.y_start,
                    sheet_length=sheet.length,
                    sheet_area_overall=sheet.area_overall,
                    sheet_area_usefull=sheet.area_usefull
                ) for sheet in sheets]
                slopes_data.append(SlopeSheetsResponse(
                    id=slope.id,
                    slope_name=slope.name,
                    slope_length=slope.length,
                    slope_area=slope.area,
                    lines=lines_slope_data,
                    sheets=sheets_data,
                    cutouts=cutouts_data
                ))
            return Step5Response(
                general_plan=lines_data,
                slopes=slopes_data
            )
        case 6:
            lines = await LinesDAO.find_all(project_id=project_id)
            accessories = await AccessoriesDAO.find_all(project_id=project_id)

            return Step6Response(
                lines=[
                    LineResponse(
                        id=line.id,
                        line_type=line.type,
                        line_name=line.name,
                        line_length=line.length,
                        coords=LineData(start=PointData(x=line.x_start, y=line.y_start),
                                        end=PointData(x=line.x_end, y=line.y_end))
                    ) for line in lines],
                accessories=[
                    AccessoriesResponse(
                        id=accessory.id,
                        type=accessory.type,
                        accessory_name=accessory.name,
                        lines_id=accessory.lines_id,
                        lines_length=accessory.lines_length,
                        length=accessory.length,
                        width=accessory.width if accessory.width is not None else None,
                        amount=accessory.quantity
                        ) for accessory in accessories
                ]
            )
        case 7:
            materials = await MaterialsDAO.find_all(project_id=project_id)
            return [
                MaterialEstimateResponse(
                    name=material.name,
                    material=material.material,
                    color=material.color
                ) for material in materials
            ]
        case 8:
            slopes = await SlopesDAO.find_all(project_id=project_id)
            materials = await MaterialsDAO.find_all(project_id=project_id)
            roof = await RoofsDAO.find_by_id(project.roof_id)
            materials_estimate = [
                MaterialEstimateResponse(
                    name=material.name,
                    material=material.material,
                    color=material.color
                ) for material in materials
            ]
            slopes_estimate = []
            slopes_area = 0
            all_sheets = []
            overall = 0
            plans_data = []
            for slope in slopes:
                lines = await LinesSlopeDAO.find_all(slope_id=slope.id)
                area_overall = 0
                area_usefull = 0
                slopes_area += slope.area
                sheets = await SheetsDAO.find_all(slope_id=slope.id)
                plans_data.append(draw_plan(lines, sheets, roof.overall_width))
                for sheet in sheets:
                    area_overall += sheet.area_overall
                    area_usefull += sheet.area_usefull
                    all_sheets.append(sheet.length)
                overall += area_overall
                slopes_estimate.append(
                    SlopeEstimateResponse(
                        slope_name=slope.name,
                        slope_length=slope.length,
                        slope_area=slope.area,
                        area_overall=area_overall,
                        area_usefull=area_usefull
                    )
                )
            length_counts = Counter(all_sheets)
            accessories = await AccessoriesDAO.find_all(project_id=project_id)
            accessories_estimate = []
            sofits_estimate = []
            for accessory in accessories:
                if 'Софит' in accessory.name or 'профиль' in accessory.name:
                    sofits_estimate.append(
                        SofitsEstimateResponce(
                            name=accessory.name,
                            type=accessory.type,
                            length=accessory.length,
                            width=accessory.width,
                            overall_length=accessory.lines_length,
                            amount=accessory.quantity,
                            price=700
                        ))
                else:
                    accessories_estimate.append(
                        AccessoriesEstimateResponse(
                            name=accessory.name,
                            type=accessory.type,
                            length=accessory.length,
                            overall_length=accessory.lines_length,
                            amount=accessory.quantity,
                            price=300
                        ))
            screws_estimate = [
                ScrewsEstimateResponse(
                    name='Саморез 4,8х35',
                    amount=int(overall*6),
                    packege_amount=250,
                    price=1500
                )
            ]
            sheets_amount_dict = dict(length_counts)

            return EstimateResponse(
                project_name=project.name,
                project_address=project.address,
                materials=materials_estimate,
                roof_base=RoofEstimateResponse(
                    roof_name=roof.name,
                    roof_type=roof.type,
                    price=650,
                    roof_overall_width=roof.overall_width,
                    roof_useful_width=roof.useful_width,
                    roof_overlap=roof.overlap,
                    roof_max_length=roof.max_length,
                    roof_max_length_standart=roof.max_length-roof.overlap),
                sheets_amount=sheets_amount_dict,
                slopes=slopes_estimate,
                accessories=accessories_estimate,
                sofits=sofits_estimate,
                screws=screws_estimate,
                sheets_extended=plans_data
            )


@router.get("/projects/{project_id}/step_number")
async def get_project_in_step(
    project_id: UUID4,
    step_number: int,
    user: Users = Depends(get_current_user)
):
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    if step_number > 8:
        raise ProjectStepLimit
    elif step_number > project.step:
        raise ProjectStepError
    match step_number:
        case 1:
            return Step1Response(
                id=project.id,
                project_name=project.name,
                project_address=project.address,
                roof_id=project.roof_id
            )
        case 2:
            lines = await LinesDAO.find_all(project_id=project_id)
            filtered_lines = [line for line in lines if line.type in ['Perimeter', 'Карниз']]
            if not filtered_lines:
                return None
            else:
                return [
                    LineResponse(
                        id=line.id,
                        line_type=line.type,
                        line_name=line.name,
                        line_length=line.length,
                        coords=LineData(start=PointData(x=line.x_start, y=line.y_start),
                                        end=PointData(x=line.x_end, y=line.y_end))
                    ) for line in filtered_lines
                ]
        case 3:
            slopes = await SlopesDAO.find_all(project_id=project_id)
            lines = await LinesDAO.find_all(project_id=project_id)
            lines_plan = [
                LineResponse(
                    id=line.id,
                    line_type=line.type,
                    line_name=line.name,
                    line_length=line.length,
                    coords=LineData(start=PointData(x=line.x_start, y=line.y_start),
                                    end=PointData(x=line.x_end, y=line.y_end))
                ) for line in lines
                ]
            slopes_data = []
            for slope in slopes:
                lines = await LinesSlopeDAO.find_all(slope_id=slope.id)
                lines_data = [LineSlopeResponse(
                    id=line.id,
                    line_id=line.line_id,
                    line_name=line.name,
                    line_length=line.length,
                    coords=LineData(start=PointData(x=line.x_start, y=line.y_start),
                                    end=PointData(x=line.x_end, y=line.y_end)
                                    )
                    ) for line in lines
                ]
                slopes_data.append(SlopeResponse(
                    id=slope.id,
                    slope_name=slope.name,
                    slope_length=slope.length,
                    slope_area=slope.area if slope.area is not None else None,
                    lines=lines_data
                    )
                )
            return Step3Response(
                general_plan=lines_plan,
                slopes=slopes_data
            )
        case 4:
            lines = await LinesDAO.find_all(project_id=project_id)
            return [LineResponse(
                id=line.id,
                line_type=line.type,
                line_name=line.name,
                line_length=line.length,
                coords=LineData(start=PointData(x=line.x_start, y=line.y_start),
                                end=PointData(x=line.x_end, y=line.y_end))
            ) for line in lines
            ]
        case 5:
            lines = await LinesDAO.find_all(project_id=project_id)
            lines_data = [LineResponse(
                id=line.id,
                line_type=line.type,
                line_name=line.name,
                line_length=line.length,
                coords=LineData(start=PointData(x=line.x_start, y=line.y_start),
                                end=PointData(x=line.x_end, y=line.y_end))
            ) for line in lines
            ]
            slopes = await SlopesDAO.find_all(project_id=project_id)
            slopes_data = []
            for slope in slopes:
                lines_slope = await LinesSlopeDAO.find_all(slope_id=slope.id)
                cutouts = await CutoutsDAO.find_all(slope_id=slope.id)
                cutouts_data = [CutoutResponse(
                    id=cutout.id,
                    cutout_name=cutout.name,
                    cutout_points=[PointData(x=x, y=y) for x, y in zip(cutout.x_coords, cutout.y_coords)]
                ) for cutout in cutouts]
                lines_slope_data = [LineSlopeResponse(
                    id=line.id,
                    line_id=line.line_id,
                    line_name=line.name,
                    line_length=line.length,
                    coords=LineData(start=PointData(x=line.x_start, y=line.y_start),
                                    end=PointData(x=line.x_end, y=line.y_end))
                    ) for line in lines_slope]
                sheets = await SheetsDAO.find_all(slope_id=slope.id)
                sheets_data = [SheetResponse(
                    id=sheet.id,
                    sheet_x_start=sheet.x_start,
                    sheet_y_start=sheet.y_start,
                    sheet_length=sheet.length,
                    sheet_area_overall=sheet.area_overall,
                    sheet_area_usefull=sheet.area_usefull
                ) for sheet in sheets]
                slopes_data.append(SlopeSheetsResponse(
                    id=slope.id,
                    slope_length=slope.length,
                    slope_name=slope.name,
                    slope_area=slope.area,
                    lines=lines_slope_data,
                    sheets=sheets_data,
                    cutouts=cutouts_data
                ))
            return Step5Response(
                general_plan=lines_data,
                slopes=slopes_data
            )
        case 6:
            lines = await LinesDAO.find_all(project_id=project_id)
            accessories = await AccessoriesDAO.find_all(project_id=project_id)

            return Step6Response(
                lines=[
                    LineResponse(
                        id=line.id,
                        line_type=line.type,
                        line_name=line.name,
                        line_length=line.length,
                        coords=LineData(start=PointData(x=line.x_start, y=line.y_start),
                                        end=PointData(x=line.x_end, y=line.y_end))
                    ) for line in lines],
                accessories=[
                    AccessoriesResponse(
                        id=accessory.id,
                        type=accessory.type,
                        accessory_name=accessory.name,
                        lines_id=accessory.lines_id,
                        lines_length=accessory.lines_length,
                        length=accessory.length,
                        width=accessory.width if accessory.width is not None else None,
                        amount=accessory.quantity
                        ) for accessory in accessories]
            )
        case 7:
            materials = await MaterialsDAO.find_all(project_id=project_id)
            return [
                MaterialEstimateResponse(
                    name=material.name,
                    material=material.material,
                    color=material.color
                ) for material in materials
            ]
        case 8:
            slopes = await SlopesDAO.find_all(project_id=project_id)
            materials = await MaterialsDAO.find_all(project_id=project_id)
            roof = await RoofsDAO.find_by_id(project.roof_id)
            materials_estimate = [
                MaterialEstimateResponse(
                    name=material.name,
                    material=material.material,
                    color=material.color
                ) for material in materials
            ]
            slopes_estimate = []
            slopes_area = 0
            all_sheets = []
            overall = 0
            plans_data = []
            for slope in slopes:
                lines = await LinesSlopeDAO.find_all(slope_id=slope.id)
                area_overall = 0
                area_usefull = 0
                slopes_area += slope.area
                sheets = await SheetsDAO.find_all(slope_id=slope.id)
                plans_data.append(draw_plan(lines, sheets, roof.overall_width))
                for sheet in sheets:
                    area_overall += sheet.area_overall
                    area_usefull += sheet.area_usefull
                    all_sheets.append(sheet.length)
                overall += area_overall
                slopes_estimate.append(
                    SlopeEstimateResponse(
                        slope_name=slope.name,
                        slope_length=slope.length,
                        slope_area=slope.area,
                        area_overall=area_overall,
                        area_usefull=area_usefull
                    )
                )
            length_counts = Counter(all_sheets)
            accessories = await AccessoriesDAO.find_all(project_id=project_id)
            accessories_estimate = []
            sofits_estimate = []
            for accessory in accessories:
                if 'Софит' in accessory.name or 'профиль' in accessory.name:
                    sofits_estimate.append(
                        SofitsEstimateResponce(
                            name=accessory.name,
                            type=accessory.type,
                            length=accessory.length,
                            width=accessory.width,
                            overall_length=accessory.lines_length,
                            amount=accessory.quantity,
                            price=700
                        ))
                else:
                    accessories_estimate.append(
                        AccessoriesEstimateResponse(
                            name=accessory.name,
                            type=accessory.type,
                            length=accessory.length,
                            overall_length=accessory.lines_length,
                            amount=accessory.quantity,
                            price=300
                        ))
            screws_estimate = [
                ScrewsEstimateResponse(
                    name='Саморез 4,8х35',
                    amount=int(overall*6),
                    packege_amount=250,
                    price=1500
                )
            ]
            sheets_amount_dict = dict(length_counts)

            return EstimateResponse(
                project_name=project.name,
                project_address=project.address,
                materials=materials_estimate,
                roof_base=RoofEstimateResponse(
                    roof_name=roof.name,
                    roof_type=roof.type,
                    price=650,
                    roof_overall_width=roof.overall_width,
                    roof_useful_width=roof.useful_width,
                    roof_overlap=roof.overlap,
                    roof_max_length=roof.max_length,
                    roof_max_length_standart=roof.max_length-roof.overlap),
                sheets_amount=sheets_amount_dict,
                slopes=slopes_estimate,
                accessories=accessories_estimate,
                sofits=sofits_estimate,
                screws=screws_estimate,
                sheets_extended=plans_data
            )


@router.post("/projects/{project_id}/add_lines", description="Add lines of sketch")
async def add_lines(
    request: Request,
    project_id: UUID4,
    lines: List[LinesData],
    user: Users = Depends(get_current_user)
) -> List[LineResponse]:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    lines_response = []
    existing_names = []
    existing_points = {}
    for line in lines:
        line_name = get_next_name(existing_names)

        if line.start in existing_points:
            start_id = existing_points[line.start]
        else:
            point = await PointsDAO.add(
                x=line.start.x,
                y=line.start.y,
            )
            start_id = point.id
            existing_points[line.start] = start_id

        if line.end in existing_points:
            end_id = existing_points[line.end]
        else:
            point = await PointsDAO.add(
                x=line.end.x,
                y=line.end.y,
            )
            end_id = point.id
            existing_points[line.end] = end_id

        new_line = await LinesDAO.add(
            project_id=project_id,
            name=line_name,
            type=line.type,
            start_id=start_id,
            end_id=end_id,
        )
        existing_names.append(line_name)
        lines_response.append(LineResponse(
            id=new_line.id,
            name=new_line.name,
            type=new_line.type,
            start=line.start,
            end=line.end)
        )
    return lines_response


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
            type=line.type,
            name=line.name,
            start=PointData(x=line.start.x,
                            y=line.start.y),
            end=PointData(x=line.end.x,
                          y=line.end.y)
        ))
        await LinesDAO.delete_(model_id=line.id)
    return lines_response


# @router.patch("/projects/{project_id}/slopes/{slope_id}/update_lines", description="Update line dimensions")
# async def add_length_lines(
#       project_id: UUID4,
#       slope_id: UUID4,
#       lines_data: List[LineUpdateRequest],
#       user: Users = Depends(get_current_user)
#       ) -> List[LineResponse]:
#     project = await ProjectsDAO.find_by_id(project_id)
#     if not project or project.user_id != user.id:
#         raise ProjectNotFound
#     # slope = await SlopesDAO.find_by_id(slope_id)
#     lines_old = await LinesSlopeDAO.find_all(slope_id=slope_id)
#     lines = sorted(lines_old, key=lambda x: x.number)
#     for line in lines:
#         for line_data in lines_data:
#             if line_data.id == line.line_id:
#                 await LinesDAO.update_(
#                     model_id=line_data.id,
#                     length=line_data.length)
#     for line_data in lines_data:
#         await LinesDAO.update_(
#             model_id=line_data.id,
#             length=line_data.length)
#         lines = await LinesSlopeDAO.find_all(line_id=line_data.id)
#         new_coords = update_coords(lines[0].x_start, lines[0].x_end, lines[0].y_start, lines[0].y_end, lines[0].length, line_data.length)
#         for line in lines:
#             await LinesSlopeDAO.update_(
#                 model_id=line.id,
#                 length=line_data.length,
#                 x_start=new_coords[0],
#                 x_end=new_coords[2],
#                 y_start=new_coords[1],
#                 y_end=new_coords[3],
#             )
#     lines = await LinesDAO.find_all(project_id=project_id)
#     return [LineResponse(
#         id=line.id,
#         line_type=line.type,
#         line_name=line.name,
#         line_length=line.length,
#         coords=LineData(start=PointData(x=line.x_start, y=line.y_start),
#                         end=PointData(x=line.x_end, y=line.y_end))
#     ) for line in lines]


# @router.get("/projects/{project_id}/slopes", description="Get list of lines")
# async def get_slopes(
#       project_id: UUID4,
#       user: Users = Depends(get_current_user)) -> Step3Response:
#     project = await ProjectsDAO.find_by_id(project_id)
#     if not project or project.user_id != user.id:
#         raise ProjectNotFound
#     slopes = await SlopesDAO.find_all(project_id=project_id)
#     lines = await LinesDAO.find_all(project_id=project_id)
#     lines_plan = [
#         LineResponse(
#             id=line.id,
#             line_type=line.type,
#             line_name=line.name,
#             line_length=line.length,
#             coords=LineData(start=PointData(x=line.x_start, y=line.y_start),
#                             end=PointData(x=line.x_end, y=line.y_end))
#         ) for line in lines
#         ]
#     slopes_data = []
#     for slope in slopes:
#         lines = await LinesSlopeDAO.find_all(slope_id=slope.id)
#         lines_data = [LineSlopeResponse(
#             id=line.id,
#             line_id=line.line_id,
#             line_name=line.name,
#             line_length=line.length,
#             coords=LineData(start=PointData(x=line.x_start, y=line.y_start),
#                             end=PointData(x=line.x_end, y=line.y_end)
#                             )
#             ) for line in lines
#         ]
#         slopes_data.append(SlopeResponse(
#             id=slope.id,
#             slope_name=slope.name,
#             slope_length=slope.length,
#             slope_area=slope.area if slope.area is not None else None,
#             lines=lines_data
#             )
#         )
#     return Step3Response(
#         general_plan=lines_plan,
#         slopes=slopes_data
#     )


@router.patch("/projects/{project_id}/lines/node_line", description="Add roof node")
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
    return None


@router.get("/projects/{project_id}/get_general_plan")
async def get_general_plan(
    project_id: UUID4,
    user: Users = Depends(get_current_user)
) -> GenPlanResponse:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    lines = await LinesDAO.find_all(project_id=project_id)
    lines_data = [
        LineResponse(
            id=line.id,
            type=line.type,
            name=line.name,
            start=PointData(x=line.start.x,
                            y=line.start.y),
            end=PointData(x=line.end.x,
                          y=line.end.y)
        ) for line in lines
    ]
    slopes = await SlopesDAO.find_all(project_id=project_id)
    if not slopes:
        raise SlopeNotFound
    slopes_data = []
    for slope in slopes:
        lines_slope = await LinesSlopeDAO.find_all(slope_id=slope.id)
        lines_slope_data = [
            LineSlopeGenPlanResponse(
                id=line_slope.id,
                parent_id=line_slope.parent_id
            ) for line_slope in lines_slope
        ]
        lines_length = await LengthSlopeDAO.find_all(slope_id=slope.id)
        length_slope_data = []
        for line_length in lines_length:
            point = await PointsDAO.find_by_id(line_length.point.parent_id)
            line = await LinesDAO.find_by_id(line_length.line_slope.parent_id)
            if line.start.x == line.end.x:
                length_slope_data.append(
                    LengthSlopeResponse(
                        id=line_length.id,
                        start=PointData(
                            x=point.x,
                            y=point.y
                        ),
                        end=PointData(
                            x=line.start.x,
                            y=point.y
                        )
                    )
                )
            else:
                length_slope_data.append(
                    LengthSlopeResponse(
                        id=line_length.id,
                        start=PointData(
                            x=point.x,
                            y=point.y
                        ),
                        end=PointData(
                            x=point.x,
                            y=line.start.y
                        )
                    )
                )
        slopes_data.append(
            SlopeGenPlanResponse(
                id=slope.id,
                name=slope.name,
                lines=lines_slope_data,
                length_line=length_slope_data
            )
        )
    return GenPlanResponse(
        lines=lines_data,
        slopes=slopes_data
    )


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
    for line_d in data.lines:
        id = line_d.id
        length = line_d.length
        line = await LinesSlopeDAO.find_by_id(id)
        if line.start.y == line.end.y:
            old_length = line.start.x - line.end.x
            if old_length > 0:
                await PointsSlopeDAO.update_(
                    model_id=line.start_id,
                    x=line.end.x+length
                )
            else:
                await PointsSlopeDAO.update_(
                    model_id=line.end_id,
                    x=line.start.x+length
                )
        elif line.start.x == line.end.x:
            old_length = line.start.y - line.end.y
            if old_length > 0:
                await PointsSlopeDAO.update_(
                    model_id=line.start_id,
                    x=line.end.y+length
                )
            else:
                await PointsSlopeDAO.update_(
                    model_id=line.end_id,
                    x=line.start.y+length
                )
        await LinesSlopeDAO.update_(
            model_id=id,
            length=length
        )
        await LinesDAO.update_(
            model_id=line.parent_id,
            length=length
        )
    for length_line_d in data.length_line:
        id = length_line_d.id
        length = length_line_d.length
        length_slope = await LengthSlopeDAO.find_by_id(id)
        if length_slope.line_slope.start.y == length_slope.line_slope.end.y:
            if length_slope.line_slope.type == "конёк":
                await PointsSlopeDAO.update_(
                    model_id=length_slope.line_slope.start_id,
                    y=length_slope.point.y+length
                )
                await PointsSlopeDAO.update_(
                    model_id=length_slope.line_slope.end_id,
                    y=length_slope.point.y+length
                )
            else:
                k = 0
                lines_1 = await LinesSlopeDAO.find_all(start_id=length_slope.point_id)
                for line_1 in lines_1:
                    if line_1.start.y == line_1.end.y:
                        await PointsSlopeDAO.update_(
                            model_id=line_1.start_id,
                            y=length_slope.line_slope.start.y+length
                        )
                        await PointsSlopeDAO.update_(
                            model_id=line_1.end_id,
                            y=length_slope.line_slope.start.y+length
                        )
                        k += 1
                lines_2 = await LinesSlopeDAO.find_all(end_id=length_slope.point_id)
                for line_2 in lines_2:
                    if line_2.start.y == line_2.end.y:
                        await PointsSlopeDAO.update_(
                            model_id=line_2.start_id,
                            y=length_slope.line_slope.start.y+length
                        )
                        await PointsSlopeDAO.update_(
                            model_id=line_2.end_id,
                            y=length_slope.line_slope.start.y+length
                        )
                        k += 1
                if k == 0:
                    await PointsSlopeDAO.update_(
                        model_id=length_slope.point_id,
                        y=length_slope.line_slope.start.y+length
                    )
    return None


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
) -> List[SlopeResponse]:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound

    lines = await LinesDAO.find_all(project_id=project.id)
    existing_names = []
    slopes = find_slope(lines)
    slope_data = []
    for slope in slopes:
        lines = []
        lines_slope = []
        length_data = []
        for line_id in slope:
            lines.append(
                await LinesDAO.find_by_id(line_id)
            )
        lines_data = []
        existing_points = {}
        slope_name = get_next_name(existing_names)
        existing_names.append(slope_name)
        new_slope = await SlopesDAO.add(
            name=slope_name,
            project_id=project.id
        )
        new_lines = rotate_slope(lines)
        for line in new_lines:
            if line.start.id in existing_points:
                start_id = existing_points[line.start.id]
            else:
                point = await PointsSlopeDAO.add(
                    x=line.start.x,
                    y=line.start.y,
                    parent_id=line.start.id,
                    slope_id=new_slope.id
                )
                start_id = point.id
                existing_points[line.start.id] = start_id

            if line.end.id in existing_points:
                end_id = existing_points[line.end.id]
            else:
                point = await PointsSlopeDAO.add(
                    x=line.end.x,
                    y=line.end.y,
                    parent_id=line.end.id,
                    slope_id=new_slope.id
                )
                end_id = point.id
                existing_points[line.end.id] = end_id
            line_slope = await LinesSlopeDAO.add(
                name=line.name,
                parent_id=line.id,
                type=line.type,
                start_id=start_id,
                end_id=end_id,
                slope_id=new_slope.id
            )
            lines_data.append(
                LineSlopeResponse(
                    id=line_slope.id,
                    parent_id=line_slope.parent_id,
                    name=line_slope.name,
                    start=PointData(x=line.start.x, y=line.start.y),
                    end=PointData(x=line.end.x, y=line.end.y)
                )
            )
        lines_slope = await LinesSlopeDAO.find_all(
            slope_id=new_slope.id
        )
        lengths_slope = process_lines_and_generate_slopes(lines_slope)
        for length_slope in lengths_slope:
            new_length = await LengthSlopeDAO.add(
                point_id=length_slope[0],
                line_slope_id=length_slope[1],
                slope_id=new_slope.id
            )

        slope_data.append(
            SlopeResponse(
                id=new_slope.id,
                name=new_slope.name,
                lines=lines_data,
                length_line=length_data
            )
        )
    return slope_data


# @router.patch("/projects/{project_id}/slopes/{slope_id}/lines_slope/{line_id}", description="Update line slope dimensions")
# async def update_line_slope(
#     project_id: UUID4,
#     slope_id: UUID4,
#     line_id: UUID4,
#     length: float,
#     user: Users = Depends(get_current_user)
# ) -> List[LineResponse]:
#     project = await ProjectsDAO.find_by_id(project_id)
#     if not project or project.user_id != user.id:
#         raise ProjectNotFound
#     slope = await SlopesDAO.find_by_id(slope_id)
#     if not slope or slope.project_id != project_id:
#         raise SlopeNotFound
#     lines = await LinesSlopeDAO.find_all(slope_id=slope_id)
#     slope_lines = SlopeUpdate(lines).change_line_length(line_id=line_id, new_line_length=length)
#     updated_lines = []
#     y_list = []
#     for line in slope_lines:
#         y_list.append(line.point2.y)
#         y_list.append(line.point1.y)
#         parent_line = await LinesDAO.find_by_id(line.parent_id)
#         await LinesDAO.update_(model_id=line.parent_id, length=max(parent_line.length, line.length))
#         updated_line = await LinesSlopeDAO.update_(
#             model_id=line.line_id,
#             x_start=line.point1.x,
#             y_start=line.point1.y,
#             x_end=line.point2.x,
#             y_end=line.point2.y,
#             length=line.length
#         )
#         updated_lines.append(LineSlopeResponse(
#             id=updated_line.id,
#             line_id=updated_line.line_id,
#             line_name=updated_line.name,
#             line_length=updated_line.length,
#             coords=LineData(start=PointData(x=updated_line.x_start, y=updated_line.y_start),
#                             end=PointData(x=updated_line.x_end, y=updated_line.y_end))
#             ))
#     y_list.sort()
#     slope_length = y_list[-1] - y_list[0]
#     if slope_length != slope.length:
#         await SlopesDAO.update_(model_id=slope.id, length=length)
#     return updated_lines


# @router.patch("/projects/{project_id}/slopes/{slope_id}", description="Update length slope dimensions")
# async def update_slope_length(
#     project_id: UUID4,
#     slope_id: UUID4,
#     length: float,
#     user: Users = Depends(get_current_user)
# ) -> List[LineResponse]:
#     project = await ProjectsDAO.find_by_id(project_id)
#     if not project or project.user_id != user.id:
#         raise ProjectNotFound
#     slope = await SlopesDAO.find_by_id(slope_id)
#     if not slope or slope.project_id != project_id:
#         raise SlopeNotFound
#     await SlopesDAO.update_(model_id=slope_id, length=length)
#     lines = await LinesSlopeDAO.find_all(slope_id=slope_id)
#     slope_lines = SlopeUpdate(lines).change_slope_length(new_slope_length=length)
#     updated_lines = []
#     for line in slope_lines:
#         parent_line = await LinesDAO.find_by_id(line.parent_id)
#         await LinesDAO.update_(model_id=line.parent_id, length=max(parent_line.length, line.length))
#         updated_line = await LinesSlopeDAO.update_(
#             model_id=line.line_id,
#             x_start=line.point1.x,
#             y_start=line.point1.y,
#             x_end=line.point2.x,
#             y_end=line.point2.y,
#             length=line.length
#         )
#         updated_lines.append(LineSlopeResponse(
#             id=updated_line.id,
#             line_id=updated_line.line_id,
#             line_name=updated_line.name,
#             line_length=updated_line.length,
#             coords=LineData(start=PointData(x=updated_line.x_start, y=updated_line.y_start),
#                             end=PointData(x=updated_line.x_end, y=updated_line.y_end))
#             ))
#     return updated_lines


@router.get("/projects/{project_id}/add_line/slopes/{slope_id}/cutounts", description="Get list of cutouts")
async def get_cutouts(
      project_id: UUID4,
      slope_id: UUID4,
      user: Users = Depends(get_current_user)) -> List[CutoutResponse]:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    slope = await SlopesDAO.find_by_id(slope_id)
    if not slope or slope.project_id != project_id:
        raise SlopeNotFound
    cutouts = await CutoutsDAO.find_all(slope_id=slope_id)
    cutouts_data = [
        CutoutResponse(
            id=cutout.id,
            cutout_name=cutout.name,
            cutout_points=[PointData(x=x, y=y) for x, y in zip(cutout.x_coords, cutout.y_coords)]
        ) for cutout in cutouts
        ]
    return cutouts_data


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
) -> CutoutResponse:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound

    slope = await SlopesDAO.find_by_id(slope_id)
    if not slope or slope.project_id != project_id:
        raise SlopeNotFound

    existing_cutouts = await CutoutsDAO.find_all(slope_id=slope.id)
    existing_names = [cutout.name for cutout in existing_cutouts]
    cutout_name = get_next_name(existing_names)
    points_x = [point.x for point in points]
    points_y = [point.y for point in points]

    new_cutout = await CutoutsDAO.add(
        slope_id=slope_id,
        name=cutout_name,
        x_coords=points_x,
        y_coords=points_y
    )
    return CutoutResponse(
        id=new_cutout.id,
        cutout_name=new_cutout.name,
        cutout_points=points,
    )


@router.patch("/projects/{project_id}/slopes/{slope_id}/cutouts/{cutout_id}", description="Update cutout")
async def update_cutout(
    project_id: UUID4,
    slope_id: UUID4,
    cutout_id: UUID4,
    points: List[PointData],
    user: Users = Depends(get_current_user)
) -> CutoutResponse:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound

    slope = await SlopesDAO.find_by_id(slope_id)
    if not slope or slope.project_id != project_id:
        raise SlopeNotFound

    points_x = [point.x for point in points]
    points_y = [point.y for point in points]

    new_cutout = await CutoutsDAO.update_(
        model_id=cutout_id,
        x_coords=points_x,
        y_coords=points_y
    )
    return CutoutResponse(
        id=new_cutout.id,
        cutout_name=new_cutout.name,
        cutout_points=points,
    )


@router.get("/projects/{project_id}/slopes/{slope_id}/sheets", description="View sheets for slope")
async def get_sheets(
    project_id: UUID4,
    slope_id: UUID4,
    user: Users = Depends(get_current_user)
) -> List[SheetResponse]:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound

    slope = await SlopesDAO.find_by_id(slope_id)
    if not slope or slope.project_id != project_id:
        raise SlopeNotFound
    sheets = await SheetsDAO.find_all(slope_id=slope_id)
    return [SheetResponse(
        id=sheet.id,
        sheet_x_start=sheet.x_start,
        sheet_y_start=sheet.y_start,
        sheet_length=sheet.length,
        sheet_area_overall=sheet.area_overall,
        sheet_area_usefull=sheet.area_usefull
        ) for sheet in sheets]


@router.delete("/projects/{project_id}/add_line/slopes/{slope_id}/sheets/{sheet_id}", description="Delete cutout")
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
    sheets_id: List[UUID4],
    user: Users = Depends(get_current_user)
) -> None:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound

    slope = await SlopesDAO.find_by_id(slope_id)
    if not slope or slope.project_id != project_id:
        raise SlopeNotFound
    for sheet_id in sheets_id:
        await SheetsDAO.delete_(model_id=sheet_id)


@router.post("/projects/{project_id}/slopes/{slope_id}/sheet", description="Add roof sheet for slope")
async def add_sheet(
    project_id: UUID4,
    slope_id: UUID4,
    sheet: NewSheetRequest,
    user: Users = Depends(get_current_user)
) -> SheetResponse:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    roof = await RoofsDAO.find_by_id(project.roof_id)
    slope = await SlopesDAO.find_by_id(slope_id)
    if not slope or slope.project_id != project_id:
        raise SlopeNotFound
    new_sheet = await SheetsDAO.add(
        x_start=sheet.sheet_x_start,
        y_start=sheet.sheet_y_start,
        length=sheet.sheet_length,
        area_overall=sheet.sheet_length*roof.overall_width,
        area_usefull=sheet.sheet_length*roof.useful_width,
        slope_id=slope_id
    )
    return SheetResponse(
        id=new_sheet.id,
        sheet_x_start=new_sheet.x_start,
        sheet_y_start=new_sheet.y_start,
        sheet_length=new_sheet.length,
        sheet_area_overall=new_sheet.area_overall,
        sheet_area_usefull=new_sheet.area_usefull
    )


@router.post("/projects/{project_id}/slopes/{slope_id}/sheets", description="Calculate roof sheets for slope")
async def add_sheets(
    project_id: UUID4,
    slope_id: UUID4,
    user: Users = Depends(get_current_user)
) -> SlopeSheetsResponse:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound

    slope = await SlopesDAO.find_by_id(slope_id)
    if not slope or slope.project_id != project_id:
        raise SlopeNotFound
    cutouts = await CutoutsDAO.find_all(slope_id=slope_id)
    lines = await LinesSlopeDAO.find_all(slope_id=slope_id)
    lines_data = [LineSlopeResponse(
        id=line.id,
        line_id=line.line_id,
        line_name=line.name,
        line_length=line.length,
        coords=LineData(start=PointData(x=line.x_start, y=line.y_start),
                        end=PointData(x=line.x_end, y=line.y_end))
        ) for line in lines]
    lines = sorted(lines, key=lambda line: line.number)
    points = []
    points1 = []
    for line in lines:
        if len(points) == 0:
            points.append((line.x_start, line.y_start))
            points.append((line.x_end, line.y_end))
            points1.append((line.x_end, line.y_end))
            points1.append((line.x_start, line.y_start))
        elif len(points) == 2:
            if (line.x_start == points[-1][0] and line.y_start == points[-1][1]):
                points.append((line.x_end, line.y_end))
            elif (line.x_end == points[-1][0] and line.y_end == points[-1][1]):
                points.append((line.x_start, line.y_start))
            elif (line.x_start == points1[-1][0] and line.y_start == points1[-1][1]):
                points = points1
                points.append((line.x_end, line.y_end))
            elif (line.x_end == points1[-1][0] and line.y_end == points1[-1][1]):
                points = points1
                points.append((line.x_start, line.y_start))
        else:
            if (line.x_start == points[-1][0] and line.y_start == points[-1][1]):
                points.append((line.x_end, line.y_end))
            elif (line.x_end == points[-1][0] and line.y_end == points[-1][1]):
                points.append((line.x_start, line.y_start))
    cutouts_data = []
    if cutouts is None:
        figure = Polygon(points)
    else:
        figure = Polygon(points)
        for cutout in cutouts:
            points_cut = list(zip(cutout.x_coords, cutout.y_coords))
            cutouts_data.append(CutoutResponse(
                id=cutout.id,
                cutout_name=cutout.name,
                cutout_points=[PointData(x=x, y=y) for x, y in zip(cutout.x_coords, cutout.y_coords)]
            ))
            figure = create_hole(figure, points_cut)
    area = figure.area
    slope = await SlopesDAO.update_(model_id=slope_id, area=area)
    roof = await RoofsDAO.find_by_id(project.roof_id)
    sheets = await create_sheets(figure, roof, 0, 0)
    sheets_data = []
    for sheet in sheets:
        new_sheet = await SheetsDAO.add(
            x_start=sheet[0],
            y_start=sheet[1],
            length=sheet[2],
            area_overall=sheet[3],
            area_usefull=sheet[4],
            slope_id=slope_id
        )
        sheets_data.append(SheetResponse(
            id=new_sheet.id,
            sheet_x_start=new_sheet.x_start,
            sheet_y_start=new_sheet.y_start,
            sheet_length=new_sheet.length,
            sheet_area_overall=new_sheet.area_overall,
            sheet_area_usefull=new_sheet.area_usefull
        ))
    return SlopeSheetsResponse(
        id=slope.id,
        slope_length=slope.length,
        slope_name=slope.name,
        slope_area=slope.area,
        lines=lines_data,
        sheets=sheets_data,
        cutouts=cutouts_data
    )


@router.patch("/projects/{project_id}/slopes/{slope_id}/update_length_sheets", description="Calculate roof sheets for slope")
async def update_length_sheets(
    project_id: UUID4,
    slope_id: UUID4,
    sheets_id: List[UUID4],
    length: float,
    user: Users = Depends(get_current_user)
) -> List[SheetResponse]:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    roof = await RoofsDAO.find_by_id(project.roof_id)
    slope = await SlopesDAO.find_by_id(slope_id)
    if not slope or slope.project_id != project_id:
        raise SlopeNotFound
    sheets_response = []
    sheets = [await SheetsDAO.find_by_id(sheet_id) for sheet_id in sheets_id]
    for sheet in sheets:
        new_length = sheet.length + length
        updated_sheet = await SheetsDAO.update_(
            model_id=sheet.id,
            length=new_length,
            area_overall=new_length*roof.overall_width,
            area_usefull=new_length*roof.useful_width
        )
        sheets_response.append(SheetResponse(
            id=updated_sheet.id,
            sheet_x_start=updated_sheet.x_start,
            sheet_y_start=updated_sheet.y_start,
            sheet_length=updated_sheet.length,
            sheet_area_overall=updated_sheet.area_overall,
            sheet_area_usefull=updated_sheet.area_usefull
        ))
    return sheets_response


@router.patch("/projects/{project_id}/slopes/{slope_id}/offset_sheets")
async def offset_sheets(
    project_id: UUID4,
    slope_id: UUID4,
    data: PointData,
    user: Users = Depends(get_current_user)
) -> SlopeSheetsResponse:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound

    slope = await SlopesDAO.find_by_id(slope_id)
    if not slope or slope.project_id != project_id:
        raise SlopeNotFound
    cutouts = await CutoutsDAO.find_all(slope_id=slope_id)
    lines = await LinesSlopeDAO.find_all(slope_id=slope_id)
    lines_data = [LineSlopeResponse(
        id=line.id,
        line_id=line.line_id,
        line_name=line.name,
        line_length=line.length,
        coords=LineData(start=PointData(x=line.x_start, y=line.y_start),
                        end=PointData(x=line.x_end, y=line.y_end))
        ) for line in lines]
    lines = sorted(lines, key=lambda line: line.number)
    points = []
    points1 = []
    for line in lines:
        if len(points) == 0:
            points.append((line.x_start, line.y_start))
            points.append((line.x_end, line.y_end))
            points1.append((line.x_end, line.y_end))
            points1.append((line.x_start, line.y_start))
        elif len(points) == 2:
            if (line.x_start == points[-1][0] and line.y_start == points[-1][1]):
                points.append((line.x_end, line.y_end))
            elif (line.x_end == points[-1][0] and line.y_end == points[-1][1]):
                points.append((line.x_start, line.y_start))
            elif (line.x_start == points1[-1][0] and line.y_start == points1[-1][1]):
                points = points1
                points.append((line.x_end, line.y_end))
            elif (line.x_end == points1[-1][0] and line.y_end == points1[-1][1]):
                points = points1
                points.append((line.x_start, line.y_start))
        else:
            if (line.x_start == points[-1][0] and line.y_start == points[-1][1]):
                points.append((line.x_end, line.y_end))
            elif (line.x_end == points[-1][0] and line.y_end == points[-1][1]):
                points.append((line.x_start, line.y_start))
    cutouts_data = []
    if cutouts is None:
        figure = Polygon(points)
    else:
        figure = Polygon(points)
        for cutout in cutouts:
            points_cut = list(zip(cutout.x_coords, cutout.y_coords))
            cutouts_data.append(CutoutResponse(
                id=cutout.id,
                cutout_name=cutout.name,
                cutout_points=[PointData(x=x, y=y) for x, y in zip(cutout.x_coords, cutout.y_coords)]
            ))
            figure = create_hole(figure, points_cut)
    area = figure.area
    slope = await SlopesDAO.update_(model_id=slope_id, area=area)
    roof = await RoofsDAO.find_by_id(project.roof_id)
    sheets = await SheetsDAO.find_all(slope_id=slope_id)
    for sheet in sheets:
        await SheetsDAO.delete_(model_id=sheet.id)
    sheets = await create_sheets(figure, roof, data.x, data.y)
    sheets_data = []
    for sheet in sheets:
        new_sheet = await SheetsDAO.add(
            x_start=sheet[0],
            y_start=sheet[1],
            length=sheet[2],
            area_overall=sheet[3],
            area_usefull=sheet[4],
            slope_id=slope_id
        )
        sheets_data.append(SheetResponse(
            id=new_sheet.id,
            sheet_x_start=new_sheet.x_start,
            sheet_y_start=new_sheet.y_start,
            sheet_length=new_sheet.length,
            sheet_area_overall=new_sheet.area_overall,
            sheet_area_usefull=new_sheet.area_usefull
        ))
    return SlopeSheetsResponse(
        id=slope.id,
        slope_length=slope.length,
        slope_name=slope.name,
        slope_area=slope.area,
        lines=lines_data,
        sheets=sheets_data,
        cutouts=cutouts_data
    )


@router.patch("/projects/{project_id}/slopes/{slope_id}/overlay", description="Calculate roof sheets for slope")
async def update_sheets_overlay(
    project_id: UUID4,
    slope_id: UUID4,
    user: Users = Depends(get_current_user)
) -> List[SheetResponse]:
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
        if previous_sheet is None:
            previous_sheet = sheet
        if previous_sheet.x_start == sheet.x_start and previous_sheet.y_start + previous_sheet.length > sheet.y_start:
            new_length = previous_sheet.length + sheet.length - roof.overlap
            if new_length <= roof.max_length:
                result = await SheetsDAO.update_(model_id=previous_sheet.id, length=new_length)
                await SheetsDAO.delete_(model_id=sheet.id)
                previous_sheet = result
    new_sheets = await SheetsDAO.find_all(slope_id=slope_id)
    return [SheetResponse(
        id=new_sheet.id,
        sheet_x_start=new_sheet.x_start,
        sheet_y_start=new_sheet.y_start,
        sheet_length=new_sheet.length,
        sheet_area_overall=new_sheet.area_overall,
        sheet_area_usefull=new_sheet.area_usefull
    )
            for new_sheet in new_sheets]


@router.get("/projects/{project_id}/accessories", description="View accessories")
async def get_accessories(
    project_id: UUID4,
    user: Users = Depends(get_current_user)
) -> List[AccessoriesResponse]:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    accessories = await AccessoriesDAO.find_all(project_id=project_id)
    return [AccessoriesResponse(
        id=accessory.id,
        type=accessory.type,
        accessory_name=accessory.name,
        lines_id=accessory.lines_id,
        lines_length=accessory.lines_length,
        length=accessory.length,
        width=accessory.width if accessory.width is not None else None,
        amount=accessory.quantity
        ) for accessory in accessories]


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
) -> AccessoriesResponse:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    lines = await asyncio.gather(*[LinesDAO.find_by_id(line_id) for line_id in accessory.lines_id])
    lines_length = 0
    for line in lines:
        lines_length += line.length
    if accessory.width is not None:
        step1 = lines_length // accessory.width
        amount = step1 // 5
        new_accessory = await AccessoriesDAO.add(
            name=accessory.name,
            type=accessory.type,
            lines_id=accessory.lines_id,
            length=accessory.length,
            lines_length=lines_length,
            width=accessory.width,
            quantity=amount,
            project_id=project_id
        )
    else:
        amount = lines_length // 1.9
        new_accessory = await AccessoriesDAO.add(
            name=accessory.name,
            type=accessory.type,
            lines_id=accessory.lines_id,
            length=accessory.length,
            lines_length=lines_length,
            quantity=amount,
            project_id=project_id
        )
    return AccessoriesResponse(
        id=new_accessory.id,
        type=new_accessory.type,
        accessory_name=new_accessory.name,
        lines_id=new_accessory.lines_id,
        lines_length=new_accessory.lines_length,
        length=new_accessory.length,
        width=new_accessory.width if new_accessory.width is not None else None,
        amount=new_accessory.quantity
    )


@router.patch("/projects/{project_id}/accessories/{accessory_id}", description="Calculate roof sheets for slope")
async def update_accessory(
    project_id: UUID4,
    accessory_id: UUID4,
    accessory: AccessoriesRequest,
    user: Users = Depends(get_current_user)
) -> AccessoriesResponse:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    lines = await asyncio.gather(*[LinesDAO.find_by_id(line_id) for line_id in accessory.lines_id])
    lines_length = 0
    for line in lines:
        lines_length += line.length
    if accessory.width is not None:
        step1 = lines_length // accessory.width
        amount = step1 // 5
        new_accessory = await AccessoriesDAO.update_(
            model_id=accessory_id,
            lines_id=accessory.lines_id,
            length=accessory.length,
            lines_length=lines_length,
            width=accessory.width,
            quantity=amount
        )
    else:
        amount = lines_length // 1.9
        new_accessory = await AccessoriesDAO.update_(
            model_id=accessory_id,
            lines_id=accessory.lines_id,
            length=accessory.length,
            lines_length=lines_length,
            quantity=amount
        )
    return AccessoriesResponse(
        id=new_accessory.id,
        type=new_accessory.type,
        accessory_name=new_accessory.name,
        lines_id=new_accessory.lines_id,
        lines_length=new_accessory.lines_length,
        length=new_accessory.length,
        width=new_accessory.width if new_accessory.width is not None else None,
        amount=new_accessory.quantity
    )


@router.post("/projects/{project_id}/materials")
async def add_material(
    project_id: UUID4,
    materials: MaterialRequest,
    user: Users = Depends(get_current_user)
) -> MaterialResponse:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    material = await MaterialsDAO.add(
        project_id=project_id,
        name=materials.name,
        material=materials.material,
        color=materials.color
        )
    return MaterialResponse(
        id=material.id,
        name=material.name,
        material=material.material,
        color=material.color
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
    materials = await MaterialsDAO.find_all(project_id=project_id)
    roof = await RoofsDAO.find_by_id(project.roof_id)
    materials_estimate = [
        MaterialEstimateResponse(
            name=material.name,
            material=material.material,
            color=material.color
        ) for material in materials
    ]
    slopes_estimate = []
    slopes_area = 0
    all_sheets = []
    overall = 0
    plans_data = []
    for slope in slopes:
        lines = await LinesSlopeDAO.find_all(slope_id=slope.id)
        area_overall = 0
        area_usefull = 0
        slopes_area += slope.area
        sheets = await SheetsDAO.find_all(slope_id=slope.id)
        plans_data.append(draw_plan(lines, sheets, roof.overall_width))
        for sheet in sheets:
            area_overall += sheet.area_overall
            area_usefull += sheet.area_usefull
            all_sheets.append(sheet.length)
        overall += area_overall
        slopes_estimate.append(
            SlopeEstimateResponse(
                slope_name=slope.name,
                slope_length=slope.length,
                slope_area=slope.area,
                area_overall=area_overall,
                area_usefull=area_usefull
            )
        )
    length_counts = Counter(all_sheets)
    accessories = await AccessoriesDAO.find_all(project_id=project_id)
    accessories_estimate = []
    sofits_estimate = []
    for accessory in accessories:
        if 'Софит' in accessory.name or 'профиль' in accessory.name:
            sofits_estimate.append(
                SofitsEstimateResponce(
                    id=accessory.id,
                    type=accessory.type,
                    name=accessory.name,
                    length=accessory.length,
                    width=accessory.width,
                    overall_length=accessory.lines_length,
                    amount=accessory.quantity,
                    price=700
                ))
        else:
            accessories_estimate.append(
                AccessoriesEstimateResponse(
                    id=accessory.id,
                    type=accessory.type,
                    name=accessory.name,
                    length=accessory.length,
                    overall_length=accessory.lines_length,
                    amount=accessory.quantity,
                    price=300
                ))
    screws_estimate = [
        ScrewsEstimateResponse(
            name='Саморез 4,8х35',
            amount=int(overall*6),
            packege_amount=250,
            price=1500
        )
    ]
    sheets_amount_dict = dict(length_counts)

    return EstimateResponse(
        project_name=project.name,
        project_address=project.address,
        materials=materials_estimate,
        roof_base=RoofEstimateResponse(
            roof_name=roof.name,
            roof_type=roof.type,
            price=650,
            roof_overall_width=roof.overall_width,
            roof_useful_width=roof.useful_width,
            roof_overlap=roof.overlap,
            roof_max_length=roof.max_length,
            roof_max_length_standart=roof.max_length-roof.overlap),
        sheets_amount=sheets_amount_dict,
        slopes=slopes_estimate,
        accessories=accessories_estimate,
        sofits=sofits_estimate,
        screws=screws_estimate,
        sheets_extended=plans_data
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
