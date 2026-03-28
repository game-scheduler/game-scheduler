# Player Guide

This guide is for Discord guild members who want to join game sessions and receive notifications.

## How to Find Game Announcements

Game announcements appear in Discord channels configured by your guild administrator. These are typically dedicated gaming channels like #board-games or #rpg-sessions.

### Game Announcement Format

Game announcements include:

- **Game Title**: The name of the session (e.g., "D&D Campaign Session", "Board Game Night")
- **Scheduled Time**: When the game starts (displayed in your local timezone)
- **Participant Count**: Current signups vs maximum (e.g., "3/5" means 3 signed up, 5 maximum)
- **Channel**: Where the game takes place (voice channel, physical location, etc.)
- **Description**: Additional details about the game
- **Participant List**: Discord mentions of players who have joined
- **Join/Leave Buttons**: Interactive buttons to signup or withdraw

Example message:

```
🎮 D&D Campaign Session

📅 When: Saturday, December 7, 2024 7:00 PM (in 2 days)
👥 Players: 3/5
📍 Channel: #voice-channel-1
📝 Description: Continuing the quest into the Shadowfell

Participants:
@Player1
@Player2
@Player3

[Join Game] [Leave Game]
```

## Joining a Game

### Using Discord Buttons (Default Method)

Most games use "Self Signup" which allows you to join directly from Discord:

1. **Click the "Join Game" button** in the game announcement
2. The bot will process your request (this takes a few seconds)
3. You'll see a confirmation message: "✅ You've joined [Game Title]!"
4. Your Discord mention is added to the participant list in the announcement
5. **One minute after joining**, you'll receive a Direct Message (DM) with:
   - Confirmation that you've joined
   - Any signup instructions from the host (e.g., "Bring your character sheet", "Install this software")
   - When the game starts

**Note**: If the game is full (max players reached), you'll be added to the waitlist automatically.

### Host-Selected Games

Some games use "Host Selected" signup method:

- The "Join Game" button is **disabled** (grayed out)
- Only the host can add participants
- You cannot join these games yourself - contact the host directly if interested

### Using the Web Dashboard (Alternative)

You can also join games through the web dashboard:

1. Navigate to the Game Scheduler web dashboard
2. Log in with your Discord account
3. Browse available games in your guild
4. Click on a game to view details
5. Click "Join Game" button
6. You'll receive the same confirmation DM one minute after joining

## Leaving a Game

### Using Discord Buttons

1. **Click the "Leave Game" button** in the game announcement
2. You'll see a confirmation message
3. Your mention is removed from the participant list

### From the Web Dashboard

1. Navigate to the game details page
2. Click "Leave Game" button
3. Confirm your decision

**Important**: You cannot leave a game after it has started (status changes to "IN_PROGRESS" or "COMPLETED"). If you need to cancel after that point, contact the host directly.

## Understanding the Waitlist

When a game reaches its maximum player capacity, additional players are automatically added to a waitlist.

### How the Waitlist Works

- **Full Game**: When max players is reached (e.g., 5/5 players)
- **Join After Full**: Your join request succeeds, but you're marked as waitlisted
- **Waitlist Position**: Determined by the order you joined
- **Automatic Promotion**: If a confirmed player leaves, the first person on the waitlist is automatically promoted
- **Promotion Notification**: You receive a DM when you're promoted from waitlist to confirmed participant

### Role-Based Priority

Some games use **Role Based** signup, where your Discord roles determine your position in the participant list. When you click Join, the bot checks your roles against the template's priority list and places you ahead of players without a matching role.

Important: priority is captured **at the moment you join**. If your Discord roles change after you've signed up, your position in the list does not change. To get a new priority position after a role change, you would need to leave the game and rejoin.

### Checking Your Status

- **Game Details Page**: Shows whether you're confirmed or waitlisted
- **Discord Announcement**: Waitlisted players appear after confirmed players in the participant list
- **Web Dashboard**: Your games page shows your participant status

### Waitlist Behavior

- You can leave the waitlist at any time by clicking "Leave Game"
- Leaving while on the waitlist does not affect confirmed players
- Promotion is automatic - no action required from you
- Host can manually adjust the participant order if needed

## Notifications You'll Receive

The bot sends Direct Messages (DMs) for important game events:

### Join Confirmation (1 Minute Delay)

After joining a game, you'll receive a DM **one minute later** with:

- Confirmation message: "✅ You've joined [Game Title]"
- Signup instructions (if the host provided any)
- When the game starts (e.g., "Game starts in 2 days")

**Why the delay?** This prevents spam if you accidentally join and immediately leave, and gives the host time to update signup instructions.

### Reminder Notification

Before the game starts, you'll receive a reminder DM:

- Sent at the reminder time configured by the host (typically 24 hours before)
- Includes game title, time, location, and participant list
- Helps you remember upcoming games

### Waitlist Promotion

If you're promoted from the waitlist to a confirmed participant:

- You receive a DM immediately
- Message explains that a spot opened up
- You're now guaranteed a spot in the game

### Game Cancellation

If the host cancels a game:

- All participants receive a DM immediately
- Message explains the game was canceled
- Game status changes to "CANCELLED" in Discord

### Game Updates

If the host makes significant changes to a game (time, location, etc.):

- Participants may receive an update notification
- Major changes (time/date) always trigger notifications
- Minor description updates may not trigger notifications

## Calendar Download Feature

You can download game sessions to your personal calendar (Google Calendar, Outlook, Apple Calendar, etc.).

### Downloading Your Games

1. Navigate to the web dashboard
2. Go to "My Games" or "Browse Games"
3. Find the game you want to add to your calendar
4. Click the "Download Calendar" button (📅 icon)
5. Your browser will download an `.ics` file
6. Open the file with your calendar application
7. The event is added to your calendar with all game details

### Calendar Event Details

The calendar event includes:

- **Title**: Game session name
- **Date/Time**: Scheduled start time (in your timezone)
- **Duration**: Expected game length
- **Location**: Where the game takes place
- **Description**: Game details and participant list
- **Reminders**: Set based on the game's reminder configuration

### Supported Calendar Apps

The `.ics` format works with:

- Google Calendar
- Microsoft Outlook
- Apple Calendar (macOS, iOS)
- Mozilla Thunderbird
- Any calendar app supporting iCalendar format

## Common Questions

### Why didn't I receive a DM?

Check the following:

1. **Discord Privacy Settings**: Ensure you allow DMs from server members
   - Go to Privacy & Safety → Direct Messages → "Allow direct messages from server members"
2. **Blocked Bot**: Verify you haven't blocked the Game Scheduler bot
3. **DM Delay**: Join confirmation DMs are sent 1 minute after joining (not immediate)
4. **Waitlist Status**: Waitlisted players don't receive join confirmation until promoted

### Can I join multiple games at the same time?

Yes! You can join as many games as you want. There's no limit on concurrent games.

### What if the game time changes?

If the host changes the game time:

- You'll receive an update notification in your DMs
- The Discord announcement is updated automatically
- Your calendar event does NOT update automatically - download a new .ics file if needed

### Can I suggest changes to a game?

Contact the game host directly via Discord DM. Only hosts can edit games through the dashboard.

### What happens if I forget to leave a game?

If you don't show up:

- The host may manually remove you from the participant list
- This could affect your ability to join future games (at the host's discretion)
- Best practice: Leave games as soon as you know you can't attend

### Why is the "Join Game" button disabled?

The join button is disabled when:

- **Game has started**: Status is "IN_PROGRESS" or "COMPLETED"
- **Game is canceled**: Status is "CANCELLED"
- **Host-Selected signup method**: Only the host can add players

Note: Role Based games use the same button as Self Signup — clicking it still works, your position in the list just depends on your Discord roles at that moment.

Note: If the game is full but not started, you can still join and you'll be waitlisted automatically.

### Can I see all games in my guild?

Yes! Use the web dashboard:

1. Log in with your Discord account
2. Select your guild
3. Click "Browse Games"
4. Filter by channel, status, or date
5. View all available games and their details

## Next Steps

- **For Game Hosts**: See [Host Guide](HOST-GUIDE.md) for creating and managing games
- **For Guild Admins**: See [Guild Admin Guide](GUILD-ADMIN.md) for bot configuration
- **For Developers**: See [Developer Documentation](developer/README.md) for contributing

## Getting Help

If you encounter issues:

1. Check your Discord privacy settings for DM permissions
2. Verify you're a member of the guild where the game is hosted
3. Ensure the game hasn't already started or been canceled
4. Contact the game host for game-specific questions
5. Ask your guild administrator for bot configuration issues
6. Check the project's GitHub repository for known issues
