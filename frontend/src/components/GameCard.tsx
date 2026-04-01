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

import { FC, useState } from 'react';
import {
  Card,
  CardContent,
  CardActions,
  Typography,
  Button,
  Chip,
  Box,
  Avatar,
  CircularProgress,
  Alert,
} from '@mui/material';
import { useNavigate } from 'react-router';
import { GameSession } from '../types';
import { Time } from '../constants/time';
import { UI } from '../constants/ui';
import { useAuth } from '../hooks/useAuth';
import { apiClient } from '../api/client';

interface GameCardProps {
  game: GameSession;
  showActions?: boolean;
  onGameUpdate?: (updatedGame: GameSession) => void;
}

export const GameCard: FC<GameCardProps> = ({ game, showActions = true, onGameUpdate }) => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isParticipant = user && game.participants?.some((p) => p.user_id === user.user_uuid);

  const handleJoinGame = async (e: React.MouseEvent) => {
    e.stopPropagation();

    try {
      setActionLoading(true);
      setError(null);
      await apiClient.post(`/api/v1/games/${game.id}/join`);

      const response = await apiClient.get<GameSession>(`/api/v1/games/${game.id}`);
      if (onGameUpdate) {
        onGameUpdate(response.data);
      }
    } catch (err: unknown) {
      console.error('Failed to join game:', err);
      const response = await apiClient.get<GameSession>(`/api/v1/games/${game.id}`);
      if (onGameUpdate) {
        onGameUpdate(response.data);
      }
    } finally {
      setActionLoading(false);
    }
  };

  const handleLeaveGame = async (e: React.MouseEvent) => {
    e.stopPropagation();

    try {
      setActionLoading(true);
      setError(null);
      await apiClient.post(`/api/v1/games/${game.id}/leave`);

      const response = await apiClient.get<GameSession>(`/api/v1/games/${game.id}`);
      if (onGameUpdate) {
        onGameUpdate(response.data);
      }
    } catch (err: unknown) {
      console.error('Failed to leave game:', err);
      const response = await apiClient.get<GameSession>(`/api/v1/games/${game.id}`);
      if (onGameUpdate) {
        onGameUpdate(response.data);
      }
    } finally {
      setActionLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'SCHEDULED':
        return 'primary';
      case 'IN_PROGRESS':
        return 'success';
      case 'COMPLETED':
        return 'default';
      case 'CANCELLED':
        return 'error';
      default:
        return 'default';
    }
  };

  const formatDateTime = (isoString: string) => {
    const date = new Date(isoString);
    return date.toLocaleString(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short',
    });
  };

  const formatDuration = (minutes: number | null): string => {
    if (!minutes) return '';
    const hours = Math.floor(minutes / Time.SECONDS_PER_MINUTE);
    const remainingMinutes = minutes % Time.SECONDS_PER_MINUTE;
    if (hours > 0 && remainingMinutes > 0) {
      return `${hours}h ${remainingMinutes}m`;
    } else if (hours > 0) {
      return `${hours}h`;
    } else {
      return `${remainingMinutes}m`;
    }
  };

  const participantCount = game.participant_count || 0;
  const maxPlayers = game.max_players || UI.DEFAULT_MAX_PLAYERS;
  const playerDisplay = `${participantCount}/${maxPlayers}`;

  const truncateDescription = (
    text: string,
    maxLength: number = UI.DEFAULT_TRUNCATE_LENGTH
  ): string => {
    if (!text || text.length <= maxLength) {
      return text;
    }
    return text.substring(0, maxLength).trim() + '...';
  };

  return (
    <Card sx={{ mb: 2 }}>
      <CardContent>
        {game.host && game.host.display_name && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            <Avatar
              src={game.host.avatar_url || undefined}
              alt={game.host.display_name}
              sx={{ width: 32, height: 32 }}
            >
              {!game.host.avatar_url && game.host.display_name[0]}
            </Avatar>
            <Typography variant="subtitle2" color="text.secondary">
              Host: <strong>{game.host.display_name}</strong>
            </Typography>
          </Box>
        )}

        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
          <Typography variant="h6" component="div">
            {game.title}
          </Typography>
          <Chip label={game.status} color={getStatusColor(game.status)} size="small" />
        </Box>

        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          {truncateDescription(game.description, UI.DEFAULT_TRUNCATE_LENGTH)}
        </Typography>

        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', mb: 1 }}>
          <Typography variant="body2">
            <strong>When:</strong> {formatDateTime(game.scheduled_at)}
          </Typography>
          {(game.where_display ?? game.where) && (
            <Typography variant="body2">
              <strong>Where:</strong> {game.where_display ?? game.where}
            </Typography>
          )}
          <Typography variant="body2">
            <strong>Players:</strong> {playerDisplay}
          </Typography>
          {game.expected_duration_minutes && (
            <Typography variant="body2">
              <strong>Duration:</strong> {formatDuration(game.expected_duration_minutes)}
            </Typography>
          )}
        </Box>

        {game.rewards && (
          <Typography variant="body2" sx={{ mb: 1 }}>
            🏆 Rewards available
          </Typography>
        )}

        {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        )}
      </CardContent>

      {showActions && (
        <CardActions>
          <Button size="small" onClick={() => navigate(`/games/${game.id}`)}>
            View Details
          </Button>

          {!isParticipant && game.status === 'SCHEDULED' && (
            <Button
              size="small"
              variant="contained"
              onClick={handleJoinGame}
              disabled={actionLoading}
            >
              {actionLoading ? <CircularProgress size={20} /> : 'Join'}
            </Button>
          )}

          {isParticipant && game.status === 'SCHEDULED' && (
            <Button
              size="small"
              variant="outlined"
              color="error"
              onClick={handleLeaveGame}
              disabled={actionLoading}
            >
              {actionLoading ? <CircularProgress size={20} /> : 'Leave'}
            </Button>
          )}
        </CardActions>
      )}
    </Card>
  );
};
