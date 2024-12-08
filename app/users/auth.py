from datetime import datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import EmailStr

from app.config import settings
from app.exceptions import TokenExpiredException
from app.users.dao import UsersDAO
from app.users.models import Users


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:

    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:

    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=90)  # Установим время жизни токена
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

async def authenticate_user(login: str, password: str) -> None | Users:

    user = await UsersDAO.find_one_or_none(login=login)

    if not user or not verify_password(password, user.hashed_password):
        return None

    else:
        return user
    
def verify_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return payload
    except JWTError:
        raise TokenExpiredException