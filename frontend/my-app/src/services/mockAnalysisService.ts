export async function getRepositoryAnalysis(owner: string, repo: string) {
  try {
    // Dynamically import the local JSON file to simulate an external data fetch
    // In the future, this will be replaced with: await fetch(`/api/analysis?repo=${owner}/${repo}`)
    const data = await import("../../mock_data/sample_posthog_analysis.json");
    return data.default || data;
  } catch (error) {
    console.error("Failed to load mock data:", error);
    throw new Error("Analysis data not found");
  }
}