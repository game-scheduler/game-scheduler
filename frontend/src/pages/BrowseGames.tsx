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
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  CircularProgress,
  Alert,
  SelectChangeEvent,
} from '@mui/material';
import { useParams } from 'react-router-dom';
import { apiClient } from '../api/client';
import { GameSession, Channel, GameListResponse } from '../types';
import { GameCard } from '../components/GameCard';

export const BrowseGames: FC = () => {
  const { guildId } = useParams<{ guildId: string }>();
  const [games, setGames] = useState<GameSession[]>([]);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedChannel, setSelectedChannel] = useState<string>('all');
  const [selectedStatus, setSelectedStatus] = useState<string>('SCHEDULED');

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);

        const params: any = {
          status: selectedStatus !== 'ALL' ? selectedStatus : undefined,
        };

        if (guildId) {
          params.guild_id = guildId;
        }

        const gamesResponse = await apiClient.get<GameListResponse>('/api/v1/games', {
          params,
        });

        let filteredGames = gamesResponse.data.games;

        if (guildId) {
          const channelsResponse = await apiClient.get<Channel[]>(
            `/api/v1/guilds/${guildId}/channels`
          );
          setChannels(channelsResponse.data);

          if (selectedChannel !== 'all') {
            filteredGames = filteredGames.filter(
              (game: GameSession) => game.channel_id === selectedChannel
            );
          }
        }

        setGames(filteredGames);
      } catch (err: any) {
        console.error('Failed to fetch games:', err);
        setError(err.response?.data?.detail || 'Failed to load games. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [guildId, selectedChannel, selectedStatus]);

  const handleChannelChange = (event: SelectChangeEvent) => {
    setSelectedChannel(event.target.value);
  };

  const handleStatusChange = (event: SelectChangeEvent) => {
    setSelectedStatus(event.target.value);
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
      <Typography variant="h4" gutterBottom>
        Browse Games
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
        <FormControl sx={{ minWidth: 200 }}>
          <InputLabel>Channel</InputLabel>
          <Select value={selectedChannel} onChange={handleChannelChange} label="Channel">
            <MenuItem value="all">All Channels</MenuItem>
            {channels.map((channel) => (
              <MenuItem key={channel.id} value={channel.id}>
                {channel.channel_name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <FormControl sx={{ minWidth: 200 }}>
          <InputLabel>Status</InputLabel>
          <Select value={selectedStatus} onChange={handleStatusChange} label="Status">
            <MenuItem value="ALL">All</MenuItem>
            <MenuItem value="SCHEDULED">Scheduled</MenuItem>
            <MenuItem value="IN_PROGRESS">In Progress</MenuItem>
            <MenuItem value="COMPLETED">Completed</MenuItem>
            <MenuItem value="CANCELLED">Cancelled</MenuItem>
          </Select>
        </FormControl>
      </Box>

      {games.length === 0 ? (
        <Alert severity="info">No games found with the selected filters.</Alert>
      ) : (
        <Box>
          {games.map((game) => (
            <GameCard key={game.id} game={game} />
          ))}
        </Box>
      )}
    </Container>
  );
};
