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

import { FC, useState } from 'react';
import { Button, CircularProgress } from '@mui/material';
import DownloadIcon from '@mui/icons-material/Download';
import axios from 'axios';

interface ExportButtonProps {
  gameId: string;
}

export const ExportButton: FC<ExportButtonProps> = ({ gameId }) => {
  const [loading, setLoading] = useState(false);

  const downloadCalendar = async () => {
    setLoading(true);

    try {
      const url = `/api/v1/export/game/${gameId}`;

      const response = await axios.get(url, {
        responseType: 'blob',
        withCredentials: true,
      });

      // Extract filename from Content-Disposition header, fallback to generated name
      const contentDisposition = response.headers['content-disposition'];
      let filename = `game-${gameId}.ics`;
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename=([^;]+)/);
        if (filenameMatch) {
          filename = filenameMatch[1].trim();
        }
      }

      const blob = new Blob([response.data], { type: 'text/calendar' });
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
    } catch (error) {
      console.error('Failed to export calendar:', error);
      const errorMessage =
        (error as any).response?.status === 403
          ? 'You must be the host or a participant to export this game.'
          : 'Failed to export calendar. Please try again.';
      alert(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Button
      variant="outlined"
      onClick={downloadCalendar}
      disabled={loading}
      startIcon={loading ? <CircularProgress size={20} /> : <DownloadIcon />}
    >
      Export to Calendar
    </Button>
  );
};
