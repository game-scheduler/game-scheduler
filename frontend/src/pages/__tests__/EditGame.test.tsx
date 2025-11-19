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
import { EditGame } from '../EditGame';
import { apiClient } from '../../api/client';
import { GameSession, Channel } from '../../types';

const mockNavigate = vi.fn();
const mockParams = { gameId: 'game123' };

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => mockParams,
  };
});

vi.mock('../../api/client');

describe('EditGame', () => {
  const mockGame: GameSession = {
    id: 'game123',
    title: 'Test Game',
    description: 'Test Description',
    scheduled_at: '2025-12-01T18:00:00Z',
    scheduled_at_unix: 1733076000,
    max_players: 8,
    guild_id: 'guild123',
    channel_id: 'channel123',
    message_id: null,
    host_id: 'user123',
    host_discord_id: '123456789',
    rules: 'Test rules',
    reminder_minutes: [60, 15],
    status: 'SCHEDULED',
    participant_count: 3,
    participants: [],
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
  };

  const mockChannels: Channel[] = [
    {
      id: 'channel123',
      guildId: 'guild123',
      channelId: '987654321',
      channelName: 'Test Channel',
      isActive: true,
      maxPlayers: null,
      reminderMinutes: null,
      defaultRules: null,
      allowedHostRoleIds: null,
      gameCategory: null,
      createdAt: '2025-01-01T00:00:00Z',
      updatedAt: '2025-01-01T00:00:00Z',
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('loads and displays game data', async () => {
    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url.includes('/games/')) {
        return Promise.resolve({ data: mockGame });
      }
      if (url.includes('/channels')) {
        return Promise.resolve({ data: mockChannels });
      }
      return Promise.reject(new Error('Unknown URL'));
    });

    render(
      <BrowserRouter>
        <EditGame />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByDisplayValue('Test Game')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Test Description')).toBeInTheDocument();
      expect(screen.getByDisplayValue('8')).toBeInTheDocument();
      expect(screen.getByDisplayValue('60, 15')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Test rules')).toBeInTheDocument();
    });
  });

  it('displays loading state initially', () => {
    vi.mocked(apiClient.get).mockImplementation(
      () => new Promise(() => {})
    );

    render(
      <BrowserRouter>
        <EditGame />
      </BrowserRouter>
    );

    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('displays error when game not found', async () => {
    vi.mocked(apiClient.get).mockRejectedValueOnce(
      new Error('Game not found')
    );

    render(
      <BrowserRouter>
        <EditGame />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Game not found')).toBeInTheDocument();
    });
  });

  it('handles save successfully', async () => {
    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url.includes('/games/')) {
        return Promise.resolve({ data: mockGame });
      }
      if (url.includes('/channels')) {
        return Promise.resolve({ data: mockChannels });
      }
      return Promise.reject(new Error('Unknown URL'));
    });

    vi.mocked(apiClient.put).mockResolvedValueOnce({ data: mockGame });

    const user = userEvent.setup();

    render(
      <BrowserRouter>
        <EditGame />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByDisplayValue('Test Game')).toBeInTheDocument();
    });

    const saveButton = screen.getByText('Save Changes');
    await user.click(saveButton);

    await waitFor(() => {
      expect(apiClient.put).toHaveBeenCalledWith(
        '/api/v1/games/game123',
        expect.objectContaining({
          title: 'Test Game',
          description: 'Test Description',
          channel_id: 'channel123',
          max_players: 8,
          reminder_minutes: [60, 15],
          rules: 'Test rules',
        })
      );
      expect(mockNavigate).toHaveBeenCalledWith('/games/game123');
    });
  });

  it('handles cancel button', async () => {
    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url.includes('/games/')) {
        return Promise.resolve({ data: mockGame });
      }
      if (url.includes('/channels')) {
        return Promise.resolve({ data: mockChannels });
      }
      return Promise.reject(new Error('Unknown URL'));
    });

    const user = userEvent.setup();

    render(
      <BrowserRouter>
        <EditGame />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByDisplayValue('Test Game')).toBeInTheDocument();
    });

    const cancelButton = screen.getByText('Cancel');
    await user.click(cancelButton);

    expect(mockNavigate).toHaveBeenCalledWith('/games/game123');
  });

  it('has required field validation', async () => {
    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url.includes('/games/')) {
        return Promise.resolve({ data: mockGame });
      }
      if (url.includes('/channels')) {
        return Promise.resolve({ data: mockChannels });
      }
      return Promise.reject(new Error('Unknown URL'));
    });

    render(
      <BrowserRouter>
        <EditGame />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByDisplayValue('Test Game')).toBeInTheDocument();
    });

    const titleInput = screen.getByLabelText(/Game Title/i);
    const descriptionInput = screen.getByLabelText(/Description/i);
    
    expect(titleInput).toHaveAttribute('required');
    expect(descriptionInput).toHaveAttribute('required');
  });

  it('handles update error', async () => {
    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url.includes('/games/')) {
        return Promise.resolve({ data: mockGame });
      }
      if (url.includes('/channels')) {
        return Promise.resolve({ data: mockChannels });
      }
      return Promise.reject(new Error('Unknown URL'));
    });

    vi.mocked(apiClient.put).mockRejectedValueOnce({
      response: { data: { detail: 'Update failed' } },
    });

    const user = userEvent.setup();

    render(
      <BrowserRouter>
        <EditGame />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByDisplayValue('Test Game')).toBeInTheDocument();
    });

    const saveButton = screen.getByText('Save Changes');
    await user.click(saveButton);

    await waitFor(() => {
      expect(screen.getByText('Update failed')).toBeInTheDocument();
    });
  });
});
