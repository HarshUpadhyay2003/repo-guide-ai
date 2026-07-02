from app.pdf.styles import PAGE_MARGIN, COLOR_PRIMARY_PURPLE, COLOR_BORDER

def draw_header(canvas_obj, doc, title_text: str):
    """
    Draw running header on the canvas.
    """
    canvas_obj.saveState()
    canvas_obj.setFont("Helvetica-Bold", 8)
    canvas_obj.setFillColor(COLOR_PRIMARY_PURPLE)
    
    page_width, page_height = canvas_obj._pagesize
    left_margin = doc.leftMargin if doc else PAGE_MARGIN
    right_margin = doc.rightMargin if doc else PAGE_MARGIN
    
    y_pos = page_height - (doc.topMargin if doc else PAGE_MARGIN) + 15
    
    # Left-aligned running title
    canvas_obj.drawString(left_margin, y_pos, title_text)
    
    # Running header line
    canvas_obj.setStrokeColor(COLOR_BORDER)
    canvas_obj.setLineWidth(0.5)
    canvas_obj.line(left_margin, y_pos - 8, page_width - right_margin, y_pos - 8)
    canvas_obj.restoreState()
