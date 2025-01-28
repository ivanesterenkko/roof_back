from app.base.models import AccessoriesBD, Roofs, Tariffs
from app.dao.base import BaseDAO


class RoofsDAO(BaseDAO):

    model = Roofs


class TariffsDAO(BaseDAO):

    model = Tariffs


class Accessory_baseDAO(BaseDAO):

    model = AccessoriesBD