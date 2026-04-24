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
import { serializeParams } from './client';

describe('serializeParams', () => {
  it('serializes array values as repeated key=value pairs', () => {
    const result = serializeParams({ status: ['SCHEDULED', 'COMPLETED'] });
    expect(result).toBe('status=SCHEDULED&status=COMPLETED');
  });

  it('serializes a single-element array as one key=value pair', () => {
    const result = serializeParams({ status: ['SCHEDULED'] });
    expect(result).toBe('status=SCHEDULED');
  });

  it('serializes scalar string values', () => {
    const result = serializeParams({ guild_id: 'guild-1' });
    expect(result).toBe('guild_id=guild-1');
  });

  it('serializes mixed array and scalar params', () => {
    const result = serializeParams({ guild_id: 'guild-1', status: ['SCHEDULED', 'IN_PROGRESS'] });
    expect(result).toBe('guild_id=guild-1&status=SCHEDULED&status=IN_PROGRESS');
  });

  it('omits undefined values', () => {
    const result = serializeParams({ guild_id: undefined, status: ['SCHEDULED'] });
    expect(result).toBe('status=SCHEDULED');
  });

  it('omits null values', () => {
    const result = serializeParams({ guild_id: null, status: ['SCHEDULED'] });
    expect(result).toBe('status=SCHEDULED');
  });

  it('returns empty string for empty params', () => {
    const result = serializeParams({});
    expect(result).toBe('');
  });
});
