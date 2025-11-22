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


export interface User {
  discordId: string;
  createdAt: string;
  updatedAt: string;
}

export interface Guild {
  id: string;
  guild_id: string;
  guild_name: string;
  default_max_players: number;
  default_reminder_minutes: number[];
  allowed_host_role_ids: string[];
  bot_manager_role_ids: string[] | null;
  require_host_role: boolean;
  created_at: string;
  updated_at: string;
}

export interface Channel {
  id: string; // Database UUID (use for navigation and API calls)
  guild_id: string;
  channel_id: string; // Discord snowflake (internal only)
  channel_name: string;
  is_active: boolean;
  max_players: number | null;
  reminder_minutes: number[] | null;
  allowed_host_role_ids: string[] | null;
  game_category: string | null;
  created_at: string;
  updated_at: string;
}

export interface GameSession {
  id: string;
  title: string;
  description: string;
  signup_instructions: string | null;
  scheduled_at: string;
  scheduled_at_unix: number;
  min_players: number | null;
  max_players: number | null;
  guild_id: string;
  channel_id: string;
  channel_name: string | null;
  message_id: string | null;
  host: Participant;
  reminder_minutes: number[] | null;
  notify_role_ids: string[] | null;
  status: 'SCHEDULED' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED';
  participant_count: number;
  participants?: Participant[];
  created_at: string;
  updated_at: string;
}

export interface Participant {
  id: string;
  game_session_id: string;
  user_id: string | null;
  discord_id: string | null;
  display_name: string | null;
  joined_at: string;
  pre_filled_position: number | null;
}

export interface GameListResponse {
  games: GameSession[];
  total: number;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}

export interface CurrentUser {
  id: string;
  user_uuid: string;
  username: string;
  discordId?: string; // For backward compatibility
  discriminator?: string;
  avatar?: string | null;
  guilds?: DiscordGuild[];
}

export interface DiscordGuild {
  id: string;
  name: string;
  icon: string | null;
  owner: boolean;
  permissions: string;
}

export interface DiscordRole {
  id: string;
  name: string;
  color: number;
  position: number;
  managed: boolean;
}
