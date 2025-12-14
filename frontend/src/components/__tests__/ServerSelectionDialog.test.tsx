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
import userEvent from '@testing-library/user-event';
import { ServerSelectionDialog } from '../ServerSelectionDialog';
import { Guild } from '../../types';

describe('ServerSelectionDialog', () => {
  const mockGuilds: Guild[] = [
    {
      id: '1',
      guild_name: 'Test Server 1',
      created_at: '2025-01-01T00:00:00Z',
      updated_at: '2025-01-01T00:00:00Z',
    },
    {
      id: '2',
      guild_name: 'Test Server 2',
      created_at: '2025-01-01T00:00:00Z',
      updated_at: '2025-01-01T00:00:00Z',
    },
  ];

  it('renders dialog when open', () => {
    const onClose = vi.fn();
    const onSelect = vi.fn();

    render(
      <ServerSelectionDialog
        open={true}
        onClose={onClose}
        guilds={mockGuilds}
        onSelect={onSelect}
      />
    );

    expect(screen.getByText('Select Server')).toBeInTheDocument();
    expect(screen.getByText('Test Server 1')).toBeInTheDocument();
    expect(screen.getByText('Test Server 2')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    const onClose = vi.fn();
    const onSelect = vi.fn();

    render(
      <ServerSelectionDialog
        open={false}
        onClose={onClose}
        guilds={mockGuilds}
        onSelect={onSelect}
      />
    );

    expect(screen.queryByText('Select Server')).not.toBeInTheDocument();
  });

  it('calls onSelect when server is clicked', async () => {
    const onClose = vi.fn();
    const onSelect = vi.fn();
    const user = userEvent.setup();

    render(
      <ServerSelectionDialog
        open={true}
        onClose={onClose}
        guilds={mockGuilds}
        onSelect={onSelect}
      />
    );

    await user.click(screen.getByText('Test Server 1'));

    expect(onSelect).toHaveBeenCalledWith(mockGuilds[0]);
  });

  it('calls onClose when Cancel button is clicked', async () => {
    const onClose = vi.fn();
    const onSelect = vi.fn();
    const user = userEvent.setup();

    render(
      <ServerSelectionDialog
        open={true}
        onClose={onClose}
        guilds={mockGuilds}
        onSelect={onSelect}
      />
    );

    await user.click(screen.getByRole('button', { name: 'Cancel' }));

    expect(onClose).toHaveBeenCalled();
  });

  it('renders all guilds in the list', () => {
    const onClose = vi.fn();
    const onSelect = vi.fn();

    render(
      <ServerSelectionDialog
        open={true}
        onClose={onClose}
        guilds={mockGuilds}
        onSelect={onSelect}
      />
    );

    mockGuilds.forEach((guild) => {
      expect(screen.getByText(guild.guild_name)).toBeInTheDocument();
    });
  });

  it('handles empty guilds array', () => {
    const onClose = vi.fn();
    const onSelect = vi.fn();

    render(<ServerSelectionDialog open={true} onClose={onClose} guilds={[]} onSelect={onSelect} />);

    expect(screen.getByText('Select Server')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Test Server/ })).not.toBeInTheDocument();
  });
});
