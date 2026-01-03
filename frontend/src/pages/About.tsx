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

import { FC, useEffect, useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Link,
  Divider,
  CircularProgress,
  Alert,
} from '@mui/material';
import { apiClient } from '../api/client';

interface VersionInfo {
  service: string;
  git_version: string;
  api_version: string;
  api_prefix: string;
}

export const About: FC = () => {
  const [versionInfo, setVersionInfo] = useState<VersionInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchVersionInfo = async () => {
      try {
        const response = await apiClient.get<VersionInfo>('/api/v1/version');
        setVersionInfo(response.data);
      } catch (err) {
        setError('Failed to load version information');
        console.error('Error fetching version:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchVersionInfo();
  }, []);

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ maxWidth: 800, mx: 'auto' }}>
      <Typography variant="h4" component="h1" gutterBottom>
        About Discord Game Scheduler
      </Typography>

      {error && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Version Information
          </Typography>
          {versionInfo && (
            <Typography variant="body1" sx={{ mt: 2 }}>
              Version {versionInfo.git_version} (API {versionInfo.api_version})
            </Typography>
          )}
        </CardContent>
      </Card>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Copyright
          </Typography>
          <Typography variant="body2" paragraph>
            Copyright © 2025 Bret McKee (
            <Link href="mailto:bret.mckee@gmail.com" color="primary">
              bret.mckee@gmail.com
            </Link>
            )
          </Typography>
          <Divider sx={{ my: 2 }} />
          <Typography variant="body2" paragraph>
            This application is part of the Game_Scheduler project.
          </Typography>
          <Typography variant="body2">
            Source code:{' '}
            <Link
              href="https://github.com/game-scheduler/game-scheduler"
              target="_blank"
              rel="noopener noreferrer"
              color="primary"
            >
              github.com/game-scheduler/game-scheduler
            </Link>
          </Typography>
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            License
          </Typography>
          <Typography variant="body2" paragraph>
            Game_Scheduler is free software: you can redistribute it and/or modify it under the
            terms of the GNU Affero General Public License as published by the Free Software
            Foundation, either version 3 of the License, or (at your option) any later version.
          </Typography>
          <Typography variant="body2" paragraph>
            Game_Scheduler is distributed in the hope that it will be useful, but WITHOUT ANY
            WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
            PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.
          </Typography>
          <Typography variant="body2">
            You should have received a copy of the GNU Affero General Public License along with
            Game_Scheduler. If not, see{' '}
            <Link
              href="https://www.gnu.org/licenses/"
              target="_blank"
              rel="noopener noreferrer"
              color="primary"
            >
              https://www.gnu.org/licenses/
            </Link>
            .
          </Typography>
        </CardContent>
      </Card>
    </Box>
  );
};
