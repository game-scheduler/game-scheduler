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


import { FC, useState } from 'react';
import {
  Box,
  Typography,
  TextField,
  IconButton,
  Button,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward';
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import ErrorIcon from '@mui/icons-material/Error';

export interface ParticipantInput {
  id: string;
  mention: string;
  preFillPosition: number;
  isExplicitlyPositioned?: boolean; // Track if user explicitly moved/added this participant
  isReadOnly?: boolean; // Joined participants can't be edited, only reordered/removed
  validationStatus?: 'valid' | 'unknown' | 'invalid'; // Track validation state
}

interface EditableParticipantListProps {
  participants: ParticipantInput[];
  onChange: (participants: ParticipantInput[]) => void;
}

export const EditableParticipantList: FC<EditableParticipantListProps> = ({
  participants,
  onChange,
}) => {
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);

  const handleMentionChange = (id: string, newMention: string) => {
    onChange(
      participants.map((p) =>
        p.id === id ? { ...p, mention: newMention, validationStatus: 'unknown' as const } : p
      )
    );
  };

  const addParticipant = () => {
    const newParticipant: ParticipantInput = {
      id: `temp-${Date.now()}-${Math.random()}`,
      mention: '',
      preFillPosition: participants.length + 1,
      isExplicitlyPositioned: true, // New participants are explicitly positioned
      validationStatus: 'unknown',
    };
    onChange([...participants, newParticipant]);
  };

  const removeParticipant = (id: string) => {
    const filtered = participants.filter((p) => p.id !== id);
    const reindexed = filtered.map((p, idx) => ({ ...p, preFillPosition: idx + 1 }));
    onChange(reindexed);
  };

  const moveUp = (index: number) => {
    if (index === 0) return;
    const newParticipants = [...participants];
    [newParticipants[index - 1], newParticipants[index]] = [
      { ...newParticipants[index]!, isExplicitlyPositioned: true }, // Mark moved participant
      newParticipants[index - 1]!, // Other participant keeps its state
    ];
    const reindexed = newParticipants.map((p, idx) => ({
      ...p,
      preFillPosition: idx + 1,
    }));
    onChange(reindexed);
  };

  const moveDown = (index: number) => {
    if (index === participants.length - 1) return;
    const newParticipants = [...participants];
    [newParticipants[index], newParticipants[index + 1]] = [
      newParticipants[index + 1]!, // Other participant keeps its state
      { ...newParticipants[index]!, isExplicitlyPositioned: true }, // Mark moved participant
    ];
    const reindexed = newParticipants.map((p, idx) => ({
      ...p,
      preFillPosition: idx + 1,
    }));
    onChange(reindexed);
  };

  const handleDragStart = (index: number) => {
    setDraggedIndex(index);
  };

  const handleDragOver = (e: React.DragEvent, _index: number) => {
    e.preventDefault(); // Allow drop
  };

  const handleDrop = (e: React.DragEvent, dropIndex: number) => {
    e.preventDefault();

    if (draggedIndex === null || draggedIndex === dropIndex) {
      setDraggedIndex(null);
      return;
    }

    const newParticipants = [...participants];
    const draggedItem = { ...newParticipants[draggedIndex]!, isExplicitlyPositioned: true };

    // Remove dragged item
    newParticipants.splice(draggedIndex, 1);
    // Insert at new position
    newParticipants.splice(dropIndex, 0, draggedItem);

    // Reindex positions
    const reindexed = newParticipants.map((p, idx) => ({
      ...p,
      preFillPosition: idx + 1,
    }));

    onChange(reindexed);
    setDraggedIndex(null);
  };

  const handleDragEnd = () => {
    setDraggedIndex(null);
  };

  return (
    <Box sx={{ mb: 3 }}>
      <Typography variant="h6" gutterBottom>
        Pre-populate Participants (Optional)
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Add Discord users who should be included automatically. Use @mentions or user names. Others
        can join via Discord button.
      </Typography>

      {participants.length === 0 ? (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2, fontStyle: 'italic' }}>
          No participants added by host (users can join via Discord button)
        </Typography>
      ) : (
        participants.map((p, index) => (
          <Box
            key={p.id}
            draggable
            onDragStart={() => handleDragStart(index)}
            onDragOver={(e) => handleDragOver(e, index)}
            onDrop={(e) => handleDrop(e, index)}
            onDragEnd={handleDragEnd}
            sx={{
              display: 'flex',
              gap: 1,
              mb: 1,
              alignItems: 'flex-start',
              cursor: 'move',
              opacity: draggedIndex === index ? 0.5 : 1,
              transition: 'opacity 0.2s',
              '&:hover': {
                backgroundColor: 'action.hover',
              },
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexGrow: 1 }}>
              {p.validationStatus === 'valid' && (
                <CheckCircleIcon color="success" fontSize="small" titleAccess="Validated" />
              )}
              {p.validationStatus === 'invalid' && (
                <ErrorIcon color="error" fontSize="small" titleAccess="Validation failed" />
              )}
              {(!p.validationStatus || p.validationStatus === 'unknown') && (
                <HelpOutlineIcon color="action" fontSize="small" titleAccess="Not validated" />
              )}
              <TextField
                value={p.mention}
                onChange={(e) => handleMentionChange(p.id, e.target.value)}
                placeholder="@username or Discord user"
                helperText={p.isReadOnly ? 'Joined player (can reorder or remove)' : undefined}
                fullWidth
                size="small"
                disabled={p.isReadOnly}
              />
            </Box>
            <IconButton onClick={() => moveUp(index)} disabled={index === 0} size="small">
              <ArrowUpwardIcon />
            </IconButton>
            <IconButton
              onClick={() => moveDown(index)}
              disabled={index === participants.length - 1}
              size="small"
            >
              <ArrowDownwardIcon />
            </IconButton>
            <IconButton onClick={() => removeParticipant(p.id)} size="small" color="error">
              <DeleteIcon />
            </IconButton>
          </Box>
        ))
      )}

      <Button onClick={addParticipant} startIcon={<AddIcon />} variant="outlined" sx={{ mt: 1 }}>
        Add Participant
      </Button>
    </Box>
  );
};
