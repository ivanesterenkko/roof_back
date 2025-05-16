from typing import List
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import UUID4

from ..exceptions import (CompanyNotFound, PermissionDeniedException,
                          UserAlreadyExistsException, UserNotFound)
from ..projects.dao import ProjectsDAO
from .auth import get_password_hash
from .dao import CompanyDAO, UsersDAO
from .dependencies import get_current_user, get_session
from .models import Users
from .schemas import CompanyProjectResponse, SUserRegister, UserResponse
from app.db import async_session_maker

router = APIRouter(prefix="/account", tags=["Account"])


@router.get("/users")
async def get_users(
      user: Users = Depends(get_current_user),
      session: AsyncSession = Depends(get_session)
) -> List[UserResponse]:
    company = await CompanyDAO.find_by_id(session, user.company_id)
    if not company:
        raise CompanyNotFound

    users = await UsersDAO.find_all(session, company_id=user.company_id)
    return [UserResponse(
          name=data.name,
          is_admin=data.is_admin
    ) for data in users]


@router.post("/users/register")
async def register_user(
      user_data: SUserRegister,
      user: Users = Depends(get_current_user),
      session: AsyncSession = Depends(get_session)
) -> UserResponse:
    if not user.is_admin:
        raise PermissionDeniedException

    existing_user = await UsersDAO.find_one_or_none(session, login=user_data.login)
    if existing_user:
        raise UserAlreadyExistsException

    company = await CompanyDAO.find_by_id(session, user_data.company_id)
    if not company:
        raise CompanyNotFound

    hashed_password = get_password_hash(user_data.password)
    new_user = await UsersDAO.add(
        session,
        name=user_data.name,
        login=user_data.login,
        hashed_password=hashed_password,
        is_admin=user_data.is_admin,
        company_id=company.id
    )
    return UserResponse(
          name=new_user.name,
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