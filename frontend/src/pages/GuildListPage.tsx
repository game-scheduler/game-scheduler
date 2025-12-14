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
import { useNavigate } from 'react-router-dom';
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
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import { useAuth } from '../hooks/useAuth';
import { apiClient } from '../api/client';
import { syncUserGuilds, GuildSyncResponse } from '../api/guilds';
import { Guild } from '../types';

export const GuildListPage: FC = () => {
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [guilds, setGuilds] = useState<Guild[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);

  const handleSyncGuilds = async () => {
    try {
      setSyncing(true);
      setSyncMessage(null);
      setError(null);

      const result: GuildSyncResponse = await syncUserGuilds();

      if (result.new_guilds > 0 || result.new_channels > 0) {
        setSyncMessage(
          `Synced ${result.new_guilds} new server(s) and ${result.new_channels} new channel(s)`
        );
        // Refresh the guilds list
        const response = await apiClient.get<{ guilds: Guild[] }>('/api/v1/guilds');
        setGuilds(response.data.guilds);
      } else {
        setSyncMessage('All servers are already synced');
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
          {syncing ? 'Syncing...' : 'Refresh Servers'}
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
            My Servers
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Select a server to manage game sessions and configurations.
          </Typography>
        </Box>
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={handleSyncGuilds}
          disabled={syncing}
        >
          {syncing ? 'Syncing...' : 'Refresh Servers'}
        </Button>
      </Box>

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
