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
      console.log('=== LOGIN DEBUG START ===');
      console.log('Initiating login request to:', '/api/v1/auth/login');
      console.log('Redirect URI:', REDIRECT_URI);
      console.log('API Base URL:', apiClient.defaults.baseURL);
      
      const response = await apiClient.get('/api/v1/auth/login', {
        params: { redirect_uri: REDIRECT_URI }
      });
      
      console.log('Login response status:', response.status);
      console.log('Login response headers:', response.headers);
      console.log('Login response data:', response.data);
      console.log('Response data type:', typeof response.data);
      console.log('Response data keys:', Object.keys(response.data || {}));
      
      const { authorization_url, state } = response.data;
      
      console.log('Extracted authorization_url:', authorization_url);
      console.log('Extracted state:', state);
      
      if (!authorization_url || !state) {
        throw new Error('Invalid response: missing authorization_url or state');
      }
      
      // Store state in sessionStorage for CSRF validation
      sessionStorage.setItem('oauth_state', state);
      
      console.log('Redirecting to Discord OAuth...');
      console.log('=== LOGIN DEBUG END ===');
      // Redirect to Discord OAuth2 authorization page
      window.location.href = authorization_url;
    } catch (err: any) {
      console.error('=== LOGIN ERROR START ===');
      console.error('Login initiation failed:', err);
      console.error('Error type:', typeof err);
      console.error('Error constructor:', err?.constructor?.name);
      console.error('Error string:', String(err));
      console.error('Error JSON:', JSON.stringify(err, Object.getOwnPropertyNames(err), 2));
      console.error('Error response:', err.response);
      console.error('Error response status:', err.response?.status);
      console.error('Error response data:', err.response?.data);
      console.error('Error message:', err.message);
      console.error('Error stack:', err.stack);
      console.error('=== LOGIN ERROR END ===');
      
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to initiate login. Please try again.';
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
