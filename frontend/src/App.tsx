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


import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import { CssBaseline } from '@mui/material';
import { theme } from './theme';
import { Layout } from './components/Layout';
import { HomePage } from './pages/HomePage';
import { LoginPage } from './pages/LoginPage';
import { AuthCallback } from './pages/AuthCallback';
import { GuildListPage } from './pages/GuildListPage';
import { GuildDashboard } from './pages/GuildDashboard';
import { GuildConfig } from './pages/GuildConfig';
import { ChannelConfig } from './pages/ChannelConfig';
import { BrowseGames } from './pages/BrowseGames';
import { GameDetails } from './pages/GameDetails';
import { CreateGame } from './pages/CreateGame';
import { MyGames } from './pages/MyGames';
import { AuthProvider } from './contexts/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/auth/callback" element={<AuthCallback />} />
            
            <Route element={<Layout />}>
              <Route path="/" element={<HomePage />} />
              
              <Route element={<ProtectedRoute />}>
                <Route path="/guilds" element={<GuildListPage />} />
                <Route path="/guilds/:guildId" element={<GuildDashboard />} />
                <Route path="/guilds/:guildId/config" element={<GuildConfig />} />
                <Route path="/channels/:channelId/config" element={<ChannelConfig />} />
                <Route path="/guilds/:guildId/games" element={<BrowseGames />} />
                <Route path="/guilds/:guildId/games/new" element={<CreateGame />} />
                <Route path="/games/:gameId" element={<GameDetails />} />
                <Route path="/my-games" element={<MyGames />} />
              </Route>
            </Route>
            
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;
