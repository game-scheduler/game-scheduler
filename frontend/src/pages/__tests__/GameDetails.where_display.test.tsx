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

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router';
import { GameDetails } from '../GameDetails';
import { AuthContext } from '../../contexts/AuthContext';
import { apiClient } from '../../api/client';
import { GameSession, ParticipantType, CurrentUser } from '../../types';

vi.mock('../../api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock('react-router', async () => {
  const actual = await vi.importActual('react-router');
  return { ...actual, useNavigate: () => vi.fn() };
});

const mockUser: CurrentUser = {
  id: 'user-db-id',
  user_uuid: 'user-uuid-123',
  username: 'testuser',
};

const baseGame: GameSession = {
  id: 'game-1',
  title: 'Test Game',
  description: 'A test game',
  signup_instructions: null,
  scheduled_at: '2099-12-25T19:00:00Z',
  where: null,
  max_players: 4,
  guild_id: 'guild-1',
  guild_name: 'Test Guild',
  channel_id: 'channel-1',
  channel_name: 'general',
  message_id: null,
  host: {
    id: 'host-participant-id',
    game_session_id: 'game-1',
    user_id: 'other-user-uuid',
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
  status: 'SCHEDULED',
  signup_method: 'SELF_SIGNUP',
  participant_count: 1,
  participants: [],
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const renderGameDetails = (user: CurrentUser | null = mockUser) => {
  const authValue = {
    user,
    login: vi.fn(),
    logout: vi.fn(),
    refreshUser: vi.fn(),
    loading: false,
  };
  return render(
    <AuthContext.Provider value={authValue}>
      <MemoryRouter initialEntries={['/games/game-1']}>
        <Routes>
          <Route path="/games/:gameId" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>
  );
};

describe('GameDetails - where_display', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows where_display when present instead of raw where token', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        ...baseGame,
        where: '<#406497579061215235>',
        where_display: '#🍻tavern-generalchat',
      },
    });

    renderGameDetails();

    await waitFor(() => {
      expect(screen.getByText(/🍻tavern-generalchat/)).toBeInTheDocument();
    });
    expect(screen.queryByText(/<#406497579061215235>/)).not.toBeInTheDocument();
  });

  it('falls back to where when where_display is null', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        ...baseGame,
        where: '#regular-channel',
        where_display: null,
      },
    });

    renderGameDetails();

    await waitFor(() => {
      expect(screen.getByText(/#regular-channel/)).toBeInTheDocument();
    });
  });
});
