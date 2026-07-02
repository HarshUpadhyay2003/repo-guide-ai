from app.pdf.styles import PAGE_MARGIN, COLOR_TEXT_MUTED, COLOR_BORDER

def draw_footer(canvas_obj, doc, current_page: int, total_pages: int):
    """
    Draw running footer on the canvas.
    """
    canvas_obj.saveState()
    canvas_obj.setFont("Helvetica", 8)
    canvas_obj.setFillColor(COLOR_TEXT_MUTED)
    
    page_width, page_height = canvas_obj._pagesize
    left_margin = doc.leftMargin if doc else PAGE_MARGIN
    right_margin = doc.rightMargin if doc else PAGE_MARGIN
    bottom_margin = doc.bottomMargin if doc else PAGE_MARGIN
    
    y_pos = bottom_margin - 20
    
    # Center page number (e.g. Page 1 of 5)
    page_str = f"Page {current_page} of {total_pages}"
    canvas_obj.drawCentredString(page_width / 2.0, y_pos, page_str)
    
    # Left brand string
    canvas_obj.drawString(left_margin, y_pos, "RepoGuideAI")
    
    # Running footer line
    canvas_obj.setStrokeColor(COLOR_BORDER)
    canvas_obj.setLineWidth(0.5)
    canvas_obj.line(left_margin, y_pos + 12, page_width - right_margin, y_pos + 12)
    canvas_obj.restoreState()
