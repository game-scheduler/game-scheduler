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
import { Box, Typography, Chip } from '@mui/material';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';

interface InheritancePreviewProps {
  label: string;
  value: string | number | number[] | null;
  inherited: boolean;
  inheritedFrom?: string;
}

export const InheritancePreview: FC<InheritancePreviewProps> = ({
  label,
  value,
  inherited,
  inheritedFrom = 'guild',
}) => {
  const displayValue = Array.isArray(value)
    ? value.join(', ')
    : value ?? 'Not set';

  return (
    <Box sx={{ mb: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
      <Typography variant="body2" color="text.secondary">
        {label}:
      </Typography>
      <Typography variant="body2" fontWeight={inherited ? 'normal' : 'bold'}>
        {displayValue}
      </Typography>
      {inherited && (
        <Chip
          icon={<InfoOutlinedIcon />}
          label={`Inherited from ${inheritedFrom}`}
          size="small"
          variant="outlined"
          sx={{ fontSize: '0.7rem', height: '20px' }}
        />
      )}
    </Box>
  );
};
