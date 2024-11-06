from matplotlib import patches
import matplotlib.pyplot as plt
from io import BytesIO
import base64

async def draw_plan(lines, sheets, width):
    coordinates_lines = [(line.x_start, line.y_start, line.x_end, line.y_end, line.name) for line in lines]
    x_max = 0
    y_max = 0
    
    fig, ax = plt.subplots()
    for sheet in sheets:
        rectangle = patches.Rectangle(
            (sheet.x_start,sheet.y_start), 
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
            ha='center',
            va='bottom',
            fontsize=10,
            color='black',
            bbox=dict(
            facecolor='white', 
            edgecolor='none', 
            boxstyle='round,pad=0.3'
            )
        )

    for (x1, y1, x2, y2, name) in coordinates_lines:
        x_max = max(x_max,x1,x2)
        y_max = max(y_max,y1,y2)
        ax.plot([x1, x2], [y1, y2], color= 'black', linewidth=3)
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        ax.text(
            mid_x, mid_y,
            name,
            ha='center',
            va='center',
            fontsize=12,
            color='black',
            fontweight='semibold',
            bbox=dict(
            facecolor='white', 
            edgecolor='none', 
            boxstyle='round,pad=0.3'
            )
        )
    
    ax.set_xticks(range(0, int(x_max) + 1))
    ax.set_yticks(range(0, int(y_max) + 1))
    ax.grid(visible=True, color='grey', linestyle='--', linewidth=0.5)

    ax.set_aspect('equal')
    
    # Сохраняем изображение в памяти в формате base64
    buf = BytesIO()
    plt.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    image_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    
    return image_base64
