from datetime import datetime
from typing import Dict, List, Optional
from pydantic import UUID4, BaseModel

from app.base.schemas import RoofResponse

# Response


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


class AboutResponse(BaseModel):
    id: UUID4
    name: str
    step: int
    datetime_created: datetime
    roof: RoofResponse


class LineResponse(BaseModel):
    id: UUID4
    name: str
    start: PointData
    end: PointData
    type: Optional[str] = None
    length: Optional[float] = None


class LineSlopeResponse(BaseModel):
    id: UUID4
    parent_id: UUID4
    name: str
    start: PointData
    end: PointData
    length: Optional[float] = None


class LengthSlopeResponse(BaseModel):
    id: UUID4
    start: PointData
    end: PointData
    point_id: UUID4
    line_slope_id: UUID4
    length: Optional[float] = None


class SheetResponse(BaseModel):
    id: UUID4
    sheet_x_start: float
    sheet_y_start: float
    sheet_length: float
    sheet_area_overall: float
    sheet_area_usefull: float


class CutoutResponse(BaseModel):
    id: UUID4
    name: str
    points: list[PointData]


class SlopeResponse(BaseModel):
    id: UUID4
    name: str
    area: Optional[float] = None
    lines: Optional[list[LineSlopeResponse]] = None
    length_line: Optional[list[LengthSlopeResponse]] = None
    cutouts: Optional[list[CutoutResponse]] = None
    sheets: Optional[list[SheetResponse]] = None


class MaterialResponse(BaseModel):
    id: UUID4
    name: str
    material: str
    color: str


class AccessoriesResponse(BaseModel):
    id: UUID4
    accessory_name: str
    type: str
    lines_id: list[UUID4]
    lines_length: float
    length: float
    width: Optional[float] = None
    amount: int


# Estimate


class AccessoriesEstimateResponse(BaseModel):
    id: UUID4
    name: str
    type: str
    length: Optional[float] = None
    overall_length: Optional[float] = None
    amount: int
    price: Optional[float] = None


class SofitsEstimateResponce(BaseModel):
    id: UUID4
    name: str
    type: str
    length: Optional[float] = None
    width: Optional[float] = None
    overall_length: Optional[float] = None
    amount: int
    price: Optional[float] = None


class ScrewsEstimateResponse(BaseModel):
    name: str
    amount: Optional[int] = None
    packege_amount: Optional[int] = 250
    price: Optional[float] = None


class SlopeEstimateResponse(BaseModel):
    slope_name: str
    slope_length: float
    slope_area: float
    area_overall: float
    area_usefull: float


class RoofEstimateResponse(BaseModel):
    roof_name: str
    roof_type: str
    price: Optional[float] = None
    roof_overall_width: float
    roof_useful_width: float
    roof_overlap: float
    roof_max_length: float
    roof_max_length_standart: float


class MaterialEstimateResponse(BaseModel):
    name: str
    material: str
    color: str


class EstimateResponse(BaseModel):
    project_name: str
    project_address: str
    materials: list[MaterialEstimateResponse]
    roof_base: RoofEstimateResponse
    PS: Optional[str] = None
    PZ: Optional[str] = None
    K: Optional[str] = None
    slopes: list[SlopeEstimateResponse]
    sheets_amount: Dict[float, int]
    accessories: list[AccessoriesEstimateResponse]
    sofits: list[SofitsEstimateResponce]
    screws: list[ScrewsEstimateResponse]
    sheets_extended: list[str]


class ProjectResponse(AboutResponse):
    lines: Optional[List[LineResponse]] = None
    slopes: Optional[List[SlopeResponse]] = None

# Request


class ProjectRequest(BaseModel):
    name: str
    address: str
    roof_id: UUID4


class LineRequest(BaseModel):
    start: PointData
    end: PointData
    type: Optional[str] = None


class MaterialRequest(BaseModel):
    name: str
    material: str
    color: str


class LineUpdateRequest(BaseModel):
    id: UUID4
    length: float


class LinesSizesRequest(BaseModel):
    id: UUID4
    length: float


class LengthSizesRequest(BaseModel):
    id: UUID4
    length: float


class SlopeSizesRequest(BaseModel):
    lines: list[LinesSizesRequest]
    length_line: list[LengthSizesRequest]


class NodeRequest(BaseModel):
    type: str
    lines_id: list[UUID4]


# class SheetRequest(BaseModel):
#     id: UUID4
#     sheet_x_start: float
#     sheet_y_start: float
#     sheet_length: float


# class NewSheetRequest(BaseModel):
#     sheet_x_start: float
#     sheet_y_start: float
#     sheet_length: float


class AccessoriesRequest(BaseModel):
    name: str
    type: str
    lines_id: list[UUID4]
    length: float
    width: Optional[float] = None


class EstimateRequest(BaseModel):
    project_name: str
    project_address: str
    materials: list[MaterialEstimateResponse]
    roof_base: RoofEstimateResponse
    PS: Optional[str] = None
    PZ: Optional[str] = None
    K: Optional[str] = None
    slopes: list[SlopeEstimateResponse]
    sheets_amount: Dict[float, int]
    accessories: list[AccessoriesEstimateResponse]
    sofits: list[SofitsEstimateResponce]
    screws: list[ScrewsEstimateResponse]
