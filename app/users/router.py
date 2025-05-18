from fastapi import APIRouter, Depends, Request, Response, HTTPException
from user_agents import parse
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import (
    CompanyAlreadyExistsException,
    IncorrectEmailOrPasswordException,
    UserAlreadyExistsException
)
from app.users.auth import (
    authenticate_user,
    create_access_token,
    get_password_hash
)
from app.users.dao import CompanyDAO, UsersDAO, SessionsDAO
from app.users.dependencies import get_current_user  # Получение текущего пользователя из токена
from app.users.models import Users
from app.users.schemas import SAdminRegister, SUserAuth, TokenResponse
from app.db import async_session_maker  # Функция для создания AsyncSession

router = APIRouter(prefix="/auth", tags=["Auth & Пользователи"])


@router.post("/register")
async def register_admin(user_data: SAdminRegister) -> dict:
    """
    Регистрирует администратора компании.

    1. Проверяет, существует ли уже компания с таким ИНН.
    2. Создаёт компанию.
    3. Проверяет, существует ли пользователь с таким логином.
    4. Создаёт администратора с захэшированным паролем.

    :param user_data: Данные для регистрации администратора.
    :return: Словарь с подтверждением успешной регистрации.
    :raises CompanyAlreadyExistsException: Если компания с указанным ИНН уже существует.
    :raises UserAlreadyExistsException: Если пользователь с указанным логином уже существует.
    """
    async with async_session_maker() as session:
        async with session.begin():
            # Проверяем, существует ли компания с таким ИНН
            existing_company = await CompanyDAO.find_one_or_none(session, INN=user_data.INN)
            if existing_company:
                raise CompanyAlreadyExistsException

            # Добавляем новую компанию
            company = await CompanyDAO.add(
                session,
                name=user_data.company,
                INN=user_data.INN,
                OGRN=user_data.OGRN
            )

            # Проверяем, существует ли пользователь с таким логином
            existing_user = await UsersDAO.find_one_or_none(session, email=user_data.email)
            if existing_user and existing_user.login == user_data.login:
                raise UserAlreadyExistsException

            # Хэшируем пароль и создаем нового администратора
            hashed_password = get_password_hash(user_data.password)
            await UsersDAO.add(
                session,
                name=user_data.name,
                login=user_data.login,
                email=user_data.email,
                hashed_password=hashed_password,
                is_admin=True,
                company_id=company.id
            )

    return {"detail": "Registration successful"}


@router.post("/login")
async def login_user(
    request: Request,
    user_data: SUserAuth,
    response: Response
) -> TokenResponse:
    """
    Аутентифицирует пользователя и возвращает JWT-токен.

    1. Аутентификация происходит через проверку логина и пароля.
    2. Определяется тип устройства (mobile/tablet/desktop) на основе user-agent.
    3. Если существует старая сессия для этого устройства, она удаляется.
    4. Создается новый JWT-токен и сохраняется сессия.
    5. Токен устанавливается в cookie и возвращается клиенту.

    :param request: Объект запроса для получения user-agent.
    :param user_data: Данные для аутентификации пользователя.
    :param response: Объект ответа для установки cookie.
    :return: Объект TokenResponse с access_token.
    :raises IncorrectEmailOrPasswordException: Если аутентификация не пройдена.
    """
    async with async_session_maker() as session:
        async with session.begin():
            # Аутентифицируем пользователя с использованием переданной сессии
            user = await authenticate_user(session, login=user_data.login, password=user_data.password)
            if not user:
                raise IncorrectEmailOrPasswordException

            # Определяем тип устройства по user-agent
            user_agent_str = request.headers.get("user-agent", "")
            user_agent = parse(user_agent_str)
            if user_agent.is_mobile:
                device_type = "mobile"
            elif user_agent.is_tablet:
                device_type = "tablet"
            else:
                device_type = "desktop"

            # Если для данного устройства уже существует сессия, удаляем её
            existing_session = await SessionsDAO.find_one_or_none(session, user_id=user.id, device=device_type)
            if existing_session:
                await SessionsDAO.delete_(session, model_id=existing_session.id)

            # Создаем новый токен доступа
            access_token = create_access_token({"sub": str(user.id)})
            # Сохраняем новую сессию с токеном
            await SessionsDAO.add(session, user_id=user.id, jwt_token=access_token, device=device_type)

            # Устанавливаем токен в cookie с параметром httponly
            response.set_cookie("access_token", access_token, httponly=True)
            return TokenResponse(access_token=access_token)


@router.post("/logout")
async def logout_user(
    request: Request,
    response: Response,
    user: Users = Depends(get_current_user)
) -> None:
    """
    Завершает сессию пользователя (logout).

    1. Определяет тип устройства по user-agent.
    2. Находит сессию для данного пользователя и устройства.
    3. Удаляет найденную сессию и удаляет cookie access_token.

    :param request: Объект запроса для получения user-agent.
    :param response: Объект ответа для удаления cookie.
    :param user: Текущий пользователь (зависимость get_current_user).
    :return: None.
    """
    async with async_session_maker() as session:
        async with session.begin():
            # Определяем тип устройства
            user_agent_str = request.headers.get("user-agent", "")
            user_agent = parse(user_agent_str)
            if user_agent.is_mobile:
                device_type = "mobile"
            elif user_agent.is_tablet:
                device_type = "tablet"
            else:
                device_type = "desktop"

            # Находим сессию пользователя для данного устройства
            existing_session = await SessionsDAO.find_one_or_none(session, user_id=user.id, device=device_type)
            if existing_session:
                await SessionsDAO.delete_(session, model_id=existing_session.id)

            # Удаляем cookie с access_token
            response.delete_cookie("access_token")
