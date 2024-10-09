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

class ProjectResponce(BaseModel):
    project_id: UUID4
    project_name: str
    datatime_created: str

class ProjectRequest(BaseModel):
    name: str
    full_name_customer: str
    is_company: bool
    company_name: str
    customer_contacts: str
    address: str

class LineResponce(BaseModel):
    line_id: UUID4
    line_name: str
    line_length: float
    
class SRoof(BaseModel):
    id: int
    points: List[PointData]
    lenght: float
    square: float
    
class Sid(BaseModel):
    id: int
