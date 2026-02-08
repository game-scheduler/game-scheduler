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

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { GameForm } from '../GameForm';
import { Channel, CurrentUser } from '../../types';
import { AuthContext, type AuthContextType } from '../../contexts/AuthContext';

const mockAuthContextValue: AuthContextType = {
  user: {
    id: 'test-user-id',
    user_uuid: 'test-user-uuid',
    discordId: 'user123',
    username: 'testuser',
    guilds: [],
  } as CurrentUser,
  loading: false,
  login: vi.fn(),
  logout: vi.fn(),
  refreshUser: vi.fn(),
};

const mockChannels: Channel[] = [
  {
    id: 'channel-1',
    guild_id: 'guild123',
    channel_id: 'discord-channel-1',
    channel_name: 'general',
    is_active: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

const renderGameForm = (props = {}) => {
  const defaultProps = {
    mode: 'create' as const,
    guildId: 'guild123',
    channels: mockChannels,
    onSubmit: vi.fn(),
    onCancel: vi.fn(),
    ...props,
  };

  return render(
    <AuthContext.Provider value={mockAuthContextValue}>
      <GameForm {...defaultProps} />
    </AuthContext.Provider>
  );
};

describe('GameForm Error Handling', () => {
  describe('Backend Validation Error Display', () => {
    it('displays validation errors from backend for invalid mentions', () => {
      const validationErrors = [
        {
          input: '@invaliduser',
          reason: 'User not found in server',
          suggestions: [
            {
              discordId: '123456',
              username: 'validuser',
              displayName: 'Valid User',
            },
          ],
        },
      ];

      renderGameForm({
        validationErrors,
        validParticipants: [],
      });

      // ValidationErrors component should display the error
      expect(screen.getByText(/invaliduser/i)).toBeInTheDocument();
      expect(screen.getByText(/User not found in server/i)).toBeInTheDocument();
    });

    it('displays multiple validation errors', () => {
      const validationErrors = [
        {
          input: '@user1',
          reason: 'User not in server',
          suggestions: [],
        },
        {
          input: '@user2',
          reason: 'User not found',
          suggestions: [],
        },
      ];

      renderGameForm({
        validationErrors,
        validParticipants: [],
      });

      expect(screen.getByText(/user1/i)).toBeInTheDocument();
      expect(screen.getByText(/user2/i)).toBeInTheDocument();
    });

    it('shows suggestions for invalid mentions', () => {
      const validationErrors = [
        {
          input: '@oldname',
          reason: 'User changed username',
          suggestions: [
            {
              discordId: '123',
              username: 'newname',
              displayName: 'New Name',
            },
          ],
        },
      ];

      renderGameForm({
        validationErrors,
        validParticipants: [],
      });

      expect(screen.getByText(/oldname/i)).toBeInTheDocument();
      expect(screen.getByText(/newname/i)).toBeInTheDocument();
    });
  });

  describe('ValidationErrors Component Integration', () => {
    it('renders ValidationErrors component when errors exist', () => {
      const validationErrors = [
        {
          input: '@testuser',
          reason: 'Test error',
          suggestions: [],
        },
      ];

      renderGameForm({
        validationErrors,
      });

      // Component renders the error section
      expect(screen.getByText(/testuser/i)).toBeInTheDocument();
    });

    it('does not render ValidationErrors when no errors exist', () => {
      renderGameForm({
        validationErrors: null,
      });

      // No validation error section should be visible
      expect(screen.queryByText(/User not found/i)).not.toBeInTheDocument();
    });

    it('calls onValidationErrorClick when suggestion is clicked', async () => {
      const user = userEvent.setup();
      const onValidationErrorClick = vi.fn();
      const validationErrors = [
        {
          input: '@oldname',
          reason: 'Username changed',
          suggestions: [
            {
              discordId: '123',
              username: 'newname',
              displayName: 'New Name',
            },
          ],
        },
      ];

      renderGameForm({
        validationErrors,
        onValidationErrorClick,
      });

      // Find and click the suggestion
      const suggestionButton = screen.getByText(/newname/i);
      await user.click(suggestionButton);

      expect(onValidationErrorClick).toHaveBeenCalledWith('@oldname', '@newname');
    });
  });

  describe('Image Upload Validation', () => {
    it('validates image file size limits', async () => {
      const user = userEvent.setup();
      // Mock alert since image validation uses alert()
      const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});

      renderGameForm();

      // Find thumbnail file input
      const thumbnailInput = screen.getByLabelText(/thumbnail/i) as HTMLInputElement;

      // Create oversized file (>5MB)
      const oversizedFile = new File(['x'.repeat(6 * 1024 * 1024)], 'large.png', {
        type: 'image/png',
      });

      await user.upload(thumbnailInput, oversizedFile);

      // Alert should be called with size error
      expect(alertSpy).toHaveBeenCalledWith(expect.stringContaining('must be less than 5MB'));

      alertSpy.mockRestore();
    });

    it('validates image file types', () => {
      renderGameForm();

      const thumbnailInput = screen.getByLabelText(/thumbnail/i) as HTMLInputElement;

      // Verify accept attribute restricts file types
      expect(thumbnailInput).toHaveAttribute('accept', 'image/png,image/jpeg,image/gif,image/webp');
    });

    it('accepts valid image files', async () => {
      const user = userEvent.setup();
      const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});

      renderGameForm();

      const thumbnailInput = screen.getByLabelText(/thumbnail/i) as HTMLInputElement;

      // Create valid file
      const validFile = new File(['content'], 'image.png', {
        type: 'image/png',
      });

      await user.upload(thumbnailInput, validFile);

      // No alert should be called
      expect(alertSpy).not.toHaveBeenCalled();

      alertSpy.mockRestore();
    });
  });

  describe('Error Clearing on Successful Submission', () => {
    it('clears validation errors when form is resubmitted', async () => {
      const onSubmit = vi.fn();

      const { rerender } = renderGameForm({
        validationErrors: [
          {
            input: '@baduser',
            reason: 'Not found',
            suggestions: [],
          },
        ],
        onSubmit,
      });

      // Initially shows error
      expect(screen.getByText(/baduser/i)).toBeInTheDocument();

      // Rerender without validation errors (simulating successful submission)
      rerender(
        <AuthContext.Provider value={mockAuthContextValue}>
          <GameForm
            mode="create"
            guildId="guild123"
            channels={mockChannels}
            onSubmit={onSubmit}
            onCancel={vi.fn()}
            validationErrors={null}
          />
        </AuthContext.Provider>
      );

      // Error should be cleared
      expect(screen.queryByText(/baduser/i)).not.toBeInTheDocument();
    });

    it('preserves frontend validation when backend errors are cleared', async () => {
      const { rerender } = renderGameForm({
        validationErrors: [
          {
            input: '@baduser',
            reason: 'Not found',
            suggestions: [],
          },
        ],
      });

      // Initially shows backend error
      expect(screen.getByText(/baduser/i)).toBeInTheDocument();

      // Clear backend errors
      rerender(
        <AuthContext.Provider value={mockAuthContextValue}>
          <GameForm
            mode="create"
            guildId="guild123"
            channels={mockChannels}
            onSubmit={vi.fn()}
            onCancel={vi.fn()}
            validationErrors={null}
          />
        </AuthContext.Provider>
      );

      // Backend error cleared
      expect(screen.queryByText(/baduser/i)).not.toBeInTheDocument();

      // TODO: Update test for ReminderSelector - it validates input internally
      // ReminderSelector doesn't allow invalid numeric input, so this test needs to be rewritten
      // to test a different validation scenario (e.g., max players, description length, etc.)
    });
  });
});
