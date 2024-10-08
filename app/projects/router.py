from asyncio import sleep
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi_cache.decorator import cache
from typing import List
from pydantic import UUID4, TypeAdapter
from shapely.geometry import Polygon
from app.exceptions import ProjectAlreadyExists, ProjectNotFound, SlopeNotFound
from app.projects.schemas import LineData, PointData, ProjectRequest, ProjectResponce, SProject, SRoof, SSlope, SlopeResponse
from app.projects.dao import LinesDAO, ProjectsDAO, RoofsDAO, SlopesDAO
from app.projects.slope import SlopeExtractor, create_hole, create_roofs
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
                          user_id=user.id)
    return ProjectResponce(project_id=result.id, project_name=result.name, datatime_created=(result.datetime_created).strftime("%d.%m.%Y в %H:%M"))

@router.patch("/projects/{project_id}/add_line", description="Создание геометрии крыши")
async def add_line(project_id: UUID4, 
                   line: LineData, 
                   user: Users = Depends(get_current_user)) -> List[SSlope]:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project:
        raise ProjectNotFound
    if project.user_id != user.id:
        raise ProjectNotFound
    result = await LinesDAO.add(project_id=project_id, 
                                x_start=line.start.x, 
                                y_start=line.start.y, 
                                x_end=line.end.x, 
                                y_end=line.end.y, 
                                length=round(((line.start.x-line.end.x)**2 + (line.start.y-line.end.y)**2)**0.5, 2))

@router.get("/my_projects/{project_id}", description="Получение проекта пользователя")
async def get_project(project_id: int, user: Users = Depends(get_current_user)) -> SProject:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project:
        raise ProjectNotFound
    if project.user_id != user.id:
        raise ProjectNotFound
    return SProject(id=project.id, lines=json.loads(project.lines)) 

@router.get("/my_projects/{project_id}/slopes", description="Получение скатов в данном проекте")
async def get_slopes(project_id: int, 
                     user: Users = Depends(get_current_user)) -> List[SSlope]:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project:
        raise ProjectNotFound
    if project.user_id != user.id:
        raise ProjectNotFound
    slopes = await SlopesDAO.find_all(project_id=project.id)
    slopes_answer = []
    for slope in slopes:
        points_list = json.loads(slope.points)
        slopes_answer.append(SSlope(id=slope.id, points=points_list))
    return slopes_answer 

@router.get("/my_projects/{project_id}/slopes/{slope_id}", description="Получение ската в данном проекте")
async def get_slope(slope_id: int, 
                     user: Users = Depends(get_current_user)) -> SSlope:
    slope = await SlopesDAO.find_by_id(slope_id)
    if not slope:
        raise SlopeNotFound
    return SSlope(id=slope.id, points=json.loads(slope.points))

@router.patch("/my_projects/{project_id}/slopes/{slope_id}", description="Создание выреза в скате")
async def add_hole(slope_id: int, 
                   points: List[PointData],
                   user: Users = Depends(get_current_user)) -> None:
    slope = await SlopesDAO.find_by_id(slope_id)
    if not slope:
        raise SlopeNotFound
    hole_points_json = json.dumps([point.dict() for point in points])
    await SlopesDAO.update_(model_id=slope_id, hole_points=hole_points_json)

@router.post("/my_projects/{project_id}/slopes/{slope_id}/roofs", description="Создание кровли для ската")
async def add_roofs(slope_id: int,
                    user: Users = Depends(get_current_user)) -> List[SRoof]:
    slope = await SlopesDAO.find_by_id(slope_id)
    if not slope:
        raise SlopeNotFound
    points_list = json.loads(slope.points)
    points = [PointData(**point_dict) for point_dict in points_list]
    coordinates = [(point.x, point.y) for point in points]
    figure = Polygon(coordinates)
    if slope.hole_points is not None:
        hole_points_list = json.loads(slope.hole_points)
        hole_points = [PointData(**point_dict) for point_dict in hole_points_list]
        figure = create_hole(figure, hole_points)
    roofs = await create_roofs(figure)
    for roof in roofs:
        roof_lenght = roof[3].y - roof[0].y
        roof_square = wight * roof_lenght
        roof_points_json = json.dumps([roof_point.dict() for roof_point in roof])
        await RoofsDAO.add(slope_id=slope_id, points=roof_points_json, lenght=roof_lenght, square=roof_square)
    roofs_bd = await RoofsDAO.find_all(slope_id=slope_id)
    roofs_answer = []
    for roof in roofs_bd:
        points_list = json.loads(roof.points)
        roofs_answer.append(SRoof(id=roof.id, points=points_list, lenght=roof.lenght, square=roof.square))
    return roofs_answer 



    
