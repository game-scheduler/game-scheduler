<!-- markdownlint-disable-file -->

# Phase 4 Task 4.1: Authentication and Redirect Flow Testing

**Test Date**: _____________
**Tester**: _____________
**Environment**: [ ] Development [ ] Staging [ ] Production

## Prerequisites

- [ ] Frontend running and accessible
- [ ] API service running
- [ ] Bot service running
- [ ] Discord bot configured with valid OAuth2 credentials
- [ ] Test Discord server with game announcement posted
- [ ] Test user account (not already authenticated)

## Test Scenarios

### Scenario 1: Unauthenticated User - First Visit

**Steps**:
1. Open private/incognito browser window (ensure no existing session)
2. Navigate to Discord and find a game announcement with clickable title
3. Click the game card title link
4. Observe redirect behavior

**Expected Results**:
- [ ] Browser opens to `/download-calendar/{game_id}` URL
- [ ] Page shows "Authenticating..." loading state
- [ ] User is automatically redirected to `/login` page
- [ ] Login page displays Discord OAuth button

**Actual Results**:
```
[Record what actually happened]
```

---

### Scenario 2: OAuth Authentication Flow

**Steps** (continuing from Scenario 1):
1. On login page, click "Login with Discord" button
2. Discord OAuth consent screen appears
3. Authorize the application
4. Observe post-authorization redirect

**Expected Results**:
- [ ] Discord OAuth consent screen displays
- [ ] After authorization, redirected back to frontend `/auth/callback`
- [ ] Callback page processes OAuth code
- [ ] User is redirected back to `/download-calendar/{game_id}`
- [ ] Calendar download begins automatically

**Actual Results**:
```
[Record what actually happened]
```

---

### Scenario 3: Already Authenticated User

**Steps**:
1. With authenticated session (from Scenario 2), keep browser window open
2. Return to Discord and click another game card title
3. Observe download behavior

**Expected Results**:
- [ ] Browser opens to `/download-calendar/{game_id}` URL
- [ ] Page shows "Downloading calendar..." loading state
- [ ] Calendar file downloads immediately (no login redirect)
- [ ] Descriptive filename: `{Game-Title}_{YYYY-MM-DD}.ics`
- [ ] User is redirected to `/my-games` after 1 second

**Actual Results**:
```
[Record what actually happened]
```

---

### Scenario 4: Permission Denied (403 Error)

**Steps**:
1. Create a private game session (only specific users can access)
2. Log in as user who is NOT host, participant, admin, or bot manager
3. Click game card title in Discord
4. Observe error handling

**Expected Results**:
- [ ] Browser opens to `/download-calendar/{game_id}` URL
- [ ] Error message displays: "You do not have permission to download this calendar."
- [ ] Error is displayed in red Alert component
- [ ] Alert has close button (X)
- [ ] Clicking close button navigates to `/my-games`

**Actual Results**:
```
[Record what actually happened]
```

---

### Scenario 5: Game Not Found (404 Error)

**Steps**:
1. Manually construct URL with invalid game ID: `/download-calendar/invalid-game-id-12345`
2. Navigate to this URL while authenticated
3. Observe error handling

**Expected Results**:
- [ ] Error message displays: "Game not found."
- [ ] Error is displayed in red Alert component
- [ ] Alert has close button (X)
- [ ] Clicking close button navigates to `/my-games`

**Actual Results**:
```
[Record what actually happened]
```

---

### Scenario 6: Network Error Handling

**Steps**:
1. Open browser developer tools → Network tab
2. Enable network throttling or offline mode
3. Click game card title in Discord
4. Observe error handling

**Expected Results**:
- [ ] Error message displays: "An error occurred while downloading the calendar."
- [ ] Error is displayed in red Alert component
- [ ] Error is logged to browser console
- [ ] Alert has close button (X)
- [ ] Clicking close button navigates to `/my-games`

**Actual Results**:
```
[Record what actually happened]
```

---

### Scenario 7: Loading States

**Steps**:
1. Open browser developer tools → Network tab
2. Enable slow 3G or similar throttling
3. Click game card title in Discord (unauthenticated)
4. Observe loading indicators

**Expected Results**:
- [ ] Initial load shows "Authenticating..." with spinner
- [ ] After login/redirect shows "Downloading calendar..." with spinner
- [ ] Loading states are centered on page
- [ ] Loading text is clear and informative

**Actual Results**:
```
[Record what actually happened]
```

---

### Scenario 8: Session Expiration

**Steps**:
1. Log in and verify authentication works
2. Manually delete session cookie from browser (DevTools → Application → Cookies)
3. Click game card title in Discord
4. Observe redirect to login

**Expected Results**:
- [ ] Expired session is detected
- [ ] User is redirected to `/login` page
- [ ] After re-authentication, returns to download page
- [ ] Calendar downloads successfully

**Actual Results**:
```
[Record what actually happened]
```

---

## Test Summary

**Total Scenarios**: 8
**Passed**: ___
**Failed**: ___
**Blocked**: ___

### Issues Found
```
[List any bugs, unexpected behavior, or areas for improvement]
```

### Recommendations
```
[Any suggestions for improvements]
```

---

## Sign-off

**Tester Signature**: _____________
**Date**: _____________
**Status**: [ ] PASSED [ ] FAILED [ ] NEEDS REVIEW
