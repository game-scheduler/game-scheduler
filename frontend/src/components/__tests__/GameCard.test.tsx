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

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { GameCard } from '../GameCard';
import { GameSession } from '../../types';

const mockGame: GameSession = {
  id: 'game-1',
  title: 'D&D Session',
  description: 'Epic adventure awaits',
  signup_instructions: null,
  scheduled_at: '2025-12-25T19:00:00Z',
  where: 'Discord',
  max_players: 6,
  guild_id: 'guild-1',
  channel_id: 'channel-1',
  channel_name: 'game-chat',
  message_id: null,
  host: {
    id: 'participant-1',
    game_session_id: 'game-1',
    user_id: 'user-1',
    discord_id: '123456789',
    display_name: 'DungeonMaster',
    avatar_url: 'https://cdn.discordapp.com/avatars/123456789/abc123.png',
    joined_at: '2025-12-20T10:00:00Z',
    pre_filled_position: null,
  },
  reminder_minutes: [60, 15],
  notify_role_ids: null,
  expected_duration_minutes: 180,
  status: 'SCHEDULED',
  participant_count: 3,
  created_at: '2025-12-20T10:00:00Z',
  updated_at: '2025-12-20T10:00:00Z',
};

describe('GameCard', () => {
  it('renders game title and description', () => {
    render(
      <MemoryRouter>
        <GameCard game={mockGame} />
      </MemoryRouter>
    );

    expect(screen.getByText('D&D Session')).toBeInTheDocument();
    expect(screen.getByText('Epic adventure awaits')).toBeInTheDocument();
  });

  it('displays host avatar when avatar_url is present', () => {
    render(
      <MemoryRouter>
        <GameCard game={mockGame} />
      </MemoryRouter>
    );

    const avatar = screen.getByAltText('DungeonMaster');
    expect(avatar).toBeInTheDocument();
    expect(avatar).toHaveAttribute(
      'src',
      'https://cdn.discordapp.com/avatars/123456789/abc123.png'
    );
  });

  it('displays host name with avatar', () => {
    render(
      <MemoryRouter>
        <GameCard game={mockGame} />
      </MemoryRouter>
    );

    expect(screen.getByText('Host:')).toBeInTheDocument();
    expect(screen.getByText('DungeonMaster')).toBeInTheDocument();
  });

  it('displays initial fallback when avatar_url is null', () => {
    const gameWithoutAvatar: GameSession = {
      ...mockGame,
      host: {
        ...mockGame.host,
        avatar_url: null,
      },
    };

    render(
      <MemoryRouter>
        <GameCard game={gameWithoutAvatar} />
      </MemoryRouter>
    );

    const avatar = screen.getByText('D');
    expect(avatar).toBeInTheDocument();
    expect(screen.getByText('Host:')).toBeInTheDocument();
    expect(screen.getByText('DungeonMaster')).toBeInTheDocument();
  });

  it('displays initial fallback when avatar_url is undefined', () => {
    const gameWithoutAvatar: GameSession = {
      ...mockGame,
      host: {
        ...mockGame.host,
        avatar_url: undefined,
      },
    };

    render(
      <MemoryRouter>
        <GameCard game={gameWithoutAvatar} />
      </MemoryRouter>
    );

    const avatar = screen.getByText('D');
    expect(avatar).toBeInTheDocument();
  });

  it('displays game status and player count', () => {
    render(
      <MemoryRouter>
        <GameCard game={mockGame} />
      </MemoryRouter>
    );

    expect(screen.getByText('SCHEDULED')).toBeInTheDocument();
    expect(screen.getByText(/3\/6/)).toBeInTheDocument();
  });

  it('displays formatted scheduled time', () => {
    render(
      <MemoryRouter>
        <GameCard game={mockGame} />
      </MemoryRouter>
    );

    expect(screen.getByText(/When:/)).toBeInTheDocument();
  });

  it('displays where information when present', () => {
    render(
      <MemoryRouter>
        <GameCard game={mockGame} />
      </MemoryRouter>
    );

    expect(screen.getByText(/Where:/)).toBeInTheDocument();
    expect(screen.getByText(/Discord/)).toBeInTheDocument();
  });

  it('displays duration when present', () => {
    render(
      <MemoryRouter>
        <GameCard game={mockGame} />
      </MemoryRouter>
    );

    expect(screen.getByText(/Duration:/)).toBeInTheDocument();
    expect(screen.getByText(/3h/)).toBeInTheDocument();
  });

  it('hides actions when showActions is false', () => {
    render(
      <MemoryRouter>
        <GameCard game={mockGame} showActions={false} />
      </MemoryRouter>
    );

    expect(screen.queryByText('View Details')).not.toBeInTheDocument();
  });

  it('shows actions by default', () => {
    render(
      <MemoryRouter>
        <GameCard game={mockGame} />
      </MemoryRouter>
    );

    expect(screen.getByText('View Details')).toBeInTheDocument();
  });

  it('avatar has proper alt text for accessibility', () => {
    render(
      <MemoryRouter>
        <GameCard game={mockGame} />
      </MemoryRouter>
    );

    const avatar = screen.getByAltText('DungeonMaster');
    expect(avatar).toBeInTheDocument();
  });
});
