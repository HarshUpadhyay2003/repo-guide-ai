import { apiClient } from "./api";

/**
 * Returns a multi-tab safe sessionStorage key for a given repository.
 */
export function getStorageKey(owner: string, repo: string): string {
  return `repo_guide_analysis_${owner.toLowerCase()}_${repo.toLowerCase()}`;
}

/**
 * Saves repository analysis payload into sessionStorage under a repository-specific key.
 */
export function saveAnalysisToStorage(owner: string, repo: string, data: any): void {
  if (typeof window === "undefined") return;
  try {
    const key = getStorageKey(owner, repo);
    sessionStorage.setItem(key, JSON.stringify(data));
  } catch (err) {
    console.error("[Storage] Failed to save analysis to sessionStorage:", err);
  }
}

/**
 * Retrieves repository analysis payload from sessionStorage for a specific repository.
 */
export function getAnalysisFromStorage(owner: string, repo: string): any | null {
  if (typeof window === "undefined") return null;
  try {
    const key = getStorageKey(owner, repo);
    const stored = sessionStorage.getItem(key);
    if (stored) {
      const parsed = JSON.parse(stored);
      return parsed.data || parsed;
    }
  } catch (err) {
    console.error("[Storage] Failed to read analysis from sessionStorage:", err);
  }
  return null;
}

/**
 * Fetches cached repository analysis payload from backend GET /repo/analysis endpoint.
 */
export async function fetchAnalysisFromBackend(owner: string, repo: string): Promise<any> {
  const response = await apiClient.get(`/repo/analysis?owner=${encodeURIComponent(owner)}&repo=${encodeURIComponent(repo)}`);
  return response.data;
}

/**
 * Get analysis data, checking sessionStorage first, then falling back to backend cache.
 */
export async function getOrFetchAnalysis(owner: string, repo: string): Promise<any | null> {
  // 1. Try local session storage
  const localData = getAnalysisFromStorage(owner, repo);
  if (localData) {
    return localData;
  }

  // 2. Fall back to backend cache
  try {
    const remoteData = await fetchAnalysisFromBackend(owner, repo);
    if (remoteData) {
      saveAnalysisToStorage(owner, repo, remoteData);
      return remoteData;
    }
  } catch (err) {
    console.warn(`[AnalysisDataService] Backend cache miss/error for ${owner}/${repo}:`, err);
  }

  return null;
}
