<!-- markdownlint-disable-file -->

# Phase 4 Task 4.2: Calendar Compatibility Testing

**Test Date**: _____________
**Tester**: _____________
**Environment**: [ ] Development [ ] Staging [ ] Production

## Prerequisites

- [ ] Successfully downloaded calendar file from Task 4.1
- [ ] Access to Google Calendar (web or app)
- [ ] Access to Microsoft Outlook (desktop, web, or mobile)
- [ ] Access to Apple Calendar (macOS or iOS)
- [ ] Test game with known details for verification

## Test Game Details

Record details of test game for verification:

- **Game Title**: _____________
- **Scheduled Date/Time**: _____________
- **Host**: _____________
- **Description**: _____________
- **Location**: _____________
- **Duration**: _____________
- **Max Players**: _____________
- **Participants**: _____________

---

## Calendar Import Tests

### Test 1: Google Calendar (Web)

**Steps**:
1. Open Google Calendar (calendar.google.com)
2. Click Settings (gear icon) → Import & Export
3. Click "Select file from your computer"
4. Choose downloaded `.ics` file
5. Select target calendar
6. Click Import
7. Navigate to the game's scheduled date
8. Open the imported event

**Expected Results**:
- [ ] Import succeeds with no errors
- [ ] Event appears on correct date/time
- [ ] Event title matches game title
- [ ] Description contains game information
- [ ] Location field populated (if specified)
- [ ] Duration is correct
- [ ] Reminders/notifications are set
- [ ] Timezone handled correctly (displays in local time)
- [ ] Event is editable after import

**Actual Results**:
```
[Record what actually happened]
```

**Screenshots**: [ ] Attached

---

### Test 2: Google Calendar (Mobile App)

**Device**: _____________
**OS Version**: _____________

**Steps**:
1. Download `.ics` file to mobile device
2. Open file with Google Calendar app
3. Tap "Add to Calendar"
4. Review event details
5. Save event

**Expected Results**:
- [ ] App recognizes `.ics` file format
- [ ] Import prompt appears
- [ ] Event details display correctly in preview
- [ ] Event saves successfully
- [ ] Notifications are configured

**Actual Results**:
```
[Record what actually happened]
```

**Screenshots**: [ ] Attached

---

### Test 3: Microsoft Outlook (Desktop)

**Outlook Version**: _____________
**OS**: _____________

**Steps**:
1. Open Outlook desktop application
2. File → Open & Export → Import/Export
3. Select "Import an iCalendar (.ics) or vCalendar file (.vcs)"
4. Click Next
5. Browse to downloaded `.ics` file
6. Click Open
7. Review import options
8. Click OK to import
9. Navigate to event in calendar

**Expected Results**:
- [ ] Outlook recognizes `.ics` format
- [ ] No import warnings or errors
- [ ] Event appears in calendar
- [ ] All event details preserved
- [ ] Reminders configured correctly
- [ ] Timezone conversion accurate

**Actual Results**:
```
[Record what actually happened]
```

**Screenshots**: [ ] Attached

---

### Test 4: Microsoft Outlook (Web)

**Steps**:
1. Open Outlook.com or Office 365 Calendar
2. Click "Add calendar" → "Upload from file"
3. Choose downloaded `.ics` file
4. Click "Import"
5. Navigate to event date
6. Open imported event

**Expected Results**:
- [ ] Upload succeeds
- [ ] Event appears in web calendar
- [ ] All details correctly displayed
- [ ] Can edit event after import
- [ ] Syncs to other Outlook clients

**Actual Results**:
```
[Record what actually happened]
```

**Screenshots**: [ ] Attached

---

### Test 5: Apple Calendar (macOS)

**macOS Version**: _____________

**Steps**:
1. Download `.ics` file to Mac
2. Double-click the `.ics` file
3. Apple Calendar should open automatically
4. Review import dialog
5. Select target calendar
6. Click "OK" or "Add"
7. Navigate to event in Calendar app
8. Open event details

**Expected Results**:
- [ ] Calendar app launches automatically
- [ ] Import dialog shows event preview
- [ ] Event imports successfully
- [ ] Event details accurate
- [ ] Alerts/notifications configured
- [ ] Timezone correct for local timezone
- [ ] Location appears in event (if applicable)

**Actual Results**:
```
[Record what actually happened]
```

**Screenshots**: [ ] Attached

---

### Test 6: Apple Calendar (iOS)

**Device**: _____________
**iOS Version**: _____________

**Steps**:
1. Email `.ics` file to test device or download from cloud
2. Tap the `.ics` file attachment
3. Tap "Add to Calendar"
4. Review event details
5. Tap "Add" to confirm
6. Open Calendar app
7. Navigate to event
8. Verify details

**Expected Results**:
- [ ] iOS recognizes `.ics` format
- [ ] Event preview displays correctly
- [ ] Import to Calendar app succeeds
- [ ] Event details preserved
- [ ] Notifications work on device
- [ ] Event syncs with iCloud (if enabled)

**Actual Results**:
```
[Record what actually happened]
```

**Screenshots**: [ ] Attached

---

## Filename Validation Tests

### Test 7: Filename Readability

**Steps**:
1. Download calendars for games with various titles:
   - Simple title: "Poker Night"
   - Special characters: "D&D Campaign!"
   - Long title: "Weekly Tabletop Gaming Session with Friends"
   - Unicode characters (if applicable)
2. Check downloaded filenames

**Expected Results**:
- [ ] Filenames are human-readable
- [ ] Special characters converted to hyphens
- [ ] Date format is `YYYY-MM-DD`
- [ ] Pattern: `{Game-Title}_{YYYY-MM-DD}.ics`
- [ ] No invalid filesystem characters
- [ ] Filenames not truncated unnecessarily

**Example Expected Filenames**:
- "Poker Night" on 2025-12-25 → `Poker-Night_2025-12-25.ics`
- "D&D Campaign!" on 2025-11-15 → `D-D-Campaign_2025-11-15.ics`

**Actual Filenames**:
```
[Record actual filenames generated]
```

---

## Data Integrity Tests

### Test 8: Event Details Verification

For one imported event in each calendar application, verify:

**Google Calendar**:
- [ ] Title: _____________
- [ ] Date/Time: _____________
- [ ] Description: _____________
- [ ] Location: _____________
- [ ] Duration: _____________

**Outlook**:
- [ ] Title: _____________
- [ ] Date/Time: _____________
- [ ] Description: _____________
- [ ] Location: _____________
- [ ] Duration: _____________

**Apple Calendar**:
- [ ] Title: _____________
- [ ] Date/Time: _____________
- [ ] Description: _____________
- [ ] Location: _____________
- [ ] Duration: _____________

**Verification**: All fields match original game details? [ ] Yes [ ] No

---

### Test 9: Timezone Handling

**Test Setup**:
- Game scheduled for: _____________ UTC
- Tester's timezone: _____________
- Expected local time: _____________

**Verification**:
- [ ] Google Calendar shows correct local time
- [ ] Outlook shows correct local time
- [ ] Apple Calendar shows correct local time
- [ ] No timezone offset errors
- [ ] Event time adjusts for daylight saving (if applicable)

**Notes**:
```
[Any timezone-related observations]
```

---

### Test 10: Reminders/Notifications

**Expected Reminders** (from game settings):
- Reminder 1: _____________
- Reminder 2: _____________

**Google Calendar**:
- [ ] Reminders imported correctly
- [ ] Notification delivery works

**Outlook**:
- [ ] Reminders imported correctly
- [ ] Notification delivery works

**Apple Calendar**:
- [ ] Alerts imported correctly
- [ ] Notification delivery works

**Notes**:
```
[Any reminder/notification observations]
```

---

## Cross-Platform Compatibility Tests

### Test 11: RFC 5545 Compliance

**Steps**:
1. Open downloaded `.ics` file in text editor
2. Review iCal structure
3. Verify required components present

**Expected Structure**:
- [ ] Starts with `BEGIN:VCALENDAR`
- [ ] Contains `VERSION:2.0`
- [ ] Contains `PRODID` field
- [ ] Contains `BEGIN:VEVENT ... END:VEVENT`
- [ ] Contains `UID` (unique identifier)
- [ ] Contains `DTSTART` and `DTEND`
- [ ] Contains `SUMMARY` (title)
- [ ] Contains `DESCRIPTION`
- [ ] Ends with `END:VCALENDAR`
- [ ] Proper line folding (max 75 octets)
- [ ] No invalid characters or formatting

**Actual Structure**:
```
[Paste first 30 lines of .ics file]
```

---

### Test 12: Import/Re-export Cycle

**Steps**:
1. Import `.ics` file into Google Calendar
2. Export event from Google Calendar as `.ics`
3. Import exported file into Outlook
4. Export from Outlook
5. Import into Apple Calendar
6. Compare final event with original

**Expected Results**:
- [ ] Event survives import/export cycle
- [ ] Core data preserved (title, date, time, description)
- [ ] No data corruption
- [ ] No formatting issues

**Actual Results**:
```
[Record any data loss or corruption]
```

---

## Test Summary

**Total Tests**: 12
**Passed**: ___
**Failed**: ___
**Blocked**: ___

### Calendar Application Support

| Application | Version | Import Success | Data Integrity | Issues |
|-------------|---------|----------------|----------------|--------|
| Google Calendar (Web) | | [ ] | [ ] | |
| Google Calendar (Mobile) | | [ ] | [ ] | |
| Outlook (Desktop) | | [ ] | [ ] | |
| Outlook (Web) | | [ ] | [ ] | |
| Apple Calendar (macOS) | | [ ] | [ ] | |
| Apple Calendar (iOS) | | [ ] | [ ] | |

### Issues Found
```
[List any compatibility issues, data loss, formatting problems, or bugs]
```

### Recommendations
```
[Suggestions for improving calendar export or compatibility]
```

---

## Sign-off

**Tester Signature**: _____________
**Date**: _____________
**Status**: [ ] PASSED [ ] FAILED [ ] NEEDS REVIEW

---

## Additional Notes

```
[Any additional observations, edge cases discovered, or recommendations]
```
