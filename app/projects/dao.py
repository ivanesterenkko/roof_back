from sqlalchemy import UUID, select
from app.dao.base import BaseDAO
from app.projects.models import Lines, Projects, Roofs, Slopes
from app.db import async_session_maker


class ProjectsDAO(BaseDAO):

    model = Projects

class SlopesDAO(BaseDAO):

    model = Slopes

class RoofsDAO(BaseDAO):
    model = Roofs

class LinesDAO(BaseDAO):
    model = Lines
