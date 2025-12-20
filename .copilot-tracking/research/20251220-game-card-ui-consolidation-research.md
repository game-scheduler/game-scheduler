<!-- markdownlint-disable-file -->
# Task Research Notes: Game Card UI Consolidation

## Overview

This research covers consolidating the UI layout between the **Web Game Details Page** and the **Discord Bot Game Card** to present a unified, consistent user experience. Both will follow a standardized field order and layout structure.

## Research Executed

### File Analysis

#### Web Frontend - GameDetails Page
- [frontend/src/pages/GameDetails.tsx](frontend/src/pages/GameDetails.tsx)
  - **Current Layout Structure**:
    1. Title with Status chip
    2. Error alerts
    3. Description text
    4. Signup instructions (boxed, blue background)
    5. Divider
    6. Game Details section header
    7. When (full date format)
    8. Where (if available)
    9. Reminders (if set)
    10. Duration (if set)
    11. Channel name
    12. Host chip (outlined, secondary color)
    13. Max Players display (shown as separate line)
    14. Divider
    15. Participants section with ParticipantList component
    16. Divider
    17. Action buttons (Export Calendar, Join/Leave, Edit, Cancel, Back)
  - **Current Removals**: None identified - max_players is currently shown
  - **ExportButton** component used for calendar download (will be replaced with calendar link)
  - Host displayed as Chip at bottom of details section

#### Web Frontend - GameCard Component
- [frontend/src/components/GameCard.tsx](frontend/src/components/GameCard.tsx)
  - **Current Layout**:
    1. Host with avatar (top of CardContent)
    2. Title with status chip
    3. Description (truncated)
    4. Horizontal flex layout with: When, Where (if available), Players, Duration (if set)
    5. View Details button
  - **Key Features**:
    - Avatar already displayed next to host
    - Compact horizontal layout for quick scanning
    - Player count shown as "participantCount/maxPlayers"

#### Discord Bot - Game Message Formatter
- [services/bot/formatters/game_message.py](services/bot/formatters/game_message.py)
  - **Current Embed Field Order**:
    1. Title (embed title property)
    2. Description (embed description)
    3. Author field: "Host: {display_name}" with avatar icon_url
    4. When: Full Discord timestamp + relative time
    5. Where: Location/address (if provided)
    6. Players: "current/max" (inline with Duration)
    7. Host: Mention (only if no host_display_name provided for backward compatibility)
    8. Duration: (inline with Players)
    9. Calendar link: Download Calendar button (inline)
    10. Voice Channel: Discord channel mention (inline)
    11. Participants: List of confirmed participants
    12. Waitlist: List of overflow participants (if any)
    13. Signup Instructions: (if provided)
    14. Footer: Status
  - **Author Field**: Already uses host avatar via `icon_url` parameter
  - **Calendar Link**: Already implemented as embed field with markdown link

#### Frontend Types Structure
- [frontend/src/types/index.ts](frontend/src/types/index.ts) - GameSession interface
  - Available fields: `id`, `title`, `description`, `signup_instructions`, `scheduled_at`, `where`, `max_players`, `guild_id`, `channel_id`, `channel_name`, `message_id`, `host` (Participant), `reminder_minutes`, `notify_role_ids`, `expected_duration_minutes`, `status`, `participant_count`, `participants`
  - Participant interface: `id`, `game_session_id`, `user_id`, `discord_id`, `display_name`, `avatar_url`, `joined_at`, `pre_filled_position`
  - Note: `avatar_url` field already exists in Participant interface

### Code Search Results

#### ExportButton Component
- [frontend/src/components/ExportButton.tsx](frontend/src/components/ExportButton.tsx)
  - Creates a Button with Download icon
  - Currently used only on GameDetails page
  - Makes API call to `/api/v1/export/game/{gameId}`
  - Returns .ics file for calendar import
  - Will be replaced by calendar link in consolidated UI

#### ParticipantList Component
- Uses `participants` array and `maxPlayers` prop
- Renders confirmed and overflow participants separately
- Shows count as "X/N" format

## Key Discoveries

### Web GameDetails Page - Current Issues
1. **Max Players shown separately**: Currently displayed as a standalone line item, should be consolidated into Players count display
2. **Export Button placement**: Currently between divider and action buttons, should be replaced by calendar link on the "When" line
3. **Host display**: Currently shown as Chip at bottom of details section, should move to top near When
4. **Field order inconsistency**: Different from Discord card layout

### Discord Bot Card - Current State
1. **Already properly structured**: Fields already follow logical order with host at top (in author field)
2. **Calendar link**: Already implemented as embed field link
3. **Channel reference**: Uses Discord voice channel mention syntax
4. **Participants display**: Already shows count and individual mentions

### Unified Target Layout

**Web GameDetails Page should become**:
1. Title with Status chip (keep top)
2. Description (keep)
3. **Host (with avatar) - MOVE TO TOP** ← Changes here
4. **When + Calendar link on same line** ← Consolidate
5. **Location (server_name # channel_name) + Where** ← Add/consolidate location display
6. Duration ← Move up
7. Reminders ← Keep
8. Channel ← Keep
9. Signup Instructions (only for host) ← Already conditional, keep boxed style
10. **Divider**
11. Participants (showing X/N count) ← Keep, update count format
12. **Remove Max Players separate display** ← Consolidate into count
13. **Remove Export Calendar button** ← Replace with link
14. Action buttons (Edit, Cancel, Join/Leave, Back)

**Discord Bot Card should become**:
1. Title (embed title)
2. Description (embed description)
3. **Host (with avatar in author field)** ← Already correct
4. **When + Calendar link** ← Reorganize fields
5. **# channel_name + Where** ← Add location context
6. Duration
7. **Channel reference** ← Update field name/format
8. Signup Instructions (only for non-host viewers) ← Already present
9. **Participants (showing X/N count)** ← Keep, ensure consistent format
10. **Remove Waitlist display separately** ← Consolidate or adjust

## Recommended Approach

### Phase 1: Web GameDetails Page Restructuring
1. **Move Host section to top** - Display with avatar, name, and optional guild member status
2. **Consolidate When + Calendar** - Single line with timestamp and calendar link button/icon
3. **Add Location context** - Display server_name (guild) and #channel_name together
4. **Remove Max Players line** - Incorporate into Participants count display as "X/N"
5. **Remove ExportButton** - Replace with calendar download link next to "When"
6. **Update Participants heading** - Show count in format "Participants (X/N)"
7. **Keep Signup Instructions boxed** - Only show if user is host

### Phase 2: Discord Bot Card Field Reorganization
1. **Verify Author field** - Ensure host avatar displays correctly with author field
2. **Reorganize embed fields** - Match new web layout order
3. **Consolidate location** - Show guild context with channel name
4. **Update field display** - Ensure consistent inline/non-inline field formatting
5. **Participants format** - Match web display as "Participants (X/N)"
6. **Calendar link** - Keep as inline field or part of When field

### Implementation Guidance
- **Objectives**:
  - Create visual consistency between web and Discord card layouts
  - Improve information hierarchy by moving host to top
  - Remove redundant UI elements (export button, max players line)
  - Consolidate related information on single lines
- **Key Tasks**:
  1. Restructure GameDetails layout sections
  2. Update Participants component to display count format
  3. Add calendar link to When line
  4. Reorganize Discord embed fields
  5. Update location display to show guild + channel context
- **Dependencies**:
  - `avatar_url` already available in Participant interface
  - Calendar download link functionality already exists (via ExportButton)
  - ParticipantList component handles count display
- **Success Criteria**:
  - Both web and Discord displays follow identical field order
  - Host avatar displays at top in both interfaces
  - Calendar link appears next to When timestamp
  - Max players consolidated into participant count
  - Export button removed and replaced with calendar link
  - Location shows server_name and channel_name together
