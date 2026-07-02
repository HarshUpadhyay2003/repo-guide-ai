from reportlab.platypus import Paragraph, Table, TableStyle
from app.pdf.styles import (
    get_shared_styles,
    COLOR_BACKGROUND_LIGHT,
    COLOR_BORDER
)

def create_info_box(content) -> Table:
    """
    Generate a styled warning/info callout box wrapping content flowables.
    """
    styles = get_shared_styles()
    
    if isinstance(content, str):
        content_flowables = [Paragraph(content, styles['InfoCardText'])]
    elif isinstance(content, list):
        content_flowables = []
        for item in content:
            if isinstance(item, str):
                content_flowables.append(Paragraph(item, styles['InfoCardText']))
            else:
                content_flowables.append(item)
    else:
        content_flowables = [content]
        
    box_table = Table([[content_flowables]], colWidths=[None])
    box_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_BACKGROUND_LIGHT),
        ('BOX', (0, 0), (-1, -1), 1, COLOR_BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('LEFTPADDING', (0, 0), (-1, -1), 16),
        ('RIGHTPADDING', (0, 0), (-1, -1), 16),
    ]))
    return box_table
