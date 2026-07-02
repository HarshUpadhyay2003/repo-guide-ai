from reportlab.platypus import Paragraph
from app.pdf.styles import get_shared_styles

def create_bullet_list(items: list) -> list:
    """
    Generate a list of bullet points with standard hanging indent.
    """
    styles = get_shared_styles()
    flowables = []
    for item in items:
        flowables.append(Paragraph(f"&bull;&nbsp;&nbsp;{item}", styles['BulletItem']))
    return flowables
