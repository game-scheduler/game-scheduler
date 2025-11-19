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


import { FC, useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Container,
  Typography,
  Card,
  CardContent,
  TextField,
  Button,
  Box,
  CircularProgress,
  Alert,
  FormControlLabel,
  Checkbox,
} from '@mui/material';
import SaveIcon from '@mui/icons-material/Save';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import { apiClient } from '../api/client';
import { Channel, Guild } from '../types';
import { InheritancePreview } from '../components/InheritancePreview';

export const ChannelConfig: FC = () => {
  const { channelId } = useParams<{ channelId: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  
  const [channel, setChannel] = useState<Channel | null>(null);
  const [guild, setGuild] = useState<Guild | null>(null);
  const [formData, setFormData] = useState({
    isActive: true,
    maxPlayers: '',
    reminderMinutes: '',
    defaultRules: '',
    allowedHostRoleIds: '',
    gameCategory: '',
  });

  useEffect(() => {
    const fetchData = async () => {
      if (!channelId) return;

      try {
        setLoading(true);
        setError(null);

        const channelResponse = await apiClient.get<Channel>(`/api/v1/channels/${channelId}`);
        const channelData = channelResponse.data;
        
        setChannel(channelData);

        const guildResponse = await apiClient.get<Guild>(`/api/v1/guilds/${channelData.guildId}`);
        setGuild(guildResponse.data);
        
        setFormData({
          isActive: channelData.isActive,
          maxPlayers: channelData.maxPlayers?.toString() || '',
          reminderMinutes: channelData.reminderMinutes?.join(', ') || '',
          defaultRules: channelData.defaultRules || '',
          allowedHostRoleIds: channelData.allowedHostRoleIds?.join(', ') || '',
          gameCategory: channelData.gameCategory || '',
        });
      } catch (err: any) {
        console.error('Failed to fetch channel:', err);
        setError(err.response?.data?.detail || 'Failed to load channel configuration.');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [channelId]);

  const handleSave = async () => {
    if (!channelId) return;

    try {
      setSaving(true);
      setError(null);
      setSuccess(false);

      const reminderMinutes = formData.reminderMinutes
        ? formData.reminderMinutes
            .split(',')
            .map((s) => parseInt(s.trim()))
            .filter((n) => !isNaN(n))
        : null;

      const allowedRoleIds = formData.allowedHostRoleIds
        ? formData.allowedHostRoleIds
            .split(',')
            .map((s) => s.trim())
            .filter((s) => s.length > 0)
        : null;

      await apiClient.put(`/api/v1/channels/${channelId}`, {
        is_active: formData.isActive,
        max_players: formData.maxPlayers ? parseInt(formData.maxPlayers) : null,
        reminder_minutes: reminderMinutes,
        default_rules: formData.defaultRules || null,
        allowed_host_role_ids: allowedRoleIds,
        game_category: formData.gameCategory || null,
      });

      setSuccess(true);
      setTimeout(() => {
        navigate(`/guilds/${channel?.guildId}`);
      }, 1500);
    } catch (err: any) {
      console.error('Failed to save channel config:', err);
      setError(err.response?.data?.detail || 'Failed to save configuration. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Container sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Container>
    );
  }

  if (error && !channel) {
    return (
      <Container sx={{ mt: 4 }}>
        <Alert severity="error">{error}</Alert>
        <Button sx={{ mt: 2 }} onClick={() => navigate(-1)}>
          Back
        </Button>
      </Container>
    );
  }

  const resolvedMaxPlayers = formData.maxPlayers
    ? parseInt(formData.maxPlayers)
    : guild?.defaultMaxPlayers || 10;

  const resolvedReminders = formData.reminderMinutes
    ? formData.reminderMinutes
        .split(',')
        .map((s) => parseInt(s.trim()))
        .filter((n) => !isNaN(n))
    : guild?.defaultReminderMinutes || [60, 15];

  const resolvedRules = formData.defaultRules || guild?.defaultRules || '';

  return (
    <Container sx={{ mt: 4, mb: 4 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3, gap: 2 }}>
        <Button
          startIcon={<ArrowBackIcon />}
          onClick={() => navigate(`/guilds/${channel?.guildId}`)}
        >
          Back
        </Button>
        <Typography variant="h4">Channel Configuration</Typography>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {success && (
        <Alert severity="success" sx={{ mb: 2 }}>
          Configuration saved successfully! Redirecting...
        </Alert>
      )}

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Channel: {channel?.channelName}
          </Typography>
          <FormControlLabel
            control={
              <Checkbox
                checked={formData.isActive}
                onChange={(e) =>
                  setFormData({ ...formData, isActive: e.target.checked })
                }
              />
            }
            label="Active (enable game posting in this channel)"
          />
        </CardContent>
      </Card>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Channel Settings
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Override guild defaults for this channel. Leave fields empty to inherit from guild.
          </Typography>

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            <TextField
              label="Max Players (override)"
              type="number"
              value={formData.maxPlayers}
              onChange={(e) =>
                setFormData({ ...formData, maxPlayers: e.target.value })
              }
              inputProps={{ min: 1, max: 100 }}
              helperText="Leave empty to inherit guild default"
              fullWidth
            />

            <TextField
              label="Reminder Times (override)"
              value={formData.reminderMinutes}
              onChange={(e) =>
                setFormData({ ...formData, reminderMinutes: e.target.value })
              }
              helperText="Comma-separated minutes (e.g., 60, 15). Leave empty to inherit guild default."
              fullWidth
            />

            <TextField
              label="Default Rules (override)"
              value={formData.defaultRules}
              onChange={(e) =>
                setFormData({ ...formData, defaultRules: e.target.value })
              }
              multiline
              rows={4}
              helperText="Leave empty to inherit guild default"
              fullWidth
            />

            <TextField
              label="Allowed Host Role IDs (override)"
              value={formData.allowedHostRoleIds}
              onChange={(e) =>
                setFormData({ ...formData, allowedHostRoleIds: e.target.value })
              }
              helperText="Comma-separated role IDs. Leave empty to inherit guild default."
              fullWidth
            />

            <TextField
              label="Game Category"
              value={formData.gameCategory}
              onChange={(e) =>
                setFormData({ ...formData, gameCategory: e.target.value })
              }
              helperText="Category for filtering games (e.g., 'D&D', 'Board Games')"
              fullWidth
            />
          </Box>
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Resolved Settings Preview
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            These are the final settings that will be used for games in this channel.
          </Typography>

          <InheritancePreview
            label="Max Players"
            value={resolvedMaxPlayers}
            inherited={!formData.maxPlayers}
            inheritedFrom="guild"
          />
          <InheritancePreview
            label="Reminder Times"
            value={resolvedReminders}
            inherited={!formData.reminderMinutes}
            inheritedFrom="guild"
          />
          <InheritancePreview
            label="Default Rules"
            value={resolvedRules || 'Not set'}
            inherited={!formData.defaultRules}
            inheritedFrom="guild"
          />
        </CardContent>
      </Card>

      <Box sx={{ display: 'flex', gap: 2, mt: 3 }}>
        <Button
          variant="contained"
          startIcon={<SaveIcon />}
          onClick={handleSave}
          disabled={saving}
        >
          {saving ? 'Saving...' : 'Save Configuration'}
        </Button>
        <Button
          variant="outlined"
          onClick={() => navigate(`/guilds/${channel?.guildId}`)}
          disabled={saving}
        >
          Cancel
        </Button>
      </Box>
    </Container>
  );
};
