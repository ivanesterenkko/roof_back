from app.dao.base import BaseDAO
from app.projects.models import (Accessories, Cutouts, LengthSlope, Lines, LinesSlope,
                                 Materials, Point, PointSlope, PointsCutout, Projects, Sheets, Slopes)


class ProjectsDAO(BaseDAO):

    model = Projects


class SlopesDAO(BaseDAO):

    model = Slopes


class SheetsDAO(BaseDAO):
    model = Sheets


class PointsDAO(BaseDAO):
    model = Point


class PointsSlopeDAO(BaseDAO):
    model = PointSlope


class LinesDAO(BaseDAO):
    model = Lines


class LinesSlopeDAO(BaseDAO):
    model = LinesSlope


class LengthSlopeDAO(BaseDAO):
    model = LengthSlope


class CutoutsDAO(BaseDAO):
    model = Cutouts


class AccessoriesDAO(BaseDAO):
    model = Accessories


class MaterialsDAO(BaseDAO):
    model = Materials


class PointsCutoutsDAO(BaseDAO):
    model = PointsCutout
