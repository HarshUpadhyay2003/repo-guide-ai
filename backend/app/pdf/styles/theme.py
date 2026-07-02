from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Color Palette (Aesthetic light theme: White background, Purple headings, Charcoal body, Gray metadata)
COLOR_PRIMARY_PURPLE = colors.HexColor("#6B46C1")  # Rich purple for headings/accents
COLOR_TEXT_DARK = colors.HexColor("#1A202C")      # Dark charcoal for readability
COLOR_TEXT_MUTED = colors.HexColor("#718096")     # Muted gray for metadata/footers
COLOR_BACKGROUND_LIGHT = colors.HexColor("#F7FAFC") # Soft gray for boxes/tables
COLOR_BORDER = colors.HexColor("#E2E8F0")           # Light border color
COLOR_WHITE = colors.HexColor("#FFFFFF")

# Spacing & Layout Constants (in points)
PAGE_MARGIN = 54  # 0.75 inch margin
SPACING_XS = 4
SPACING_SM = 8
SPACING_MD = 16
SPACING_LG = 24
SPACING_XL = 32

def get_shared_styles():
    """
    Get or initialize the shared stylesheet for PDF generation.
    Safely registers custom ParagraphStyles to avoid duplicates.
    """
    styles = getSampleStyleSheet()
    
    # 1. Document Title
    if 'DocTitle' not in styles:
        styles.add(ParagraphStyle(
            name='DocTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=24,
            leading=30,
            textColor=COLOR_TEXT_DARK,
            spaceAfter=SPACING_XL,
            alignment=0  # Left-aligned
        ))
        
    # 1.5 Document Subtitle
    if 'DocSubtitle' not in styles:
        styles.add(ParagraphStyle(
            name='DocSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=14,
            leading=18,
            textColor=COLOR_TEXT_MUTED,
            spaceAfter=SPACING_XL,
            alignment=0
        ))
        
    # 2. Section Heading
    if 'SectionHeading' not in styles:
        styles.add(ParagraphStyle(
            name='SectionHeading',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=14,
            leading=18,
            textColor=COLOR_PRIMARY_PURPLE,
            spaceBefore=SPACING_LG,
            spaceAfter=SPACING_MD,
            keepWithNext=True
        ))

    # 3. Body Text
    if 'DocBody' not in styles:
        styles.add(ParagraphStyle(
            name='DocBody',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=COLOR_TEXT_DARK,
            spaceAfter=SPACING_SM
        ))

    # 4. Metadata Text
    if 'DocMetadata' not in styles:
        styles.add(ParagraphStyle(
            name='DocMetadata',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=12,
            textColor=COLOR_TEXT_MUTED,
            spaceAfter=SPACING_SM
        ))
        
    # 5. Footer Style
    if 'DocFooter' not in styles:
        styles.add(ParagraphStyle(
            name='DocFooter',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=10,
            textColor=COLOR_TEXT_MUTED,
            alignment=1  # Centered
        ))
        
    # 6. Information Card Style
    if 'InfoCardText' not in styles:
        styles.add(ParagraphStyle(
            name='InfoCardText',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9.5,
            leading=13,
            textColor=COLOR_TEXT_DARK
        ))

    # 7. Table Header
    if 'TableHeader' not in styles:
        styles.add(ParagraphStyle(
            name='TableHeader',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9.5,
            leading=12,
            textColor=COLOR_WHITE
        ))
        
    # 8. Table Cell
    if 'TableCell' not in styles:
        styles.add(ParagraphStyle(
            name='TableCell',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=12,
            textColor=COLOR_TEXT_DARK
        ))

    # 9. Bullet List Item
    if 'BulletItem' not in styles:
        styles.add(ParagraphStyle(
            name='BulletItem',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=COLOR_TEXT_DARK,
            leftIndent=15,
            firstLineIndent=-10,
            spaceAfter=SPACING_XS
        ))

    return styles
