import pytest
from shapely.geometry import Polygon
from app.projects.slope import create_sheets


class MockRoof:
    def __init__(self, **kwargs):
        self.overall_width = kwargs.get("overall_width", 1.19)
        self.useful_width = kwargs.get("useful_width", 1.1)
        self.max_length = kwargs.get("max_length", 8)
        self.min_length = kwargs.get("min_length", 0.5)
        self.overlap = kwargs.get("overlap", 0.35)
        self.imp_sizes = kwargs.get("imp_sizes", [])


@pytest.fixture
def roof():
    return MockRoof(
        overall_width=1.19,
        useful_width=1.1,
        max_length=8,
        min_length=0.5,
        overlap=0.35,
        imp_sizes=[]
    )


# https://wiki.yandex.ru/k/tipovojj-proet/
class TestDataset1:

    @pytest.mark.asyncio
    @pytest.mark.parametrize("polygon, direction, overhang, expected_sheets", [
        (
            Polygon([
                (0, 0),
                (10.75, 0),
                (5.375, 5.8),
            ]),
            False,
            0,
            [0.820, 2.01, 3.2, 4.390, 5.570, 5.8, 4.750, 3.570, 2.380, 1.190]
        ),
        (
            Polygon([
                (0, 0), 
                (12.3, 0), 
                (6.95, 5.8),
                (5.375, 5.8),
            ]),
            False,
            0,
            [1.32, 2.51, 3.7, 4.89,  5.8, 5.8, 5.8, 4.77, 3.58, 2.39, 1.2]
        ),
        (
            Polygon([
                (0, 0),
                (10.1, 0),
                (5.05, 5.6),
            ]),
            True,
            0,
            [1.22, 2.44, 3.66, 4.88, 5.6, 5.01, 3.79, 2.57, 1.35]
        ),
        (
            Polygon([
                (0, 0), 
                (13.9, 0), 
                (8.92, 5.6),
                (4.97, 5.6),
            ]),
            True,
            0,
            [1.24, 2.48, 3.72, 4.96, 5.6, 5.6, 5.6, 5.6, 5.6, 4.41, 3.17, 1.93, 0.69]
        ),
        (
            Polygon([
                (0, 0),
                (4.1, 0),
                (2.05, 2.4),
            ]),
            True,
            0,
            [1.29, 2.4, 2.12, 0.84]
        ),
        (
            Polygon([
                (0, 2.4),
                (2, 2.4),
                (4.1, 0),
                (2.1, 0),
            ]),
            False,
            0,
            [1, 2.4, 2.4, 1.25]
        ),
        (
            Polygon([
                (0, 0),
                (2, 0),
                (4.1, 2.4),
                (2.1, 2.4),
            ]),
            True,
            0,
            [1, 2.4, 2.4, 1.25]
        ),
    ])
    async def test_create_sheets(self, roof, polygon, direction, overhang, expected_sheets):
        sheets = create_sheets(polygon, roof, direction, overhang)
        actual = [round(row[2], 2) for row in sheets]

        expected_sorted = sorted(expected_sheets)
        actual_sorted = sorted(actual)

        # Погрешность для каждого листа
        tolerance = 0.03

        diffs = [
            (i, x, y) for i, (x, y) in enumerate(zip(expected_sorted, actual_sorted))
            if abs(x - y) > tolerance
        ]

        assert not diffs, (
            f"\n❌ Погрешность длины листа больше чем {tolerance}м" +
            f"\nexpected: {expected_sorted}\nactual: {actual_sorted}\n"
        )

        # Общая сумма погрешности
        OVERALL_TOLERANCE = 0.08
        total_error = sum(abs(x - y) for x, y in zip(expected_sorted, actual_sorted))

        assert total_error <= OVERALL_TOLERANCE, (
            f"\n❌ Суммарная погрешность превышает лимит {OVERALL_TOLERANCE}м:"
            f"\n  Total error: {round(total_error, 3)} м"
            f"\n  Allowed max: {OVERALL_TOLERANCE} м"
            f"\nexpected: {expected_sorted}\nactual: {actual_sorted}"
        )