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
import { TemplateForm } from '../TemplateForm';
import { GameTemplate, Channel, DiscordRole } from '../../types';

describe('TemplateForm', () => {
  const mockOnClose = vi.fn();
  const mockOnSubmit = vi.fn();

  const mockChannels: Channel[] = [
    {
      id: 'channel-1',
      guild_id: 'guild-1',
      channel_id: '123456',
      channel_name: 'general',
      is_active: true,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
  ];

  const mockRoles: DiscordRole[] = [
    {
      id: 'role-1',
      name: 'Player',
      color: 0,
      position: 1,
      managed: false,
    },
    {
      id: 'role-2',
      name: 'Host',
      color: 0,
      position: 2,
      managed: false,
    },
  ];

  const mockTemplate: GameTemplate = {
    id: 'template-1',
    guild_id: 'guild-1',
    name: 'D&D Campaign',
    description: 'Weekly D&D session',
    channel_id: 'channel-1',
    channel_name: 'general',
    order: 1,
    is_default: false,
    where: 'Online via Discord',
    signup_instructions: 'React to sign up',
    max_players: 6,
    expected_duration_minutes: 180,
    reminder_minutes: [60, 15],
    notify_role_ids: ['role-1'],
    allowed_player_role_ids: [],
    allowed_host_role_ids: ['role-2'],
    allowed_signup_methods: ['BUTTON', 'EMOJI'],
    default_signup_method: 'BUTTON',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockOnSubmit.mockResolvedValue(undefined);
  });

  it('converts empty strings to null for optional fields', async () => {
    const user = userEvent.setup();

    render(
      <TemplateForm
        open={true}
        template={null}
        guildId="guild-1"
        channels={mockChannels}
        roles={mockRoles}
        onClose={mockOnClose}
        onSubmit={mockOnSubmit}
      />
    );

    const nameInput = screen.getByLabelText(/Template Name/i);
    await user.click(nameInput);
    await user.paste('New Template');

    const comboboxes = screen.getAllByRole('combobox');
    const channelSelect = comboboxes[0];
    if (channelSelect) {
      await user.click(channelSelect);
      await user.click(screen.getByRole('option', { name: 'general' }));
    }

    await user.click(screen.getByRole('button', { name: /create/i }));

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'New Template',
          description: null,
          where: null,
          signup_instructions: null,
        })
      );
    });
  });

  it('includes null values in update requests for cleared fields', async () => {
    const user = userEvent.setup();

    render(
      <TemplateForm
        open={true}
        template={mockTemplate}
        guildId="guild-1"
        channels={mockChannels}
        roles={mockRoles}
        onClose={mockOnClose}
        onSubmit={mockOnSubmit}
      />
    );

    const descriptionInput = screen.getByLabelText(/Description/i);
    await user.clear(descriptionInput);

    const locationInput = screen.getByLabelText(/Location/i);
    await user.clear(locationInput);

    await user.click(screen.getByRole('button', { name: /update/i }));

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          description: null,
          where: null,
        })
      );
    });
  });

  it('includes non-empty values correctly in update requests', async () => {
    const user = userEvent.setup();

    render(
      <TemplateForm
        open={true}
        template={mockTemplate}
        guildId="guild-1"
        channels={mockChannels}
        roles={mockRoles}
        onClose={mockOnClose}
        onSubmit={mockOnSubmit}
      />
    );

    const descriptionInput = screen.getByLabelText(/Description/i);
    await user.clear(descriptionInput);
    await user.click(descriptionInput);
    await user.paste('Updated description');

    await user.click(screen.getByRole('button', { name: /update/i }));

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          description: 'Updated description',
        })
      );
    });
  });

  it('sends all form fields including nulls on update', async () => {
    const user = userEvent.setup();

    const templateWithNulls: GameTemplate = {
      ...mockTemplate,
      description: null,
      where: null,
      signup_instructions: null,
      max_players: null,
      expected_duration_minutes: null,
      reminder_minutes: null,
      notify_role_ids: null,
      allowed_player_role_ids: null,
      allowed_host_role_ids: null,
      allowed_signup_methods: null,
      default_signup_method: null,
    };

    render(
      <TemplateForm
        open={true}
        template={templateWithNulls}
        guildId="guild-1"
        channels={mockChannels}
        roles={mockRoles}
        onClose={mockOnClose}
        onSubmit={mockOnSubmit}
      />
    );

    await user.click(screen.getByRole('button', { name: /update/i }));

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalled();
      const submitCall = mockOnSubmit.mock.calls[0]?.[0];
      expect(submitCall).toEqual(
        expect.objectContaining({
          name: mockTemplate.name,
          description: null,
          where: null,
          signup_instructions: null,
          max_players: null,
          expected_duration_minutes: null,
          reminder_minutes: null,
          notify_role_ids: null,
          allowed_player_role_ids: null,
          allowed_host_role_ids: null,
        })
      );
    });
  });

  it('validates required fields before submission', async () => {
    const user = userEvent.setup();

    render(
      <TemplateForm
        open={true}
        template={null}
        guildId="guild-1"
        channels={mockChannels}
        roles={mockRoles}
        onClose={mockOnClose}
        onSubmit={mockOnSubmit}
      />
    );

    await user.click(screen.getByRole('button', { name: /create/i }));

    await waitFor(() => {
      expect(mockOnSubmit).not.toHaveBeenCalled();
    });
  });
});
