# Game Host Guide

This guide is for Discord guild members who want to create and manage game sessions using the Game Scheduler bot.

## Prerequisites

- Discord account and membership in a guild with Game Scheduler bot installed
- Host permissions (configured by guild administrator)
- Web browser for accessing the dashboard

## Step 1: Access the Web Dashboard

### Logging In

1. Navigate to the Game Scheduler web dashboard (URL provided by your guild administrator)
2. Click "Login with Discord"
3. Authorize the application to access your Discord account
   - **Required permissions**:
     - `identify` - Access your Discord username and avatar
     - `guilds` - See which guilds you're a member of
4. After authorization, you'll be redirected back to the dashboard

### OAuth Login Process

The login process uses Discord's OAuth2 authentication:

- Your login session is secure and expires after 24 hours
- Access tokens are stored server-side, never exposed to the browser
- You can revoke application access anytime via Discord's "Authorized Apps" settings

## Step 2: Select Your Guild

After logging in:

1. You'll see a list of Discord guilds where you're a member
2. Only guilds with the Game Scheduler bot installed will appear
3. Click on the guild where you want to create a game
4. If you only have access to one guild, it will be selected automatically

## Step 3: Create a Game

### Using Game Templates

Game templates provide pre-filled defaults to speed up game creation. Your guild administrator creates and manages templates.

1. From the guild dashboard, click "Create Game"
2. Select a template from the dropdown
   - Templates include defaults for:
     - Announcement channel
     - Max players
     - Expected duration
     - Reminder timing
     - Notification roles
     - Signup instructions
     - Location
3. The default template is pre-selected automatically

### Filling Out Game Details

Required fields:

- **Title**: Name of your game session (e.g., "D&D Session 5", "Board Game Night")
- **Scheduled Time**: When the game starts (DateTimePicker uses your browser's timezone)
- **Channel**: Discord channel where the announcement will be posted

Optional fields:

- **Description**: Additional details about the game
- **Location**: Where the game takes place (e.g., "Discord Voice Channel", "Local Game Store")
  - Defaults to template value if not specified
- **Max Players**: Participant limit (empty = unlimited)
  - Defaults to template value if not specified
- **Expected Duration**: How long the game will last (hours and minutes)
  - Defaults to template value if not specified
- **Reminder Time**: When to send reminder notifications (minutes before start)
  - Defaults to template value if not specified
- **Signup Instructions**: Instructions for players joining the game
  - Defaults to template value if not specified
- **Signup Method**: How players can join the game
  - **Self Signup**: Players click Discord buttons to join/leave
  - **Host Selected**: Only you can add players (buttons disabled)
  - **Role Based**: Players click Discord buttons to join, but their position in the participant list is determined by their Discord roles at the time they sign up. Members whose roles match the template's priority list are sorted ahead of other players. This is useful when a game is likely to fill up and you want certain role groups to have guaranteed spots over others.
  - Defaults to template's default method if not specified
- **Initial Participants**: Pre-fill the participant list with Discord mentions or placeholders
  - Enter Discord usernames (e.g., `@PlayerName`) or plain text placeholders
  - Each participant on a new line or separated by commas
  - Invalid mentions will show suggestions for disambiguation

**Bot Manager Exclusive Feature**:

- **Host**: Bot managers can specify another user as the game host by entering their Discord mention
- Regular users cannot access this field - games are automatically hosted by the creator

### Image Attachments (Optional)

You can attach images to your game announcement:

- **Thumbnail**: Small image displayed in the game card (max 5MB, PNG/JPEG/GIF/WebP)
- **Full Image**: Larger image shown in detailed views (max 5MB, PNG/JPEG/GIF/WebP)

### Validation and Submission

1. Click "Create Game" to submit
2. If there are validation errors (e.g., invalid @mentions), you'll see:
   - Specific error messages
   - Suggestions for ambiguous usernames (click to select the correct user)
   - All your form data is preserved - no need to re-enter everything
3. Once validation passes, the game is created and announced in Discord

## Step 4: Manage Your Games

### Viewing Your Games

1. From the guild dashboard, click "My Games"
2. You'll see all games you're hosting with status indicators:
   - **SCHEDULED**: Game is upcoming
   - **IN_PROGRESS**: Game is currently happening
   - **COMPLETED**: Game has finished
   - **CANCELLED**: Game was canceled

### Editing Games

1. Click on a game to view details
2. Click "Edit Game"
3. Modify any game details (same fields as creation)
4. Click "Update Game" to save changes
5. Changes are announced in Discord if participants are affected

**Note**: You can only edit games you're hosting (or if you're a bot manager)

### Managing Participants

During game creation or editing, you can:

- Add participants using Discord @mentions
- Add placeholder participants (text without @mention)
- Reorder participants using drag-and-drop
- Remove participants before the game starts

After game creation:

- Players can join/leave using Discord buttons (if signup method is "Self Signup")
- You can see who's joined in the game details page
- Waitlist is automatically managed when max players is reached

### Recording Rewards

After a game completes, you can record what was awarded to participants:

1. Open the game details page for a completed game
2. Click "Edit Game"
3. Enter reward details in the **Rewards** field (e.g., "Magic sword +1, 500 gold")
4. Click "Update Game" to save

Rewards are displayed as a spoiler in the archived game announcement so players can choose when to reveal them.

If you checked **"Remind me to add rewards"** when creating the game, the bot will send you a DM when the game completes as a prompt to fill this in.

### Save and Archive

If your guild has an archive channel configured on the template, a **Save and Archive** button appears on the edit form once you have entered a rewards value for a completed game. Clicking it saves the rewards and immediately moves the game to the archive channel in a single step.

### Canceling Games

1. View game details for your hosted game
2. Click "Cancel Game"
3. Confirm the cancellation
4. All participants receive a cancellation notification in Discord
5. The game status changes to CANCELLED

**Note**: Only hosts and bot managers can cancel games

## Step 5: Understanding Notifications

### Automatic Notifications

The bot sends notifications to participants:

- **Game Creation**: Announcement posted in the configured channel
- **Reminder**: Sent at the time specified in "Reminder Time" (e.g., 24 hours before)
- **Waitlist Promotion**: Players are notified if they move from waitlist to confirmed
- **Game Cancellation**: All participants notified when a game is canceled
- **Game Updates**: Participants notified of significant changes (time, location, etc.)

### Notification Roles

Templates can specify Discord roles to ping when games are created:

- Guild administrators configure which roles receive notifications
- These roles are notified in addition to individual participants
- Useful for game-type specific announcement roles (e.g., @RPG-Players, @BoardGamers)

## Host Permissions

### Who Can Host Games?

Host permissions are configured by guild administrators in two ways:

1. **Template-Based Permissions**:
   - Each template can specify `allowed_host_role_ids`
   - Only users with these roles can create games using that template
   - If empty, all bot managers can use the template

2. **Guild-Level Permissions**:
   - **Bot Manager Roles**: Roles configured by guild admin that grant hosting permissions
   - **Discord Permissions**: Users with `MANAGE_GUILD` or `ADMINISTRATOR` Discord permissions
   - **Require Host Role** setting: Guild admin can toggle whether bot manager roles are required

### Checking Your Permissions

If you can't see the "Create Game" button or templates:

1. Check with your guild administrator about host permissions
2. Verify you have the required roles
3. Confirm the guild has configured game templates

## Common Issues and Solutions

### Can't See Any Guilds After Login

- Ensure you're a member of a guild with the Game Scheduler bot installed
- Try logging out and logging back in
- Clear your browser cache and cookies

### Can't Create Games

- Verify you have host permissions (check with guild admin)
- Ensure your guild has at least one game template configured
- Check that you have the required roles for the template

### @Mention Validation Errors

- Ensure usernames are spelled correctly
- Include the @ symbol for Discord mentions
- Click on suggested usernames if disambiguation is offered
- Verify the user is a member of your Discord guild

### Game Doesn't Appear in Discord

- Verify you selected the correct channel when creating the game
- Ask your guild administrator to check bot permissions - see [Guild Admin Guide: Bot Permissions](GUILD-ADMIN.md#step-1-invite-the-bot-to-your-server)
- Ensure the channel is configured as an announcement channel (check with guild admin)
- Contact your guild administrator if the bot is offline or unresponsive

### Can't Edit a Game

- Only game hosts and bot managers can edit games
- Completed or canceled games cannot be edited
- Ensure you're logged in with the correct Discord account

## Best Practices

### Creating Clear Game Announcements

- Use descriptive titles (include session number for ongoing campaigns)
- Provide detailed descriptions with expectations
- Specify location clearly (voice channel, physical address, etc.)
- Set realistic max player limits
- Include any required materials or preparation in signup instructions

### Managing Participants

- Pre-fill known participants to reserve their spots
- Use placeholder names for "friends of friends" not yet in Discord
- Set appropriate reminder times (24 hours is standard)
- Choose signup method based on game type:
  - Self Signup: Drop-in games, open sessions
  - Host Selected: Curated groups, campaign continuity

### Timing and Scheduling

- Account for your timezone when setting game times (the DatePicker uses your browser timezone)
- Build in buffer time for setup and player arrival
- Set reminder times that give players enough notice
- Cancel games as early as possible if plans change

## Next Steps

- **For Guild Admins**: See [Guild Admin Guide](GUILD-ADMIN.md) for bot configuration
- **For Players**: See [Player Guide](PLAYER-GUIDE.md) for joining games
- **For Developers**: See [Developer Documentation](developer/README.md) for contributing

## Getting Help

If you need assistance:

1. Check this guide's [Common Issues](#common-issues-and-solutions) section
2. Ask your guild administrator about permission configuration
3. Review the game creation form validation messages
4. Contact the bot maintainer for technical support
5. Check the project's GitHub repository for documentation updates
