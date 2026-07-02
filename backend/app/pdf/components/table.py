from reportlab.platypus import Table, TableStyle, Paragraph
from app.pdf.styles import (
    get_shared_styles,
    COLOR_PRIMARY_PURPLE,
    COLOR_BACKGROUND_LIGHT,
    COLOR_BORDER,
    COLOR_WHITE
)

def create_table(headers: list, rows: list, col_widths: list = None) -> Table:
    """
    Generate a styled table with auto-wrapped cells and alternating row colors.
    """
    styles = get_shared_styles()
    
    # Wrap all string inputs in Paragraphs to support auto-wrapping
    header_row = [
        Paragraph(h, styles['TableHeader']) if isinstance(h, str) else h
        for h in headers
    ]
    
    body_rows = []
    for row in rows:
        body_rows.append([
            Paragraph(cell, styles['TableCell']) if isinstance(cell, str) else cell
            for cell in row
        ])
        
    data = [header_row] + body_rows
    t = Table(data, colWidths=col_widths)
    
    # Construct base style
    t_style = [
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_PRIMARY_PURPLE),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
    ]
    
    # Alternate row background colors
    for idx in range(1, len(data)):
        bg_color = COLOR_BACKGROUND_LIGHT if idx % 2 != 0 else COLOR_WHITE
        t_style.append(('BACKGROUND', (0, idx), (-1, idx), bg_color))
        
    t.setStyle(TableStyle(t_style))
    return t
