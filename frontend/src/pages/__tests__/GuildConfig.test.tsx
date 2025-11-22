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
    guild_id: 'guild123',
    guild_name: 'Test Guild',
    default_max_players: 10,
    default_reminder_minutes: [60, 15],
    default_rules: 'Be nice',
    allowed_host_role_ids: ['role1', 'role2'],
    bot_manager_role_ids: [],
    require_host_role: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('loads and displays guild configuration', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockGuild });

    render(
      <BrowserRouter>
        <GuildConfig />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByDisplayValue('10')).toBeInTheDocument();
      expect(screen.getByDisplayValue('60, 15')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Be respectful')).toBeInTheDocument();
    });
  });

  it('displays loading state initially', () => {
    vi.mocked(apiClient.get).mockImplementation(() => new Promise(() => {}));

    render(
      <BrowserRouter>
        <GuildConfig />
      </BrowserRouter>
    );

    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('handles save successfully', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockGuild });
    vi.mocked(apiClient.put).mockResolvedValueOnce({ data: mockGuild });

    const user = userEvent.setup();

    render(
      <BrowserRouter>
        <GuildConfig />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByDisplayValue('10')).toBeInTheDocument();
    });

    const saveButton = screen.getByText('Save Configuration');
    await user.click(saveButton);

    await waitFor(() => {
      expect(apiClient.put).toHaveBeenCalledWith('/api/v1/guilds/guild123', {
        default_max_players: 10,
        default_reminder_minutes: [60, 15],
        default_rules: 'Be respectful',
        allowed_host_role_ids: ['role1', 'role2'],
        require_host_role: true,
      });
    });
  });

  it('handles API errors gracefully', async () => {
    vi.mocked(apiClient.get).mockRejectedValueOnce({
      response: { data: { detail: 'Guild not found' } },
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
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockGuild });

    render(
      <BrowserRouter>
        <GuildConfig />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByDisplayValue('10')).toBeInTheDocument();
    });

    const maxPlayersInput = screen.getByLabelText(/Default Max Players/) as HTMLInputElement;
    const reminderInput = screen.getByLabelText(/Default Reminder Times/) as HTMLInputElement;
    const rulesInput = screen.getByLabelText(/Default Rules/) as HTMLTextAreaElement;

    expect(maxPlayersInput.value).toBe('10');
    expect(reminderInput.value).toBe('60, 15');
    expect(rulesInput.value).toBe('Be respectful');
  });
});
