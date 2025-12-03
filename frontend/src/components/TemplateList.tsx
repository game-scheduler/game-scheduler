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
import { Box, Typography } from '@mui/material';
import { TemplateCard } from './TemplateCard';
import { GameTemplate, DiscordRole } from '../types';

interface TemplateListProps {
  templates: GameTemplate[];
  roles: DiscordRole[];
  onEdit: (template: GameTemplate) => void;
  onDelete: (template: GameTemplate) => void;
  onSetDefault: (template: GameTemplate) => void;
  onReorder: (templateIds: string[]) => void;
}

export const TemplateList: FC<TemplateListProps> = ({
  templates,
  roles,
  onEdit,
  onDelete,
  onSetDefault,
  onReorder,
}) => {
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);

  const handleDragStart = (index: number) => {
    setDraggedIndex(index);
  };

  const handleDragOver = (index: number, e: React.DragEvent) => {
    e.preventDefault();
    if (draggedIndex === null || draggedIndex === index) return;
    setDragOverIndex(index);
  };

  const handleDragEnd = () => {
    if (draggedIndex === null || dragOverIndex === null || draggedIndex === dragOverIndex) {
      setDraggedIndex(null);
      setDragOverIndex(null);
      return;
    }

    const newTemplates = [...templates];
    const [draggedTemplate] = newTemplates.splice(draggedIndex, 1);
    newTemplates.splice(dragOverIndex, 0, draggedTemplate!);

    const templateIds = newTemplates.map((t) => t.id);
    onReorder(templateIds);

    setDraggedIndex(null);
    setDragOverIndex(null);
  };

  const handleDragLeave = () => {
    setDragOverIndex(null);
  };

  if (templates.length === 0) {
    return (
      <Box sx={{ textAlign: 'center', py: 4 }}>
        <Typography variant="body1" color="text.secondary">
          No templates found. Create your first template to get started.
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      {templates.map((template, index) => (
        <Box
          key={template.id}
          draggable
          onDragStart={() => handleDragStart(index)}
          onDragOver={(e) => handleDragOver(index, e)}
          onDragEnd={handleDragEnd}
          onDragLeave={handleDragLeave}
          sx={{
            opacity: draggedIndex === index ? 0.5 : 1,
            transition: 'opacity 0.2s',
            borderTop: dragOverIndex === index ? '2px solid primary.main' : 'none',
          }}
        >
          <TemplateCard
            template={template}
            roles={roles}
            onEdit={onEdit}
            onDelete={onDelete}
            onSetDefault={onSetDefault}
            dragHandleProps={{
              style: { cursor: 'grab' },
            }}
          />
        </Box>
      ))}
    </Box>
  );
};
