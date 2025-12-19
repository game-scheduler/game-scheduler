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

import { FC, useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router';
import { Box, CircularProgress, Typography, Alert } from '@mui/material';
import { useAuth } from '../hooks/useAuth';

export const DownloadCalendar: FC = () => {
  const { gameId } = useParams<{ gameId: string }>();
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const hasDownloaded = useRef(false);

  const downloadCalendar = async () => {
    setDownloading(true);
    try {
      const response = await fetch(`/api/v1/export/game/${gameId}`, {
        credentials: 'include',
      });

      if (!response.ok) {
        if (response.status === 403) {
          setError('You do not have permission to download this calendar.');
        } else if (response.status === 404) {
          setError('Game not found.');
        } else {
          setError('Failed to download calendar.');
        }
        return;
      }

      const contentDisposition = response.headers.get('Content-Disposition');
      const filenameMatch = contentDisposition?.match(/filename="?(.+)"?/i);
      const filename = filenameMatch?.[1] || `game-${gameId}.ics`;

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);

      setTimeout(() => navigate('/my-games'), 1000);
    } catch (err) {
      setError('An error occurred while downloading the calendar.');
      console.error('Calendar download error:', err);
    } finally {
      setDownloading(false);
    }
  };

  useEffect(() => {
    // Prevent duplicate downloads (React StrictMode runs effects twice)
    if (hasDownloaded.current) return;

    if (!authLoading && user && gameId && !downloading) {
      hasDownloaded.current = true;
      downloadCalendar();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, authLoading, gameId]);

  if (authLoading || downloading) {
    return (
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100vh',
          gap: 2,
        }}
      >
        <CircularProgress />
        <Typography variant="body1">
          {authLoading ? 'Authenticating...' : 'Downloading calendar...'}
        </Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100vh',
          p: 3,
        }}
      >
        <Alert severity="error" onClose={() => navigate('/my-games')}>
          {error}
        </Alert>
      </Box>
    );
  }

  return null;
};
