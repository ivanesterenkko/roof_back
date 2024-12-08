from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.exceptions import (IncorrectEmailOrPasswordException,
                            UserAlreadyExistsException)
from app.users.auth import (authenticate_user, create_access_token,
                            get_password_hash)
from app.users.dao import UsersDAO, SessionsDAO
from app.users.dependencies import get_current_user
from app.users.models import Users
from app.users.schemas import SUserAuth, SUserRegister, TokenResponse


router = APIRouter(prefix="/auth", tags=["Auth & Пользователи"])


@router.post("/register")
async def register_user(user_data: SUserRegister) -> None:
    existing_user = await UsersDAO.find_one_or_none(login=user_data.login)

    if existing_user:
                raise UserAlreadyExistsException

    hashed_password = get_password_hash(user_data.password)
    await UsersDAO.add(login=user_data.login, hashed_password=hashed_password)


@router.post("/login")
async def login_user(user_data: SUserAuth, response: Response) -> TokenResponse:

    user = await authenticate_user(login=user_data.login, password=user_data.password)

    if not user:

        raise IncorrectEmailOrPasswordException
    
    existing_session = await SessionsDAO.find_one_or_none(user_id=user.id)
    if existing_session:
        await SessionsDAO.delete_(model_id=existing_session.id)

    access_token = create_access_token(
        {"sub": str(user.id)}
    )
    await SessionsDAO.add(user_id=user.id, jwt_token=access_token)

    response.set_cookie("access_token", access_token, httponly=True)
    return TokenResponse(access_token=access_token)


@router.post("/logout")
async def logout_user(response: Response, user: Users = Depends(get_current_user)) -> None:
    
    existing_session = await SessionsDAO.find_one_or_none(user_id=user.id)
    if existing_session:
        await SessionsDAO.delete_(model_id=existing_session.id)

    response.delete_cookie("access_token")
