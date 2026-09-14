import { ApiResponse } from '../types';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

export class ApiError extends Error {
  errorCode: string | null;
  status: number;

  constructor(message: string, errorCode: string | null = null, status: number = 500) {
    super(message);
    this.name = 'ApiError';
    this.errorCode = errorCode;
    this.status = status;
  }
}

export async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  const token = localStorage.getItem('veramedia_token');
  const headers = new Headers(options.headers || {});

  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  // Ensure JSON header if body is not FormData
  if (!(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const url = endpoint.startsWith('http') ? endpoint : `${BASE_URL}${endpoint}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      // Auto-clear invalid/expired token on authentication failures
      if (endpoint !== '/api/auth/login') {
        localStorage.removeItem('veramedia_token');
        localStorage.removeItem('veramedia_user');
      }
    }

    const data: ApiResponse<T> = await response.json().catch(() => ({
      success: false,
      message: `HTTP Error ${response.status}: ${response.statusText}`,
      data: null,
      error_code: `HTTP_${response.status}`,
    }));

    if (!response.ok || !data.success) {
      throw new ApiError(
        data.message || 'An unexpected error occurred.',
        data.error_code || `HTTP_${response.status}`,
        response.status
      );
    }

    return data;
  } catch (err: any) {
    if (err instanceof ApiError) {
      throw err;
    }

    const isNetworkError =
      err?.name === 'TypeError' ||
      err?.message === 'Failed to fetch' ||
      err?.message?.includes('NetworkError') ||
      err?.message?.includes('failed to fetch');

    const errorMessage = isNetworkError
      ? `Cannot connect to VeraMedia backend at ${BASE_URL}. The Flask backend server is not running or unreachable on port 5000.`
      : (err?.message || 'Unable to connect to VeraMedia AI backend server. Please verify port 5000 is running.');

    throw new ApiError(
      errorMessage,
      'NETWORK_ERROR',
      0
    );
  }
}
