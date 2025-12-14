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

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { GameForm } from '../GameForm';

describe('GameForm - getNextHalfHour', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  const mockChannel = {
    id: 'ch1',
    channel_name: 'General',
    guild_id: 'guild1',
    channel_id: 'ch1',
    is_active: true,
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
  };

  it('rounds up time from 5:13 to 5:30', () => {
    const testDate = new Date('2025-12-05T17:13:25.500Z');
    vi.setSystemTime(testDate);

    const mockOnSubmit = vi.fn();
    const mockOnCancel = vi.fn();

    render(
      <GameForm
        mode="create"
        guildId="test-guild"
        channels={[mockChannel]}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    const dateInput = screen.getByLabelText(/Scheduled Time/i);
    const inputValue = (dateInput as HTMLInputElement).value;

    // Check that the time is rounded to 5:30 PM (17:30 local)
    expect(inputValue).toContain('05:30 PM');
    expect(inputValue).not.toContain('05:13');
  });

  it('rounds up time from 5:31 to 6:00', () => {
    const testDate = new Date('2025-12-05T17:31:00.000Z');
    vi.setSystemTime(testDate);

    const mockOnSubmit = vi.fn();
    const mockOnCancel = vi.fn();

    render(
      <GameForm
        mode="create"
        guildId="test-guild"
        channels={[mockChannel]}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    const dateInput = screen.getByLabelText(/Scheduled Time/i);
    const inputValue = (dateInput as HTMLInputElement).value;

    // Check that the time is rounded to 6:00 PM (18:00 local)
    expect(inputValue).toContain('06:00 PM');
    expect(inputValue).not.toContain('05:31');
  });

  it('keeps time at 5:30 when already on half hour', () => {
    const testDate = new Date('2025-12-05T17:30:00.000Z');
    vi.setSystemTime(testDate);

    const mockOnSubmit = vi.fn();
    const mockOnCancel = vi.fn();

    render(
      <GameForm
        mode="create"
        guildId="test-guild"
        channels={[mockChannel]}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    const dateInput = screen.getByLabelText(/Scheduled Time/i);
    const inputValue = (dateInput as HTMLInputElement).value;

    // Check that the time stays at 5:30 PM (17:30 local)
    expect(inputValue).toContain('05:30 PM');
  });

  it('rounds up from 11:45 PM to midnight', () => {
    const testDate = new Date('2025-12-06T04:45:00.000Z');
    vi.setSystemTime(testDate);

    const mockOnSubmit = vi.fn();
    const mockOnCancel = vi.fn();

    render(
      <GameForm
        mode="create"
        guildId="test-guild"
        channels={[mockChannel]}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    const dateInput = screen.getByLabelText(/Scheduled Time/i);
    const inputValue = (dateInput as HTMLInputElement).value;

    // Check that the time is rounded to 5:00 AM next day (midnight + 30min rounded)
    expect(inputValue).toContain('05:00 AM');
  });

  it('rounds up from 11:59 to 12:00 (noon)', () => {
    const testDate = new Date('2025-12-05T19:59:00.000Z');
    vi.setSystemTime(testDate);

    const mockOnSubmit = vi.fn();
    const mockOnCancel = vi.fn();

    render(
      <GameForm
        mode="create"
        guildId="test-guild"
        channels={[mockChannel]}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    const dateInput = screen.getByLabelText(/Scheduled Time/i);
    const inputValue = (dateInput as HTMLInputElement).value;

    // Check that the time is rounded to 8:00 PM (20:00 local)
    expect(inputValue).toContain('08:00 PM');
  });

  it('uses provided scheduled_at when editing existing game', () => {
    const testDate = new Date('2025-12-05T17:13:00.000Z');
    vi.setSystemTime(testDate);

    const existingScheduledTime = new Date('2025-12-10T14:45:00.000Z');
    const mockOnSubmit = vi.fn();
    const mockOnCancel = vi.fn();

    render(
      <GameForm
        mode="edit"
        guildId="test-guild"
        channels={[mockChannel]}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
        initialData={{
          id: 'game-1',
          title: 'Existing Game',
          scheduled_at: existingScheduledTime.toISOString(),
          channel_id: 'ch1',
          description: 'Test game',
        }}
      />
    );

    const dateInput = screen.getByLabelText(/Scheduled Time/i);
    const inputValue = (dateInput as HTMLInputElement).value;

    // Check that it uses the existing scheduled time (2:45 PM)
    expect(inputValue).toContain('02:45 PM');
    expect(inputValue).toContain('12/10/2025');
  });
});
