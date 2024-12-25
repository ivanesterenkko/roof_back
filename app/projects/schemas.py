from datetime import datetime
from typing import Dict, List, Optional
from pydantic import UUID4, BaseModel

# Line and Point


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


class LinesData(BaseModel):
    start: PointData
    end: PointData
    type: str

# Project


class ProjectResponse(BaseModel):
    id: UUID4
    project_name: str
    project_step: int
    datetime_created: datetime


class ProjectRequest(BaseModel):
    name: str
    address: str
    roof_id: UUID4


class MaterialRequest(BaseModel):
    name: str
    material: str
    color: str


class MaterialResponse(BaseModel):
    id: UUID4
    name: str
    material: str
    color: str


# Line


class LineRequestUpdate(BaseModel):
    id: UUID4
    coords: LineData


class LineUpdateRequest(BaseModel):
    id: UUID4
    length: float


class LineResponse(BaseModel):
    id: UUID4
    line_name: str
    coords: LineData
    line_type: Optional[str] = ""
    line_length: float


class LineSlopeResponse(BaseModel):
    id: UUID4
    line_id: UUID4
    line_name: str
    coords: LineData
    line_length: float


class LineRequest(BaseModel):
    type: str


# Slope, Cutout and Sheet


class SlopeResponse(BaseModel):
    id: UUID4
    slope_name: str
    slope_length: float
    slope_area: float | None
    lines: list[LineSlopeResponse]


class SheetResponse(BaseModel):
    id: UUID4
    sheet_x_start: float
    sheet_y_start: float
    sheet_length: float
    sheet_area_overall: float
    sheet_area_usefull: float


class SheetRequest(BaseModel):
    id: UUID4
    sheet_x_start: float
    sheet_y_start: float
    sheet_length: float


class NewSheetRequest(BaseModel):
    sheet_x_start: float
    sheet_y_start: float
    sheet_length: float


class CutoutResponse(BaseModel):
    id: UUID4
    cutout_name: str
    cutout_points: list[PointData]


class SlopeSheetsResponse(BaseModel):
    id: UUID4
    slope_name: str
    slope_area: float
    slope_length: float
    lines: list[LineSlopeResponse]
    sheets: list[SheetResponse]
    cutouts: list[CutoutResponse]


# Accessoies


class AccessoriesRequest(BaseModel):
    name: str
    type: str
    lines_id: list[UUID4]
    length: float
    width: Optional[float] = None


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


class Step6Response(BaseModel):
    lines: list[LineResponse]
    accessories: list[AccessoriesResponse]


class Step3Response(BaseModel):
    general_plan: List[LineResponse]
    slopes: List[SlopeResponse]


class Step1Response(BaseModel):
    id: UUID4
    project_name: str
    project_address: str
    roof_id: UUID4


class Step5Response(BaseModel):
    general_plan: List[LineResponse]
    slopes: List[SlopeSheetsResponse]
