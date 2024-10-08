from app.dao.base import BaseDAO
from app.projects.models import Lines, Projects, Roofs, Slopes


class ProjectsDAO(BaseDAO):

    model = Projects

class SlopesDAO(BaseDAO):

    model = Slopes

class RoofsDAO(BaseDAO):
    model = Roofs

class LinesDAO(BaseDAO):
    model = Lines
