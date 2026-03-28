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

### Bot Permissions

When you open the invitation URL, Discord will display the list of permissions the bot is requesting and ask you to approve them before it joins your server. The requested permissions are:

- **View Channels** - Read channel list for game announcements
- **Send Messages** - Post game announcements and updates
- **Embed Links** - Display game announcements as rich Discord embeds with formatted details, images, and signup buttons

For information on what data the bot stores, see [Data Privacy](#data-privacy).

**Note**: If you're self-hosting or developing, see the [Developer Guide](developer/README.md) for instructions on generating invite URLs from the Discord Developer Portal.

## Step 2: Roles

The bot defines four roles that control what members can do. Each bot role can be mapped to one or more Discord roles via the Web Dashboard, allowing you to align bot permissions with your existing guild structure.

### Management Roles

#### Bot Manager Role

The bot manager role allows a guild owner to share bot management responsibility with trusted members, without granting them full Discord administrator access. Bot managers can create and manage templates, configure guild settings, and create or manage any game regardless of other role restrictions.

**Note**: Discord guild administrators and the guild owner automatically have bot manager access without needing an explicit role assignment.

### Game Roles

Game roles allow bot managers to control who gets notified about new games, who can join them, and who can host them. These roles are configured per template, giving you fine-grained control over each game type.

#### Notify Role

Members with a notify role are pinged when a new game is created. This lets interested players hear about new games without having to monitor channels manually.

#### Player Role

Members with a player role can sign up for games. When no player roles are assigned to a template, any guild member can join.

#### Host Role

Members with a host role can create games from a specific template. Host roles are configured per template, so you can control who can run which types of games. Bot managers always retain host permissions regardless of template host role settings. When no host roles are assigned to a template, only bot managers can create games from it.

#### Note

The same Discord role can be assigned to multiple game bot roles — for example, a small home game group that rotates hosts could map a single "Sunday Players" Discord role to the notify, player, and host bot roles at once. If your server exists solely for one game, you could simply use `@everyone` for these three.

### Creating Discord Roles

Before mapping Discord roles to bot roles, you need to have the appropriate Discord roles created in your guild. If you need to create new roles:

1. Open your Discord server and go to **Server Settings**
2. Select **Roles** from the left sidebar
3. Click **Create Role** and configure the role name and color — the bot only uses role membership to identify users, so the role does not need any Discord permissions enabled
4. Assign the role to the appropriate members

For detailed instructions, see the [Discord Roles documentation](https://support.discord.com/hc/en-us/articles/214836687-Role-Management-101).

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

**Note**: The bot is granted these permissions by default when it joins your server. You only need to take action if these permissions have been explicitly removed or overridden for a specific channel.

### Managing Multiple Channels

You can configure multiple announcement channels. This is useful when your server hosts different types of games and you want members to only see announcements relevant to them — for example, if your server runs both tabletop RPG sessions and board game nights, separate channels let members opt in to just the games they care about.

- Each game is posted to ONE channel, determined by the template
- Hosts select a template when creating a game, which determines the channel

## Step 4: Templates

Templates serve two purposes. First, they let bot managers lock in parameters that define a game type — such as the announcement channel, notification roles, and which Discord roles can host or join — which game hosts cannot change. Second, they let bot managers set convenient defaults for host-editable fields like max players, expected duration, location, and reminder times, saving hosts from filling in the same values every time.

Each template defines the announcement channel, the roles used for notifications, player eligibility, and host permissions, as well as default values for new games like max players and reminder times.

When the bot joins your guild, one template is created automatically. However, it needs to be customized before it is useful — at minimum, you must set the announcement channel and adjust any role assignments.

If your server hosts different types of games, create a separate template for each game type. This lets you set different channels, roles, and defaults per game type, and gives hosts a clear starting point when scheduling a game.

### Creating Templates

1. In the Web Dashboard, navigate to "Templates" under your guild
2. Click "Create Template"
3. Fill in the general fields:
   - **Name**: Template identifier (e.g., "D&D Session", "Board Game Night")
   - **Description**: What this template is for
4. Configure the locked settings (hosts cannot change these):
   - **Channel**: Where games using this template will be announced
   - **Archive Channel**: Channel where completed announcements are reposted when the game is archived (optional; leave empty to delete the original post without reposting)
   - **Archive Delay**: How long after completion to wait before archiving (days/hours/minutes; leave empty to archive immediately)
   - **Notify Roles**: Discord roles to ping when a game is created
   - **Allowed Player Roles**: Roles that can join games (empty = everyone)
   - **Allowed Host Roles**: Roles that can create games from this template (empty = all bot managers)
   - **Signup Priority Roles**: Ordered list of Discord roles that determines join priority when the game fills up (up to 8 roles, drag to reorder). Earlier positions take higher priority. Changing this list does not affect existing games — priority is captured per-participant at the moment they join.
5. Optionally, configure the pre-populated defaults (hosts can override these):
   - **Max Players**: Default participant limit
   - **Expected Duration**: How long games typically last
   - **Reminder Times**: When to send reminder notifications (minutes before start)
   - **Location**: Default location (e.g., "Discord Voice", "Local Game Store")
   - **Signup Instructions**: Instructions displayed to players
6. Click "Create"

### Template Management

- **Default Template**: Mark one template as default - it will be pre-selected when creating games
- **Template Order**: Drag templates to reorder how they appear in the creation form
- **Editing Templates**: Changes to templates do NOT affect existing games created from them
- **Deleting Templates**: Games created from deleted templates remain unaffected

## Step 5: Test the Bot

### Verify Bot Functionality

1. Create a test game using the web dashboard
2. Check that the game announcement appears in the designated channel
3. Try joining/leaving the game using Discord buttons
4. Verify that notifications are sent at the configured reminder time

### Common Issues

- **Bot can't see channels**: Verify "View Channels" permission is granted
- **Can't post announcements**: Verify "Send Messages" and "Embed Links" permissions in the target channel
- **Users can't create games**: Verify host roles are configured correctly on the relevant template

## Security Considerations

### Permission Model

- Bot uses Discord's role-based permission system
- Bot manager roles grant game management permissions
- Web dashboard requires Discord OAuth login - users must be guild members
- Bot cannot access channels it doesn't have permissions for

### Data Privacy

- Bot only stores game scheduling data (titles, descriptions, participants)
- User Discord IDs are stored for participant management
- The bot does not have the "Read Message History" or "Message Content Intent" permissions and cannot read messages it did not post
- Bot uses Discord API to verify permissions in real-time
- **Reminder**: The person or organization hosting the bot instance has access to all data stored by the bot. Do not enter any information you would not trust them to see.

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
