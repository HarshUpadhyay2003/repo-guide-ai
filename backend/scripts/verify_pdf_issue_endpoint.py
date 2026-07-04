import os
import sys
from unittest.mock import patch
from fastapi.testclient import TestClient

# Ensure the backend directory is in the sys.path so app imports resolve
scripts_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(scripts_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from dotenv import load_dotenv
env_path = os.path.join(backend_dir, ".env")
load_dotenv(env_path)

from main import app
from app.services.repo_service import RepoService
from app.core.cache.dependencies import get_cache_manager

def main():
    default_url = "https://github.com/pallets/flask/"
    repo_url = sys.argv[1] if len(sys.argv) > 1 else default_url
    
    print(f"Verifying GET /pdf/issue/{{issue_number}} for: {repo_url}")
    
    try:
        from app.utils.github_parser import parse_github_url
        parsed = parse_github_url(repo_url)
        owner = parsed["owner"]
        repo = parsed["repo"]
        
        # 1. Run repository analysis to populate cache (mocking get_good_first_issues to ensure we have issues)
        print("Running repository analysis to populate snapshot cache...")
        repo_service = RepoService()
        
        mock_issue = {
            "number": 12345,
            "title": "Mock Issue Title",
            "body": "Mock Issue Body explaining the problem.",
            "url": "https://github.com/pallets/flask/issues/12345",
            "labels": ["good first issue"],
            "created_at": "2026-07-04T12:00:00Z",
            "comments": 0
        }
        
        with patch("app.services.github_service.GitHubService.get_good_first_issues", return_value=[mock_issue]):
            analysis_result = repo_service.analyze_repository(repo_url, mode="FAST_MVP")

        
        # 2. Select one analyzed issue
        issues = analysis_result.get("issues", [])
        if not issues:
            print("\n-------------------------------------------------")
            print("Status:\nFAILURE")
            print("Error: No issues analyzed in the repository results.")
            print("-------------------------------------------------")
            sys.exit(1)
            
        selected_issue = issues[0]
        raw_issue = selected_issue.get("raw_issue", {})
        issue_number = raw_issue.get("number")
        
        if not issue_number:
            print("\n-------------------------------------------------")
            print("Status:\nFAILURE")
            print("Error: Selected issue lacks a valid issue number.")
            print("-------------------------------------------------")
            sys.exit(1)
            
        print(f"Selected issue #{issue_number} for verification.")
        
        # 3. Verify cache has the analysis snapshot
        cache_mgr = get_cache_manager()
        snapshot = cache_mgr.get_analysis(owner, repo)
        if not snapshot:
            print("\n-------------------------------------------------")
            print("Status:\nFAILURE")
            print("Error: Analysis snapshot not found in cache after analysis.")
            print("-------------------------------------------------")
            sys.exit(1)
            
        print("Analysis snapshot successfully found in cache.")
        
        # 4. Call PDF issue endpoint
        client = TestClient(app)
        
        # We will mock GitHubService and LLMService during the GET /pdf/issue/{number} call
        # to ensure that NO GitHub or LLM requests are made.
        print(f"Calling GET /pdf/issue/{issue_number} endpoint (with mocked external services)...")
        
        def assert_no_external_call(*args, **kwargs):
            raise AssertionError("Endpoint attempted to make an external GitHub or LLM call!")
            
        with patch("app.services.github_service.GitHubService.get_repo_metadata", side_effect=assert_no_external_call), \
             patch("app.services.github_service.GitHubService.get_readme", side_effect=assert_no_external_call), \
             patch("app.services.github_service.GitHubService.get_contributing", side_effect=assert_no_external_call), \
             patch("app.services.github_service.GitHubService.get_repository_tree", side_effect=assert_no_external_call), \
             patch("app.services.github_service.GitHubService.get_good_first_issues", side_effect=assert_no_external_call), \
             patch("app.services.github_service.GitHubService.get_issue_comments", side_effect=assert_no_external_call), \
             patch("app.services.llm_service.LLMService.generate_json", side_effect=assert_no_external_call):
            
            response = client.get(f"/pdf/issue/{issue_number}?owner={owner}&repo={repo}")
            
        if response.status_code != 200:
            print("\n-------------------------------------------------")
            print("Status:\nFAILURE")
            print(f"Error: PDF Issue endpoint returned status code {response.status_code}")
            print(f"Detail: {response.text}")
            print("-------------------------------------------------")
            sys.exit(1)
            
        # 5. Verify headers and content
        content_type = response.headers.get("content-type")
        content_disposition = response.headers.get("content-disposition")
        
        print(f"Response Content-Type: {content_type}")
        print(f"Response Content-Disposition: {content_disposition}")
        
        if content_type != "application/pdf":
            print("\n-------------------------------------------------")
            print("Status:\nFAILURE")
            print(f"Error: Content-Type is {content_type}, expected application/pdf")
            print("-------------------------------------------------")
            sys.exit(1)
            
        expected_filename = f"{repo.lower()}_issue_{issue_number}_guide.pdf"
        if f"filename={expected_filename}" not in content_disposition:
            print("\n-------------------------------------------------")
            print("Status:\nFAILURE")
            print(f"Error: Content-Disposition is {content_disposition}, expected filename={expected_filename}")
            print("-------------------------------------------------")
            sys.exit(1)
            
        # 6. Write PDF output to generated/ folder
        generated_dir = os.path.join(backend_dir, "generated")
        os.makedirs(generated_dir, exist_ok=True)
        pdf_path = os.path.join(generated_dir, expected_filename)
        
        with open(pdf_path, "wb") as f:
            f.write(response.content)
            
        print("\n-------------------------------------------------")
        print(f"Repository: {owner}/{repo}")
        print(f"Issue Number: {issue_number}")
        print(f"Output:\nbackend/generated/{expected_filename}")
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
