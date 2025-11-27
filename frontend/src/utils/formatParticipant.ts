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
 * Formats a participant's display for UI presentation.
 * 
 * @param displayName - The participant's display name (nullable)
 * @param discordId - The participant's Discord ID (nullable/optional)
 * @returns Formatted string for display
 * 
 * Rules:
 * - Discord users (have discord_id): Prepend @ to display name, or use <@id> if no name
 * - Placeholders (no discord_id): Return as-is without @
 */
export const formatParticipantDisplay = (
  displayName: string | null,
  discordId?: string | null
): string => {
  // If we have a discord_id, this is a Discord user
  if (discordId) {
    // Prefer display name with @ prefix if available
    if (displayName) {
      return displayName.startsWith('@') ? displayName : `@${displayName}`;
    }
    // Fallback to Discord ID format if no display name
    return `<@${discordId}>`;
  }
  
  // No discord_id means this is a placeholder - return display_name as-is without @
  if (displayName) {
    return displayName;
  }
  
  return 'Unknown User';
};
