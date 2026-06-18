export interface ApiResponse<T> {
  success: boolean;
  execution_time_seconds?: number;
  data: T | null;
  error: string | null;
}