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
import { render, screen, waitFor, cleanup } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router';
import { DownloadCalendar } from '../DownloadCalendar';
import { AuthContext } from '../../contexts/AuthContext';
import { CurrentUser } from '../../types';

const mockNavigate = vi.fn();

vi.mock('react-router', async () => {
  const actual = await vi.importActual('react-router');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

globalThis.fetch = vi.fn();
globalThis.URL.createObjectURL = vi.fn(() => 'blob:mock-url');
globalThis.URL.revokeObjectURL = vi.fn();

describe('DownloadCalendar', () => {
  const mockUser: CurrentUser = {
    id: 'id-123',
    user_uuid: 'user-123',
    username: 'testuser',
    discordId: 'discord-123',
    avatar: null,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  const renderWithAuth = (user: CurrentUser | null = mockUser, loading = false) => {
    const mockAuthValue = {
      user,
      login: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
      loading,
    };

    return render(
      <MemoryRouter initialEntries={['/download-calendar/game-123']}>
        <AuthContext.Provider value={mockAuthValue}>
          <Routes>
            <Route path="/download-calendar/:gameId" element={<DownloadCalendar />} />
          </Routes>
        </AuthContext.Provider>
      </MemoryRouter>
    );
  };

  it('shows loading state while authenticating', () => {
    renderWithAuth(null, true);
    expect(screen.getByText('Authenticating...')).toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('downloads calendar when authenticated', async () => {
    const mockBlob = new Blob(['calendar data'], { type: 'text/calendar' });
    const mockResponse = {
      ok: true,
      headers: {
        get: vi.fn(() => 'attachment; filename="Test-Game_2025-12-19.ics"'),
      },
      blob: vi.fn().mockResolvedValue(mockBlob),
    };

    vi.mocked(globalThis.fetch).mockResolvedValue(mockResponse as any);

    renderWithAuth(mockUser, false);

    await waitFor(() => {
      expect(screen.getByText('Downloading calendar...')).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith('/api/v1/export/game/game-123', {
        credentials: 'include',
      });
    });

    expect(globalThis.URL.createObjectURL).toHaveBeenCalledWith(mockBlob);
  });

  it('uses default filename when Content-Disposition header is missing', async () => {
    const mockBlob = new Blob(['calendar data'], { type: 'text/calendar' });
    const mockResponse = {
      ok: true,
      headers: {
        get: vi.fn(() => null),
      },
      blob: vi.fn().mockResolvedValue(mockBlob),
    };

    vi.mocked(globalThis.fetch).mockResolvedValue(mockResponse as any);

    renderWithAuth(mockUser, false);

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith('/api/v1/export/game/game-123', {
        credentials: 'include',
      });
    });

    expect(globalThis.URL.createObjectURL).toHaveBeenCalledWith(mockBlob);
  });

  it('shows permission denied error for 403 response', async () => {
    const mockResponse = {
      ok: false,
      status: 403,
    };

    vi.mocked(globalThis.fetch).mockResolvedValue(mockResponse as any);

    renderWithAuth(mockUser, false);

    await waitFor(
      () => {
        expect(
          screen.getByText('You do not have permission to download this calendar.')
        ).toBeInTheDocument();
      },
      { timeout: 3000 }
    );
  });

  it('shows not found error for 404 response', async () => {
    const mockResponse = {
      ok: false,
      status: 404,
    };

    vi.mocked(globalThis.fetch).mockResolvedValue(mockResponse as any);

    renderWithAuth(mockUser, false);

    await waitFor(
      () => {
        expect(screen.getByText('Game not found.')).toBeInTheDocument();
      },
      { timeout: 3000 }
    );
  });

  it('shows generic error for other error status codes', async () => {
    const mockResponse = {
      ok: false,
      status: 500,
    };

    vi.mocked(globalThis.fetch).mockResolvedValue(mockResponse as any);

    renderWithAuth(mockUser, false);

    await waitFor(
      () => {
        expect(screen.getByText('Failed to download calendar.')).toBeInTheDocument();
      },
      { timeout: 3000 }
    );
  });

  it('shows generic error when fetch throws exception', async () => {
    vi.mocked(globalThis.fetch).mockRejectedValue(new Error('Network error'));

    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    renderWithAuth(mockUser, false);

    await waitFor(
      () => {
        expect(
          screen.getByText('An error occurred while downloading the calendar.')
        ).toBeInTheDocument();
      },
      { timeout: 3000 }
    );

    expect(consoleErrorSpy).toHaveBeenCalledWith('Calendar download error:', expect.any(Error));

    consoleErrorSpy.mockRestore();
  });

  it('navigates to my-games when error alert is closed', async () => {
    const mockResponse = {
      ok: false,
      status: 404,
    };

    vi.mocked(globalThis.fetch).mockResolvedValue(mockResponse as any);

    renderWithAuth(mockUser, false);

    await waitFor(
      () => {
        expect(screen.getByText('Game not found.')).toBeInTheDocument();
      },
      { timeout: 3000 }
    );

    const closeButton = screen.getByRole('button', { name: /close/i });
    closeButton.click();

    expect(mockNavigate).toHaveBeenCalledWith('/my-games');
  });
});
