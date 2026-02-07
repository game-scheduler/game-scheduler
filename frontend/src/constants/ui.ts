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
 * UI and UX constants for the application.
 *
 * Defines animation delays, file size limits, and styling values.
 */

const BYTES_PER_KB = 1024;
const KB_PER_MB = 1024;
const MB_FILE_SIZE_LIMIT = 5;

export const UI = {
  /**
   * Short animation delay in milliseconds (1.5 seconds).
   */
  ANIMATION_DELAY_SHORT: 1500,

  /**
   * Standard animation delay in milliseconds (3 seconds).
   */
  ANIMATION_DELAY_STANDARD: 3000,

  /**
   * Maximum file upload size in bytes (5 MB).
   */
  MAX_FILE_SIZE_BYTES: MB_FILE_SIZE_LIMIT * KB_PER_MB * BYTES_PER_KB,

  /**
   * Standard avatar image size in pixels.
   */
  AVATAR_SIZE: 200,

  /**
   * Hover effect opacity value.
   */
  HOVER_OPACITY: 0.5,

  /**
   * Default maximum description length for text truncation (characters).
   */
  DEFAULT_TRUNCATE_LENGTH: 200,

  /**
   * Default max players when none specified.
   */
  DEFAULT_MAX_PLAYERS: 10,

  /**
   * Maximum allowed players in a game.
   */
  MAX_PLAYERS_LIMIT: 100,

  /**
   * Maximum description length (characters).
   */
  MAX_DESCRIPTION_LENGTH: 4000,

  /**
   * Maximum location length (characters).
   */
  MAX_LOCATION_LENGTH: 500,

  /**
   * Maximum signup instructions length (characters).
   */
  MAX_SIGNUP_INSTRUCTIONS_LENGTH: 1000,

  /**
   * Number of hex digits for color padding.
   */
  HEX_COLOR_PADDING: 6,

  /**
   * Grid spacing for layouts (MUI grid columns).
   */
  GRID_SPACING_LARGE: 16,
  GRID_SPACING_SMALL: 6,
} as const;
