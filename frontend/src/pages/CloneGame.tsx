// Copyright 2026 Bret McKee
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
  Box,
  Button,
  CircularProgress,
  Alert,
  Container,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  SelectChangeEvent,
  Typography,
} from '@mui/material';
import { DateTimePicker } from '@mui/x-date-pickers/DateTimePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { addDays } from 'date-fns';
import { useNavigate, useParams } from 'react-router';
import { apiClient } from '../api/client';
import { GameSession } from '../types';

type CarryoverOption = 'NO' | 'YES' | 'YES_WITH_DEADLINE';

interface CloneGameRequest {
  scheduled_at: string;
  player_carryover: CarryoverOption;
  player_deadline?: string;
  waitlist_carryover: CarryoverOption;
  waitlist_deadline?: string;
}

const CARRYOVER_OPTIONS: { value: CarryoverOption; label: string }[] = [
  { value: 'NO', label: 'No — start with an empty roster' },
  { value: 'YES', label: 'Yes — carry over existing players' },
  { value: 'YES_WITH_DEADLINE', label: 'Yes — carry over with confirmation deadline' },
];

const DEFAULT_DAYS_AHEAD = 14;

export const CloneGame: FC = () => {
  const { gameId } = useParams<{ gameId: string }>();
  const navigate = useNavigate();

  const [sourceGame, setSourceGame] = useState<GameSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const [scheduledAt, setScheduledAt] = useState<Date | null>(null);
  const [playerCarryover, setPlayerCarryover] = useState<CarryoverOption>('NO');
  const [waitlistCarryover, setWaitlistCarryover] = useState<CarryoverOption>('NO');
  const [playerDeadline, setPlayerDeadline] = useState<Date | null>(null);
  const [waitlistDeadline, setWaitlistDeadline] = useState<Date | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    if (!gameId) return;

    const fetchGame = async () => {
      try {
        setLoading(true);
        setFetchError(null);
        const response = await apiClient.get<GameSession>(`/api/v1/games/${gameId}`);
        const game = response.data;
        setSourceGame(game);
        setScheduledAt(addDays(new Date(game.scheduled_at), DEFAULT_DAYS_AHEAD));
      } catch {
        setFetchError('Failed to load game. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    fetchGame();
  }, [gameId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!gameId || !scheduledAt) return;

    setValidationError(null);
    setSubmitError(null);

    const now = new Date();
    if (playerCarryover === 'YES_WITH_DEADLINE') {
      if (!playerDeadline) {
        setValidationError('Player deadline is required when using deadline carryover.');
        return;
      }
      if (playerDeadline <= now) {
        setValidationError('Player deadline must be in the future.');
        return;
      }
    }
    if (waitlistCarryover === 'YES_WITH_DEADLINE') {
      if (!waitlistDeadline) {
        setValidationError('Waitlist deadline is required when using deadline carryover.');
        return;
      }
      if (waitlistDeadline <= now) {
        setValidationError('Waitlist deadline must be in the future.');
        return;
      }
    }

    setSubmitting(true);

    const payload: CloneGameRequest = {
      scheduled_at: scheduledAt.toISOString(),
      player_carryover: playerCarryover,
      ...(playerCarryover === 'YES_WITH_DEADLINE' && playerDeadline
        ? { player_deadline: playerDeadline.toISOString() }
        : {}),
      waitlist_carryover: waitlistCarryover,
      ...(waitlistCarryover === 'YES_WITH_DEADLINE' && waitlistDeadline
        ? { waitlist_deadline: waitlistDeadline.toISOString() }
        : {}),
    };

    try {
      const response = await apiClient.post<GameSession>(`/api/v1/games/${gameId}/clone`, payload);
      navigate(`/games/${response.data.id}`);
    } catch (err: unknown) {
      const message =
        (err as any).response?.data?.detail ?? 'Failed to clone game. Please try again.';
      setSubmitError(typeof message === 'string' ? message : JSON.stringify(message));
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <Container maxWidth="sm" sx={{ mt: 4, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress />
      </Container>
    );
  }

  if (fetchError || !sourceGame) {
    return (
      <Container maxWidth="sm" sx={{ mt: 4 }}>
        <Alert severity="error">{fetchError ?? 'Game not found'}</Alert>
        <Button sx={{ mt: 2 }} onClick={() => navigate(-1)}>
          Back
        </Button>
      </Container>
    );
  }

  return (
    <Container maxWidth="sm" sx={{ mt: 4, mb: 4 }}>
      <Paper sx={{ p: 4 }}>
        <Typography variant="h5" gutterBottom>
          Clone Game
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Cloning: <strong>{sourceGame.title}</strong>
        </Typography>

        {(validationError || submitError) && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {validationError ?? submitError}
          </Alert>
        )}

        <LocalizationProvider dateAdapter={AdapterDateFns}>
          <Box
            component="form"
            onSubmit={handleSubmit}
            sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}
          >
            <DateTimePicker
              label="Scheduled Date & Time"
              value={scheduledAt}
              onChange={(value) => setScheduledAt(value)}
              slotProps={{
                textField: { required: true, fullWidth: true },
              }}
            />

            <FormControl fullWidth>
              <InputLabel id="player-carryover-label">Player Carryover</InputLabel>
              <Select
                labelId="player-carryover-label"
                value={playerCarryover}
                label="Player Carryover"
                onChange={(e: SelectChangeEvent<CarryoverOption>) =>
                  setPlayerCarryover(e.target.value as CarryoverOption)
                }
              >
                {CARRYOVER_OPTIONS.map((opt) => (
                  <MenuItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {playerCarryover === 'YES_WITH_DEADLINE' && (
              <DateTimePicker
                label="Player Confirmation Deadline"
                value={playerDeadline}
                onChange={(value) => setPlayerDeadline(value)}
                slotProps={{
                  textField: { required: true, fullWidth: true },
                }}
              />
            )}

            <FormControl fullWidth>
              <InputLabel id="waitlist-carryover-label">Waitlist Carryover</InputLabel>
              <Select
                labelId="waitlist-carryover-label"
                value={waitlistCarryover}
                label="Waitlist Carryover"
                onChange={(e: SelectChangeEvent<CarryoverOption>) =>
                  setWaitlistCarryover(e.target.value as CarryoverOption)
                }
              >
                {CARRYOVER_OPTIONS.map((opt) => (
                  <MenuItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {waitlistCarryover === 'YES_WITH_DEADLINE' && (
              <DateTimePicker
                label="Waitlist Confirmation Deadline"
                value={waitlistDeadline}
                onChange={(value) => setWaitlistDeadline(value)}
                slotProps={{
                  textField: { required: true, fullWidth: true },
                }}
              />
            )}

            <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
              <Button
                variant="text"
                onClick={() => navigate(`/games/${gameId}`)}
                disabled={submitting}
              >
                Cancel
              </Button>
              <Button type="submit" variant="contained" disabled={submitting || !scheduledAt}>
                {submitting ? <CircularProgress size={20} /> : 'Clone Game'}
              </Button>
            </Box>
          </Box>
        </LocalizationProvider>
      </Paper>
    </Container>
  );
};
