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
import { TemplateList } from '../TemplateList';
import { GameTemplate } from '../../types';

const mockTemplates: GameTemplate[] = [
  {
    id: 'template-1',
    guild_id: 'guild-1',
    name: 'D&D Campaign',
    description: 'Weekly D&D game',
    order: 0,
    is_default: true,
    channel_id: 'channel-1',
    channel_name: 'game-chat',
    notify_role_ids: null,
    allowed_player_role_ids: null,
    allowed_host_role_ids: null,
    max_players: 6,
    expected_duration_minutes: 180,
    reminder_minutes: [60, 15],
    where: 'Discord Voice',
    signup_instructions: 'Please bring your character sheet',
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
  },
  {
    id: 'template-2',
    guild_id: 'guild-1',
    name: 'Board Game Night',
    description: 'Casual board games',
    order: 1,
    is_default: false,
    channel_id: 'channel-2',
    channel_name: 'board-games',
    notify_role_ids: null,
    allowed_player_role_ids: null,
    allowed_host_role_ids: null,
    max_players: 8,
    expected_duration_minutes: 120,
    reminder_minutes: [30],
    where: 'Community Center',
    signup_instructions: null,
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
  },
];

const mockRoles = [
  { id: 'role-1', name: '@Players', color: 0, position: 1, managed: false },
  { id: 'role-2', name: '@DM', color: 0, position: 2, managed: false },
];

describe('TemplateList', () => {
  it('renders all templates', () => {
    const onEdit = vi.fn();
    const onDelete = vi.fn();
    const onSetDefault = vi.fn();
    const onReorder = vi.fn();

    render(
      <TemplateList
        templates={mockTemplates}
        roles={mockRoles}
        onEdit={onEdit}
        onDelete={onDelete}
        onSetDefault={onSetDefault}
        onReorder={onReorder}
      />
    );

    expect(screen.getByText('D&D Campaign')).toBeInTheDocument();
    expect(screen.getByText('Board Game Night')).toBeInTheDocument();
  });

  it('shows message when no templates', () => {
    const onEdit = vi.fn();
    const onDelete = vi.fn();
    const onSetDefault = vi.fn();
    const onReorder = vi.fn();

    render(
      <TemplateList
        templates={[]}
        roles={mockRoles}
        onEdit={onEdit}
        onDelete={onDelete}
        onSetDefault={onSetDefault}
        onReorder={onReorder}
      />
    );

    expect(
      screen.getByText(/No templates found. Create your first template to get started./)
    ).toBeInTheDocument();
  });

  it('renders templates in order', () => {
    const onEdit = vi.fn();
    const onDelete = vi.fn();
    const onSetDefault = vi.fn();
    const onReorder = vi.fn();

    const { container } = render(
      <TemplateList
        templates={mockTemplates}
        roles={mockRoles}
        onEdit={onEdit}
        onDelete={onDelete}
        onSetDefault={onSetDefault}
        onReorder={onReorder}
      />
    );

    const templateNames = container.querySelectorAll('h6');
    expect(templateNames[0]).toHaveTextContent('D&D Campaign');
    expect(templateNames[1]).toHaveTextContent('Board Game Night');
  });
});
