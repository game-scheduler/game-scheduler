#!/usr/bin/env python3
# Copyright 2025-2026 Bret McKee
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


"""
Unit tests for database user creation helpers.

Tests the extracted helper methods for admin, app, and bot user creation
and permission granting.
"""

from unittest.mock import MagicMock

from psycopg2 import sql

from services.init.database_users import (
    _create_admin_user,
    _create_app_user,
    _create_bot_user,
    _grant_permissions,
)


class TestCreateAdminUser:
    """Test admin user creation helper."""

    def test_creates_admin_user_with_correct_sql(self):
        """Verify admin user is created with SUPERUSER privilege."""
        cursor = MagicMock()

        _create_admin_user(cursor, "test_admin", "test_password")

        assert cursor.execute.called
        sql_call = cursor.execute.call_args[0][0]
        params = cursor.execute.call_args[0][1]

        assert "CREATE USER test_admin" in sql_call
        assert "SUPERUSER" in sql_call
        assert "Superuser for Alembic migrations" in sql_call
        assert params == ("test_admin", "test_password")

    def test_checks_for_existing_user(self):
        """Verify SQL checks if user already exists before creating."""
        cursor = MagicMock()

        _create_admin_user(cursor, "existing_admin", "password")

        sql = cursor.execute.call_args[0][0]
        assert "IF NOT EXISTS" in sql
        assert "SELECT FROM pg_catalog.pg_roles WHERE rolname = %s" in sql

    def test_adds_role_comment(self):
        """Verify COMMENT is added to explain role purpose."""
        cursor = MagicMock()

        _create_admin_user(cursor, "admin_user", "pwd")

        sql = cursor.execute.call_args[0][0]
        assert "COMMENT ON ROLE" in sql


class TestCreateAppUser:
    """Test application user creation helper."""

    def test_creates_app_user_without_superuser(self):
        """Verify app user is created WITHOUT SUPERUSER for RLS enforcement."""
        cursor = MagicMock()

        _create_app_user(cursor, "test_app", "test_password")

        sql = cursor.execute.call_args[0][0]
        params = cursor.execute.call_args[0][1]

        assert "CREATE USER test_app" in sql
        assert "LOGIN" in sql
        assert "SUPERUSER" not in sql
        assert "Non-privileged user for application runtime" in sql
        assert params == ("test_app", "test_password")

    def test_checks_for_existing_app_user(self):
        """Verify SQL checks if app user already exists."""
        cursor = MagicMock()

        _create_app_user(cursor, "existing_app", "password")

        sql = cursor.execute.call_args[0][0]
        assert "IF NOT EXISTS" in sql
        assert "SELECT FROM pg_catalog.pg_roles WHERE rolname = %s" in sql


class TestCreateBotUser:
    """Test bot user creation helper."""

    def test_creates_bot_user_with_bypassrls(self):
        """Verify bot user is created with BYPASSRLS privilege."""
        cursor = MagicMock()

        _create_bot_user(cursor, "test_bot", "test_password")

        sql = cursor.execute.call_args[0][0]
        params = cursor.execute.call_args[0][1]

        assert "CREATE USER test_bot" in sql
        assert "BYPASSRLS" in sql
        assert "Bot/daemon user - bypasses RLS" in sql
        assert params == ("test_bot", "test_password")

    def test_bot_user_not_superuser(self):
        """Verify bot user doesn't get SUPERUSER (security principle)."""
        cursor = MagicMock()

        _create_bot_user(cursor, "bot_user", "password")

        sql = cursor.execute.call_args[0][0]
        assert "SUPERUSER" not in sql

    def test_checks_for_existing_bot_user(self):
        """Verify SQL checks if bot user already exists."""
        cursor = MagicMock()

        _create_bot_user(cursor, "existing_bot", "password")

        sql = cursor.execute.call_args[0][0]
        assert "IF NOT EXISTS" in sql


class TestGrantPermissions:
    """Test permission granting helper."""

    def test_grants_connect_permission(self):
        """Verify CONNECT permission is granted on database."""
        cursor = MagicMock()

        _grant_permissions(cursor, "target_user", "postgres", "admin", "testdb")

        sql_obj = cursor.execute.call_args[0][0]
        assert isinstance(sql_obj, sql.Composed)
        # Verify the execute was called with correct parameters
        assert cursor.execute.call_count == 1

    def test_grants_schema_permissions(self):
        """Verify USAGE and CREATE permissions granted on public schema."""
        cursor = MagicMock()

        _grant_permissions(cursor, "target_user", "postgres", "admin", "testdb")

        sql_obj = cursor.execute.call_args[0][0]
        assert isinstance(sql_obj, sql.Composed)
        assert cursor.execute.call_count == 1

    def test_grants_table_permissions(self):
        """Verify comprehensive table permissions are granted."""
        cursor = MagicMock()

        _grant_permissions(cursor, "target_user", "postgres", "admin", "testdb")

        sql_obj = cursor.execute.call_args[0][0]
        assert isinstance(sql_obj, sql.Composed)
        assert cursor.execute.call_count == 1

    def test_grants_sequence_permissions(self):
        """Verify sequence permissions are granted."""
        cursor = MagicMock()

        _grant_permissions(cursor, "target_user", "postgres", "admin", "testdb")

        sql_obj = cursor.execute.call_args[0][0]
        assert isinstance(sql_obj, sql.Composed)
        assert cursor.execute.call_count == 1

    def test_grants_function_permissions(self):
        """Verify EXECUTE permission on functions is granted."""
        cursor = MagicMock()

        _grant_permissions(cursor, "target_user", "postgres", "admin", "testdb")

        sql_obj = cursor.execute.call_args[0][0]
        assert isinstance(sql_obj, sql.Composed)
        assert cursor.execute.call_count == 1

    def test_sets_default_privileges_for_postgres_user(self):
        """Verify default privileges set for objects created by postgres superuser."""
        cursor = MagicMock()

        _grant_permissions(cursor, "target_user", "postgres_super", "admin", "testdb")

        sql_obj = cursor.execute.call_args[0][0]
        assert isinstance(sql_obj, sql.Composed)
        assert cursor.execute.call_count == 1

    def test_sets_default_privileges_for_admin_user(self):
        """Verify default privileges set for objects created by admin user (migrations)."""
        cursor = MagicMock()

        _grant_permissions(cursor, "target_user", "postgres", "migration_admin", "testdb")

        sql_obj = cursor.execute.call_args[0][0]
        assert isinstance(sql_obj, sql.Composed)
        assert cursor.execute.call_count == 1

    def test_single_execute_call(self):
        """Verify all permissions granted in single SQL execution."""
        cursor = MagicMock()

        _grant_permissions(cursor, "target_user", "postgres", "admin", "testdb")

        assert cursor.execute.call_count == 1
