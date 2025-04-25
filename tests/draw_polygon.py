from shapely.geometry import Polygon, Point, LineString
import matplotlib.pyplot as plt

# Создаем фигуру (например, полигон крыши)
polygon = Polygon([
        (0, 0),
        (4.975, 5.6),
        (8.131, 5.6),
        (13.9, 0),
        (9, 0),
        (6.95, 2.4),
        (4.9, 0),
])

# Получаем координаты внешнего контура
x, y = polygon.exterior.xy

# Отрисовка
plt.figure(figsize=(6, 6))
plt.plot(x, y, color='blue', linewidth=2)
plt.fill(x, y, color='skyblue', alpha=0.5)

plt.title("Shapely Polygon")
plt.grid(True)
plt.axis('equal')
plt.show()