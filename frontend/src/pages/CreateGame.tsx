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

import { FC, useState, useEffect, useMemo } from 'react';
import { StatusCodes } from 'http-status-codes';
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
import { useNavigate } from 'react-router';
import { apiClient } from '../api/client';
import { getTemplates } from '../api/templates';
import { GameTemplate, Guild } from '../types';
import { GameForm, GameFormData } from '../components/GameForm';
import { canUserCreateGames, canUserManageBotSettings } from '../utils/permissions';

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
  const [guilds, setGuilds] = useState<Guild[]>([]);
  const [selectedGuild, setSelectedGuild] = useState<Guild | null>(null);
  const [guildsWithTemplates, setGuildsWithTemplates] = useState<Set<string>>(new Set());
  const [templates, setTemplates] = useState<GameTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<GameTemplate | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<ValidationError[] | null>(null);
  const [validParticipants, setValidParticipants] = useState<string[] | null>(null);
  const [isBotManager, setIsBotManager] = useState<boolean>(false);

  // Load guilds on mount
  useEffect(() => {
    const fetchGuilds = async () => {
      try {
        setLoading(true);
        const guildsResponse = await apiClient.get<{ guilds: Guild[] }>('/api/v1/guilds');
        const allGuilds = guildsResponse.data.guilds;
        setGuilds(allGuilds);

        // Check which guilds have accessible templates
        const guildsWithAccess = new Set<string>();
        await Promise.all(
          allGuilds.map(async (guild) => {
            if (await canUserCreateGames(guild.id)) {
              guildsWithAccess.add(guild.id);
            }
          })
        );
        setGuildsWithTemplates(guildsWithAccess);

        // Auto-select if only one guild with templates
        const availableGuilds = allGuilds.filter((guild) => guildsWithAccess.has(guild.id));
        if (availableGuilds.length === 1 && availableGuilds[0]) {
          setSelectedGuild(availableGuilds[0]);
        }
      } catch (err: unknown) {
        console.error('Failed to fetch guilds:', err);
        setError(
          (err as any).response?.data?.detail || 'Failed to load servers. Please try again.'
        );
      } finally {
        setLoading(false);
      }
    };

    fetchGuilds();
  }, []);

  // Load templates when guild is selected
  useEffect(() => {
    const fetchData = async () => {
      if (!selectedGuild) return;

      try {
        setLoading(true);
        const templatesResponse = await getTemplates(selectedGuild.id);
        setTemplates(templatesResponse);

        // Check bot manager permissions
        const hasBotManagerPerms = await canUserManageBotSettings(selectedGuild.id);
        setIsBotManager(hasBotManagerPerms);

        // Auto-select default template
        const defaultTemplate = templatesResponse.find((t) => t.is_default);
        if (defaultTemplate) {
          setSelectedTemplate(defaultTemplate);
        } else if (templatesResponse.length > 0) {
          setSelectedTemplate(templatesResponse[0]!);
        }
      } catch (err: unknown) {
        console.error('Failed to fetch data:', err);
        setError(
          (err as any).response?.data?.detail || 'Failed to load server data. Please try again.'
        );
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [selectedGuild]);

  const handleSubmit = async (formData: GameFormData) => {
    if (!selectedGuild || !selectedTemplate) {
      throw new Error('Server ID and template are required');
    }

    const maxPlayers = formData.maxPlayers ? parseInt(formData.maxPlayers) : null;

    try {
      setValidationErrors(null);
      setError(null);

      const payload = new FormData();

      // Add required fields
      payload.append('template_id', selectedTemplate.id);
      payload.append('title', formData.title);
      payload.append('description', formData.description);
      payload.append('scheduled_at', formData.scheduledAt!.toISOString());

      // Add optional text fields (always include to allow clearing template defaults)
      payload.append('signup_instructions', formData.signupInstructions || '');
      payload.append('where', formData.where || '');

      if (maxPlayers !== null) {
        payload.append('max_players', maxPlayers.toString());
      }
      // Don't send field at all if null - backend will use template default

      // Add host field only if bot manager and field has value
      if (isBotManager && formData.host && formData.host.trim()) {
        payload.append('host', formData.host.trim());
      }

      // Add reminder minutes as JSON array
      // Send empty array when field is empty (no reminders)
      const reminderMinutesArray = formData.reminderMinutes
        ? formData.reminderMinutes
            .split(',')
            .map((m) => parseInt(m.trim()))
            .filter((m) => !isNaN(m))
        : [];
      payload.append('reminder_minutes', JSON.stringify(reminderMinutesArray));

      // Add expected duration only if provided
      if (formData.expectedDurationMinutes !== null) {
        payload.append('expected_duration_minutes', formData.expectedDurationMinutes.toString());
      }
      // Don't send field at all if null - backend will use template default

      // Add signup method
      if (formData.signupMethod) {
        payload.append('signup_method', formData.signupMethod);
      }

      // Add initial participants as JSON array
      const participantsList = formData.participants
        .filter((p) => p.mention.trim())
        .map((p) => p.mention.trim());
      if (participantsList.length > 0) {
        payload.append('initial_participants', JSON.stringify(participantsList));
      }

      // Add image files
      if (formData.thumbnailFile) {
        payload.append('thumbnail', formData.thumbnailFile);
      }
      if (formData.imageFile) {
        payload.append('image', formData.imageFile);
      }

      const response = await apiClient.post('/api/v1/games', payload, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      navigate(`/games/${response.data.id}`);
    } catch (err: unknown) {
      console.error('Failed to create game:', err);

      if (
        (err as any).response?.status === StatusCodes.UNPROCESSABLE_ENTITY &&
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

  // Memoize initialData to prevent form reset on re-renders
  const initialData = useMemo(
    () =>
      selectedTemplate
        ? {
            max_players: selectedTemplate.max_players,
            expected_duration_minutes: selectedTemplate.expected_duration_minutes,
            reminder_minutes: selectedTemplate.reminder_minutes,
            where: selectedTemplate.where,
            signup_instructions: selectedTemplate.signup_instructions,
            channel_id: selectedTemplate.channel_id,
          }
        : undefined,
    [selectedTemplate]
  );

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

  const availableGuilds = guilds.filter((guild) => guildsWithTemplates.has(guild.id));

  return (
    <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Create New Game
      </Typography>

      {availableGuilds.length === 0 ? (
        <Alert severity="warning">
          No servers available with game templates. Please create a template first in the server
          settings.
        </Alert>
      ) : (
        <>
          {/* Server Selection */}
          {availableGuilds.length > 1 && (
            <Box sx={{ mb: 3 }}>
              <FormControl fullWidth>
                <InputLabel>Server</InputLabel>
                <Select
                  value={selectedGuild?.id || ''}
                  onChange={(e) => {
                    const guild = guilds.find((g) => g.id === e.target.value);
                    setSelectedGuild(guild || null);
                    setTemplates([]);
                    setSelectedTemplate(null);
                  }}
                  label="Server"
                >
                  {availableGuilds.map((guild) => (
                    <MenuItem key={guild.id} value={guild.id}>
                      {guild.guild_name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Box>
          )}

          {selectedGuild && templates.length === 0 && (
            <Alert severity="info" sx={{ mb: 3 }}>
              Loading templates...
            </Alert>
          )}

          {selectedGuild && templates.length > 0 && (
            <>
              <Typography variant="h6" gutterBottom sx={{ mb: 2 }}>
                Game Details
              </Typography>

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
                  guildId={selectedGuild.id}
                  guildName={selectedGuild.guild_name}
                  canChangeChannel={isBotManager}
                  isBotManager={isBotManager}
                  channels={[
                    {
                      id: selectedTemplate.channel_id,
                      guild_id: selectedGuild.id,
                      channel_id: selectedTemplate.channel_id,
                      channel_name: selectedTemplate.channel_name,
                      is_active: true,
                      created_at: '',
                      updated_at: '',
                    },
                  ]}
                  allowedSignupMethods={selectedTemplate.allowed_signup_methods}
                  defaultSignupMethod={selectedTemplate.default_signup_method}
                  initialData={initialData}
                  onSubmit={handleSubmit}
                  onCancel={() => navigate(-1)}
                  validationErrors={validationErrors}
                  validParticipants={validParticipants}
                  onValidationErrorClick={handleSuggestionClick}
                />
              )}
            </>
          )}
        </>
      )}
    </Container>
  );
};
