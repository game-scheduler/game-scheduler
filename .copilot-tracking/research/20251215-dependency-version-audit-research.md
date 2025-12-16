<!-- markdownlint-disable-file -->
# Task Research Notes: Dependency Version Audit and Upgrade Strategy

## Research Executed

### Infrastructure Service Version Analysis

**PostgreSQL 17-alpine vs 18-alpine**:
- Current: postgres:17-alpine
- Latest Stable: postgres:18.1 (December 2024 release)
- PostgreSQL 17: Maintained until November 2029
- PostgreSQL 18: New features include SQL/JSON improvements, performance enhancements
- Breaking changes: Minimal for standard usage
- Migration complexity: Low (follows standard upgrade path)

**RabbitMQ 4.2**:
- Current: rabbitmq:4.2-management-alpine
- Latest: 4.2.1-management-alpine (patch release)
- Status: On current major version (4.x released mid-2024)
- No action needed

**Redis 7.4-alpine vs 8.4-alpine**:
- Current: redis:7.4-alpine
- Latest: redis:8.4.0-alpine (October 2024 release)
- Redis 8 changes: New license (RSALv2/SSPLv1/AGPLv3), significant performance improvements
- Breaking changes: License model change, some command deprecations
- Migration complexity: Medium (license review required, test data compatibility)

**Python 3.13-slim**:
- Current: python:3.13-slim
- Latest Stable: python:3.13.11-slim
- Python 3.14: Release Candidate phase
- Status: On current production release
- No action needed

**Node.js 22-alpine vs 24-alpine**:
- Current: node:22-alpine
- Node 22: Active LTS until April 2025, then Maintenance until April 2027
- Node 24 "Krypton": Active LTS until April 2026, Maintenance until April 2029
- Breaking changes: Minimal for standard usage
- Migration complexity: Low (LTS to LTS upgrade)

### Python Package Constraint Analysis

**Current pyproject.toml patterns**:
```toml
dependencies = [
    "discord.py>=2.3.0",
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "pydantic>=2.5.0",
    "cryptography>=41.0.0",
    # ... more packages
]
```

**Issue Identified**: Using minimum version constraints (`>=`) without upper bounds
- Allows any future version to be installed
- Current constraints are 6-12 months old
- Many packages have had major/minor releases since constraints set
- Could lead to unexpected breaking changes

**Best Practice Patterns**:
1. **Optimistic**: `package>=X.Y.0,<(X+1).0` - Allow minor/patch updates, block major
2. **Caret**: `package~=X.Y.0` - Equivalent to `>=X.Y.0,<X.(Y+1).0`
3. **Conservative**: `package>=X.Y.Z` - Current approach (allows all updates)

**Package-Specific Research**:

- **fastapi**: Latest 0.115.6 (from >=0.104.0)
  - 0.104.0: October 2023
  - 0.115.6: December 2024
  - Changes: Multiple feature additions, deprecations handled gracefully

- **pydantic**: Latest 2.10.6 (from >=2.5.0)
  - 2.5.0: December 2023
  - 2.10.6: December 2024
  - Changes: Performance improvements, new validation features

- **cryptography**: Latest 44.0.0 (from >=41.0.0)
  - 41.0.0: August 2023
  - 44.0.0: November 2024
  - Changes: Security fixes, deprecated algorithms removed

- **opentelemetry-***: Latest 1.29.0 (from >=1.20.0)
  - 1.20.0: September 2023
  - 1.29.0: December 2024
  - Changes: New features, improved performance, stability fixes

### NPM Package Version Analysis

**Recently Upgraded (Phase 1-4)**:
- React: 18.3.1 → 19.2.3 ✅
- MUI: 5.18.0 → 7.3.6 ✅
- ESLint: 8.57.1 → 9.39.2 ✅
- Vite: 5.4.21 → 6.4.1 ✅
- React Router: 6.20.0 → 7.1.1 ✅
- date-fns: 2.30.0 → 4.1.0 ✅

**Remaining Updates Needed**:
- **axios**: 1.6.2 → 1.7.9 (minor security fixes)
- **vite**: 6.4.1 → 7.2.7 (latest stable)
- **typescript**: 5.3.3 → 5.7.2 (latest stable)
- **@vitejs/plugin-react**: 4.2.1 → 5.0.1 (Vite 7 compatibility)

## Key Discoveries

### Database Migration Consolidation Lessons (Dec 2025)
- Alembic autogenerate dropped PostgreSQL server defaults because the SQLAlchemy models only used `default=` (Python-side) and did not declare `server_default=` (database-side). Example defects: `guild_configurations.require_host_role` lost default false; `channel_configurations.is_active` lost default true.
- Alembic autogenerate also cannot detect PostgreSQL functions/triggers; missing `notify_schedule_changed`, `notify_game_status_schedule_changed`, and their triggers were the root cause of daemon/test failures. The missing `ix_game_sessions_template_id` index was not in models and was also omitted.
- Alembic-utils would have prevented the function/trigger loss but would not fix missing server defaults; the real fix is to add `server_default` to the ORM models before regenerating migrations.
- Actionable fix path if redoing the migration: (1) add `server_default` to models for required defaults, (2) register functions/triggers via alembic-utils, (3) autogenerate the consolidated migration, (4) re-run integration tests to validate defaults and triggers.

### Infrastructure Service Upgrade Priorities

**HIGH PRIORITY - Node.js 22 → 24 LTS**:
- Node 22 enters Maintenance mode in 4 months (April 2025)
- Node 24 has 4 years of active support remaining
- Migration path: Well-documented, minimal breaking changes
- Risk: Low
- Effort: 30 minutes (update Dockerfile, test builds)

**MEDIUM PRIORITY - Redis 7.4 → 8.4**:
- Performance improvements: Up to 50% faster on certain workloads
- License change: Requires review for compliance
- Risk: Medium (data compatibility testing required)
- Effort: 2-4 hours (license review, testing, migration validation)

**HIGH PRIORITY - PostgreSQL 17 → 18**:
- PostgreSQL 17 supported until 2029, but upgrade is straightforward
- No production databases exist - can delete volumes and recreate
- **OPPORTUNITY**: Combine with Alembic reset to clean migration history
- Risk: Low (fresh database, no data migration)
- Effort: 1-2 hours (update image, reset Alembic, recreate database)

### Python Dependency Management Strategy

**Recommended Approach**: Use "compatible release" operator (`~=`)

```toml
dependencies = [
    "fastapi~=0.115.0",      # Allows 0.115.x, blocks 0.116.0
    "pydantic~=2.10.0",      # Allows 2.10.x, blocks 2.11.0
    "cryptography~=44.0.0",  # Allows 44.x.x, blocks 45.0.0
]
```

**Benefits**:
- Automatic security patches and bug fixes
- Blocks potentially breaking minor/major updates
- Explicit upgrade decisions for feature releases
- Reduces maintenance burden

**Alternative Approach**: Pin exact versions with periodic updates

```toml
dependencies = [
    "fastapi==0.115.6",
    "pydantic==2.10.6",
]
```

**Benefits**:
- Completely deterministic builds
- No surprises from updates
- Full control over upgrade timing

**Drawbacks**:
- Misses automatic security patches
- Requires active monitoring and updates
- More maintenance overhead

### NPM Package Update Strategy

**Vite 6 → 7 Considerations**:
- #fetch:"https://vite.dev/guide/migration" - Migration guide
- Breaking changes: Plugin API updates, config changes
- Requires @vitejs/plugin-react update to v5
- Benefits: Faster dev server, improved HMR, better error handling
- Estimated effort: 1-2 hours

**TypeScript 5.3 → 5.7 Considerations**:
- Decorator support improvements
- New type system features
- No breaking changes for standard usage
- Estimated effort: 15 minutes (update, verify build)

**axios 1.6 → 1.7 Considerations**:
- Security fixes for request handling
- Minor API additions
- No breaking changes
- Estimated effort: 5 minutes (update, verify tests)

## Recommended Approach

### Phase 1: High Priority Infrastructure (Immediate)
**Target: PostgreSQL 18 + Alembic Reset & Node.js 24 LTS Upgrade**

**Part A: PostgreSQL 18 Upgrade + Alembic Reset**

1. Update PostgreSQL image:
   - `compose.yaml`: `postgres:18-alpine`
   - `compose.*.yaml`: Update all environment-specific files

2. Reset Alembic migration history:
   ```bash
   # Stop and remove existing database volumes
   docker compose down -v

   # Delete all migration files except __init__.py
   rm alembic/versions/*.py

   # Create new initial migration from current models
   docker compose up -d postgres
   alembic revision --autogenerate -m "initial_schema"
   alembic upgrade head
   ```

3. Verify database schema:
   ```bash
   # Connect to database and verify tables
   docker compose exec postgres psql -U gamebot -d game_scheduler -c "\dt"
   ```

**Part B: Node.js 24 LTS Upgrade**

1. Update base images:
   - `docker/frontend.Dockerfile`: `FROM node:24-alpine`
   - `docker/test.Dockerfile`: `FROM node:24-alpine` (if exists)

2. Test frontend builds:
   ```bash
   docker compose build frontend
   npm run build
   npm run test
   ```

3. Verify CI/CD compatibility:
   - Check GitHub Actions workflows
   - Update any Node version specifications

**Success Criteria**:
- PostgreSQL 18 running successfully
- Clean Alembic migration history (single initial migration)
- All database tables created correctly
- Frontend Docker image builds successfully
- All npm scripts execute correctly
- CI/CD pipeline passes
- No compatibility warnings

**Estimated Effort**: 1-2 hours
**Risk Level**: LOW (no data migration, fresh start)

### Phase 2: Python Dependency Modernization (Short-term)
**Target: Update dependency constraints and upgrade packages**

1. Analyze current installed versions:
   ```bash
   uv pip list
   uv pip list --outdated
   ```

2. Update `pyproject.toml` with compatible release constraints:
   ```toml
   dependencies = [
       "fastapi~=0.115.0",
       "uvicorn[standard]~=0.34.0",
       "pydantic~=2.10.0",
       "pydantic-settings~=2.7.0",
       "sqlalchemy[asyncio]~=2.0.36",
       "cryptography~=44.0.0",
       "opentelemetry-api~=1.29.0",
       "opentelemetry-sdk~=1.29.0",
       # Update all OpenTelemetry packages to 1.29.0/0.50b0
   ]
   ```

3. Test upgrade:
   ```bash
   uv pip install --upgrade .
   pytest tests/
   ```

4. Update development dependencies similarly

**Success Criteria**:
- All packages upgrade successfully
- Zero test failures
- No deprecation warnings
- Type checking passes (mypy)

**Estimated Effort**: 2-3 hours
**Risk Level**: MEDIUM (requires thorough testing)

### Phase 3: NPM Package Updates (Short-term)
**Target: Minor version updates for build tools**

1. Update packages:
   ```bash
   cd frontend
   npm install axios@^1.7.0 typescript@^5.7.0
   npm run type-check
   npm run build
   npm run test
   ```

2. If no issues, consider Vite 7 upgrade:
   ```bash
   npm install vite@^7.0.0 @vitejs/plugin-react@^5.0.0
   # Review vite.config.ts for breaking changes
   npm run dev  # Test dev server
   npm run build  # Test production build
   ```

**Success Criteria**:
- All tests pass
- Production build succeeds
- Dev server starts without errors
- No type errors

**Estimated Effort**: 1-2 hours (without Vite 7), 2-3 hours (with Vite 7)
**Risk Level**: LOW (without Vite 7), MEDIUM (with Vite 7)

### Phase 4: Redis Evaluation (Medium-term)
**Target: Assess Redis 8 upgrade**

**Redis 7.4 → 8.4 Assessment**:
1. Review license changes (RSALv2/SSPLv1/AGPLv3)
2. Set up staging environment with Redis 8
3. Test data persistence and compatibility
4. Benchmark performance differences
5. Validate all Redis operations in application

**Decision Point**: Defer unless specific features/performance needed
- Redis 7.4 is stable and performant
- License review required for Redis 8
- Testing effort needed for data compatibility

**Estimated Effort**: 2-4 hours (assessment + implementation)
**Risk Level**: MEDIUM

## Implementation Guidance

### PostgreSQL 18 Upgrade + Alembic Reset Implementation

**Context**: No production databases exist, can safely delete volumes and start fresh with clean migration history.

**Files to Modify**:
1. `compose.yaml`:
   ```yaml
   postgres:
     image: postgres:18-alpine
   ```

2. All environment-specific compose files:
   - `compose.prod.yaml`
   - `compose.staging.yaml`
   - `compose.int.yaml`
   - `compose.e2e.yaml`

**Alembic Reset Procedure**:

```bash
# Step 1: Stop all services and remove volumes
docker compose down -v

# Step 2: Backup current Alembic versions (optional reference)
mkdir -p history/alembic_backup_$(date +%Y%m%d)
cp alembic/versions/*.py history/alembic_backup_$(date +%Y%m%d)/ || true

# Step 3: Clean migration directory (keep __init__.py only)
find alembic/versions -name "*.py" ! -name "__init__.py" -delete

# Step 4: Update PostgreSQL image version in compose files
sed -i 's/postgres:17-alpine/postgres:18-alpine/g' compose*.yaml

# Step 5: Start PostgreSQL
docker compose up -d postgres

# Step 6: Wait for PostgreSQL to be ready
sleep 5

# Step 7: Create fresh initial migration
alembic revision --autogenerate -m "initial_schema"

# Step 8: Apply migration
alembic upgrade head

# Step 9: Verify database schema
docker compose exec postgres psql -U gamebot -d game_scheduler -c "\dt"
docker compose exec postgres psql -U gamebot -d game_scheduler -c "\d+ games"

# Step 10: Start all services
docker compose up -d

# Step 11: Run integration tests to verify schema
pytest tests/integration/ -v
```

**Expected Initial Migration Contents**:
- `games` table with all current fields
- `game_participants` table
- `game_templates` table
- `discord_users` table
- All indexes and constraints
- Foreign key relationships

**Verification Checklist**:
- [ ] PostgreSQL 18 image running
- [ ] Single migration file in `alembic/versions/`
- [ ] `alembic_version` table shows current head
- [ ] All tables created with correct schema
- [ ] All services start successfully
- [ ] Integration tests pass
- [ ] API endpoints functional

**Rollback Procedure** (if issues):
```bash
# Restore original state
docker compose down -v
sed -i 's/postgres:18-alpine/postgres:17-alpine/g' compose*.yaml
cp history/alembic_backup_YYYYMMDD/*.py alembic/versions/
docker compose up -d
alembic upgrade head
```

### Node.js 24 LTS Upgrade Implementation

**Files to Modify**:
1. `docker/frontend.Dockerfile`:
   ```dockerfile
   FROM node:24-alpine AS base
   ```

2. `.github/workflows/*.yml` (if Node version specified):
   ```yaml
   - uses: actions/setup-node@v4
     with:
       node-version: '24'
   ```

3. `frontend/package.json` (optional, for documentation):
   ```json
   "engines": {
     "node": ">=24.0.0",
     "npm": ">=10.0.0"
   }
   ```

**Testing Checklist**:
- [ ] Docker image builds successfully
- [ ] `npm install` completes without errors
- [ ] `npm run build` produces valid build artifacts
- [ ] `npm run test` passes all tests
- [ ] `npm run dev` starts development server
- [ ] CI/CD pipeline succeeds
- [ ] No deprecation warnings in npm output

### Python Dependency Update Implementation

**Step 1: Backup current state**:
```bash
uv pip freeze > requirements.lock.txt
```

**Step 2: Update pyproject.toml**:
```toml
[project]
dependencies = [
    # Core Framework
    "discord.py~=2.4.0",
    "fastapi~=0.115.0",
    "uvicorn[standard]~=0.34.0",

    # Database
    "sqlalchemy[asyncio]~=2.0.36",
    "asyncpg~=0.30.0",
    "psycopg2-binary~=2.9.10",
    "alembic~=1.14.0",

    # Data Validation
    "pydantic~=2.10.0",
    "pydantic-settings~=2.7.0",

    # Storage & Messaging
    "redis~=5.2.0",
    "aio-pika~=9.5.0",
    "pika~=1.3.0",

    # HTTP Clients
    "httpx~=0.28.0",
    "aiohttp~=3.11.0",
    "python-multipart~=0.0.20",

    # Security
    "cryptography~=44.0.0",
    "python-jose[cryptography]~=3.3.0",

    # Utilities
    "icalendar~=6.0.0",

    # Observability
    "opentelemetry-api~=1.29.0",
    "opentelemetry-sdk~=1.29.0",
    "opentelemetry-instrumentation-fastapi~=0.50b0",
    "opentelemetry-instrumentation-sqlalchemy~=0.50b0",
    "opentelemetry-instrumentation-asyncpg~=0.50b0",
    "opentelemetry-instrumentation-redis~=0.50b0",
    "opentelemetry-instrumentation-aio-pika~=0.50b0",
    "opentelemetry-exporter-otlp~=1.29.0",
]

[dependency-groups]
dev = [
    "pytest~=8.3.0",
    "pytest-asyncio~=0.24.0",
    "pytest-cov~=6.0.0",
    "ruff~=0.9.0",
    "mypy~=1.15.0",
    "autocopyright~=1.1.0",
    "pre-commit~=4.0.0",
]
```

**Step 3: Upgrade and test**:
```bash
# Upgrade packages
uv pip install --upgrade .

# Verify installation
uv pip list

# Run type checking
mypy shared/ services/

# Run tests
pytest tests/ -v

# Run linting
ruff check .
```

**Step 4: Validate services**:
```bash
# Test each service independently
cd services/api && uv run uvicorn main:app --reload  # Ctrl+C after startup
cd services/bot && uv run python -m bot.main --help
# ... test other services
```

**Rollback Procedure** (if issues found):
```bash
# Restore previous state
cp requirements.lock.txt requirements.txt
uv pip install -r requirements.txt
```

### NPM Package Update Implementation

**Axios Update**:
```bash
cd frontend
npm install axios@^1.7.0
npm run test
npm run build
```

**TypeScript Update**:
```bash
npm install -D typescript@^5.7.0
npm run type-check
npm run build
npm run test
```

**Vite 7 Update** (if proceeding):
```bash
# Review migration guide first
npm install -D vite@^7.0.0 @vitejs/plugin-react@^5.0.0

# Check vite.config.ts for breaking changes
npm run dev  # Test dev server
npm run build  # Test production build
npm run preview  # Test preview server

# Run full test suite
npm run test
```

## Dependencies

- Docker and Docker Compose (installed)
- Node.js LTS (for local frontend development)
- Python 3.11+ with uv (installed in dev container)
- Git (for version control)

## Success Criteria

### Phase 1 Success (PostgreSQL 18 + Alembic Reset & Node.js 24 LTS)
- [ ] PostgreSQL 18-alpine image running
- [ ] Clean Alembic migration history (single initial migration)
- [ ] All database tables match current model definitions
- [ ] All foreign keys and indexes created correctly
- [ ] Docker image builds with node:24-alpine
- [ ] All npm scripts execute successfully
- [ ] Integration tests pass
- [ ] CI/CD pipeline passes
- [ ] No compatibility warnings
- [ ] All services start and connect successfully

### Phase 2 Success (Python Dependencies)
- [ ] All packages upgrade to modern versions
- [ ] Zero test failures across all test suites
- [ ] Type checking passes with no errors
- [ ] No deprecation warnings in logs
- [ ] All services start successfully

### Phase 3 Success (NPM Updates)
- [ ] Build process completes successfully
- [ ] All tests pass (51/51)
- [ ] Dev server starts without errors
- [ ] Production bundle size within acceptable range
- [ ] No console errors or warnings

### Phase 4 Success (Redis Evaluation)
- [ ] Comprehensive assessment documented
- [ ] License review completed
- [ ] Staging environment tested
- [ ] Performance benchmarks completed
- [ ] Data compatibility validated
- [ ] Go/no-go decision made with rationale
- [ ] If proceeding: Upgrade plan documented

## Risk Mitigation

**High-Risk Changes**:
- Major version upgrades of core dependencies
- Infrastructure service major version changes
- Database engine upgrades

**Mitigation Strategies**:
1. **Staging Environment Testing**: Test all changes in staging before production
2. **Backup Procedures**: Full database backups before any DB upgrades
3. **Rollback Plans**: Document and test rollback procedures
4. **Incremental Deployment**: Deploy changes in phases, not all at once
5. **Monitoring**: Enhanced monitoring during and after upgrades
6. **Communication**: Notify team of planned changes and potential impacts

**Low-Risk Changes**:
- Patch version updates within compatible ranges
- Development tool updates
- Documentation updates

**Best Practices**:
- Always pin exact versions in lockfiles (package-lock.json, uv.lock)
- Test in development container before production
- Use feature flags for gradual rollout when applicable
- Maintain changelog of all dependency updates
