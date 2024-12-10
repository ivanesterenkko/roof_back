from app.dao.base import BaseDAO
from app.users.models import Company, Users, Sessions


class UsersDAO(BaseDAO):

    model = Users

class SessionsDAO(BaseDAO):

    model = Sessions

class CompanyDAO(BaseDAO):

    model = Company