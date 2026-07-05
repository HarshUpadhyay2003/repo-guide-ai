import os
from reportlab.platypus import Paragraph, PageBreak, Spacer, Image
from app.pdf.styles import (
    get_shared_styles,
    SPACING_LG,
    SPACING_XL,
    SPACING_MD
)
from app.pdf.components.divider import create_horizontal_divider

def create_cover_page(title: str, subtitle: str, metadata: dict) -> list:
    """
    Generate cover page flowables.
    """
    styles = get_shared_styles()
    flowables = []
    
    # Logo integration at the top of the cover page
    try:
        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "repo_pilot_light_logo.png")
        if os.path.exists(logo_path):
            flowables.append(Spacer(1, SPACING_XL))
            # Width = 140, Height = 68 (preserves aspect ratio 2.05)
            flowables.append(Image(logo_path, width=140, height=68))
            flowables.append(Spacer(1, SPACING_LG))
        else:
            flowables.append(Spacer(1, SPACING_XL * 3))
    except Exception:
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
