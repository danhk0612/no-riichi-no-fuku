"""Create the initial application schema.

Revision ID: 20260829_0001
Revises:
Create Date: 2026-08-29
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260829_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("login_id", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("player_name", sa.String(length=80), nullable=True),
        sa.Column("profile_image_key", sa.String(length=512), nullable=True),
        sa.Column("current_hp", sa.Integer(), nullable=True),
        sa.Column("max_hp", sa.Integer(), nullable=True),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("must_change_password", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *timestamps(),
        sa.CheckConstraint(
            "current_hp IS NULL OR current_hp >= 0", name="ck_users_current_hp"
        ),
        sa.CheckConstraint("max_hp IS NULL OR max_hp > 0", name="ck_users_max_hp"),
        sa.CheckConstraint(
            "current_hp IS NULL OR max_hp IS NULL OR current_hp <= max_hp",
            name="ck_users_hp_range",
        ),
    )
    op.create_index("ix_users_login_id", "users", ["login_id"], unique=True)
    op.create_index("ix_users_role", "users", ["role"])
    op.create_index("ix_users_is_active", "users", ["is_active"])

    op.create_table(
        "cpu_characters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("age_adult", sa.Boolean(), nullable=False),
        sa.Column("style", sa.String(length=40), nullable=False),
        sa.Column("short_description", sa.String(length=255), nullable=False),
        sa.Column("long_description", sa.Text(), nullable=True),
        sa.Column("profile_image_key", sa.String(length=512), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("aggression", sa.Float(), nullable=False),
        sa.Column("defense", sa.Float(), nullable=False),
        sa.Column("call_preference", sa.Float(), nullable=False),
        sa.Column("riichi_preference", sa.Float(), nullable=False),
        sa.Column("hand_value_preference", sa.Float(), nullable=False),
        sa.Column("speed_preference", sa.Float(), nullable=False),
        *timestamps(),
        sa.CheckConstraint("age_adult = true", name="ck_cpu_characters_adult"),
    )
    op.create_index(
        "ix_cpu_characters_slug", "cpu_characters", ["slug"], unique=True
    )
    op.create_index("ix_cpu_characters_active", "cpu_characters", ["active"])

    op.create_table(
        "user_cpu_progress",
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "cpu_character_id",
            sa.Integer(),
            sa.ForeignKey("cpu_characters.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("defeat_stage", sa.Integer(), nullable=False),
        *timestamps(),
        sa.CheckConstraint(
            "defeat_stage >= 0 AND defeat_stage <= 3",
            name="ck_user_cpu_progress_defeat_stage",
        ),
    )

    op.create_table(
        "cpu_dialogues",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "cpu_character_id",
            sa.Integer(),
            sa.ForeignKey("cpu_characters.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_key", sa.String(length=64), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        *timestamps(),
    )
    op.create_index(
        "ix_cpu_dialogues_cpu_character_id",
        "cpu_dialogues",
        ["cpu_character_id"],
    )
    op.create_index("ix_cpu_dialogues_event_key", "cpu_dialogues", ["event_key"])
    op.create_index("ix_cpu_dialogues_active", "cpu_dialogues", ["active"])

    op.create_table(
        "cpu_result_assets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "cpu_character_id",
            sa.Integer(),
            sa.ForeignKey("cpu_characters.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("defeat_stage", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        *timestamps(),
        sa.CheckConstraint(
            "defeat_stage >= 1 AND defeat_stage <= 3",
            name="ck_cpu_result_assets_defeat_stage",
        ),
        sa.UniqueConstraint(
            "cpu_character_id",
            "defeat_stage",
            name="uq_cpu_result_assets_character_stage",
        ),
        sa.UniqueConstraint("storage_key", name="uq_cpu_result_assets_storage_key"),
    )
    op.create_index(
        "ix_cpu_result_assets_cpu_character_id",
        "cpu_result_assets",
        ["cpu_character_id"],
    )

    op.create_table(
        "game_settings",
        sa.Column("key", sa.String(length=80), primary_key=True),
        sa.Column("value", sa.JSON(), nullable=False),
        *timestamps(),
    )


def downgrade() -> None:
    op.drop_table("game_settings")
    op.drop_index(
        "ix_cpu_result_assets_cpu_character_id", table_name="cpu_result_assets"
    )
    op.drop_table("cpu_result_assets")
    op.drop_index("ix_cpu_dialogues_active", table_name="cpu_dialogues")
    op.drop_index("ix_cpu_dialogues_event_key", table_name="cpu_dialogues")
    op.drop_index(
        "ix_cpu_dialogues_cpu_character_id", table_name="cpu_dialogues"
    )
    op.drop_table("cpu_dialogues")
    op.drop_table("user_cpu_progress")
    op.drop_index("ix_cpu_characters_active", table_name="cpu_characters")
    op.drop_index("ix_cpu_characters_slug", table_name="cpu_characters")
    op.drop_table("cpu_characters")
    op.drop_index("ix_users_is_active", table_name="users")
    op.drop_index("ix_users_role", table_name="users")
    op.drop_index("ix_users_login_id", table_name="users")
    op.drop_table("users")
