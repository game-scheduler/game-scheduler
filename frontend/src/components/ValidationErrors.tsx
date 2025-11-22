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
import { Alert, AlertTitle, Box, Typography } from '@mui/material';
import { MentionChip } from './MentionChip';

interface ValidationError {
  input: string;
  reason: string;
  suggestions: Array<{
    discordId: string;
    username: string;
    displayName: string;
  }>;
}

interface ValidationErrorsProps {
  errors: ValidationError[];
  onSuggestionClick: (originalInput: string, newUsername: string) => void;
}

export const ValidationErrors: FC<ValidationErrorsProps> = ({ errors, onSuggestionClick }) => {
  return (
    <Alert severity="error" sx={{ mb: 2 }}>
      <AlertTitle>Could not resolve some @mentions</AlertTitle>
      {errors.map((err, idx) => (
        <Box key={idx} mb={2}>
          <Typography variant="body2">
            <strong>{err.input}</strong>: {err.reason}
          </Typography>
          {err.suggestions.length > 0 && (
            <Box ml={2} mt={1}>
              <Typography variant="caption" display="block" gutterBottom>
                Did you mean:
              </Typography>
              {err.suggestions.map((sugg) => (
                <MentionChip
                  key={sugg.discordId}
                  username={sugg.username}
                  displayName={sugg.displayName}
                  onClick={() => onSuggestionClick(err.input, `@${sugg.username}`)}
                />
              ))}
            </Box>
          )}
        </Box>
      ))}
    </Alert>
  );
};
