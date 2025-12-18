<!-- markdownlint-disable-file -->
# Task Research Notes: Discord Calendar Download Feature

## Research Executed

### File Analysis
- `frontend/src/components/ExportButton.tsx`
  - React component that downloads .ics file from API endpoint `/api/v1/export/game/{gameId}`
  - Creates blob download with filename `game-{gameId}.ics`
  - Handles permissions (403 error if not host/participant)
- `services/api/services/calendar_export.py`
  - CalendarExportService.export_game() generates iCal format calendar data
  - Uses python's icalendar library to create VCALENDAR with VEVENT
  - Returns bytes that represent complete .ics file
  - Includes game details, time, location, participants, reminders
- `services/bot/formatters/game_message.py`
  - format_game_announcement() creates Discord embed + GameView buttons
  - GameView currently has 2 buttons: "Join Game" and "Leave Game"
  - Buttons use custom_id pattern: `{action}_game_{game_id}`
- `services/bot/views/game_view.py`
  - GameView class with persistent buttons (timeout=None)
  - Buttons have callbacks that get registered with bot interaction handlers
  - Current implementation: join_button and leave_button

### Code Search Results
- **Discord.py File Attachment Capabilities**
  - `discord.File` class supports sending file attachments
  - Channel.send() accepts `file` or `files` parameters
  - Message.edit() accepts `attachments` parameter (list of Attachment or File objects)
  - Files can be created from BytesIO: `discord.File(io.BytesIO(data), filename="file.ics")`
  - Button interactions can send followup messages with files

### External Research
- #githubRepo:"Rapptz/discord.py send file attachment message discord.File buttons view"
  - Discord button interactions support sending files in followup responses
  - Pattern: `await interaction.followup.send(file=discord.File(...))`
  - Can send files alongside embeds and views
  - File objects accept BytesIO for in-memory file data
  - Multiple files can be sent: `files=[discord.File(...), discord.File(...)]`
- #fetch:"https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Disposition"
  - HTTP header for file downloads: `Content-Disposition: attachment; filename="file.ics"`
  - Triggers browser "Save As" dialog with specified filename
  - Filename parameter should use quoted strings for special characters

### Authentication Research
- Current OAuth2 system uses HTTPOnly cookies with session tokens
- `Depends(auth_deps.get_current_user)` validates session from cookie
- Frontend `ProtectedRoute` redirects to `/login` if not authenticated
- Current export endpoint requires authentication and checks permissions
- OAuth flow supports redirect_uri for post-login redirects

### Project Conventions
- Standards referenced: Python best practices, discord.py patterns
- Instructions followed: Minimize changes, surgical modifications

## Key Discoveries

### Authentication Analysis for Calendar Download

**User Question:** How much effort would it take to require web login for calendar downloads? Can we redirect to login and back to the endpoint?

**Context:** The selected approach embeds a URL in the Discord game card title. When users click the title, it opens their browser and directly downloads the calendar file from the API endpoint.

#### Current Authentication System
The project has complete Discord OAuth2 authentication:
- **Login endpoint**: `GET /api/v1/auth/login?redirect_uri=...` generates OAuth2 URL
- **OAuth callback**: `GET /api/v1/auth/callback?code=...&state=...` exchanges code for tokens
- **Session management**: HTTPOnly cookies store session tokens (validated via Redis)
- **Dependency injection**: `Depends(auth_deps.get_current_user)` extracts authenticated user from cookies
- **Frontend protection**: `ProtectedRoute` component redirects to `/login` if not authenticated

#### Current Export Endpoint
[services/api/routes/export.py](services/api/routes/export.py#L48-L105) **requires authentication**:
```python
async def export_game(
    user: auth_schemas.CurrentUser = Depends(auth_deps.get_current_user),
    # Checks: host, participant, admin, or bot manager only
)
```

#### Can We Redirect to Login and Back?

**Yes! Three approaches, from simplest to most complex:**

##### Approach 1: Frontend Download Page (SIMPLEST - 1 hour)

**Create a new frontend route that handles the download:**
```tsx
// frontend/src/pages/DownloadCalendar.tsx
export const DownloadCalendar: FC = () => {
  const { gameId } = useParams<{ gameId: string }>();
  const { user, loading } = useAuth();

  useEffect(() => {
    if (!loading && user) {
      // User is authenticated - download the calendar
      downloadCalendar(gameId);
    }
  }, [user, loading, gameId]);

  if (loading) {
    return <CircularProgress />;
  }

  // Not authenticated - ProtectedRoute will redirect to /login
  return null;
};

async function downloadCalendar(gameId: string) {
  const response = await fetch(`/api/v1/export/game/${gameId}`, {
    credentials: 'include', // Send session cookie
  });

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `game-${gameId}.ics`;
  a.click();
}
```

**Add route to App.tsx:**
```tsx
<Route path="/download-calendar/:gameId" element={
  <ProtectedRoute>
    <DownloadCalendar />
  </ProtectedRoute>
} />
```

**Discord embed links to:**
```python
url = f"{settings.FRONTEND_URL}/download-calendar/{game_id}"
```

**The flow:**
1. User clicks Discord title link → Opens browser
2. Frontend checks authentication (useAuth hook)
3. If authenticated: Downloads calendar immediately
4. If not: ProtectedRoute redirects to `/login`
5. After login: Redirects back to `/download-calendar/{game_id}`
6. Downloads calendar automatically

**Why this is best:**
- ✅ Leverages existing `ProtectedRoute` redirect logic
- ✅ Uses existing `useAuth` hook - no new auth code
- ✅ Frontend already handles OAuth callback redirects
- ✅ Clean separation: frontend handles auth, backend serves file
- ✅ Can show nice loading UI or error messages
- ✅ Session cookie automatically included in fetch

**Implementation time: ~1 hour**
- Create new page component (20 min)
- Add route to App.tsx (5 min)
- Update Discord bot to use frontend URL (10 min)
- Keep existing API endpoint with auth (already done)
- Testing (25 min)

##### Approach 2: Backend HTTP 302 Redirect (2-3 hours)

When unauthenticated user clicks Discord link:
```python
@router.get("/game/{game_id}")
async def export_game(game_id: str, request: Request, db: AsyncSession):
    # Try to get current user from cookie
    try:
        user = await get_current_user_optional(request.cookies.get("session_token"))
    except:
        user = None

    if not user:
        # Redirect to login with return URL
        return_url = str(request.url)
        login_url = f"/login?return_to={quote(return_url)}"
        return RedirectResponse(login_url, status_code=302)

    # Authenticated - serve the file
    # ...
```

**The login flow would be:**
1. Click Discord link → Browser opens `/api/v1/export/game/123`
2. No session cookie → Redirect to `/login?return_to=/api/v1/export/game/123`
3. Frontend `/login` page → OAuth flow → Discord authorization
4. Discord redirects back → `/api/v1/auth/callback`
5. Callback sets session cookie → Redirects to `return_to` URL
6. Browser requests `/api/v1/export/game/123` again with session cookie
7. File downloads

**Implementation requirements:**
- Modify export endpoint to check auth and redirect (30 min)
- Update OAuth callback to handle `return_to` parameter (30 min)
- Store `return_to` URL in OAuth state for security (30 min)
- Frontend login page must extract and use `return_to` param (30 min)
- Testing full flow (1 hour)
- **Total: 2.5-3 hours**

##### Approach 2: Signed Token URLs (2-3 hours)

Generate time-limited signed URLs in Discord bot:
```python
# When creating Discord embed
import jwt
from datetime import datetime, timedelta

token = jwt.encode(
    {
        "game_id": game_id,
        "exp": datetime.utcnow() + timedelta(hours=24),
        "iat": datetime.utcnow(),
    },
    settings.SECRET_KEY,
    algorithm="HS256",
)

url = f"{settings.BASE_URL}/api/v1/export/game/{game_id}?token={token}"
```

```python
# Export endpoint validates token
@router.get("/game/{game_id}")
async def export_game(game_id: str, token: str = Query(...), db: AsyncSession):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        if payload["game_id"] != game_id:
            raise HTTPException(403, "Invalid token for this game")
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Download link expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")

    # Token valid - serve the file
    # ...
```

**Implementation requirements:**
- Add JWT library dependency (5 min)
- Generate signed tokens in bot when creating embeds (30 min)
- Validate tokens in export endpoint (30 min)
- Handle expired token errors gracefully (30 min)
- Testing and security review (1 hour)
- **Total: 2.5-3 hours**

**Trade-offs:**
- ✅ No login required - just need valid token
- ✅ Time-limited access (can expire after 24 hours)
- ❌ Anyone with the link can download (tokens are in Discord message)
- ❌ Cannot revoke access once posted

#### Why Authentication May Be Unnecessary

**The calendar download link is embedded in a Discord message that:**
1. Is already posted publicly in the Discord channel
2. Contains all the game information (title, time, description, participants)
3. Is visible to all channel members

**Security question:** What additional protection does authentication provide?
- Game details are already public in the Discord message
- Calendar file contains the same information visible in Discord
- Anyone in the channel can already see everything

**When authentication makes sense:**
- Private DMs (messages not posted to public channels)
- Sensitive information not shown in Discord message
- Audit trail requirements for who downloaded what
- Compliance requirements

#### Recommendation: Keep Calendar Public (Selected Approach)

**Rationale:**
1. ✅ **Game info is already public** - Posted in Discord channel visible to all members
2. ✅ **No additional security risk** - Calendar contains same info as Discord message
3. ✅ **Superior user experience** - One click → immediate download
4. ✅ **Dramatically simpler** - No auth code, no error handling
5. ✅ **Matches user expectations** - Public post = public data

**Effort comparison:**
- **Public URL (current selected approach)**: 5-10 minutes implementation
- **Frontend download page with auth**: 1 hour implementation + clean UX
- **Backend redirect approach**: 2.5-3 hours implementation + complex UX
- **Signed token approach**: 2.5-3 hours implementation + tokens in public messages

#### Updated Recommendation

**If you want authentication, use the frontend download page approach:**
- Only 1 hour implementation
- Leverages all existing infrastructure
- Clean user experience with loading states
- Natural redirect flow users already understand
- Easy to add error handling and user feedback

**If authentication isn't needed (game info is public), keep the simple public URL:**
- 5-10 minutes implementation
- One-click download
- No login friction

### Existing Calendar Export Implementation
The web frontend already has complete calendar export functionality:
- API endpoint: `GET /api/v1/export/game/{game_id}` (services/api/routes/export.py)
- Service: `CalendarExportService.export_game()` generates iCal bytes
- Permissions: User must be host, participant, or have admin/bot manager permissions
- Output: RFC 5545 compliant iCal file with:
  - Event details (title, description, time, duration, location)
  - Participant information
  - Reminders/alarms
  - Status tracking
  - Timezone handling (UTC)

### Discord Button Architecture
Current game cards have two buttons:
```python
# services/bot/views/game_view.py
class GameView(View):
    def __init__(self, game_id: str, ...):
        super().__init__(timeout=None)  # Persistent

        self.join_button = Button(
            style=discord.ButtonStyle.success,
            label="Join Game",
            custom_id=f"join_game_{game_id}",
        )

        self.leave_button = Button(
            style=discord.ButtonStyle.danger,
            label="Leave Game",
            custom_id=f"leave_game_{game_id}",
        )
```

Interaction handler pattern:
```python
# services/bot/handlers/button_handler.py
async def handle_interaction(interaction: discord.Interaction):
    custom_id = interaction.data.get("custom_id")
    if custom_id.startswith("download_calendar_"):
        game_id = custom_id.replace("download_calendar_", "")
        await handle_download_calendar(interaction, game_id)
```

### Discord.py File Sending Capabilities

**From Button Interactions**
```python
# Example from discord.py documentation
async def button_callback(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    # Generate file data
    file_data = generate_calendar_data(game_id)

    # Send as followup with file
    await interaction.followup.send(
        content="Here's your calendar file!",
        file=discord.File(
            io.BytesIO(file_data),
            filename="game.ics"
        ),
        ephemeral=True
    )
```

**Key Discord.py Patterns**
- `discord.File(fp, filename)` where fp can be:
  - File path string
  - File-like object (io.BytesIO)
  - Open file handle
- Button interactions must respond within 3 seconds:
  - Use `await interaction.response.defer()` for long operations
  - Then use `await interaction.followup.send()` to send actual response
- `ephemeral=True` makes message visible only to clicking user
- Files work with embeds, content, and views in same message

### Permission Checking Requirements
From existing code (services/api/routes/export.py):
```python
can_export = await permissions_deps.check_can_export_game(
    game_participants=game.participants,
    guild_id=game.guild.guild_id,
    user_id=user.user.id,
    discord_id=user.user.discord_id,
    role_service=role_service,
    db=db,
    access_token=user.access_token,
    current_user=user,
)
```

Permission logic checks:
1. Is user the game host?
2. Is user a participant?
3. Does user have admin/bot manager role?

## Recommended Approach

**Frontend download page with authentication via protected route**

### Implementation Strategy

Create a new frontend page at `/download-calendar/:gameId` that handles authentication and triggers the calendar download.

### Why This Approach

**User Decision:** Authentication is required to ensure only authorized users can download calendars.

**Benefits:**
- ✅ Leverages existing authentication infrastructure (`useAuth`, `ProtectedRoute`)
- ✅ Reuses existing OAuth redirect flow
- ✅ Clean user experience with loading states
- ✅ Session cookie automatically included in API requests
- ✅ Can show error messages and user feedback
- ✅ Maintains permission checking (host, participant, admin, or bot manager)
- ✅ Only 1 hour implementation time

### Discord Embed URL Capabilities
Discord.py supports adding URLs to embeds:
- **Embed title as link**: `discord.Embed(title="Game Title", url="https://...")`
- Makes the entire title clickable
- Opens link in user's browser (frontend download page)

### Complete Implementation

#### Step 1: Create Frontend Download Page (~20 minutes)

```tsx
// frontend/src/pages/DownloadCalendar.tsx
import { FC, useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router';
import { Box, CircularProgress, Typography, Alert } from '@mui/material';
import { useAuth } from '../hooks/useAuth';
import { api } from '../api/client';

export const DownloadCalendar: FC = () => {
  const { gameId } = useParams<{ gameId: string }>();
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    if (!authLoading && user && gameId && !downloading) {
      downloadCalendar();
    }
  }, [user, authLoading, gameId]);

  const downloadCalendar = async () => {
    setDownloading(true);
    try {
      const response = await fetch(`/api/v1/export/game/${gameId}`, {
        credentials: 'include', // Include session cookie
      });

      if (!response.ok) {
        if (response.status === 403) {
          setError('You do not have permission to download this calendar.');
        } else if (response.status === 404) {
          setError('Game not found.');
        } else {
          setError('Failed to download calendar.');
        }
        return;
      }

      // Get filename from Content-Disposition header or use default
      const contentDisposition = response.headers.get('Content-Disposition');
      const filenameMatch = contentDisposition?.match(/filename="?(.+)"?/i);
      const filename = filenameMatch?.[1] || `game-${gameId}.ics`;

      // Create blob and trigger download
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);

      // Optionally redirect after download
      setTimeout(() => navigate('/my-games'), 1000);
    } catch (err) {
      setError('An error occurred while downloading the calendar.');
      console.error('Calendar download error:', err);
    } finally {
      setDownloading(false);
    }
  };

  if (authLoading || downloading) {
    return (
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100vh',
          gap: 2,
        }}
      >
        <CircularProgress />
        <Typography variant="body1">
          {authLoading ? 'Authenticating...' : 'Downloading calendar...'}
        </Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100vh',
          p: 3,
        }}
      >
        <Alert severity="error" onClose={() => navigate('/my-games')}>
          {error}
        </Alert>
      </Box>
    );
  }

  return null;
};
```

#### Step 2: Add Route to App (~5 minutes)

```tsx
// frontend/src/App.tsx
import { DownloadCalendar } from './pages/DownloadCalendar';

// Inside <Routes>
<Route
  path="/download-calendar/:gameId"
  element={
    <ProtectedRoute>
      <DownloadCalendar />
    </ProtectedRoute>
  }
/>
```

#### Step 3: Update Discord Bot Embed (~10 minutes)

```python
# services/bot/formatters/game_message.py
from services.bot.config import get_bot_config

def create_game_embed(...) -> discord.Embed:
    config = get_bot_config()
    calendar_url = f"{config.frontend_url}/download-calendar/{game_id}"

    embed = discord.Embed(
        title=game_title,
        url=calendar_url,  # Makes title clickable - links to frontend
        description=truncated_description,
        color=GameMessageFormatter._get_status_color(status),
        timestamp=scheduled_at,
    )
    # ... rest of embed creation
```

#### Step 4: Update API Endpoint for Better Filenames (~10 minutes)

```python
# services/api/routes/export.py
import re
from datetime import datetime

def generate_calendar_filename(game_title: str, scheduled_at: datetime) -> str:
    """Generate descriptive filename for calendar download."""
    # Remove special characters except spaces and hyphens
    safe_title = re.sub(r'[^\w\s-]', '', game_title).strip()
    safe_title = re.sub(r'[-\s]+', '-', safe_title)[:100]
    date_str = scheduled_at.strftime('%Y-%m-%d')
    return f"{safe_title}_{date_str}.ics"

@router.get("/game/{game_id}")
async def export_game(
    game_id: str,
    user: auth_schemas.CurrentUser = Depends(auth_deps.get_current_user),  # Keep auth!
    db: AsyncSession = Depends(database.get_db),
    role_service: roles_module.RoleVerificationService = Depends(
        permissions_deps.get_role_service
    ),
) -> Response:
    """Export a single game to iCal format (requires authentication)."""
    # Existing permission checking code stays the same

    # ... fetch game and check permissions ...

    service = CalendarExportService(db)
    ical_data = await service.export_game(game_id)

    # Generate descriptive filename
    filename = generate_calendar_filename(game.title, game.scheduled_at)

    return Response(
        content=ical_data,
        media_type="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

#### Step 5: Add Frontend URL Configuration (~5 minutes)

```python
# services/bot/config.py
class BotConfig:
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
```

### User Flow

1. **User clicks Discord game card title**
   - Opens browser: `https://your-site.com/download-calendar/{game_id}`

2. **Frontend checks authentication**
   - If authenticated: Proceeds to step 3
   - If not: `ProtectedRoute` redirects to `/login`

3. **After authentication (or if already logged in)**
   - OAuth callback redirects back to `/download-calendar/{game_id}`
   - Page automatically calls API with session cookie

4. **API validates permissions**
   - Checks: host, participant, admin, or bot manager
   - Returns 403 if unauthorized

5. **File downloads**
   - Browser downloads with descriptive filename
   - User sees "Downloading calendar..." message
   - Redirects to `/my-games` after download

### Alternative Options (Not Selected)
```python
# services/bot/formatters/game_message.py
def create_game_embed(...) -> discord.Embed:
    calendar_url = f"{settings.BASE_URL}/api/v1/export/game/{game_id}"

    embed = discord.Embed(
        title=game_title,
        url=calendar_url,  # Add this line - makes title clickable
        description=truncated_description,
        color=GameMessageFormatter._get_status_color(status),
        timestamp=scheduled_at,
    )
    # ... rest of embed creation
```

**Then relax export endpoint permissions and add descriptive filenames:**
```python
# services/api/routes/export.py
import re

@router.get("/game/{game_id}")
async def export_game(
    game_id: str,
    db: AsyncSession = Depends(database.get_db),
) -> Response:
    # No authentication required - anyone with game_id can download
    # Game info is already public in Discord channel

    # Fetch game to get title and date for filename
    game = await db.get(GameSession, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    service = CalendarExportService(db)
    ical_data = await service.export_game(game_id)

    # Generate descriptive filename: "Game-Title_YYYY-MM-DD.ics"
    safe_title = re.sub(r'[^\w\s-]', '', game.title).strip()
    safe_title = re.sub(r'[-\s]+', '-', safe_title)[:100]  # Max 100 chars
    date_str = game.scheduled_at.strftime('%Y-%m-%d')
    filename = f"{safe_title}_{date_str}.ics"

    return Response(
        content=ical_data,
        media_type="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

**Filename Examples:**
- "D-D-Campaign_2025-11-15.ics"
- "Poker-Night_2025-12-25.ics"
- "Weekly-Meetup_2025-01-10.ics"

**Changes needed:**
1. Add `url` parameter to `create_game_embed()`
2. Remove authentication decorators from export endpoint
3. Add filename generation logic with title sanitization
4. Simplify export service to not require user_id checks

**Total time: 10-15 minutes**

---

**Option B: Link to Web App (30 minutes)**
```python
embed = discord.Embed(
    title=game_title,
    url=f"{settings.BASE_URL}/games/{game_id}",  # Link to web page
    description=truncated_description,
    ...
)
```

User flow: Click title → Web page → Click download button
**Total time: 30 minutes** (add URL config + modify embed)

---

**Option C: Separate Public Endpoint (30 minutes)**
Create new public endpoint alongside secured one:
```python
@router.get("/public/game/{game_id}")  # New public endpoint
async def export_game_public(game_id: str, db: AsyncSession) -> Response:
    # No auth required

@router.get("/game/{game_id}")  # Keep existing secured endpoint
async def export_game(
    game_id: str,
    user: CurrentUser = Depends(get_current_user),  # Still requires auth
    db: AsyncSession = Depends(database.get_db),
) -> Response:
    # Original secured implementation
```

**Total time: 30 minutes** (new endpoint + modify embed)

### Recommended: Option A - Direct API Link

**Why this is best:**
1. ✅ **5 minutes implementation** - Just add URL to embed + remove auth
2. ✅ **Instant download** - Click title → file downloads immediately
3. ✅ **No security concerns** - Game info already public in Discord
4. ✅ **Simplest code** - Removes authentication complexity
5. ✅ **Best UX** - One click to download

**Trade-offs:**
- Anyone with game_id can download (acceptable per user - info is public)
- Can't revoke access to calendar after posting (acceptable - posted = public)

### Complete Implementation Estimate
**Option A (Direct API): 5-10 minutes**
**Option B (Web App Link): 30 minutes**
**Option C (Public Endpoint): 30 minutes**

All approaches are **dramatically simpler** than the button approach!

## Implementation Guidance

### Objectives
- Allow Discord users to download calendar files from game cards with authentication
- Use frontend download page approach with protected route
- Provide descriptive filenames for downloaded .ics files
- Handle errors gracefully (not authenticated, no permission, game not found)
- Maintain existing permission checks (host, participant, admin, or bot manager)

### Key Tasks (Frontend Download Page with Authentication)
1. Create new frontend page component: `/download-calendar/:gameId`
2. Add route with `ProtectedRoute` wrapper to App.tsx
3. Update Discord bot embed to link to frontend URL
4. Add `FRONTEND_URL` configuration to bot service
5. Update API endpoint to generate descriptive filenames
6. Add game title and date sanitization for safe filenames

### Dependencies
- Existing: `useAuth` hook (frontend/src/hooks/useAuth.ts)
- Existing: `ProtectedRoute` component (frontend/src/components/ProtectedRoute.tsx)
- Existing: OAuth redirect flow (services/api/routes/auth.py)
- Existing: CalendarExportService (services/api/services/calendar_export.py)
- Existing: Permission checking (services/api/dependencies/permissions.py)
- Configuration: `FRONTEND_URL` environment variable for bot service

### Success Criteria
- Embed title is clickable on all game announcement messages
- Clicking title opens browser to frontend download page
- Unauthenticated users are redirected to `/login` page
- After authentication, user is redirected back to download page
- Calendar downloads automatically with correct permissions
- Unauthorized users see clear error message (403 Forbidden)
- Filename is descriptive: `Game-Title_YYYY-MM-DD.ics`
- Calendar file imports successfully into Google Calendar, Outlook, Apple Calendar
- Works on new games and existing persistent game messages
- Loading states and error messages display properly

### Technical Notes
- Discord embed title becomes clickable hyperlink when URL is set
- URL points to frontend page, not directly to API
- Frontend `ProtectedRoute` handles authentication redirect automatically
- OAuth callback includes return URL, redirects back after login
- Session cookie automatically included in fetch requests (`credentials: 'include'`)
- API maintains existing authentication and permission checks
- Filename generation: Sanitize title + format date + .ics extension
- Filename sanitization: Remove special characters, replace spaces with hyphens
- Date format: YYYY-MM-DD for sortable filenames
- CalendarExportService already generates correct iCal format
- `Content-Disposition` header triggers browser download with custom filename

### Filename Generation Pattern
```python
import re
from datetime import datetime

def generate_calendar_filename(game_title: str, scheduled_at: datetime) -> str:
    """Generate descriptive filename for calendar download.

    Args:
        game_title: Game title (may contain special characters)
        scheduled_at: Game scheduled datetime

    Returns:
        Safe filename: "Game-Title_YYYY-MM-DD.ics"

    Examples:
        "D&D Campaign" + 2025-11-15 → "D-D-Campaign_2025-11-15.ics"
        "Poker Night!" + 2025-12-25 → "Poker-Night_2025-12-25.ics"
    """
    # Remove special characters except spaces and hyphens
    safe_title = re.sub(r'[^\w\s-]', '', game_title).strip()

    # Replace multiple spaces/hyphens with single hyphen
    safe_title = re.sub(r'[-\s]+', '-', safe_title)

    # Truncate if too long (max 100 chars before date)
    if len(safe_title) > 100:
        safe_title = safe_title[:100].rstrip('-')

    # Format date
    date_str = scheduled_at.strftime('%Y-%m-%d')

    return f"{safe_title}_{date_str}.ics"
```

### Implementation Summary

**Total implementation time: ~1 hour**

**Files to create:**
1. `frontend/src/pages/DownloadCalendar.tsx` - New download page component

**Files to modify:**
2. `frontend/src/App.tsx` - Add new route with ProtectedRoute
3. `services/bot/formatters/game_message.py` - Update embed URL to frontend
4. `services/bot/config.py` - Add FRONTEND_URL configuration
5. `services/api/routes/export.py` - Add descriptive filename generation (keep existing auth)

**No changes needed:**
- Authentication system (already works)
- Permission checking (already works)
- CalendarExportService (already works)
- ProtectedRoute redirect logic (already works)

**Environment variables:**
- `FRONTEND_URL` - URL of frontend application (e.g., https://your-site.com)
