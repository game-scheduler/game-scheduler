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

import { FC, useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router';
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
  Autocomplete,
  Chip,
} from '@mui/material';
import SaveIcon from '@mui/icons-material/Save';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import { apiClient } from '../api/client';
import { GuildConfigData, DiscordRole } from '../types';
import { UI } from '../constants/ui';

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
      });

      setSuccess(true);
      setTimeout(() => {
        navigate(`/guilds/${guildId}`);
      }, UI.ANIMATION_DELAY_SHORT);
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
                          ? `#${option.color.toString(UI.GRID_SPACING_LARGE).padStart(UI.GRID_SPACING_SMALL, '0')}`
                          : undefined,
                        color: option.color ? '#ffffff' : undefined,
                      }}
                    />
                  );
                })
              }
              fullWidth
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
