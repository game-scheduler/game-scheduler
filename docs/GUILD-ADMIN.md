# Guild Administrator Guide

This guide is for Discord server administrators who want to add the Game Scheduler bot to their guild and configure it for their community.

## Prerequisites

- Discord server (guild) ownership or Administrator permission
- Bot invite URL from the bot owner or your self-hosted instance

## Step 1: Invite the Bot to Your Server

### Using a Pre-Generated Invite URL

1. Obtain the bot invite URL from:
   - The bot owner/maintainer if using a hosted instance
   - Your deployment documentation if self-hosting (see [Developer Guide](developer/README.md))
2. Open the invite URL in your browser
3. Select your server from the dropdown
4. Review the requested permissions and click "Authorize"
5. Complete the captcha verification if prompted

The bot will join your server immediately and be ready for configuration.

### Required Bot Permissions

The bot requires these Discord permissions to function properly:

- **View Channels** - Read channel list for game announcements
- **Send Messages** - Post game announcements and updates
- **Send Messages in Threads** - Post updates in thread discussions
- **Embed Links** - Display rich game information embeds
- **Attach Files** - Upload game images and attachments
- **Use External Emojis** - Enhanced message formatting (optional)
- **Add Reactions** - React to messages (optional)

**Note**: If you're self-hosting or developing, see the [Developer Guide](developer/README.md) for instructions on generating invite URLs from the Discord Developer Portal.

## Step 2: Configure Bot Manager Roles

Bot manager roles determine who can create and manage games beyond Discord's built-in permissions. By default, users with `MANAGE_GUILD` or `ADMINISTRATOR` permissions can configure the bot.

### Setting Bot Manager Roles

1. Log into the [Game Scheduler Web Dashboard](https://your-dashboard-url.com)
2. Select your guild from the guild list
3. Navigate to "Guild Settings"
4. In the "Bot Manager Roles" section:
   - Add Discord roles that should have host permissions
   - These roles allow users to create and manage games
   - Users with these roles can also manage game templates

### Permission Model

The system uses a per-template host role model:

- By default, only users with assigned bot manager roles (or `MANAGE_GUILD` permission) can create games from a template.
- To allow all server members to host games from a specific template, add the `@everyone` role to that template's **Allowed Host Roles**. Discord's `@everyone` role is automatically included in every member's effective role set, so this grants open access without altering any other permissions.
- Bot manager roles always retain full game management permissions regardless of template settings.

## Step 3: Configure Channels for Game Announcements

The bot posts game announcements in specific channels you designate.

### Adding Announcement Channels

1. In the Web Dashboard, navigate to your guild settings
2. Go to "Channel Configuration"
3. Click "Add Channel"
4. Select the channel from the dropdown (bot must have "View Channels" permission)
5. Toggle channel active status (inactive channels won't receive new announcements)

### Channel Requirements

- Bot must have "Send Messages" permission in the channel
- Bot must have "Embed Links" permission to display rich game cards
- Bot must have "Attach Files" permission if games include images

### Managing Multiple Channels

You can configure multiple announcement channels:

- Each game is posted to ONE channel (selected by the host)
- Hosts choose the channel when creating a game
- Different channels can be used for different game types (e.g., #board-games, #rpg-sessions)

## Step 4: Create Game Templates (Optional)

Game templates provide pre-filled defaults for common game types, making it faster for hosts to create games.

### Why Use Templates?

- Pre-set max players for specific game types (e.g., "D&D Session" defaults to 5 players)
- Default reminder times (e.g., 24 hours before)
- Pre-configured notification roles
- Consistent signup instructions across similar games
- Restrict which roles can host specific game types

### Creating Templates

1. In the Web Dashboard, navigate to "Templates" under your guild
2. Click "Create Template"
3. Configure template settings:
   - **Name**: Template identifier (e.g., "D&D Session", "Board Game Night")
   - **Description**: What this template is for
   - **Default Channel**: Where games using this template will be announced
   - **Max Players**: Default participant limit
   - **Expected Duration**: How long games typically last (minutes)
   - **Reminder Time**: When to send reminder notifications (minutes before start)
   - **Notification Roles**: Discord roles to ping when games are created
   - **Allowed Player Roles**: Roles that can join games (empty = everyone)
   - **Allowed Host Roles**: Roles that can create games from this template (empty = all bot managers)
   - **Where**: Default location (e.g., "Discord Voice", "Local Game Store")
   - **Signup Instructions**: Instructions displayed to players
   - **Allowed Signup Methods**: Which methods players can use (Discord buttons, web dashboard, react with emoji)
   - **Default Signup Method**: Preferred signup method for this template

4. Click "Create Template"

### Template Management

- **Default Template**: Mark one template as default - it will be pre-selected when creating games
- **Template Order**: Drag templates to reorder how they appear in the creation form
- **Editing Templates**: Changes to templates do NOT affect existing games created from them
- **Deleting Templates**: Games created from deleted templates remain unaffected

## Step 5: Test the Bot

### Verify Bot Functionality

1. Create a test game using the web dashboard or `/create-game` slash command
2. Check that the game announcement appears in the designated channel
3. Try joining/leaving the game using Discord buttons
4. Verify that notifications are sent at the configured reminder time

### Common Issues

- **Bot can't see channels**: Verify "View Channels" permission is granted
- **Can't post announcements**: Verify "Send Messages" and "Embed Links" permissions in the target channel
- **Slash commands don't appear**: Re-invite bot with `applications.commands` scope
- **Users can't create games**: Verify bot manager roles are configured correctly

## Security Considerations

### Permission Model

- Bot uses Discord's role-based permission system
- Bot manager roles grant game management permissions
- Web dashboard requires Discord OAuth login - users must be guild members
- Bot cannot access channels it doesn't have permissions for

### Data Privacy

- Bot only stores game scheduling data (titles, descriptions, participants)
- User Discord IDs are stored for participant management
- No message content is read or stored
- Bot uses Discord API to verify permissions in real-time

## Next Steps

- **For Game Hosts**: See [Host Guide](HOST-GUIDE.md) for creating and managing games
- **For Players**: See [Player Guide](PLAYER-GUIDE.md) for joining games and receiving notifications
- **For Developers**: See [Developer Documentation](developer/README.md) for contributing to the project

## Getting Help

If you encounter issues:

1. Check the [Common Issues](#common-issues) section above
2. Review bot permissions in Discord Server Settings
3. Verify channel permissions for announcement channels
4. Check the project's GitHub repository for known issues
5. Contact the bot maintainer for support
