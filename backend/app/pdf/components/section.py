from reportlab.platypus import Paragraph
from app.pdf.styles import get_shared_styles

def create_section_title(title_text: str) -> Paragraph:
    """
    Generate a styled section title flowable.
    """
    styles = get_shared_styles()
    return Paragraph(title_text, styles['SectionHeading'])
