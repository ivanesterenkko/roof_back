from app.base.models import Accessories, Roofs
from app.dao.base import BaseDAO


class AccessoriesDAO(BaseDAO):

    model = Accessories

class RoofsDAO(BaseDAO):

    model = Roofs
