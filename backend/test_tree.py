from app.services.github_service import GitHubService

g = GitHubService()

tree = g.get_repository_tree(
    "PostHog",
    "posthog"
)

print(len(tree))
print(tree.keys())