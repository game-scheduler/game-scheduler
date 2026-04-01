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

import { describe, it, expect, vi } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { GameForm } from '../GameForm';
import { Channel, CurrentUser, GameSession, ParticipantType } from '../../types';
import { AuthContext, type AuthContextType } from '../../contexts/AuthContext';

const mockAuthContextValue: AuthContextType = {
  user: {
    id: 'test-user-id',
    user_uuid: 'test-user-uuid',
    discordId: 'user123',
    username: 'testuser',
    guilds: [],
  } as CurrentUser,
  loading: false,
  login: vi.fn(),
  logout: vi.fn(),
  refreshUser: vi.fn(),
};

const mockChannels: Channel[] = [
  {
    id: 'channel-1',
    guild_id: 'guild123',
    channel_id: 'discord-channel-1',
    channel_name: 'general',
    is_active: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

const baseInitialData: Partial<GameSession> = {
  id: 'game-1',
  title: 'Test Game',
  description: 'Desc',
  signup_instructions: null,
  scheduled_at: '2099-12-25T19:00:00Z',
  where: '<#406497579061215235>',
  max_players: 4,
  guild_id: 'guild123',
  guild_name: 'Test Guild',
  channel_id: 'channel-1',
  channel_name: 'general',
  message_id: null,
  host: {
    id: 'host-participant-id',
    game_session_id: 'game-1',
    user_id: 'user-uuid',
    discord_id: 'host-discord-id',
    display_name: 'Host User',
    avatar_url: null,
    joined_at: '2026-01-01T00:00:00Z',
    position_type: ParticipantType.SELF_ADDED,
    position: 0,
  },
  reminder_minutes: null,
  notify_role_ids: null,
  expected_duration_minutes: null,
  status: 'SCHEDULED' as const,
  signup_method: 'SELF_SIGNUP',
  participant_count: 1,
  participants: [],
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const renderGameForm = (props = {}) => {
  const defaultProps = {
    mode: 'edit' as const,
    guildId: 'guild123',
    channels: mockChannels,
    onSubmit: vi.fn(),
    onCancel: vi.fn(),
    ...props,
  };

  return render(
    <AuthContext.Provider value={mockAuthContextValue}>
      <GameForm {...defaultProps} />
    </AuthContext.Provider>
  );
};

describe('GameForm - where_display pre-populate', () => {
  it('pre-populates Location with where_display when available', () => {
    const initialData: Partial<GameSession> = {
      ...baseInitialData,
      where: '<#406497579061215235>',
      where_display: '#🍻tavern-generalchat',
    };

    renderGameForm({ initialData });

    const locationField = screen.getByRole('textbox', { name: /Location/i });
    expect(locationField).toHaveValue('#🍻tavern-generalchat');
  });

  it('pre-populates Location with where when where_display is absent', () => {
    const initialData: Partial<GameSession> = {
      ...baseInitialData,
      where: '#regular-channel',
    };

    renderGameForm({ initialData });

    const locationField = screen.getByRole('textbox', { name: /Location/i });
    expect(locationField).toHaveValue('#regular-channel');
  });

  it('updates Location when initialData changes to include where_display (useEffect path)', () => {
    const initialData: Partial<GameSession> = {
      ...baseInitialData,
      where: '<#406497579061215235>',
      where_display: undefined,
    };

    const { rerender } = renderGameForm({ initialData });

    const locationField = screen.getByRole('textbox', { name: /Location/i });
    expect(locationField).toHaveValue('<#406497579061215235>');

    act(() => {
      rerender(
        <AuthContext.Provider value={mockAuthContextValue}>
          <GameForm
            mode="edit"
            guildId="guild123"
            channels={mockChannels}
            onSubmit={vi.fn()}
            onCancel={vi.fn()}
            initialData={{
              ...baseInitialData,
              where: '<#406497579061215235>',
              where_display: '#🍻tavern-generalchat',
            }}
          />
        </AuthContext.Provider>
      );
    });

    expect(locationField).toHaveValue('#🍻tavern-generalchat');
  });
});

describe('GameForm - channel suggestion click updates Location field', () => {
  it('updates Location field value when channel suggestion chip is clicked', async () => {
    const user = userEvent.setup();
    const onChannelValidationErrorClick = vi.fn();

    const channelValidationErrors = [
      {
        type: 'channel',
        input: '#old-channel',
        reason: 'Channel not found',
        suggestions: [{ id: 'ch-new', name: '🍻tavern-generalchat' }],
      },
    ];

    renderGameForm({
      initialData: { ...baseInitialData, where: '#old-channel' },
      channelValidationErrors,
      onChannelValidationErrorClick,
    });

    const chip = screen.getByText('#🍻tavern-generalchat');
    await user.click(chip);

    const locationField = screen.getByRole('textbox', { name: /Location/i });
    expect(locationField).toHaveValue('#🍻tavern-generalchat');
  });

  it('calls onChannelValidationErrorClick callback after suggestion click', async () => {
    const user = userEvent.setup();
    const onChannelValidationErrorClick = vi.fn();

    const channelValidationErrors = [
      {
        type: 'channel',
        input: '#old-channel',
        reason: 'Channel not found',
        suggestions: [{ id: 'ch-new', name: 'new-channel' }],
      },
    ];

    renderGameForm({
      initialData: { ...baseInitialData, where: '#old-channel' },
      channelValidationErrors,
      onChannelValidationErrorClick,
    });

    const chip = screen.getByText('#new-channel');
    await user.click(chip);

    expect(onChannelValidationErrorClick).toHaveBeenCalledWith('#old-channel', '#new-channel');
  });
});
