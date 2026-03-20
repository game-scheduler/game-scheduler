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

/**
 * Time conversion constants.
 *
 * Defines standard time unit conversions.
 */

export const Time = {
  /**
   * Number of seconds in one minute.
   */
  SECONDS_PER_MINUTE: 60,

  /**
   * Number of seconds in one hour.
   */
  SECONDS_PER_HOUR: 3600,

  /**
   * Number of seconds in one day.
   */
  SECONDS_PER_DAY: 86400,

  /**
   * Number of milliseconds in one second.
   */
  MILLISECONDS_PER_SECOND: 1000,

  /**
   * Number of minutes in a half hour.
   */
  MINUTES_PER_HALF_HOUR: 30,
} as const;
