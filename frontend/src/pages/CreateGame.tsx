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
import { Container, CircularProgress, Alert } from '@mui/material';
import { useNavigate, useParams } from 'react-router-dom';
import { apiClient } from '../api/client';
import { Channel, DiscordRole } from '../types';
import { GameForm, GameFormData, parseDurationString } from '../components/GameForm';

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
  const [roles, setRoles] = useState<DiscordRole[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<ValidationError[] | null>(null);
  const [validParticipants, setValidParticipants] = useState<string[] | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      if (!guildId) return;

      try {
        setLoading(true);
        const [channelsResponse, rolesResponse] = await Promise.all([
          apiClient.get<Channel[]>(`/api/v1/guilds/${guildId}/channels`),
          apiClient.get<DiscordRole[]>(`/api/v1/guilds/${guildId}/roles`),
        ]);
        setChannels(channelsResponse.data);
        setRoles(rolesResponse.data);
      } catch (err: any) {
        console.error('Failed to fetch data:', err);
        setError('Failed to load server data. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [guildId]);

  const handleSubmit = async (formData: GameFormData) => {
    if (!guildId) {
      throw new Error('Server ID is required');
    }

    const minPlayers = formData.minPlayers ? parseInt(formData.minPlayers) : null;
    const maxPlayers = formData.maxPlayers ? parseInt(formData.maxPlayers) : null;

    try {
      setValidationErrors(null);
      setError(null);

      const payload = {
        title: formData.title,
        description: formData.description,
        signup_instructions: formData.signupInstructions || null,
        scheduled_at: formData.scheduledAt!.toISOString(),
        guild_id: guildId,
        channel_id: formData.channelId,
        min_players: minPlayers,
        max_players: maxPlayers,
        reminder_minutes: formData.reminderMinutes
          ? formData.reminderMinutes.split(',').map((m) => parseInt(m.trim()))
          : null,
        expected_duration_minutes: parseDurationString(formData.expectedDurationMinutes),
        notify_role_ids: formData.notifyRoleIds.length > 0 ? formData.notifyRoleIds : null,
        initial_participants: formData.participants
          .filter((p) => p.mention.trim())
          .map((p) => p.mention.trim()),
      };

      const response = await apiClient.post('/api/v1/games', payload);
      navigate(`/games/${response.data.id}`);
    } catch (err: any) {
      console.error('Failed to create game:', err);

      if (err.response?.status === 422 && err.response.data?.detail?.error === 'invalid_mentions') {
        const errorData = err.response.data.detail as ValidationErrorResponse;
        setValidationErrors(errorData.invalid_mentions);
        setValidParticipants(errorData.valid_participants);
        setError(errorData.message);
        // Don't throw - let form stay open for corrections
        return;
      }
      
      // Handle string detail or extract message from object
      const errorDetail = err.response?.data?.detail;
      const errorMessage = typeof errorDetail === 'string' 
        ? errorDetail 
        : errorDetail?.message || 'Failed to create game. Please try again.';
      setError(errorMessage);
      throw err;
    }
  };

  const handleSuggestionClick = (_originalInput: string, _newUsername: string) => {
    setValidationErrors(null);
    setValidParticipants(null);
    setError(null);
  };

  if (loading) {
    return (
      <Container maxWidth="md" sx={{ mt: 4, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress />
      </Container>
    );
  }

  if (error && !validationErrors) {
    return (
      <Container maxWidth="md" sx={{ mt: 4 }}>
        <Alert severity="error">{error}</Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
      <GameForm
        mode="create"
        guildId={guildId!}
        channels={channels}
        roles={roles}
        onSubmit={handleSubmit}
        onCancel={() => navigate(-1)}
        validationErrors={validationErrors}
        validParticipants={validParticipants}
        onValidationErrorClick={handleSuggestionClick}
      />
    </Container>
  );
};
