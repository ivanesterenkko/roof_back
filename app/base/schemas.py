from pydantic import UUID4, BaseModel


class RoofRequest(BaseModel):
    name: str
    type: str
    price: float
    overal_width: float
    useful_width: float
    overlap: float
    material: str
    color: str
    min_length: float
    max_length: float

class RoofResponce(BaseModel):
    roof_id: UUID4
    roof_name: str
    roof_type: str
    roof_price: float
    roof_overal_width: float
    roof_useful_width: float
    roof_overlap: float
    roof_material: str
    roof_color: str
    roof_min_length: float
    roof_max_length: float
