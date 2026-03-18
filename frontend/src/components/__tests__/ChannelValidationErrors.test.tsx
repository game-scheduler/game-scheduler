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
import { ChannelValidationErrors } from '../ChannelValidationErrors';

describe('ChannelValidationErrors', () => {
  it('renders error alert with title', () => {
    const errors = [
      {
        type: 'not_found',
        input: '#general',
        reason: "Channel '#general' not found",
        suggestions: [],
      },
    ];

    render(<ChannelValidationErrors errors={errors} onSuggestionClick={vi.fn()} />);

    expect(screen.getByText('Location contains an invalid channel reference')).toBeInTheDocument();
  });

  it('displays error input and reason', () => {
    const errors = [
      {
        type: 'not_found',
        input: '#test-channel',
        reason: "Channel '#test-channel' not found",
        suggestions: [],
      },
    ];

    render(<ChannelValidationErrors errors={errors} onSuggestionClick={vi.fn()} />);

    expect(screen.getByText('#test-channel')).toBeInTheDocument();
    expect(screen.getByText(/Channel '#test-channel' not found/)).toBeInTheDocument();
  });

  it('displays "Did you mean:" text when suggestions exist', () => {
    const errors = [
      {
        type: 'not_found',
        input: '#general',
        reason: "Channel '#general' not found",
        suggestions: [
          { id: '123', name: 'general-chat' },
          { id: '456', name: 'general-discussion' },
        ],
      },
    ];

    render(<ChannelValidationErrors errors={errors} onSuggestionClick={vi.fn()} />);

    expect(screen.getByText('Did you mean:')).toBeInTheDocument();
  });

  it('renders suggestion chips with channel names', () => {
    const errors = [
      {
        type: 'ambiguous',
        input: '#general',
        reason: "Multiple channels match '#general'",
        suggestions: [
          { id: '123', name: 'general-chat' },
          { id: '456', name: 'general-discussion' },
        ],
      },
    ];

    render(<ChannelValidationErrors errors={errors} onSuggestionClick={vi.fn()} />);

    expect(screen.getByText('#general-chat')).toBeInTheDocument();
    expect(screen.getByText('#general-discussion')).toBeInTheDocument();
  });

  it('calls onSuggestionClick when suggestion chip is clicked', async () => {
    const user = userEvent.setup();
    const onSuggestionClick = vi.fn();
    const errors = [
      {
        type: 'not_found',
        input: '#general',
        reason: "Channel '#general' not found",
        suggestions: [{ id: '123', name: 'general-chat' }],
      },
    ];

    render(<ChannelValidationErrors errors={errors} onSuggestionClick={onSuggestionClick} />);

    const chip = screen.getByText('#general-chat');
    await user.click(chip);

    expect(onSuggestionClick).toHaveBeenCalledWith('#general', '#general-chat');
  });

  it('displays multiple errors', () => {
    const errors = [
      {
        type: 'not_found',
        input: '#general',
        reason: "Channel '#general' not found",
        suggestions: [],
      },
      {
        type: 'ambiguous',
        input: '#test',
        reason: "Multiple channels match '#test'",
        suggestions: [
          { id: '789', name: 'test-1' },
          { id: '012', name: 'test-2' },
        ],
      },
    ];

    render(<ChannelValidationErrors errors={errors} onSuggestionClick={vi.fn()} />);

    expect(screen.getByText('#general')).toBeInTheDocument();
    expect(screen.getByText(/Channel '#general' not found/)).toBeInTheDocument();
    expect(screen.getByText('#test')).toBeInTheDocument();
    expect(screen.getByText(/Multiple channels match '#test'/)).toBeInTheDocument();
  });

  it('does not show suggestions section when no suggestions', () => {
    const errors = [
      {
        type: 'not_found',
        input: '#nonexistent',
        reason: "Channel '#nonexistent' not found",
        suggestions: [],
      },
    ];

    render(<ChannelValidationErrors errors={errors} onSuggestionClick={vi.fn()} />);

    expect(screen.queryByText('Did you mean:')).not.toBeInTheDocument();
  });

  it('renders chips as clickable', () => {
    const errors = [
      {
        type: 'not_found',
        input: '#general',
        reason: "Channel '#general' not found",
        suggestions: [{ id: '123', name: 'general-chat' }],
      },
    ];

    render(<ChannelValidationErrors errors={errors} onSuggestionClick={vi.fn()} />);

    const chip = screen.getByText('#general-chat');
    expect(chip).toBeInTheDocument();
  });
});
