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
import { EditGame } from '../EditGame';
import { apiClient } from '../../api/client';
import { GameSession, Channel, ParticipantType } from '../../types';
import { AuthContext } from '../../contexts/AuthContext';

const mockNavigate = vi.fn();
const mockParams = { gameId: 'game123' };

const mockAuthContextValue = {
  user: { id: '1', user_uuid: 'uuid1', username: 'testuser' },
  loading: false,
  login: vi.fn(),
  logout: vi.fn(),
  refreshUser: vi.fn(),
};

vi.mock('react-router', async () => {
  const actual = await vi.importActual('react-router');
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
    signup_instructions: 'Test signup instructions',
    scheduled_at: '2025-12-01T18:00:00Z',
    where: null,
    max_players: 8,
    guild_id: 'guild123',
    guild_name: 'Test Server',
    channel_id: 'channel123',
    channel_name: 'Test Channel',
    message_id: null,
    host: {
      id: 'host-participant-id',
      game_session_id: 'game123',
      user_id: 'user123',
      discord_id: '123456789',
      display_name: 'Test Host',
      joined_at: '2025-01-01T00:00:00Z',
      position_type: ParticipantType.SELF_ADDED,
      position: 0,
    },
    reminder_minutes: [60, 15],
    notify_role_ids: [],
    expected_duration_minutes: null,
    status: 'SCHEDULED',
    signup_method: 'SELF_SIGNUP',
    participant_count: 3,
    participants: [],
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
  };

  const mockChannels: Channel[] = [
    {
      id: 'channel123',
      guild_id: 'guild123',
      channel_id: '987654321',
      channel_name: 'Test Channel',
      is_active: true,
      created_at: '2025-01-01T00:00:00Z',
      updated_at: '2025-01-01T00:00:00Z',
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
      if (url.includes('/roles')) {
        return Promise.resolve({ data: [] });
      }
      return Promise.reject(new Error('Unknown URL'));
    });

    render(
      <AuthContext.Provider value={mockAuthContextValue}>
        <BrowserRouter>
          <EditGame />
        </BrowserRouter>
      </AuthContext.Provider>
    );

    await waitFor(() => {
      expect(screen.getByDisplayValue('Test Game')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Test Description')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Test signup instructions')).toBeInTheDocument();
      expect(screen.getByDisplayValue('8')).toBeInTheDocument();
    });

    // Check reminder selector is present (chips may take longer to render)
    await waitFor(() => {
      expect(screen.getByLabelText('Add Reminder Time')).toBeInTheDocument();
    });
  });

  it('displays loading state initially', () => {
    vi.mocked(apiClient.get).mockImplementation(() => new Promise(() => {}));

    render(
      <AuthContext.Provider value={mockAuthContextValue}>
        <BrowserRouter>
          <EditGame />
        </BrowserRouter>
      </AuthContext.Provider>
    );

    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('displays error when game not found', async () => {
    vi.mocked(apiClient.get).mockRejectedValueOnce(new Error('Game not found'));

    render(
      <AuthContext.Provider value={mockAuthContextValue}>
        <BrowserRouter>
          <EditGame />
        </BrowserRouter>
      </AuthContext.Provider>
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
      if (url.includes('/roles')) {
        return Promise.resolve({ data: [] });
      }
      return Promise.reject(new Error('Unknown URL'));
    });

    vi.mocked(apiClient.put).mockResolvedValueOnce({ data: mockGame });

    const user = userEvent.setup();

    render(
      <AuthContext.Provider value={mockAuthContextValue}>
        <BrowserRouter>
          <EditGame />
        </BrowserRouter>
      </AuthContext.Provider>
    );

    await waitFor(() => {
      expect(screen.getByDisplayValue('Test Game')).toBeInTheDocument();
    });

    const saveButton = screen.getByText('Save Changes');
    await user.click(saveButton);

    await waitFor(() => {
      expect(apiClient.put).toHaveBeenCalledWith(
        '/api/v1/games/game123',
        expect.any(FormData),
        expect.objectContaining({
          headers: {
            'Content-Type': 'multipart/form-data',
          },
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
      if (url.includes('/roles')) {
        return Promise.resolve({ data: [] });
      }
      return Promise.reject(new Error('Unknown URL'));
    });

    const user = userEvent.setup();

    render(
      <AuthContext.Provider value={mockAuthContextValue}>
        <BrowserRouter>
          <EditGame />
        </BrowserRouter>
      </AuthContext.Provider>
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
      if (url.includes('/roles')) {
        return Promise.resolve({ data: [] });
      }
      return Promise.reject(new Error('Unknown URL'));
    });

    render(
      <AuthContext.Provider value={mockAuthContextValue}>
        <BrowserRouter>
          <EditGame />
        </BrowserRouter>
      </AuthContext.Provider>
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
      if (url.includes('/roles')) {
        return Promise.resolve({ data: [] });
      }
      return Promise.reject(new Error('Unknown URL'));
    });

    vi.mocked(apiClient.put).mockRejectedValueOnce({
      response: { data: { detail: 'Update failed' } },
    });

    const user = userEvent.setup();

    render(
      <AuthContext.Provider value={mockAuthContextValue}>
        <BrowserRouter>
          <EditGame />
        </BrowserRouter>
      </AuthContext.Provider>
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
