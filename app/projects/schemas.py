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


class SlopeResponse(BaseModel):
    id: UUID4
    slope_name: str
    lines_id: list[UUID4]

class ProjectResponse(BaseModel):
    project_id: UUID4
    project_name: str
    datetime_created: str

class ProjectRequest(BaseModel):
    name: str
    full_name_customer: str
    is_company: bool
    company_name: str
    customer_contacts: str
    address: str
    roof_id: UUID4

class LineResponse(BaseModel):
    line_id: UUID4
    line_name: str
    line_type: str = ''
    line_length: float

class LineRequest(BaseModel):
    type: str

class SheetResponse(BaseModel):
    id: UUID4
    sheet_name: str
    sheet_x_start: float
    sheet_length: float
    sheet_area: float
