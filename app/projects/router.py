from fastapi import APIRouter, Depends
from typing import List
from pydantic import UUID4
from shapely.geometry import Polygon
from app.base.dao import RoofsDAO
from app.exceptions import LineNotFound, ProjectAlreadyExists, ProjectNotFound, ProjectStepLimit, SheetNotFound, SlopeNotFound
from app.projects.schemas import AccessoriesEstimateResponse, AccessoriesRequest, AccessoriesResponse, CutoutResponse, EstimateResponse, LineData, LineRequest, LineResponse, LineSlopeResponse, PointData, ProjectMaterialRequest, ProjectMaterialResponse, ProjectRequest, ProjectResponse, SheetEstimateResponse, SheetResponse, SlopeEstimateResponse, SlopeResponse, SlopeSheetsResponse
from app.projects.dao import AccessoriesDAO, CutoutsDAO, LinesDAO, LinesSlopeDAO, ProjectsDAO, SheetsDAO, SlopesDAO
from app.projects.slope import LineRotate, SlopeExtractor, align_figure, create_hole, create_sheets, get_next_name
from app.users.dependencies import get_current_user
from app.users.models import Users
import asyncio
from collections import defaultdict

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
    existing_project = await ProjectsDAO.find_one_or_none(name=project.name)
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
@router.get("/projects/{project_id}/lines/{line_id}", description="Get list of projects")
async def get_line(line_id: UUID4,
                   user: Users = Depends(get_current_user)) -> LineResponse:
    line = await LinesDAO.find_by_id(line_id)
    return LineResponse(
        id=line.id,
        line_type=line.type,
        line_name=line.name,
        line_length=line.length,
        coords=LineData(start=PointData(x=line.x_start, y=line.y_start), 
                            end=PointData(x=line.x_end, y=line.y_end))
    )

@router.delete("/projects/{project_id}/lines/{line_id}", description="Delete a line")
async def delete_line(
    project_id: UUID4,
    line_id: UUID4,
    user: Users = Depends(get_current_user)
) -> None:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound

    line = await LinesDAO.find_by_id(line_id)
    if not line or line.project_id != project_id:
        raise LineNotFound
    await LinesDAO.delete_(model_id=line_id)

@router.post("/projects/{project_id}/lines_perimeter", description="Create roof geometry")
async def add_line_perimeter(
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
        x_start=line.start.x,
        y_start=line.start.y,
        x_end=line.end.x,
        y_end=line.end.y,
        type="Perimeter",
        length=round(((line.start.x - line.end.x) ** 2 + (line.start.y - line.end.y) ** 2) ** 0.5, 2)
    )
    return LineResponse(
        id=new_line.id,
        line_name=new_line.name,
        line_type=new_line.type,
        line_length=new_line.length,
        coords=LineData(start=PointData(x=new_line.x_start, y=new_line.y_start), 
                            end=PointData(x=new_line.x_end, y=new_line.y_end))
    )

@router.post("/projects/{project_id}/lines_nontype", description="Create roof geometry")
async def add_line_nontype(
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
        type='',
        x_start=line.start.x,
        y_start=line.start.y,
        x_end=line.end.x,
        y_end=line.end.y,
        length=round(((line.start.x - line.end.x) ** 2 + (line.start.y - line.end.y) ** 2) ** 0.5, 2)
    )
    return LineResponse(
        id=new_line.id,
        line_name=new_line.name,
        line_type=new_line.type,
        line_length=new_line.length,
        coords=LineData(start=PointData(x=new_line.x_start, y=new_line.y_start), 
                            end=PointData(x=new_line.x_end, y=new_line.y_end))
    )

@router.patch("/projects/{project_id}/lines/{line_id}", description="Update line dimensions")
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
        id=updated_line.id,
        line_type=updated_line.type,
        line_name=updated_line.name,
        line_length=updated_line.length,
        coords=LineData(start=PointData(x=updated_line.x_start, y=updated_line.y_start), 
                            end=PointData(x=updated_line.x_end, y=updated_line.y_end))
    )

@router.patch("/projects/{project_id}/lines/{line_id}/node_line", description="Add roof node")
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
        id=updated_line.id,
        line_type=updated_line.type,
        line_name=updated_line.name,
        line_length=updated_line.length,
        coords=LineData(start=PointData(x=updated_line.x_start, y=updated_line.y_start), 
                            end=PointData(x=updated_line.x_end, y=updated_line.y_end))
    )

@router.get("/projects/{project_id}/slopes/{slope_id}", description="View slope")
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
    lines = await LinesSlopeDAO.find_all(slope_id=slope_id)

    return SlopeResponse(
        id=slope.id,
        slope_name=slope.name,
        lines=[ LineSlopeResponse(id=line.id,
                                  line_id=line.line_id,
                                  line_name=line.name,
                                  line_length=line.length,
                                  coords=LineData(start=PointData(x=line.x_start, y=line.y_start), 
                                                     end=PointData(x=line.x_end, y=line.y_end))
                                ) for line in lines]
    )

@router.post("/projects/{project_id}/slopes", description="Add roof slopes")
async def add_slope(
    project_id: UUID4,
    user: Users = Depends(get_current_user)
) -> List[SlopeResponse]:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound

    lines = await LinesDAO.find_all(project_id=project.id)
    lines_data = [
        [line.id, LineData(start=PointData(x=line.x_start, y=line.y_start),
                           end=PointData(x=line.x_end, y=line.y_end))]
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
            project_id=project.id
        )

        lines = await asyncio.gather(*[LinesDAO.find_by_id(line_id) for line_id in slope])
        lines_rotate = align_figure([LineRotate(line.id, line.name, (line.x_start, line.y_start),
                                                (line.x_end, line.y_end), line.type)
                                     for line in lines])
        count = 1
        lines_slope = []
        for line_rotate in lines_rotate:
            line_slope =await LinesSlopeDAO.add(
                    line_id=line_rotate.id,
                    name=line_rotate.name,
                    x_start=line_rotate.start[0],
                    y_start=line_rotate.start[1],
                    x_end=line_rotate.end[0],
                    y_end=line_rotate.end[1],
                    length=round(((line_rotate.start[0] - line_rotate.end[0]) ** 2 + (line_rotate.start[1] - line_rotate.end[1]) ** 2) ** 0.5, 2),
                    number=count,
                    slope_id=new_slope.id
                )
            count += 1
            lines_slope.append(line_slope)
        slopes_list.append(SlopeResponse(
            id=new_slope.id,
            slope_name=new_slope.name,
            lines=[ LineSlopeResponse(id=line.id,
                                      line_id=line.line_id,
                                      line_name=line.name,
                                      line_length=line.length,
                                      coords=LineData(start=PointData(x=line.x_start, y=line.y_start), 
                                                      end=PointData(x=line.x_end, y=line.y_end))
                                ) for line in lines_slope]
        ))
    return slopes_list

@router.patch("/projects/{project_id}/slopes/{slope_id}/lines_slope/{line_id}", description="Update line slope dimensions")
async def update_line_slope(
    project_id: UUID4,
    slope_id: UUID4,
    line_id: UUID4,
    line_data: LineData,
    user: Users = Depends(get_current_user)
) -> LineResponse:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    slope = await SlopesDAO.find_by_id(slope_id)
    if not slope or slope.project_id != project_id:
        raise SlopeNotFound
    line = await LinesSlopeDAO.find_by_id(line_id)
    if not line or line.project_id != project_id:
        raise LineNotFound
    updated_line = await LinesSlopeDAO.update_(
        model_id=line_id,
        x_start=line_data.start.x,
        y_start=line_data.start.y,
        x_end=line_data.end.x,
        y_end=line_data.end.y,
        length=round(((line_data.start.x - line_data.end.x) ** 2 + (line_data.start.y - line_data.end.y) ** 2) ** 0.5, 2)
    )
    return LineSlopeResponse(
        id=updated_line.id,
        line_id=updated_line.line_id,
        line_name=updated_line.name,
        line_length=updated_line.length,
        coords=LineData(start=PointData(x=updated_line.x_start, y=updated_line.y_start), 
                            end=PointData(x=updated_line.x_end, y=updated_line.y_end))
    )

@router.delete("/projects/{project_id}/add_line/slopes/{slope_id}", description="Delete cutout")
async def delete_cutout(
    slope_id: UUID4,
    cutout_id: UUID4,
    user: Users = Depends(get_current_user)
) -> None:
    cutout = await CutoutsDAO.find_by_id(cutout_id)
    if not cutout or cutout.slope_id != slope_id:
        raise SlopeNotFound
    await CutoutsDAO.delete_(model_id=cutout_id)

@router.post("/projects/{project_id}/slopes/{slope_id}", description="Add cutout")
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
        cutout_id=new_cutout.id,
        cutout_name=new_cutout.name,
        cutout_points=points,
        slope_id=new_cutout.slope_id
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
    return [ SheetResponse(
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
    if cutouts is None:
        figure = Polygon(points)
    else:
        figure = Polygon(points)
        for cutout in cutouts:
            points_cut = list(zip(cutout.x_coords, cutout.y_coords))
            figure = create_hole(figure, points_cut)
    area = figure.area
    slope = await SlopesDAO.update_(model_id=slope_id, 
                            area=area)
    roof = await RoofsDAO.find_by_id(project.roof_id)
    sheets = await create_sheets(figure, roof)
    sheets_data = []
    for sheet in sheets:
        new_sheet = await SheetsDAO.add(
            x_start=sheet[0],
            y_start=sheet[1],
            length=sheet[2],
            area_overall = sheet[3],
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
    return SlopeSheetsResponse(id=slope.id,
                               slope_name=slope.name,
                               slope_area=slope.area,
                               sheets=sheets_data
    )

@router.patch("/projects/{project_id}/slopes/{slope_id}/sheets/{sheet_id}", description="Calculate roof sheets for slope")
async def update_sheet(
    project_id: UUID4,
    slope_id: UUID4,
    sheet_id: UUID4,
    sheet_data: PointData, 
    user: Users = Depends(get_current_user)
) -> List[SheetResponse]:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound

    slope = await SlopesDAO.find_by_id(slope_id)
    if not slope or slope.project_id != project_id:
        raise SlopeNotFound
    sheet = await SheetsDAO.find_by_id(sheet_id)
    if not sheet or sheet.slope_id != slope_id:
        raise SheetNotFound
    
    updated_sheet = await SheetsDAO.update_(
        model_id=sheet_id,
        x_start=sheet_data.start.x,
        y_start=sheet_data.start.y,
    )
    return SheetResponse(
        id=updated_sheet.id,
            sheet_x_start=updated_sheet.x_start,
            sheet_y_start=updated_sheet.y_start,
            sheet_length=updated_sheet.length,
            sheet_area_overall=sheet.area_overall,
            sheet_area_usefull=sheet.area_usefull
    )

@router.patch("/projects/{project_id}/slopes/{slope_id}/sheets/", description="Calculate roof sheets for slope")
async def update_sheets(
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
                result = await SheetsDAO.update_(model_id=previous_sheet.id, 
                                        length=new_length
                )
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
    return [ AccessoriesResponse(
            id=accessory.id,
            accessory_name=accessory.name,
            lines_id=accessory.lines_id,
            parameters=accessory.parameters,
            quantity=accessory.quantity
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
    length = 0
    for line in lines:
        length += line.length
    new_accessory = await AccessoriesDAO.add(
        name=accessory.name,
        lines_id=accessory.lines_id,
        parameters=accessory.parameters,
        quantity=length,
        project_id=project_id
    )
    return AccessoriesResponse(
        id=new_accessory.id,
        accessory_name=new_accessory.name,
        lines_id=new_accessory.lines_id,
        parameters=new_accessory.parameters,
        quantity=new_accessory.quantity
    )
@router.patch("/projects/{project_id}/materials")
async def update_material_project(
    project_id: UUID4,
    data: ProjectMaterialRequest,
    user: Users = Depends(get_current_user)
) -> ProjectMaterialResponse:
    project = await ProjectsDAO.find_by_id(project_id)
    if not project or project.user_id != user.id:
        raise ProjectNotFound
    new_project = await ProjectsDAO.update_(
        model_id=project_id,
        material=data.material,
        color=data.color
        )
    return ProjectMaterialResponse(
        id=project_id,
        project_name=new_project.name,
        project_step=new_project.step,
        project_material=new_project.material,
        project_color=new_project.color
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
    slopes_estimate = []
    for slope in slopes:
        sheets = await SheetsDAO.find_all(slope_id=slope.id)
        sheets_estimate = [
            SheetEstimateResponse(
                sheet_length=sheet.length,
                sheet_area_overall=sheet.area_overall,
                sheet_area_usefull=sheet.area_usefull
            ) for sheet in sheets
        ]
        slopes_estimate.append(
            SlopeEstimateResponse(
                slope_name=slope.name,
                slope_area=slope.area,
                slope_sheets=sheets_estimate
            )
        )
    accessories = await AccessoriesDAO.find_all(project_id=project_id)
    accessories_estimate = [
        AccessoriesEstimateResponse(
            accessory_name=accessory.name,
            accessory_quantity=accessory.quantity
        ) for accessory in accessories
    ]
    return EstimateResponse(
        project_name=project.name,
        project_address=project.address,
        slopes=slopes_estimate,
        accessories=accessories_estimate,
        material=project.material,
        color=project.color
    )