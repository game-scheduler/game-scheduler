<!-- markdownlint-disable-file -->

# Task Details: Game Card UI Consolidation - Web and Discord

## Research Reference

**Source Research**: #file:../research/20251220-game-card-ui-consolidation-research.md

## Phase 1: Web GameDetails Page - Layout Restructuring

### Task 1.1: Move host section to top of game details

Move the host information display from the bottom of the Game Details section (currently line ~265) to appear after the title and before the "When" field. Host should display with avatar, name, and be visually consistent with the GameCard component.

- **Files**:
  - [frontend/src/pages/GameDetails.tsx](frontend/src/pages/GameDetails.tsx) - Restructure host display section

- **Success**:
  - Host section appears at top of game details with avatar displayed
  - Layout visually matches GameCard component structure
  - Host information properly aligned with avatar

- **Research References**:
  - #file:../research/20251220-game-card-ui-consolidation-research.md (Lines 54-72) - GameCard component already shows host at top with avatar
  - #file:../research/20251220-game-card-ui-consolidation-research.md (Lines 153-164) - Target unified layout shows host first

- **Dependencies**:
  - GameCard component reference for visual consistency

### Task 1.2: Consolidate When + Calendar link on same line

Combine the "When" timestamp display with the calendar download link on a single line. Replace the ExportButton component reference with an inline calendar link icon/button.

- **Files**:
  - [frontend/src/pages/GameDetails.tsx](frontend/src/pages/GameDetails.tsx) - Update When field to include calendar link
  - [frontend/src/components/ExportButton.tsx](frontend/src/components/ExportButton.tsx) - Reference for calendar download logic

- **Success**:
  - When timestamp and calendar link display on same line
  - Calendar link is clickable and functional
  - Icon-based link maintains clean aesthetic

- **Research References**:
  - #file:../research/20251220-game-card-ui-consolidation-research.md (Lines 90-95) - Current When field structure
  - #file:../research/20251220-game-card-ui-consolidation-research.md (Lines 140-142) - ExportButton component details
  - #file:../research/20251220-game-card-ui-consolidation-research.md (Lines 165-171) - Target consolidated layout

- **Dependencies**:
  - Task 1.1 completion (host moved to top)

### Task 1.3: Add location context with server and channel display

Add a new display field showing both the server (guild) name and channel name together. This consolidates location information in one visual area.

- **Files**:
  - [frontend/src/pages/GameDetails.tsx](frontend/src/pages/GameDetails.tsx) - Add location field
  - [frontend/src/types/index.ts](frontend/src/types/index.ts) - Reference for available fields (guild_id, channel_name)

- **Success**:
  - Location field displays server name and #channel_name
  - Information is clearly formatted and easy to read
  - Field appears in correct position in layout order

- **Research References**:
  - #file:../research/20251220-game-card-ui-consolidation-research.md (Lines 77-85) - Current channel display
  - #file:../research/20251220-game-card-ui-consolidation-research.md (Lines 172-175) - Target location display format
  - #file:../research/20251220-game-card-ui-consolidation-research.md (Lines 120-125) - Available guild and channel data

- **Dependencies**:
  - Task 1.1 and 1.2 completion

### Task 1.4: Consolidate participant count and remove max players line

Update the participant count display to show format "X/N" and remove the separate "Max Players" line that currently appears (line ~266). The count should appear in the Participants section heading.

- **Files**:
  - [frontend/src/pages/GameDetails.tsx](frontend/src/pages/GameDetails.tsx) - Remove max players line, update participants heading
  - [frontend/src/components/ParticipantList.tsx](frontend/src/components/ParticipantList.tsx) - Reference for participant rendering

- **Success**:
  - Max Players separate line removed
  - Participants heading shows format "Participants (X/N)"
  - Count calculated from participant_count and max_players fields

- **Research References**:
  - #file:../research/20251220-game-card-ui-consolidation-research.md (Lines 110-115) - Current max players display
  - #file:../research/20251220-game-card-ui-consolidation-research.md (Lines 178-182) - Target consolidated format

- **Dependencies**:
  - Task 1.1 completion

### Task 1.5: Remove ExportButton and replace with calendar link

Remove the ExportButton component from the action buttons section (line ~272) and replace it with an inline calendar link integrated into the "When" line as per Task 1.2.

- **Files**:
  - [frontend/src/pages/GameDetails.tsx](frontend/src/pages/GameDetails.tsx) - Remove ExportButton import and usage

- **Success**:
  - ExportButton component no longer imported or rendered
  - Calendar link functionality moved to When field (Task 1.2)
  - No broken references

- **Research References**:
  - #file:../research/20251220-game-card-ui-consolidation-research.md (Lines 37-40) - ExportButton current usage

- **Dependencies**:
  - Task 1.2 completion

### Task 1.6: Update signup instructions display for host-only visibility

Ensure signup instructions are only displayed when the current user is the host. The boxed blue-background style should be maintained.

- **Files**:
  - [frontend/src/pages/GameDetails.tsx](frontend/src/pages/GameDetails.tsx) - Add conditional rendering for signup instructions

- **Success**:
  - Signup instructions only visible to host
  - Non-hosts cannot see signup instructions
  - Styling remains consistent with current design

- **Research References**:
  - #file:../research/20251220-game-card-ui-consolidation-research.md (Lines 60-70) - Current signup instructions rendering
  - #file:../research/20251220-game-card-ui-consolidation-research.md (Lines 183-186) - Target host-only display

- **Dependencies**:
  - isHost variable already available in component (line ~129)

## Phase 2: Web GameDetails Page - Testing and Validation

### Task 2.1: Test GameDetails page layout changes

Run component tests and verify all layout changes work correctly. Test with various game data scenarios including games with/without where, reminders, duration, signup instructions.

- **Files**:
  - [frontend/src/pages/__tests__/GameDetails.test.tsx](frontend/src/pages/__tests__/GameDetails.test.tsx) - Unit tests for GameDetails

- **Success**:
  - All existing tests pass
  - New layout renders without console errors
  - All conditional fields display correctly based on data
  - No layout shifts or responsive design issues

- **Research References**:
  - #file:../research/20251220-game-card-ui-consolidation-research.md (Lines 175-186) - All layout changes to verify

- **Dependencies**:
  - Phase 1 completion

### Task 2.2: Verify responsive design across screen sizes

Test GameDetails page layout on mobile, tablet, and desktop views to ensure fields remain readable and properly formatted.

- **Files**:
  - [frontend/src/pages/GameDetails.tsx](frontend/src/pages/GameDetails.tsx) - Responsive layout verification

- **Success**:
  - When + calendar link wraps appropriately on mobile
  - Location display readable on all screen sizes
  - Participant list remains accessible on small screens
  - No horizontal scrolling issues

- **Research References**:
  - #file:../research/20251220-game-card-ui-consolidation-research.md (Lines 175-186) - Layout structure to test

- **Dependencies**:
  - Phase 1 completion

## Phase 3: Discord Bot Card - Field Reorganization

### Task 3.1: Verify and document host author field with avatar

Verify that the Discord embed's author field correctly displays the host with avatar. The author field should use `set_author()` with name and icon_url parameters.

- **Files**:
  - [services/bot/formatters/game_message.py](services/bot/formatters/game_message.py) - Verify author field usage (lines ~105-111)

- **Success**:
  - Author field correctly populated with host_display_name
  - Avatar URL (icon_url) properly set from host_avatar_url parameter
  - Backward compatibility maintained for calls without avatar data

- **Research References**:
  - #file:../research/20251220-game-card-ui-consolidation-research.md (Lines 76-85) - Current Discord embed author field implementation
  - #file:../research/20251220-game-card-ui-consolidation-research.md (Lines 119-125) - Discord avatar URL formatting

- **Dependencies**:
  - None - verification only

### Task 3.2: Reorganize embed fields to match web layout order

Reorder the embed fields to match the unified layout: Host (author), When, Where, Duration, Channel, Signup Instructions, Participants. Remove or consolidate redundant fields.

- **Files**:
  - [services/bot/formatters/game_message.py](services/bot/formatters/game_message.py) - Reorganize embed.add_field() calls (lines ~112-165)

- **Success**:
  - Fields appear in standardized order matching web layout
  - No duplicate information displayed
  - Field inline/non-inline formatting consistent and readable

- **Research References**:
  - #file:../research/20251220-game-card-ui-consolidation-research.md (Lines 76-95) - Current Discord embed field order
  - #file:../research/20251220-game-card-ui-consolidation-research.md (Lines 165-186) - Target unified field order

- **Dependencies**:
  - Task 3.1 completion

### Task 3.3: Update location/channel field display

Consolidate the "Voice Channel" field to show context about guild/server alongside the channel. Update field name and format for consistency.

- **Files**:
  - [services/bot/formatters/game_message.py](services/bot/formatters/game_message.py) - Update channel field display (around line ~150)

- **Success**:
  - Channel field includes context about server/location
  - Field name clearly indicates it's a voice channel
  - Mention syntax remains functional in Discord

- **Research References**:
  - #file:../research/20251220-game-card-ui-consolidation-research.md (Lines 90-93) - Current channel mention format
  - #file:../research/20251220-game-card-ui-consolidation-research.md (Lines 172-175) - Target location display

- **Dependencies**:
  - Task 3.2 completion

### Task 3.4: Consolidate participant count format

Update the "Players" field to show count in format "X/N" and ensure consistency with web display. Update any related field labels.

- **Files**:
  - [services/bot/formatters/game_message.py](services/bot/formatters/game_message.py) - Update Players field (around line ~130)

- **Success**:
  - Participant count displays as "X/N" format consistently
  - Maximum player count properly included in display
  - Format matches web interface

- **Research References**:
  - #file:../research/20251220-game-card-ui-consolidation-research.md (Lines 88-90) - Current Players field
  - #file:../research/20251220-game-card-ui-consolidation-research.md (Lines 178-182) - Target count format

- **Dependencies**:
  - Task 3.2 completion

### Task 3.5: Remove or adjust waitlist display

Determine whether to remove the separate Waitlist field or consolidate it with the main Participants field. Update embed accordingly.

- **Files**:
  - [services/bot/formatters/game_message.py](services/bot/formatters/game_message.py) - Remove/adjust overflow participants display (lines ~153-157)

- **Success**:
  - Waitlist display adjusted or removed as appropriate
  - Participant count accurately reflects confirmed participants
  - No confusion about available spots vs overflow

- **Research References**:
  - #file:../research/20251220-game-card-ui-consolidation-research.md (Lines 93-96) - Current overflow/waitlist display
  - #file:../research/20251220-game-card-ui-consolidation-research.md (Lines 183-186) - Target adjustment guidance

- **Dependencies**:
  - Task 3.2 completion

## Phase 4: Discord Bot Card - Testing and Validation

### Task 4.1: Test game message formatting

Run existing game message formatter tests to ensure all field reorganization maintains correct functionality.

- **Files**:
  - [tests/services/bot/formatters/test_game_message.py](tests/services/bot/formatters/test_game_message.py) - Existing formatter tests

- **Success**:
  - All existing tests pass
  - New field order produces valid Discord embeds
  - No breaking changes to test expectations

- **Research References**:
  - #file:../research/20251220-game-card-ui-consolidation-research.md (Lines 76-95) - Current embed field structure

- **Dependencies**:
  - Phase 3 completion

### Task 4.2: Verify Discord embed rendering

Test actual Discord embed rendering by sending test messages to Discord to verify visual appearance and field layout.

- **Files**:
  - Documentation of test results and screenshots

- **Success**:
  - Embed renders correctly in Discord client
  - Fields display in proper order
  - Avatar displays correctly in author field
  - All text and links render properly

- **Research References**:
  - #file:../research/20251220-game-card-ui-consolidation-research.md (Lines 119-125) - Discord CDN avatar formatting

- **Dependencies**:
  - Phase 3 completion, Task 4.1 passing tests

## Dependencies

- Web frontend changes: React, TypeScript, MUI components
- Discord bot changes: discord.py library, embed formatting
- API data structure: avatar_url already available in Participant interface
- Calendar link functionality: Already exists via ExportButton logic

## Success Criteria

- Both web GameDetails and Discord embed follow identical field order
- Host information with avatar appears at top of both interfaces
- Calendar link integrated into When timestamp display
- Location context shows server and channel information
- Participant count displayed as "X/N" format
- Max players separate line removed from web interface
- Signup instructions only visible to host in web interface
- All unit tests passing
- Visual consistency maintained across responsive layouts
