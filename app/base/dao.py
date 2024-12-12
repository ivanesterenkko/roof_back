from app.base.models import Roofs, Tariffs
from app.dao.base import BaseDAO


class RoofsDAO(BaseDAO):

    model = Roofs


class TariffsDAO(BaseDAO):

    model = Tariffs
