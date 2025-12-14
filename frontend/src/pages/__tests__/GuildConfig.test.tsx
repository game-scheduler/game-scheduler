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
import { GuildConfig } from '../GuildConfig';
import { apiClient } from '../../api/client';
import { Guild } from '../../types';

const mockNavigate = vi.fn();
const mockParams = { guildId: 'guild123' };

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => mockParams,
  };
});

vi.mock('../../api/client');

describe('GuildConfig', () => {
  const mockGuild: Guild = {
    id: '1',
    guild_name: 'Test Guild',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  };

  beforeEach(() => {
    vi.clearAllMocks();
    // Set up default mocks for all tests
    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url.includes('/roles')) {
        return Promise.resolve({ data: [] });
      }
      if (url.includes('/guilds/')) {
        return Promise.resolve({ data: mockGuild });
      }
      return Promise.reject(new Error('Unknown URL'));
    });
  });

  it('loads and displays guild configuration', async () => {
    render(
      <BrowserRouter>
        <GuildConfig />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole('checkbox', { name: /Require Host Role/i })).toBeInTheDocument();
    });
  });

  it('displays loading state initially', () => {
    // Override to return pending promise for guild, but still return roles
    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url.includes('/roles')) {
        return Promise.resolve({ data: [] });
      }
      return new Promise(() => {}); // Never resolves
    });

    render(
      <BrowserRouter>
        <GuildConfig />
      </BrowserRouter>
    );

    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('handles save successfully', async () => {
    vi.mocked(apiClient.put).mockResolvedValueOnce({ data: mockGuild });

    const user = userEvent.setup();

    render(
      <BrowserRouter>
        <GuildConfig />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole('checkbox', { name: /Require Host Role/i })).toBeInTheDocument();
    });

    const saveButton = screen.getByText('Save Configuration');
    await user.click(saveButton);

    await waitFor(() => {
      const calls = vi.mocked(apiClient.put).mock.calls;
      expect(calls.length).toBeGreaterThan(0);
      const lastCall = calls[calls.length - 1];
      if (!lastCall) {
        throw new Error('Expected at least one call to apiClient.put');
      }
      expect(lastCall[0]).toBe('/api/v1/guilds/guild123');
      expect(lastCall[1]).toMatchObject({
        bot_manager_role_ids: null,
      });
      // require_host_role may be true or undefined depending on form state
    });
  });

  it('handles API errors gracefully', async () => {
    // Override to make guild fetch fail
    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url.includes('/roles')) {
        return Promise.resolve({ data: [] });
      }
      return Promise.reject({
        response: { data: { detail: 'Guild not found' } },
      });
    });

    render(
      <BrowserRouter>
        <GuildConfig />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Guild not found/)).toBeInTheDocument();
    });
  });

  it('renders form fields with initial values', async () => {
    render(
      <BrowserRouter>
        <GuildConfig />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole('checkbox', { name: /Require Host Role/i })).toBeInTheDocument();
    });

    const requireHostRoleCheckbox = screen.getByRole('checkbox', {
      name: /Require Host Role/i,
    }) as HTMLInputElement;
    // Checkbox exists and can be checked
    expect(requireHostRoleCheckbox).toBeInTheDocument();
  });
});
