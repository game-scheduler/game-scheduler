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
import { MentionChip } from '../MentionChip';

describe('MentionChip', () => {
  it('renders username and display name correctly', () => {
    const onClick = vi.fn();
    render(<MentionChip username="johndoe" displayName="John Doe" onClick={onClick} />);

    expect(screen.getByText(/@johndoe \(John Doe\)/)).toBeInTheDocument();
  });

  it('calls onClick when clicked', async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();

    render(<MentionChip username="johndoe" displayName="John Doe" onClick={onClick} />);

    const chip = screen.getByText(/@johndoe \(John Doe\)/);
    await user.click(chip);

    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('renders as a clickable chip', () => {
    const onClick = vi.fn();
    render(<MentionChip username="johndoe" displayName="John Doe" onClick={onClick} />);

    const chip = screen.getByText(/@johndoe \(John Doe\)/);
    expect(chip).toBeVisible();
  });
});
