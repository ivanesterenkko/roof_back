from pydantic import UUID4, BaseModel


class RoofRequest(BaseModel):
    name: str
    type: str
    overall_width: float
    useful_width: float
    overlap: float
    max_length: float

class RoofResponse(BaseModel):
    roof_id: UUID4
    roof_name: str
    roof_type: str
    roof_overall_width: float
    roof_useful_width: float
    roof_overlap: float
    roof_max_length: float
