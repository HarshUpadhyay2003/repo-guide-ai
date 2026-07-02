from reportlab.pdfgen import canvas
from app.pdf.components.header import draw_header
from app.pdf.components.footer import draw_footer
from app.pdf.components.cover import create_cover_page
from app.pdf.components.section import create_section_title
from app.pdf.components.info_box import create_info_box
from app.pdf.components.table import create_table
from app.pdf.components.bullet_list import create_bullet_list
from app.pdf.components.checklist import create_checklist
from app.pdf.components.divider import create_horizontal_divider

class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and draw headers/footers
    with correct total page counts.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        # Retrieve document template context
        doc = getattr(self, '_doctemplate', None)
        has_cover = getattr(doc, 'has_cover_page', False)
        pdf_title = getattr(doc, 'pdf_title', "RepoGuideAI Report")

        # Skip header/footer on page 1 if a cover page is enabled
        if has_cover and self._pageNumber == 1:
            return

        # Draw header and footer
        draw_header(self, doc, pdf_title)
        draw_footer(self, doc, self._pageNumber, page_count)

__all__ = [
    "NumberedCanvas",
    "draw_header",
    "draw_footer",
    "create_cover_page",
    "create_section_title",
    "create_info_box",
    "create_table",
    "create_bullet_list",
    "create_checklist",
    "create_horizontal_divider"
]
