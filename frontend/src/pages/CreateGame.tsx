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
  Container,
  CircularProgress,
  Alert,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Box,
  Typography,
} from '@mui/material';
import { useNavigate, useParams } from 'react-router-dom';
import { apiClient } from '../api/client';
import { getTemplates } from '../api/templates';
import { GameTemplate } from '../types';
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
  const [templates, setTemplates] = useState<GameTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<GameTemplate | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<ValidationError[] | null>(null);
  const [validParticipants, setValidParticipants] = useState<string[] | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      if (!guildId) return;

      try {
        setLoading(true);
        const templatesResponse = await getTemplates(guildId);
        setTemplates(templatesResponse);

        // Auto-select default template
        const defaultTemplate = templatesResponse.find((t) => t.is_default);
        if (defaultTemplate) {
          setSelectedTemplate(defaultTemplate);
        } else if (templatesResponse.length > 0) {
          setSelectedTemplate(templatesResponse[0]!);
        }
      } catch (err: unknown) {
        console.error('Failed to fetch data:', err);
        setError('Failed to load server data. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [guildId]);

  const handleSubmit = async (formData: GameFormData) => {
    if (!guildId || !selectedTemplate) {
      throw new Error('Server ID and template are required');
    }

    const maxPlayers = formData.maxPlayers ? parseInt(formData.maxPlayers) : null;

    try {
      setValidationErrors(null);
      setError(null);

      const payload = {
        template_id: selectedTemplate.id,
        title: formData.title,
        description: formData.description,
        signup_instructions: formData.signupInstructions || null,
        scheduled_at: formData.scheduledAt!.toISOString(),
        where: formData.where || null,
        max_players: maxPlayers,
        reminder_minutes: formData.reminderMinutes
          ? formData.reminderMinutes.split(',').map((m) => parseInt(m.trim()))
          : null,
        expected_duration_minutes: parseDurationString(formData.expectedDurationMinutes),
        initial_participants: formData.participants
          .filter((p) => p.mention.trim())
          .map((p) => p.mention.trim()),
      };

      const response = await apiClient.post('/api/v1/games', payload);
      navigate(`/games/${response.data.id}`);
    } catch (err: unknown) {
      console.error('Failed to create game:', err);

      if (
        (err as any).response?.status === 422 &&
        (err as any).response.data?.detail?.error === 'invalid_mentions'
      ) {
        const errorData = (err as any).response.data.detail as ValidationErrorResponse;
        setValidationErrors(errorData.invalid_mentions);
        setValidParticipants(errorData.valid_participants);
        setError(errorData.message);
        // Don't throw - let form stay open for corrections
        return;
      }

      // Handle string detail or extract message from object
      const errorDetail = (err as any).response?.data?.detail;
      const errorMessage =
        typeof errorDetail === 'string'
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
      {templates.length === 0 ? (
        <Alert severity="warning">
          No templates available. Please create a template first in the server settings.
        </Alert>
      ) : (
        <>
          <Box sx={{ mb: 3 }}>
            <FormControl fullWidth>
              <InputLabel>Game Template</InputLabel>
              <Select
                value={selectedTemplate?.id || ''}
                onChange={(e) => {
                  const template = templates.find((t) => t.id === e.target.value);
                  setSelectedTemplate(template || null);
                }}
                label="Game Template"
              >
                {templates.map((template) => (
                  <MenuItem key={template.id} value={template.id}>
                    {template.name}
                    {template.is_default && ' (Default)'}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            {selectedTemplate?.description && (
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                {selectedTemplate.description}
              </Typography>
            )}
          </Box>

          {selectedTemplate && (
            <GameForm
              mode="create"
              guildId={guildId!}
              channels={[
                {
                  id: selectedTemplate.channel_id,
                  guild_id: guildId!,
                  channel_id: selectedTemplate.channel_id,
                  channel_name: selectedTemplate.channel_name,
                  is_active: true,
                  created_at: '',
                  updated_at: '',
                },
              ]}
              initialData={{
                max_players: selectedTemplate.max_players,
                expected_duration_minutes: selectedTemplate.expected_duration_minutes,
                reminder_minutes: selectedTemplate.reminder_minutes,
                where: selectedTemplate.where,
                signup_instructions: selectedTemplate.signup_instructions,
                channel_id: selectedTemplate.channel_id,
              }}
              onSubmit={handleSubmit}
              onCancel={() => navigate(-1)}
              validationErrors={validationErrors}
              validParticipants={validParticipants}
              onValidationErrorClick={handleSuggestionClick}
            />
          )}
        </>
      )}
    </Container>
  );
};
