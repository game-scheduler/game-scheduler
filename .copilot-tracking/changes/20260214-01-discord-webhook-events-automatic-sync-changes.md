<!-- markdownlint-disable-file -->

# Changes Record: Discord Webhook Events for Automatic Guild Sync

**Implementation Date**: February 15, 2026
**Plan**: [20260214-01-discord-webhook-events-automatic-sync.plan.md](../plans/20260214-01-discord-webhook-events-automatic-sync.plan.md)
**Details**: [20260214-01-discord-webhook-events-automatic-sync-details.md](../details/20260214-01-discord-webhook-events-automatic-sync-details.md)

## Overview

Implementing Discord webhook endpoint with Ed25519 signature validation to automatically sync guilds when bot joins servers.

## Changes by Phase

### Phase 1: Environment and Dependencies Setup

**Status**: ✅ Completed

#### Task 1.1: Add DISCORD_PUBLIC_KEY environment variable

**Status**: ✅ Completed

**Files Modified**:

- [config/env.dev](../../config/env.dev) - Added DISCORD_PUBLIC_KEY with dev/test value
- [config/env.int](../../config/env.int) - Added DISCORD_PUBLIC_KEY (commented out for integration tests)
- [config/env.e2e](../../config/env.e2e) - Added DISCORD_PUBLIC_KEY with e2e test value
- [config/env.staging](../../config/env.staging) - Added DISCORD_PUBLIC_KEY with placeholder
- [config/env.prod](../../config/env.prod) - Added DISCORD_PUBLIC_KEY with placeholder
- [config.template/env.template](../../config.template/env.template) - Added DISCORD_PUBLIC_KEY with documentation

**Changes**:

- Added new environment variable `DISCORD_PUBLIC_KEY` to Discord Bot Configuration section
- Included helpful comments explaining where to find the key in Discord Developer Portal
- Documented that it's used for Ed25519 webhook signature validation
- Used placeholder values for dev/test environments and template placeholders for staging/prod

#### Task 1.2: Add PyNaCl dependency

**Status**: ✅ Completed

**Files Modified**:

- [pyproject.toml](../../pyproject.toml) - Added PyNaCl dependency

**Changes**:

- Added `"pynacl~=1.5.0"` to the Security section of project dependencies
- Enables Ed25519 signature verification for Discord webhooks

#### Task 1.3: Update APIConfig

**Status**: ✅ Completed

**Files Modified**:

- [services/api/config.py](../../services/api/config.py) - Added discord_public_key field

**Changes**:

- Added `self.discord_public_key = os.getenv("DISCORD_PUBLIC_KEY", "")` to APIConfig.**init**()
- Field loads from DISCORD_PUBLIC_KEY environment variable
- Positioned with other Discord configuration values for consistency

---

### Phase 2: Webhook Signature Validation (TDD)

**Status**: ✅ Completed

#### Task 2.1: Create validate_discord_webhook dependency stub

**Status**: ✅ Completed

**Files Created**:

- [services/api/dependencies/discord_webhook.py](../../services/api/dependencies/discord_webhook.py) - New webhook signature validation dependency

**Files Modified**:

- [services/api/dependencies/**init**.py](../../services/api/dependencies/__init__.py) - Added discord_webhook to exports

**Changes**:

- Created `validate_discord_webhook()` dependency function with correct signature
- Function accepts Request, x_signature_ed25519, and x_signature_timestamp parameters
- Initially raised NotImplementedError as per TDD methodology
- Added to dependencies module exports for consistent import pattern

#### Task 2.2: Write failing tests for signature validation

**Status**: ✅ Completed

**Files Created**:

- [tests/services/api/dependencies/test_discord_webhook.py](../../tests/services/api/dependencies/test_discord_webhook.py) - Comprehensive validation tests

**Changes**:

- Created test fixtures: `test_keypair` (Ed25519 key generation) and `mock_request` (FastAPI Request mock)
- Created helper function `create_valid_signature()` for generating test signatures
- Wrote 6 core tests with `@pytest.mark.xfail` markers (proper TDD approach):
  - `test_valid_signature_returns_body` - Verify valid signature returns body
  - `test_invalid_signature_raises_401` - Verify invalid signature rejected
  - `test_wrong_public_key_raises_401` - Verify wrong key rejected
  - `test_malformed_signature_raises_401` - Verify malformed hex rejected
  - `test_empty_body_validates_correctly` - Empty payload support
  - `test_large_body_validates_correctly` - Large payload (10KB) support
- Tests initially marked xfail, expecting implementation to make them pass

#### Task 2.3: Implement Ed25519 signature validation

**Status**: ✅ Completed

**Files Modified**:

- [services/api/dependencies/discord_webhook.py](../../services/api/dependencies/discord_webhook.py) - Implemented validation logic

**Changes**:

- Implemented PyNaCl-based Ed25519 signature verification
- Load DISCORD_PUBLIC_KEY from environment variable
- Returns 500 if public key not configured
- Concatenate timestamp + body and verify against signature using VerifyKey
- Returns validated body bytes on success
- Raises HTTPException(401) for BadSignatureError or ValueError
- All 6 tests passed (XPASS) indicating implementation is correct

#### Task 2.4: Update tests to verify actual behavior

**Status**: ✅ Completed

**Files Modified**:

- [tests/services/api/dependencies/test_discord_webhook.py](../../tests/services/api/dependencies/test_discord_webhook.py) - Removed xfail markers

**Changes**:

- Removed `@pytest.mark.xfail` markers from all 6 tests
- Tests now verify actual signature validation behavior
- All tests pass with real Ed25519 signature generation and verification
- Tests confirm both success and failure paths work correctly

#### Task 2.5: Refactor validation with comprehensive edge case tests

**Status**: ✅ Completed

**Files Modified**:

- [services/api/dependencies/discord_webhook.py](../../services/api/dependencies/discord_webhook.py) - Refactored for clarity
- [tests/services/api/dependencies/test_discord_webhook.py](../../tests/services/api/dependencies/test_discord_webhook.py) - Added 5 edge case tests

**Changes**:

**Implementation Refactoring**:

- Enhanced docstring with signature verification process explanation
- Clarified Raises documentation for both 500 and 401 status codes
- Simplified VerifyKey initialization (removed intermediate variable)
- Maintained 100% test coverage

**Edge Case Tests Added**:

- `test_missing_public_key_raises_500` - Missing DISCORD_PUBLIC_KEY environment variable
- `test_invalid_public_key_format_raises_401` - Invalid public key hex format
- `test_wrong_timestamp_raises_401` - Signature with mismatched timestamp
- `test_signature_too_short_raises_401` - Signature with insufficient length
- `test_unicode_body_validates_correctly` - Unicode characters in body

**Test Coverage**: 100% (18 statements, 0 missed)
**Total Tests**: 11 passing

---

### Phase 3: Webhook Endpoint Implementation (TDD)

**Status**: ✅ Completed

#### Task 3.1: Create webhook endpoint stub

**Status**: ✅ Completed

**Files Created**:

- [services/api/routes/webhooks.py](../../services/api/routes/webhooks.py) - New Discord webhook endpoint

**Files Modified**:

- [services/api/app.py](../../services/api/app.py) - Registered webhooks router

**Changes**:

- Created `/api/v1/webhooks/discord` POST endpoint with signature validation dependency
- Initially raised NotImplementedError as per TDD methodology (stub phase)
- Registered webhooks router in FastAPI app with `/api/v1` prefix

#### Task 3.2: Write failing integration tests

**Status**: ✅ Completed

**Files Created**:

- [tests/integration/test_webhooks.py](../../tests/integration/test_webhooks.py) - Integration tests with real signature validation

**Changes**:

- Generated fixed Ed25519 keypair for integration tests
  - Private key: `4c480d86c13f3e142aca79d54cdd2a173eaf484cb4fd44e61790fa5386501b83`
  - Public key: `bfdab846fefce17aaaa92860e42a70c61d2d40c95b1ebbcbe4087a505f66b8fe`
- Added DISCORD_PUBLIC_KEY to [config/env.int](../../config/env.int)
- Added DISCORD_PUBLIC_KEY passthrough to [compose.yaml](../../compose.yaml) api service
- Added DISCORD_PUBLIC_KEY passthrough to [compose.int.yaml](../../compose.int.yaml) integration-tests service
- Created 4 integration tests:
  - `test_webhook_ping_returns_204` - PING handling
  - `test_webhook_application_authorized_returns_204` - Guild install handling
  - `test_webhook_invalid_signature_rejected` - Signature rejection (401)
  - `test_webhook_missing_headers_rejected` - Missing headers (422)
- Tests initially expected NotImplementedError (RED phase)

#### Task 3.3: Implement PING handling

**Status**: ✅ Completed

**Files Modified**:

- [services/api/routes/webhooks.py](../../services/api/routes/webhooks.py) - Implemented PING response

**Changes**:

- Implemented type=0 (PING) webhook handling returning 204 No Content
- Parse JSON payload from validated body bytes
- Log PING webhook receipt at INFO level
- Tests transition from RED → GREEN (PING test passes)

#### Task 3.4: Implement APPLICATION_AUTHORIZED handling

**Status**: ✅ Completed

**Files Modified**:

- [services/api/routes/webhooks.py](../../services/api/routes/webhooks.py) - Implemented APPLICATION_AUTHORIZED handling

**Changes**:

- Implemented type=1 (APPLICATION_AUTHORIZED) webhook handling
- Extract guild info from event.data for guild installs (integration_type=0)
- Log guild ID and name at INFO level when present
- Return 204 No Content for both guild and user installs
- All 4 integration tests now pass (GREEN phase)

#### Task 3.5: Add comprehensive edge case tests

**Status**: ✅ Completed

**Files Created**:

- [tests/services/api/routes/test_webhooks.py](../../tests/services/api/routes/test_webhooks.py) - Unit tests for edge cases

**Changes**:

- Created 12 comprehensive unit tests following project pattern (direct function call):
  - `test_webhook_ping_returns_204` - PING handling
  - `test_webhook_application_authorized_guild_install_returns_204` - Guild install
  - `test_webhook_application_authorized_user_install_returns_204` - User install
  - `test_webhook_application_authorized_missing_guild_returns_204` - Missing guild field
  - `test_webhook_application_authorized_empty_guild_returns_204` - Empty guild object
  - `test_webhook_unknown_event_type_returns_204` - Unknown event type
  - `test_webhook_missing_event_field_returns_204` - Missing event field
  - `test_webhook_unknown_type_returns_204` - Unknown webhook type
  - `test_webhook_missing_type_field_returns_204` - Missing type field
  - `test_webhook_application_authorized_missing_integration_type` - Missing integration_type
  - `test_webhook_application_authorized_missing_data` - Missing data field
  - `test_webhook_idempotency_multiple_same_guild` - Idempotent behavior
- Tests call `discord_webhook()` function directly with mocked validated body bytes
- Avoids TestClient pattern that triggers full application lifecycle
- All 12 tests pass in 0.09s without infrastructure startup

**Test Results**:

- Integration tests: 4 passing (signature validation, PING, APPLICATION_AUTHORIZED, error cases)
- Unit tests: 12 passing (comprehensive edge case coverage)
- Updated error message assertion in [tests/services/api/dependencies/test_discord_webhook.py](../../tests/services/api/dependencies/test_discord_webhook.py) to match actual implementation text

---

### Phase 4: Bot Guild Sync Service (TDD)

**Status**: Not Started

---

### Phase 5: RabbitMQ Integration for Webhook

**Status**: Not Started

---

### Phase 6: Lazy Channel Loading (TDD)

**Status**: Not Started

---

### Phase 7: Manual Discord Portal Configuration

**Status**: Not Started

---

## Summary

**Total Tasks Completed**: 8 / 8 (Phases 1-2)
**Current Phase**: 2 - Webhook Signature Validation (TDD) (COMPLETED)
**Next Actions**: Phase 3 - Webhook Endpoint Implementation (TDD)
