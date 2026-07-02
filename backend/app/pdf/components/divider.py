from reportlab.platypus import Table, TableStyle
from app.pdf.styles import COLOR_BORDER

def create_horizontal_divider() -> Table:
    """
    Generate a responsive thin horizontal rule flowable.
    """
    divider = Table([[""]], colWidths=[None])
    divider.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
    ]))
    return divider
