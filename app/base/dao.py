from app.base.models import Accessoriesbase, Roofsbase
from app.dao.base import BaseDAO


class AccessoriesbaseDAO(BaseDAO):

    model = Accessoriesbase

class RoofbaseDAO(BaseDAO):

    model = Roofsbase
