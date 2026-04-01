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
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { GameCard } from '../GameCard';
import { GameSession, ParticipantType } from '../../types';
import { AuthContext } from '../../contexts/AuthContext';

vi.mock('../../api/client', () => ({
  apiClient: {
    post: vi.fn(),
    get: vi.fn(),
  },
}));

const mockAuthContext = {
  user: null,
  login: vi.fn(),
  logout: vi.fn(),
  loading: false,
  refreshUser: vi.fn(),
};

const baseGame: GameSession = {
  id: 'game-1',
  title: 'Test Game',
  description: 'A test game',
  signup_instructions: null,
  scheduled_at: '2099-12-25T19:00:00Z',
  where: '<#406497579061215235>',
  max_players: 4,
  guild_id: 'guild-1',
  guild_name: 'Test Guild',
  channel_id: 'channel-1',
  channel_name: 'general',
  message_id: null,
  host: {
    id: 'participant-1',
    game_session_id: 'game-1',
    user_id: 'user-1',
    discord_id: '123456789',
    display_name: 'TestHost',
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
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const renderWithAuth = (ui: React.ReactElement) => {
  return render(
    <AuthContext.Provider value={mockAuthContext}>
      <MemoryRouter>{ui}</MemoryRouter>
    </AuthContext.Provider>
  );
};

describe('GameCard - where_display', () => {
  it('shows where_display when present instead of raw where token', () => {
    const game: GameSession = {
      ...baseGame,
      where: '<#406497579061215235>',
      where_display: '#🍻tavern-generalchat',
    };

    renderWithAuth(<GameCard game={game} />);

    expect(screen.getByText(/🍻tavern-generalchat/)).toBeInTheDocument();
    expect(screen.queryByText(/<#406497579061215235>/)).not.toBeInTheDocument();
  });

  it('falls back to where when where_display is null', () => {
    const game: GameSession = {
      ...baseGame,
      where: '#regular-channel',
      where_display: null,
    };

    renderWithAuth(<GameCard game={game} />);

    expect(screen.getByText(/#regular-channel/)).toBeInTheDocument();
  });

  it('falls back to where when where_display is undefined', () => {
    const game: GameSession = {
      ...baseGame,
      where: '#regular-channel',
    };

    renderWithAuth(<GameCard game={game} />);

    expect(screen.getByText(/#regular-channel/)).toBeInTheDocument();
  });
});
