---
applyTo: ".copilot-tracking/changes/20251218-game-image-attachments-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Game Image Upload Feature

## Overview

Add support for uploading and displaying thumbnail and banner images for game sessions in Discord embeds and the web frontend.

## Objectives

- Store game images as binary data in PostgreSQL database
- Accept multipart/form-data file uploads via API with validation
- Serve images via dedicated GET endpoints
- Display images in Discord embeds (thumbnail and banner)
- Enable image upload/removal in frontend forms

## Research Summary

### Project Files

- services/bot/formatters/game_message.py - Discord embed creation, currently no image support
- shared/schemas/game.py - API request/response schemas, no image fields
- shared/models/game.py - GameSession model, no image storage
- frontend/src/components/GameForm.tsx - Form component, no file upload fields
- services/api/routes/games.py - API endpoints using JSON payloads only

### External References

- #file:../research/20251218-game-image-attachments-research.md - Comprehensive research on Discord embed images, FastAPI file uploads, and database storage patterns
- Discord API Documentation - embed.set_thumbnail() and embed.set_image() methods for displaying images
- FastAPI Documentation - UploadFile and multipart/form-data handling

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/reactjs.instructions.md - React/TypeScript conventions
- #file:../../.github/instructions/coding-best-practices.instructions.md - General best practices

## Implementation Checklist

### [x] Phase 1: Database Schema Migration

- [x] Task 1.1: Create Alembic migration for image storage columns
  - Details: .copilot-tracking/details/20251218-game-image-attachments-details.md (Lines 13-40)

- [x] Task 1.2: Update GameSession model with image fields
  - Details: .copilot-tracking/details/20251218-game-image-attachments-details.md (Lines 42-58)

### [x] Phase 2: API File Upload Endpoints

- [x] Task 2.1: Update create_game endpoint for multipart/form-data
  - Details: .copilot-tracking/details/20251218-game-image-attachments-details.md (Lines 13-40)

- [x] Task 2.2: Update update_game endpoint for file uploads
  - Details: .copilot-tracking/details/20251218-game-image-attachments-details.md (Lines 42-58)

- [x] Task 2.3: Add file validation helper function
  - Details: .copilot-tracking/details/20251218-game-image-attachments-details.md (Lines 135-161)

### [x] Phase 3: Image Serving Endpoints

- [x] Task 3.1: Add GET /games/{game_id}/thumbnail endpoint
  - Details: .copilot-tracking/details/20251218-game-image-attachments-details.md (Lines 163-191)

- [x] Task 3.2: Add GET /games/{game_id}/image endpoint
  - Details: .copilot-tracking/details/20251218-game-image-attachments-details.md (Lines 193-220)

### [x] Phase 4: Frontend File Upload UI

- [x] Task 4.1: Update TypeScript interfaces for images
  - Details: .copilot-tracking/details/20251218-game-image-attachments-details.md (Lines 287-312)

- [x] Task 4.2: Add file input components to GameForm
  - Details: .copilot-tracking/details/20251218-game-image-attachments-details.md (Lines 314-379)

- [x] Task 4.3: Update form submission to use FormData
  - Details: .copilot-tracking/details/20251218-game-image-attachments-details.md (Lines 381-423)

### [x] Phase 5: Frontend Image Display

- [x] Task 5.1: Add image display to GameDetails page
  - Details: .copilot-tracking/details/20251218-game-image-attachments-details.md (Lines 425-468)

### [x] Phase 6: Discord Bot Integration

- [x] Task 6.1: Update game message formatter to accept image flags
  - Details: .copilot-tracking/details/20251218-game-image-attachments-details.md (Lines 222-261)

- [x] Task 6.2: Update bot event handlers to pass image flags
  - Details: .copilot-tracking/details/20251218-game-image-attachments-details.md (Lines 263-285)

### [x] Phase 7: Environment and Schema Updates

- [x] Task 7.1: Add API_BASE_URL environment variable
  - Details: .copilot-tracking/details/20251218-game-image-attachments-details.md (Lines 470-491)

- [x] Task 7.2: Update GameResponse schema with image flags
  - Details: .copilot-tracking/details/20251218-game-image-attachments-details.md (Lines 493-518)

### [x] Phase 8: Testing

- [x] Task 8.1: Add unit tests for model and validation
  - Details: .copilot-tracking/details/20251218-game-image-attachments-details.md (Lines 520-582)

- [x] Task 8.2: Add integration tests for upload flow
  - Details: .copilot-tracking/details/20251218-game-image-attachments-details.md (Lines 584-624)

## Dependencies

- PostgreSQL with BYTEA support (already present)
- FastAPI UploadFile and File (already available)
- Discord.py with Embed support (already present)
- SQLAlchemy LargeBinary column type (already present)
- Material-UI Button component (already present)

## Success Criteria

- Database stores image binary data in BYTEA columns with MIME types
- API accepts and validates file uploads (PNG/JPEG/GIF/WebP, <5MB)
- API serves images via GET endpoints with correct Content-Type headers
- Discord embeds display thumbnail (upper right) and banner (bottom) when uploaded
- Frontend forms support uploading, replacing, and removing images
- Frontend displays images on game detail page
- Both images are optional and nullable
- All new code has unit and integration tests
