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


import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { GuildListPage } from '../GuildListPage';
import { AuthContext } from '../../contexts/AuthContext';
import { CurrentUser } from '../../types';

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('GuildListPage', () => {
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

  it('renders guild list when user has guilds', () => {
    renderWithAuth();
    expect(screen.getByText('My Guilds')).toBeInTheDocument();
    expect(screen.getByText('Test Guild 1')).toBeInTheDocument();
    expect(screen.getByText('Test Guild 2')).toBeInTheDocument();
  });

  it('filters guilds without manage permissions', () => {
    renderWithAuth();
    expect(screen.getByText('Test Guild 1')).toBeInTheDocument();
    expect(screen.getByText('Test Guild 2')).toBeInTheDocument();
    expect(screen.queryByText('Test Guild 3 (No Permissions)')).not.toBeInTheDocument();
  });

  it('displays owner badge for owned guilds', () => {
    renderWithAuth();
    expect(screen.getByText('Owner')).toBeInTheDocument();
  });

  it('renders empty state when user has no guilds', () => {
    const userWithNoGuilds: CurrentUser = {
      ...mockUser,
      guilds: [],
    };
    renderWithAuth(userWithNoGuilds);
    expect(screen.getByText(/You don't have management permissions/)).toBeInTheDocument();
  });

  it('renders empty state when user has guilds but no manage permissions', () => {
    const userWithNoManagePermissions: CurrentUser = {
      ...mockUser,
      guilds: [
        {
          id: 'guild1',
          name: 'No Permission Guild',
          icon: null,
          owner: false,
          permissions: '0',
        },
      ],
    };
    renderWithAuth(userWithNoManagePermissions);
    expect(screen.getByText(/You don't have management permissions/)).toBeInTheDocument();
  });

  it('displays guild with icon', () => {
    renderWithAuth();
    const icon = screen.getByAltText('Test Guild 1');
    expect(icon).toBeInTheDocument();
    expect(icon).toHaveAttribute('src', 'https://cdn.discordapp.com/icons/guild1/icon1.png');
  });

  it('displays guild without icon with first letter avatar', () => {
    renderWithAuth();
    expect(screen.getByText('T')).toBeInTheDocument();
  });
});
