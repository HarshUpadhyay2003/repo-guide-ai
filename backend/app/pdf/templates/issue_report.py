from app.pdf.pdf_service import PDFService
from app.pdf.components import (
    create_cover_page,
    create_section_title,
    create_info_box,
    create_table,
    create_bullet_list,
    create_checklist
)
from reportlab.platypus import Paragraph, Spacer
from app.pdf.styles import (
    get_shared_styles,
    COLOR_PRIMARY_PURPLE,
    SPACING_XS,
    SPACING_SM,
    SPACING_MD,
    SPACING_LG
)
import datetime
from app.pdf.utils.link_builder import build_issue_url

class IssueReportTemplate:
    """
    Report template for the Issue Guide.
    Composes shared visual components using real backend issue analysis data.
    """
    @staticmethod
    def generate(issue_data: dict, repo_name: str = None, author: str = "RepoPilot", date_str: str = None) -> bytes:
        styles = get_shared_styles()
        flowables = []
        
        # Fall back to empty dictionary if no data is provided
        if not issue_data:
            issue_data = {}
            
        raw_issue = issue_data.get("raw_issue", {})
        analysis = issue_data.get("analysis", {})
        exploration_hints = issue_data.get("exploration_hints", {})
        
        # Extracted fields
        owner = raw_issue.get("owner") or ""
        repo = raw_issue.get("repo") or ""
        
        if repo_name and "/" in repo_name:
            parts = repo_name.split("/", 1)
            if not owner:
                owner = parts[0]
            if not repo:
                repo = parts[1]

        if not repo_name or "/" not in repo_name:
            if owner and repo:
                repo_name = f"{owner}/{repo}"
            else:
                repo_name = repo or "Unknown Repository"

        # Ensure raw_issue contains owner and repo for link_builder
        if owner and not raw_issue.get("owner"):
            raw_issue["owner"] = owner
        if repo and not raw_issue.get("repo"):
            raw_issue["repo"] = repo
                
        issue_title = raw_issue.get("title", "Untitled Issue")
        issue_number = raw_issue.get("number", "Unknown")
        difficulty = analysis.get("difficulty", "Beginner")
        
        # Get confidence score, defaulting to analysis confidence or exploration hints confidence
        confidence_score = analysis.get("confidence_score") or exploration_hints.get("confidence") or 50
        
        beginner_explanation = analysis.get("beginner_explanation", "No explanation provided.")
        affected_area = analysis.get("affected_area", "General")
        skills_required = analysis.get("skills_required", [])
        
        likely_directories = exploration_hints.get("likely_directories", [])
        possible_files = exploration_hints.get("possible_files", [])
        reasoning = exploration_hints.get("reasoning", "No investigation details available.")
        
        # 1. Cover Page
        cover_metadata = {
            "Repository": repo_name,
            "Issue Number": f"#{issue_number}",
            "Difficulty": difficulty,
            "Confidence": f"{confidence_score}%",
            "Generated At": date_str or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        flowables.extend(create_cover_page(
            title="RepoPilot",
            subtitle=f"Issue Guide: {issue_title}",
            metadata=cover_metadata
        ))
        
        # 2. Issue Overview
        flowables.append(create_section_title("1. Issue Overview"))
        flowables.append(Spacer(1, SPACING_SM))
        
        # Simple beginner explanation
        flowables.append(Paragraph(beginner_explanation, styles['DocBody']))
        flowables.append(Spacer(1, SPACING_SM))
        
        # Key facts table
        overview_headers = ["Aspect", "Details"]
        overview_rows = [
            ["Difficulty Level", difficulty],
            ["Confidence Score", f"{confidence_score}%"],
            ["Affected Area", affected_area],
            ["Skills Required", ", ".join(skills_required) if skills_required else "General Software Development"]
        ]
        flowables.append(create_table(overview_headers, overview_rows, col_widths=[150, None]))
        flowables.append(Spacer(1, SPACING_MD))
        
        # 3. Exploration Hints
        flowables.append(create_section_title("2. Exploration Hints"))
        flowables.append(Spacer(1, SPACING_SM))
        
        # Investigation reasoning in an info box
        flowables.append(create_info_box(f"<b>Investigation Reasoning:</b> {reasoning}"))
        flowables.append(Spacer(1, SPACING_MD))
        
        # List of likely directories
        if likely_directories:
            flowables.append(Paragraph("<b>Likely Directories:</b>", styles['DocBody']))
            flowables.append(Spacer(1, SPACING_XS))
            flowables.extend(create_bullet_list(likely_directories))
            flowables.append(Spacer(1, SPACING_SM))
        else:
            flowables.append(Paragraph("<b>Likely Directories:</b> None identified", styles['DocBody']))
            flowables.append(Spacer(1, SPACING_SM))
            
        # List of possible files
        if possible_files:
            flowables.append(Paragraph("<b>Possible Files:</b>", styles['DocBody']))
            flowables.append(Spacer(1, SPACING_XS))
            flowables.extend(create_bullet_list(possible_files))
            flowables.append(Spacer(1, SPACING_SM))
        else:
            flowables.append(Paragraph("<b>Possible Files:</b> None identified", styles['DocBody']))
            flowables.append(Spacer(1, SPACING_SM))
            
        # 4. Suggested Workflow
        flowables.append(create_section_title("3. Suggested Workflow"))
        flowables.append(Spacer(1, SPACING_SM))
        
        # Get suggested workflow metadata if available, otherwise fallback deterministically
        workflow_data = issue_data.get("suggested_workflow") or issue_data.get("workflow") or {}
        
        # Recommended implementation steps
        steps = workflow_data.get("implementation_steps") or workflow_data.get("steps")
        if not steps:
            steps = [
                "Clone the repository and set up the local development environment.",
                f"Locate the '{affected_area}' module and examine key files."
            ]
            if possible_files:
                steps.append(f"Trace execution flow and inspect: {', '.join(possible_files[:3])}.")
            if issue_title:
                steps.append(f"Try to reproduce the issue: '{issue_title}'.")
            steps.extend([
                f"Implement the changes using {', '.join(skills_required) if skills_required else 'appropriate practices'}.",
                "Write tests to verify your implementation and run existing tests.",
                "Open a Pull Request and detail your changes in the PR description."
            ])
            
        checklist_items = [(step, False) for step in steps]
        flowables.append(Paragraph("<b>Recommended Implementation Steps:</b>", styles['DocBody']))
        flowables.append(Spacer(1, SPACING_XS))
        flowables.extend(create_checklist(checklist_items))
        flowables.append(Spacer(1, SPACING_MD))
        
        # Learning Path
        learning_path = workflow_data.get("learning_path") or workflow_data.get("learning_order")
        if not learning_path:
            learning_path = []
            if likely_directories:
                learning_path.append(
                    f"Understand the codebase layout around directories: {', '.join(likely_directories[:2])}"
                )
            else:
                learning_path.append("Familiarize yourself with the repository layout and structure.")
                
            if skills_required:
                learning_path.append(
                    f"Review core technologies: {', '.join(skills_required)}"
                )
            else:
                learning_path.append("Review standard project patterns and language features.")
                
            learning_path.append(f"Study code logic within the '{affected_area}' module.")
            
        flowables.append(Paragraph("<b>Learning Path:</b>", styles['DocBody']))
        flowables.append(Spacer(1, SPACING_XS))
        flowables.extend(create_bullet_list(learning_path))
        flowables.append(Spacer(1, SPACING_MD))
        
        # Setup/Testing guidance
        testing_guidance = workflow_data.get("testing_guidance") or workflow_data.get("setup_guidance")
        if not testing_guidance:
            testing_guidance = []
            languages_lower = [s.lower() for s in skills_required]
            if any(l in languages_lower for l in ["python", "django", "flask", "fastapi"]):
                testing_guidance.append("Run python tests using: pytest tests/ or python -m unittest")
            elif any(l in languages_lower for l in ["javascript", "typescript", "react", "nextjs", "node"]):
                testing_guidance.append("Run javascript tests using: npm test or yarn test")
            else:
                testing_guidance.append("Check the CONTRIBUTING.md or README.md file for test suites and testing commands.")
                
        if testing_guidance:
            flowables.append(Paragraph("<b>Setup & Testing Guidance:</b>", styles['DocBody']))
            flowables.append(Spacer(1, SPACING_XS))
            flowables.extend(create_bullet_list(testing_guidance))
            flowables.append(Spacer(1, SPACING_MD))
            
        # 5. Reference Section
        flowables.append(create_section_title("4. Reference Section"))
        flowables.append(Spacer(1, SPACING_SM))
        
        # Use the central Link Builder utility to construct the issue URL
        issue_url = build_issue_url(raw_issue, issue_number)
        issue_link = f"<a href='{issue_url}'><font color='{COLOR_PRIMARY_PURPLE.hexval()}'><u>Link to GitHub Issue #{issue_number}</u></font></a>"
        
        labels = raw_issue.get("labels", [])
        
        ref_headers = ["Reference", "Value"]
        ref_rows = [
            ["Repository Name", repo_name],
            ["GitHub Issue URL", issue_link],
            ["Labels", ", ".join(labels) if labels else "None"],
            ["Technologies", ", ".join(skills_required) if skills_required else "General development technologies"]
        ]
        flowables.append(create_table(ref_headers, ref_rows, col_widths=[150, None]))
        
        # Build document and return generated PDF bytes
        return PDFService.generate_pdf(flowables, has_cover=True, title=f"Issue Guide - {repo_name} #{issue_number}")

