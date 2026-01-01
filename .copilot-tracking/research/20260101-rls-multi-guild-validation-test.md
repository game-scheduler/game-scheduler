<!-- markdownlint-disable-file -->
# RLS Multi-Guild Validation Test

## Purpose

Minimal throwaway test to validate that PostgreSQL Row-Level Security (RLS) correctly filters rows based on a comma-separated list of guild IDs stored in a session variable.

**Critical Question**: Does the RLS policy `guild_id::text = ANY(string_to_array(current_setting(...), ','))` work correctly with multiple guilds?

**Success Criteria**: Query returns exactly 2 out of 3 rows when context set to 2 guild IDs.

## Test Script

### Standalone SQL Test

**File**: `tests/manual/test_rls_multi_guild.sql` (throwaway)

```sql
-- Clean up from any previous runs
DROP TABLE IF EXISTS test_rls_guilds CASCADE;

-- Create test table with guild_id
CREATE TABLE test_rls_guilds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    guild_id TEXT NOT NULL,
    data TEXT NOT NULL
);

-- Create index for RLS performance
CREATE INDEX idx_test_rls_guilds_guild_id ON test_rls_guilds(guild_id);

-- Create RLS policy (same pattern as production)
CREATE POLICY test_guild_isolation ON test_rls_guilds
    FOR ALL
    USING (
        guild_id = ANY(
            string_to_array(
                current_setting('app.current_guild_ids', true),
                ','
            )
        )
    );

-- Enable RLS
ALTER TABLE test_rls_guilds ENABLE ROW LEVEL SECURITY;

-- Insert 3 test rows with different guild IDs
INSERT INTO test_rls_guilds (guild_id, data) VALUES
    ('guild_alpha', 'Data from Guild Alpha'),
    ('guild_beta', 'Data from Guild Beta'),
    ('guild_gamma', 'Data from Guild Gamma');

-- Verify all 3 rows exist (no RLS context set yet)
SELECT COUNT(*) as total_rows FROM test_rls_guilds;
-- Expected: 3 rows

-- Test 1: Set context with 2 guild IDs
SET LOCAL app.current_guild_ids = 'guild_alpha,guild_beta';

-- Query should return only 2 rows (guild_alpha and guild_beta)
SELECT guild_id, data FROM test_rls_guilds ORDER BY guild_id;
-- Expected: 2 rows (guild_alpha, guild_beta)

-- Verify count
SELECT COUNT(*) as filtered_count FROM test_rls_guilds;
-- Expected: 2

-- Test 2: Change context to different guild
ROLLBACK;  -- Clear LOCAL setting
BEGIN;
SET LOCAL app.current_guild_ids = 'guild_gamma';

-- Query should return only 1 row (guild_gamma)
SELECT guild_id, data FROM test_rls_guilds;
-- Expected: 1 row (guild_gamma)

SELECT COUNT(*) as filtered_count FROM test_rls_guilds;
-- Expected: 1

-- Test 3: Empty context (no guilds)
ROLLBACK;
BEGIN;
SET LOCAL app.current_guild_ids = '';

-- Query should return 0 rows
SELECT COUNT(*) as filtered_count FROM test_rls_guilds;
-- Expected: 0

-- Test 4: All three guilds
ROLLBACK;
BEGIN;
SET LOCAL app.current_guild_ids = 'guild_alpha,guild_beta,guild_gamma';

-- Query should return all 3 rows
SELECT COUNT(*) as filtered_count FROM test_rls_guilds;
-- Expected: 3

-- Cleanup
ROLLBACK;
DROP TABLE IF EXISTS test_rls_guilds CASCADE;
```

### How to Run

**From host machine**:
```bash
# Run SQL test script
docker compose exec postgres psql -U gamebot -d game_scheduler -f /tmp/test_rls_multi_guild.sql

# Or copy-paste into psql session
docker compose exec postgres psql -U gamebot -d game_scheduler
# Then paste SQL commands
```

**Expected Output**:
```
CREATE TABLE
CREATE INDEX
CREATE POLICY
ALTER TABLE

INSERT 0 3

 total_rows
------------
          3
(1 row)

SET

    guild_id   |          data
---------------+-------------------------
 guild_alpha   | Data from Guild Alpha
 guild_beta    | Data from Guild Beta
(2 rows)

 filtered_count
----------------
              2
(1 row)

ROLLBACK
BEGIN
SET

    guild_id   |          data
---------------+-------------------------
 guild_gamma   | Data from Guild Gamma
(1 row)

 filtered_count
----------------
              1
(1 row)

ROLLBACK
BEGIN
SET

 filtered_count
----------------
              0
(1 row)

ROLLBACK
BEGIN
SET

 filtered_count
----------------
              3
(1 row)

ROLLBACK
DROP TABLE
```

## Python Integration Test Version

**File**: `tests/integration/test_rls_multi_guild_validation.py` (temporary)

```python
"""
Validation test for PostgreSQL RLS with multiple guilds.

This is a throwaway test to validate the RLS mechanism before full implementation.
"""
import pytest
from sqlalchemy import text
from shared.database import get_sync_db_session


@pytest.mark.integration
def test_rls_filters_multiple_guilds():
    """RLS policy correctly filters rows based on comma-separated guild list."""

    with get_sync_db_session() as db:
        # Setup: Create test table with RLS
        db.execute(text("DROP TABLE IF EXISTS test_rls_guilds CASCADE"))
        db.execute(text("""
            CREATE TABLE test_rls_guilds (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                guild_id TEXT NOT NULL,
                data TEXT NOT NULL
            )
        """))
        db.execute(text("""
            CREATE INDEX idx_test_rls_guilds_guild_id
            ON test_rls_guilds(guild_id)
        """))
        db.execute(text("""
            CREATE POLICY test_guild_isolation ON test_rls_guilds
                FOR ALL
                USING (
                    guild_id = ANY(
                        string_to_array(
                            current_setting('app.current_guild_ids', true),
                            ','
                        )
                    )
                )
        """))
        db.execute(text("ALTER TABLE test_rls_guilds ENABLE ROW LEVEL SECURITY"))
        db.commit()

        # Insert test data
        db.execute(text("""
            INSERT INTO test_rls_guilds (guild_id, data) VALUES
                ('guild_alpha', 'Data from Guild Alpha'),
                ('guild_beta', 'Data from Guild Beta'),
                ('guild_gamma', 'Data from Guild Gamma')
        """))
        db.commit()

        # Test 1: Multiple guilds in context
        db.execute(text("SET LOCAL app.current_guild_ids = 'guild_alpha,guild_beta'"))
        result = db.execute(text("SELECT COUNT(*) FROM test_rls_guilds"))
        count = result.scalar()
        assert count == 2, f"Expected 2 rows, got {count}"

        # Verify correct guilds returned
        result = db.execute(text("SELECT guild_id FROM test_rls_guilds ORDER BY guild_id"))
        guild_ids = [row[0] for row in result]
        assert guild_ids == ['guild_alpha', 'guild_beta']

        db.rollback()  # Clear LOCAL setting

        # Test 2: Single guild in context
        db.execute(text("SET LOCAL app.current_guild_ids = 'guild_gamma'"))
        result = db.execute(text("SELECT COUNT(*) FROM test_rls_guilds"))
        count = result.scalar()
        assert count == 1, f"Expected 1 row, got {count}"

        result = db.execute(text("SELECT guild_id FROM test_rls_guilds"))
        guild_id = result.scalar()
        assert guild_id == 'guild_gamma'

        db.rollback()

        # Test 3: Empty context
        db.execute(text("SET LOCAL app.current_guild_ids = ''"))
        result = db.execute(text("SELECT COUNT(*) FROM test_rls_guilds"))
        count = result.scalar()
        assert count == 0, f"Expected 0 rows, got {count}"

        db.rollback()

        # Test 4: All guilds
        db.execute(text("SET LOCAL app.current_guild_ids = 'guild_alpha,guild_beta,guild_gamma'"))
        result = db.execute(text("SELECT COUNT(*) FROM test_rls_guilds"))
        count = result.scalar()
        assert count == 3, f"Expected 3 rows, got {count}"

        db.rollback()

        # Cleanup
        db.execute(text("DROP TABLE IF EXISTS test_rls_guilds CASCADE"))
        db.commit()


@pytest.mark.integration
def test_rls_with_uuid_guild_ids():
    """RLS policy works with UUID guild_ids (production pattern)."""

    with get_sync_db_session() as db:
        # Setup: Create test table matching production schema
        db.execute(text("DROP TABLE IF EXISTS test_rls_guilds_uuid CASCADE"))
        db.execute(text("""
            CREATE TABLE test_rls_guilds_uuid (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                guild_id UUID NOT NULL,
                data TEXT NOT NULL
            )
        """))
        db.execute(text("""
            CREATE INDEX idx_test_rls_guilds_uuid_guild_id
            ON test_rls_guilds_uuid(guild_id)
        """))
        db.execute(text("""
            CREATE POLICY test_guild_isolation_uuid ON test_rls_guilds_uuid
                FOR ALL
                USING (
                    guild_id::text = ANY(
                        string_to_array(
                            current_setting('app.current_guild_ids', true),
                            ','
                        )
                    )
                )
        """))
        db.execute(text("ALTER TABLE test_rls_guilds_uuid ENABLE ROW LEVEL SECURITY"))
        db.commit()

        # Insert test data with UUIDs
        db.execute(text("""
            INSERT INTO test_rls_guilds_uuid (guild_id, data) VALUES
                ('11111111-1111-1111-1111-111111111111', 'Guild 1 Data'),
                ('22222222-2222-2222-2222-222222222222', 'Guild 2 Data'),
                ('33333333-3333-3333-3333-333333333333', 'Guild 3 Data')
        """))
        db.commit()

        # Test: Filter with 2 UUIDs (matching production scenario)
        db.execute(text("""
            SET LOCAL app.current_guild_ids =
            '11111111-1111-1111-1111-111111111111,22222222-2222-2222-2222-222222222222'
        """))
        result = db.execute(text("SELECT COUNT(*) FROM test_rls_guilds_uuid"))
        count = result.scalar()
        assert count == 2, f"Expected 2 rows with UUID filtering, got {count}"

        # Verify correct rows returned
        result = db.execute(text("""
            SELECT guild_id::text FROM test_rls_guilds_uuid ORDER BY guild_id
        """))
        guild_ids = [row[0] for row in result]
        assert len(guild_ids) == 2
        assert '11111111-1111-1111-1111-111111111111' in guild_ids
        assert '22222222-2222-2222-2222-222222222222' in guild_ids
        assert '33333333-3333-3333-3333-333333333333' not in guild_ids

        db.rollback()

        # Cleanup
        db.execute(text("DROP TABLE IF EXISTS test_rls_guilds_uuid CASCADE"))
        db.commit()
```

### Run Python Test

```bash
# Run integration test
uv run scripts/run-integration-tests.sh -- tests/integration/test_rls_multi_guild_validation.py -v

# Or run directly with pytest
uv run pytest tests/integration/test_rls_multi_guild_validation.py -v
```

## Discord Snowflake ID Test

**Note**: In production, Discord guild IDs are snowflakes (numeric strings like "123456789012345678"), but stored as TEXT in `app.current_guild_ids`. The database `guild_id` column is UUID. This test validates the conversion.

**File**: Add to `tests/integration/test_rls_multi_guild_validation.py`

```python
@pytest.mark.integration
def test_rls_with_discord_snowflakes_to_uuid():
    """RLS policy works with Discord snowflake IDs mapped to database UUIDs."""

    with get_sync_db_session() as db:
        # Setup test table
        db.execute(text("DROP TABLE IF EXISTS test_discord_guilds CASCADE"))
        db.execute(text("""
            CREATE TABLE test_discord_guilds (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                guild_id UUID NOT NULL,  -- Database UUID
                discord_id TEXT NOT NULL,  -- Discord snowflake
                data TEXT NOT NULL
            )
        """))
        db.execute(text("""
            CREATE POLICY test_discord_isolation ON test_discord_guilds
                FOR ALL
                USING (
                    -- Filter by database UUID matching Discord IDs in context
                    guild_id::text = ANY(
                        string_to_array(
                            current_setting('app.current_guild_ids', true),
                            ','
                        )
                    )
                )
        """))
        db.execute(text("ALTER TABLE test_discord_guilds ENABLE ROW LEVEL SECURITY"))
        db.commit()

        # Insert with known UUIDs
        guild_a_uuid = '11111111-1111-1111-1111-111111111111'
        guild_b_uuid = '22222222-2222-2222-2222-222222222222'
        guild_c_uuid = '33333333-3333-3333-3333-333333333333'

        db.execute(text(f"""
            INSERT INTO test_discord_guilds (guild_id, discord_id, data) VALUES
                ('{guild_a_uuid}', '123456789012345678', 'Guild A Data'),
                ('{guild_b_uuid}', '234567890123456789', 'Guild B Data'),
                ('{guild_c_uuid}', '345678901234567890', 'Guild C Data')
        """))
        db.commit()

        # Simulate production: OAuth returns Discord IDs, we look up UUIDs,
        # then store UUIDs in context
        db.execute(text(f"""
            SET LOCAL app.current_guild_ids = '{guild_a_uuid},{guild_b_uuid}'
        """))

        result = db.execute(text("SELECT COUNT(*) FROM test_discord_guilds"))
        count = result.scalar()
        assert count == 2, f"Expected 2 rows with UUID context, got {count}"

        result = db.execute(text("""
            SELECT discord_id FROM test_discord_guilds ORDER BY discord_id
        """))
        discord_ids = [row[0] for row in result]
        assert discord_ids == ['123456789012345678', '234567890123456789']

        db.rollback()

        # Cleanup
        db.execute(text("DROP TABLE IF EXISTS test_discord_guilds CASCADE"))
        db.commit()
```

## Production Pattern Note

**Important**: The production implementation will:

1. **User authenticates** → OAuth returns Discord guild IDs (snowflakes)
2. **Fetch database UUIDs** → Query `guilds` table: `SELECT id FROM guilds WHERE guild_id IN (discord_ids)`
3. **Store UUIDs in context** → `set_current_guild_ids([uuid1, uuid2, ...])`
4. **Event listener** → `SET LOCAL app.current_guild_ids = 'uuid1,uuid2'`
5. **RLS policy** → Filter `WHERE guild_id::text = ANY(string_to_array(...))`

This test validates step 5 works correctly with multiple UUIDs.

## Expected Results

### Success Indicators
- ✅ SQL test returns 2 rows when context has 2 guild IDs
- ✅ SQL test returns 1 row when context has 1 guild ID
- ✅ SQL test returns 0 rows when context is empty
- ✅ SQL test returns 3 rows when context has all 3 guild IDs
- ✅ Python test passes all assertions
- ✅ UUID filtering works correctly
- ✅ Performance: Query uses index (`EXPLAIN ANALYZE` shows Index Scan)

### Failure Indicators
- ❌ Returns wrong number of rows
- ❌ Returns rows from guilds not in context
- ❌ RLS policy syntax error
- ❌ Performance: Query uses Seq Scan instead of Index Scan
- ❌ NULL handling issues

## Performance Validation

```sql
-- After running test setup, verify index usage
EXPLAIN ANALYZE
SELECT * FROM test_rls_guilds
WHERE guild_id = ANY(string_to_array('guild_alpha,guild_beta', ','));
```

**Expected plan**:
```
Index Scan using idx_test_rls_guilds_guild_id on test_rls_guilds
  Index Cond: (guild_id = ANY(...))
  Planning Time: 0.X ms
  Execution Time: 0.X ms
```

**Red flag**: If shows `Seq Scan` instead of `Index Scan`, index not being used.

## Cleanup

After validation passes, delete temporary files:
```bash
rm tests/manual/test_rls_multi_guild.sql
rm tests/integration/test_rls_multi_guild_validation.py
```

## Next Steps

1. **Run SQL test manually** - Validate RLS mechanism works
2. **Run Python integration test** - Validate from application code
3. **Check performance** - Verify index usage
4. **If all pass** → Proceed with full implementation in [20260101-middleware-rls-guild-isolation-research.md](20260101-middleware-rls-guild-isolation-research.md)
5. **If any fail** → Research alternative RLS policy patterns

## References

- PostgreSQL RLS documentation: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
- string_to_array function: https://www.postgresql.org/docs/current/functions-array.html
- current_setting function: https://www.postgresql.org/docs/current/functions-admin.html
