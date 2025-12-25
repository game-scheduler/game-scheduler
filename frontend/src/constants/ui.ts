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
   * Number of hex digits for color padding.
   */
  HEX_COLOR_PADDING: 6,

  /**
   * Grid spacing for layouts (MUI grid columns).
   */
  GRID_SPACING_LARGE: 16,
  GRID_SPACING_SMALL: 6,
} as const;
