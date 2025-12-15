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
import { BrowserRouter } from 'react-router';
import { GuildListPage } from '../GuildListPage';
import { AuthContext } from '../../contexts/AuthContext';
import { CurrentUser, Guild } from '../../types';
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

describe('GuildListPage', () => {
  const mockGuilds: Guild[] = [
    {
      id: '1',
      guild_name: 'Test Guild 1',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
    {
      id: '2',
      guild_name: 'Test Guild 2',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
  ];

  const mockUser: CurrentUser = {
    id: '123',
    user_uuid: 'uuid-123',
    username: 'testuser',
    discordId: '123',
    guilds: [
      {
        id: 'guild1',
        name: 'Test Guild 1',
        icon: 'icon1',
        owner: true,
        permissions: '0',
      },
      {
        id: 'guild2',
        name: 'Test Guild 2',
        icon: null,
        owner: false,
        permissions: '32',
      },
      {
        id: 'guild3',
        name: 'Test Guild 3 (No Permissions)',
        icon: null,
        owner: false,
        permissions: '0',
      },
    ],
  };

  const mockAuthContextValue = {
    user: mockUser,
    loading: false,
    login: vi.fn(),
    logout: vi.fn(),
    refreshUser: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiClient.get).mockResolvedValue({ data: { guilds: mockGuilds } });
  });

  const renderWithAuth = (user: CurrentUser | null = mockUser, loading = false) => {
    return render(
      <BrowserRouter>
        <AuthContext.Provider
          value={{
            ...mockAuthContextValue,
            user,
            loading,
          }}
        >
          <GuildListPage />
        </AuthContext.Provider>
      </BrowserRouter>
    );
  };

  it('renders loading state', () => {
    renderWithAuth(mockUser, true);
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('renders guild list when user has guilds', async () => {
    renderWithAuth();
    await waitFor(() => {
      expect(screen.getByText('My Servers')).toBeInTheDocument();
    });
    expect(screen.getByText('Test Guild 1')).toBeInTheDocument();
    expect(screen.getByText('Test Guild 2')).toBeInTheDocument();
  });

  it('renders empty state when API returns no guilds', async () => {
    const userWithNoGuilds: CurrentUser = {
      ...mockUser,
      guilds: [],
    };
    vi.mocked(apiClient.get).mockResolvedValue({ data: { guilds: [] } });
    renderWithAuth(userWithNoGuilds);
    await waitFor(() => {
      expect(screen.getByText(/No servers with bot configurations found/)).toBeInTheDocument();
    });
  });

  it('displays guild with first letter avatar', async () => {
    renderWithAuth();
    await waitFor(() => {
      expect(screen.getByText('Test Guild 1')).toBeInTheDocument();
    });
    const avatars = screen.getAllByText('T');
    expect(avatars.length).toBeGreaterThan(0);
  });
});
