from datetime import datetime
from typing import Dict, List, Optional
from pydantic import UUID4, BaseModel

from app.base.schemas import AccessoryBDResponse, RoofResponse

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
    address: str
    step: int
    overhang: Optional[float] = None
    datetime_created: datetime
    roof: RoofResponse


class LineResponse(BaseModel):
    id: UUID4
    name: str
    start: PointData
    end: PointData
    is_perimeter: bool
    type: Optional[str] = None
    length: Optional[float] = None


class PointSlopeResponse(BaseModel):
    id: UUID4
    x: float
    y: float


class PointCutoutResponse(PointSlopeResponse):
    number: int


class LineSlopeResponse(BaseModel):
    id: UUID4
    parent_id: UUID4
    name: str
    number: int
    start_id: UUID4
    end_id: UUID4
    start: PointData
    end: PointData
    length: Optional[float] = None


class LengthSlopeResponse(BaseModel):
    id: UUID4
    name: str
    type: int
    start: PointData
    end: PointData
    line_slope_1_id: Optional[UUID4] = None
    line_slope_2_id: Optional[UUID4] = None
    point_1_id: Optional[UUID4] = None
    point_2_id: Optional[UUID4] = None
    length: Optional[float] = None


class SheetResponse(BaseModel):
    id: UUID4
    x_start: float
    y_start: float
    length: float
    area_overall: float
    area_usefull: float
    is_deleted: bool


class DeletedSheetResponse(SheetResponse):
    id: UUID4
    deleted_sheet_id: UUID4
    change_sheet_id: UUID4


class CutoutResponse(BaseModel):
    id: UUID4
    points: list[PointCutoutResponse]


class SlopeResponse(BaseModel):
    id: UUID4
    name: str
    area: Optional[float] = None
    is_left: bool
    points: Optional[list[PointSlopeResponse]] = None
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
    accessory_base: AccessoryBDResponse
    lines_id: list[UUID4]
    lines_length: float
    quantity: int
    color: Optional[str] = None


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
    id: UUID4
    name: str
    amount: Optional[int] = None
    packege_amount: Optional[int] = 250
    price: Optional[float] = None
    ral: None


class SlopeEstimateResponse(BaseModel):
    name: str
    area_full: float
    area_overall: float
    area_usefull: float


class RoofEstimateResponse(RoofResponse):
    price: None


class MaterialEstimateResponse(BaseModel):
    name: str
    material: str
    color: str


class EstimateResponse(AboutResponse):
    PS: Optional[str] = None
    PZ: Optional[str] = None
    K: Optional[str] = None
    slopes: Optional[list[SlopeEstimateResponse]] = None
    sheets_amount: Optional[Dict[float, int]] = None
    accessories: Optional[list[AccessoriesResponse]] = None
    screws: Optional[list[ScrewsEstimateResponse]] = None


class ProjectResponse(AboutResponse):
    lines: Optional[List[LineResponse]] = None
    slopes: Optional[List[SlopeResponse]] = None
    accessories: Optional[List[AccessoriesResponse]] = None
    deleted_sheets: Optional[list[DeletedSheetResponse]] = None

# Request


class ProjectRequest(BaseModel):
    name: str
    address: str
    roof_id: UUID4


class LineRequest(BaseModel):
    start: PointData
    end: PointData
    is_perimeter: bool


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
    lines_id: list[UUID4]
    accessory_bd_id: UUID4


class AccessoriesUpdateRequest(BaseModel):
    lines_id: list[UUID4]
    accessory_id: UUID4


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
