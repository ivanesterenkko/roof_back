from datetime import datetime
from typing import List, Tuple
from pydantic import UUID4, BaseModel


class PointData(BaseModel):
    x: float
    y: float

    def __hash__(self):
        return hash((self.x, self.y))

    def __eq__(self, other):
        if isinstance(other, PointData):
            return self.x == other.x and self.y == other.y
        
    def __lt__(self, other):
        if isinstance(other, PointData):
            return (self.x, self.y) < (other.x, other.y)
        return NotImplemented

class LineData(BaseModel):
    start: PointData
    end: PointData


class ProjectResponse(BaseModel):
    id: UUID4
    project_name: str
    project_step: int
    datetime_created: datetime

class ProjectRequest(BaseModel):
    name: str
    address: str
    roof_id: UUID4

class LineResponse(BaseModel):
    id: UUID4
    line_name: str
    coords: LineData
    line_type: str = ''
    line_length: float

class LineSlopeResponse(BaseModel):
    id: UUID4
    line_id: UUID4
    line_name: str
    coords: LineData
    line_length: float
    
class LineRequest(BaseModel):
    type: str

class SlopeResponse(BaseModel):
    id: UUID4
    slope_name: str
    lines: list[LineSlopeResponse]

class SheetResponse(BaseModel):
    id: UUID4
    sheet_x_start: float
    sheet_y_start: float
    sheet_length: float
    sheet_area_overall: float
    sheet_area_usefull: float

class SlopeSheetsResponse(BaseModel):
    id: UUID4
    slope_name: str
    slope_area: float
    sheets: list[SheetResponse]
    
class CutoutResponse(BaseModel):
    cutout_id: UUID4
    cutout_name: str
    cutout_points: list[PointData]
    slope_id: UUID4

class AccessoriesRequest(BaseModel):
    name: str
    lines_id: list[UUID4]
    parameters: list[float]

class AccessoriesResponse(BaseModel):
    id: UUID4
    accessory_name: str
    lines_id: list[UUID4]
    parameters: list[float]
    quantity: int
