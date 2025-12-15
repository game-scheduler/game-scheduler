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
import { useParams, useNavigate } from 'react-router';
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
} from '@mui/material';
import SettingsIcon from '@mui/icons-material/Settings';
import AddIcon from '@mui/icons-material/Add';
import CategoryIcon from '@mui/icons-material/Category';
import { apiClient } from '../api/client';
import { Guild } from '../types';
import { canUserCreateGames } from '../utils/permissions';

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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tabValue, setTabValue] = useState(0);
  const [isManager, setIsManager] = useState(false);
  const [canCreateGames, setCanCreateGames] = useState(false);

  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    if (newValue === 1) {
      // Games tab - navigate to games page
      navigate(`/guilds/${guildId}/games`);
    } else {
      setTabValue(newValue);
    }
  };

  useEffect(() => {
    const fetchData = async () => {
      if (!guildId) return;

      try {
        setLoading(true);
        setError(null);

        const guildResponse = await apiClient.get<Guild>(`/api/v1/guilds/${guildId}`);

        setGuild(guildResponse.data);

        // Try to fetch config to determine if user is a manager
        try {
          await apiClient.get(`/api/v1/guilds/${guildId}/config`);
          setIsManager(true);
        } catch {
          // User is not a manager (403) or other error
          setIsManager(false);
        }

        // Check if user can create games by fetching templates
        setCanCreateGames(await canUserCreateGames(guildId));
      } catch (err: unknown) {
        console.error('Failed to fetch guild data:', err);
        setError(
          (err as any).response?.data?.detail || 'Failed to load server data. Please try again.'
        );
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
          Back to Servers
        </Button>
      </Container>
    );
  }

  if (!guild) {
    return (
      <Container sx={{ mt: 4 }}>
        <Alert severity="warning">Server not found</Alert>
        <Button sx={{ mt: 2 }} onClick={() => navigate('/guilds')}>
          Back to Servers
        </Button>
      </Container>
    );
  }

  return (
    <Container sx={{ mt: 4, mb: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">{guild.guild_name}</Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          {isManager && (
            <>
              <Button
                variant="outlined"
                startIcon={<CategoryIcon />}
                onClick={() => navigate(`/guilds/${guildId}/templates`)}
              >
                Templates
              </Button>
              <Button
                variant="outlined"
                startIcon={<SettingsIcon />}
                onClick={() => navigate(`/guilds/${guildId}/config`)}
              >
                Settings
              </Button>
            </>
          )}
        </Box>
      </Box>

      <Tabs value={tabValue} onChange={handleTabChange} sx={{ mb: 2 }}>
        <Tab label="Overview" />
        <Tab label="Games" />
      </Tabs>

      <TabPanel value={tabValue} index={0}>
        <Grid container spacing={3}>
          <Grid size={{ xs: 12, md: 6 }}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Quick Actions
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  {canCreateGames && (
                    <Button
                      variant="contained"
                      startIcon={<AddIcon />}
                      onClick={() => navigate(`/guilds/${guildId}/games/new`)}
                    >
                      Create New Game
                    </Button>
                  )}
                  <Button variant="outlined" onClick={() => navigate(`/guilds/${guildId}/games`)}>
                    Browse All Games
                  </Button>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </TabPanel>
    </Container>
  );
};
