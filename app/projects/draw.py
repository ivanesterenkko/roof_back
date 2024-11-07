import base64
import matplotlib.pyplot as plt
from matplotlib import patches
from io import BytesIO

def draw_plan(lines, sheets, width):
    # Предварительное вычисление максимальных значений координат
    x_values = [sheet.x_start + width for sheet in sheets] + [line.x_end for line in lines]
    y_values = [sheet.y_start + sheet.length for sheet in sheets] + [line.y_end for line in lines]
    x_max = max(x_values)
    y_max = max(y_values)
    
    fig, ax = plt.subplots()

    # Общие параметры для стилей текста и рамок
    bbox_props = dict(facecolor='white', edgecolor='none', boxstyle='round,pad=0.3')
    text_props = dict(ha='center', va='center', fontsize=10, color='black', bbox=bbox_props)

    # Рисуем листы в виде прямоугольников
    for sheet in sheets:
        rectangle = patches.Rectangle(
            (sheet.x_start, sheet.y_start), 
            width,                      
            sheet.length,                  
            linewidth=1,                 
            edgecolor='gray',                  
            facecolor='none'                    
        )
        ax.add_patch(rectangle)
        ax.text(
            sheet.x_start + width / 2, 
            sheet.y_start + sheet.length / 2,  
            f"{sheet.length:.2f}", 
            **text_props
        )

    # Рисуем линии и их метки
    for line in lines:
        x1, y1, x2, y2 = line.x_start, line.y_start, line.x_end, line.y_end
        ax.plot([x1, x2], [y1, y2], color='black', linewidth=3)
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        ax.text(
            mid_x, mid_y,
            line.name,
            fontweight='semibold',
            **text_props
        )
    
    # Устанавливаем пределы осей
    ax.set_xlim(0, x_max + 1)
    ax.set_ylim(0, y_max + 1)
    
    # Настраиваем сетку и пропорции
    ax.set_xticks(range(0, int(x_max) + 2))
    ax.set_yticks(range(0, int(y_max) + 2))
    ax.grid(visible=True, color='grey', linestyle='--', linewidth=0.5)
    ax.set_aspect('equal')
    
    # Сохраняем изображение в буфер в формате PNG
    buf = BytesIO()
    plt.savefig(buf, format="png", dpi=300, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    image_bytes = buf.getvalue()
    
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')

    return image_base64
