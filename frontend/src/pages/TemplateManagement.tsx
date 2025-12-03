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
import { useParams, useNavigate } from 'react-router-dom';
import {
  Container,
  Typography,
  Button,
  Box,
  CircularProgress,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import { TemplateList } from '../components/TemplateList';
import { TemplateForm } from '../components/TemplateForm';
import { apiClient } from '../api/client';
import * as templateApi from '../api/templates';
import {
  GameTemplate,
  Channel,
  DiscordRole,
  TemplateCreateRequest,
  TemplateUpdateRequest,
} from '../types';

export const TemplateManagement: FC = () => {
  const { guildId } = useParams<{ guildId: string }>();
  const navigate = useNavigate();

  const [templates, setTemplates] = useState<GameTemplate[]>([]);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [roles, setRoles] = useState<DiscordRole[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<GameTemplate | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [templateToDelete, setTemplateToDelete] = useState<GameTemplate | null>(null);

  const fetchData = async () => {
    if (!guildId) return;

    try {
      setLoading(true);
      setError(null);

      const [templatesResponse, channelsResponse, rolesResponse] = await Promise.all([
        templateApi.getTemplates(guildId),
        apiClient.get<Channel[]>(`/api/v1/guilds/${guildId}/channels`),
        apiClient.get<DiscordRole[]>(`/api/v1/guilds/${guildId}/roles`),
      ]);

      setTemplates(templatesResponse);
      setChannels(channelsResponse.data);
      setRoles(rolesResponse.data);
    } catch (err: any) {
      console.error('Failed to fetch data:', err);
      setError(err.response?.data?.detail || 'Failed to load template data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    // fetchData is defined within the component and should not be a dependency
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [guildId]);

  const handleCreateTemplate = () => {
    setSelectedTemplate(null);
    setFormOpen(true);
  };

  const handleEditTemplate = (template: GameTemplate) => {
    setSelectedTemplate(template);
    setFormOpen(true);
  };

  const handleFormSubmit = async (data: TemplateCreateRequest | TemplateUpdateRequest) => {
    if (selectedTemplate) {
      await templateApi.updateTemplate(selectedTemplate.id, data as TemplateUpdateRequest);
    } else {
      await templateApi.createTemplate(data as TemplateCreateRequest);
    }
    await fetchData();
    setFormOpen(false);
  };

  const handleDeleteClick = (template: GameTemplate) => {
    if (template.is_default) {
      setError('Cannot delete the default template');
      return;
    }
    setTemplateToDelete(template);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!templateToDelete) return;

    try {
      await templateApi.deleteTemplate(templateToDelete.id);
      await fetchData();
      setDeleteDialogOpen(false);
      setTemplateToDelete(null);
    } catch (err: any) {
      console.error('Failed to delete template:', err);
      setError(err.response?.data?.detail || 'Failed to delete template');
      setDeleteDialogOpen(false);
    }
  };

  const handleSetDefault = async (template: GameTemplate) => {
    if (template.is_default) return;

    try {
      await templateApi.setDefaultTemplate(template.id);
      await fetchData();
    } catch (err: any) {
      console.error('Failed to set default template:', err);
      setError(err.response?.data?.detail || 'Failed to set default template');
    }
  };

  const handleReorder = async (templateIds: string[]) => {
    try {
      await templateApi.reorderTemplates(templateIds);
      await fetchData();
    } catch (err: any) {
      console.error('Failed to reorder templates:', err);
      setError(err.response?.data?.detail || 'Failed to reorder templates');
    }
  };

  if (loading) {
    return (
      <Container sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Container>
    );
  }

  return (
    <Container sx={{ mt: 4, mb: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Button startIcon={<ArrowBackIcon />} onClick={() => navigate(`/guilds/${guildId}`)}>
            Back to Server
          </Button>
          <Typography variant="h4">Game Templates</Typography>
        </Box>
        <Button variant="contained" startIcon={<AddIcon />} onClick={handleCreateTemplate}>
          New Template
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Templates define game types with locked and pre-populated settings. Drag to reorder.
      </Typography>

      <TemplateList
        templates={templates}
        roles={roles}
        onEdit={handleEditTemplate}
        onDelete={handleDeleteClick}
        onSetDefault={handleSetDefault}
        onReorder={handleReorder}
      />

      <TemplateForm
        open={formOpen}
        template={selectedTemplate}
        guildId={guildId!}
        channels={channels}
        roles={roles}
        onClose={() => setFormOpen(false)}
        onSubmit={handleFormSubmit}
      />

      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete the template &ldquo;{templateToDelete?.name}&rdquo;?
            This action cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleDeleteConfirm} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};
