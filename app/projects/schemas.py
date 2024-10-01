from typing import List, Tuple
from pydantic import BaseModel


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

class SProjects(BaseModel):
    id: int
    lines: str

class SSlopes(BaseModel):
    id: int
    points: List[PointData]

class Sid(BaseModel):
    id: int
