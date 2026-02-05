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
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormHelperText,
  Box,
  Typography,
  Divider,
  Chip,
  OutlinedInput,
  SelectChangeEvent,
} from '@mui/material';
import LockIcon from '@mui/icons-material/Lock';
import {
  GameTemplate,
  Channel,
  DiscordRole,
  TemplateCreateRequest,
  TemplateUpdateRequest,
} from '../types';
import { formatDurationForDisplay, parseDurationString } from './GameForm';
import { UI } from '../constants/ui';

interface TemplateFormProps {
  open: boolean;
  template: GameTemplate | null;
  guildId: string;
  channels: Channel[];
  roles: DiscordRole[];
  onClose: () => void;
  onSubmit: (data: TemplateCreateRequest | TemplateUpdateRequest) => Promise<void>;
}

export const TemplateForm: FC<TemplateFormProps> = ({
  open,
  template,
  guildId,
  channels,
  roles,
  onClose,
  onSubmit,
}) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [channelId, setChannelId] = useState('');
  const [maxPlayers, setMaxPlayers] = useState('');
  const [expectedDuration, setExpectedDuration] = useState('');
  const [reminderMinutes, setReminderMinutes] = useState('');
  const [where, setWhere] = useState('');
  const [signupInstructions, setSignupInstructions] = useState('');
  const [notifyRoleIds, setNotifyRoleIds] = useState<string[]>([]);
  const [allowedPlayerRoleIds, setAllowedPlayerRoleIds] = useState<string[]>([]);
  const [allowedHostRoleIds, setAllowedHostRoleIds] = useState<string[]>([]);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (template) {
      setName(template.name);
      setDescription(template.description || '');
      setChannelId(template.channel_id);
      setMaxPlayers(template.max_players !== null ? String(template.max_players) : '');
      setExpectedDuration(
        template.expected_duration_minutes !== null
          ? formatDurationForDisplay(template.expected_duration_minutes)
          : ''
      );
      setReminderMinutes(template.reminder_minutes ? template.reminder_minutes.join(', ') : '');
      setWhere(template.where || '');
      setSignupInstructions(template.signup_instructions || '');
      setNotifyRoleIds(template.notify_role_ids || []);
      setAllowedPlayerRoleIds(template.allowed_player_role_ids || []);
      setAllowedHostRoleIds(template.allowed_host_role_ids || []);
    } else {
      // Reset for new template
      setName('');
      setDescription('');
      setChannelId(channels.length > 0 ? channels[0]!.id : '');
      setMaxPlayers('');
      setExpectedDuration('');
      setReminderMinutes('');
      setWhere('');
      setSignupInstructions('');
      setNotifyRoleIds([]);
      setAllowedPlayerRoleIds([]);
      setAllowedHostRoleIds([]);
    }
    setErrors({});
  }, [template, channels, open]);

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!name.trim()) {
      newErrors.name = 'Template name is required';
    }

    if (!channelId) {
      newErrors.channelId = 'Channel is required';
    }

    if (maxPlayers && (parseInt(maxPlayers) < 1 || parseInt(maxPlayers) > UI.MAX_PLAYERS_LIMIT)) {
      newErrors.maxPlayers = `Max players must be between 1 and ${UI.MAX_PLAYERS_LIMIT}`;
    }

    if (expectedDuration && parseDurationString(expectedDuration) === null) {
      newErrors.expectedDuration = 'Invalid duration format (e.g., 2h, 90m, 1h 30m)';
    }

    if (reminderMinutes) {
      const minutes = reminderMinutes.split(',').map((m) => m.trim());
      for (const m of minutes) {
        if (isNaN(parseInt(m)) || parseInt(m) < 1) {
          newErrors.reminderMinutes =
            'Reminder minutes must be positive numbers separated by commas';
          break;
        }
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validate()) return;

    setSubmitting(true);
    try {
      const data: any = {
        name: name.trim(),
        description: description.trim() || null,
        channel_id: channelId,
        notify_role_ids: notifyRoleIds.length > 0 ? notifyRoleIds : null,
        allowed_player_role_ids: allowedPlayerRoleIds.length > 0 ? allowedPlayerRoleIds : null,
        allowed_host_role_ids: allowedHostRoleIds.length > 0 ? allowedHostRoleIds : null,
        max_players: maxPlayers ? parseInt(maxPlayers) : null,
        expected_duration_minutes: expectedDuration ? parseDurationString(expectedDuration) : null,
        reminder_minutes: reminderMinutes
          ? reminderMinutes.split(',').map((m) => parseInt(m.trim()))
          : null,
        where: where.trim() || null,
        signup_instructions: signupInstructions.trim() || null,
      };

      if (template) {
        // For updates, remove null values so backend only updates provided fields
        const updateData: any = {};
        for (const [key, value] of Object.entries(data)) {
          if (value !== null) {
            updateData[key] = value;
          }
        }
        await onSubmit(updateData as TemplateUpdateRequest);
      } else {
        await onSubmit({ ...data, guild_id: guildId } as TemplateCreateRequest);
      }

      onClose();
    } catch (error: any) {
      setErrors(error.response?.data?.detail || 'Failed to save template');
    } finally {
      setSubmitting(false);
    }
  };

  const handleRoleChange = (
    event: SelectChangeEvent<string[]>,
    setter: (value: string[]) => void
  ) => {
    const value = event.target.value;
    setter(typeof value === 'string' ? value.split(',') : value);
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>{template ? 'Edit Template' : 'Create Template'}</DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
          {errors.submit && (
            <Typography color="error" variant="body2">
              {errors.submit}
            </Typography>
          )}

          <TextField
            label="Template Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            error={!!errors.name}
            helperText={errors.name}
            fullWidth
            required
          />

          <TextField
            label="Description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            multiline
            rows={2}
            fullWidth
          />

          <Divider>
            <Chip label="Locked Settings" icon={<LockIcon />} size="small" />
          </Divider>

          <Typography variant="caption" color="text.secondary">
            These settings are locked and cannot be changed by game hosts.
          </Typography>

          <FormControl fullWidth required error={!!errors.channelId}>
            <InputLabel>Channel</InputLabel>
            <Select
              value={channelId}
              onChange={(e) => setChannelId(e.target.value)}
              label="Channel"
            >
              {channels.map((channel) => (
                <MenuItem key={channel.id} value={channel.id}>
                  {channel.channel_name}
                </MenuItem>
              ))}
            </Select>
            {errors.channelId && <FormHelperText>{errors.channelId}</FormHelperText>}
          </FormControl>

          <FormControl fullWidth>
            <InputLabel>Notify Roles</InputLabel>
            <Select
              multiple
              value={notifyRoleIds}
              onChange={(e) => handleRoleChange(e, setNotifyRoleIds)}
              input={<OutlinedInput label="Notify Roles" />}
              renderValue={(selected) =>
                selected.map((id) => roles.find((r) => r.id === id)?.name || id).join(', ')
              }
            >
              {roles.map((role) => (
                <MenuItem key={role.id} value={role.id}>
                  {role.name.startsWith('@') ? role.name : `@${role.name}`}
                </MenuItem>
              ))}
            </Select>
            <FormHelperText>Roles to notify when a game is created</FormHelperText>
          </FormControl>

          <FormControl fullWidth>
            <InputLabel>Allowed Player Roles</InputLabel>
            <Select
              multiple
              value={allowedPlayerRoleIds}
              onChange={(e) => handleRoleChange(e, setAllowedPlayerRoleIds)}
              input={<OutlinedInput label="Allowed Player Roles" />}
              renderValue={(selected) =>
                selected
                  .map((id) => {
                    const role = roles.find((r) => r.id === id);
                    if (!role) return id;
                    return role.name.startsWith('@') ? role.name : `@${role.name}`;
                  })
                  .join(', ')
              }
            >
              {roles.map((role) => (
                <MenuItem key={role.id} value={role.id}>
                  {role.name.startsWith('@') ? role.name : `@${role.name}`}
                </MenuItem>
              ))}
            </Select>
            <FormHelperText>Roles allowed to join games (empty = all)</FormHelperText>
          </FormControl>

          <FormControl fullWidth>
            <InputLabel>Allowed Host Roles</InputLabel>
            <Select
              multiple
              value={allowedHostRoleIds}
              onChange={(e) => handleRoleChange(e, setAllowedHostRoleIds)}
              input={<OutlinedInput label="Allowed Host Roles" />}
              renderValue={(selected) =>
                selected
                  .map((id) => {
                    const role = roles.find((r) => r.id === id);
                    if (!role) return id;
                    return role.name.startsWith('@') ? role.name : `@${role.name}`;
                  })
                  .join(', ')
              }
            >
              {roles.map((role) => (
                <MenuItem key={role.id} value={role.id}>
                  {role.name.startsWith('@') ? role.name : `@${role.name}`}
                </MenuItem>
              ))}
            </Select>
            <FormHelperText>Roles allowed to use this template (empty = all)</FormHelperText>
          </FormControl>

          <Divider>
            <Chip label="Pre-populated Settings" size="small" />
          </Divider>

          <Typography variant="caption" color="text.secondary">
            These provide default values that game hosts can override.
          </Typography>

          <TextField
            label="Max Players"
            type="number"
            value={maxPlayers}
            onChange={(e) => setMaxPlayers(e.target.value)}
            error={!!errors.maxPlayers}
            helperText={errors.maxPlayers || 'Leave empty for unlimited'}
            fullWidth
            inputProps={{ min: 1, max: 100 }}
          />

          <TextField
            label="Expected Duration"
            value={expectedDuration}
            onChange={(e) => setExpectedDuration(e.target.value)}
            error={!!errors.expectedDuration}
            helperText={errors.expectedDuration || 'e.g., 2h, 90m, 1h 30m'}
            fullWidth
          />

          <TextField
            label="Reminder Minutes"
            value={reminderMinutes}
            onChange={(e) => setReminderMinutes(e.target.value)}
            error={!!errors.reminderMinutes}
            helperText={
              errors.reminderMinutes || 'Comma-separated minutes before game (e.g., 60, 15)'
            }
            fullWidth
          />

          <TextField
            label="Location"
            value={where}
            onChange={(e) => setWhere(e.target.value)}
            helperText="Default location for games"
            fullWidth
          />

          <TextField
            label="Signup Instructions"
            value={signupInstructions}
            onChange={(e) => setSignupInstructions(e.target.value)}
            helperText="Default instructions for players"
            multiline
            rows={3}
            fullWidth
          />
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={submitting}>
          Cancel
        </Button>
        <Button onClick={handleSubmit} variant="contained" disabled={submitting}>
          {submitting ? 'Saving...' : template ? 'Update' : 'Create'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
