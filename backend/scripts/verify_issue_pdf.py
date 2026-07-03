import os
import sys
from dotenv import load_dotenv

# Ensure the backend directory is in the sys.path so app imports resolve
scripts_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(scripts_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Load environment variables from backend/.env
env_path = os.path.join(backend_dir, ".env")
load_dotenv(env_path)

def main():
    # 1. Accept repository URL or default
    default_url = "https://github.com/langchain-ai/langchain"
    repo_url = sys.argv[1] if len(sys.argv) > 1 else default_url
    
    print(f"Verifying Issue PDF Generation for: {repo_url}")
    
    try:
        # Import services & templates after path is initialized
        from app.utils.github_parser import parse_github_url
        from app.services.repo_service import RepoService
        from app.pdf.templates.issue_report import IssueReportTemplate
        
        # 2. Parse owner and repo name from URL
        parsed = parse_github_url(repo_url)
        owner = parsed["owner"]
        repo_name = parsed["repo"]
        
        # 3. Initialize and run RepoService pipeline
        print("Running repository analysis pipeline (this may take a moment)...")
        repo_service = RepoService()
        analysis_result = repo_service.analyze_repository(repo_url, mode="FAST_MVP")
        
        # 4. Select one analyzed issue
        issues = analysis_result.get("issues", [])
        if not issues:
            print("\n-------------------------------------------------")
            print("Status:\nFAILURE")
            print("Error: No issues analyzed in the repository results.")
            print("-------------------------------------------------")
            sys.exit(1)
            
        selected_issue = issues[0]
        
        # 5. Extract issue metadata for printout
        raw_issue = selected_issue.get("raw_issue", {})
        issue_number = raw_issue.get("number", "Unknown")
        issue_title = raw_issue.get("title", "Untitled Issue")
        
        # 6. Generate PDF bytes
        print("Generating Issue PDF document...")
        pdf_bytes = IssueReportTemplate.generate(
            issue_data=selected_issue,
            repo_name=repo_name
        )
        
        # 7. Write PDF output to generated/ folder
        generated_dir = os.path.join(backend_dir, "generated")
        os.makedirs(generated_dir, exist_ok=True)
        
        pdf_filename = f"{repo_name.lower()}_issue_{issue_number}_guide.pdf"
        pdf_path = os.path.join(generated_dir, pdf_filename)
        
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)
            
        # 8. Print requested clean console summary
        print("\n-------------------------------------------------")
        print(f"Repository: {repo_name}")
        print(f"Issue Number: {issue_number}")
        print(f"Issue Title: {issue_title}")
        print(f"Output:\nbackend/generated/{pdf_filename}")
        print("Status:\nSUCCESS")
        print("-------------------------------------------------")
        
        sys.exit(0)

    except Exception as e:
        import traceback
        print("\n-------------------------------------------------")
        print("Status:\nFAILURE")
        print(f"Error: {e}")
        print("-------------------------------------------------")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
