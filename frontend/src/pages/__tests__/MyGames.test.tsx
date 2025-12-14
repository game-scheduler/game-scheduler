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

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { MyGames } from '../MyGames';
import { AuthContext } from '../../contexts/AuthContext';
import { CurrentUser, Guild, GameListResponse } from '../../types';
import { apiClient } from '../../api/client';

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock('../../api/client');

vi.mock('../../utils/permissions', () => ({
  canUserCreateGames: vi.fn().mockResolvedValue(true),
}));

describe('MyGames - Server Selection Logic', () => {
  const mockUser: CurrentUser = {
    id: 'id-123',
    user_uuid: 'user-123',
    username: 'testuser',
    discordId: 'discord-123',
    avatar: null,
  };

  const mockGuild: Guild = {
    id: '1',
    guild_name: 'Test Server 1',
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
  };

  const mockGamesResponse: GameListResponse = {
    games: [],
    total: 0,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url === '/api/v1/games') {
        return Promise.resolve({ data: mockGamesResponse });
      }
      return Promise.resolve({ data: { guilds: [] } });
    });
  });

  const renderWithAuth = (user: CurrentUser | null = mockUser) => {
    const mockAuthValue = {
      user,
      login: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
      loading: false,
    };

    return render(
      <BrowserRouter>
        <AuthContext.Provider value={mockAuthValue}>
          <MyGames />
        </AuthContext.Provider>
      </BrowserRouter>
    );
  };

  it('navigates directly to create form when user has one server', async () => {
    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url === '/api/v1/games') {
        return Promise.resolve({ data: mockGamesResponse });
      }
      if (url === '/api/v1/guilds') {
        return Promise.resolve({ data: { guilds: [mockGuild] } });
      }
      return Promise.resolve({ data: { guilds: [] } });
    });

    const user = userEvent.setup();
    renderWithAuth();

    await waitFor(() => {
      expect(screen.getByText('Create New Game')).toBeInTheDocument();
    });

    await user.click(screen.getByText('Create New Game'));

    expect(mockNavigate).toHaveBeenCalledWith('/guilds/1/games/new');
  });

  it('shows server selection dialog when user has multiple servers', async () => {
    const mockGuilds: Guild[] = [
      mockGuild,
      {
        id: '2',
        guild_name: 'Test Server 2',
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
      },
    ];

    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url === '/api/v1/games') {
        return Promise.resolve({ data: mockGamesResponse });
      }
      if (url === '/api/v1/guilds') {
        return Promise.resolve({ data: { guilds: mockGuilds } });
      }
      return Promise.resolve({ data: { guilds: [] } });
    });

    const user = userEvent.setup();
    renderWithAuth();

    const createButton = await screen.findByText('Create New Game', {}, { timeout: 3000 });
    expect(createButton).toBeInTheDocument();

    await user.click(createButton);

    const dialogTitle = await screen.findByText('Select Server', {}, { timeout: 3000 });
    expect(dialogTitle).toBeInTheDocument();
  });

  it('hides create button when user has no servers', async () => {
    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url === '/api/v1/games') {
        return Promise.resolve({ data: mockGamesResponse });
      }
      if (url === '/api/v1/guilds') {
        return Promise.resolve({ data: { guilds: [] } });
      }
      return Promise.resolve({ data: { guilds: [] } });
    });

    renderWithAuth();

    // Wait for loading to complete
    await screen.findByText('My Games');

    // Button should not be in the document when there are no guilds
    const createButton = screen.queryByText('Create New Game');
    expect(createButton).not.toBeInTheDocument();
  });

  it('navigates when server is selected from dialog', async () => {
    const mockGuilds: Guild[] = [
      mockGuild,
      {
        id: '2',
        guild_name: 'Test Server 2',
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
      },
    ];

    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url === '/api/v1/games') {
        return Promise.resolve({ data: mockGamesResponse });
      }
      if (url === '/api/v1/guilds') {
        return Promise.resolve({ data: { guilds: mockGuilds } });
      }
      return Promise.resolve({ data: { guilds: [] } });
    });

    const user = userEvent.setup();
    renderWithAuth();

    const createButton = await screen.findByText('Create New Game', {}, { timeout: 3000 });
    expect(createButton).toBeInTheDocument();

    await user.click(createButton);

    const dialogTitle = await screen.findByText('Select Server', {}, { timeout: 3000 });
    expect(dialogTitle).toBeInTheDocument();

    const serverOption = await screen.findByText('Test Server 1', {}, { timeout: 3000 });
    await user.click(serverOption);

    expect(mockNavigate).toHaveBeenCalledWith('/guilds/1/games/new');
  });

  it('fetches guilds on component mount', async () => {
    renderWithAuth();

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/guilds');
    });
  });
});
