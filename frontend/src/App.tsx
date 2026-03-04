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

import { BrowserRouter, Routes, Route, Navigate } from 'react-router';
import { ThemeProvider } from '@mui/material/styles';
import { CssBaseline } from '@mui/material';
import { theme } from './theme';
import { Layout } from './components/Layout';
import { LoginPage } from './pages/LoginPage';
import { AuthCallback } from './pages/AuthCallback';
import { MyGames } from './pages/MyGames';
import { GuildListPage } from './pages/GuildListPage';
import { GuildDashboard } from './pages/GuildDashboard';
import { GuildConfig } from './pages/GuildConfig';
import { BrowseGames } from './pages/BrowseGames';
import { GameDetails } from './pages/GameDetails';
import { CreateGame } from './pages/CreateGame';
import { EditGame } from './pages/EditGame';
import { CloneGame } from './pages/CloneGame';
import { TemplateManagement } from './pages/TemplateManagement';
import { DownloadCalendar } from './pages/DownloadCalendar';
import { About } from './pages/About';
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

            <Route element={<ProtectedRoute />}>
              <Route path="/download-calendar/:gameId" element={<DownloadCalendar />} />
            </Route>

            <Route element={<Layout />}>
              <Route element={<ProtectedRoute />}>
                <Route path="/" element={<MyGames />} />
                <Route path="/guilds" element={<GuildListPage />} />
                <Route path="/guilds/:guildId" element={<GuildDashboard />} />
                <Route path="/guilds/:guildId/config" element={<GuildConfig />} />
                <Route path="/guilds/:guildId/templates" element={<TemplateManagement />} />
                <Route path="/guilds/:guildId/games" element={<BrowseGames />} />
                <Route path="/games/new" element={<CreateGame />} />
                <Route path="/games/:gameId" element={<GameDetails />} />
                <Route path="/games/:gameId/edit" element={<EditGame />} />
                <Route path="/games/:gameId/clone" element={<CloneGame />} />
                <Route path="/my-games" element={<MyGames />} />
              </Route>
              <Route path="/about" element={<About />} />
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;
