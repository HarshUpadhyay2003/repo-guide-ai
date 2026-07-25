import pytest
from app.pdf.utils.link_builder import build_issue_url, build_repository_url, parse_repo_info

def test_build_issue_url_from_direct_html_url():
    """Verify that direct GitHub API html_url or url containing /issues/ is returned as canonical URL."""
    raw_issue = {
        "number": 31267,
        "title": "Fix issue link generation",
        "html_url": "https://github.com/PostHog/posthog/issues/31267",
        "url": "https://github.com/PostHog/posthog/issues/31267",
    }
    url = build_issue_url(raw_issue, 31267)
    assert url == "https://github.com/PostHog/posthog/issues/31267"

def test_build_issue_url_across_multiple_repositories():
    """Verify issue URL generation for various public open-source repos."""
    cases = [
        ("microsoft", "vscode", 12345, "https://github.com/microsoft/vscode/issues/12345"),
        ("langchain-ai", "langchain", 500, "https://github.com/langchain-ai/langchain/issues/500"),
        ("PostHog", "posthog", 31267, "https://github.com/PostHog/posthog/issues/31267"),
    ]
    for owner, repo, issue_num, expected_url in cases:
        # Case 1: metadata with owner and repo
        metadata = {"owner": owner, "repo": repo}
        assert build_issue_url(metadata, issue_num) == expected_url

        # Case 2: metadata with owner and name
        metadata_name = {"owner": owner, "name": repo}
        assert build_issue_url(metadata_name, issue_num) == expected_url

        # Case 3: metadata with html_url containing issue
        metadata_html = {"html_url": expected_url}
        assert build_issue_url(metadata_html, issue_num) == expected_url

def test_build_repository_url_does_not_duplicate_issues_path():
    """Verify build_repository_url cleanly extracts repo home URL even when given an issue URL."""
    issue_meta = {
        "html_url": "https://github.com/microsoft/vscode/issues/9999",
    }
    repo_url = build_repository_url(issue_meta)
    assert repo_url == "https://github.com/microsoft/vscode"

    # build_issue_url should not produce duplicate /issues/ paths
    issue_url = build_issue_url(issue_meta, 9999)
    assert issue_url == "https://github.com/microsoft/vscode/issues/9999"
