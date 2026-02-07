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
import { StatusCodes } from 'http-status-codes';
import { Container, CircularProgress, Alert } from '@mui/material';
import { useNavigate, useParams } from 'react-router';
import { apiClient } from '../api/client';
import { Channel, DiscordRole, GameSession, Participant } from '../types';
import { GameForm, GameFormData } from '../components/GameForm';

interface EditGameState {
  game: GameSession | null;
  channels: Channel[];
  roles: DiscordRole[];
  initialParticipants: Participant[];
}

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

export const EditGame: FC = () => {
  const navigate = useNavigate();
  const { gameId } = useParams<{ gameId: string }>();
  const [state, setState] = useState<EditGameState>({
    game: null,
    channels: [],
    roles: [],
    initialParticipants: [],
  });
  const [loading, setLoading] = useState(true);
  const [validationErrors, setValidationErrors] = useState<ValidationError[] | null>(null);
  const [validParticipants, setValidParticipants] = useState<string[] | null>(null);

  useEffect(() => {
    const fetchGameAndChannels = async () => {
      if (!gameId) return;

      try {
        setLoading(true);
        const gameResponse = await apiClient.get<GameSession>(`/api/v1/games/${gameId}`);
        const gameData = gameResponse.data;

        const channelsResponse = await apiClient.get<Channel[]>(
          `/api/v1/guilds/${gameData.guild_id}/channels`
        );

        const rolesResponse = await apiClient.get<DiscordRole[]>(
          `/api/v1/guilds/${gameData.guild_id}/roles`
        );

        setState({
          game: gameData,
          channels: channelsResponse.data,
          roles: rolesResponse.data,
          initialParticipants: gameData.participants || [],
        });
      } catch (err: unknown) {
        console.error('Failed to fetch game:', err);
        // GameForm will display the error
      } finally {
        setLoading(false);
      }
    };

    fetchGameAndChannels();
  }, [gameId]);

  const handleSubmit = async (formData: GameFormData) => {
    if (!gameId) {
      throw new Error('Game ID is required');
    }

    const maxPlayers = formData.maxPlayers ? parseInt(formData.maxPlayers) : null;

    // Detect removed participants by comparing initial vs current
    const currentParticipantIds = new Set(
      formData.participants
        .map((p) => {
          // Extract participant ID if it exists (not a temp ID)
          return p.id.startsWith('temp-') ? null : p.id;
        })
        .filter(Boolean)
    );

    const removedParticipantIds = state.initialParticipants
      .filter((initial) => !currentParticipantIds.has(initial.id))
      .map((p) => p.id);

    try {
      setValidationErrors(null);

      const payload = new FormData();

      // Add all required fields
      payload.append('title', formData.title);
      payload.append('description', formData.description);
      payload.append('scheduled_at', formData.scheduledAt!.toISOString());
      payload.append('channel_id', formData.channelId);

      // Add optional text fields (always include to allow clearing defaults)
      payload.append('signup_instructions', formData.signupInstructions || '');
      payload.append('where', formData.where || '');

      if (maxPlayers !== null) {
        payload.append('max_players', maxPlayers.toString());
      }
      // Don't send field at all if null - keeps existing value

      // Add reminder minutes as JSON array
      // Send empty array when field is cleared to signal deletion
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
      // Don't send field at all if null - keeps existing value

      // Add signup method
      payload.append('signup_method', formData.signupMethod);

      // Add participants as JSON array
      const participantsList = formData.participants
        .filter((p) => p.mention.trim() && p.isExplicitlyPositioned)
        .map((p) => {
          if (!p.id.startsWith('temp-')) {
            return {
              participant_id: p.id,
              position: p.preFillPosition,
            };
          }
          return {
            mention: p.mention.trim(),
            position: p.preFillPosition,
          };
        });
      if (participantsList.length > 0) {
        payload.append('participants', JSON.stringify(participantsList));
      }

      // Add removed participant IDs as JSON array
      if (removedParticipantIds.length > 0) {
        payload.append('removed_participant_ids', JSON.stringify(removedParticipantIds));
      }

      // Add image files
      if (formData.thumbnailFile) {
        payload.append('thumbnail', formData.thumbnailFile);
      }
      if (formData.imageFile) {
        payload.append('image', formData.imageFile);
      }

      // Add removal flags
      if (formData.removeThumbnail) {
        payload.append('remove_thumbnail', 'true');
      }
      if (formData.removeImage) {
        payload.append('remove_image', 'true');
      }

      await apiClient.put(`/api/v1/games/${gameId}`, payload, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      navigate(`/games/${gameId}`);
    } catch (err: unknown) {
      console.error('Failed to update game:', err);

      if (
        (err as any).response?.status === StatusCodes.UNPROCESSABLE_ENTITY &&
        (err as any).response.data?.detail?.error === 'invalid_mentions'
      ) {
        const errorData = (err as any).response.data.detail as ValidationErrorResponse;
        setValidationErrors(errorData.invalid_mentions);
        setValidParticipants(errorData.valid_participants);
        // Don't throw - let form stay open for corrections
        return;
      }

      // For other errors, let GameForm handle display
      throw err;
    }
  };

  const handleSuggestionClick = (_originalInput: string, _newUsername: string) => {
    setValidationErrors(null);
    setValidParticipants(null);
  };

  if (loading) {
    return (
      <Container maxWidth="md" sx={{ mt: 4, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress />
      </Container>
    );
  }

  if (!state.game) {
    return (
      <Container maxWidth="md" sx={{ mt: 4 }}>
        <Alert severity="error">Game not found</Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
      <GameForm
        mode="edit"
        initialData={state.game}
        guildId={state.game.guild_id}
        guildName={state.game.guild_name || undefined}
        channels={state.channels}
        onSubmit={handleSubmit}
        onCancel={() => navigate(`/games/${gameId}`)}
        validationErrors={validationErrors}
        validParticipants={validParticipants}
        onValidationErrorClick={handleSuggestionClick}
      />
    </Container>
  );
};
