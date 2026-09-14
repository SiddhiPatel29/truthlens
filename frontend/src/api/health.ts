import { request } from './client';
import { ApiResponse, HealthStatus } from '../types';

export async function getHealth(): Promise<ApiResponse<HealthStatus>> {
  return request<HealthStatus>('/api/health', {
    method: 'GET',
  });
}
