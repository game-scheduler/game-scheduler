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
import { useParams, useNavigate } from 'react-router-dom';
import {
  Container,
  Typography,
  Card,
  CardContent,
  Grid,
  Button,
  Box,
  CircularProgress,
  Alert,
  Tabs,
  Tab,
  List,
  ListItem,
  ListItemText,
  ListItemButton,
} from '@mui/material';
import SettingsIcon from '@mui/icons-material/Settings';
import AddIcon from '@mui/icons-material/Add';
import { apiClient } from '../api/client';
import { Guild, Channel } from '../types';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: FC<TabPanelProps> = ({ children, value, index }) => {
  return (
    <div role="tabpanel" hidden={value !== index}>
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
};

export const GuildDashboard: FC = () => {
  const { guildId } = useParams<{ guildId: string }>();
  const navigate = useNavigate();
  const [guild, setGuild] = useState<Guild | null>(null);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tabValue, setTabValue] = useState(0);

  useEffect(() => {
    const fetchData = async () => {
      if (!guildId) return;

      try {
        setLoading(true);
        setError(null);

        const [guildResponse, channelsResponse] = await Promise.all([
          apiClient.get<Guild>(`/api/v1/guilds/${guildId}`),
          apiClient.get<Channel[]>(`/api/v1/guilds/${guildId}/channels`),
        ]);

        setGuild(guildResponse.data);
        setChannels(channelsResponse.data);
      } catch (err: any) {
        console.error('Failed to fetch guild data:', err);
        setError(err.response?.data?.detail || 'Failed to load guild data. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [guildId]);

  if (loading) {
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
        <Button sx={{ mt: 2 }} onClick={() => navigate('/guilds')}>
          Back to Guilds
        </Button>
      </Container>
    );
  }

  if (!guild) {
    return (
      <Container sx={{ mt: 4 }}>
        <Alert severity="warning">Guild not found</Alert>
        <Button sx={{ mt: 2 }} onClick={() => navigate('/guilds')}>
          Back to Guilds
        </Button>
      </Container>
    );
  }

  return (
    <Container sx={{ mt: 4, mb: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">{guild.guild_name}</Typography>
        <Button
          variant="outlined"
          startIcon={<SettingsIcon />}
          onClick={() => navigate(`/guilds/${guildId}/config`)}
        >
          Guild Settings
        </Button>
      </Box>

      <Tabs value={tabValue} onChange={(_, newValue) => setTabValue(newValue)} sx={{ mb: 2 }}>
        <Tab label="Overview" />
        <Tab label="Channels" />
        <Tab label="Games" />
      </Tabs>

      <TabPanel value={tabValue} index={0}>
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Default Settings
                </Typography>
                <List>
                  <ListItem>
                    <ListItemText primary="Max Players" secondary={guild.default_max_players} />
                  </ListItem>
                  <ListItem>
                    <ListItemText
                      primary="Reminder Times"
                      secondary={`${guild.default_reminder_minutes.join(', ')} minutes before`}
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText
                      primary="Default Rules"
                      secondary={guild.default_rules || 'Not set'}
                    />
                  </ListItem>
                </List>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Quick Actions
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <Button
                    variant="contained"
                    startIcon={<AddIcon />}
                    onClick={() => navigate(`/guilds/${guildId}/games/new`)}
                  >
                    Create New Game
                  </Button>
                  <Button variant="outlined" onClick={() => navigate(`/guilds/${guildId}/games`)}>
                    Browse All Games
                  </Button>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </TabPanel>

      <TabPanel value={tabValue} index={1}>
        <Card>
          <CardContent>
            <Box
              sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}
            >
              <Typography variant="h6">Configured Channels</Typography>
            </Box>

            {channels.length === 0 ? (
              <Alert severity="info">
                No channels configured yet. Channels will be created automatically when you post
                your first game.
              </Alert>
            ) : (
              <List>
                {channels.map((channel) => (
                  <ListItemButton
                    key={channel.id}
                    onClick={() => navigate(`/channels/${channel.id}/config`)}
                  >
                    <ListItemText
                      primary={channel.channel_name}
                      secondary={
                        <>
                          {channel.game_category && `Category: ${channel.game_category} • `}
                          {channel.is_active ? 'Active' : 'Inactive'}
                          {channel.max_players !== null && ` • Max: ${channel.max_players}`}
                        </>
                      }
                    />
                  </ListItemButton>
                ))}
              </List>
            )}
          </CardContent>
        </Card>
      </TabPanel>

      <TabPanel value={tabValue} index={2}>
        <Alert severity="info">Game browsing will be implemented in the next task.</Alert>
        <Button
          sx={{ mt: 2 }}
          variant="contained"
          onClick={() => navigate(`/guilds/${guildId}/games`)}
        >
          Browse Games
        </Button>
      </TabPanel>
    </Container>
  );
};
