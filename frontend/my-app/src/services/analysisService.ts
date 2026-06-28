import { apiClient } from "./api";

export async function analyzeRepository(payload: { url: string }) {
  const response = await apiClient.post('/repo/analyze', payload);
  return response.data;
}