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

import { describe, it, expect } from 'vitest';
import {
  validateDuration,
  validateReminderMinutes,
  validateMaxPlayers,
  validateCharacterLimit,
  validateFutureDate,
} from '../fieldValidation';

describe('validateDuration', () => {
  it('should accept null as valid (optional field)', () => {
    const result = validateDuration(null);
    expect(result.isValid).toBe(true);
    expect(result.error).toBeUndefined();
  });

  it('should accept 0 as valid (optional field)', () => {
    const result = validateDuration(0);
    expect(result.isValid).toBe(true);
    expect(result.error).toBeUndefined();
  });

  it('should accept 1 minute as valid', () => {
    const result = validateDuration(1);
    expect(result.isValid).toBe(true);
    expect(result.error).toBeUndefined();
  });

  it('should accept 120 minutes as valid', () => {
    const result = validateDuration(120);
    expect(result.isValid).toBe(true);
    expect(result.error).toBeUndefined();
  });

  it('should accept 1440 minutes (1 day) as valid maximum', () => {
    const result = validateDuration(1440);
    expect(result.isValid).toBe(true);
    expect(result.error).toBeUndefined();
  });

  it('should reject 1441 minutes (exceeds max)', () => {
    const result = validateDuration(1441);
    expect(result.isValid).toBe(false);
    expect(result.error).toContain('1440');
  });

  it('should reject negative minutes', () => {
    const result = validateDuration(-5);
    expect(result.isValid).toBe(false);
    expect(result.error).toBeDefined();
  });
});

describe('validateReminderMinutes', () => {
  it('should accept empty string as valid (optional field)', () => {
    const result = validateReminderMinutes('');
    expect(result.isValid).toBe(true);
    expect(result.value).toEqual([]);
  });

  it('should parse single valid value', () => {
    const result = validateReminderMinutes('60');
    expect(result.isValid).toBe(true);
    expect(result.value).toEqual([60]);
  });

  it('should parse multiple valid values', () => {
    const result = validateReminderMinutes('60,15');
    expect(result.isValid).toBe(true);
    expect(result.value).toEqual([60, 15]);
  });

  it('should reject non-numeric value', () => {
    const result = validateReminderMinutes('abc');
    expect(result.isValid).toBe(false);
    expect(result.error).toContain('numeric');
  });

  it('should reject mixed valid and invalid values', () => {
    const result = validateReminderMinutes('60,abc,15');
    expect(result.isValid).toBe(false);
    expect(result.error).toContain('numeric');
  });

  it('should reject negative value', () => {
    const result = validateReminderMinutes('-60');
    expect(result.isValid).toBe(false);
    expect(result.error).toBeDefined();
  });

  it('should reject value exceeding 10080 (1 week)', () => {
    const result = validateReminderMinutes('10081');
    expect(result.isValid).toBe(false);
    expect(result.error).toContain('10080');
  });
});

describe('validateMaxPlayers', () => {
  it('should accept empty string as valid (optional field)', () => {
    const result = validateMaxPlayers('');
    expect(result.isValid).toBe(true);
    expect(result.value).toBeUndefined();
  });

  it('should accept 1 as minimum valid value', () => {
    const result = validateMaxPlayers('1');
    expect(result.isValid).toBe(true);
    expect(result.value).toBe(1);
  });

  it('should accept 50 as middle range value', () => {
    const result = validateMaxPlayers('50');
    expect(result.isValid).toBe(true);
    expect(result.value).toBe(50);
  });

  it('should accept 100 as maximum valid value', () => {
    const result = validateMaxPlayers('100');
    expect(result.isValid).toBe(true);
    expect(result.value).toBe(100);
  });

  it('should reject 0', () => {
    const result = validateMaxPlayers('0');
    expect(result.isValid).toBe(false);
    expect(result.error).toContain('1');
  });

  it('should reject 101 (exceeds max)', () => {
    const result = validateMaxPlayers('101');
    expect(result.isValid).toBe(false);
    expect(result.error).toContain('100');
  });

  it('should reject non-numeric value', () => {
    const result = validateMaxPlayers('abc');
    expect(result.isValid).toBe(false);
    expect(result.error).toContain('number');
  });

  it('should reject negative value', () => {
    const result = validateMaxPlayers('-5');
    expect(result.isValid).toBe(false);
    expect(result.error).toBeDefined();
  });
});

describe('validateCharacterLimit', () => {
  it('should accept value within limit', () => {
    const result = validateCharacterLimit('hello', 100, 'Test Field');
    expect(result.isValid).toBe(true);
    expect(result.error).toBeUndefined();
    expect(result.warning).toBeUndefined();
  });

  it('should warn at 95% threshold', () => {
    const value = 'a'.repeat(95);
    const result = validateCharacterLimit(value, 100, 'Test Field');
    expect(result.isValid).toBe(true);
    expect(result.warning).toBeDefined();
    expect(result.warning).toContain('95');
  });

  it('should reject value exceeding limit', () => {
    const value = 'a'.repeat(101);
    const result = validateCharacterLimit(value, 100, 'Test Field');
    expect(result.isValid).toBe(false);
    expect(result.error).toContain('100');
    expect(result.error).toContain('101');
  });

  it('should accept empty string', () => {
    const result = validateCharacterLimit('', 100, 'Test Field');
    expect(result.isValid).toBe(true);
  });

  it('should accept value exactly at limit', () => {
    const value = 'a'.repeat(100);
    const result = validateCharacterLimit(value, 100, 'Test Field');
    expect(result.isValid).toBe(true);
    expect(result.error).toBeUndefined();
  });
});

describe('validateFutureDate', () => {
  it('should reject null date', () => {
    const result = validateFutureDate(null);
    expect(result.isValid).toBe(false);
    expect(result.error).toContain('date');
  });

  it('should reject past date', () => {
    const pastDate = new Date('2020-01-01');
    const result = validateFutureDate(pastDate);
    expect(result.isValid).toBe(false);
    expect(result.error).toContain('future');
  });

  it('should accept future date', () => {
    const futureDate = new Date(Date.now() + 86400000);
    const result = validateFutureDate(futureDate);
    expect(result.isValid).toBe(true);
  });

  it('should reject date not meeting minHours requirement', () => {
    const nearFutureDate = new Date(Date.now() + 3600000);
    const result = validateFutureDate(nearFutureDate, 2);
    expect(result.isValid).toBe(false);
    expect(result.error).toContain('2');
  });

  it('should reject undefined date', () => {
    const result = validateFutureDate(undefined);
    expect(result.isValid).toBe(false);
    expect(result.error).toContain('date');
  });

  it('should accept date meeting minHours requirement', () => {
    const futureDate = new Date(Date.now() + 7200000);
    const result = validateFutureDate(futureDate, 2);
    expect(result.isValid).toBe(true);
  });
});
