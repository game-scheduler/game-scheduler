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

import { FC } from 'react';
import { Alert, AlertTitle, Box, Typography, Chip } from '@mui/material';

interface ChannelSuggestion {
  id: string;
  name: string;
}

interface ChannelValidationError {
  type: string;
  input: string;
  reason: string;
  suggestions: ChannelSuggestion[];
}

interface ChannelValidationErrorsProps {
  errors: ChannelValidationError[];
  onSuggestionClick: (originalInput: string, newChannelName: string) => void;
}

export const ChannelValidationErrors: FC<ChannelValidationErrorsProps> = ({
  errors,
  onSuggestionClick,
}) => {
  return (
    <Alert severity="error" sx={{ mb: 2 }}>
      <AlertTitle>Location contains an invalid channel reference</AlertTitle>
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
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                {err.suggestions.map((sugg) => (
                  <Chip
                    key={sugg.id}
                    label={`#${sugg.name}`}
                    onClick={() => onSuggestionClick(err.input, `#${sugg.name}`)}
                    clickable
                    size="small"
                    color="primary"
                    variant="outlined"
                  />
                ))}
              </Box>
            </Box>
          )}
        </Box>
      ))}
    </Alert>
  );
};
