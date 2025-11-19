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
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  CircularProgress,
  Alert,
  Paper,
  SelectChangeEvent,
} from '@mui/material';
import { DateTimePicker } from '@mui/x-date-pickers/DateTimePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { useNavigate, useParams } from 'react-router-dom';
import { apiClient } from '../api/client';
import { Channel, GameSession } from '../types';

interface FormData {
  title: string;
  description: string;
  scheduledAt: Date | null;
  channelId: string;
  maxPlayers: string;
  reminderMinutes: string;
  rules: string;
}

export const EditGame: FC = () => {
  const navigate = useNavigate();
  const { gameId } = useParams<{ gameId: string }>();
  const [game, setGame] = useState<GameSession | null>(null);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState<FormData>({
    title: '',
    description: '',
    scheduledAt: null,
    channelId: '',
    maxPlayers: '',
    reminderMinutes: '',
    rules: '',
  });

  useEffect(() => {
    const fetchGameAndChannels = async () => {
      if (!gameId) return;

      try {
        setLoading(true);
        const gameResponse = await apiClient.get<GameSession>(`/api/v1/games/${gameId}`);
        const gameData = gameResponse.data;
        setGame(gameData);

        const channelsResponse = await apiClient.get<Channel[]>(
          `/api/v1/guilds/${gameData.guild_id}/channels`
        );
        setChannels(channelsResponse.data);

        setFormData({
          title: gameData.title,
          description: gameData.description,
          scheduledAt: new Date(gameData.scheduled_at),
          channelId: gameData.channel_id,
          maxPlayers: gameData.max_players?.toString() || '',
          reminderMinutes: gameData.reminder_minutes?.join(', ') || '',
          rules: gameData.rules || '',
        });
      } catch (err: any) {
        console.error('Failed to fetch game:', err);
        setError('Failed to load game. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    fetchGameAndChannels();
  }, [gameId]);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSelectChange = (event: SelectChangeEvent) => {
    setFormData((prev) => ({ ...prev, channelId: event.target.value }));
  };

  const handleDateChange = (date: Date | null) => {
    setFormData((prev) => ({ ...prev, scheduledAt: date }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!gameId || !formData.channelId || !formData.scheduledAt) {
      setError('Please fill in all required fields.');
      return;
    }

    try {
      setSaving(true);
      setError(null);

      const payload = {
        title: formData.title,
        description: formData.description,
        scheduled_at: formData.scheduledAt.toISOString(),
        channel_id: formData.channelId,
        max_players: formData.maxPlayers ? parseInt(formData.maxPlayers) : null,
        reminder_minutes: formData.reminderMinutes
          ? formData.reminderMinutes.split(',').map((m) => parseInt(m.trim()))
          : null,
        rules: formData.rules || null,
      };

      await apiClient.put(`/api/v1/games/${gameId}`, payload);

      navigate(`/games/${gameId}`);
    } catch (err: any) {
      console.error('Failed to update game:', err);
      setError(
        err.response?.data?.detail || 'Failed to update game. Please try again.'
      );
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Container maxWidth="md" sx={{ mt: 4, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress />
      </Container>
    );
  }

  if (!game) {
    return (
      <Container maxWidth="md" sx={{ mt: 4 }}>
        <Alert severity="error">Game not found</Alert>
      </Container>
    );
  }

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns}>
      <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
        <Paper elevation={3} sx={{ p: 4 }}>
          <Typography variant="h4" gutterBottom>
            Edit Game
          </Typography>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          <Box component="form" onSubmit={handleSubmit} sx={{ mt: 3 }}>
            <TextField
              fullWidth
              required
              label="Game Title"
              name="title"
              value={formData.title}
              onChange={handleChange}
              margin="normal"
              disabled={saving}
            />

            <TextField
              fullWidth
              required
              multiline
              rows={3}
              label="Description"
              name="description"
              value={formData.description}
              onChange={handleChange}
              margin="normal"
              disabled={saving}
            />

            <DateTimePicker
              label="Scheduled Time *"
              value={formData.scheduledAt}
              onChange={handleDateChange}
              disabled={saving}
              sx={{ width: '100%', mt: 2, mb: 1 }}
            />

            <FormControl fullWidth margin="normal" required>
              <InputLabel>Channel</InputLabel>
              <Select
                value={formData.channelId}
                onChange={handleSelectChange}
                label="Channel"
                disabled={saving}
              >
                {channels.map((channel) => (
                  <MenuItem key={channel.id} value={channel.id}>
                    {channel.channelName}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <TextField
              fullWidth
              label="Max Players"
              name="maxPlayers"
              type="number"
              value={formData.maxPlayers}
              onChange={handleChange}
              margin="normal"
              helperText="Leave empty to use channel/guild default"
              disabled={saving}
              inputProps={{ min: 1, max: 100 }}
            />

            <TextField
              fullWidth
              label="Reminder Times (minutes)"
              name="reminderMinutes"
              value={formData.reminderMinutes}
              onChange={handleChange}
              margin="normal"
              helperText="Comma-separated (e.g., 60, 15). Leave empty for default"
              disabled={saving}
            />

            <TextField
              fullWidth
              multiline
              rows={3}
              label="Rules"
              name="rules"
              value={formData.rules}
              onChange={handleChange}
              margin="normal"
              helperText="Leave empty to use channel/guild default"
              disabled={saving}
            />

            <Box sx={{ display: 'flex', gap: 2, mt: 3 }}>
              <Button
                type="submit"
                variant="contained"
                disabled={saving}
                fullWidth
              >
                {saving ? <CircularProgress size={24} /> : 'Save Changes'}
              </Button>
              <Button
                variant="outlined"
                onClick={() => navigate(`/games/${gameId}`)}
                disabled={saving}
                fullWidth
              >
                Cancel
              </Button>
            </Box>
          </Box>
        </Paper>
      </Container>
    </LocalizationProvider>
  );
};
