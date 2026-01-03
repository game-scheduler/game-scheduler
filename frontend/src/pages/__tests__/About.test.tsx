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

import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { About } from '../About';
import { apiClient } from '../../api/client';

vi.mock('../../api/client');

describe('About', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockVersionInfo = {
    service: 'api',
    git_version: '0.0.1.dev478+gd128f6a',
    api_version: '1.0.0',
    api_prefix: '/api/v1',
  };

  it('displays loading state initially', () => {
    vi.mocked(apiClient.get).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    render(<About />);

    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('fetches and displays version information', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockVersionInfo });

    render(<About />);

    await waitFor(() => {
      expect(
        screen.getByText(/Version 0\.0\.1\.dev478\+gd128f6a \(API 1\.0\.0\)/)
      ).toBeInTheDocument();
    });
  });

  it('calls /api/v1/version endpoint', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockVersionInfo });

    render(<About />);

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/version');
    });
  });

  it('displays error message when fetch fails', async () => {
    vi.mocked(apiClient.get).mockRejectedValue(new Error('Network error'));

    render(<About />);

    await waitFor(() => {
      expect(screen.getByText('Failed to load version information')).toBeInTheDocument();
    });
  });

  it('displays copyright information', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockVersionInfo });

    render(<About />);

    await waitFor(() => {
      expect(screen.getByText(/Copyright © 2025 Bret McKee/)).toBeInTheDocument();
    });

    expect(screen.getByText('bret.mckee@gmail.com')).toBeInTheDocument();
  });

  it('displays license information', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockVersionInfo });

    render(<About />);

    await waitFor(() => {
      const licenseElements = screen.getAllByText(/GNU Affero General Public License/);
      expect(licenseElements.length).toBeGreaterThan(0);
    });

    expect(screen.getByText(/version 3 of the License/)).toBeInTheDocument();
  });

  it('includes link to GitHub repository', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockVersionInfo });

    render(<About />);

    await waitFor(() => {
      const link = screen.getByRole('link', { name: /game-scheduler/ });
      expect(link).toHaveAttribute('href', 'https://github.com/game-scheduler/game-scheduler');
    });
  });

  it('includes link to license text', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockVersionInfo });

    render(<About />);

    await waitFor(() => {
      const link = screen.getByRole('link', { name: /gnu.org/ });
      expect(link).toHaveAttribute('href', 'https://www.gnu.org/licenses/');
    });
  });

  it('displays version in correct format', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockVersionInfo });

    render(<About />);

    await waitFor(() => {
      expect(screen.getByText(/Version .+ \(API .+\)/)).toBeInTheDocument();
    });
  });

  it('shows warning alert on error but still displays other content', async () => {
    vi.mocked(apiClient.get).mockRejectedValue(new Error('Network error'));

    render(<About />);

    await waitFor(() => {
      expect(screen.getByText('Failed to load version information')).toBeInTheDocument();
    });

    // Other content should still be visible
    expect(screen.getByText('Copyright')).toBeInTheDocument();
    expect(screen.getByText('License')).toBeInTheDocument();
  });

  it('handles empty version response gracefully', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        service: 'api',
        git_version: '',
        api_version: '',
        api_prefix: '/api/v1',
      },
    });

    render(<About />);

    await waitFor(() => {
      expect(screen.getByText('Version Information')).toBeInTheDocument();
    });

    // Should not crash with empty versions - checking for content containing "Version" and "API" in parentheses
    expect(
      screen.getByText((content, element) => {
        return element?.tagName === 'P' && /Version.*\(API.*\)/.test(content);
      })
    ).toBeInTheDocument();
  });

  it('displays page title', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockVersionInfo });

    render(<About />);

    await waitFor(() => {
      expect(
        screen.getByRole('heading', { name: 'About Discord Game Scheduler' })
      ).toBeInTheDocument();
    });
  });

  it('displays all main sections', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockVersionInfo });

    render(<About />);

    await waitFor(() => {
      expect(screen.getByText('Version Information')).toBeInTheDocument();
    });

    expect(screen.getByText('Copyright')).toBeInTheDocument();
    expect(screen.getByText('License')).toBeInTheDocument();
  });
});
