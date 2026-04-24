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
import { MemoryRouter, Route, Routes } from 'react-router';
import { BrowseGames } from '../BrowseGames';
import { apiClient } from '../../api/client';
import { GameSession, ParticipantType } from '../../types';
import { AuthContext } from '../../contexts/AuthContext';

vi.mock('../../api/client', () => ({
  apiClient: {
    get: vi.fn(),
  },
}));

vi.mock('../../hooks/useGameUpdates', () => ({
  useGameUpdates: vi.fn(),
}));

const mockAuthContext = {
  user: null,
  login: vi.fn(),
  logout: vi.fn(),
  loading: false,
  refreshUser: vi.fn(),
};

const mockGame: GameSession = {
  id: 'game-1',
  title: 'D&D Adventure',
  description: 'Epic quest awaits',
  signup_instructions: null,
  scheduled_at: '2026-12-25T19:00:00Z',
  where: 'Discord',
  max_players: 6,
  guild_id: 'guild-1',
  guild_name: 'Test Guild',
  channel_id: 'channel-1',
  channel_name: 'game-chat',
  message_id: null,
  host: {
    id: 'host-1',
    game_session_id: 'game-1',
    user_id: 'user-1',
    discord_id: '123',
    display_name: 'GameMaster',
    avatar_url: null,
    joined_at: '2026-01-01T00:00:00Z',
    position_type: ParticipantType.SELF_ADDED,
    position: 0,
  },
  reminder_minutes: null,
  notify_role_ids: null,
  expected_duration_minutes: 180,
  status: 'SCHEDULED',
  signup_method: 'SELF_SIGNUP',
  participant_count: 3,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

describe('BrowseGames - SSE Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches and updates game when SSE event received', async () => {
    const updatedGame = { ...mockGame, participant_count: 4 };
    let sseCallback: ((gameId: string) => void) | undefined;

    vi.mocked(apiClient.get)
      .mockResolvedValueOnce({
        data: { games: [mockGame], total: 1 },
      })
      .mockResolvedValueOnce({
        data: updatedGame,
      });

    const { useGameUpdates } = await import('../../hooks/useGameUpdates');
    vi.mocked(useGameUpdates).mockImplementation((_guildId, callback) => {
      sseCallback = callback;
    });

    render(
      <AuthContext.Provider value={mockAuthContext}>
        <MemoryRouter initialEntries={['/browse/guild-1']}>
          <Routes>
            <Route path="/browse/:guildId" element={<BrowseGames />} />
          </Routes>
        </MemoryRouter>
      </AuthContext.Provider>
    );

    await waitFor(() => {
      expect(screen.getByText('D&D Adventure')).toBeInTheDocument();
    });

    expect(apiClient.get).toHaveBeenCalledWith('/api/v1/games', {
      params: expect.objectContaining({ guild_id: 'guild-1', status: ['SCHEDULED'] }),
    });

    sseCallback!('game-1');

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/games/game-1');
    });
  });

  it('handles SSE update for game not in current list gracefully', async () => {
    let sseCallback: ((gameId: string) => void) | undefined;

    vi.mocked(apiClient.get)
      .mockResolvedValueOnce({
        data: { games: [mockGame], total: 1 },
      })
      .mockResolvedValueOnce({
        data: { ...mockGame, id: 'game-2' },
      });

    const { useGameUpdates } = await import('../../hooks/useGameUpdates');
    vi.mocked(useGameUpdates).mockImplementation((_guildId, callback) => {
      sseCallback = callback;
    });

    render(
      <AuthContext.Provider value={mockAuthContext}>
        <MemoryRouter initialEntries={['/browse/guild-1']}>
          <Routes>
            <Route path="/browse/:guildId" element={<BrowseGames />} />
          </Routes>
        </MemoryRouter>
      </AuthContext.Provider>
    );

    await waitFor(() => {
      expect(screen.getByText('D&D Adventure')).toBeInTheDocument();
    });

    sseCallback!('game-2');

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/games/game-2');
    });
  });
});

describe('BrowseGames - Status Filter', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('passes status as array for specific status selection', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({
      data: { games: [mockGame], total: 1 },
    });

    const { useGameUpdates } = await import('../../hooks/useGameUpdates');
    vi.mocked(useGameUpdates).mockImplementation(() => {});

    render(
      <AuthContext.Provider value={mockAuthContext}>
        <MemoryRouter initialEntries={['/browse/guild-1']}>
          <Routes>
            <Route path="/browse/:guildId" element={<BrowseGames />} />
          </Routes>
        </MemoryRouter>
      </AuthContext.Provider>
    );

    await waitFor(() => {
      expect(screen.getByText('D&D Adventure')).toBeInTheDocument();
    });

    expect(apiClient.get).toHaveBeenCalledWith('/api/v1/games', {
      params: expect.objectContaining({ status: ['SCHEDULED'] }),
    });
  });

  it('passes full non-archived status list when ALL is selected', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({
      data: { games: [mockGame], total: 1 },
    });

    const { useGameUpdates } = await import('../../hooks/useGameUpdates');
    vi.mocked(useGameUpdates).mockImplementation(() => {});

    render(
      <AuthContext.Provider value={mockAuthContext}>
        <MemoryRouter initialEntries={['/browse/guild-1']}>
          <Routes>
            <Route path="/browse/:guildId" element={<BrowseGames />} />
          </Routes>
        </MemoryRouter>
      </AuthContext.Provider>
    );

    await waitFor(() => {
      expect(screen.getByText('D&D Adventure')).toBeInTheDocument();
    });

    vi.mocked(apiClient.get).mockResolvedValueOnce({
      data: { games: [mockGame], total: 1 },
    });

    const statusSelect = screen.getAllByRole('combobox')[1]!;
    await import('@testing-library/user-event').then(async ({ default: userEvent }) => {
      const user = userEvent.setup();
      await user.click(statusSelect);
    });
    const allOption = screen.getByRole('option', { name: 'All' });
    await import('@testing-library/user-event').then(async ({ default: userEvent }) => {
      const user = userEvent.setup();
      await user.click(allOption);
    });

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenLastCalledWith('/api/v1/games', {
        params: expect.objectContaining({
          status: ['SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED'],
        }),
      });
    });
  });
});

describe('BrowseGames - Channel Filter', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('channel dropdown options are sorted alphabetically', async () => {
    const gameWithAlpha = {
      ...mockGame,
      id: 'g1',
      channel_id: 'ch-a',
      channel_name: 'zebra-games',
    };
    const gameWithZebra = {
      ...mockGame,
      id: 'g2',
      channel_id: 'ch-b',
      channel_name: 'alpha-games',
    };
    const gameWithMiddle = {
      ...mockGame,
      id: 'g3',
      channel_id: 'ch-c',
      channel_name: 'middle-games',
    };

    vi.mocked(apiClient.get).mockResolvedValueOnce({
      data: { games: [gameWithAlpha, gameWithZebra, gameWithMiddle], total: 3 },
    });

    const { useGameUpdates } = await import('../../hooks/useGameUpdates');
    vi.mocked(useGameUpdates).mockImplementation(() => {});

    render(
      <AuthContext.Provider value={mockAuthContext}>
        <MemoryRouter initialEntries={['/browse/guild-1']}>
          <Routes>
            <Route path="/browse/:guildId" element={<BrowseGames />} />
          </Routes>
        </MemoryRouter>
      </AuthContext.Provider>
    );

    await waitFor(() => {
      expect(screen.getAllByText('D&D Adventure')).toHaveLength(3);
    });
    const channelSelect = screen.getAllByRole('combobox')[0]!;
    await import('@testing-library/user-event').then(async ({ default: userEvent }) => {
      const user = userEvent.setup();
      await user.click(channelSelect);
    });

    const options = screen.getAllByRole('option').map((el) => el.textContent);
    // Skip the first option ('All Channels'), check the rest are sorted
    const channelOptions = options.slice(1);
    expect(channelOptions).toEqual([...channelOptions].sort());
    expect(channelOptions).toEqual(['alpha-games', 'middle-games', 'zebra-games']);
  });

  it('derives channel list from loaded games without calling channels endpoint', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({
      data: { games: [mockGame], total: 1 },
    });

    const { useGameUpdates } = await import('../../hooks/useGameUpdates');
    vi.mocked(useGameUpdates).mockImplementation(() => {});

    render(
      <AuthContext.Provider value={mockAuthContext}>
        <MemoryRouter initialEntries={['/browse/guild-1']}>
          <Routes>
            <Route path="/browse/:guildId" element={<BrowseGames />} />
          </Routes>
        </MemoryRouter>
      </AuthContext.Provider>
    );

    await waitFor(() => {
      expect(screen.getByText('D&D Adventure')).toBeInTheDocument();
    });

    expect(apiClient.get).toHaveBeenCalledTimes(1);
    expect(apiClient.get).not.toHaveBeenCalledWith(
      expect.stringContaining('/channels'),
      expect.anything()
    );
  });
});
