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
import { Channel } from '../types';

export const ChannelConfig: FC = () => {
  const { channelUuid } = useParams<{ channelUuid: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const [channel, setChannel] = useState<Channel | null>(null);
  const [formData, setFormData] = useState({
    isActive: true,
  });

  useEffect(() => {
    const fetchData = async () => {
      if (!channelUuid) return;

      try {
        setLoading(true);
        setError(null);

        const channelResponse = await apiClient.get<Channel>(`/api/v1/channels/${channelUuid}`);
        const channelData = channelResponse.data;

        setChannel(channelData);

        setFormData({
          isActive: channelData.is_active,
        });
      } catch (err: unknown) {
        console.error('Failed to fetch channel:', err);
        setError((err as any).response?.data?.detail || 'Failed to load channel configuration.');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [channelUuid]);

  const handleSave = async () => {
    if (!channelUuid) return;

    try {
      setSaving(true);
      setError(null);
      setSuccess(false);

      await apiClient.put(`/api/v1/channels/${channelUuid}`, {
        is_active: formData.isActive,
      });

      setSuccess(true);
      setTimeout(() => {
        navigate(`/guilds/${channel?.guild_id}`);
      }, 1500);
    } catch (err: unknown) {
      console.error('Failed to save channel config:', err);
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

  return (
    <Container sx={{ mt: 4, mb: 4 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3, gap: 2 }}>
        <Button
          startIcon={<ArrowBackIcon />}
          onClick={() => navigate(`/guilds/${channel?.guild_id}`)}
        >
          Back
        </Button>
        <Typography variant="h4">Channel Configuration</Typography>
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

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Channel: {channel?.channel_name}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Enable or disable game posting in this channel.
          </Typography>
          <FormControlLabel
            control={
              <Checkbox
                checked={formData.isActive}
                onChange={(e) => setFormData({ ...formData, isActive: e.target.checked })}
              />
            }
            label="Active (enable game posting in this channel)"
          />
        </CardContent>
      </Card>

      <Box sx={{ display: 'flex', gap: 2, mt: 3 }}>
        <Button variant="contained" startIcon={<SaveIcon />} onClick={handleSave} disabled={saving}>
          {saving ? 'Saving...' : 'Save Configuration'}
        </Button>
        <Button
          variant="outlined"
          onClick={() => navigate(`/guilds/${channel?.guild_id}`)}
          disabled={saving}
        >
          Cancel
        </Button>
      </Box>
    </Container>
  );
};
