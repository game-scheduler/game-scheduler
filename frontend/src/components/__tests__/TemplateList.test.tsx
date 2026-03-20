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
    archive_channel_id: null,
    archive_channel_name: null,
    archive_delay_seconds: null,
    notify_role_ids: null,
    allowed_player_role_ids: null,
    allowed_host_role_ids: null,
    max_players: 6,
    expected_duration_minutes: 180,
    reminder_minutes: [60, 15],
    where: 'Discord Voice',
    signup_instructions: 'Please bring your character sheet',
    allowed_signup_methods: null,
    default_signup_method: null,
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
    archive_channel_id: null,
    archive_channel_name: null,
    archive_delay_seconds: null,
    notify_role_ids: null,
    allowed_player_role_ids: null,
    allowed_host_role_ids: null,
    max_players: 8,
    expected_duration_minutes: 120,
    reminder_minutes: [30],
    where: 'Community Center',
    signup_instructions: null,
    allowed_signup_methods: null,
    default_signup_method: null,
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
