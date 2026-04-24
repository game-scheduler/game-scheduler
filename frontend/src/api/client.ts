// Copyright 2025-2026 Bret McKee
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in all
// copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.

import axios from 'axios';
import { StatusCodes } from 'http-status-codes';

// Runtime config from /config.js (loaded in index.html)
// Falls back to VITE_BACKEND_URL for development
// BACKEND_URL is always required and should be set to the full backend API URL
declare global {
  interface Window {
    __RUNTIME_CONFIG__?: {
      BACKEND_URL?: string;
    };
  }
}

const API_BASE_URL =
  window.__RUNTIME_CONFIG__?.BACKEND_URL || import.meta.env.VITE_BACKEND_URL || '';

// Serializes params so arrays produce repeated key=val1&key=val2 pairs,
// which FastAPI expects for list[str] query params.
export function serializeParams(params: Record<string, unknown>): string {
  const searchParams = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (Array.isArray(value)) {
      for (const v of value) {
        searchParams.append(key, String(v));
      }
    } else if (value !== undefined && value !== null) {
      searchParams.append(key, String(value));
    }
  }
  return searchParams.toString();
}

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
  paramsSerializer: { serialize: serializeParams },
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Skip interceptor logic if we're already on login or callback pages
    const isAuthPage =
      window.location.pathname === '/login' ||
      window.location.pathname === '/auth/callback' ||
      window.location.pathname === '/';

    // Don't retry if this is already a retry, or if this is the refresh endpoint itself
    if (
      error.response?.status === StatusCodes.UNAUTHORIZED &&
      !originalRequest._retry &&
      !originalRequest.url?.includes('/auth/refresh') &&
      !isAuthPage
    ) {
      originalRequest._retry = true;

      try {
        await apiClient.post('/api/v1/auth/refresh');
        return apiClient(originalRequest);
      } catch (_refreshError) {
        // Refresh failed, redirect to login
        window.location.href = '/login';
        return new Promise(() => {}); // Never resolves, prevents further processing
      }
    }

    // For 401 on refresh endpoint or already retried requests, redirect to login (unless already on login page)
    if (error.response?.status === StatusCodes.UNAUTHORIZED && !isAuthPage) {
      window.location.href = '/login';
      return new Promise(() => {}); // Never resolves, prevents further processing
    }

    return Promise.reject(error);
  }
);
