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
  Button,
  CircularProgress,
  Alert,
  Paper,
  Chip,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import { useParams, useNavigate } from 'react-router-dom';
import { apiClient } from '../api/client';
import { GameSession } from '../types';
import { ParticipantList } from '../components/ParticipantList';
import { useAuth } from '../hooks/useAuth';

export const GameDetails: FC = () => {
  const { gameId } = useParams<{ gameId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [game, setGame] = useState<GameSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);

  useEffect(() => {
    const fetchGame = async () => {
      if (!gameId) return;

      try {
        setLoading(true);
        setError(null);
        const response = await apiClient.get<GameSession>(`/api/v1/games/${gameId}`);
        setGame(response.data);
      } catch (err: any) {
        console.error('Failed to fetch game:', err);
        setError(
          err.response?.data?.detail || 'Failed to load game. Please try again.'
        );
      } finally {
        setLoading(false);
      }
    };

    fetchGame();
  }, [gameId]);

  const handleJoinGame = async () => {
    if (!gameId) return;

    try {
      setActionLoading(true);
      setError(null);
      await apiClient.post(`/api/v1/games/${gameId}/join`);
      
      const response = await apiClient.get<GameSession>(`/api/v1/games/${gameId}`);
      setGame(response.data);
    } catch (err: any) {
      console.error('Failed to join game:', err);
      setError(
        err.response?.data?.detail || 'Failed to join game. Please try again.'
      );
    } finally {
      setActionLoading(false);
    }
  };

  const handleLeaveGame = async () => {
    if (!gameId) return;

    try {
      setActionLoading(true);
      setError(null);
      await apiClient.post(`/api/v1/games/${gameId}/leave`);
      
      const response = await apiClient.get<GameSession>(`/api/v1/games/${gameId}`);
      setGame(response.data);
    } catch (err: any) {
      console.error('Failed to leave game:', err);
      setError(
        err.response?.data?.detail || 'Failed to leave game. Please try again.'
      );
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancelGame = async () => {
    if (!gameId) return;

    try {
      setActionLoading(true);
      setError(null);
      await apiClient.delete(`/api/v1/games/${gameId}`);
      navigate('/my-games');
    } catch (err: any) {
      console.error('Failed to cancel game:', err);
      setError(
        err.response?.data?.detail || 'Failed to cancel game. Please try again.'
      );
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
      dateStyle: 'full',
      timeStyle: 'short',
    });
  };

  const isHost = user && game && game.host?.user_id === user.user_uuid;
  const isParticipant =
    user &&
    game &&
    game.participants?.some((p) => p.user_id === user.user_uuid);

  if (loading) {
    return (
      <Container>
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
          <CircularProgress />
        </Box>
      </Container>
    );
  }

  if (!game) {
    return (
      <Container>
        <Alert severity="error" sx={{ mt: 4 }}>
          Game not found.
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
      <Paper elevation={3} sx={{ p: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
          <Typography variant="h4" component="h1">
            {game.title}
          </Typography>
          <Chip
            label={game.status}
            color={getStatusColor(game.status)}
            size="medium"
          />
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Typography variant="body1" paragraph>
          {game.description}
        </Typography>

        {game.signup_instructions && (
          <Box
            sx={{
              p: 2,
              mb: 2,
              bgcolor: 'info.light',
              borderRadius: 1,
              border: '1px solid',
              borderColor: 'info.main',
            }}
          >
            <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 'bold' }}>
              ℹ️ Signup Instructions
            </Typography>
            <Typography variant="body2">{game.signup_instructions}</Typography>
          </Box>
        )}

        <Divider sx={{ my: 3 }} />

        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Game Details
          </Typography>
          <Typography variant="body1" paragraph sx={{ fontSize: '1.1rem', fontWeight: 'bold' }}>
            <strong>When:</strong> {formatDateTime(game.scheduled_at)}
          </Typography>
          {game.host && game.host.display_name && (
            <Box sx={{ mb: 2 }}>
              <Chip
                label={`Host: ${game.host.display_name}`}
                color="secondary"
                size="medium"
                variant="outlined"
                sx={{ fontWeight: 'bold' }}
              />
            </Box>
          )}
          <Typography variant="body2" paragraph>
            <strong>Max Players:</strong> {game.max_players || 10}
          </Typography>
          {game.rules && (
            <Typography variant="body2" paragraph>
              <strong>Rules:</strong> {game.rules}
            </Typography>
          )}
          {game.reminder_minutes && game.reminder_minutes.length > 0 && (
            <Typography variant="body2">
              <strong>Reminders:</strong>{' '}
              {game.reminder_minutes.join(', ')} minutes before
            </Typography>
          )}
        </Box>

        <Divider sx={{ my: 3 }} />

        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Participants
          </Typography>
          <ParticipantList
            participants={game.participants || []}
            minPlayers={game.min_players || 1}
            maxPlayers={game.max_players || 10}
          />
        </Box>

        <Divider sx={{ my: 3 }} />

        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          {!isHost && !isParticipant && game.status === 'SCHEDULED' && (
            <Button
              variant="contained"
              onClick={handleJoinGame}
              disabled={actionLoading}
            >
              Join Game
            </Button>
          )}

          {!isHost && isParticipant && game.status === 'SCHEDULED' && (
            <Button
              variant="outlined"
              color="error"
              onClick={handleLeaveGame}
              disabled={actionLoading}
            >
              Leave Game
            </Button>
          )}

          {isHost && game.status === 'SCHEDULED' && (
            <>
              <Button
                variant="outlined"
                onClick={() => navigate(`/games/${gameId}/edit`)}
                disabled={actionLoading}
              >
                Edit Game
              </Button>
              <Button
                variant="outlined"
                color="error"
                onClick={() => setCancelDialogOpen(true)}
                disabled={actionLoading}
              >
                Cancel Game
              </Button>
            </>
          )}

          <Button variant="text" onClick={() => navigate(-1)}>
            Back
          </Button>
        </Box>
      </Paper>

      <Dialog open={cancelDialogOpen} onClose={() => setCancelDialogOpen(false)}>
        <DialogTitle>Cancel Game</DialogTitle>
        <DialogContent>
          Are you sure you want to cancel this game? This action cannot be undone.
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCancelDialogOpen(false)}>No, Keep It</Button>
          <Button
            onClick={() => {
              setCancelDialogOpen(false);
              handleCancelGame();
            }}
            color="error"
            autoFocus
          >
            Yes, Cancel Game
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};
