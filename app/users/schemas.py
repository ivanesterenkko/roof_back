from datetime import datetime
from pydantic import UUID4, BaseModel, Field


class SUserRegister(BaseModel):
    name: str = Field(
        pattern=r'^[А-ЯЁ][а-яё]+ [А-ЯЁ][а-яё]+ [А-ЯЁ][а-яё]+$',
        example="Нестеренко Иван Владимирович",
    )
    email: str = Field(
        pattern=r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$',
        example="ivan.nester@example.com",
    )
    is_admin: bool


class SAdminRegister(BaseModel):
    name: str = Field(
        pattern=r'^[А-ЯЁ][а-яё]+ [А-ЯЁ][а-яё]+ [А-ЯЁ][а-яё]+$',
        example="Нестеренко Иван Владимирович",
    )
    email: str = Field(
        pattern=r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$',
        example="ivan.nester@example.com",
    )
    company: str
    INN: str
    OGRN: str
    login: str
    password: str


class NewUserResponse(BaseModel):
    id: UUID4
    name: str
    login: str
    email: str
    password: str
    is_admin: bool


class UserResponse(BaseModel):
    name: str
    is_admin: bool
    is_active: bool
    is_paid: bool


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


class UserSessionsRespnse(BaseModel):
    id: UUID4
    device: str
    created_at: datetime


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


class ChangePasswordRequest(BaseModel):

    current_password: str
    new_password: str


class CompanyRequest(BaseModel):
    name: str
    INN: str
    OGRN: str

class CompanyResponse(BaseModel):
    id: UUID4
    name: str
    INN: str
    OGRN: str
    users: list[UserResponse]
