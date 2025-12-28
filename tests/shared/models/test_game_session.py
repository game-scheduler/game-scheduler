# Copyright 2025 Bret McKee (bret.mckee@gmail.com)
#
# This file is part of Game_Scheduler. (https://github.com/game-scheduler)
#
# Game_Scheduler is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# Game_Scheduler is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General
# Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with Game_Scheduler If not, see <https://www.gnu.org/licenses/>.


"""Tests for GameSession model image storage."""

from sqlalchemy import inspect

from shared.models.game import GameSession


def test_game_session_has_image_columns():
    """Verify GameSession model has image storage columns."""
    mapper = inspect(GameSession)
    column_names = {col.key for col in mapper.columns}

    image_columns = {
        "thumbnail_data",
        "thumbnail_mime_type",
        "image_data",
        "image_mime_type",
    }

    assert image_columns.issubset(column_names), (
        f"Missing image columns: {image_columns - column_names}"
    )


def test_game_session_image_columns_nullable():
    """Verify image columns are nullable."""
    mapper = inspect(GameSession)
    columns = {col.key: col for col in mapper.columns}

    assert columns["thumbnail_data"].nullable, "thumbnail_data should be nullable"
    assert columns["thumbnail_mime_type"].nullable, "thumbnail_mime_type should be nullable"
    assert columns["image_data"].nullable, "image_data should be nullable"
    assert columns["image_mime_type"].nullable, "image_mime_type should be nullable"


def test_game_session_mime_type_columns_are_strings():
    """Verify MIME type columns are string type."""
    mapper = inspect(GameSession)
    columns = {col.key: col for col in mapper.columns}

    assert str(columns["thumbnail_mime_type"].type) == "VARCHAR(50)"
    assert str(columns["image_mime_type"].type) == "VARCHAR(50)"


def test_game_session_data_columns_are_binary():
    """Verify data columns are binary type."""
    mapper = inspect(GameSession)
    columns = {col.key: col for col in mapper.columns}

    assert "BYTEA" in str(columns["thumbnail_data"].type) or "BLOB" in str(
        columns["thumbnail_data"].type
    )
    assert "BYTEA" in str(columns["image_data"].type) or "BLOB" in str(columns["image_data"].type)


def test_game_session_has_signup_method_column():
    """Verify GameSession model has signup_method column."""
    mapper = inspect(GameSession)
    column_names = {col.key for col in mapper.columns}

    assert "signup_method" in column_names, "Missing signup_method column"


def test_game_session_signup_method_not_nullable():
    """Verify signup_method column is not nullable and has default."""
    mapper = inspect(GameSession)
    columns = {col.key: col for col in mapper.columns}

    signup_method_col = columns["signup_method"]
    assert not signup_method_col.nullable, "signup_method should not be nullable"
    assert signup_method_col.default is not None, "signup_method should have default value"


def test_game_session_signup_method_is_string():
    """Verify signup_method column is string type."""
    mapper = inspect(GameSession)
    columns = {col.key: col for col in mapper.columns}

    assert "VARCHAR(50)" in str(columns["signup_method"].type)
