<!-- markdownlint-disable-file -->

# Release Changes: Game Image Upload Feature

**Related Plan**: 20251218-game-image-attachments-plan.instructions.md
**Implementation Date**: 2025-12-21

## Summary

Adding support for uploading and displaying thumbnail and banner images for game sessions in Discord embeds and the web frontend. Images are stored as binary data in PostgreSQL and served via dedicated API endpoints.

## Changes

### Added

- alembic/versions/3aeec3d09d7c_add_game_image_storage.py - Database migration adding four columns for storing thumbnail and banner images

### Modified

- shared/models/game.py - Added four image storage fields to GameSession model (thumbnail_data, thumbnail_mime_type, image_data, image_mime_type)
- tests/integration/test_database_infrastructure.py - Added test_game_sessions_image_storage_schema to verify new columns
- services/api/routes/games.py - Added \_validate_image_upload helper function for file validation (PNG/JPEG/GIF/WebP, <5MB)
- services/api/routes/games.py - Updated create_game endpoint to accept multipart/form-data with File() and Form() parameters
- services/api/routes/games.py - Updated update_game endpoint to accept multipart/form-data with file uploads and removal flags
- services/api/services/games.py - Updated GameService.create_game to accept and store image binary data and MIME types
- services/api/services/games.py - Updated GameService.update_game to handle image uploads, replacements, and removals
- tests/services/api/routes/test_games_image_validation.py - Added comprehensive unit tests for image validation (9 tests)
- tests/services/api/services/test_games_image_upload.py - Added comprehensive unit tests for service layer image handling (5 tests)
- services/api/routes/games.py - Added Response import from fastapi.responses for serving binary data
- services/api/routes/games.py - Added GET /games/{game_id}/thumbnail endpoint to serve thumbnail images with caching
- services/api/routes/games.py - Added GET /games/{game_id}/image endpoint to serve banner images with caching
- tests/services/api/routes/test_games_image_serving.py - Added comprehensive unit tests for image serving endpoints (8 tests)
- frontend/src/types/index.ts - Added has_thumbnail and has_image optional boolean fields to GameSession interface
- frontend/src/components/GameForm.tsx - Added thumbnailFile, imageFile, removeThumbnail, removeImage fields to GameFormData interface
- frontend/src/components/GameForm.tsx - Added handleThumbnailChange, handleImageChange, handleRemoveThumbnail, handleRemoveImage handlers with file validation
- frontend/src/components/GameForm.tsx - Added file input UI sections for thumbnail and banner with Material-UI Button components and validation
- frontend/src/pages/CreateGame.tsx - Updated handleSubmit to use FormData with multipart/form-data for image uploads
- frontend/src/pages/EditGame.tsx - Updated handleSubmit to use FormData with file uploads and removal flags

### Removed
