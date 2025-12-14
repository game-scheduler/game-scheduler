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
  Grid,
} from '@mui/material';
import { DateTimePicker } from '@mui/x-date-pickers/DateTimePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { Channel, GameSession } from '../types';
import { ValidationErrors } from './ValidationErrors';
import { formatParticipantDisplay } from '../utils/formatParticipant';
import {
  EditableParticipantList,
  ParticipantInput as EditableParticipantInput,
} from './EditableParticipantList';

/**
 * Round time up to the next half hour (e.g., 5:13 -> 5:30, 5:30 -> 5:30, 5:31 -> 6:00)
 */
function getNextHalfHour(): Date {
  const now = new Date();
  const minutes = now.getMinutes();
  const seconds = now.getSeconds();
  const milliseconds = now.getMilliseconds();

  // If already on the half hour exactly, keep it
  if (minutes === 0 || minutes === 30) {
    if (seconds === 0 && milliseconds === 0) {
      return now;
    }
  }

  // Round up to next half hour
  const nextHalfHour = new Date(now);
  if (minutes < 30) {
    nextHalfHour.setMinutes(30, 0, 0);
  } else {
    nextHalfHour.setHours(now.getHours() + 1, 0, 0, 0);
  }

  return nextHalfHour;
}

export interface GameFormData {
  title: string;
  description: string;
  signupInstructions: string;
  scheduledAt: Date | null;
  where: string;
  channelId: string;
  maxPlayers: string;
  reminderMinutes: string;
  expectedDurationMinutes: string;
  participants: EditableParticipantInput[];
}

interface GameFormProps {
  mode: 'create' | 'edit';
  initialData?: Partial<GameSession>;
  guildId: string;
  channels: Channel[];
  onSubmit: (formData: GameFormData) => Promise<void>;
  onCancel: () => void;
  validationErrors?: Array<{
    input: string;
    reason: string;
    suggestions: Array<{
      discordId: string;
      username: string;
      displayName: string;
    }>;
  }> | null;
  validParticipants?: string[] | null;
  onValidationErrorClick?: (originalInput: string, newUsername: string) => void;
}

export const formatDurationForDisplay = (minutes: number | null): string => {
  if (!minutes) return '';
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  if (hours > 0 && remainingMinutes > 0) {
    return `${hours}h ${remainingMinutes}m`;
  } else if (hours > 0) {
    return `${hours}h`;
  } else {
    return `${remainingMinutes}m`;
  }
};

export const parseDurationString = (input: string): number | null => {
  if (!input || !input.trim()) return null;

  const trimmed = input.trim().toLowerCase();

  // Parse formats like "1h 30m", "1h30m", "90m", "2h"
  const hourMinuteMatch = trimmed.match(/^(\d+)h\s*(\d+)m$/);
  if (hourMinuteMatch) {
    return parseInt(hourMinuteMatch[1]!) * 60 + parseInt(hourMinuteMatch[2]!);
  }

  const hoursOnlyMatch = trimmed.match(/^(\d+)h$/);
  if (hoursOnlyMatch) {
    return parseInt(hoursOnlyMatch[1]!) * 60;
  }

  const minutesOnlyMatch = trimmed.match(/^(\d+)m$/);
  if (minutesOnlyMatch) {
    return parseInt(minutesOnlyMatch[1]!);
  }

  // Parse colon format like "1:30" (hours:minutes)
  const colonMatch = trimmed.match(/^(\d+):(\d+)$/);
  if (colonMatch) {
    return parseInt(colonMatch[1]!) * 60 + parseInt(colonMatch[2]!);
  }

  // Try parsing as plain number (minutes)
  const numericValue = parseInt(trimmed);
  if (!isNaN(numericValue) && numericValue > 0) {
    return numericValue;
  }

  return null;
};

export const GameForm: FC<GameFormProps> = ({
  mode,
  initialData,
  guildId,
  channels,
  onSubmit,
  onCancel,
  validationErrors,
  validParticipants,
  onValidationErrorClick,
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState<GameFormData>({
    title: initialData?.title || '',
    description: initialData?.description || '',
    signupInstructions: initialData?.signup_instructions || '',
    scheduledAt: initialData?.scheduled_at ? new Date(initialData.scheduled_at) : getNextHalfHour(),
    where: initialData?.where || '',
    channelId: initialData?.channel_id || '',
    maxPlayers: initialData?.max_players?.toString() || '8',
    reminderMinutes: initialData?.reminder_minutes?.join(', ') || '',
    expectedDurationMinutes: formatDurationForDisplay(
      initialData?.expected_duration_minutes ?? null
    ),
    participants: initialData?.participants
      ? initialData.participants
          .sort((a, b) => {
            // Sort: pre-filled first (by position), then joined (by join time)
            const aPos = a.pre_filled_position ?? Number.MAX_SAFE_INTEGER;
            const bPos = b.pre_filled_position ?? Number.MAX_SAFE_INTEGER;
            return aPos - bPos;
          })
          .map((p, index) => ({
            id: p.id,
            mention: formatParticipantDisplay(p.display_name, p.discord_id),
            isValid: true,
            preFillPosition: index + 1,
            isExplicitlyPositioned: p.pre_filled_position !== null,
            isReadOnly: p.pre_filled_position === null, // Joined users are read-only
            validationStatus: 'valid' as const, // From server, so validated
          }))
      : [],
  });

  // Update form when initialData changes (e.g., after async fetch in edit mode)
  useEffect(() => {
    if (initialData) {
      setFormData({
        title: initialData.title || '',
        description: initialData.description || '',
        signupInstructions: initialData.signup_instructions || '',
        scheduledAt: initialData.scheduled_at
          ? new Date(initialData.scheduled_at)
          : getNextHalfHour(),
        where: initialData.where || '',
        channelId: initialData.channel_id || '',
        maxPlayers: initialData.max_players?.toString() || '8',
        reminderMinutes: initialData.reminder_minutes?.join(', ') || '',
        expectedDurationMinutes: formatDurationForDisplay(
          initialData.expected_duration_minutes ?? null
        ),
        participants: initialData.participants
          ? initialData.participants
              .sort((a, b) => {
                const aPos = a.pre_filled_position ?? Number.MAX_SAFE_INTEGER;
                const bPos = b.pre_filled_position ?? Number.MAX_SAFE_INTEGER;
                return aPos - bPos;
              })
              .map((p, index) => ({
                id: p.id,
                mention: formatParticipantDisplay(p.display_name, p.discord_id),
                isValid: true,
                preFillPosition: index + 1,
                isExplicitlyPositioned: p.pre_filled_position !== null,
                isReadOnly: p.pre_filled_position === null,
                validationStatus: 'valid' as const,
              }))
          : [],
      });
    }
  }, [initialData]);

  // Auto-select channel when only one is available
  useEffect(() => {
    if (channels.length === 1 && !formData.channelId && channels[0]) {
      setFormData((prev) => ({ ...prev, channelId: channels[0]!.id }));
    }
  }, [channels, formData.channelId]);

  // Update participant validation status when validationErrors change
  useEffect(() => {
    if (!validationErrors && !validParticipants) return;

    const invalidInputs = new Set(validationErrors?.map((err) => err.input.trim()) || []);
    const validInputs = new Set(validParticipants?.map((input) => input.trim()) || []);

    setFormData((prev) => ({
      ...prev,
      participants: prev.participants.map((p) => {
        const mention = p.mention.trim();
        if (invalidInputs.has(mention)) {
          return { ...p, validationStatus: 'invalid' as const };
        }
        if (validInputs.has(mention)) {
          return { ...p, validationStatus: 'valid' as const };
        }
        // Don't change status for other participants
        return p;
      }),
    }));
  }, [validationErrors, validParticipants]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSelectChange = (event: SelectChangeEvent) => {
    setFormData((prev) => ({ ...prev, channelId: event.target.value }));
  };

  const handleDateChange = (date: Date | null) => {
    setFormData((prev) => ({ ...prev, scheduledAt: date }));
  };

  const handleParticipantsChange = (participants: EditableParticipantInput[]) => {
    setFormData((prev) => ({ ...prev, participants }));
  };

  const handleSuggestionClick = (originalInput: string, newUsername: string) => {
    const updatedParticipants = formData.participants.map((p) =>
      p.mention.trim() === originalInput.trim()
        ? { ...p, mention: newUsername, validationStatus: 'unknown' as const }
        : p
    );
    setFormData((prev) => ({ ...prev, participants: updatedParticipants }));

    if (onValidationErrorClick) {
      onValidationErrorClick(originalInput, newUsername);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!guildId || !formData.channelId || !formData.scheduledAt) {
      setError('Please fill in all required fields.');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      await onSubmit(formData);
    } catch (err: unknown) {
      console.error('Failed to submit form:', err);
      // Don't set error here if validation errors exist - parent handles those
      if (!validationErrors) {
        const errorDetail = (err as any).response?.data?.detail;
        const errorMessage =
          typeof errorDetail === 'string'
            ? errorDetail
            : errorDetail?.message || 'Failed to submit. Please try again.';
        setError(errorMessage);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns}>
      <Paper elevation={3} sx={{ p: 4 }}>
        <Typography variant="h4" gutterBottom>
          {mode === 'create' ? 'Create New Game' : 'Edit Game'}
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {validationErrors && (
          <ValidationErrors errors={validationErrors} onSuggestionClick={handleSuggestionClick} />
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
            label="Location"
            name="where"
            value={formData.where}
            onChange={handleChange}
            margin="normal"
            multiline
            rows={2}
            helperText="Game location (optional, up to 500 characters)"
            disabled={loading}
            inputProps={{ maxLength: 500 }}
          />

          <DateTimePicker
            label="Scheduled Time *"
            value={formData.scheduledAt}
            onChange={handleDateChange}
            disabled={loading}
            sx={{ width: '100%', mt: 2, mb: 1 }}
          />

          <TextField
            fullWidth
            label="Expected Duration"
            name="expectedDurationMinutes"
            value={formData.expectedDurationMinutes}
            onChange={handleChange}
            margin="normal"
            helperText="e.g., 2h, 90m, 1h 30m, 1:30 (optional)"
            disabled={loading}
            placeholder="2h 30m"
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

          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid size={{ xs: 12, md: 6 }}>
              <TextField
                fullWidth
                label="Max Players"
                name="maxPlayers"
                type="number"
                value={formData.maxPlayers}
                onChange={handleChange}
                helperText="Leave empty to use channel/server default"
                disabled={loading}
                inputProps={{ min: 1, max: 100 }}
              />
            </Grid>
          </Grid>

          <EditableParticipantList
            participants={formData.participants}
            onChange={handleParticipantsChange}
          />

          <Box sx={{ display: 'flex', gap: 2, mt: 3 }}>
            <Button type="submit" variant="contained" disabled={loading} fullWidth>
              {loading ? (
                <CircularProgress size={24} />
              ) : mode === 'create' ? (
                'Create Game'
              ) : (
                'Save Changes'
              )}
            </Button>
            <Button variant="outlined" onClick={onCancel} disabled={loading} fullWidth>
              Cancel
            </Button>
          </Box>
        </Box>
      </Paper>
    </LocalizationProvider>
  );
};
