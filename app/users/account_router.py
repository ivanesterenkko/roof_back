from typing import List
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import UUID4

from ..exceptions import (ChangePasswordException, CompanyNotFound, IncorrectCurrentPasswordException, PermissionDeniedException,
                          UserAlreadyExistsException, UserNotFound)
from ..projects.dao import ProjectsDAO
from .auth import get_password_hash, verify_password
from .dao import CompanyDAO, SessionsDAO, UsersDAO
from .dependencies import generate_random_password, generate_unique_login, get_current_user, get_session
from .models import Users
from .schemas import ChangePasswordRequest, CompanyProjectResponse, CompanyRequest, CompanyResponse, NewUserResponse, SUserRegister, UserResponse, UserSessionsRespnse
from app.db import async_session_maker

router = APIRouter(prefix="/account", tags=["Account"])


@router.get("/company", description="Get company info")
async def get_company(
      user: Users = Depends(get_current_user),
      session: AsyncSession = Depends(get_session)
) -> CompanyResponse:
    company = await CompanyDAO.find_by_id(session, user.company_id)
    if not company:
        raise CompanyNotFound
    users = await UsersDAO.find_all(session, company_id=company.id)
    if not users:
        raise CompanyNotFound
    users_data = []
    for user in users:
        sessions = await SessionsDAO.find_all(session, user_id=user.id)
        is_active = True
        if not sessions:
            is_active = False
        users_data.append(UserResponse(
            name=user.name,
            is_admin=user.is_admin,
            is_active=is_active,
            is_paid=True
        ))
    return CompanyResponse(
            id=company.id,
            name=company.name,
            INN=company.INN,
            OGRN=company.OGRN,
            users=users_data
    )


@router.delete("/company", description="Delete company")
async def delete_company(
      user: Users = Depends(get_current_user),
      session: AsyncSession = Depends(get_session)
) -> None:
    company = await CompanyDAO.find_by_id(session, user.company_id)
    if not company:
        raise CompanyNotFound
    if not user.is_admin:
        raise PermissionDeniedException
    await CompanyDAO.delete_(session, model_id=company.id)


@router.patch("/company/{company_id}", description="Update company info")
async def update_company(
      company_id: UUID4,
      company_data: CompanyRequest,
      user: Users = Depends(get_current_user),
      session: AsyncSession = Depends(get_session)
) -> None:
    company = await CompanyDAO.find_by_id(session, company_id)
    if not company:
        raise CompanyNotFound
    await CompanyDAO.update_(
        session, 
        model_id=company.id,
        name=company_data.name,
        INN=company_data.INN,
        OGRN=company_data.OGRN
        )

@router.post("/users/register")
async def register_user(
      user_data: SUserRegister,
      user: Users = Depends(get_current_user),
      session: AsyncSession = Depends(get_session)
) -> NewUserResponse:
    if not user.is_admin:
        raise PermissionDeniedException

    existing_user = await UsersDAO.find_one_or_none(session, email=user_data.email)
    if existing_user:
        raise UserAlreadyExistsException

    company = await CompanyDAO.find_by_id(session, user.company_id)
    if not company:
        raise CompanyNotFound
    raw_password = generate_random_password()
    hashed_password = get_password_hash(raw_password)
    login = await generate_unique_login(
        full_name=user_data.name,
        session=session
    )
    new_user = await UsersDAO.add(
        session,
        name=user_data.name,
        login=login,
        email=user_data.email,
        hashed_password=hashed_password,
        is_admin=user_data.is_admin,
        company_id=company.id
    )
    return NewUserResponse(
        id=new_user.id,
        name=new_user.name,
        login=new_user.login,
        email=new_user.email,
        password=raw_password,
        is_admin=new_user.is_admin
    )


@router.delete("/users/{user_id}")
async def delete_user(
      user_id: UUID4,
      user: Users = Depends(get_current_user),
      session: AsyncSession = Depends(get_session)
) -> None:
    if not user.is_admin or user.id == user_id:
        raise PermissionDeniedException

    user_delete = await UsersDAO.find_by_id(session, user_id)
    if not user_delete:
        raise UserNotFound

    await UsersDAO.delete_(session, model_id=user_id)


@router.patch("/users/{user_id}", description="Update user info")
async def update_user(
      user_id: UUID4,
      user_data: SUserRegister,
      user: Users = Depends(get_current_user),
      session: AsyncSession = Depends(get_session)
) -> None:
    if user.id != user_id:
        raise PermissionDeniedException

    user_update = await UsersDAO.find_by_id(session, user_id)
    if not user_update:
        raise UserNotFound
    existing_user = await UsersDAO.find_one_or_none(session, email=user_data.email)
    if existing_user:
        raise UserAlreadyExistsException
    await UsersDAO.update_(
        session,
        model_id=user_update.id,
        name=user_data.name,
        email=user_data.email,
        is_admin=user_data.is_admin
    )


@router.get("/projects", description="Get list of projects")
async def get_company_projects(
      user: Users = Depends(get_current_user),
      session: AsyncSession = Depends(get_session)
) -> List[CompanyProjectResponse]:
    company = await CompanyDAO.find_by_id(session, user.company_id)
    if not company:
        raise CompanyNotFound

    users = await UsersDAO.find_all(session, company_id=user.company_id)
    projects_data = []
    for user_now in users:
        projects = await ProjectsDAO.find_all(session, user_id=user_now.id)
        for project in projects:
            projects_data.append(CompanyProjectResponse(
                id=project.id,
                project_name=project.name,
                project_step=project.step,
                user_id=user_now.id,
                datetime_created=project.datetime_created
            ))
    return projects_data


@router.get("/users/sessions", description="Get list of projects")
async def get_sessions(
      user: Users = Depends(get_current_user),
      session: AsyncSession = Depends(get_session)
) -> List[UserSessionsRespnse]:
    # company = await CompanyDAO.find_by_id(session, user.company_id)
    # if not company:
    #     raise CompanyNotFound
    user_sessions = await SessionsDAO.find_all(session, user_id=user.id)
    if not user_sessions:
        raise UserNotFound
    sessions_data = []
    for user_session in user_sessions:
        sessions_data.append(UserSessionsRespnse(
            id=user_session.id,
            device=user_session.device,
            created_at=user_session.created_at
        ))
    return sessions_data

@router.delete("/users/sessions/{session_id}", description="Get list of projects")
async def delete_session(
      session_id: UUID4,
      user: Users = Depends(get_current_user),
      session: AsyncSession = Depends(get_session)
) -> None:
    # company = await CompanyDAO.find_by_id(session, user.company_id)
    # if not company:
    #     raise CompanyNotFound
    user_session = await SessionsDAO.find_by_id(session, model_id=session_id)
    if not user_session:
        raise UserNotFound
    if user_session.user_id != user.id:
        raise PermissionDeniedException
    if not user_session:
        raise UserNotFound
    sessions_data = []
    await SessionsDAO.delete_(session, model_id=user_session.id)


@router.patch("/users/password", description="Change password")
async def change_password(
      change_password: ChangePasswordRequest,
      user: Users = Depends(get_current_user),
      session: AsyncSession = Depends(get_session)
) -> None:
    if not verify_password(change_password.current_password, user.hashed_password):
        raise IncorrectCurrentPasswordException
    if change_password.new_password == change_password.current_password:
        raise ChangePasswordException
    hashed_password = get_password_hash(change_password.new_password)
    await UsersDAO.update_(
        session,
        model_id=user.id,
        hashed_password=hashed_password
    )