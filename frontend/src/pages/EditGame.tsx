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
import { Channel, GameSession, Participant } from '../types';
import { GameForm, GameFormData, parseDurationString } from '../components/GameForm';

interface EditGameState {
  game: GameSession | null;
  channels: Channel[];
  initialParticipants: Participant[];
}

export const EditGame: FC = () => {
  const navigate = useNavigate();
  const { gameId } = useParams<{ gameId: string }>();
  const [state, setState] = useState<EditGameState>({
    game: null,
    channels: [],
    initialParticipants: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

        setState({
          game: gameData,
          channels: channelsResponse.data,
          initialParticipants: gameData.participants || [],
        });
      } catch (err: any) {
        console.error('Failed to fetch game:', err);
        setError('Failed to load game. Please try again.');
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

    const minPlayers = formData.minPlayers ? parseInt(formData.minPlayers) : null;
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
      const payload = {
        title: formData.title,
        description: formData.description,
        signup_instructions: formData.signupInstructions || null,
        scheduled_at: formData.scheduledAt!.toISOString(),
        channel_id: formData.channelId,
        min_players: minPlayers,
        max_players: maxPlayers,
        reminder_minutes: formData.reminderMinutes
          ? formData.reminderMinutes.split(',').map((m) => parseInt(m.trim()))
          : null,
        expected_duration_minutes: parseDurationString(formData.expectedDurationMinutes),
        participants: formData.participants
          .filter((p) => p.mention.trim() && p.isExplicitlyPositioned)
          .map((p) => ({
            mention: p.mention.trim(),
            pre_filled_position: p.preFillPosition,
          })),
        removed_participant_ids: removedParticipantIds,
      };

      await apiClient.put(`/api/v1/games/${gameId}`, payload);
      navigate(`/games/${gameId}`);
    } catch (err: any) {
      console.error('Failed to update game:', err);
      throw err;
    }
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

  if (error) {
    return (
      <Container maxWidth="md" sx={{ mt: 4 }}>
        <Alert severity="error">{error}</Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
      <GameForm
        mode="edit"
        initialData={state.game}
        guildId={state.game.guild_id}
        channels={state.channels}
        roles={[]}
        onSubmit={handleSubmit}
        onCancel={() => navigate(`/games/${gameId}`)}
      />
    </Container>
  );
};
