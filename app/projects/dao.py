from sqlalchemy import UUID, select
from app.dao.base import BaseDAO
from app.projects.models import Cutouts, Lines, Projects, Sheets, Slopes
from app.db import async_session_maker


class ProjectsDAO(BaseDAO):

    model = Projects

class SlopesDAO(BaseDAO):

    model = Slopes

class SheetsDAO(BaseDAO):
    model = Sheets

class LinesDAO(BaseDAO):
    model = Lines

class CutoutsDAO(BaseDAO):
    model = Cutouts