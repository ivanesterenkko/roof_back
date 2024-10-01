import matplotlib.pyplot as plt
from shapely.geometry import Polygon
from shapely.plotting import plot_polygon
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PyPDF2 import PdfWriter
from reportlab.lib.units import inch
import datetime

from math import sqrt

from app.projects.schemas import LineData, PointData

async def lay_roof(figure: Polygon) -> list:
    sheets = []
    width_full = 0.9  #Размеры листа, в последсвии будет браться из БД
    overlap_horizontal = 0.06
    length_max = 2.0
    length_min = 0.5
    overlap_vertical = 0.15
    x_min, y_min, x_max, y_max = figure.bounds
    x = 0
    while x < x_max:
        x_ls = x
        x += width_full
        y = 0
        while y < y_max:
            y_ls = y
            y+= length_max
            sheet = Polygon([(x_ls, y_ls), (x, y_ls), (x, y), (x_ls, y)])
            intersection = figure.intersection(sheet)
            if not intersection.is_empty:
                coords = list(intersection.bounds)
                if coords[3] - coords[1] < overlap_vertical or coords[2] - coords[0] < overlap_horizontal:
                    continue
                elif coords[3] - coords[1] < length_min:
                    coords[3] = coords[1] + length_min
                sheets.append(Polygon([(x_ls, coords[1]), (x, coords[1]), (x, coords[3]), (x_ls, coords[3])]))
            if y + length_min - overlap_vertical < y_max:
                y -= overlap_vertical
        x -= overlap_horizontal
    return sheets

async def create_estimate(figure: Polygon, sheets: list[Polygon]):
    fig, ax = plt.subplots()
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_path = f"pdf/polygon_plot_{timestamp}.pdf"
    plot_polygon(figure, ax=ax, add_points=False,facecolor='none', edgecolor='red', linewidth=2)
    lengths = []
    for sheet in sheets:
        centr = sheet.centroid
        x, y = sheet.exterior.xy
        length = round(max(y) - min(y),3)
        lengths.append(length)
        ax.plot(x, y, color='black', linewidth=0.5)
        ax.annotate(f'{length:.3f}',  (centr.x,centr.y),
                fontsize=6, color='blue',ha='center', va='center')
    plt.savefig(pdf_path, dpi=300)
    return pdf_path


sheets = [[PointData()*4], ...]
wight = 2.0
square = 0
for sheet in sheets:
    lenght = sheet[3].y - sheet[0].y
    square += wight * lenght
print(square)

lines = [LineData()]
lenght_koneks = 0
for line in lines:
    lenght_konek = sqrt((line.end.x - line.start.x)**2 + (line.end.y - line.start.y)**2)
    lenght_koneks += lenght_konek
print(lenght_koneks)