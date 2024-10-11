from fastapi import APIRouter, Depends
from typing import List
from pydantic import UUID4
from shapely.geometry import Polygon
from app.base.dao import RoofsDAO
from app.exceptions import LineNotFound, ProjectAlreadyExists, ProjectNotFound, SlopeNotFound
from app.projects.schemas import LineData, LineRequest, LineResponse, PointData, ProjectRequest, ProjectResponse, SheetResponse, SlopeResponse
from app.projects.dao import LinesDAO, ProjectsDAO, SheetsDAO, SlopesDAO
from app.projects.slope import LineRotate, SlopeExtractor, align_figure, create_sheets, get_next_name
from app.users.dependencies import get_current_user
from app.users.models import Users
import asyncio

router = APIRouter(prefix="/roofs", tags=["Roofs"])



@router.get("/projects", description="Get list of projects")
async def get_projects(user: Users = Depends(get_current_user)) -> List[ProjectResponse]:
    projects = await ProjectsDAO.find_all(user_id=user.id)
    return [
        ProjectResponse(
            project_id=project.id,
            project_name=project.name,
            datetime_created=project.datetime_created.strftime("%d.%m.%Y at %H:%M")
        ) for project in projects
    ]


@router.post("/projects", description="Create a roofing project")
async def add_project(
    project: ProjectRequest,
    user: Users = Depends(get_current_user)
) -> ProjectResponse:
    existing_project = await ProjectsDAO.find_one_or_none(name=project.name)
    if existing_project:
        raise ProjectAlreadyExists

    new_project = await ProjectsDAO.add(
        name=project.name,
        full_name_customer=project.full_name_customer,
        is_company=project.is_company,
        company_name=project.company_name if project.is_company else None,
        customer_contacts=project.customer_contacts,
        address=project.address,
        roof_id=project.roof_id,
        user_id=user.id
    )
    return ProjectResponse(
        project_id=new_project.id,
        project_name=new_project.name,
        datetime_created=new_project.datetime_created.strftime("%d.%m.%Y at %H:%M")
    )


@router.post("/projects/{project_id}/add_line", description="Create roof geometry")
async def add_line(
    project_id: UUID4,
    line: LineData,
    user: Users = Depends(get_current_user)
) -> LineResponse:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound

    existing_lines = await LinesDAO.find_all(project_id=project.id)
    existing_names = [line.name for line in existing_lines]
    line_name = get_next_name(existing_names)

    new_line = await LinesDAO.add(
        project_id=project_id,
        name=line_name,
        x_start_projection=line.start.x,
        y_start_projection=line.start.y,
        x_end_projection=line.end.x,
        y_end_projection=line.end.y,
        length=round(((line.start.x - line.end.x) ** 2 + (line.start.y - line.end.y) ** 2) ** 0.5, 2)
    )
    return LineResponse(
        line_id=new_line.id,
        line_name=new_line.name,
        line_length=new_line.length
    )


@router.patch("/projects/{project_id}/lines/{line_id}/add_node", description="Add roof node")
async def add_node(
    project_id: UUID4,
    line_id: UUID4,
    line_data: LineRequest,
    user: Users = Depends(get_current_user)
) -> LineResponse:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound

    line = await LinesDAO.find_by_id(line_id)
    if not line or line.project_id != project_id:
        raise LineNotFound

    updated_line = await LinesDAO.update_(model_id=line_id, type=line_data.type)
    return LineResponse(
        line_id=updated_line.id,
        line_type=updated_line.type,
        line_name=updated_line.name,
        line_length=updated_line.length
    )


@router.patch("/projects/{project_id}/lines/{line_id}/update_line", description="Update line dimensions")
async def update_line(
    project_id: UUID4,
    line_id: UUID4,
    line_data: LineData,
    user: Users = Depends(get_current_user)
) -> LineResponse:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound

    line = await LinesDAO.find_by_id(line_id)
    if not line or line.project_id != project_id:
        raise LineNotFound

    updated_line = await LinesDAO.update_(
        model_id=line_id,
        x_start=line_data.start.x,
        y_start=line_data.start.y,
        x_end=line_data.end.x,
        y_end=line_data.end.y,
        length=round(((line_data.start.x - line_data.end.x) ** 2 + (line_data.start.y - line_data.end.y) ** 2) ** 0.5, 2)
    )
    return LineResponse(
        line_id=updated_line.id,
        line_type=updated_line.type,
        line_name=updated_line.name,
        line_length=updated_line.length
    )


@router.post("/projects/{project_id}/add_line/slopes", description="Add roof slopes")
async def add_slope(
    project_id: UUID4,
    user: Users = Depends(get_current_user)
) -> List[SlopeResponse]:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound

    lines = await LinesDAO.find_all(project_id=project.id)
    lines_data = [
        [line.id, LineData(start=PointData(x=line.x_start_projection, y=line.y_start_projection),
                           end=PointData(x=line.x_end_projection, y=line.y_end_projection))]
        for line in lines
    ]
    slopes = SlopeExtractor(lines_data).extract_slopes()
    existing_slopes = await SlopesDAO.find_all(project_id=project.id)
    existing_names = [slope.name for slope in existing_slopes]

    slopes_list = []
    for slope in slopes:
        slope_name = get_next_name(existing_names)
        existing_names.append(slope_name)
        new_slope = await SlopesDAO.add(
            name=slope_name,
            lines_id=slope,
            project_id=project.id
        )

        lines = await asyncio.gather(*[LinesDAO.find_by_id(line_id) for line_id in slope])
        lines_rotate = align_figure([LineRotate(line.id, (line.x_start_projection, line.y_start_projection),
                                                (line.x_end_projection, line.y_end_projection), line.type)
                                     for line in lines])

        await asyncio.gather(*[
            LinesDAO.update_(
                model_id=line_rotate.id,
                x_start=round(line_rotate.start[0], 2),
                y_start=round(line_rotate.start[1], 2),
                x_end=round(line_rotate.end[0], 2),
                y_end=round(line_rotate.end[1], 2)
            ) for line_rotate in lines_rotate
        ])

        slopes_list.append(SlopeResponse(
            id=new_slope.id,
            slope_name=new_slope.name,
            lines_id=new_slope.lines_id
        ))
    return slopes_list


@router.get("/my_projects/{project_id}/add_line/slopes/{slope_id}", description="View slope")
async def get_slope(
    project_id: UUID4,
    slope_id: UUID4,
    user: Users = Depends(get_current_user)
) -> SlopeResponse:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound

    slope = await SlopesDAO.find_by_id(slope_id)
    if not slope or slope.project_id != project_id:
        raise SlopeNotFound

    return SlopeResponse(
        id=slope.id,
        slope_name=slope.name,
        lines_id=slope.lines_id
    )


@router.post("/my_projects/{project_id}/slopes/{slope_id}/roofs", description="Calculate roof sheets for slope")
async def add_sheets(
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

    lines = await asyncio.gather(*[LinesDAO.find_by_id(line_id) for line_id in slope.lines_id])
    points = [(line.x_start, line.y_start) for line in lines]
    roof = await RoofsDAO.find_by_id(project.roof_id)
    sheets = await create_sheets(Polygon(points), roof)

    existing_sheets = await SheetsDAO.find_all(slope_id=slope_id)
    existing_names = [sheet.name for sheet in existing_sheets]

    sheets_data = []
    for sheet in sheets:
        sheet_name = get_next_name(existing_names)
        existing_names.append(sheet_name)
        new_sheet = await SheetsDAO.add(
            name=sheet_name,
            x_start=sheet[0],
            length=sheet[1],
            area=sheet[2],
            slope_id=slope_id
        )
        sheets_data.append(SheetResponse(
            id=new_sheet.id,
            sheet_name=new_sheet.name,
            sheet_x_start=new_sheet.x_start,
            sheet_length=new_sheet.length,
            sheet_area=new_sheet.area
        ))
    return sheets_data