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
import userEvent from '@testing-library/user-event';
import { TemplateCard } from '../TemplateCard';
import { GameTemplate } from '../../types';

const mockTemplate: GameTemplate = {
  id: 'template-1',
  guild_id: 'guild-1',
  name: 'D&D Campaign',
  description: 'Weekly D&D game',
  order: 0,
  is_default: false,
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
};

const mockRoles = [
  { id: 'role-1', name: '@Players', color: 0, position: 1, managed: false },
  { id: 'role-2', name: '@DM', color: 0, position: 2, managed: false },
];

describe('TemplateCard', () => {
  it('renders template name and description', () => {
    const onEdit = vi.fn();
    const onDelete = vi.fn();
    const onSetDefault = vi.fn();

    render(
      <TemplateCard
        template={mockTemplate}
        roles={mockRoles}
        onEdit={onEdit}
        onDelete={onDelete}
        onSetDefault={onSetDefault}
      />
    );

    expect(screen.getByText('D&D Campaign')).toBeInTheDocument();
    expect(screen.getByText('Weekly D&D game')).toBeInTheDocument();
  });

  it('displays template settings', () => {
    const onEdit = vi.fn();
    const onDelete = vi.fn();
    const onSetDefault = vi.fn();

    render(
      <TemplateCard
        template={mockTemplate}
        roles={mockRoles}
        onEdit={onEdit}
        onDelete={onDelete}
        onSetDefault={onSetDefault}
      />
    );

    expect(screen.getByText('6')).toBeInTheDocument();
    expect(screen.getByText(/game-chat/)).toBeInTheDocument();
    expect(
      screen.getByText((_content, element) => {
        return element?.textContent === 'Max Players: 6';
      })
    ).toBeInTheDocument();
    expect(
      screen.getByText((_content, element) => {
        return element?.textContent === 'Duration: 180 minutes';
      })
    ).toBeInTheDocument();
    expect(
      screen.getByText((_content, element) => {
        return element?.textContent === 'Reminders: 60, 15 minutes before';
      })
    ).toBeInTheDocument();
    expect(screen.getByText(/Location:/)).toBeInTheDocument();
    expect(screen.getByText(/Discord Voice/)).toBeInTheDocument();
  });

  it('calls onEdit when edit button is clicked', async () => {
    const onEdit = vi.fn();
    const onDelete = vi.fn();
    const onSetDefault = vi.fn();
    const user = userEvent.setup();

    render(
      <TemplateCard
        template={mockTemplate}
        roles={mockRoles}
        onEdit={onEdit}
        onDelete={onDelete}
        onSetDefault={onSetDefault}
      />
    );

    const editButton = screen.getByTitle('Edit template');
    await user.click(editButton);

    expect(onEdit).toHaveBeenCalledWith(mockTemplate);
  });

  it('calls onDelete when delete button is clicked', async () => {
    const onEdit = vi.fn();
    const onDelete = vi.fn();
    const onSetDefault = vi.fn();
    const user = userEvent.setup();

    render(
      <TemplateCard
        template={mockTemplate}
        roles={mockRoles}
        onEdit={onEdit}
        onDelete={onDelete}
        onSetDefault={onSetDefault}
      />
    );

    const deleteButton = screen.getByTitle('Delete template');
    await user.click(deleteButton);

    expect(onDelete).toHaveBeenCalledWith(mockTemplate);
  });

  it('disables delete button for default template', () => {
    const defaultTemplate = { ...mockTemplate, is_default: true };
    const onEdit = vi.fn();
    const onDelete = vi.fn();
    const onSetDefault = vi.fn();

    render(
      <TemplateCard
        template={defaultTemplate}
        roles={mockRoles}
        onEdit={onEdit}
        onDelete={onDelete}
        onSetDefault={onSetDefault}
      />
    );

    const deleteButton = screen.getByTitle('Cannot delete default template');
    expect(deleteButton).toBeDisabled();
  });

  it('shows default chip for default template', () => {
    const defaultTemplate = { ...mockTemplate, is_default: true };
    const onEdit = vi.fn();
    const onDelete = vi.fn();
    const onSetDefault = vi.fn();

    render(
      <TemplateCard
        template={defaultTemplate}
        roles={mockRoles}
        onEdit={onEdit}
        onDelete={onDelete}
        onSetDefault={onSetDefault}
      />
    );

    expect(screen.getByText('Default')).toBeInTheDocument();
  });

  it('calls onSetDefault when set default button is clicked', async () => {
    const onEdit = vi.fn();
    const onDelete = vi.fn();
    const onSetDefault = vi.fn();
    const user = userEvent.setup();

    render(
      <TemplateCard
        template={mockTemplate}
        roles={mockRoles}
        onEdit={onEdit}
        onDelete={onDelete}
        onSetDefault={onSetDefault}
      />
    );

    const setDefaultButton = screen.getByTitle('Set as default');
    await user.click(setDefaultButton);

    expect(onSetDefault).toHaveBeenCalledWith(mockTemplate);
  });
});
