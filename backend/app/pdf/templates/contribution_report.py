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
from app.pdf.utils.link_builder import (
    build_repository_url,
    build_issue_url,
    build_readme_url,
    build_contributing_url
)

class ContributionReportTemplate:
    """
    Report template for the Contribution Guide.
    Composes shared visual components using real backend contributor roadmap data.
    """
    @staticmethod
    def generate(repo_name: str, analysis_data: dict = None, author: str = "RepoPilot", date_str: str = None) -> bytes:
        styles = get_shared_styles()
        flowables = []
        
        # Fall back to empty dictionary if no analysis data is provided
        if not analysis_data:
            analysis_data = {}
            
        metadata = analysis_data.get("metadata", {})
        summary = analysis_data.get("summary", {})
        roadmap = analysis_data.get("roadmap", {})
        
        # Extract metadata fields
        owner = metadata.get("owner", "Unknown Owner")
        name = metadata.get("name", repo_name)
        repo = name
        estimated_learning_time = summary.get("estimated_learning_time", "Unknown")
        
        # Extract best issue to start
        best_issue = roadmap.get("best_issue_to_start", {})
        best_issue_number = best_issue.get("issue_number", "Unknown")
        best_issue_title = best_issue.get("title", "Recommended Issue")
        
        # Try to locate the issue details from analysis_data.get("issues", [])
        matching_issue = None
        for issue_entry in analysis_data.get("issues", []):
            raw = issue_entry.get("raw_issue", {})
            if raw.get("number") == best_issue_number:
                matching_issue = issue_entry
                break
                
        # Fallbacks for issue-specific fields
        difficulty = "Beginner"
        skills_required = []
        affected_area = "General"
        possible_files = []
        likely_directories = []
        reasoning = "This issue is identified as an excellent starting point for new contributors."
        
        if matching_issue:
            issue_analysis = matching_issue.get("analysis", {})
            exploration_hints = matching_issue.get("exploration_hints", {})
            difficulty = issue_analysis.get("difficulty", "Beginner")
            skills_required = issue_analysis.get("skills_required", [])
            affected_area = issue_analysis.get("affected_area", "General")
            possible_files = exploration_hints.get("possible_files", [])
            likely_directories = exploration_hints.get("likely_directories", [])
            reasoning = exploration_hints.get("reasoning", reasoning)
            
        # 1. Cover Page
        cover_metadata = {
            "Repository Name": name,
            "Repository Owner": owner,
            "Recommended Issue": f"#{best_issue_number}",
            "Issue Title": best_issue_title,
            "Difficulty": difficulty,
            "Estimated Learning Time": estimated_learning_time,
            "Generated At": date_str or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Author": "RepoPilot AI Contribution Assistant"
        }
        flowables.extend(create_cover_page(
            title="RepoPilot",
            subtitle="Contribution Guide",
            metadata=cover_metadata
        ))
        
        # 2. Section 1: Contribution Goal
        flowables.append(create_section_title("1. Contribution Goal"))
        flowables.append(Spacer(1, SPACING_SM))
        
        why_this_issue = roadmap.get("why_this_issue", "")
        if why_this_issue:
            flowables.append(Paragraph(f"<b>Recommendation Reason:</b> {why_this_issue}", styles['DocBody']))
            flowables.append(Spacer(1, SPACING_SM))
            
        flowables.append(Paragraph(
            f"<b>Objective:</b> By completing this contribution guide, you will resolve issue <b>#{best_issue_number}</b> "
            f"({best_issue_title}) and help improve the project's <b>{affected_area}</b> module.",
            styles['DocBody']
        ))
        flowables.append(Spacer(1, SPACING_SM))
        
        flowables.append(Paragraph(
            "<b>Expected Outcome:</b> Successful integration of your code modifications, verified by localized test coverage, "
            "and a submitted Pull Request addressing all requirements of the issue.",
            styles['DocBody']
        ))
        flowables.append(Spacer(1, SPACING_MD))
        
        # 3. Section 2: Skills Required
        languages_list = []
        frameworks_list = []
        concepts_list = []
        tools_list = []
        
        lang_keywords = {"python", "javascript", "typescript", "go", "rust", "c++", "java", "ruby", "php", "html", "css"}
        framework_keywords = {"react", "fastapi", "django", "flask", "nextjs", "node", "angular", "vue", "spring", "express"}
        tool_keywords = {"docker", "git", "pytest", "npm", "yarn", "pip", "poetry", "uv", "pipenv", "postgresql", "mysql", "redis", "mongodb"}
        
        for s in skills_required:
            s_lower = s.lower()
            if any(k in s_lower for k in lang_keywords):
                languages_list.append(s)
            elif any(k in s_lower for k in framework_keywords):
                frameworks_list.append(s)
            elif any(k in s_lower for k in tool_keywords):
                tools_list.append(s)
            else:
                concepts_list.append(s)
                
        if not languages_list and not frameworks_list and not concepts_list and not tools_list:
            concepts_list.append("General Software Development")
            tools_list.append("Git")
            
        skills_rows = []
        if languages_list:
            skills_rows.append(["Programming Languages", ", ".join(languages_list)])
        if frameworks_list:
            skills_rows.append(["Frameworks", ", ".join(frameworks_list)])
        if concepts_list:
            skills_rows.append(["Concepts", ", ".join(concepts_list)])
        if tools_list:
            skills_rows.append(["Tools / Utilities", ", ".join(tools_list)])
            
        flowables.append(create_section_title("2. Skills Required"))
        flowables.append(Spacer(1, SPACING_SM))
        flowables.append(create_table(["Category", "Requirement"], skills_rows, col_widths=[150, None]))
        flowables.append(Spacer(1, SPACING_MD))
        
        # 4. Section 3: Repository Learning Path
        learning_path = roadmap.get("recommended_learning_order", [])
        flowables.append(create_section_title("3. Repository Learning Path"))
        flowables.append(Spacer(1, SPACING_SM))
        if learning_path:
            for idx, step in enumerate(learning_path):
                flowables.append(Paragraph(f"<b>{idx + 1}.</b> {step}", styles['DocBody']))
                flowables.append(Spacer(1, SPACING_XS))
        else:
            flowables.append(Paragraph("No specific learning path recommended.", styles['DocBody']))
        flowables.append(Spacer(1, SPACING_MD))
        
        # 5. Section 4: Files To Explore
        files_to_read = roadmap.get("files_to_read_first", [])
        if not files_to_read:
            files_to_read = possible_files
            
        def get_file_purpose(path: str, area: str) -> str:
            path_lower = path.lower()
            if "test" in path_lower or "spec" in path_lower:
                return "Test suite files for verifying module functionality."
            elif "readme" in path_lower:
                return "General project documentation and setup guidance."
            elif "contributing" in path_lower:
                return "Guidelines for contribution standards and workflow setup."
            elif "requirements" in path_lower or "pyproject.toml" in path_lower or "package.json" in path_lower:
                return "Dependency definitions and configuration management."
            elif path.endswith(".py"):
                return f"Python source code implementation file relevant to {area}."
            elif path.endswith((".js", ".jsx", ".ts", ".tsx")):
                return f"Frontend source code file relevant to {area}."
            elif path.endswith(".md"):
                return "Documentation file describing codebase components."
            else:
                return f"Codebase resource file relevant to {area}."
                
        file_rows = []
        for path in files_to_read:
            purpose = get_file_purpose(path, affected_area)
            file_rows.append([path, purpose])
            
        flowables.append(create_section_title("4. Files To Explore"))
        flowables.append(Spacer(1, SPACING_SM))
        if file_rows:
            flowables.append(create_table(["File", "Purpose"], file_rows, col_widths=[200, None]))
        else:
            flowables.append(Paragraph("No files identified for inspection.", styles['DocBody']))
        flowables.append(Spacer(1, SPACING_MD))
        
        # 6. Section 5: Suggested Workflow
        contribution_plan = roadmap.get("contribution_plan", [])
        if not contribution_plan:
            contribution_plan = [
                "Clone the repository and set up the local development environment.",
                "Create a new git branch for your issue resolution.",
                f"Locate the '{affected_area}' module and trace execution paths.",
                f"Implement the changes requested in issue #{best_issue_number}.",
                "Run unit and integration test suites to verify functionality.",
                "Commit your changes with descriptive messages.",
                "Push your branch to your fork on GitHub.",
                "Open a Pull Request comparing your branch against main."
            ]
            
        workflow_checklist = [(step, False) for step in contribution_plan]
        flowables.append(create_section_title("5. Suggested Workflow"))
        flowables.append(Spacer(1, SPACING_SM))
        flowables.extend(create_checklist(workflow_checklist))
        flowables.append(Spacer(1, SPACING_MD))
        
        # 7. Section 6: Testing Strategy
        languages_lower = [s.lower() for s in skills_required]
        commands = []
        tips = [
            "Always run the full test suite locally before pushing your changes.",
            "Write descriptive test cases that cover both happy paths and edge cases.",
            "Ensure that any third-party HTTP requests or heavy operations are properly mocked."
        ]
        
        if any(l in languages_lower for l in ["python", "django", "flask", "fastapi"]):
            commands.append("Run python tests: pytest tests/ or python -m unittest")
            tips.append("Run style checks using flake8 or black formatting tools.")
        elif any(l in languages_lower for l in ["javascript", "typescript", "react", "nextjs", "node"]):
            commands.append("Run tests using npm: npm test")
            commands.append("Run tests using yarn: yarn test")
            tips.append("Validate TypeScript syntax and linter checks using npm run lint.")
        else:
            commands.append("Consult project documentation (README.md/CONTRIBUTING.md) to locate test execution commands.")
            
        flowables.append(create_section_title("6. Testing Strategy"))
        flowables.append(Spacer(1, SPACING_SM))
        
        if commands:
            flowables.append(Paragraph("<b>Recommended Testing Commands:</b>", styles['DocBody']))
            flowables.append(Spacer(1, SPACING_XS))
            command_text = "<br/>".join(f"<code>{cmd}</code>" for cmd in commands)
            flowables.append(create_info_box(command_text))
            flowables.append(Spacer(1, SPACING_SM))
            
        flowables.append(Paragraph("<b>Testing Tips & Best Practices:</b>", styles['DocBody']))
        flowables.append(Spacer(1, SPACING_XS))
        flowables.extend(create_bullet_list(tips))
        flowables.append(Spacer(1, SPACING_SM))
        
        validation_checklist = [
            ("All unit tests run and pass without failures", False),
            ("New integration/unit tests added covering modifications", False),
            ("Edge cases (null parameters, invalid inputs) validated", False),
            ("No performance regressions introduced", False)
        ]
        flowables.append(Paragraph("<b>Validation Checklist:</b>", styles['DocBody']))
        flowables.append(Spacer(1, SPACING_XS))
        flowables.extend(create_checklist(validation_checklist))
        flowables.append(Spacer(1, SPACING_MD))
        
        # 8. Section 7: Pull Request Checklist
        pr_checklist = [
            ("Documentation updated in files or wiki", False),
            ("All new and existing tests pass locally", False),
            ("Code formatted correctly (style guide compliance checked)", False),
            ("Linter warnings and errors resolved", False),
            ("Visual screenshots or command outputs added (if applicable)", False),
            ("Pull Request description fully completed referencing issue", False)
        ]
        flowables.append(create_section_title("7. Pull Request Checklist"))
        flowables.append(Spacer(1, SPACING_SM))
        flowables.extend(create_checklist(pr_checklist))
        flowables.append(Spacer(1, SPACING_MD))
        
        # 9. Section 8: Additional Resources
        repo_url = build_repository_url(metadata)
        issue_url = build_issue_url(matching_issue.get("raw_issue", {}) if matching_issue else metadata, best_issue_number)
        readme_url = build_readme_url(metadata)
        contributing_url = build_contributing_url(metadata)
        
        resources_headers = ["Resource Name", "Description", "Clickable URL"]
        resources_rows = [
            [
                "Repository Home",
                "Main landing page of the GitHub repository.",
                f"<a href='{repo_url}'><font color='{COLOR_PRIMARY_PURPLE.hexval()}'><u>{repo_url}</u></font></a>"
            ],
            [
                "Target Issue",
                f"GitHub issue #{best_issue_number}: {best_issue_title}",
                f"<a href='{issue_url}'><font color='{COLOR_PRIMARY_PURPLE.hexval()}'><u>Issue #{best_issue_number}</u></font></a>"
            ],
            [
                "README",
                "Main repository README file with setup instructions.",
                f"<a href='{readme_url}'><font color='{COLOR_PRIMARY_PURPLE.hexval()}'><u>View README.md</u></font></a>"
            ],
            [
                "CONTRIBUTING",
                "Codebase contribution guidelines and standards.",
                f"<a href='{contributing_url}'><font color='{COLOR_PRIMARY_PURPLE.hexval()}'><u>View CONTRIBUTING.md</u></font></a>"
            ]
        ]
        
        homepage = metadata.get("homepage")
        if homepage:
            resources_rows.append([
                "Documentation",
                "Official homepage or documentation for the project.",
                f"<a href='{homepage}'><font color='{COLOR_PRIMARY_PURPLE.hexval()}'><u>{homepage}</u></font></a>"
            ])
            
        flowables.append(create_section_title("8. Additional Resources"))
        flowables.append(Spacer(1, SPACING_SM))
        flowables.append(create_table(resources_headers, resources_rows, col_widths=[120, 180, None]))
        flowables.append(Spacer(1, SPACING_MD))
        
        # 10. Final Section: Ready To Contribute
        flowables.append(create_section_title("Ready To Contribute"))
        flowables.append(Spacer(1, SPACING_SM))
        
        motivation_text = (
            "Congratulations! You now have a complete, structured roadmap to make your contribution. "
            "You know exactly <b>where to begin</b>, <b>what to modify</b>, <b>how to test</b>, and "
            "<b>how to submit</b> your changes. Contribution is a great way to grow your skills and "
            "help the open-source community. Good luck with your pull request!"
        )
        flowables.append(Paragraph(motivation_text, styles['DocBody']))
        flowables.append(Spacer(1, SPACING_SM))
        flowables.append(create_info_box("<b>Generated by RepoPilot</b><br/>Your automated onboarding and contribution companion."))
        
        # Build document and return generated PDF bytes
        return PDFService.generate_pdf(flowables, has_cover=True, title=f"Contribution Guide - {name}")

