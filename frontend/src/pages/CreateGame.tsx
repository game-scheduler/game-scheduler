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
import { Channel } from '../types';
import { ValidationErrors } from '../components/ValidationErrors';

interface FormData {
  title: string;
  description: string;
  signupInstructions: string;
  scheduledAt: Date | null;
  channelId: string;
  minPlayers: string;
  maxPlayers: string;
  reminderMinutes: string;
  rules: string;
  initialParticipants: string;
}

interface ValidationError {
  input: string;
  reason: string;
  suggestions: Array<{
    discordId: string;
    username: string;
    displayName: string;
  }>;
}

interface ValidationErrorResponse {
  error: string;
  message: string;
  invalid_mentions: ValidationError[];
  valid_participants: string[];
}

export const CreateGame: FC = () => {
  const navigate = useNavigate();
  const { guildId } = useParams<{ guildId: string }>();
  const [channels, setChannels] = useState<Channel[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<ValidationError[] | null>(null);
  const [formData, setFormData] = useState<FormData>({
    title: '',
    description: '',
    signupInstructions: '',
    scheduledAt: null,
    channelId: '',
    minPlayers: '',
    maxPlayers: '',
    reminderMinutes: '',
    rules: '',
    initialParticipants: '',
  });

  useEffect(() => {
    const fetchChannels = async () => {
      if (!guildId) return;

      try {
        const response = await apiClient.get<Channel[]>(
          `/api/v1/guilds/${guildId}/channels`
        );
        setChannels(response.data);
      } catch (err: any) {
        console.error('Failed to fetch channels:', err);
        setError('Failed to load channels. Please try again.');
      }
    };

    fetchChannels();
  }, [guildId]);

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

    if (!guildId || !formData.channelId || !formData.scheduledAt) {
      setError('Please fill in all required fields.');
      return;
    }

    const minPlayers = formData.minPlayers ? parseInt(formData.minPlayers) : null;
    const maxPlayers = formData.maxPlayers ? parseInt(formData.maxPlayers) : null;

    if (minPlayers && maxPlayers && minPlayers > maxPlayers) {
      setError('Minimum players cannot be greater than maximum players.');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setValidationErrors(null);

      const payload = {
        title: formData.title,
        description: formData.description,
        signup_instructions: formData.signupInstructions || null,
        scheduled_at: formData.scheduledAt.toISOString(),
        guild_id: guildId,
        channel_id: formData.channelId,
        min_players: minPlayers,
        max_players: maxPlayers,
        reminder_minutes: formData.reminderMinutes
          ? formData.reminderMinutes.split(',').map((m) => parseInt(m.trim()))
          : null,
        rules: formData.rules || null,
        initial_participants: formData.initialParticipants
          ? formData.initialParticipants
              .split('\n')
              .map((s) => s.trim())
              .filter((s) => s.length > 0)
          : [],
      };

      const response = await apiClient.post('/api/v1/games', payload);

      navigate(`/games/${response.data.id}`);
    } catch (err: any) {
      console.error('Failed to create game:', err);
      
      if (err.response?.status === 422 && err.response.data?.error === 'invalid_mentions') {
        const errorData = err.response.data as ValidationErrorResponse;
        setValidationErrors(errorData.invalid_mentions);
        setError(errorData.message);
      } else {
        setError(
          err.response?.data?.detail || 'Failed to create game. Please try again.'
        );
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSuggestionClick = (originalInput: string, newUsername: string) => {
    const lines = formData.initialParticipants.split('\n');
    const updatedLines = lines.map(line => 
      line.trim() === originalInput ? newUsername : line
    );
    setFormData(prev => ({
      ...prev,
      initialParticipants: updatedLines.join('\n')
    }));
    setValidationErrors(null);
    setError(null);
  };

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns}>
      <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
        <Paper elevation={3} sx={{ p: 4 }}>
          <Typography variant="h4" gutterBottom>
            Create New Game
          </Typography>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          {validationErrors && (
            <ValidationErrors 
              errors={validationErrors}
              onSuggestionClick={handleSuggestionClick}
            />
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
              disabled={loading}
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
              disabled={loading}
            />

            <TextField
              fullWidth
              multiline
              rows={2}
              label="Signup Instructions"
              name="signupInstructions"
              value={formData.signupInstructions}
              onChange={handleChange}
              margin="normal"
              helperText="Special requirements or instructions for participants"
              disabled={loading}
            />

            <DateTimePicker
              label="Scheduled Time *"
              value={formData.scheduledAt}
              onChange={handleDateChange}
              disabled={loading}
              sx={{ width: '100%', mt: 2, mb: 1 }}
            />

            <FormControl fullWidth margin="normal" required>
              <InputLabel>Channel</InputLabel>
              <Select
                value={formData.channelId}
                onChange={handleSelectChange}
                label="Channel"
                disabled={loading}
              >
                {channels.map((channel) => (
                  <MenuItem key={channel.id} value={channel.id}>
                    {channel.channel_name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <TextField
              fullWidth
              label="Min Players"
              name="minPlayers"
              type="number"
              value={formData.minPlayers}
              onChange={handleChange}
              margin="normal"
              helperText="Minimum players required (default: 1)"
              disabled={loading}
              inputProps={{ min: 1, max: 100 }}
            />

            <TextField
              fullWidth
              label="Max Players"
              name="maxPlayers"
              type="number"
              value={formData.maxPlayers}
              onChange={handleChange}
              margin="normal"
              helperText="Leave empty to use channel/guild default"
              disabled={loading}
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
              disabled={loading}
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
              disabled={loading}
            />

            <TextField
              fullWidth
              multiline
              rows={4}
              label="Initial Participants"
              name="initialParticipants"
              value={formData.initialParticipants}
              onChange={handleChange}
              margin="normal"
              helperText="One per line. Use @username for Discord users or plain text for placeholders"
              disabled={loading}
            />

            <Box sx={{ display: 'flex', gap: 2, mt: 3 }}>
              <Button
                type="submit"
                variant="contained"
                disabled={loading}
                fullWidth
              >
                {loading ? <CircularProgress size={24} /> : 'Create Game'}
              </Button>
              <Button
                variant="outlined"
                onClick={() => navigate(-1)}
                disabled={loading}
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
