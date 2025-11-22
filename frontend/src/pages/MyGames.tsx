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
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../api/client';
import { GameSession, GameListResponse } from '../types';
import { GameCard } from '../components/GameCard';
import { useAuth } from '../hooks/useAuth';

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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tabValue, setTabValue] = useState(0);

  useEffect(() => {
    const fetchGames = async () => {
      if (!user) return;

      try {
        setLoading(true);
        setError(null);

        const response = await apiClient.get<GameListResponse>('/api/v1/games');
        const allGames = response.data.games;

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
      } catch (err: any) {
        console.error('Failed to fetch games:', err);
        setError(err.response?.data?.detail || 'Failed to load games. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    fetchGames();
  }, [user]);

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

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
        <Button variant="contained" onClick={() => navigate('/guilds')}>
          Create New Game
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={tabValue} onChange={handleTabChange} aria-label="game tabs">
          <Tab label={`Hosting (${hostedGames.length})`} />
          <Tab label={`Joined (${joinedGames.length})`} />
        </Tabs>
      </Box>

      <TabPanel value={tabValue} index={0}>
        {hostedGames.length === 0 ? (
          <Alert severity="info">
            You haven&apos;t hosted any games yet. Create one to get started!
          </Alert>
        ) : (
          <Box>
            {hostedGames.map((game) => (
              <GameCard key={game.id} game={game} />
            ))}
          </Box>
        )}
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
    </Container>
  );
};
