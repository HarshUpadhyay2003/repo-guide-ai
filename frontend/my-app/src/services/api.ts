import axios from 'axios';
import { ENV } from '../lib/env';

export const apiClient = axios.create({
  baseURL: ENV.API_BASE_URL,
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