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
  Autocomplete,
  Chip,
} from '@mui/material';
import SaveIcon from '@mui/icons-material/Save';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import { apiClient } from '../api/client';
import { GuildConfigData, DiscordRole } from '../types';

export const GuildConfig: FC = () => {
  const { guildId } = useParams<{ guildId: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [loadingRoles, setLoadingRoles] = useState(false);
  const [roles, setRoles] = useState<DiscordRole[]>([]);

  const [guild, setGuild] = useState<GuildConfigData | null>(null);
  const [formData, setFormData] = useState({
    botManagerRoleIds: [] as string[],
    requireHostRole: false,
  });

  useEffect(() => {
    const fetchGuild = async () => {
      if (!guildId) return;

      try {
        setLoading(true);
        setError(null);

        const response = await apiClient.get<GuildConfigData>(`/api/v1/guilds/${guildId}/config`);
        const guildData = response.data;

        setGuild(guildData);
        setFormData({
          botManagerRoleIds: guildData.bot_manager_role_ids || [],
          requireHostRole: guildData.require_host_role,
        });
      } catch (err: unknown) {
        console.error('Failed to fetch guild:', err);
        setError((err as any).response?.data?.detail || 'Failed to load server configuration.');
      } finally {
        setLoading(false);
      }
    };

    fetchGuild();
  }, [guildId]);

  useEffect(() => {
    const fetchRoles = async () => {
      if (!guildId) return;

      try {
        setLoadingRoles(true);
        const response = await apiClient.get<DiscordRole[]>(`/api/v1/guilds/${guildId}/roles`);
        setRoles(response.data);
      } catch (err: unknown) {
        console.error('Failed to fetch roles:', err);
      } finally {
        setLoadingRoles(false);
      }
    };

    fetchRoles();
  }, [guildId]);

  const handleSave = async () => {
    if (!guildId) return;

    try {
      setSaving(true);
      setError(null);
      setSuccess(false);

      await apiClient.put(`/api/v1/guilds/${guildId}`, {
        bot_manager_role_ids:
          formData.botManagerRoleIds.length > 0 ? formData.botManagerRoleIds : null,
        require_host_role: formData.requireHostRole,
      });

      setSuccess(true);
      setTimeout(() => {
        navigate(`/guilds/${guildId}`);
      }, 1500);
    } catch (err: unknown) {
      console.error('Failed to save guild config:', err);
      setError(
        (err as any).response?.data?.detail || 'Failed to save configuration. Please try again.'
      );
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
          Back to Server
        </Button>
      </Container>
    );
  }

  return (
    <Container sx={{ mt: 4, mb: 4 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3, gap: 2 }}>
        <Button startIcon={<ArrowBackIcon />} onClick={() => navigate(`/guilds/${guildId}`)}>
          Back
        </Button>
        <Typography variant="h4">Server Configuration</Typography>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      {success && (
        <Alert severity="success" sx={{ mb: 2 }}>
          Configuration saved successfully! Redirecting...
        </Alert>
      )}

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Server Settings
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Configure server-wide permissions and roles for game management.
          </Typography>

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            <Autocomplete
              multiple
              options={roles}
              value={roles.filter((role) => formData.botManagerRoleIds.includes(role.id))}
              onChange={(_, newValue) =>
                setFormData({
                  ...formData,
                  botManagerRoleIds: newValue.map((role) => role.id),
                })
              }
              getOptionLabel={(option) => option.name}
              loading={loadingRoles}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Bot Manager Roles"
                  placeholder="Select Bot Manager roles"
                  helperText="Roles for Bot Managers (can edit/delete any game in this server). Leave empty for none."
                />
              )}
              renderTags={(value, getTagProps) =>
                value.map((option, index) => {
                  const { key, ...chipProps } = getTagProps({ index });
                  return (
                    <Chip
                      key={key}
                      label={option.name}
                      {...chipProps}
                      sx={{
                        backgroundColor: option.color
                          ? `#${option.color.toString(16).padStart(6, '0')}`
                          : undefined,
                        color: option.color ? '#ffffff' : undefined,
                      }}
                    />
                  );
                })
              }
              fullWidth
            />

            <FormControlLabel
              control={
                <Checkbox
                  checked={formData.requireHostRole}
                  onChange={(e) => setFormData({ ...formData, requireHostRole: e.target.checked })}
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
