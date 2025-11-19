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


import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { InheritancePreview } from '../InheritancePreview';

describe('InheritancePreview', () => {
  it('renders label and value correctly', () => {
    render(
      <InheritancePreview
        label="Max Players"
        value={10}
        inherited={false}
      />
    );

    expect(screen.getByText(/Max Players:/)).toBeInTheDocument();
    expect(screen.getByText('10')).toBeInTheDocument();
  });

  it('displays inherited indicator when inherited is true', () => {
    render(
      <InheritancePreview
        label="Max Players"
        value={10}
        inherited={true}
        inheritedFrom="guild"
      />
    );

    expect(screen.getByText(/Inherited from guild/)).toBeInTheDocument();
  });

  it('does not display inherited indicator when inherited is false', () => {
    render(
      <InheritancePreview
        label="Max Players"
        value={10}
        inherited={false}
      />
    );

    expect(screen.queryByText(/Inherited from/)).not.toBeInTheDocument();
  });

  it('formats array values with commas', () => {
    render(
      <InheritancePreview
        label="Reminder Times"
        value={[60, 15, 5]}
        inherited={false}
      />
    );

    expect(screen.getByText('60, 15, 5')).toBeInTheDocument();
  });

  it('displays "Not set" for null values', () => {
    render(
      <InheritancePreview
        label="Rules"
        value={null}
        inherited={false}
      />
    );

    expect(screen.getByText('Not set')).toBeInTheDocument();
  });
});
