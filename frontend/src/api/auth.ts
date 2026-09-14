import { request } from './client';
import { ApiResponse, LoginResponse, UserProfile } from '../types';

export async function loginUser(email: string, password: string): Promise<ApiResponse<LoginResponse>> {
  return request<LoginResponse>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export async function registerUser(name: string, email: string, password: string): Promise<ApiResponse<UserProfile>> {
  return request<UserProfile>('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify({ name, email, password }),
  });
}

export async function getCurrentUser(): Promise<ApiResponse<UserProfile>> {
  return request<UserProfile>('/api/auth/me', {
    method: 'GET',
  });
}
