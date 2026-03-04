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
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router';
import { CloneGame } from '../CloneGame';
import { apiClient } from '../../api/client';
import { GameSession, ParticipantType } from '../../types';

const mockNavigate = vi.fn();
const mockParams = { gameId: 'game123' };

vi.mock('react-router', async () => {
  const actual = await vi.importActual('react-router');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => mockParams,
  };
});

vi.mock('../../api/client');

vi.mock('@mui/x-date-pickers/LocalizationProvider', () => ({
  LocalizationProvider: ({ children }: { children: unknown }) => children,
}));

vi.mock('@mui/x-date-pickers/DateTimePicker', () => ({
  DateTimePicker: ({
    label,
    value,
    onChange,
    slotProps,
  }: {
    label: string;
    value: Date | null;
    onChange: (v: Date | null) => void;
    slotProps?: { textField?: { required?: boolean; fullWidth?: boolean } };
  }) => (
    <input
      aria-label={label}
      required={slotProps?.textField?.required}
      value={value ? value.toISOString() : ''}
      onChange={(e) => onChange(e.target.value ? new Date(e.target.value) : null)}
    />
  ),
}));

vi.mock('@mui/x-date-pickers/AdapterDateFns', () => ({
  AdapterDateFns: class {},
}));

describe('CloneGame', () => {
  const mockGame: GameSession = {
    id: 'game123',
    title: 'Test Game To Clone',
    description: 'A game',
    signup_instructions: null,
    scheduled_at: '2026-09-01T18:00:00Z',
    where: null,
    max_players: 4,
    guild_id: 'guild123',
    guild_name: 'Test Server',
    channel_id: 'channel123',
    channel_name: 'Test Channel',
    message_id: null,
    host: {
      id: 'host-id',
      game_session_id: 'game123',
      user_id: 'user123',
      discord_id: '123456789',
      display_name: 'Test Host',
      joined_at: '2026-01-01T00:00:00Z',
      position_type: ParticipantType.SELF_ADDED,
      position: 0,
    },
    reminder_minutes: [],
    notify_role_ids: [],
    expected_duration_minutes: null,
    status: 'SCHEDULED',
    signup_method: 'SELF_SIGNUP',
    participant_count: 0,
    participants: [],
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderCloneGame = () =>
    render(
      <BrowserRouter>
        <CloneGame />
      </BrowserRouter>
    );

  it('shows loading spinner while fetching source game', () => {
    vi.mocked(apiClient.get).mockImplementation(() => new Promise(() => {}));
    renderCloneGame();
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('shows error when fetch fails', async () => {
    vi.mocked(apiClient.get).mockRejectedValueOnce(new Error('Network error'));
    renderCloneGame();
    await waitFor(() => {
      expect(screen.getByText('Failed to load game. Please try again.')).toBeInTheDocument();
    });
  });

  it('shows back button on fetch error', async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.get).mockRejectedValueOnce(new Error('Network error'));
    renderCloneGame();
    await waitFor(() => {
      expect(screen.getByText('Back')).toBeInTheDocument();
    });
    await user.click(screen.getByText('Back'));
    expect(mockNavigate).toHaveBeenCalledWith(-1);
  });

  it('renders form with source game title after fetch', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockGame });
    renderCloneGame();
    await waitFor(() => {
      expect(screen.getByText('Test Game To Clone')).toBeInTheDocument();
    });
    expect(screen.getAllByText('Clone Game').length).toBeGreaterThan(0);
  });

  it('renders carryover dropdowns', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockGame });
    renderCloneGame();
    await waitFor(() => {
      expect(screen.getByLabelText('Player Carryover')).toBeInTheDocument();
      expect(screen.getByLabelText('Waitlist Carryover')).toBeInTheDocument();
    });
  });

  it('cancel button navigates back to source game', async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockGame });
    renderCloneGame();
    await waitFor(() => {
      expect(screen.getByText('Cancel')).toBeInTheDocument();
    });
    await user.click(screen.getByText('Cancel'));
    expect(mockNavigate).toHaveBeenCalledWith('/games/game123');
  });

  it('submits clone request and navigates to new game on success', async () => {
    const user = userEvent.setup();
    const newGame = { ...mockGame, id: 'new-game-456' };
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockGame });
    vi.mocked(apiClient.post).mockResolvedValueOnce({ data: newGame });

    renderCloneGame();

    await waitFor(() => {
      expect(screen.getByText('Test Game To Clone')).toBeInTheDocument();
    });

    const cloneButton = screen.getByRole('button', { name: 'Clone Game' });
    await user.click(cloneButton);

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith(
        '/api/v1/games/game123/clone',
        expect.objectContaining({
          player_carryover: 'NO',
          waitlist_carryover: 'NO',
        })
      );
      expect(mockNavigate).toHaveBeenCalledWith('/games/new-game-456');
    });
  });

  it('shows error message when clone request fails', async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockGame });
    vi.mocked(apiClient.post).mockRejectedValueOnce({
      response: { data: { detail: 'Permission denied' } },
    });

    renderCloneGame();

    await waitFor(() => {
      expect(screen.getByText('Test Game To Clone')).toBeInTheDocument();
    });

    const cloneButton = screen.getByRole('button', { name: 'Clone Game' });
    await user.click(cloneButton);

    await waitFor(() => {
      expect(screen.getByText('Permission denied')).toBeInTheDocument();
    });
  });

  it('shows generic error when clone request fails without detail', async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockGame });
    vi.mocked(apiClient.post).mockRejectedValueOnce(new Error('Network error'));

    renderCloneGame();

    await waitFor(() => {
      expect(screen.getByText('Test Game To Clone')).toBeInTheDocument();
    });

    const cloneButton = screen.getByRole('button', { name: 'Clone Game' });
    await user.click(cloneButton);

    await waitFor(() => {
      expect(screen.getByText('Failed to clone game. Please try again.')).toBeInTheDocument();
    });
  });
});
