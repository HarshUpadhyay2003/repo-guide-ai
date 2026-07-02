from app.pdf.pdf_service import PDFService
from app.pdf.components import (
    create_cover_page,
    create_section_title,
    create_info_box,
    create_table,
    create_bullet_list,
    create_checklist,
    create_horizontal_divider
)
from reportlab.platypus import Paragraph, Spacer
from app.pdf.styles import get_shared_styles, SPACING_SM, SPACING_MD

class IssueReportTemplate:
    """
    Placeholder report template for the Issue Guide.
    Composes shared visual components without populating actual domain content.
    """
    @staticmethod
    def generate(issue_title: str, author: str = "RepoGuideAI", date_str: str = "Today") -> bytes:
        styles = get_shared_styles()
        flowables = []
        
        # 1. Compose Cover Page
        metadata = {
            "Issue Target": issue_title,
            "Author": author,
            "Date": date_str,
            "Report Type": "Issue Analysis & Resolution Steps"
        }
        flowables.extend(create_cover_page(
            title=f"Issue Guide: {issue_title}",
            subtitle="Automated Issue Assessment and Contextual Recommendations",
            metadata=metadata
        ))
        
        # 2. Add Section 1: Overview
        flowables.append(create_section_title("1. Issue Overview"))
        flowables.append(Spacer(1, SPACING_SM))
        flowables.append(Paragraph(
            "This document is a generated guidance report for fixing the specified issue. "
            "It outlines the impact, relevant codebase locations, and actionable steps to resolve it.",
            styles['DocBody']
        ))
        
        # Info Box component
        flowables.append(create_info_box(
            "Note: This is a placeholder report representing the Production PDF Infrastructure. "
            "Actual issue telemetry and context mapping will be populated in subsequent stages."
        ))
        flowables.append(Spacer(1, SPACING_MD))
        
        # 3. Add Section 2: Codebase Context (Composing Table)
        flowables.append(create_section_title("2. Affected Code Areas"))
        flowables.append(Spacer(1, SPACING_SM))
        
        headers = ["File Path", "Line Range", "Relevance / Functionality"]
        rows = [
            ["backend/app/api/v1/routes.py", "L45-L60", "Main routing definitions for incoming request validations"],
            ["backend/app/services/llm_service.py", "L102-L125", "Handles formatting of structural prompt payloads"],
            ["backend/app/utils/logging.py", "L12-L30", "Configures stream handlers and logging formatters"]
        ]
        flowables.append(create_table(headers, rows))
        flowables.append(Spacer(1, SPACING_MD))
        
        # 4. Add Section 3: Action Plan Checklist
        flowables.append(create_section_title("3. Resolution Checklist"))
        flowables.append(Spacer(1, SPACING_SM))
        
        checklist_items = [
            ("Reproduce behavior locally via integration tests", True),
            ("Implement check condition for missing token fields", False),
            ("Deploy localized service config patch", False),
            ("Verify performance indicators under load tests", False)
        ]
        flowables.extend(create_checklist(checklist_items))
        flowables.append(Spacer(1, SPACING_MD))
        
        flowables.append(create_section_title("4. Reference Guidelines"))
        flowables.append(Spacer(1, SPACING_SM))
        
        bullet_items = [
            "Keep API parameters backward compatible.",
            "Verify all lint checks pass successfully.",
            "Avoid introducing thread blocking synchronous blocks."
        ]
        flowables.extend(create_bullet_list(bullet_items))
        
        # Build document and return generated PDF bytes
        return PDFService.generate_pdf(flowables, has_cover=True, title=f"Issue Guide - {issue_title}")
