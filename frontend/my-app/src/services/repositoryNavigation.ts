export const REPOPILOT_GITHUB_URL = 'https://github.com/HarshUpadhyay2003/repo-guide-ai';
export const REPOPILOT_DOCS_URL = 'https://github.com/HarshUpadhyay2003/repo-guide-ai/blob/main/README.md';

export interface RepositoryNavigationResult {
  url: string;
  isFallback: boolean;
  repositoryName: string;
}

/**
 * Reconstructs current repository identity from URL search parameters, path context, or sessionStorage cache.
 */
export function resolveRepositoryFromContext(
  pathname: string,
  searchParams?: { get: (key: string) => string | null } | null
): string | null {
  // 1. Check search parameters (?repo=owner/name or ?repository=owner/name)
  if (searchParams) {
    const repoParam = searchParams.get('repo') || searchParams.get('repository');
    if (repoParam && repoParam.trim().length > 0) {
      const clean = repoParam.trim();
      return clean.includes('/') ? clean : `PostHog/${clean}`;
    }
  }

  // 2. Check sessionStorage for cached repository context if on report routes
  if (typeof window !== 'undefined' && pathname.startsWith('/report')) {
    try {
      for (let i = 0; i < sessionStorage.length; i++) {
        const key = sessionStorage.key(i);
        if (key && key.startsWith('repo_guide_analysis_')) {
          const raw = sessionStorage.getItem(key);
          if (raw) {
            const parsed = JSON.parse(raw);
            const data = parsed.data || parsed;
            if (data?.metadata?.name) {
              return data.metadata.name;
            }
          }
        }
      }
    } catch {
      // ignore
    }
  }

  return null;
}

/**
 * Returns dynamic GitHub URL based on active repository context.
 * Falls back safely to RepoPilot GitHub URL if no context exists.
 */
export function getRepositoryGitHubUrl(
  pathname: string,
  searchParams?: { get: (key: string) => string | null } | null
): RepositoryNavigationResult {
  const repo = resolveRepositoryFromContext(pathname, searchParams);

  if (repo) {
    return {
      url: `https://github.com/${repo}`,
      isFallback: false,
      repositoryName: repo,
    };
  }

  return {
    url: REPOPILOT_GITHUB_URL,
    isFallback: true,
    repositoryName: 'HarshUpadhyay2003/repo-guide-ai',
  };
}

/**
 * Returns RepoPilot's official documentation URL.
 */
export function getDocumentationUrl(): string {
  return REPOPILOT_DOCS_URL;
}
