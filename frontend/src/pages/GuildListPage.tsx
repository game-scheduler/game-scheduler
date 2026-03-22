// Copyright 2025-2026 Bret McKee
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in all
// copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.

import { FC, useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import {
  Container,
  Typography,
  Card,
  CardContent,
  CardActionArea,
  Grid,
  Avatar,
  Box,
  CircularProgress,
  Alert,
  Button,
  Switch,
  FormControlLabel,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import { useAuth } from '../hooks/useAuth';
import { toggleMaintainerMode, refreshMaintainers } from '../api/maintainers';
import { apiClient } from '../api/client';
import { syncUserGuilds, GuildSyncResponse } from '../api/guilds';
import { Guild } from '../types';

export const GuildListPage: FC = () => {
  const { user, loading: authLoading, refreshUser } = useAuth();
  const navigate = useNavigate();
  const [guilds, setGuilds] = useState<Guild[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const [confirmRefreshOpen, setConfirmRefreshOpen] = useState(false);

  const handleToggleMaintainer = async () => {
    try {
      await toggleMaintainerMode();
      await refreshUser();
    } catch (err: any) {
      console.error('Failed to toggle maintainer mode:', err);
      setError(err.response?.data?.detail || 'Failed to toggle maintainer mode.');
    }
  };

  const handleConfirmRefreshMaintainers = async () => {
    setConfirmRefreshOpen(false);
    try {
      await refreshMaintainers();
      await refreshUser();
    } catch (err: any) {
      console.error('Failed to refresh maintainers:', err);
      setError(err.response?.data?.detail || 'Failed to refresh maintainers.');
    }
  };

  const handleSyncGuilds = async () => {
    try {
      setSyncing(true);
      setSyncMessage(null);
      setError(null);

      const result: GuildSyncResponse = await syncUserGuilds();

      if (result.new_guilds > 0 || result.new_channels > 0) {
        const messageParts: string[] = [];
        if (result.new_guilds > 0) {
          messageParts.push(`${result.new_guilds} new server${result.new_guilds > 1 ? 's' : ''}`);
        }
        if (result.new_channels > 0) {
          messageParts.push(
            `${result.new_channels} new channel${result.new_channels > 1 ? 's' : ''}`
          );
        }
        setSyncMessage(`Synced ${messageParts.join(', ')}`);
        // Refresh the guilds list
        const response = await apiClient.get<{ guilds: Guild[] }>('/api/v1/guilds');
        setGuilds(response.data.guilds);
      } else {
        setSyncMessage('All servers and channels are already synced');
      }
    } catch (err: any) {
      console.error('Failed to sync guilds:', err);
      setError(err.response?.data?.detail || 'Failed to sync servers. Please try again.');
    } finally {
      setSyncing(false);
    }
  };

  useEffect(() => {
    const fetchGuilds = async () => {
      if (!user) {
        return;
      }

      try {
        setLoading(true);
        setError(null);

        const response = await apiClient.get<{ guilds: Guild[] }>('/api/v1/guilds');
        setGuilds(response.data.guilds);
      } catch (err) {
        console.error('Failed to fetch guilds:', err);
        setError('Failed to load servers. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    if (!authLoading) {
      fetchGuilds();
    }
  }, [user, authLoading]);

  if (authLoading || loading) {
    return (
      <Container sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Container>
    );
  }

  if (error) {
    return (
      <Container sx={{ mt: 4 }}>
        <Alert severity="error">{error}</Alert>
      </Container>
    );
  }

  if (guilds.length === 0) {
    return (
      <Container sx={{ mt: 4 }}>
        <Alert severity="info" sx={{ mb: 2 }}>
          No servers with bot configurations found. Make sure the bot is added to your Discord
          server.
        </Alert>
        <Button
          variant="contained"
          startIcon={<RefreshIcon />}
          onClick={handleSyncGuilds}
          disabled={syncing}
        >
          {syncing ? 'Syncing...' : 'Sync Guilds'}
        </Button>
        {syncMessage && (
          <Alert severity="success" sx={{ mt: 2 }} onClose={() => setSyncMessage(null)}>
            {syncMessage}
          </Alert>
        )}
      </Container>
    );
  }

  return (
    <Container sx={{ mt: 4, mb: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" gutterBottom>
            {user?.is_maintainer ? 'All Servers (Maintainer Mode)' : 'Your Servers'}
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Select a server to manage game sessions and configurations.
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 1 }}>
          {user?.can_be_maintainer && (
            <FormControlLabel
              control={<Switch checked={!!user?.is_maintainer} onChange={handleToggleMaintainer} />}
              label="Maintainer Mode"
            />
          )}
          {user?.is_maintainer && (
            <Button variant="outlined" color="warning" onClick={() => setConfirmRefreshOpen(true)}>
              Refresh Maintainers
            </Button>
          )}
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={handleSyncGuilds}
            disabled={syncing}
          >
            {syncing ? 'Syncing...' : 'Sync Guilds'}
          </Button>
        </Box>
      </Box>

      <Dialog open={confirmRefreshOpen} onClose={() => setConfirmRefreshOpen(false)}>
        <DialogTitle>Refresh Maintainers</DialogTitle>
        <DialogContent>
          <DialogContentText>
            This will refresh the maintainer list and log out all other elevated maintainers.
            Continue?
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmRefreshOpen(false)}>Cancel</Button>
          <Button onClick={handleConfirmRefreshMaintainers} color="warning" autoFocus>
            Confirm
          </Button>
        </DialogActions>
      </Dialog>

      {syncMessage && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSyncMessage(null)}>
          {syncMessage}
        </Alert>
      )}

      <Grid container spacing={3}>
        {guilds.map((guild) => (
          <Grid size={{ xs: 12, sm: 6, md: 4 }} key={guild.id}>
            <Card>
              <CardActionArea onClick={() => navigate(`/guilds/${guild.id}`)}>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <Avatar sx={{ width: 56, height: 56 }}>
                      {guild.guild_name.charAt(0).toUpperCase()}
                    </Avatar>
                    <Box>
                      <Typography variant="h6">{guild.guild_name}</Typography>
                    </Box>
                  </Box>
                </CardContent>
              </CardActionArea>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Container>
  );
};
