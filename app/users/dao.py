from app.dao.base import BaseDAO
from app.users.models import Company, Orders, Subscriptions, Users, Sessions


class UsersDAO(BaseDAO):

    model = Users


class SessionsDAO(BaseDAO):

    model = Sessions


class CompanyDAO(BaseDAO):

    model = Company


class SubscriptionDAO(BaseDAO):

    model = Subscriptions


class OrdersDAO(BaseDAO):

    model = Orders