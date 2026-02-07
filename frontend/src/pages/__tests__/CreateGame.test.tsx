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
import { StatusCodes } from 'http-status-codes';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router';
import { CreateGame } from '../CreateGame';
import { AuthContext } from '../../contexts/AuthContext';
import { CurrentUser, Guild, GameTemplate } from '../../types';
import { apiClient } from '../../api/client';

const mockNavigate = vi.fn();

vi.mock('react-router', async () => {
  const actual = await vi.importActual('react-router');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock('../../api/client');

vi.mock('../../utils/permissions', () => ({
  canUserCreateGames: vi.fn().mockResolvedValue(true),
  canUserManageBotSettings: vi.fn().mockResolvedValue(false),
}));

describe('CreateGame', () => {
  const mockUser: CurrentUser = {
    id: 'id-123',
    user_uuid: 'user-123',
    username: 'testuser',
    discordId: 'discord-123',
    avatar: null,
  };

  const mockGuild: Guild = {
    id: '1',
    guild_name: 'Test Server',
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
  };

  const mockTemplate: GameTemplate = {
    id: 'template-1',
    guild_id: '1',
    name: 'Default Game',
    description: 'Default game template',
    channel_id: 'channel-1',
    channel_name: 'general',
    max_players: 8,
    expected_duration_minutes: 120,
    reminder_minutes: [60, 15],
    where: null,
    signup_instructions: null,
    is_default: true,
    order: 1,
    notify_role_ids: null,
    allowed_player_role_ids: null,
    allowed_host_role_ids: null,
    allowed_signup_methods: null,
    default_signup_method: null,
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
  };

  beforeEach(() => {
    vi.clearAllMocks();
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
          <CreateGame />
        </AuthContext.Provider>
      </BrowserRouter>
    );
  };

  it('renders loading state initially', () => {
    vi.mocked(apiClient.get).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    renderWithAuth();
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('renders server dropdown when multiple servers available', async () => {
    const mockGuilds: Guild[] = [
      mockGuild,
      {
        id: '2',
        guild_name: 'Another Server',
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
      },
    ];

    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url === '/api/v1/guilds') {
        return Promise.resolve({ data: { guilds: mockGuilds } });
      }
      return Promise.resolve({ data: [] });
    });

    renderWithAuth();

    await waitFor(() => {
      // Verify a Select combobox is present for server selection
      const comboboxes = screen.getAllByRole('combobox');
      expect(comboboxes.length).toBeGreaterThan(0);
    });

    // Verify a Select combobox is present
    const comboboxes = screen.getAllByRole('combobox');
    expect(comboboxes.length).toBeGreaterThan(0);
  });

  it('auto-selects single server and loads templates', async () => {
    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url === '/api/v1/guilds') {
        return Promise.resolve({ data: { guilds: [mockGuild] } });
      }
      if (url === '/api/v1/guilds/1/templates') {
        return Promise.resolve({ data: [mockTemplate] });
      }
      if (url === '/api/v1/guilds/1/config') {
        return Promise.resolve({ status: StatusCodes.FORBIDDEN });
      }
      return Promise.resolve({ data: [] });
    });

    renderWithAuth();

    await waitFor(() => {
      // Template should be auto-selected
      expect(screen.getByText('Default Game (Default)')).toBeInTheDocument();
    });

    // Game form should be visible
    expect(screen.getByRole('textbox', { name: /game title/i })).toBeInTheDocument();
  });

  it('loads templates when server is selected', async () => {
    const mockGuilds: Guild[] = [mockGuild];

    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url === '/api/v1/guilds') {
        return Promise.resolve({ data: { guilds: mockGuilds } });
      }
      if (url === '/api/v1/guilds/1/templates') {
        return Promise.resolve({ data: [mockTemplate] });
      }
      if (url === '/api/v1/guilds/1/config') {
        return Promise.resolve({ status: StatusCodes.FORBIDDEN });
      }
      return Promise.resolve({ data: [] });
    });

    renderWithAuth();

    await waitFor(() => {
      // Template should be loaded and auto-selected
      expect(screen.getByText('Default Game (Default)')).toBeInTheDocument();
    });

    // Verify template description is shown
    expect(screen.getByText('Default game template')).toBeInTheDocument();
  });

  it('displays warning when no servers available', async () => {
    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url === '/api/v1/guilds') {
        return Promise.resolve({ data: { guilds: [] } });
      }
      return Promise.resolve({ data: [] });
    });

    renderWithAuth();

    await waitFor(() => {
      expect(screen.getByText(/No servers available with game templates/i)).toBeInTheDocument();
    });
  });

  it('displays template description when available', async () => {
    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url === '/api/v1/guilds') {
        return Promise.resolve({ data: { guilds: [mockGuild] } });
      }
      if (url === '/api/v1/guilds/1/templates') {
        return Promise.resolve({ data: [mockTemplate] });
      }
      if (url === '/api/v1/guilds/1/config') {
        return Promise.resolve({ status: StatusCodes.FORBIDDEN });
      }
      return Promise.resolve({ data: [] });
    });

    renderWithAuth();

    await waitFor(() => {
      expect(screen.getByText('Default game template')).toBeInTheDocument();
    });
  });

  it('shows GameForm after template selection', async () => {
    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url === '/api/v1/guilds') {
        return Promise.resolve({ data: { guilds: [mockGuild] } });
      }
      if (url === '/api/v1/guilds/1/templates') {
        return Promise.resolve({ data: [mockTemplate] });
      }
      if (url === '/api/v1/guilds/1/config') {
        return Promise.resolve({ status: StatusCodes.FORBIDDEN });
      }
      return Promise.resolve({ data: [] });
    });

    renderWithAuth();

    await waitFor(() => {
      expect(screen.getByRole('textbox', { name: /game title/i })).toBeInTheDocument();
    });
  });

  it('handles server selection change', async () => {
    const mockGuilds: Guild[] = [
      mockGuild,
      {
        id: '2',
        guild_name: 'Another Server',
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
      },
    ];

    const mockTemplate2: GameTemplate = {
      ...mockTemplate,
      id: 'template-2',
      guild_id: '2',
      name: 'Server 2 Game',
    };

    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url === '/api/v1/guilds') {
        return Promise.resolve({ data: { guilds: mockGuilds } });
      }
      if (url === '/api/v1/guilds/2/templates') {
        return Promise.resolve({ data: [mockTemplate2] });
      }
      if (url.includes('/config')) {
        return Promise.resolve({ status: StatusCodes.FORBIDDEN });
      }
      return Promise.resolve({ data: [] });
    });

    const user = userEvent.setup();
    renderWithAuth();

    // Wait for Server dropdown to appear
    await waitFor(() => {
      const comboboxes = screen.getAllByRole('combobox');
      expect(comboboxes.length).toBeGreaterThan(0);
    });

    // Get the first combobox (Server selector)
    const comboboxes = screen.getAllByRole('combobox');
    const serverSelect = comboboxes[0];
    if (!serverSelect) throw new Error('Server select not found');

    await user.click(serverSelect);

    const server2Option = await screen.findByRole('option', { name: /another server/i });
    await user.click(server2Option);

    await waitFor(() => {
      expect(screen.getByText('Server 2 Game (Default)')).toBeInTheDocument();
    });
  });

  it('includes signup_method in form submission when provided', async () => {
    const mockTemplateWithSignup: GameTemplate = {
      ...mockTemplate,
      default_signup_method: 'HOST_SELECTED',
    };

    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url === '/api/v1/guilds') {
        return Promise.resolve({ data: { guilds: [mockGuild] } });
      }
      if (url === '/api/v1/guilds/1/templates') {
        return Promise.resolve({ data: [mockTemplateWithSignup] });
      }
      if (url === '/api/v1/guilds/1/config') {
        return Promise.resolve({ status: StatusCodes.FORBIDDEN });
      }
      return Promise.resolve({ data: [] });
    });

    vi.mocked(apiClient.post).mockResolvedValue({
      data: { id: 'new-game-id' },
    });

    const user = userEvent.setup();
    renderWithAuth();

    // Wait for the form to load with template
    await waitFor(() => {
      expect(screen.getByRole('textbox', { name: /game title/i })).toBeInTheDocument();
    });

    // Fill in required fields
    const titleInput = screen.getByRole('textbox', { name: /game title/i });
    await user.clear(titleInput);
    await user.paste('Test Game');

    const descriptionInput = screen.getByRole('textbox', { name: /description/i });
    await user.clear(descriptionInput);
    await user.paste('Test Description');

    // Submit the form
    const submitButton = screen.getByRole('button', { name: /create game/i });
    await user.click(submitButton);

    // Verify the API was called with signup_method in the payload
    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalled();
    });

    const postCall = vi.mocked(apiClient.post).mock.calls[0];
    expect(postCall).toBeDefined();
    const formData = postCall![1] as FormData;

    // Verify signup_method is in the FormData
    expect(formData.get('signup_method')).toBe('HOST_SELECTED');
  });
});
