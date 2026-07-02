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

class ContributionReportTemplate:
    """
    Placeholder report template for the Contribution Guide.
    Composes shared visual components without populating actual domain content.
    """
    @staticmethod
    def generate(project_name: str, author: str = "RepoGuideAI", date_str: str = "Today") -> bytes:
        styles = get_shared_styles()
        flowables = []
        
        # 1. Compose Cover Page
        metadata = {
            "Project Target": project_name,
            "Author": author,
            "Date": date_str,
            "Report Type": "Contribution Guidelines & Onboarding Plan"
        }
        flowables.extend(create_cover_page(
            title=f"Contribution Guide: {project_name}",
            subtitle="Developer Onboarding, Setup Guide, and Code Submission Standards",
            metadata=metadata
        ))
        
        # 2. Add Section 1: Overview
        flowables.append(create_section_title("1. Getting Started"))
        flowables.append(Spacer(1, SPACING_SM))
        flowables.append(Paragraph(
            "Welcome to the project! This onboarding guide is designed to help new contributors "
            "set up their local environment, understand our git branching policies, and run test suites.",
            styles['DocBody']
        ))
        
        # Info Box component
        flowables.append(create_info_box(
            "Note: This is a placeholder report representing the Production PDF Infrastructure. "
            "Actual codebase workflow and onboarding metadata will be populated in subsequent stages."
        ))
        flowables.append(Spacer(1, SPACING_MD))
        
        # 3. Add Section 2: Requirements (Composing Table)
        flowables.append(create_section_title("2. Prerequisites & Infrastructure"))
        flowables.append(Spacer(1, SPACING_SM))
        
        headers = ["Tool / Package", "Minimum Version", "Purpose"]
        rows = [
            ["Python", "3.10.x", "Backend runtime engine and test orchestration"],
            ["Node.js", "18.x.x", "Frontend user interface dashboard development"],
            ["PostgreSQL", "14.x", "Persistent data store for repository mappings and telemetry"],
            ["Docker", "24.x", "Local development sandbox orchestration and services simulation"]
        ]
        flowables.append(create_table(headers, rows))
        flowables.append(Spacer(1, SPACING_MD))
        
        # 4. Add Section 3: Step-by-Step Setup Checklist
        flowables.append(create_section_title("3. Local Environment Setup Tasks"))
        flowables.append(Spacer(1, SPACING_SM))
        
        checklist_items = [
            ("Clone repository and configure local secrets (.env)", True),
            ("Build python virtual environment and restore backend packages", False),
            ("Run database migrations against postgres container", False),
            ("Launch local developer servers and run smoke checks", False)
        ]
        flowables.extend(create_checklist(checklist_items))
        flowables.append(Spacer(1, SPACING_MD))
        
        flowables.append(create_section_title("4. Contribution Best Practices"))
        flowables.append(Spacer(1, SPACING_SM))
        
        bullet_items = [
            "Write comprehensive docstrings for all new service methods.",
            "Cover code modifications with both unit and integration tests.",
            "Sign-off all git commits and squash development branches before review."
        ]
        flowables.extend(create_bullet_list(bullet_items))
        
        # Build document and return generated PDF bytes
        return PDFService.generate_pdf(flowables, has_cover=True, title=f"Contribution Guide - {project_name}")
