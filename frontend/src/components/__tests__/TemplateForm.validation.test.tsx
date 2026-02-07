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
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TemplateForm } from '../TemplateForm';
import { Channel, DiscordRole } from '../../types';

describe('TemplateForm Validation', () => {
  const mockChannels: Channel[] = [
    {
      id: 'channel-1',
      channel_id: 'channel-1',
      channel_name: 'general',
      guild_id: 'guild-1',
      is_active: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
  ];

  const mockRoles: DiscordRole[] = [
    { id: 'role-1', name: '@player', color: 0, position: 1, managed: false },
  ];

  const mockOnClose = vi.fn();
  const mockOnSubmit = vi.fn();

  it('duration validation is handled by DurationSelector', () => {
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

    // Duration validation is fully tested in DurationSelector.test.tsx
    // This test just verifies DurationSelector is present by checking for InputLabel
    expect(screen.getAllByText('Expected Duration').length).toBeGreaterThan(0);
  });

  it('validates reminder minutes on blur', async () => {
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

    const reminderInput = screen.getByLabelText(/Reminder Minutes/i);
    await user.click(reminderInput);
    await user.keyboard('invalid,60');
    await user.tab();

    await waitFor(() => {
      expect(screen.getByText(/All reminder values must be numeric integers/i)).toBeInTheDocument();
    });
  });

  it('validates max players on blur', async () => {
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

    const maxPlayersInput = screen.getByLabelText(/Max Players/i);
    await user.click(maxPlayersInput);
    await user.keyboard('101');
    await user.tab();

    await waitFor(() => {
      expect(screen.getByText(/Max players cannot exceed 100/i)).toBeInTheDocument();
    });
  });

  it('shows character counter for description', async () => {
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

    const descriptionInput = screen.getByLabelText(/Description/i);
    await user.click(descriptionInput);
    await user.keyboard('Test description');
    await user.tab();

    await waitFor(() => {
      expect(screen.getByText(/16 \/ 4000 characters/i)).toBeInTheDocument();
    });
  });

  it('shows character counter for location', async () => {
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

    const locationInput = screen.getByLabelText(/Location/i);
    await user.click(locationInput);
    await user.keyboard('Test location');
    await user.tab();

    await waitFor(() => {
      expect(screen.getByText(/13 \/ 500 characters/i)).toBeInTheDocument();
    });
  });

  it('shows character counter for signup instructions', async () => {
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

    const signupInput = screen.getByLabelText(/Signup Instructions/i);
    await user.click(signupInput);
    await user.keyboard('Test instructions');
    await user.tab();

    await waitFor(() => {
      expect(screen.getByText(/17 \/ 1000 characters/i)).toBeInTheDocument();
    });
  });

  it('clears validation error when field corrected', async () => {
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

    const maxPlayersInput = screen.getByLabelText(/Max Players/i);

    await user.click(maxPlayersInput);
    await user.keyboard('101');
    await user.tab();

    await waitFor(() => {
      expect(screen.getByText(/Max players cannot exceed 100/i)).toBeInTheDocument();
    });

    await user.click(maxPlayersInput);
    await user.clear(maxPlayersInput);
    await user.keyboard('50');
    await user.tab();

    await waitFor(() => {
      expect(screen.queryByText(/Max players cannot exceed 100/i)).not.toBeInTheDocument();
    });
  });

  it('preserves submit-time validation', async () => {
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

    const submitButton = screen.getByRole('button', { name: /Create/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/Template name is required/i)).toBeInTheDocument();
    });
  });
});
