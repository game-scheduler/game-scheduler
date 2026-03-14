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

import { StatusCodes } from 'http-status-codes';
import { apiClient } from '../api/client';

/**
 * Check if user has permission to create games on a guild by checking template access.
 * Returns true if user has access to at least one template, false otherwise.
 */
export async function canUserCreateGames(guildId: string): Promise<boolean> {
  try {
    const templates = await apiClient.get(`/api/v1/guilds/${guildId}/templates`);
    return templates.data && templates.data.length > 0;
  } catch {
    // User has no accessible templates (403 or other error)
    return false;
  }
}

/**
 * Check if the current user can manage (edit/clone) a game.
 * The backend sets can_manage=true when the user is the host, a bot manager, or a maintainer.
 */
export function canManageGame(game: { can_manage?: boolean } | null): boolean {
  return !!game?.can_manage;
}

/**
 * Check if user has bot manager permissions for a guild.
 * Bot managers can manage templates, channels, and have elevated permissions.
 * Returns true if user has bot manager role or MANAGE_GUILD permission.
 */
export async function canUserManageBotSettings(guildId: string): Promise<boolean> {
  try {
    const response = await apiClient.get(`/api/v1/guilds/${guildId}/config`);
    return response.status === StatusCodes.OK;
  } catch (error: any) {
    if (error.response?.status === StatusCodes.FORBIDDEN) {
      return false;
    }
    return false;
  }
}
