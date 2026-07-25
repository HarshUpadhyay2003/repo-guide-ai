export const API_ENDPOINTS = {
  ANALYZE_REPO: '/api/v1/analyze',
} as const;

export const QUERY_KEYS = {
  ANALYSIS: 'analysis',
  REPOSITORY: 'repository',
} as const;

export const ROUTES = {
  HOME: '/',
  REPO_DASHBOARD: (owner: string, name: string) => `/repo/${owner}/${name}`,
  ISSUE_DETAIL: (owner: string, name: string, issueId: string | number) => `/repo/${owner}/${name}/issue/${issueId}`,
} as const;

export const APP_CONFIG = {
  APP_NAME: 'RepoGuideAI',
} as const;