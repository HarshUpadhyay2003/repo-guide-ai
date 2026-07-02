from reportlab.platypus import Paragraph, Table, TableStyle
from app.pdf.styles import get_shared_styles, COLOR_PRIMARY_PURPLE

def create_checklist(items: list) -> list:
    """
    Generate a list of checklist items with custom-colored checkbox symbols.
    Items should be structured as tuples: (text_string, checked_bool)
    """
    styles = get_shared_styles()
    flowables = []
    
    for text, checked in items:
        box_char = "[x]" if checked else "[ ]"
        checkbox_markup = f"<font color='{COLOR_PRIMARY_PURPLE.hexval()}'><b>{box_char}</b></font>"
        checkbox_p = Paragraph(checkbox_markup, styles['TableCell'])
        text_p = Paragraph(text, styles['DocBody'])
        
        # 2-column layout table for the checkbox and label text
        item_table = Table([[checkbox_p, text_p]], colWidths=[24, None])
        item_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (1, 0), (1, 0), 4),
        ]))
        flowables.append(item_table)
        
    return flowables
