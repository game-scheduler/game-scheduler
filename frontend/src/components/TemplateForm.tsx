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

import { FC, useState, useEffect, useRef } from 'react';
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
  IconButton,
  List,
  ListItem,
  ListItemText,
} from '@mui/material';
import LockIcon from '@mui/icons-material/Lock';
import DragHandleIcon from '@mui/icons-material/DragHandle';
import {
  GameTemplate,
  Channel,
  DiscordRole,
  TemplateCreateRequest,
  TemplateUpdateRequest,
} from '../types';
import { UI } from '../constants/ui';
import { Time } from '../constants/time';
import { validateMaxPlayers, validateCharacterLimit } from '../utils/fieldValidation';
import { DurationSelector } from './DurationSelector';
import { ReminderSelector } from './ReminderSelector';

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
  const [expectedDuration, setExpectedDuration] = useState<number | null>(null);
  const [reminderMinutesArray, setReminderMinutesArray] = useState<number[]>([]);
  const [where, setWhere] = useState('');
  const [signupInstructions, setSignupInstructions] = useState('');
  const [archiveChannelId, setArchiveChannelId] = useState<string>('');
  const [archiveDelayDays, setArchiveDelayDays] = useState<string>('');
  const [archiveDelayHours, setArchiveDelayHours] = useState<string>('');
  const [archiveDelayMinutes, setArchiveDelayMinutes] = useState<string>('');
  const [notifyRoleIds, setNotifyRoleIds] = useState<string[]>([]);
  const [allowedPlayerRoleIds, setAllowedPlayerRoleIds] = useState<string[]>([]);
  const [allowedHostRoleIds, setAllowedHostRoleIds] = useState<string[]>([]);
  const [signupPriorityRoleIds, setSignupPriorityRoleIds] = useState<string[]>([]);
  const [priorityRoleSelectorValue, setPriorityRoleSelectorValue] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  const dragItemIndex = useRef<number | null>(null);

  // Validation error state
  const [maxPlayersError, setMaxPlayersError] = useState('');
  const [descriptionError, setDescriptionError] = useState('');
  const [locationError, setLocationError] = useState('');
  const [signupInstructionsError, setSignupInstructionsError] = useState('');

  useEffect(() => {
    if (template) {
      setName(template.name);
      setDescription(template.description || '');
      setChannelId(template.channel_id);
      setMaxPlayers(template.max_players !== null ? String(template.max_players) : '');
      setExpectedDuration(template.expected_duration_minutes);

      setReminderMinutesArray(template.reminder_minutes || []);
      setWhere(template.where || '');
      setSignupInstructions(template.signup_instructions || '');
      setArchiveChannelId(template.archive_channel_id || '');
      setNotifyRoleIds(template.notify_role_ids || []);
      setAllowedPlayerRoleIds(template.allowed_player_role_ids || []);
      setAllowedHostRoleIds(template.allowed_host_role_ids || []);
      setSignupPriorityRoleIds(template.signup_priority_role_ids || []);
      if (template.archive_delay_seconds !== null && template.archive_delay_seconds !== undefined) {
        const totalSeconds = template.archive_delay_seconds;
        const days = Math.floor(totalSeconds / Time.SECONDS_PER_DAY);
        const hours = Math.floor((totalSeconds % Time.SECONDS_PER_DAY) / Time.SECONDS_PER_HOUR);
        const minutes = Math.floor(
          (totalSeconds % Time.SECONDS_PER_HOUR) / Time.SECONDS_PER_MINUTE
        );
        setArchiveDelayDays(days > 0 ? String(days) : '');
        setArchiveDelayHours(hours > 0 ? String(hours) : '');
        setArchiveDelayMinutes(minutes > 0 ? String(minutes) : '');
      } else {
        setArchiveDelayDays('');
        setArchiveDelayHours('');
        setArchiveDelayMinutes('');
      }
    } else {
      // Reset for new template
      setName('');
      setDescription('');
      setChannelId(channels.length > 0 ? channels[0]!.id : '');
      setMaxPlayers('');
      setExpectedDuration(null);

      setReminderMinutesArray([]);
      setWhere('');
      setSignupInstructions('');
      setArchiveChannelId('');
      setArchiveDelayDays('');
      setArchiveDelayHours('');
      setArchiveDelayMinutes('');
      setNotifyRoleIds([]);
      setAllowedPlayerRoleIds([]);
      setAllowedHostRoleIds([]);
      setSignupPriorityRoleIds([]);
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

    const MAX_DURATION_MINUTES = 1440;
    if (expectedDuration && (expectedDuration < 1 || expectedDuration > MAX_DURATION_MINUTES)) {
      newErrors.expectedDuration = `Duration must be between 1 and ${MAX_DURATION_MINUTES} minutes`;
    }

    const MAX_REMINDER_MINUTES = 10080;
    const invalidReminderValues = reminderMinutesArray.filter(
      (val) => val < 1 || val > MAX_REMINDER_MINUTES || !Number.isInteger(val)
    );
    if (invalidReminderValues.length > 0) {
      newErrors.reminderMinutes = `All reminder values must be integers between 1 and ${MAX_REMINDER_MINUTES} minutes`;
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const computeArchiveDelaySeconds = (
    days: string,
    hours: string,
    minutes: string
  ): number | null => {
    const d = days ? parseInt(days, 10) : 0;
    const h = hours ? parseInt(hours, 10) : 0;
    const m = minutes ? parseInt(minutes, 10) : 0;
    const total =
      d * Time.SECONDS_PER_DAY + h * Time.SECONDS_PER_HOUR + m * Time.SECONDS_PER_MINUTE;
    return total > 0 ? total : null;
  };

  const handleSubmit = async () => {
    if (!validate()) return;

    setSubmitting(true);
    try {
      const archiveDelaySecs = computeArchiveDelaySeconds(
        archiveDelayDays,
        archiveDelayHours,
        archiveDelayMinutes
      );

      const data: any = {
        name: name.trim(),
        description: description.trim() || null,
        channel_id: channelId,
        archive_channel_id: archiveChannelId || null,
        archive_delay_seconds: archiveDelaySecs,
        notify_role_ids: notifyRoleIds.length > 0 ? notifyRoleIds : null,
        allowed_player_role_ids: allowedPlayerRoleIds.length > 0 ? allowedPlayerRoleIds : null,
        allowed_host_role_ids: allowedHostRoleIds.length > 0 ? allowedHostRoleIds : null,
        signup_priority_role_ids: signupPriorityRoleIds.length > 0 ? signupPriorityRoleIds : null,
        max_players: maxPlayers ? parseInt(maxPlayers) : null,
        expected_duration_minutes: expectedDuration,
        reminder_minutes: reminderMinutesArray.length > 0 ? reminderMinutesArray : null,
        where: where.trim() || null,
        signup_instructions: signupInstructions.trim() || null,
      };

      if (template) {
        await onSubmit(data as TemplateUpdateRequest);
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

  const handleReminderChange = (minutes: number[]) => {
    setReminderMinutesArray(minutes);
  };

  const handleRoleChange = (
    event: SelectChangeEvent<string[]>,
    setter: (value: string[]) => void
  ) => {
    const value = event.target.value;
    setter(typeof value === 'string' ? value.split(',') : value);
  };

  const handleAddPriorityRole = (roleId: string) => {
    if (
      roleId &&
      !signupPriorityRoleIds.includes(roleId) &&
      signupPriorityRoleIds.length < UI.MAX_SIGNUP_PRIORITY_ROLES
    ) {
      setSignupPriorityRoleIds([...signupPriorityRoleIds, roleId]);
      setPriorityRoleSelectorValue('');
    }
  };

  const handleRemovePriorityRole = (id: string) => {
    setSignupPriorityRoleIds(signupPriorityRoleIds.filter((r) => r !== id));
  };

  const handlePriorityDragStart = (index: number) => {
    dragItemIndex.current = index;
  };

  const handlePriorityDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handlePriorityDrop = (targetIndex: number) => {
    if (dragItemIndex.current === null || dragItemIndex.current === targetIndex) return;
    const reordered = [...signupPriorityRoleIds];
    const [moved] = reordered.splice(dragItemIndex.current, 1);
    reordered.splice(targetIndex, 0, moved!);
    setSignupPriorityRoleIds(reordered);
    dragItemIndex.current = null;
  };

  const handlePriorityDragEnd = () => {
    dragItemIndex.current = null;
  };

  const handleMaxPlayersBlur = () => {
    const result = validateMaxPlayers(maxPlayers);
    setMaxPlayersError(result.error || '');
  };

  const handleDescriptionBlur = () => {
    const result = validateCharacterLimit(description, UI.MAX_DESCRIPTION_LENGTH, 'Description');
    setDescriptionError(result.error || result.warning || '');
  };

  const handleLocationBlur = () => {
    const result = validateCharacterLimit(where, UI.MAX_LOCATION_LENGTH, 'Location');
    setLocationError(result.error || result.warning || '');
  };

  const handleSignupInstructionsBlur = () => {
    const result = validateCharacterLimit(
      signupInstructions,
      UI.MAX_SIGNUP_INSTRUCTIONS_LENGTH,
      'Signup Instructions'
    );
    setSignupInstructionsError(result.error || result.warning || '');
  };

  const getDescriptionHelperText = () => {
    if (descriptionError) return descriptionError;
    const count = description.length;
    if (count === 0) return undefined;
    return `${count} / ${UI.MAX_DESCRIPTION_LENGTH} characters`;
  };

  const getLocationHelperText = () => {
    if (locationError) return locationError;
    const count = where.length;
    if (count === 0) return 'Default location for games';
    return `${count} / ${UI.MAX_LOCATION_LENGTH} characters`;
  };

  const getSignupInstructionsHelperText = () => {
    if (signupInstructionsError) return signupInstructionsError;
    const count = signupInstructions.length;
    if (count === 0) return 'Default instructions for players';
    return `${count} / ${UI.MAX_SIGNUP_INSTRUCTIONS_LENGTH} characters`;
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
            onBlur={handleDescriptionBlur}
            error={!!descriptionError}
            helperText={getDescriptionHelperText()}
            multiline
            minRows={6}
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
            <InputLabel>Archive Channel</InputLabel>
            <Select
              value={archiveChannelId}
              onChange={(e) => setArchiveChannelId(e.target.value)}
              label="Archive Channel"
            >
              <MenuItem value="">
                <em>None (delete announcement only)</em>
              </MenuItem>
              {channels.map((channel) => (
                <MenuItem key={channel.id} value={channel.id}>
                  {channel.channel_name}
                </MenuItem>
              ))}
            </Select>
            <FormHelperText>
              Channel where completed announcements are reposted (leave empty to delete only)
            </FormHelperText>
          </FormControl>

          <Box>
            <Typography variant="body2" sx={{ mb: 1 }}>
              Archive Delay
            </Typography>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <TextField
                label="Days"
                type="number"
                value={archiveDelayDays}
                onChange={(e) => setArchiveDelayDays(e.target.value)}
                inputProps={{ min: 0 }}
                sx={{ flex: 1 }}
              />
              <TextField
                label="Hours"
                type="number"
                value={archiveDelayHours}
                onChange={(e) => setArchiveDelayHours(e.target.value)}
                inputProps={{ min: 0, max: 23 }}
                sx={{ flex: 1 }}
              />
              <TextField
                label="Minutes"
                type="number"
                value={archiveDelayMinutes}
                onChange={(e) => setArchiveDelayMinutes(e.target.value)}
                inputProps={{ min: 0, max: 59 }}
                sx={{ flex: 1 }}
              />
            </Box>
            <Typography variant="caption" color="text.secondary">
              How long after completion before archiving (leave empty to archive immediately)
            </Typography>
          </Box>

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

          <Box>
            <Typography variant="body2" sx={{ mb: 1 }}>
              Role Priority
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, mb: 1 }}>
              <FormControl sx={{ flex: 1 }}>
                <InputLabel id="priority-role-select-label">Add Priority Role</InputLabel>
                <Select
                  labelId="priority-role-select-label"
                  inputProps={{ 'aria-label': 'Add Priority Role' }}
                  value={priorityRoleSelectorValue}
                  onChange={(e) => handleAddPriorityRole(e.target.value)}
                  input={<OutlinedInput label="Add Priority Role" />}
                  disabled={signupPriorityRoleIds.length >= UI.MAX_SIGNUP_PRIORITY_ROLES}
                >
                  {roles
                    .filter((r) => !signupPriorityRoleIds.includes(r.id))
                    .map((role) => (
                      <MenuItem key={role.id} value={role.id}>
                        {role.name.startsWith('@') ? role.name : `@${role.name}`}
                      </MenuItem>
                    ))}
                </Select>
              </FormControl>
            </Box>
            <List dense disablePadding>
              {signupPriorityRoleIds.map((id, index) => {
                const role = roles.find((r) => r.id === id);
                const displayName = role
                  ? role.name.startsWith('@')
                    ? role.name
                    : `@${role.name}`
                  : id;
                return (
                  <ListItem
                    key={id}
                    draggable
                    onDragStart={() => handlePriorityDragStart(index)}
                    onDragOver={handlePriorityDragOver}
                    onDrop={() => handlePriorityDrop(index)}
                    onDragEnd={handlePriorityDragEnd}
                    sx={{
                      border: '1px solid',
                      borderColor: 'divider',
                      borderRadius: 1,
                      mb: 0.5,
                      cursor: 'grab',
                    }}
                    secondaryAction={
                      <IconButton
                        edge="end"
                        aria-label={`Remove ${displayName}`}
                        size="small"
                        onClick={() => handleRemovePriorityRole(id)}
                      >
                        <Typography variant="caption">✕</Typography>
                      </IconButton>
                    }
                  >
                    <DragHandleIcon sx={{ mr: 1, color: 'text.secondary', fontSize: 20 }} />
                    <ListItemText primary={displayName} />
                  </ListItem>
                );
              })}
            </List>
            <FormHelperText>
              Role join priority order for Role-Based signup (max 8, drag to reorder)
            </FormHelperText>
          </Box>

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
            onBlur={handleMaxPlayersBlur}
            error={!!maxPlayersError || !!errors.maxPlayers}
            helperText={maxPlayersError || errors.maxPlayers || 'Leave empty for unlimited'}
            fullWidth
            inputProps={{ min: 1, max: 100 }}
          />

          <DurationSelector
            value={expectedDuration}
            onChange={setExpectedDuration}
            error={!!errors.expectedDuration}
            helperText={errors.expectedDuration}
          />

          <ReminderSelector
            value={reminderMinutesArray}
            onChange={handleReminderChange}
            error={!!errors.reminderMinutes}
            helperText={errors.reminderMinutes || 'Select one or more reminder times'}
          />

          <TextField
            label="Location"
            value={where}
            onChange={(e) => setWhere(e.target.value)}
            onBlur={handleLocationBlur}
            error={!!locationError}
            helperText={getLocationHelperText()}
            fullWidth
          />

          <TextField
            label="Signup Instructions"
            value={signupInstructions}
            onChange={(e) => setSignupInstructions(e.target.value)}
            onBlur={handleSignupInstructionsBlur}
            error={!!signupInstructionsError}
            helperText={getSignupInstructionsHelperText()}
            multiline
            minRows={6}
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
