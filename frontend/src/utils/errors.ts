// Copyright 2025 Bret McKee (bret.mckee@gmail.com)
//
// This file is part of Game_Scheduler. (https://github.com/game-scheduler)
//
// Game_Scheduler is free software: you can redistribute it and/or
// modify it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or (at your
// option) any later version.
//
// Game_Scheduler is distributed in the hope that it will be
// useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General
// Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License along
// with Game_Scheduler If not, see <https://www.gnu.org/licenses/>.

/**
 * Type-safe error handling utilities for API errors.
 */

/**
 * Structure of errors returned from axios/API calls.
 */
export interface ApiError {
  response?: {
    status?: number;
    data?: {
      detail?: string | ApiErrorDetail;
    };
  };
  message?: string;
}

/**
 * Structured API error detail object.
 */
export interface ApiErrorDetail {
  error?: string;
  message?: string;
  [key: string]: unknown;
}

/**
 * Type guard to check if an unknown error is an API error.
 */
export function isApiError(error: unknown): error is ApiError {
  return (
    typeof error === 'object' &&
    error !== null &&
    'response' in error &&
    typeof (error as ApiError).response === 'object'
  );
}

/**
 * Extract a user-friendly error message from an unknown error.
 * Handles both string and object error details from API responses.
 *
 * @param error - The error to extract a message from
 * @param fallback - Default message if no specific message found
 * @returns User-friendly error message
 */
export function getErrorMessage(error: unknown, fallback = 'An error occurred'): string {
  if (isApiError(error)) {
    const detail = error.response?.data?.detail;

    if (typeof detail === 'string') {
      return detail;
    }

    if (typeof detail === 'object' && detail !== null) {
      return detail.message || fallback;
    }
  }

  if (error instanceof Error) {
    return error.message;
  }

  return fallback;
}

/**
 * Check if an API error has a specific status code.
 */
export function hasStatusCode(error: unknown, statusCode: number): boolean {
  return isApiError(error) && error.response?.status === statusCode;
}

/**
 * Extract structured error detail from API error.
 */
export function getErrorDetail(error: unknown): ApiErrorDetail | null {
  if (!isApiError(error)) {
    return null;
  }

  const detail = error.response?.data?.detail;

  if (typeof detail === 'object' && detail !== null) {
    return detail as ApiErrorDetail;
  }

  return null;
}
