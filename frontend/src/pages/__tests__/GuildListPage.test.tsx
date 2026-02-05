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

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
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

  it('displays success message with new guilds and channels on sync', async () => {
    renderWithAuth();
    await waitFor(() => {
      expect(screen.getByText('My Servers')).toBeInTheDocument();
    });

    vi.mocked(apiClient.post).mockResolvedValue({
      data: { new_guilds: 1, new_channels: 2, updated_channels: 0 },
    });

    const syncButton = screen.getByRole('button', { name: /Sync Servers and Channels/i });
    await userEvent.click(syncButton);

    await waitFor(() => {
      expect(screen.getByText(/Synced 1 new server, 2 new channels/)).toBeInTheDocument();
    });
  });

  it('displays success message with updated channels on sync', async () => {
    renderWithAuth();
    await waitFor(() => {
      expect(screen.getByText('My Servers')).toBeInTheDocument();
    });

    vi.mocked(apiClient.post).mockResolvedValue({
      data: { new_guilds: 0, new_channels: 1, updated_channels: 3 },
    });

    const syncButton = screen.getByRole('button', { name: /Sync Servers and Channels/i });
    await userEvent.click(syncButton);

    await waitFor(() => {
      expect(screen.getByText(/Synced 1 new channel, 3 updated channels/)).toBeInTheDocument();
    });
  });

  it('displays success message when all synced', async () => {
    renderWithAuth();
    await waitFor(() => {
      expect(screen.getByText('My Servers')).toBeInTheDocument();
    });

    vi.mocked(apiClient.post).mockResolvedValue({
      data: { new_guilds: 0, new_channels: 0, updated_channels: 0 },
    });

    const syncButton = screen.getByRole('button', { name: /Sync Servers and Channels/i });
    await userEvent.click(syncButton);

    await waitFor(() => {
      expect(screen.getByText(/All servers and channels are already synced/)).toBeInTheDocument();
    });
  });

  it('handles proper pluralization in sync messages', async () => {
    renderWithAuth();
    await waitFor(() => {
      expect(screen.getByText('My Servers')).toBeInTheDocument();
    });

    vi.mocked(apiClient.post).mockResolvedValue({
      data: { new_guilds: 2, new_channels: 1, updated_channels: 1 },
    });

    const syncButton = screen.getByRole('button', { name: /Sync Servers and Channels/i });
    await userEvent.click(syncButton);

    await waitFor(() => {
      expect(
        screen.getByText(/Synced 2 new servers, 1 new channel, 1 updated channel/)
      ).toBeInTheDocument();
    });
  });
});
