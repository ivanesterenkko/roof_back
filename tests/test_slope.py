import pytest
from shapely.geometry import Polygon
from app.projects.slope import create_sheets


class MockRoof:
    def __init__(self, **kwargs):
        self.overall_width = kwargs.get("overall_width", 1.2)
        self.useful_width = kwargs.get("useful_width", 1.19)
        self.max_length = kwargs.get("max_length", 8)
        self.min_length = kwargs.get("min_length", 0.5)
        self.overlap = kwargs.get("overlap", 0.35)
        self.imp_sizes = kwargs.get("imp_sizes", [])  


@pytest.fixture
def roof():
    return MockRoof(
        overall_width=1.2,
        useful_width=1.19,
        max_length=8,
        min_length=0.5,
        overlap=0.35,
        imp_sizes=[]
    )


# https://wiki.yandex.ru/k/tipovojj-proet/
class TestDataset1: 

    @pytest.mark.asyncio
    @pytest.mark.parametrize("polygon, expected_sheets", [
        (
            Polygon([
                (0, 0), 
                (5.8, 6.15), 
                (11.6, 0),
            ]),
            [1.710, 2.880, 4.040, 5.21, 6.15, 5.84, 4.670, 3.5, 2.34]
        ),
        ( 
            Polygon([
                (0, 0), 
                (0, 2.8), 
                (2.3, 2.8),
                (5.18, 6.2),
                (7.48, 6.2),
                (13.1, 0),
            ]),
            [2.8, 2.8, 3.99, 5.29, 6.2, 6.2, 6.2, 5.86, 4.64, 3.43, 2.22]
        ),
        ( 
            Polygon([
                (0, 0), 
                (5.62, 6.2), 
                (7.92, 6.2),
                (10.55, 3.03),
                (13.1, 3.03),
                (13.1, 0),
            ]),
            [2.22, 3.43, 4.64, 5.86, 6.2, 6.2, 6.2, 5.27, 3.94, 3.030, 3.030]
        ),
        (
            Polygon([
                (0, 0), 
                (0, 2.93), 
                (2.55, 2.93),
            ]),
            [2.930, 1.88]
        ),
        ( 
            Polygon([
                (0, 2.7), 
                (2.3, 2.7), 
                (2.3, 0),
            ]),
            [1.65, 2.7]
        ),
        ( 
            Polygon([
                (0, 2.9), 
                (3.42, 5.65), 
                (6.55, 2.7),
                (3.95, 0),
                (2.95, 0),
            ]),
            [1.37, 3.350, 5.330, 5.650, 4.970, 2.990, 1.020]
        ),
    ])
    async def test_create_sheets(self, roof, polygon, expected_sheets):
        sheets = await create_sheets(polygon, roof)
        actual = [round(row[2], 2) for row in sheets]

        expected_sorted = sorted(expected_sheets)
        actual_sorted = sorted(actual)

        tolerance = 0

        diffs = [
            (i, x, y) for i, (x, y) in enumerate(zip(expected_sorted, actual_sorted))
            if abs(x - y) == 0
        ]

        assert not diffs, (
            f"\n❌ Отличия в длинах листов {polygon}:" +
            f"\nexpected: {expected_sorted}\nactual: {actual_sorted}\n"
        )