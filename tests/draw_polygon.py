from shapely.geometry import Polygon, Point, LineString
import matplotlib.pyplot as plt

# Создаем фигуру (например, полигон крыши)
polygon = Polygon([
            (0, 0), 
                (0, 2.8), 
                (2.3, 2.8),
                (5.18, 6.2),
                (7.48, 6.2),
                (13.1, 0),
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