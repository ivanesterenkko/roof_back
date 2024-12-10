from typing import List
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import UUID4

from app.exceptions import (CompanyAlreadyExistsException, CompanyNotFound, IncorrectEmailOrPasswordException, PermissionDeniedException,
                            UserAlreadyExistsException, UserNotFound)
from app.projects.dao import ProjectsDAO
from app.users.auth import (authenticate_user, create_access_token,
                            get_password_hash)
from app.users.dao import CompanyDAO, UsersDAO, SessionsDAO
from app.users.dependencies import get_current_user
from app.users.models import Users
from app.users.schemas import CompanyProjectResponse, SAdminRegister, SUserAuth, SUserRegister, TokenResponse, UserResponse


router = APIRouter(prefix="/account", tags=["Account"])

@router.get("users")
async def get_users(user: Users = Depends(get_current_user)) -> List[UserResponse]:
    company = await CompanyDAO.find_by_id(user.company_id)
    if not company:
          raise CompanyNotFound
    users = await UsersDAO.find_all(company_id=user.company_id)
    return [UserResponse(
          name=data.name,
          is_admin=data.is_admin
    ) for data in users]

@router.post("users/register")
async def register_user(user_data: SUserRegister, user: Users = Depends(get_current_user)) -> UserResponse:
    if user.is_admin != True:
           raise PermissionDeniedException
    existing_user = await UsersDAO.find_one_or_none(login=user_data.login)
    if existing_user:
                raise UserAlreadyExistsException
    company = await CompanyDAO.find_by_id(user_data.company_id)
    if not company:
          raise CompanyNotFound

    hashed_password = get_password_hash(user_data.password)
    new_user = await UsersDAO.add(
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

@router.delete("users/{user_id}")
async def delete_user(user_id: UUID4, user: Users = Depends(get_current_user)) -> None:
    if user.is_admin != True or user.id == user_id:
           raise PermissionDeniedException
    user_delete = await UsersDAO.find_by_id(user_id)
    if not user_delete:
          raise UserNotFound
    await UsersDAO.delete_(
           model_id=user_id
    )

@router.get("/projects", description="Get list of projects")
async def get_company_projects(user: Users = Depends(get_current_user)) -> List[CompanyProjectResponse]:
    company = await CompanyDAO.find_by_id(user.company_id)
    if not company:
          raise CompanyNotFound
    users = await UsersDAO.find_all(company_id=user.company_id)
    projects_data = []
    for user_now in users:
        projects = await ProjectsDAO.find_all(user_id=user_now.id)
        for project in projects:
            projects_data.append(CompanyProjectResponse(
                id=project.id,
                project_name=project.name,
                project_step=project.step,
                user_id=user_now.id,
                datetime_created=project.datetime_created
            ))
    return projects_data