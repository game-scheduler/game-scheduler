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
import { Box, Typography, Button, Container } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

export const HomePage: FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();

  return (
    <Container maxWidth="md">
      <Box sx={{ textAlign: 'center', py: 8 }}>
        <Typography variant="h2" component="h1" gutterBottom>
          Discord Game Scheduler
        </Typography>
        <Typography variant="h5" color="text.secondary" paragraph>
          Organize and manage game sessions with your Discord community
        </Typography>
        <Box sx={{ mt: 4 }}>
          {user ? (
            <>
              <Button
                variant="contained"
                size="large"
                onClick={() => navigate('/guilds')}
                sx={{ mr: 2 }}
              >
                View My Guilds
              </Button>
              <Button variant="outlined" size="large" onClick={() => navigate('/my-games')}>
                My Games
              </Button>
            </>
          ) : (
            <Button variant="contained" size="large" onClick={() => navigate('/login')}>
              Login with Discord
            </Button>
          )}
        </Box>
      </Box>
    </Container>
  );
};
