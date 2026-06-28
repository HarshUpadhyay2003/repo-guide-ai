import os
import sys

# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))
sys.path.append(os.path.dirname(__file__))

# Set mock env variables or load dotenv
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

from app.services.repository_map_service import RepositoryMapService

def test_repo(owner, repo):
    print("=" * 80)
    print(f"TESTING REPOSITORY: {owner}/{repo}")
    print("=" * 80)
    service = RepositoryMapService()
    try:
        repo_map = service.generate_map(owner, repo)
        print("\nResulting Repository Map:")
        for category, paths in repo_map.items():
            print(f"  {category.upper()} ({len(paths)}):")
            for path in sorted(paths)[:5]:
                print(f"    - {path}")
            if len(paths) > 5:
                print(f"    - ... and {len(paths) - 5} more")
    except Exception as e:
        print(f"Failed to generate repository map: {e}")

if __name__ == '__main__':
    # Test repos
    repos = [
        ("PostHog", "posthog"),
        ("langchain-ai", "langchain"),
        ("supabase", "supabase"),
        ("appwrite", "appwrite")
    ]
    for owner, repo in repos:
        test_repo(owner, repo)
