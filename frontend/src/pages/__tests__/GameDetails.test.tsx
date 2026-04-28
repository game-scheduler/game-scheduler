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
import { render, screen, waitFor, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
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

describe('GameDetails - Edit Game button visibility', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows Edit Game button when can_manage is true', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { ...baseGame, can_manage: true },
    });

    renderGameDetails();

    await waitFor(() => {
      expect(screen.getByText('Edit Game')).toBeInTheDocument();
    });
    expect(screen.getByText('Clone Game')).toBeInTheDocument();
  });

  it('hides Edit Game button when can_manage is false', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { ...baseGame, can_manage: false },
    });

    renderGameDetails();

    await waitFor(() => {
      expect(screen.getByText('Test Game')).toBeInTheDocument();
    });
    expect(screen.queryByText('Edit Game')).not.toBeInTheDocument();
    expect(screen.queryByText('Clone Game')).not.toBeInTheDocument();
  });
});

describe('GameDetails - Rewards spoiler', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('hides rewards section when game has no rewards', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: { ...baseGame, rewards: null } });

    renderGameDetails();

    await waitFor(() => {
      expect(screen.getByText('Test Game')).toBeInTheDocument();
    });
    expect(screen.queryByText('🏆 Rewards')).not.toBeInTheDocument();
  });

  it('shows blurred rewards with click-to-reveal when rewards are set', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { ...baseGame, rewards: 'Gold and glory' },
    });

    renderGameDetails();

    await waitFor(() => {
      expect(screen.getByText('🏆 Rewards')).toBeInTheDocument();
    });
    expect(screen.getByText('Click to reveal rewards')).toBeInTheDocument();
  });

  it('reveals rewards text after click', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { ...baseGame, rewards: 'Gold and glory' },
    });

    const user = userEvent.setup();
    renderGameDetails();

    await waitFor(() => {
      expect(screen.getByText('Click to reveal rewards')).toBeInTheDocument();
    });

    await user.click(screen.getByText('Click to reveal rewards'));

    expect(screen.getByText('Gold and glory')).toBeInTheDocument();
    expect(screen.queryByText('Click to reveal rewards')).not.toBeInTheDocument();
  });
});

describe('GameDetails - Cancel Game button visibility', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows Cancel Game button for host when game is SCHEDULED', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        ...baseGame,
        can_manage: true,
        host: { ...baseGame.host, user_id: mockUser.user_uuid },
        status: 'SCHEDULED',
      },
    });

    renderGameDetails();

    await waitFor(() => {
      expect(screen.getByText('Cancel Game')).toBeInTheDocument();
    });
  });

  it('shows Cancel Game button for host when game is IN_PROGRESS', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        ...baseGame,
        can_manage: true,
        host: { ...baseGame.host, user_id: mockUser.user_uuid },
        status: 'IN_PROGRESS',
      },
    });

    renderGameDetails();

    await waitFor(() => {
      expect(screen.getByText('Cancel Game')).toBeInTheDocument();
    });
  });

  it('hides Cancel Game button for host when game is COMPLETED', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        ...baseGame,
        can_manage: true,
        host: { ...baseGame.host, user_id: mockUser.user_uuid },
        status: 'COMPLETED',
      },
    });

    renderGameDetails();

    await waitFor(() => {
      expect(screen.getByText('Test Game')).toBeInTheDocument();
    });
    expect(screen.queryByText('Cancel Game')).not.toBeInTheDocument();
  });

  it('shows Cancel Game button for manager (non-host) regardless of status', async () => {
    for (const status of ['SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'ARCHIVED']) {
      vi.clearAllMocks();
      cleanup();
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { ...baseGame, can_manage: true, status },
      });

      renderGameDetails();

      await waitFor(() => {
        expect(screen.getByText('Cancel Game')).toBeInTheDocument();
      });
    }
  });

  it('hides Cancel Game button when can_manage is false', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { ...baseGame, can_manage: false, status: 'SCHEDULED' },
    });

    renderGameDetails();

    await waitFor(() => {
      expect(screen.getByText('Test Game')).toBeInTheDocument();
    });
    expect(screen.queryByText('Cancel Game')).not.toBeInTheDocument();
  });
});
