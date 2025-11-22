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
} from '@mui/material';
import { useAuth } from '../hooks/useAuth';
import { apiClient } from '../api/client';
import { Guild } from '../types';

export const GuildListPage: FC = () => {
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [guilds, setGuilds] = useState<Guild[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
        setError('Failed to load guilds. Please try again.');
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
        <Alert severity="info">
          No guilds with bot configurations found. Make sure the bot is added to your Discord
          server.
        </Alert>
      </Container>
    );
  }

  return (
    <Container sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" gutterBottom>
        My Guilds
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Select a guild to manage game sessions and configurations.
      </Typography>

      <Grid container spacing={3}>
        {guilds.map((guild) => (
          <Grid item xs={12} sm={6} md={4} key={guild.id}>
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
