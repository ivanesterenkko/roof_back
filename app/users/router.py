from fastapi import APIRouter, Depends, Request, Response
from user_agents import parse

from app.exceptions import (CompanyAlreadyExistsException,
                            IncorrectEmailOrPasswordException,
                            UserAlreadyExistsException)
from app.users.auth import (authenticate_user, create_access_token,
                            get_password_hash)
from app.users.dao import CompanyDAO, UsersDAO, SessionsDAO
from app.users.dependencies import get_current_user
from app.users.models import Users
from app.users.schemas import SAdminRegister, SUserAuth, TokenResponse


router = APIRouter(prefix="/auth", tags=["Auth & Пользователи"])


@router.post("/register")
async def register_admin(user_data: SAdminRegister) -> None:
    existing_company = await CompanyDAO.find_one_or_none(INN=user_data.INN)
    if existing_company:
        raise CompanyAlreadyExistsException

    company = await CompanyDAO.add(
        name=user_data.company,
        INN=user_data.INN
    )
    existing_user = await UsersDAO.find_one_or_none(login=user_data.login)
    if existing_user:
        raise UserAlreadyExistsException

    hashed_password = get_password_hash(user_data.password)

    await UsersDAO.add(
        name=user_data.name,
        login=user_data.login,
        hashed_password=hashed_password,
        is_admin=True,
        company_id=company.id
    )


@router.post("/login")
async def login_user(
      request: Request,
      user_data: SUserAuth,
      response: Response
      ) -> TokenResponse:

    user = await authenticate_user(
        login=user_data.login,
        password=user_data.password
        )

    if not user:

        raise IncorrectEmailOrPasswordException
    user_agent_str = request.headers.get("user-agent", "")
    user_agent = parse(user_agent_str)
    if user_agent.is_mobile:
        device_type = "mobile"
    elif user_agent.is_tablet:
        device_type = "tablet"
    else:
        device_type = "desktop"

    existing_session = await SessionsDAO.find_one_or_none(user_id=user.id, device=device_type)
    if existing_session:
        await SessionsDAO.delete_(model_id=existing_session.id)

    access_token = create_access_token(
        {"sub": str(user.id)}
    )
    await SessionsDAO.add(user_id=user.id, jwt_token=access_token, device=device_type)

    response.set_cookie("access_token", access_token, httponly=True)
    return TokenResponse(access_token=access_token)


@router.post("/logout")
async def logout_user(
      request: Request,
      response: Response,
      user: Users = Depends(get_current_user)
      ) -> None:

    user_agent_str = request.headers.get("user-agent", "")
    user_agent = parse(user_agent_str)
    if user_agent.is_mobile:
        device_type = "mobile"
    elif user_agent.is_tablet:
        device_type = "tablet"
    else:
        device_type = "desktop"

    existing_session = await SessionsDAO.find_one_or_none(user_id=user.id, device=device_type)
    if existing_session:
        await SessionsDAO.delete_(model_id=existing_session.id)

    response.delete_cookie("access_token")
