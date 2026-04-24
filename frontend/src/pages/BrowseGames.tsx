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
import { useParams } from 'react-router';
import { apiClient } from '../api/client';
import { GameSession, GameListResponse } from '../types';
import { GameCard } from '../components/GameCard';
import { useGameUpdates } from '../hooks/useGameUpdates';

export const BrowseGames: FC = () => {
  const { guildId } = useParams<{ guildId: string }>();
  const [games, setGames] = useState<GameSession[]>([]);
  const [channels, setChannels] = useState<{ id: string; channel_name: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedChannel, setSelectedChannel] = useState<string>('all');
  const [selectedStatus, setSelectedStatus] = useState<string>('SCHEDULED');

  const handleGameUpdate = (updatedGame: GameSession) => {
    setGames((prevGames) =>
      prevGames.map((game) => (game.id === updatedGame.id ? updatedGame : game))
    );
  };

  const handleSSEUpdate = async (gameId: string) => {
    try {
      const response = await apiClient.get<GameSession>(`/api/v1/games/${gameId}`);
      handleGameUpdate(response.data);
    } catch (err) {
      console.error('Failed to fetch updated game:', err);
    }
  };

  useGameUpdates(guildId, handleSSEUpdate);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);

        const params: any = {
          status:
            selectedStatus !== 'ALL'
              ? [selectedStatus]
              : ['SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED'],
        };

        if (guildId) {
          params.guild_id = guildId;
        }

        const gamesResponse = await apiClient.get<GameListResponse>('/api/v1/games', {
          params,
        });

        let filteredGames = gamesResponse.data.games;

        if (guildId) {
          const channelMap = new Map<string, string>();
          for (const game of filteredGames) {
            if (game.channel_name && !channelMap.has(game.channel_id)) {
              channelMap.set(game.channel_id, game.channel_name);
            }
          }
          setChannels(
            Array.from(channelMap.entries())
              .map(([id, channel_name]) => ({ id, channel_name }))
              .sort((a, b) => a.channel_name.localeCompare(b.channel_name))
          );

          if (selectedChannel !== 'all') {
            if (!channelMap.has(selectedChannel)) {
              setSelectedChannel('all');
            } else {
              filteredGames = filteredGames.filter(
                (game: GameSession) => game.channel_id === selectedChannel
              );
            }
          }
        }

        setGames(filteredGames);
      } catch (err: unknown) {
        console.error('Failed to fetch games:', err);
        setError((err as any).response?.data?.detail || 'Failed to load games. Please try again.');
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
            <GameCard key={game.id} game={game} onGameUpdate={handleGameUpdate} />
          ))}
        </Box>
      )}
    </Container>
  );
};
