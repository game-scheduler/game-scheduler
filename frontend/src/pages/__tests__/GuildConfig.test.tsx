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
import { GuildConfig } from '../GuildConfig';
import { apiClient } from '../../api/client';
import { Guild } from '../../types';

const mockNavigate = vi.fn();
const mockParams = { guildId: 'guild123' };

vi.mock('react-router', async () => {
  const actual = await vi.importActual('react-router');
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
      expect(screen.getByText('Server Configuration')).toBeInTheDocument();
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
      expect(screen.getByText('Save Configuration')).toBeInTheDocument();
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
});
