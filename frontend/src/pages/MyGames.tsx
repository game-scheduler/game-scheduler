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

import { FC, useState, useEffect } from 'react';
import {
  Container,
  Typography,
  Box,
  Tabs,
  Tab,
  CircularProgress,
  Alert,
  Button,
} from '@mui/material';
import { useNavigate } from 'react-router';
import { apiClient } from '../api/client';
import { GameSession, GameListResponse, Guild } from '../types';
import { GameCard } from '../components/GameCard';
import { useAuth } from '../hooks/useAuth';
import { ServerSelectionDialog } from '../components/ServerSelectionDialog';
import { canUserCreateGames } from '../utils/permissions';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`games-tabpanel-${index}`}
      aria-labelledby={`games-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

export const MyGames: FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [hostedGames, setHostedGames] = useState<GameSession[]>([]);
  const [joinedGames, setJoinedGames] = useState<GameSession[]>([]);
  const [guilds, setGuilds] = useState<Guild[]>([]);
  const [guildsWithTemplates, setGuildsWithTemplates] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tabValue, setTabValue] = useState(0);
  const [serverDialogOpen, setServerDialogOpen] = useState(false);

  useEffect(() => {
    const fetchGames = async () => {
      if (!user) return;

      try {
        setLoading(true);
        setError(null);

        const [gamesResponse, guildsResponse] = await Promise.all([
          apiClient.get<GameListResponse>('/api/v1/games'),
          apiClient.get<{ guilds: Guild[] }>('/api/v1/guilds'),
        ]);

        const allGames = gamesResponse.data.games;

        const hosted = allGames.filter(
          (game: GameSession) => game.host?.user_id === user.user_uuid
        );
        const joined = allGames.filter(
          (game: GameSession) =>
            game.host?.user_id !== user.user_uuid &&
            game.participants?.some((p) => p.user_id === user.user_uuid)
        );

        setHostedGames(hosted);
        setJoinedGames(joined);
        setGuilds(guildsResponse.data.guilds);

        // Check which guilds have accessible templates
        const guildsWithAccess = new Set<string>();
        await Promise.all(
          guildsResponse.data.guilds.map(async (guild) => {
            if (await canUserCreateGames(guild.id)) {
              guildsWithAccess.add(guild.id);
            }
          })
        );
        setGuildsWithTemplates(guildsWithAccess);
      } catch (err: unknown) {
        console.error('Failed to fetch games:', err);
        setError((err as any).response?.data?.detail || 'Failed to load games. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    fetchGames();
  }, [user]);

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleCreateGame = () => {
    const availableGuilds = guilds.filter((guild) => guildsWithTemplates.has(guild.id));

    if (availableGuilds.length === 1 && availableGuilds[0]) {
      navigate(`/guilds/${availableGuilds[0].id}/games/new`);
    } else {
      setServerDialogOpen(true);
    }
  };

  const handleServerSelect = (guild: Guild) => {
    setServerDialogOpen(false);
    navigate(`/guilds/${guild.id}/games/new`);
  };

  const availableGuilds = guilds.filter((guild) => guildsWithTemplates.has(guild.id));
  const canCreateGames = availableGuilds.length > 0;

  if (loading) {
    return (
      <Container>
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
          <CircularProgress />
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="h4" gutterBottom>
          My Games
        </Typography>
        {canCreateGames && (
          <Button variant="contained" onClick={handleCreateGame}>
            Create New Game
          </Button>
        )}
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {hostedGames.length > 0 ? (
        <>
          <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <Tabs value={tabValue} onChange={handleTabChange} aria-label="game tabs">
              <Tab label={`Hosting (${hostedGames.length})`} />
              <Tab label={`Joined (${joinedGames.length})`} />
            </Tabs>
          </Box>

          <TabPanel value={tabValue} index={0}>
            <Box>
              {hostedGames.map((game) => (
                <GameCard key={game.id} game={game} />
              ))}
            </Box>
          </TabPanel>

          <TabPanel value={tabValue} index={1}>
            {joinedGames.length === 0 ? (
              <Alert severity="info">
                You haven&apos;t joined any games yet. Browse games to find one to join!
              </Alert>
            ) : (
              <Box>
                {joinedGames.map((game) => (
                  <GameCard key={game.id} game={game} />
                ))}
              </Box>
            )}
          </TabPanel>
        </>
      ) : (
        <Box>
          {joinedGames.length === 0 ? (
            <Alert severity="info">No games to show</Alert>
          ) : (
            <Box>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Joined Games
              </Typography>
              {joinedGames.map((game) => (
                <GameCard key={game.id} game={game} />
              ))}
            </Box>
          )}
        </Box>
      )}

      <ServerSelectionDialog
        open={serverDialogOpen}
        onClose={() => setServerDialogOpen(false)}
        guilds={availableGuilds}
        onSelect={handleServerSelect}
      />
    </Container>
  );
};
