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

class RepositoryReportTemplate:
    """
    Placeholder report template for the Repository Guide.
    Composes shared visual components without populating actual domain content.
    """
    @staticmethod
    def generate(repo_name: str, author: str = "RepoGuideAI", date_str: str = "Today") -> bytes:
        styles = get_shared_styles()
        flowables = []
        
        # 1. Compose Cover Page
        metadata = {
            "Repository": repo_name,
            "Author": author,
            "Date": date_str,
            "Report Type": "Repository Analysis & Architecture"
        }
        flowables.extend(create_cover_page(
            title=f"Repository Guide: {repo_name}",
            subtitle="Automated Codebase Analysis and Architectural Overview",
            metadata=metadata
        ))
        
        # 2. Add Section 1: Overview (Composing Section Title, Info Box, and Body Paragraphs)
        flowables.append(create_section_title("1. Architecture Overview"))
        flowables.append(Spacer(1, SPACING_SM))
        flowables.append(Paragraph(
            "This document is an architectural analysis of the repository. "
            "It outlines key modules, components, dependency graphs, and structural design patterns.",
            styles['DocBody']
        ))
        
        # Info Box / Warning Callout Component
        flowables.append(create_info_box(
            "Note: This is a placeholder report representing the Production PDF Infrastructure. "
            "Actual repository indexing and profiling diagnostics will be populated in subsequent stages."
        ))
        flowables.append(Spacer(1, SPACING_MD))
        
        # 3. Add Section 2: Structure Table (Composing Table Component)
        flowables.append(create_section_title("2. Core Modules & Directories"))
        flowables.append(Spacer(1, SPACING_SM))
        
        headers = ["Directory/File", "Type", "Responsibilities"]
        rows = [
            ["backend/app/api", "Directory", "Exposes REST API endpoints and routing tables"],
            ["backend/app/core", "Directory", "Configuration, security utilities, and cache management"],
            ["backend/app/services", "Directory", "Domain logic, external API integrations, and analysis engines"],
            ["backend/app/models", "Directory", "SQLAlchemy schemas and persistence structures"]
        ]
        flowables.append(create_table(headers, rows))
        flowables.append(Spacer(1, SPACING_MD))
        
        # 4. Add Section 3: Lists (Composing Bullet Lists and Checklists)
        flowables.append(create_section_title("3. Verification and Standards Checklist"))
        flowables.append(Spacer(1, SPACING_SM))
        
        checklist_items = [
            ("All core models are covered by unit tests", True),
            ("Database migrations are fully generated and applied", False),
            ("Environment variables align with production spec", True),
            ("Cache policies are active and optimized", False)
        ]
        flowables.extend(create_checklist(checklist_items))
        flowables.append(Spacer(1, SPACING_MD))
        
        flowables.append(create_section_title("4. Summary & Action Items"))
        flowables.append(Spacer(1, SPACING_SM))
        
        bullet_items = [
            "Upgrade API route handler exception logging frameworks",
            "Optimize memory usage profiles in AST repository walk",
            "Configure secondary failover caching zones"
        ]
        flowables.extend(create_bullet_list(bullet_items))
        
        # Build document and return generated PDF bytes
        return PDFService.generate_pdf(flowables, has_cover=True, title=f"Repository Guide - {repo_name}")
