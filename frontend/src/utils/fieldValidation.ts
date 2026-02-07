// Copyright 2026 Bret McKee
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

export interface ValidationResult {
  isValid: boolean;
  error?: string;
  warning?: string;
  value?: unknown;
}

const MILLISECONDS_PER_HOUR = 3600000;

export function validateDuration(minutes: number | null | undefined): ValidationResult {
  if (minutes === null || minutes === undefined || minutes === 0) {
    return { isValid: true };
  }

  if (minutes < 1) {
    return { isValid: false, error: 'Duration must be at least 1 minute' };
  }

  const MAX_DURATION_MINUTES = 1440;
  if (minutes > MAX_DURATION_MINUTES) {
    return {
      isValid: false,
      error: `Duration cannot exceed ${MAX_DURATION_MINUTES} minutes (1 day)`,
    };
  }

  return { isValid: true };
}

export function validateReminderMinutes(value: string): ValidationResult {
  if (!value || value.trim() === '') {
    return { isValid: true, value: [] };
  }

  const parts = value.split(',').map((s) => s.trim());
  const numbers: number[] = [];

  for (const part of parts) {
    const num = Number(part);
    if (isNaN(num) || !Number.isInteger(num)) {
      return { isValid: false, error: 'All reminder values must be numeric integers' };
    }
    if (num < 1) {
      return { isValid: false, error: 'Reminder minutes must be at least 1' };
    }

    const MAX_REMINDER_MINUTES = 10080;
    if (num > MAX_REMINDER_MINUTES) {
      return {
        isValid: false,
        error: `Reminder minutes cannot exceed ${MAX_REMINDER_MINUTES} (1 week)`,
      };
    }
    numbers.push(num);
  }

  return { isValid: true, value: numbers };
}

export function validateMaxPlayers(value: string): ValidationResult {
  if (!value || value.trim() === '') {
    return { isValid: true };
  }

  const num = Number(value);
  if (isNaN(num) || !Number.isInteger(num)) {
    return { isValid: false, error: 'Max players must be a valid number' };
  }

  if (num < 1) {
    return { isValid: false, error: 'Max players must be at least 1' };
  }

  const MAX_PLAYERS = 100;
  if (num > MAX_PLAYERS) {
    return { isValid: false, error: `Max players cannot exceed ${MAX_PLAYERS}` };
  }

  return { isValid: true, value: num };
}

export function validateCharacterLimit(
  value: string,
  maxLength: number,
  fieldName: string
): ValidationResult {
  const length = value.length;

  if (length > maxLength) {
    return {
      isValid: false,
      error: `${fieldName} exceeds maximum length of ${maxLength} characters (current: ${length})`,
    };
  }

  const WARNING_THRESHOLD = 0.95;
  if (length >= maxLength * WARNING_THRESHOLD) {
    return {
      isValid: true,
      warning: `${fieldName} is at ${length}/${maxLength} characters (95% of limit)`,
    };
  }

  return { isValid: true };
}

export function validateFutureDate(
  date: Date | null | undefined,
  minHoursInFuture: number = 0
): ValidationResult {
  if (!date) {
    return { isValid: false, error: 'A valid date is required' };
  }

  const now = new Date();
  const minFutureTime = new Date(now.getTime() + minHoursInFuture * MILLISECONDS_PER_HOUR);

  if (date < minFutureTime) {
    if (minHoursInFuture === 0) {
      return { isValid: false, error: 'Date must be in the future' };
    }
    return {
      isValid: false,
      error: `Date must be at least ${minHoursInFuture} hours in the future`,
    };
  }

  return { isValid: true };
}
