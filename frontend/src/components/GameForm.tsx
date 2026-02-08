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
import { Channel, GameSession, ParticipantType, SignupMethod, SIGNUP_METHOD_INFO } from '../types';
import { ValidationErrors } from './ValidationErrors';
import { formatParticipantDisplay } from '../utils/formatParticipant';
import {
  EditableParticipantList,
  ParticipantInput as EditableParticipantInput,
} from './EditableParticipantList';
import { DurationSelector } from './DurationSelector';
import { ReminderSelector } from './ReminderSelector';
import { useAuth } from '../hooks/useAuth';
import { Time } from '../constants/time';
import { UI } from '../constants/ui';
import {
  validateDuration,
  validateMaxPlayers,
  validateCharacterLimit,
  validateFutureDate,
} from '../utils/fieldValidation';

/**
 * Round time up to the next half hour (e.g., 5:13 -> 5:30, 5:30 -> 5:30, 5:31 -> 6:00)
 */
function getNextHalfHour(): Date {
  const now = new Date();
  const minutes = now.getMinutes();
  const seconds = now.getSeconds();
  const milliseconds = now.getMilliseconds();

  // If already on the half hour exactly, keep it
  if (minutes === 0 || minutes === Time.MINUTES_PER_HALF_HOUR) {
    if (seconds === 0 && milliseconds === 0) {
      return now;
    }
  }

  // Round up to next half hour
  const nextHalfHour = new Date(now);
  if (minutes < Time.MINUTES_PER_HALF_HOUR) {
    nextHalfHour.setMinutes(Time.MINUTES_PER_HALF_HOUR, 0, 0);
  } else {
    nextHalfHour.setHours(now.getHours() + 1, 0, 0, 0);
  }

  return nextHalfHour;
}

export interface GameFormData {
  title: string;
  host?: string;
  description: string;
  signupInstructions: string;
  scheduledAt: Date | null;
  where: string;
  channelId: string;
  maxPlayers: string;
  reminderMinutes: string;
  reminderMinutesArray: number[];
  expectedDurationMinutes: number | null;
  participants: EditableParticipantInput[];
  signupMethod: string;
  thumbnailFile: File | null;
  imageFile: File | null;
  removeThumbnail: boolean;
  removeImage: boolean;
}

interface GameFormProps {
  mode: 'create' | 'edit';
  initialData?: Partial<GameSession>;
  guildId: string;
  guildName?: string;
  canChangeChannel?: boolean;
  isBotManager?: boolean;
  channels: Channel[];
  allowedSignupMethods?: string[] | null;
  defaultSignupMethod?: string | null;
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

export const GameForm: FC<GameFormProps> = ({
  mode,
  initialData,
  guildId,
  guildName: _guildName,
  canChangeChannel = true,
  isBotManager = false,
  channels,
  allowedSignupMethods = null,
  defaultSignupMethod = null,
  onSubmit,
  onCancel,
  validationErrors,
  validParticipants,
  onValidationErrorClick,
}) => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hostError, setHostError] = useState<string | null>(null);

  // Validation error states
  const [durationError, setDurationError] = useState<string | null>(null);
  const [reminderError, setReminderError] = useState<string | null>(null);
  const [maxPlayersError, setMaxPlayersError] = useState<string | null>(null);
  const [locationError, setLocationError] = useState<string | null>(null);
  const [descriptionError, setDescriptionError] = useState<string | null>(null);
  const [signupInstructionsError, setSignupInstructionsError] = useState<string | null>(null);
  const [scheduledAtError, setScheduledAtError] = useState<string | null>(null);

  // Calculate available signup methods: if empty/null, all methods are available
  const availableSignupMethods =
    !allowedSignupMethods || allowedSignupMethods.length === 0
      ? Object.values(SignupMethod)
      : allowedSignupMethods.filter((method) => method in SignupMethod);

  // Determine default signup method
  const resolvedDefaultSignupMethod =
    defaultSignupMethod && availableSignupMethods.includes(defaultSignupMethod)
      ? defaultSignupMethod
      : availableSignupMethods[0] || SignupMethod.SELF_SIGNUP;

  const [formData, setFormData] = useState<GameFormData>({
    title: initialData?.title || '',
    host: '',
    description: initialData?.description || '',
    signupInstructions: initialData?.signup_instructions || '',
    scheduledAt: initialData?.scheduled_at ? new Date(initialData.scheduled_at) : getNextHalfHour(),
    where: initialData?.where || '',
    channelId: initialData?.channel_id || '',
    maxPlayers: initialData?.max_players?.toString() || '8',
    reminderMinutes: initialData?.reminder_minutes?.join(', ') || '',
    reminderMinutesArray:
      initialData?.reminder_minutes && Array.isArray(initialData.reminder_minutes)
        ? [...initialData.reminder_minutes]
        : [],
    expectedDurationMinutes: initialData?.expected_duration_minutes ?? null,
    participants: initialData?.participants
      ? initialData.participants
          .sort((a, b) => {
            // Sort: host-added first (by position), then self-added (by join time)
            const aPos =
              a.position_type === ParticipantType.HOST_ADDED ? a.position : Number.MAX_SAFE_INTEGER;
            const bPos =
              b.position_type === ParticipantType.HOST_ADDED ? b.position : Number.MAX_SAFE_INTEGER;
            return aPos - bPos;
          })
          .map((p, index) => ({
            id: p.id,
            mention: formatParticipantDisplay(p.display_name, p.discord_id),
            isValid: true,
            preFillPosition: index + 1,
            isExplicitlyPositioned: p.position_type === ParticipantType.HOST_ADDED,
            isReadOnly: p.position_type !== ParticipantType.HOST_ADDED, // Self-added users are read-only
            validationStatus: 'valid' as const, // From server, so validated
          }))
      : [],
    signupMethod: initialData?.signup_method || resolvedDefaultSignupMethod,
    thumbnailFile: null,
    imageFile: null,
    removeThumbnail: false,
    removeImage: false,
  });

  // Update form when initialData changes (e.g., after async fetch in edit mode)
  useEffect(() => {
    if (initialData) {
      setFormData({
        title: initialData.title || '',
        host: '',
        description: initialData.description || '',
        signupInstructions: initialData.signup_instructions || '',
        scheduledAt: initialData.scheduled_at
          ? new Date(initialData.scheduled_at)
          : getNextHalfHour(),
        where: initialData.where || '',
        channelId: initialData.channel_id || '',
        maxPlayers: initialData.max_players?.toString() || '8',
        reminderMinutes: initialData.reminder_minutes?.join(', ') || '',
        reminderMinutesArray:
          initialData.reminder_minutes && Array.isArray(initialData.reminder_minutes)
            ? [...initialData.reminder_minutes]
            : [],
        expectedDurationMinutes: initialData.expected_duration_minutes ?? null,
        participants: initialData.participants
          ? initialData.participants
              .sort((a, b) => {
                const aPos =
                  a.position_type === ParticipantType.HOST_ADDED
                    ? a.position
                    : Number.MAX_SAFE_INTEGER;
                const bPos =
                  b.position_type === ParticipantType.HOST_ADDED
                    ? b.position
                    : Number.MAX_SAFE_INTEGER;
                return aPos - bPos;
              })
              .map((p, index) => ({
                id: p.id,
                mention: formatParticipantDisplay(p.display_name, p.discord_id),
                isValid: true,
                preFillPosition: index + 1,
                isExplicitlyPositioned: p.position_type === ParticipantType.HOST_ADDED,
                isReadOnly: p.position_type !== ParticipantType.HOST_ADDED,
                validationStatus: 'valid' as const,
              }))
          : [],
        signupMethod: initialData.signup_method || resolvedDefaultSignupMethod,
        thumbnailFile: null,
        imageFile: null,
        removeThumbnail: false,
        removeImage: false,
      });
    }
  }, [initialData, resolvedDefaultSignupMethod]);

  // Auto-select channel when only one is available
  useEffect(() => {
    if (channels.length === 1 && !formData.channelId && channels[0]) {
      setFormData((prev) => ({ ...prev, channelId: channels[0]!.id }));
    }
  }, [channels, formData.channelId]);

  // Update participant and host validation status when validationErrors change
  useEffect(() => {
    if (!validationErrors && !validParticipants) return;

    const invalidInputs = new Set(validationErrors?.map((err) => err.input.trim()) || []);
    const validInputs = new Set(validParticipants?.map((input) => input.trim()) || []);

    // Check if host field has a validation error
    const hostInput = formData.host?.trim();
    if (hostInput) {
      const hostValidationError = validationErrors?.find((err) => err.input.trim() === hostInput);
      setHostError(hostValidationError?.reason || null);
    } else {
      setHostError(null);
    }

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
  }, [validationErrors, validParticipants, formData.host]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  // Validation handler stubs
  const validateDurationField = () => {
    const result = validateDuration(formData.expectedDurationMinutes);
    setDurationError(result.error || null);
  };

  const validateReminderField = () => {
    // Validate array directly since ReminderSelector ensures valid input
    // Still validate range to catch any edge cases
    const MAX_REMINDER_MINUTES = 10080;
    const invalidValues = formData.reminderMinutesArray.filter(
      (val) => val < 1 || val > MAX_REMINDER_MINUTES || !Number.isInteger(val)
    );

    if (invalidValues.length > 0) {
      setReminderError(
        `All reminder values must be integers between 1 and ${MAX_REMINDER_MINUTES} minutes`
      );
    } else {
      setReminderError(null);
    }
  };

  const validateMaxPlayersField = () => {
    const result = validateMaxPlayers(formData.maxPlayers);
    setMaxPlayersError(result.error || null);
  };

  const validateLocationField = () => {
    const MAX_LOCATION_LENGTH = 500;
    const result = validateCharacterLimit(formData.where, MAX_LOCATION_LENGTH, 'Location');
    setLocationError(result.error || result.warning || null);
  };

  const validateDescriptionField = () => {
    const MAX_DESCRIPTION_LENGTH = 2000;
    const result = validateCharacterLimit(
      formData.description,
      MAX_DESCRIPTION_LENGTH,
      'Description'
    );
    setDescriptionError(result.error || result.warning || null);
  };

  const validateSignupInstructionsField = () => {
    const MAX_SIGNUP_INSTRUCTIONS_LENGTH = 1000;
    const result = validateCharacterLimit(
      formData.signupInstructions,
      MAX_SIGNUP_INSTRUCTIONS_LENGTH,
      'Signup Instructions'
    );
    setSignupInstructionsError(result.error || result.warning || null);
  };

  const validateScheduledAtField = () => {
    const result = validateFutureDate(formData.scheduledAt);
    setScheduledAtError(result.error || null);
  };

  // Helper text generators with character counts
  const getLocationHelperText = () => {
    if (locationError) return locationError;
    const MAX_LOCATION_LENGTH = 500;
    const count = formData.where.length;
    if (count === 0) return 'Game location (optional, up to 500 characters)';
    return `${count}/${MAX_LOCATION_LENGTH} characters`;
  };

  const getDescriptionHelperText = () => {
    if (descriptionError) return descriptionError;
    const MAX_DESCRIPTION_LENGTH = 2000;
    const count = formData.description.length;
    if (count === 0) return undefined;
    return `${count}/${MAX_DESCRIPTION_LENGTH} characters`;
  };

  const getSignupInstructionsHelperText = () => {
    if (signupInstructionsError) return signupInstructionsError;
    const MAX_SIGNUP_INSTRUCTIONS_LENGTH = 1000;
    const count = formData.signupInstructions.length;
    if (count === 0)
      return 'Special requirements or instructions (visible to host only after creation)';
    return `${count}/${MAX_SIGNUP_INSTRUCTIONS_LENGTH} characters`;
  };

  const handleSelectChange = (event: SelectChangeEvent) => {
    const { name, value } = event.target;
    if (name === 'signupMethod') {
      setFormData((prev) => ({ ...prev, signupMethod: value }));
    } else {
      setFormData((prev) => ({ ...prev, channelId: value }));
    }
  };

  const handleDateChange = (date: Date | null) => {
    setFormData((prev) => ({ ...prev, scheduledAt: date }));
    validateScheduledAtField();
  };

  const handleDurationChange = (minutes: number | null) => {
    setFormData((prev) => ({ ...prev, expectedDurationMinutes: minutes }));
    validateDurationField();
  };

  const handleReminderChange = (minutes: number[]) => {
    setFormData((prev) => ({
      ...prev,
      reminderMinutesArray: minutes,
      reminderMinutes: minutes.join(', '),
    }));
    validateReminderField();
  };

  const handleParticipantsChange = (participants: EditableParticipantInput[]) => {
    setFormData((prev) => ({ ...prev, participants }));
  };

  const handleThumbnailChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] || null;

    if (file) {
      // Validate file size (<5MB)
      if (file.size > UI.MAX_FILE_SIZE_BYTES) {
        alert('Thumbnail must be less than 5MB');
        return;
      }

      // Validate file type
      const validTypes = ['image/png', 'image/jpeg', 'image/gif', 'image/webp'];
      if (!validTypes.includes(file.type)) {
        alert('Thumbnail must be PNG, JPEG, GIF, or WebP');
        return;
      }
    }

    setFormData((prev) => ({
      ...prev,
      thumbnailFile: file,
      removeThumbnail: false,
    }));
  };

  const handleImageChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] || null;

    if (file) {
      // Validate file size (<5MB)
      if (file.size > UI.MAX_FILE_SIZE_BYTES) {
        alert('Banner image must be less than 5MB');
        return;
      }

      // Validate file type
      const validTypes = ['image/png', 'image/jpeg', 'image/gif', 'image/webp'];
      if (!validTypes.includes(file.type)) {
        alert('Banner must be PNG, JPEG, GIF, or WebP');
        return;
      }
    }

    setFormData((prev) => ({
      ...prev,
      imageFile: file,
      removeImage: false,
    }));
  };

  const handleRemoveThumbnail = () => {
    setFormData((prev) => ({
      ...prev,
      thumbnailFile: null,
      removeThumbnail: true,
    }));
  };

  const handleRemoveImage = () => {
    setFormData((prev) => ({
      ...prev,
      imageFile: null,
      removeImage: true,
    }));
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

    const hasValidationErrors =
      !!durationError ||
      !!reminderError ||
      !!maxPlayersError ||
      !!locationError ||
      !!descriptionError ||
      !!signupInstructionsError ||
      !!scheduledAtError;

    if (hasValidationErrors) {
      setError('Please fix all validation errors before submitting.');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      await onSubmit(formData);
    } catch (err: unknown) {
      console.error('Failed to submit form:', err);
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
        <Typography variant="h4" component="h1" gutterBottom>
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
            InputLabelProps={{
              sx: { fontSize: '1.1rem' },
            }}
            sx={{ mb: 1 }}
          />

          {isBotManager && (
            <TextField
              fullWidth
              label="Game Host"
              name="host"
              value={formData.host}
              onChange={handleChange}
              margin="normal"
              disabled={loading}
              placeholder={user?.username || 'Your username'}
              helperText={
                hostError || 'Game host (@mention or username). Leave empty to host yourself.'
              }
              error={!!hostError}
              InputLabelProps={{
                sx: { fontSize: '1.1rem' },
              }}
              sx={{ mb: 1 }}
            />
          )}

          <TextField
            fullWidth
            label="Location"
            name="where"
            value={formData.where}
            onChange={handleChange}
            onBlur={validateLocationField}
            margin="normal"
            multiline
            rows={2}
            helperText={getLocationHelperText()}
            error={!!locationError}
            disabled={loading}
            inputProps={{ maxLength: 500 }}
            InputLabelProps={{
              sx: { fontSize: '1.1rem' },
            }}
            sx={{ mb: 1 }}
          />

          <DateTimePicker
            label="Scheduled Time *"
            value={formData.scheduledAt}
            onChange={handleDateChange}
            disablePast
            disabled={loading}
            slotProps={{
              textField: {
                error: !!scheduledAtError,
                helperText: scheduledAtError,
                InputLabelProps: {
                  sx: { fontSize: '1.1rem' },
                },
              },
            }}
            sx={{ width: '100%', mt: 1, mb: 1 }}
          />

          <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap', mb: 1, mt: 1 }}>
            <Box sx={{ flex: '1 1 45%', minWidth: '200px' }}>
              <DurationSelector
                value={formData.expectedDurationMinutes}
                onChange={handleDurationChange}
                error={!!durationError}
                helperText={durationError || undefined}
              />
            </Box>

            <Box sx={{ flex: '1 1 45%', minWidth: '200px' }}>
              <ReminderSelector
                value={formData.reminderMinutesArray}
                onChange={handleReminderChange}
                error={!!reminderError}
                helperText={reminderError || 'Select one or more reminder times'}
              />
            </Box>
          </Box>

          {canChangeChannel ? (
            <FormControl fullWidth margin="normal" required sx={{ mb: 1 }}>
              <InputLabel sx={{ fontSize: '1.1rem' }}>Channel</InputLabel>
              <Select
                value={formData.channelId}
                onChange={handleSelectChange}
                label="Channel"
                disabled={loading}
              >
                {channels.map((channel) => (
                  <MenuItem key={channel.id} value={channel.id}>
                    # {channel.channel_name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          ) : (
            <Box sx={{ mb: 2 }}>
              <Typography variant="body1" sx={{ fontSize: '1.1rem' }}>
                <strong>Channel:</strong> #{' '}
                {channels.find((c) => c.id === formData.channelId)?.channel_name || 'Unknown'}
              </Typography>
            </Box>
          )}

          <FormControl fullWidth margin="normal" sx={{ mb: 1 }}>
            <InputLabel sx={{ fontSize: '1.1rem' }}>Signup Method</InputLabel>
            <Select
              value={formData.signupMethod}
              onChange={handleSelectChange}
              name="signupMethod"
              label="Signup Method"
              disabled={loading || availableSignupMethods.length === 1}
              data-testid="signup-method-select"
            >
              {availableSignupMethods.map((method) => (
                <MenuItem key={method} value={method}>
                  {SIGNUP_METHOD_INFO[method as SignupMethod].displayName}
                </MenuItem>
              ))}
            </Select>
            <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, ml: 1.5 }}>
              {SIGNUP_METHOD_INFO[formData.signupMethod as SignupMethod]?.description ||
                'Select how players can join this game'}
            </Typography>
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
            onBlur={validateDescriptionField}
            margin="normal"
            disabled={loading}
            helperText={getDescriptionHelperText()}
            error={!!descriptionError}
            InputLabelProps={{
              sx: { fontSize: '1.1rem' },
            }}
            sx={{ mb: 1 }}
          />

          <TextField
            fullWidth
            multiline
            rows={2}
            label="Signup Instructions"
            name="signupInstructions"
            value={formData.signupInstructions}
            onChange={handleChange}
            onBlur={validateSignupInstructionsField}
            margin="normal"
            helperText={getSignupInstructionsHelperText()}
            error={!!signupInstructionsError}
            disabled={loading}
            sx={{ mb: 1 }}
          />

          <Grid container spacing={2} sx={{ mt: 1, mb: 2 }}>
            <Grid size={{ xs: 12, md: 6 }}>
              <TextField
                fullWidth
                label="Max Players"
                name="maxPlayers"
                type="number"
                value={formData.maxPlayers}
                onChange={handleChange}
                onBlur={validateMaxPlayersField}
                helperText={maxPlayersError || 'Leave empty to use channel/server default'}
                error={!!maxPlayersError}
                disabled={loading}
                inputProps={{ min: 1, max: 100 }}
                InputLabelProps={{
                  sx: { fontSize: '1.1rem' },
                }}
              />
            </Grid>
          </Grid>

          <Box sx={{ mt: 3, mb: 2 }}>
            <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 'bold' }}>
              Images (optional)
            </Typography>
            <Box sx={{ mt: 2 }}>
              <Typography variant="subtitle2" gutterBottom>
                Thumbnail Image
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Button variant="outlined" component="label" disabled={loading}>
                  Choose Thumbnail
                  <input
                    type="file"
                    hidden
                    accept="image/png,image/jpeg,image/gif,image/webp"
                    onChange={handleThumbnailChange}
                  />
                </Button>
                {formData.thumbnailFile && (
                  <Typography variant="body2">{formData.thumbnailFile.name}</Typography>
                )}
                {mode === 'edit' &&
                  initialData?.has_thumbnail &&
                  !formData.thumbnailFile &&
                  !formData.removeThumbnail && (
                    <Button
                      size="small"
                      color="error"
                      onClick={handleRemoveThumbnail}
                      disabled={loading}
                    >
                      Remove Thumbnail
                    </Button>
                  )}
              </Box>
            </Box>

            <Box sx={{ mt: 2 }}>
              <Typography variant="subtitle2" gutterBottom>
                Banner Image
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Button variant="outlined" component="label" disabled={loading}>
                  Choose Banner
                  <input
                    type="file"
                    hidden
                    accept="image/png,image/jpeg,image/gif,image/webp"
                    onChange={handleImageChange}
                  />
                </Button>
                {formData.imageFile && (
                  <Typography variant="body2">{formData.imageFile.name}</Typography>
                )}
                {mode === 'edit' &&
                  initialData?.has_image &&
                  !formData.imageFile &&
                  !formData.removeImage && (
                    <Button
                      size="small"
                      color="error"
                      onClick={handleRemoveImage}
                      disabled={loading}
                    >
                      Remove Banner
                    </Button>
                  )}
              </Box>
            </Box>
          </Box>

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
