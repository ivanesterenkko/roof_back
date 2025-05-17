from datetime import datetime

import secrets
import string
from unidecode import unidecode
from fastapi import Depends, HTTPException, Request
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.exceptions import (
    IncorrectTokenFormatException,
    TokenAbsentException,
    TokenExpiredException,
    UserIsNotPresentException
)
from app.users.dao import SessionsDAO, UsersDAO


def get_token(request: Request) -> str:
    """
    Извлекает токен доступа из cookies или заголовков запроса.

    :param request: Объект запроса FastAPI.
    :return: Токен доступа в виде строки.
    :raises TokenAbsentException: Если токен не найден.
    """
    token = request.cookies.get("access_token") or request.headers.get("Authorization")

    if not token:
        raise TokenAbsentException

    # Удаляем префикс "Bearer ", если он присутствует.
    if token.startswith("Bearer "):
        token = token[len("Bearer "):]

    return token


async def get_current_user(
    token: str = Depends(get_token),
    session: AsyncSession = Depends(get_session)
):
    """
    Получает текущего пользователя на основе JWT-токена.

    :param token: JWT-токен, извлеченный с помощью зависимости get_token.
    :param session: Асинхронная сессия для работы с базой данных.
    :return: Объект пользователя.
    :raises IncorrectTokenFormatException: Если токен имеет неверный формат.
    :raises TokenExpiredException: Если токен истек.
    :raises UserIsNotPresentException: Если пользователь не найден в базе.
    :raises HTTPException: Если не найдена сессия для данного токена.
    """
    try:
        # Декодирование токена с указанием алгоритма в виде списка.
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
    except JWTError:
        raise IncorrectTokenFormatException

    expire = payload.get("exp")
    # Проверка наличия и срока действия токена.
    if (not expire) or (int(expire) < datetime.utcnow().timestamp()):
        raise TokenExpiredException

    user_id = payload.get("sub")
    if not user_id:
        raise UserIsNotPresentException

    # Получаем пользователя из базы, передавая открытый сеанс.
    user = await UsersDAO.find_by_id(session, user_id)
    if not user:
        raise UserIsNotPresentException

    # Проверяем, существует ли сессия для данного токена.
    session_obj = await SessionsDAO.find_one_or_none(session, jwt_token=token)
    if not session_obj:
        raise HTTPException(status_code=401, detail="Token mismatch")

    return user


def generate_random_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()"
    return "".join(secrets.choice(alphabet) for _ in range(length))

async def generate_unique_login(
    full_name: str,
    session: AsyncSession,
    max_tries: int = 1000
) -> str:
    parts = full_name.strip().split()
    surname, name = parts[0], parts[1]
    lat_surname = unidecode(surname).lower()
    lat_initial = unidecode(name[0]).lower()
    base = f"{lat_initial}{lat_surname}"
    for _ in range(max_tries):
        suffix = secrets.randbelow(1000)
        candidate = f"{base}{suffix}"
        exists = await UsersDAO.find_one_or_none(session, login=candidate)
        if not exists:
            return candidate
    raise RuntimeError("Не удалось сгенерировать уникальный логин")