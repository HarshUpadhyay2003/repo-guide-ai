import axios from 'axios';

export const apiClient = axios.create({
  // Fallback to localhost if env var is missing
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  // generous timeout for LLM generation tasks
  timeout: 60000, 
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use(
  (config) => {
    return config;
  },
  (error) => Promise.reject(error)
);

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    return Promise.reject(error);
  }
);