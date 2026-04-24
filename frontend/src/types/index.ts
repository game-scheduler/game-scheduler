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

export enum SignupMethod {
  SELF_SIGNUP = 'SELF_SIGNUP',
  HOST_SELECTED = 'HOST_SELECTED',
  ROLE_BASED = 'ROLE_BASED',
}

export interface SignupMethodInfo {
  value: SignupMethod;
  displayName: string;
  description: string;
}

export const SIGNUP_METHOD_INFO: Record<SignupMethod, SignupMethodInfo> = {
  [SignupMethod.SELF_SIGNUP]: {
    value: SignupMethod.SELF_SIGNUP,
    displayName: 'Self Signup',
    description: 'Players can join the game by clicking the Discord button',
  },
  [SignupMethod.HOST_SELECTED]: {
    value: SignupMethod.HOST_SELECTED,
    displayName: 'Host Selected',
    description: 'Only the host can add players (Discord button disabled)',
  },
  [SignupMethod.ROLE_BASED]: {
    value: SignupMethod.ROLE_BASED,
    displayName: 'Role Based',
    description: 'Players are prioritised by Discord role when the game fills up',
  },
};

// NOTE: Changes to these values must be mirrored in the Python enum
// located at shared/models/participant.py
export enum ParticipantType {
  HOST_ADDED = 8000,
  ROLE_MATCHED = 16000,
  SELF_ADDED = 24000,
}

export interface User {
  discordId: string;
  createdAt: string;
  updatedAt: string;
}

export interface Guild {
  id: string;
  guild_name: string;
  created_at: string;
  updated_at: string;
}

export interface GuildConfigData extends Guild {
  bot_manager_role_ids: string[] | null;
}

export interface Channel {
  id: string; // Database UUID (use for navigation and API calls)
  guild_id: string;
  channel_id: string; // Discord snowflake (internal only)
  channel_name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface GameSession {
  id: string;
  title: string;
  description: string;
  signup_instructions: string | null;
  scheduled_at: string;
  where: string | null;
  max_players: number | null;
  guild_id: string;
  guild_name: string | null;
  channel_id: string;
  channel_name: string | null;
  message_id: string | null;
  host: Participant;
  reminder_minutes: number[] | null;
  notify_role_ids: string[] | null;
  expected_duration_minutes: number | null;
  signup_method: string;
  status: 'SCHEDULED' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED' | 'ARCHIVED';
  participant_count: number;
  participants?: Participant[];
  created_at: string;
  updated_at: string;
  has_thumbnail?: boolean;
  has_image?: boolean;
  thumbnail_id?: string | null;
  banner_image_id?: string | null;
  can_manage?: boolean;
  rewards?: string | null;
  remind_host_rewards?: boolean;
  archive_channel_id?: string | null;
  where_display?: string | null;
}

export interface Participant {
  id: string;
  game_session_id: string;
  user_id: string | null;
  discord_id: string | null;
  display_name: string | null;
  avatar_url?: string | null;
  joined_at: string;
  position_type: number;
  position: number;
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
  can_be_maintainer?: boolean;
  is_maintainer?: boolean;
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

export interface GameTemplate {
  id: string;
  guild_id: string;
  name: string;
  description: string | null;
  order: number;
  is_default: boolean;
  channel_id: string;
  channel_name: string;
  archive_channel_id: string | null;
  remind_host_rewards?: boolean;
  archive_channel_name: string | null;
  archive_delay_seconds: number | null;
  notify_role_ids: string[] | null;
  allowed_player_role_ids: string[] | null;
  allowed_host_role_ids: string[] | null;
  signup_priority_role_ids?: string[] | null;
  max_players: number | null;
  expected_duration_minutes: number | null;
  reminder_minutes: number[] | null;
  where: string | null;
  signup_instructions: string | null;
  allowed_signup_methods: string[] | null;
  default_signup_method: string | null;
  created_at: string;
  updated_at: string;
}

export type TemplateListItem = Omit<
  GameTemplate,
  'guild_id' | 'order' | 'created_at' | 'updated_at'
>;

export interface TemplateCreateRequest {
  guild_id: string;
  name: string;
  description?: string | null;
  order?: number;
  is_default?: boolean;
  channel_id: string;
  archive_channel_id?: string | null;
  archive_delay_seconds?: number | null;
  notify_role_ids?: string[] | null;
  allowed_player_role_ids?: string[] | null;
  allowed_host_role_ids?: string[] | null;
  signup_priority_role_ids?: string[] | null;
  max_players?: number | null;
  expected_duration_minutes?: number | null;
  reminder_minutes?: number[] | null;
  where?: string | null;
  signup_instructions?: string | null;
  allowed_signup_methods?: string[] | null;
  default_signup_method?: string | null;
}

export type TemplateUpdateRequest = Partial<
  Omit<GameTemplate, 'id' | 'guild_id' | 'channel_name' | 'created_at' | 'updated_at'>
>;
