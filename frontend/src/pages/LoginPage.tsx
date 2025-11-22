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
import { Box, Button, Container, Typography, Paper, Alert } from '@mui/material';
import { apiClient } from '../api/client';

const REDIRECT_URI = `${window.location.origin}/auth/callback`;

export const LoginPage: FC = () => {
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.get('/api/v1/auth/login', {
        params: { redirect_uri: REDIRECT_URI },
      });

      const { authorization_url, state } = response.data;

      if (!authorization_url || !state) {
        throw new Error('Invalid response: missing authorization_url or state');
      }

      // Store state in sessionStorage for CSRF validation
      sessionStorage.setItem('oauth_state', state);

      // Redirect to Discord OAuth2 authorization page
      window.location.href = authorization_url;
    } catch (err: unknown) {
      console.error('Login initiation failed:', err);

      const errorMessage =
        err instanceof Error ? err.message : 'Failed to initiate login. Please try again.';
      setError(errorMessage);
      setLoading(false);
    }
  };

  return (
    <Container maxWidth="sm">
      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', mt: 8 }}>
        <Paper sx={{ p: 4, width: '100%', textAlign: 'center' }}>
          <Typography variant="h4" component="h1" gutterBottom>
            Welcome to Discord Game Scheduler
          </Typography>
          <Typography variant="body1" color="text.secondary" paragraph>
            Sign in with your Discord account to get started
          </Typography>

          {error && (
            <Alert severity="error" sx={{ mt: 2, mb: 2 }}>
              {error}
            </Alert>
          )}

          <Button
            variant="contained"
            size="large"
            onClick={handleLogin}
            disabled={loading}
            sx={{ mt: 2 }}
          >
            {loading ? 'Connecting to Discord...' : 'Login with Discord'}
          </Button>
        </Paper>
      </Box>
    </Container>
  );
};
