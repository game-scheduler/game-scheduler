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


"""add_signup_methods

Revision ID: b49eb343d5a6
Revises: 8438728f8184
Create Date: 2025-12-27 12:50:58.193701

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b49eb343d5a6"
down_revision: str | None = "8438728f8184"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "game_templates",
        sa.Column("allowed_signup_methods", sa.JSON(), nullable=True),
    )
    op.add_column(
        "game_templates",
        sa.Column("default_signup_method", sa.String(length=50), nullable=True),
    )

    op.add_column(
        "game_sessions",
        sa.Column(
            "signup_method",
            sa.String(length=50),
            nullable=True,
            server_default="SELF_SIGNUP",
        ),
    )

    op.execute("UPDATE game_sessions SET signup_method = 'SELF_SIGNUP' WHERE signup_method IS NULL")

    op.alter_column("game_sessions", "signup_method", nullable=False)


def downgrade() -> None:
    op.drop_column("game_sessions", "signup_method")
    op.drop_column("game_templates", "default_signup_method")
    op.drop_column("game_templates", "allowed_signup_methods")
