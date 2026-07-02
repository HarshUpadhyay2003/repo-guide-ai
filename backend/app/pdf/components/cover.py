from reportlab.platypus import Paragraph, PageBreak, Spacer
from app.pdf.styles import (
    get_shared_styles,
    SPACING_LG,
    SPACING_XL
)
from app.pdf.components.divider import create_horizontal_divider

def create_cover_page(title: str, subtitle: str, metadata: dict) -> list:
    """
    Generate cover page flowables.
    """
    styles = get_shared_styles()
    flowables = []
    
    # Large spacer to push title down
    flowables.append(Spacer(1, SPACING_XL * 3))
    
    # Document Title
    flowables.append(Paragraph(title, styles['DocTitle']))
    
    # Subtitle
    if subtitle:
        flowables.append(Paragraph(subtitle, styles['DocSubtitle']))
        
    # Visual divider
    flowables.append(create_horizontal_divider())
    flowables.append(Spacer(1, SPACING_LG))
    
    # Metadata block
    if metadata:
        for key, val in metadata.items():
            flowables.append(Paragraph(f"<b>{key}:</b> {val}", styles['DocMetadata']))
            
    flowables.append(PageBreak())
    return flowables
