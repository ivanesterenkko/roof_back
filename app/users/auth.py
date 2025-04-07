from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import TokenExpiredException
from app.users.dao import UsersDAO
from app.users.models import Users

# Создаем контекст для хэширования паролей с использованием алгоритма bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """
    Возвращает хэш пароля.

    :param password: Открытый текст пароля.
    :return: Хэш пароля.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверяет, соответствует ли открытый пароль его хэшу.

    :param plain_password: Открытый текст пароля.
    :param hashed_password: Хэш пароля.
    :return: True, если пароли совпадают, иначе False.
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: Dict[str, Any]) -> str:
    """
    Создает JWT-токен с заданными данными и временем истечения.

    :param data: Словарь с данными, которые необходимо закодировать в токене.
    :return: Закодированный JWT-токен.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=90)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


async def authenticate_user(
    session: AsyncSession, login: str, password: str
) -> Optional[Users]:
    """
    Аутентифицирует пользователя по логину и паролю.

    :param session: Асинхронная сессия для работы с базой данных.
    :param login: Логин пользователя.
    :param password: Пароль пользователя.
    :return: Объект пользователя, если аутентификация успешна, иначе None.
    """
    user = await UsersDAO.find_one_or_none(session, login=login)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def verify_access_token(token: str) -> Dict[str, Any]:
    """
    Проверяет валидность JWT-токена и возвращает закодированные данные.

    :param token: JWT-токен.
    :return: Словарь с данными, полученными из токена.
    :raises TokenExpiredException: Если токен недействителен или истек.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        raise TokenExpiredException
