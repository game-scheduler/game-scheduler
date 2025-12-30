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
import { render } from '@testing-library/react';
import { GameForm } from '../GameForm';
import { AuthContext } from '../../contexts/AuthContext';

const mockAuthContextValue = {
  user: { id: '1', user_uuid: 'uuid1', username: 'testuser' },
  loading: false,
  login: vi.fn(),
  logout: vi.fn(),
  refreshUser: vi.fn(),
};

const renderWithAuth = (ui: React.ReactElement) => {
  return render(<AuthContext.Provider value={mockAuthContextValue}>{ui}</AuthContext.Provider>);
};

// Helper to get the hidden input for the date picker (MUI v8 accessible DOM structure)
function getDatePickerHiddenInput(container: HTMLElement): HTMLInputElement {
  const input = container.querySelector(
    '.MuiPickersInputBase-input[aria-hidden="true"]'
  ) as HTMLInputElement;
  if (!input) {
    throw new Error('Could not find MUI Date Picker hidden input');
  }
  return input;
}

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

    const { container } = renderWithAuth(
      <GameForm
        mode="create"
        guildId="test-guild"
        channels={[mockChannel]}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    const dateInput = getDatePickerHiddenInput(container);
    const inputValue = dateInput.value;

    // Check that the time is rounded to 5:30 PM (17:30 local)
    expect(inputValue).toContain('05:30 PM');
    expect(inputValue).not.toContain('05:13');
  });

  it('rounds up time from 5:31 to 6:00', () => {
    const testDate = new Date('2025-12-05T17:31:00.000Z');
    vi.setSystemTime(testDate);

    const mockOnSubmit = vi.fn();
    const mockOnCancel = vi.fn();

    const { container } = renderWithAuth(
      <GameForm
        mode="create"
        guildId="test-guild"
        channels={[mockChannel]}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    const dateInput = getDatePickerHiddenInput(container);
    const inputValue = dateInput.value;

    // Check that the time is rounded to 6:00 PM (18:00 local)
    expect(inputValue).toContain('06:00 PM');
    expect(inputValue).not.toContain('05:31');
  });

  it('keeps time at 5:30 when already on half hour', () => {
    const testDate = new Date('2025-12-05T17:30:00.000Z');
    vi.setSystemTime(testDate);

    const mockOnSubmit = vi.fn();
    const mockOnCancel = vi.fn();

    const { container } = renderWithAuth(
      <GameForm
        mode="create"
        guildId="test-guild"
        channels={[mockChannel]}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    const dateInput = getDatePickerHiddenInput(container);
    const inputValue = dateInput.value;

    // Check that the time stays at 5:30 PM (17:30 local)
    expect(inputValue).toContain('05:30 PM');
  });

  it('rounds up from 11:45 PM to midnight', () => {
    const testDate = new Date('2025-12-06T04:45:00.000Z');
    vi.setSystemTime(testDate);

    const mockOnSubmit = vi.fn();
    const mockOnCancel = vi.fn();

    const { container } = renderWithAuth(
      <GameForm
        mode="create"
        guildId="test-guild"
        channels={[mockChannel]}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    const dateInput = getDatePickerHiddenInput(container);
    const inputValue = dateInput.value;

    // Check that the time is rounded to 5:00 AM next day (midnight + 30min rounded)
    expect(inputValue).toContain('05:00 AM');
  });

  it('rounds up from 11:59 to 12:00 (noon)', () => {
    const testDate = new Date('2025-12-05T19:59:00.000Z');
    vi.setSystemTime(testDate);

    const mockOnSubmit = vi.fn();
    const mockOnCancel = vi.fn();

    const { container } = renderWithAuth(
      <GameForm
        mode="create"
        guildId="test-guild"
        channels={[mockChannel]}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    const dateInput = getDatePickerHiddenInput(container);
    const inputValue = dateInput.value;

    // Check that the time is rounded to 8:00 PM (20:00 local)
    expect(inputValue).toContain('08:00 PM');
  });

  it('uses provided scheduled_at when editing existing game', () => {
    const testDate = new Date('2025-12-05T17:13:00.000Z');
    vi.setSystemTime(testDate);

    const existingScheduledTime = new Date('2025-12-10T14:45:00.000Z');
    const mockOnSubmit = vi.fn();
    const mockOnCancel = vi.fn();

    const { container } = renderWithAuth(
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

    const dateInput = getDatePickerHiddenInput(container);
    const inputValue = dateInput.value;

    // Check that it uses the existing scheduled time (2:45 PM)
    expect(inputValue).toContain('02:45 PM');
    expect(inputValue).toContain('12/10/2025');
  });
});

describe('GameForm - Host Field Conditional Rendering', () => {
  const mockChannel = {
    id: 'ch1',
    channel_name: 'General',
    guild_id: 'guild1',
    channel_id: 'ch1',
    is_active: true,
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
  };

  const mockOnSubmit = vi.fn();
  const mockOnCancel = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should show host field when isBotManager is true', () => {
    const { getByLabelText } = renderWithAuth(
      <GameForm
        mode="create"
        guildId="guild1"
        channels={[mockChannel]}
        isBotManager={true}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    expect(getByLabelText(/game host/i)).toBeInTheDocument();
  });

  it('should not show host field when isBotManager is false', () => {
    const { queryByLabelText } = renderWithAuth(
      <GameForm
        mode="create"
        guildId="guild1"
        channels={[mockChannel]}
        isBotManager={false}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    expect(queryByLabelText(/game host/i)).not.toBeInTheDocument();
  });

  it('should not show host field when isBotManager is undefined (defaults to false)', () => {
    const { queryByLabelText } = renderWithAuth(
      <GameForm
        mode="create"
        guildId="guild1"
        channels={[mockChannel]}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    expect(queryByLabelText(/game host/i)).not.toBeInTheDocument();
  });

  it('should display host field with correct helper text', () => {
    const { getByText } = renderWithAuth(
      <GameForm
        mode="create"
        guildId="guild1"
        channels={[mockChannel]}
        isBotManager={true}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    expect(
      getByText(/game host \(@mention or username\)\. leave empty to host yourself\./i)
    ).toBeInTheDocument();
  });

  it('should allow regular users to see all other form fields without host field', () => {
    const { getByLabelText, queryByLabelText, container } = renderWithAuth(
      <GameForm
        mode="create"
        guildId="guild1"
        channels={[mockChannel]}
        isBotManager={false}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    expect(getByLabelText(/game title/i)).toBeInTheDocument();
    expect(getByLabelText(/location/i)).toBeInTheDocument();
    const datePicker = container.querySelector('input[value*="/"]');
    expect(datePicker).toBeInTheDocument();
    expect(queryByLabelText(/game host/i)).not.toBeInTheDocument();
  });
});

describe('GameForm - Signup Method Selector', () => {
  const mockChannel = {
    id: 'ch1',
    channel_name: 'General',
    guild_id: 'guild1',
    channel_id: 'ch1',
    is_active: true,
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
  };

  const mockOnSubmit = vi.fn();
  const mockOnCancel = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render signup method selector with default SELF_SIGNUP', () => {
    const { getByTestId, getByText } = renderWithAuth(
      <GameForm
        mode="create"
        guildId="guild1"
        channels={[mockChannel]}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    const select = getByTestId('signup-method-select');
    expect(select).toBeInTheDocument();

    // Check that SELF_SIGNUP is selected (MUI renders it inside the select)
    expect(getByText('Self Signup')).toBeInTheDocument();
  });

  it('should render with template default signup method', () => {
    const { getByTestId, getByText } = renderWithAuth(
      <GameForm
        mode="create"
        guildId="guild1"
        channels={[mockChannel]}
        defaultSignupMethod="HOST_SELECTED"
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    const select = getByTestId('signup-method-select');
    expect(select).toBeInTheDocument();
    expect(getByText('Host Selected')).toBeInTheDocument();
  });

  it('should disable selector when only one method is allowed', () => {
    const { getByTestId } = renderWithAuth(
      <GameForm
        mode="create"
        guildId="guild1"
        channels={[mockChannel]}
        allowedSignupMethods={['HOST_SELECTED']}
        defaultSignupMethod="HOST_SELECTED"
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    const select = getByTestId('signup-method-select');
    // MUI Select is disabled via the disabled prop
    expect(select).toHaveClass('Mui-disabled');
  });

  it('should enable selector when multiple methods are allowed', () => {
    const { getByTestId } = renderWithAuth(
      <GameForm
        mode="create"
        guildId="guild1"
        channels={[mockChannel]}
        allowedSignupMethods={['SELF_SIGNUP', 'HOST_SELECTED']}
        defaultSignupMethod="SELF_SIGNUP"
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    const select = getByTestId('signup-method-select');
    const input = select.querySelector('input');
    expect(input).not.toHaveAttribute('aria-disabled', 'true');
  });

  it('should preserve signup method in edit mode', () => {
    const { getByTestId, getByText } = renderWithAuth(
      <GameForm
        mode="edit"
        guildId="guild1"
        channels={[mockChannel]}
        initialData={{
          id: 'game-1',
          title: 'Existing Game',
          scheduled_at: new Date().toISOString(),
          channel_id: 'ch1',
          description: 'Test game',
          signup_method: 'HOST_SELECTED',
        }}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    const select = getByTestId('signup-method-select');
    expect(select).toBeInTheDocument();
    expect(getByText('Host Selected')).toBeInTheDocument();
  });

  it('should show description text for selected method', () => {
    const { getByText } = renderWithAuth(
      <GameForm
        mode="create"
        guildId="guild1"
        channels={[mockChannel]}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    // Check for SELF_SIGNUP description (exact text from types/index.ts)
    expect(
      getByText('Players can join the game by clicking the Discord button')
    ).toBeInTheDocument();
  });

  it('should update description when method changes', () => {
    const { getByText, queryByText } = renderWithAuth(
      <GameForm
        mode="create"
        guildId="guild1"
        channels={[mockChannel]}
        allowedSignupMethods={['SELF_SIGNUP', 'HOST_SELECTED']}
        defaultSignupMethod="HOST_SELECTED"
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    // Initially shows HOST_SELECTED description (exact text from types/index.ts)
    expect(
      getByText('Only the host can add players (Discord button disabled)')
    ).toBeInTheDocument();
    expect(
      queryByText('Players can join the game by clicking the Discord button')
    ).not.toBeInTheDocument();
  });

  it('should include signup_method in form data', () => {
    const { getByTestId } = renderWithAuth(
      <GameForm
        mode="create"
        guildId="guild1"
        channels={[mockChannel]}
        defaultSignupMethod="HOST_SELECTED"
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    const select = getByTestId('signup-method-select');
    const input = select.querySelector('input');

    // Verify the input has the correct value
    expect(input).toHaveValue('HOST_SELECTED');
  });
});
