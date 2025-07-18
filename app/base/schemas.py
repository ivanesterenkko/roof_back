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
    length: float
    material: str
    overlap: float
    price: Optional[int] = None
    modulo: Optional[float] = None


class AccessoryBDResponse(BaseModel):
    id: UUID4
    name: str
    type: str
    parent_type: str
    length: float
    material: str
    overlap: float
    price: Optional[int] = None
    modulo: Optional[float] = None


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
    type: str
    price: int
    price_sale: int
    duration: int
    limit_users: int
    atributes: Optional[str] = None


class TariffResponse(BaseModel):
    id: UUID4
    name: str
    type: str
    price: int
    price_sale: int
    duration: int
    limit_users: int
    atributes: Optional[str] = None