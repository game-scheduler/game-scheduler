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
import { Guild } from '../types';

export const GuildConfig: FC = () => {
  const { guildId } = useParams<{ guildId: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  
  const [guild, setGuild] = useState<Guild | null>(null);
  const [formData, setFormData] = useState({
    defaultMaxPlayers: 10,
    defaultReminderMinutes: '60, 15',
    defaultRules: '',
    allowedHostRoleIds: '',
    botManagerRoleIds: '',
    requireHostRole: false,
  });

  useEffect(() => {
    const fetchGuild = async () => {
      if (!guildId) return;

      try {
        setLoading(true);
        setError(null);

        const response = await apiClient.get<Guild>(`/api/v1/guilds/${guildId}`);
        const guildData = response.data;
        
        setGuild(guildData);
        setFormData({
          defaultMaxPlayers: guildData.default_max_players,
          defaultReminderMinutes: guildData.default_reminder_minutes.join(', '),
          defaultRules: guildData.default_rules || '',
          allowedHostRoleIds: guildData.allowed_host_role_ids.join(', '),
          botManagerRoleIds: (guildData.bot_manager_role_ids || []).join(', '),
          requireHostRole: guildData.require_host_role,
        });
      } catch (err: any) {
        console.error('Failed to fetch guild:', err);
        setError(err.response?.data?.detail || 'Failed to load guild configuration.');
      } finally {
        setLoading(false);
      }
    };

    fetchGuild();
  }, [guildId]);

  const handleSave = async () => {
    if (!guildId) return;

    try {
      setSaving(true);
      setError(null);
      setSuccess(false);

      const reminderMinutes = formData.defaultReminderMinutes
        .split(',')
        .map((s) => parseInt(s.trim()))
        .filter((n) => !isNaN(n));

      const allowedRoleIds = formData.allowedHostRoleIds
        .split(',')
        .map((s) => s.trim())
        .filter((s) => s.length > 0);

      const botManagerRoleIds = formData.botManagerRoleIds
        .split(',')
        .map((s) => s.trim())
        .filter((s) => s.length > 0);

      await apiClient.put(`/api/v1/guilds/${guildId}`, {
        default_max_players: formData.defaultMaxPlayers,
        default_reminder_minutes: reminderMinutes,
        default_rules: formData.defaultRules || null,
        allowed_host_role_ids: allowedRoleIds,
        bot_manager_role_ids: botManagerRoleIds.length > 0 ? botManagerRoleIds : null,
        require_host_role: formData.requireHostRole,
      });

      setSuccess(true);
      setTimeout(() => {
        navigate(`/guilds/${guildId}`);
      }, 1500);
    } catch (err: any) {
      console.error('Failed to save guild config:', err);
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

  if (error && !guild) {
    return (
      <Container sx={{ mt: 4 }}>
        <Alert severity="error">{error}</Alert>
        <Button sx={{ mt: 2 }} onClick={() => navigate(`/guilds/${guildId}`)}>
          Back to Guild
        </Button>
      </Container>
    );
  }

  return (
    <Container sx={{ mt: 4, mb: 4 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3, gap: 2 }}>
        <Button
          startIcon={<ArrowBackIcon />}
          onClick={() => navigate(`/guilds/${guildId}`)}
        >
          Back
        </Button>
        <Typography variant="h4">Guild Configuration</Typography>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {success && (
        <Alert severity="success" sx={{ mb: 2 }}>
          Configuration saved successfully! Redirecting...
        </Alert>
      )}

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Default Game Settings
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            These settings will be used as defaults for all new games in this guild.
            Individual channels and games can override these values.
          </Typography>

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            <TextField
              label="Default Max Players"
              type="number"
              value={formData.defaultMaxPlayers}
              onChange={(e) =>
                setFormData({ ...formData, defaultMaxPlayers: parseInt(e.target.value) || 10 })
              }
              inputProps={{ min: 1, max: 100 }}
              helperText="Default maximum number of players per game (1-100)"
              fullWidth
            />

            <TextField
              label="Default Reminder Times (minutes)"
              value={formData.defaultReminderMinutes}
              onChange={(e) =>
                setFormData({ ...formData, defaultReminderMinutes: e.target.value })
              }
              helperText="Comma-separated list of minutes before game to send reminders (e.g., 60, 15)"
              fullWidth
            />

            <TextField
              label="Default Rules"
              value={formData.defaultRules}
              onChange={(e) =>
                setFormData({ ...formData, defaultRules: e.target.value })
              }
              multiline
              rows={4}
              helperText="Default rules or guidelines that apply to all games"
              fullWidth
            />

            <TextField
              label="Allowed Host Role IDs"
              value={formData.allowedHostRoleIds}
              onChange={(e) =>
                setFormData({ ...formData, allowedHostRoleIds: e.target.value })
              }
              helperText="Comma-separated Discord role IDs that can host games. Leave empty to allow users with MANAGE_GUILD permission."
              fullWidth
            />

            <TextField
              label="Bot Manager Role IDs"
              value={formData.botManagerRoleIds}
              onChange={(e) =>
                setFormData({ ...formData, botManagerRoleIds: e.target.value })
              }
              helperText="Comma-separated Discord role IDs for Bot Managers (can edit/delete any game in this guild). Leave empty for none."
              fullWidth
            />

            <FormControlLabel
              control={
                <Checkbox
                  checked={formData.requireHostRole}
                  onChange={(e) =>
                    setFormData({ ...formData, requireHostRole: e.target.checked })
                  }
                />
              }
              label="Require host role to create games"
            />
          </Box>

          <Box sx={{ display: 'flex', gap: 2, mt: 4 }}>
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
              onClick={() => navigate(`/guilds/${guildId}`)}
              disabled={saving}
            >
              Cancel
            </Button>
          </Box>
        </CardContent>
      </Card>
    </Container>
  );
};
