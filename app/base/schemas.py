from typing import List, Optional, Tuple
from pydantic import UUID4, BaseModel


class RoofRequest(BaseModel):
    name: str
    type: str
    overall_width: float
    useful_width: float
    overlap: float
    len_wave: float
    max_length: float
    min_length: float
    imp_sizes: Optional[List[Tuple[float, float]]] = None


class AccessoryBDRequest(BaseModel):
    name: str
    type: str
    parent_type: str
    price: int
    length: float
    overlap: float


class AccessoryBDResponse(BaseModel):
    id: UUID4
    name: str
    type: str
    parent_type: str
    price: int
    length: float
    overlap: float


class RoofResponse(BaseModel):
    id: UUID4
    name: str
    type: str
    overall_width: float
    useful_width: float
    overlap: float
    len_wave: float
    max_length: float
    min_length: float
    imp_sizes: Optional[List[Tuple[float, float]]] = None


class TariffRequest(BaseModel):
    name: str
    limit_users: int
    price: int


class TariffResponse(BaseModel):
    id: UUID4
    name: str
    limit_users: int
    price: int
