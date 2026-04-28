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
import { StatusCodes } from 'http-status-codes';
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
  Avatar,
  IconButton,
} from '@mui/material';
import DownloadIcon from '@mui/icons-material/Download';
import { useParams, useNavigate } from 'react-router';
import axios from 'axios';
import { apiClient } from '../api/client';
import { GameSession, SignupMethod, SIGNUP_METHOD_INFO } from '../types';
import { ParticipantList } from '../components/ParticipantList';
import { useAuth } from '../hooks/useAuth';
import { canManageGame } from '../utils/permissions';
import { Time } from '../constants/time';
import { UI } from '../constants/ui';

export const GameDetails: FC = () => {
  const { gameId } = useParams<{ gameId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [game, setGame] = useState<GameSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
  const [calendarLoading, setCalendarLoading] = useState(false);
  const [rewardsRevealed, setRewardsRevealed] = useState(false);

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

  useEffect(() => {
    const fetchGame = async () => {
      if (!gameId) return;

      try {
        setLoading(true);
        setError(null);
        const response = await apiClient.get<GameSession>(`/api/v1/games/${gameId}`);
        setGame(response.data);
      } catch (err: unknown) {
        console.error('Failed to fetch game:', err);
        setError((err as any).response?.data?.detail || 'Failed to load game. Please try again.');
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
    } catch (err: unknown) {
      console.error('Failed to join game:', err);
      setError((err as any).response?.data?.detail || 'Failed to join game. Please try again.');
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
    } catch (err: unknown) {
      console.error('Failed to leave game:', err);
      setError((err as any).response?.data?.detail || 'Failed to leave game. Please try again.');
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
    } catch (err: unknown) {
      console.error('Failed to cancel game:', err);
      setError((err as any).response?.data?.detail || 'Failed to cancel game. Please try again.');
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
  const canEdit = canManageGame(game);
  const isParticipant =
    user && game && game.participants?.some((p) => p.user_id === user.user_uuid);

  const handleDownloadCalendar = async () => {
    if (!gameId) return;

    setCalendarLoading(true);
    try {
      const url = `/api/v1/export/game/${gameId}`;
      const response = await axios.get(url, {
        responseType: 'blob',
        withCredentials: true,
      });

      const contentDisposition = response.headers['content-disposition'];
      let filename = `game-${gameId}.ics`;
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename=([^;]+)/);
        if (filenameMatch) {
          filename = filenameMatch[1].trim();
        }
      }

      const blob = new Blob([response.data], { type: 'text/calendar' });
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
    } catch (err) {
      console.error('Failed to export calendar:', err);
      const errorMessage =
        (err as any).response?.status === StatusCodes.FORBIDDEN
          ? 'You must be the host or a participant to export this game.'
          : 'Failed to export calendar. Please try again.';
      alert(errorMessage);
    } finally {
      setCalendarLoading(false);
    }
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
          <Chip label={game.status} color={getStatusColor(game.status)} size="medium" />
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Typography
          variant="body1"
          paragraph
          sx={{ wordBreak: 'break-word', whiteSpace: 'pre-wrap' }}
        >
          {game.description}
        </Typography>

        <Divider sx={{ my: 3 }} />

        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Game Details
          </Typography>
          {game.host && game.host.display_name && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
              <Avatar
                src={game.host.avatar_url || undefined}
                alt={game.host.display_name}
                sx={{ width: 40, height: 40 }}
              >
                {!game.host.avatar_url && game.host.display_name[0]}
              </Avatar>
              <Typography variant="body1" sx={{ fontSize: '1.1rem' }}>
                <strong>Host:</strong> {game.host.display_name}
              </Typography>
            </Box>
          )}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
            <Typography variant="body1" sx={{ fontSize: '1.1rem', fontWeight: 'bold' }}>
              <strong>When:</strong> {formatDateTime(game.scheduled_at)}
            </Typography>
            {(isHost || isParticipant) && (
              <IconButton
                size="small"
                onClick={handleDownloadCalendar}
                disabled={calendarLoading}
                title="Download calendar event"
                sx={{ ml: 1 }}
              >
                {calendarLoading ? <CircularProgress size={20} /> : <DownloadIcon />}
              </IconButton>
            )}
          </Box>
          <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap', mb: 1 }}>
            {game.expected_duration_minutes && (
              <Typography variant="body2">
                <strong>Duration:</strong> {formatDuration(game.expected_duration_minutes)}
              </Typography>
            )}
            {game.reminder_minutes && game.reminder_minutes.length > 0 && (
              <Typography variant="body2">
                <strong>Reminders:</strong> {game.reminder_minutes.join(', ')} minutes before
              </Typography>
            )}
            {game.signup_method && (
              <Typography variant="body2">
                <strong>Signup Method:</strong>{' '}
                {SIGNUP_METHOD_INFO[game.signup_method as SignupMethod]?.displayName ||
                  game.signup_method}
              </Typography>
            )}
          </Box>
          {(game.where_display ?? game.where) && (
            <Typography variant="body1" paragraph sx={{ fontSize: '1.1rem' }}>
              <strong>Where:</strong> {game.where_display ?? game.where}
            </Typography>
          )}
          <Typography variant="body1" paragraph sx={{ fontSize: '1.1rem' }}>
            <strong>Location:</strong> {game.guild_name || 'Unknown Server'} #
            {game.channel_name || 'Unknown Channel'}
          </Typography>
        </Box>

        {isHost && game.signup_instructions && (
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
            <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
              {game.signup_instructions}
            </Typography>
          </Box>
        )}

        {game.rewards && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 'bold' }}>
              🏆 Rewards
            </Typography>
            <Box
              onClick={() => setRewardsRevealed(true)}
              sx={{
                p: 1.5,
                borderRadius: 1,
                border: '1px solid',
                borderColor: 'divider',
                filter: rewardsRevealed ? 'none' : 'blur(6px)',
                cursor: rewardsRevealed ? 'default' : 'pointer',
                userSelect: rewardsRevealed ? 'text' : 'none',
                transition: 'filter 0.2s',
              }}
              title={rewardsRevealed ? undefined : 'Click to reveal rewards'}
            >
              <Typography variant="body2">
                {rewardsRevealed ? game.rewards : 'Click to reveal rewards'}
              </Typography>
            </Box>
          </Box>
        )}

        <Divider sx={{ my: 3 }} />

        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Participants ({game.participant_count || 0}/{game.max_players || UI.DEFAULT_MAX_PLAYERS}
            )
          </Typography>
          <ParticipantList
            participants={game.participants || []}
            maxPlayers={game.max_players || UI.DEFAULT_MAX_PLAYERS}
          />
        </Box>

        <Divider sx={{ my: 3 }} />

        {(game.has_thumbnail || game.has_image) && (
          <Box sx={{ mb: 3 }}>
            {game.has_thumbnail && game.thumbnail_id && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="h6" gutterBottom>
                  Thumbnail
                </Typography>
                <Box
                  component="img"
                  src={`/api/v1/public/images/${game.thumbnail_id}`}
                  alt="Game thumbnail"
                  sx={{
                    maxWidth: '200px',
                    maxHeight: '200px',
                    border: '1px solid',
                    borderColor: 'divider',
                    borderRadius: 1,
                  }}
                />
              </Box>
            )}
            {game.has_image && game.banner_image_id && (
              <Box>
                <Typography variant="h6" gutterBottom>
                  Banner
                </Typography>
                <Box
                  component="img"
                  src={`/api/v1/public/images/${game.banner_image_id}`}
                  alt="Game banner"
                  sx={{
                    maxWidth: '100%',
                    height: 'auto',
                    border: '1px solid',
                    borderColor: 'divider',
                    borderRadius: 1,
                  }}
                />
              </Box>
            )}
          </Box>
        )}

        <Divider sx={{ my: 3 }} />

        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          {!isHost && !isParticipant && game.status === 'SCHEDULED' && (
            <Button variant="contained" onClick={handleJoinGame} disabled={actionLoading}>
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

          {canEdit && (
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
                onClick={() => navigate(`/games/${gameId}/clone`)}
                disabled={actionLoading}
              >
                Clone Game
              </Button>
              {(!isHost || game.status === 'SCHEDULED' || game.status === 'IN_PROGRESS') && (
                <Button
                  variant="outlined"
                  color="error"
                  onClick={() => setCancelDialogOpen(true)}
                  disabled={actionLoading}
                >
                  Cancel Game
                </Button>
              )}
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
