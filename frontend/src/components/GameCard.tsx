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


import { FC } from 'react';
import {
  Card,
  CardContent,
  CardActions,
  Typography,
  Button,
  Chip,
  Box,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { GameSession } from '../types';

interface GameCardProps {
  game: GameSession;
  showActions?: boolean;
}

export const GameCard: FC<GameCardProps> = ({ game, showActions = true }) => {
  const navigate = useNavigate();

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'SCHEDULED':
        return 'primary';
      case 'IN_PROGRESS':
        return 'success';
      case 'COMPLETED':
        return 'default';
      case 'CANCELLED':
        return 'error';
      default:
        return 'default';
    }
  };

  const formatDateTime = (isoString: string) => {
    const date = new Date(isoString);
    return date.toLocaleString(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short',
    });
  };

  const participantCount = game.participant_count || 0;
  const minPlayers = game.min_players || 1;
  const maxPlayers = game.max_players || 10;
  const playerDisplay = minPlayers === maxPlayers 
    ? `${participantCount}/${maxPlayers}` 
    : `${participantCount}/${minPlayers}-${maxPlayers}`;

  const truncateDescription = (text: string, maxLength: number = 200): string => {
    if (!text || text.length <= maxLength) {
      return text;
    }
    return text.substring(0, maxLength).trim() + '...';
  };

  return (
    <Card sx={{ mb: 2 }}>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
          <Typography variant="h6" component="div">
            {game.title}
          </Typography>
          <Chip
            label={game.status}
            color={getStatusColor(game.status)}
            size="small"
          />
        </Box>

        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          {truncateDescription(game.description, 200)}
        </Typography>

        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', mb: 1 }}>
          <Typography variant="body2">
            <strong>When:</strong> {formatDateTime(game.scheduled_at)}
          </Typography>
          <Typography variant="body2">
            <strong>Players:</strong> {playerDisplay}
          </Typography>
        </Box>

        {game.host && game.host.display_name && (
          <Box sx={{ mb: 1 }}>
            <Chip
              label={`Host: ${game.host.display_name}`}
              color="secondary"
              size="small"
              variant="outlined"
            />
          </Box>
        )}

        {game.rules && (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            <strong>Rules:</strong> {game.rules}
          </Typography>
        )}
      </CardContent>

      {showActions && (
        <CardActions>
          <Button size="small" onClick={() => navigate(`/games/${game.id}`)}>
            View Details
          </Button>
        </CardActions>
      )}
    </Card>
  );
};
