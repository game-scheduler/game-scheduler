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
    archive_channel_id: null,
    archive_channel_name: null,
    archive_delay_seconds: null,
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
      archive_channel_id: null,
      archive_channel_name: null,
      archive_delay_seconds: null,
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

describe('TemplateForm - ReminderSelector Integration', () => {
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

  const mockRoles: DiscordRole[] = [];

  beforeEach(() => {
    vi.clearAllMocks();
    mockOnSubmit.mockResolvedValue(undefined);
  });

  it('should render ReminderSelector component', () => {
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

    expect(screen.getByLabelText('Add Reminder Time')).toBeInTheDocument();
  });

  it('should initialize ReminderSelector with empty array for new template', () => {
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

    const chips = screen.queryByRole('button', { name: /delete/i });
    expect(chips).not.toBeInTheDocument();
  });

  it('should initialize ReminderSelector with existing reminder times', () => {
    const mockTemplate: GameTemplate = {
      id: 'template-1',
      guild_id: 'guild-1',
      name: 'Test Template',
      description: 'Test',
      channel_id: 'channel-1',
      channel_name: 'general',
      order: 1,
      is_default: false,
      where: null,
      signup_instructions: null,
      max_players: null,
      expected_duration_minutes: null,
      reminder_minutes: [30, 60, 1440],
      notify_role_ids: null,
      allowed_player_role_ids: null,
      allowed_host_role_ids: null,
      allowed_signup_methods: ['BUTTON', 'EMOJI'],
      default_signup_method: 'BUTTON',
      archive_channel_id: null,
      archive_channel_name: null,
      archive_delay_seconds: null,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    };

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

    expect(screen.getByLabelText('Add Reminder Time')).toBeInTheDocument();
  });

  it('should update state when preset is selected', async () => {
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

    const select = screen.getByLabelText('Add Reminder Time');
    await user.click(select);

    const option = screen.getByRole('option', { name: '30 minutes' });
    await user.click(option);

    await waitFor(() => {
      expect(screen.getByText('30 minutes')).toBeInTheDocument();
    });
  });

  it('should allow chip deletion', async () => {
    const user = userEvent.setup();
    const mockTemplate: GameTemplate = {
      id: 'template-1',
      guild_id: 'guild-1',
      name: 'Test Template',
      description: 'Test',
      channel_id: 'channel-1',
      channel_name: 'general',
      order: 1,
      is_default: false,
      where: null,
      signup_instructions: null,
      max_players: null,
      expected_duration_minutes: null,
      reminder_minutes: [30, 60],
      notify_role_ids: null,
      allowed_player_role_ids: null,
      allowed_host_role_ids: null,
      allowed_signup_methods: ['BUTTON', 'EMOJI'],
      default_signup_method: 'BUTTON',
      archive_channel_id: null,
      archive_channel_name: null,
      archive_delay_seconds: null,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    };

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

    await waitFor(() => {
      expect(screen.getByText('30 minutes')).toBeInTheDocument();
      expect(screen.getByText('1 hour')).toBeInTheDocument();
    });

    // Find chip with delete button by finding the chip button role
    const chipButtons = screen.getAllByRole('button');
    const thirtyMinChip = chipButtons.find((button) => button.textContent === '30 minutes');
    expect(thirtyMinChip).toBeDefined();

    // Click the delete icon within the chip
    const deleteIcon = thirtyMinChip?.querySelector('[data-testid="CancelIcon"]');
    if (deleteIcon) {
      await user.click(deleteIcon as Element);
    }

    await waitFor(() => {
      expect(screen.queryByText('30 minutes')).not.toBeInTheDocument();
      expect(screen.getByText('1 hour')).toBeInTheDocument();
    });
  });

  it('should allow custom value addition', async () => {
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

    const select = screen.getByLabelText('Add Reminder Time');
    await user.click(select);

    const customOption = screen.getByRole('option', { name: /custom/i });
    await user.click(customOption);

    await waitFor(() => {
      expect(screen.getByLabelText(/custom minutes/i)).toBeInTheDocument();
    });

    const input = screen.getByLabelText(/custom minutes/i);
    await user.type(input, '45');

    const addButton = screen.getByRole('button', { name: /^add$/i });
    await user.click(addButton);

    await waitFor(() => {
      expect(screen.getByText('45 minutes')).toBeInTheDocument();
    });
  });

  it('should include reminder times in template submission', async () => {
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

    await user.type(screen.getByLabelText(/template name/i), 'Test Template');

    const select = screen.getByLabelText('Add Reminder Time');
    await user.click(select);
    const option = screen.getByRole('option', { name: '1 hour' });
    await user.click(option);

    await waitFor(() => {
      expect(screen.getByText('1 hour')).toBeInTheDocument();
    });

    const createButton = screen.getByRole('button', { name: /create/i });
    await user.click(createButton);

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          reminder_minutes: [60],
        })
      );
    });
  });
});

describe('TemplateForm - Archive Fields', () => {
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
    {
      id: 'channel-archive',
      guild_id: 'guild-1',
      channel_id: '789012',
      channel_name: 'archive',
      is_active: true,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
  ];

  const mockRoles: DiscordRole[] = [];

  beforeEach(() => {
    vi.clearAllMocks();
    mockOnSubmit.mockResolvedValue(undefined);
  });

  it('renders archive channel dropdown and delay fields', () => {
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

    expect(screen.getAllByText('Archive Channel').length).toBeGreaterThan(0);
    expect(screen.getByLabelText(/^Days$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^Hours$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^Minutes$/i)).toBeInTheDocument();
  });

  it('includes null archive fields for new template when left empty', async () => {
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

    await user.type(screen.getByLabelText(/Template Name/i), 'Test');
    await user.click(screen.getByRole('button', { name: /create/i }));

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          archive_channel_id: null,
          archive_delay_seconds: null,
        })
      );
    });
  });

  it('converts days/hours/minutes to seconds in submission', async () => {
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

    await user.type(screen.getByLabelText(/Template Name/i), 'Test');
    await user.type(screen.getByLabelText(/^Days$/i), '1');
    await user.type(screen.getByLabelText(/^Hours$/i), '2');
    await user.type(screen.getByLabelText(/^Minutes$/i), '30');

    await user.click(screen.getByRole('button', { name: /create/i }));

    await waitFor(() => {
      // 1 day + 2 hours + 30 minutes = 86400 + 7200 + 1800 = 95400 seconds
      expect(mockOnSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          archive_delay_seconds: 95400,
        })
      );
    });
  });

  it('populates archive fields from existing template', () => {
    const templateWithArchive: GameTemplate = {
      id: 'template-1',
      guild_id: 'guild-1',
      name: 'Test Template',
      description: null,
      channel_id: 'channel-1',
      channel_name: 'general',
      order: 1,
      is_default: false,
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
      archive_channel_id: 'channel-archive',
      archive_channel_name: 'archive',
      archive_delay_seconds: 90000,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    };

    render(
      <TemplateForm
        open={true}
        template={templateWithArchive}
        guildId="guild-1"
        channels={mockChannels}
        roles={mockRoles}
        onClose={mockOnClose}
        onSubmit={mockOnSubmit}
      />
    );

    // 90000 seconds = 1 day + 1 hour (86400 + 3600)
    expect((screen.getByLabelText(/^Days$/i) as HTMLInputElement).value).toBe('1');
    expect((screen.getByLabelText(/^Hours$/i) as HTMLInputElement).value).toBe('1');
    expect((screen.getByLabelText(/^Minutes$/i) as HTMLInputElement).value).toBe('');
  });
});

describe('TemplateForm - Role Priority Section', () => {
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
    { id: 'role-1', name: 'Mage', color: 0, position: 1, managed: false },
    { id: 'role-2', name: 'Warrior', color: 0, position: 2, managed: false },
    { id: 'role-3', name: 'Rogue', color: 0, position: 3, managed: false },
  ];

  const baseTemplate: GameTemplate = {
    id: 'template-1',
    guild_id: 'guild-1',
    name: 'Role Game',
    description: null,
    channel_id: 'channel-1',
    channel_name: 'general',
    order: 1,
    is_default: false,
    archive_channel_id: null,
    archive_channel_name: null,
    archive_delay_seconds: null,
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
    signup_priority_role_ids: null,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockOnSubmit.mockResolvedValue(undefined);
  });

  it('renders the Role Priority section', () => {
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

    expect(screen.getByText(/role priority/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/add priority role/i)).toBeInTheDocument();
  });

  it('adds a role to the priority list on selection', async () => {
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

    const select = screen.getByLabelText(/add priority role/i);
    await user.click(select);
    await user.click(screen.getByRole('option', { name: /@Mage/i }));

    expect(screen.getByText('@Mage')).toBeInTheDocument();
  });

  it('removes a role from the priority list', async () => {
    const user = userEvent.setup();
    render(
      <TemplateForm
        open={true}
        template={{ ...baseTemplate, signup_priority_role_ids: ['role-1', 'role-2'] }}
        guildId="guild-1"
        channels={mockChannels}
        roles={mockRoles}
        onClose={mockOnClose}
        onSubmit={mockOnSubmit}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('@Mage')).toBeInTheDocument();
      expect(screen.getByText('@Warrior')).toBeInTheDocument();
    });

    const removeButtons = screen.getAllByRole('button', { name: /remove @Mage/i });
    await user.click(removeButtons[0]!);

    await waitFor(() => {
      expect(screen.queryByText('@Mage')).not.toBeInTheDocument();
      expect(screen.getByText('@Warrior')).toBeInTheDocument();
    });
  });

  it('disables the role dropdown when 8 roles are already selected', async () => {
    const eightRoles = Array.from({ length: 8 }, (_, i) => `role-extra-${i}`);
    const templateWith8 = {
      ...baseTemplate,
      signup_priority_role_ids: eightRoles,
    };
    const rolesWithExtras: DiscordRole[] = [
      ...mockRoles,
      ...eightRoles.map((id, i) => ({
        id,
        name: `Extra${i}`,
        color: 0,
        position: i + 10,
        managed: false,
      })),
    ];

    render(
      <TemplateForm
        open={true}
        template={templateWith8}
        guildId="guild-1"
        channels={mockChannels}
        roles={rolesWithExtras}
        onClose={mockOnClose}
        onSubmit={mockOnSubmit}
      />
    );

    const select = screen.getByLabelText(/add priority role/i);
    expect(select).toHaveAttribute('aria-disabled', 'true');
  });

  it('initializes priority role list from existing template', () => {
    render(
      <TemplateForm
        open={true}
        template={{ ...baseTemplate, signup_priority_role_ids: ['role-2', 'role-1'] }}
        guildId="guild-1"
        channels={mockChannels}
        roles={mockRoles}
        onClose={mockOnClose}
        onSubmit={mockOnSubmit}
      />
    );

    const items = screen.getAllByRole('listitem');
    expect(items[0]).toHaveTextContent('@Warrior');
    expect(items[1]).toHaveTextContent('@Mage');
  });

  it('submits signup_priority_role_ids in priority order', async () => {
    const user = userEvent.setup();
    render(
      <TemplateForm
        open={true}
        template={{ ...baseTemplate, signup_priority_role_ids: ['role-1', 'role-2'] }}
        guildId="guild-1"
        channels={mockChannels}
        roles={mockRoles}
        onClose={mockOnClose}
        onSubmit={mockOnSubmit}
      />
    );

    await user.click(screen.getByRole('button', { name: /update/i }));

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          signup_priority_role_ids: ['role-1', 'role-2'],
        })
      );
    });
  });

  it('reorders roles by dragging', async () => {
    const user = userEvent.setup();
    render(
      <TemplateForm
        open={true}
        template={{ ...baseTemplate, signup_priority_role_ids: ['role-1', 'role-2', 'role-3'] }}
        guildId="guild-1"
        channels={mockChannels}
        roles={mockRoles}
        onClose={mockOnClose}
        onSubmit={mockOnSubmit}
      />
    );

    await waitFor(() => {
      const items = screen.getAllByRole('listitem');
      expect(items[0]).toHaveTextContent('@Mage');
      expect(items[1]).toHaveTextContent('@Warrior');
      expect(items[2]).toHaveTextContent('@Rogue');
    });

    const items = screen.getAllByRole('listitem');

    // Drag first item over the last item to reorder
    await user.pointer([
      { keys: '[MouseLeft>]', target: items[0]! },
      { target: items[2]! },
      { keys: '[/MouseLeft]' },
    ]);

    // Trigger dragstart, dragover, drop, dragend manually via fireEvent
    const { fireEvent } = await import('@testing-library/react');
    fireEvent.dragStart(items[0]!);
    fireEvent.dragOver(items[2]!, { preventDefault: vi.fn() });
    fireEvent.drop(items[2]!);
    fireEvent.dragEnd(items[0]!);

    await waitFor(() => {
      const submitButton = screen.getByRole('button', { name: /update/i });
      return submitButton;
    });

    await user.click(screen.getByRole('button', { name: /update/i }));

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          signup_priority_role_ids: ['role-2', 'role-3', 'role-1'],
        })
      );
    });
  });

  it('submits signup_priority_role_ids as null when list is empty', async () => {
    const user = userEvent.setup();
    render(
      <TemplateForm
        open={true}
        template={baseTemplate}
        guildId="guild-1"
        channels={mockChannels}
        roles={mockRoles}
        onClose={mockOnClose}
        onSubmit={mockOnSubmit}
      />
    );

    await user.click(screen.getByRole('button', { name: /update/i }));

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          signup_priority_role_ids: null,
        })
      );
    });
  });
});
