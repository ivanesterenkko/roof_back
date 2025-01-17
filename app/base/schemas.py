from pydantic import UUID4, BaseModel


class RoofRequest(BaseModel):
    name: str
    type: str
    overall_width: float
    useful_width: float
    overlap: float
    max_length: float


class RoofResponse(BaseModel):
    id: UUID4
    name: str
    type: str
    overall_width: float
    useful_width: float
    overlap: float
    max_length: float


class TariffRequest(BaseModel):
    name: str
    limit_users: int
    price: int


class TariffResponse(BaseModel):
    id: UUID4
    name: str
    limit_users: int
    price: int
