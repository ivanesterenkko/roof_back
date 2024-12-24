from datetime import datetime
from pydantic import UUID4, BaseModel


class SUserRegister(BaseModel):
    name: str
    login: str
    password: str
    is_admin: bool
    company_id: UUID4


class SAdminRegister(BaseModel):
    name: str
    company: str
    INN: str
    login: str
    password: str


class UserResponse(BaseModel):
    name: str
    is_admin: bool


class SUserAuth(BaseModel):

    login: str
    password: str


class TokenResponse(BaseModel):
    access_token: str


class CompanyProjectResponse(BaseModel):
    id: UUID4
    project_name: str
    project_step: int
    user_id: UUID4
    datetime_created: datetime


class OrderRequest(BaseModel):
    tariff_id: UUID4
    duration: int


class OrderResponse(BaseModel):
    id: UUID4
    subscription_id: UUID4
    duration: int
    is_paid: bool


class SubscriptionResponse(BaseModel):
    id: UUID4
    expired_at: datetime
    tariff_id: UUID4
    company_id: UUID4
