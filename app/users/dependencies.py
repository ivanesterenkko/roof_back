from datetime import datetime

from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt

from app.config import settings
from app.exceptions import (IncorrectTokenFormatException,
                            TokenAbsentException, TokenExpiredException,
                            UserIsNotPresentException)
from app.users.dao import UsersDAO


def get_token(request: Request):

    token = request.cookies.get("access_token") or request.headers.get("Authorization")

    if not token:
        raise TokenAbsentException

    if token.startswith("Bearer "):
        token = token[len("Bearer "):]

    return token


async def get_current_user(token: str = Depends(get_token)):

    try:

        payload = jwt.decode(
            token, settings.SECRET_KEY, settings.ALGORITHM
        )

    except JWTError:

        raise IncorrectTokenFormatException

    expire = payload.get("exp")

    if (not expire) or (int(expire) < datetime.utcnow().timestamp()):

        raise TokenExpiredException

    user_id = payload.get("sub")

    if not user_id:

        raise UserIsNotPresentException

    user = await UsersDAO.find_by_id(user_id)

    if not user:
        raise UserIsNotPresentException

    return user