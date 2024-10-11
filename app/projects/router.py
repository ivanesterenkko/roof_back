import json
from fastapi import APIRouter, Depends
from typing import List
from pydantic import UUID4
from shapely.geometry import Polygon
from app.base.dao import RoofsDAO
from app.exceptions import LineNotFound, ProjectAlreadyExists, ProjectNotFound, SlopeNotFound
from app.projects.schemas import LineData, LineRequest, LineResponce, PointData, ProjectRequest, ProjectResponce, SheetResponce,  SlopeResponse
from app.projects.dao import LinesDAO, ProjectsDAO, SheetsDAO, SlopesDAO
from app.projects.slope import LineRotate, SlopeExtractor, align_figure, create_hole, create_sheets, get_next_name
from app.users.dependencies import get_current_user
from app.users.models import Users

router = APIRouter(prefix="/roofs", tags=["Roofs"])

wight = 0.9

@router.get("/projects", description="Получить список проектов")
async def get_projects(user: Users = Depends(get_current_user)) -> List[ProjectResponce]:
    projects = await ProjectsDAO.find_all(user_id=user.id)
    projects_answer = []
    for project in projects:
        projects_answer.append(ProjectResponce(project_id=project.id, project_name=project.name, datatime_created=(project.datetime_created).strftime("%d.%m.%Y в %H:%M")))
    return projects_answer

@router.post("/projects", description="Создание проекта кровли")
async def add_project(project:ProjectRequest,
                      user: Users = Depends(get_current_user)) -> ProjectResponce:
    already_project = await ProjectsDAO.find_one_or_none(name=project.name)
    if already_project is not None:
         raise ProjectAlreadyExists 
    result = await ProjectsDAO.add(name=project.name,
                          full_name_customer=project.full_name_customer,
                          is_company=project.is_company,
                          company_name=project.company_name if project.is_company else None, 
                          customer_contacts=project.customer_contacts,
                          address=project.address,
                          roof_id=project.roof_id,
                          user_id=user.id)
    return ProjectResponce(project_id=result.id, 
                           project_name=result.name, 
                           datatime_created=(result.datetime_created).strftime("%d.%m.%Y в %H:%M"))

@router.post("/projects/{project_id}/add_line", description="Создание геометрии крыши")
async def add_line(project_id: UUID4, 
                   line: LineData, 
                   user: Users = Depends(get_current_user)) -> List[SSlope]:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project:
        raise ProjectNotFound
    if project.user_id != user.id:
        raise ProjectNotFound
    existing_lines = await LinesDAO.find_all(project_id=project.id)
    existing_names = [line.name for line in existing_lines]
    line_name = get_next_name(existing_names)
    result = await LinesDAO.add(project_id=project_id,
                                name=line_name,
                                x_start_projection=line.start.x, 
                                y_start_projection=line.start.y, 
                                x_end_projection=line.end.x, 
                                y_end_projection=line.end.y, 
                                length=round(((line.start.x-line.end.x)**2 + (line.start.y-line.end.y)**2)**0.5, 2))

@router.get("/my_projects/{project_id}", description="Получение проекта пользователя")
async def get_project(project_id: int, user: Users = Depends(get_current_user)) -> SProject:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project:
        raise ProjectNotFound
    if project.user_id != user.id:
        raise ProjectNotFound
    return SProject(id=project.id, lines=json.loads(project.lines)) 

@router.post("/projects/{project_id}/add_line/slopes", description="Разметка скатов")
async def add_slope(project_id: UUID4, 
                    user: Users = Depends(get_current_user)) -> List[SlopeResponse]:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project:
        raise ProjectNotFound
    if project.user_id != user.id:
        raise ProjectNotFound
    lines = await LinesDAO.find_all(project_id=project.id)
    lines_data = [ [line.id,
                    LineData(start=PointData(x=line.x_start_projection, y=line.y_start_projection),
                             end=PointData(x=line.x_end_projection, y=line.y_end_projection))]
                             for line in lines ]
    slopes = SlopeExtractor(lines_data).extract_slopes()
    existing_slopes = await SlopesDAO.find_all(project_id=project.id)
    existing_names = [slope.name for slope in existing_slopes]
    slopes_list = []
    for slope in slopes:
        slope_name = get_next_name(existing_names)
        existing_names.append(slope_name)
        result = await SlopesDAO.add(name=slope_name,
                                     lines_id = slope,
                                     project_id=project.id)
        lines = []
        for line_id in slope:
            line = await LinesDAO.find_by_id(line_id)
            lines.append(LineRotate(line.id, (line.x_start_projection, line.y_start_projection), (line.x_end_projection, line.y_end_projection), line.type))
        lines_rotate = align_figure(lines)
        for line_rotate in lines_rotate:
            await LinesDAO.update_(model_id=line_rotate.id, 
                                   x_start=round(line_rotate.start[0],2), 
                                   y_start=round(line_rotate.start[1],2),
                                   x_end=round(line_rotate.end[0],2), 
                                   y_end=round(line_rotate.end[1],2))
        slopes_list.append(SlopeResponse(id=result.id, 
                                         slope_name=result.name,
                                         lines_id=result.lines_id))
    return slopes_list

@router.get("/my_projects/{project_id}/add_line/slopes/{slope_id}", description="Просмотр ската")
async def get_slope(project_id: UUID4,
                    slope_id: UUID4, 
                    user: Users = Depends(get_current_user)) -> SlopeResponse:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project:
        raise ProjectNotFound
    if project.user_id != user.id:
        raise ProjectNotFound
    slope = await SlopesDAO.find_by_id(slope_id)
    if not slope or slope.project_id != project_id:
        raise SlopeNotFound
    return SlopeResponse(id=slope.id, 
                         slope_name=slope.name,
                         lines_id=slope.lines_id)

# @router.patch("/my_projects/{project_id}/slopes/{slope_id}", description="Создание выреза в скате")
# async def add_hole(slope_id: int, 
#                    points: List[PointData],
#                    user: Users = Depends(get_current_user)) -> None:
#     slope = await SlopesDAO.find_by_id(slope_id)
#     if not slope:
#         raise SlopeNotFound
#     hole_points_json = json.dumps([point.dict() for point in points])
#     await SlopesDAO.update_(model_id=slope_id, hole_points=hole_points_json)

@router.post("/my_projects/{project_id}/slopes/{slope_id}/roofs", description="Рассчет кровельных листов для ската")
async def add_sheets(project_id: UUID4,
                     slope_id: UUID4,
                     user: Users = Depends(get_current_user)) -> List[SheetResponce]:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project:
        raise ProjectNotFound
    if project.user_id != user.id:
        raise ProjectNotFound
    slope = await SlopesDAO.find_by_id(slope_id)
    if not slope or slope.project_id != project_id:
        raise SlopeNotFound
    lines = [await LinesDAO.find_by_id(line_id) for line_id in slope.lines_id]
    points = [(line.x_start, line.y_start) for line in lines ]
    roof = await RoofsDAO.find_by_id(project.roof_id)
    sheets = await create_sheets(Polygon(points), roof)
    existing_sheets = await SheetsDAO.find_all(slope_id=slope_id)
    existing_names = [sheet.name for sheet in existing_sheets]
    sheets_data = []
    for sheet in sheets:
        sheet_name = get_next_name(existing_names)
        existing_names.append(sheet_name)
        result = await SheetsDAO.add(name=sheet_name,
                               x_start=sheet[0], 
                               length=sheet[1], 
                               area=sheet[2],
                               slope_id=slope_id)
        sheets_data.append(SheetResponce(id=result.id, 
                                         sheet_name=result.name, 
                                         sheet_x_start=result.x_start,
                                         sheet_length=result.length,
                                         sheet_area=result.area ))
    return sheets_data



    
