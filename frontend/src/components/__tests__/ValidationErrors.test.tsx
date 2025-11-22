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
import { ValidationErrors } from '../ValidationErrors';

describe('ValidationErrors', () => {
  const mockErrors = [
    {
      input: '@nonexistent',
      reason: 'User not found in guild',
      suggestions: [],
    },
    {
      input: '@john',
      reason: 'Multiple matches found',
      suggestions: [
        { discordId: '111', username: 'johndoe', displayName: 'John Doe' },
        { discordId: '222', username: 'johnny', displayName: 'Johnny' },
      ],
    },
  ];

  it('renders all validation errors', () => {
    const onSuggestionClick = vi.fn();
    render(<ValidationErrors errors={mockErrors} onSuggestionClick={onSuggestionClick} />);

    expect(screen.getByText(/Could not resolve some @mentions/)).toBeInTheDocument();
    expect(screen.getByText(/@nonexistent/)).toBeInTheDocument();
    expect(screen.getByText(/User not found in guild/)).toBeInTheDocument();
    expect(screen.getAllByText(/@john/).length).toBeGreaterThan(0);
    expect(screen.getByText(/Multiple matches found/)).toBeInTheDocument();
  });

  it('renders suggestion chips when available', () => {
    const onSuggestionClick = vi.fn();
    render(<ValidationErrors errors={mockErrors} onSuggestionClick={onSuggestionClick} />);

    expect(screen.getByText(/@johndoe \(John Doe\)/)).toBeInTheDocument();
    expect(screen.getByText(/@johnny \(Johnny\)/)).toBeInTheDocument();
  });

  it('does not render suggestions for errors without them', () => {
    const onSuggestionClick = vi.fn();
    render(<ValidationErrors errors={mockErrors} onSuggestionClick={onSuggestionClick} />);

    const firstError = screen.getByText(/@nonexistent/).parentElement;
    expect(firstError?.textContent).not.toContain('Did you mean:');
  });

  it('calls onSuggestionClick when suggestion chip is clicked', async () => {
    const onSuggestionClick = vi.fn();
    const user = userEvent.setup();

    render(<ValidationErrors errors={mockErrors} onSuggestionClick={onSuggestionClick} />);

    const suggestion = screen.getByText(/@johndoe \(John Doe\)/);
    await user.click(suggestion);

    expect(onSuggestionClick).toHaveBeenCalledWith('@john', '@johndoe');
  });

  it('displays "Did you mean:" text when suggestions exist', () => {
    const onSuggestionClick = vi.fn();
    render(<ValidationErrors errors={mockErrors} onSuggestionClick={onSuggestionClick} />);

    expect(screen.getByText(/Did you mean:/)).toBeInTheDocument();
  });
});
