"""Initial GameTracker schema."""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("username", sa.String(40), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
    op.create_index("ix_auth_sessions_token_hash", "auth_sessions", ["token_hash"], unique=True)
    op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"])

    op.create_table(
        "steam_openid_nonces",
        sa.Column("nonce_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_steam_openid_nonces_user_id", "steam_openid_nonces", ["user_id"])
    op.create_index("ix_steam_openid_nonces_expires_at", "steam_openid_nonces", ["expires_at"])

    op.create_table(
        "games",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("cover_url", sa.String(1000), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("developer", sa.String(160), nullable=True),
        sa.Column("publisher", sa.String(160), nullable=True),
        sa.Column("release_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_games_name", "games", ["name"])

    op.create_table(
        "user_games",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("game_id", sa.String(36), sa.ForeignKey("games.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(80), nullable=False),
        sa.Column("genre", sa.String(80), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("favorite", sa.Boolean(), nullable=False),
        sa.Column("tags", sa.Text(), nullable=False),
        sa.Column("personal_notes", sa.Text(), nullable=True),
        sa.Column("cover_override_url", sa.String(1000), nullable=True),
        sa.Column("external_game_id", sa.String(100), nullable=True),
        sa.Column("imported_playtime_minutes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "game_id", "platform", name="uq_user_game_platform"),
        sa.UniqueConstraint("user_id", "external_game_id", name="uq_user_external_game"),
        sa.CheckConstraint("rating IS NULL OR (rating >= 0 AND rating <= 10)", name="ck_rating_0_10"),
    )
    for column in ("user_id", "game_id", "genre", "status", "favorite", "external_game_id"):
        op.create_index(f"ix_user_games_{column}", "user_games", [column])

    op.create_table(
        "gaming_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_game_id", sa.String(36), sa.ForeignKey("user_games.id", ondelete="CASCADE"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paused_seconds", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("duration_seconds >= 0", name="ck_session_duration_nonnegative"),
    )
    for column in ("user_id", "user_game_id", "started_at"):
        op.create_index(f"ix_gaming_sessions_{column}", "gaming_sessions", [column])
    op.create_index("ix_session_user_start", "gaming_sessions", ["user_id", "started_at"])
    op.create_index("uq_active_gaming_session_user", "gaming_sessions", ["user_id"], unique=True,
                    sqlite_where=sa.text("state IN ('running', 'paused')"),
                    postgresql_where=sa.text("state IN ('running', 'paused')"))

    op.create_table(
        "goals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("goal_type", sa.String(30), nullable=False),
        sa.Column("target", sa.Float(), nullable=False),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("target > 0", name="ck_goal_target_positive"),
    )
    op.create_index("ix_goals_user_id", "goals", ["user_id"])
    op.create_index("ix_goals_status", "goals", ["status"])

    op.create_table(
        "goal_games",
        sa.Column("goal_id", sa.String(36), sa.ForeignKey("goals.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_game_id", sa.String(36), sa.ForeignKey("user_games.id", ondelete="CASCADE"), primary_key=True),
    )

    op.create_table(
        "platform_connections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("external_user_id", sa.String(120), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "provider", name="uq_user_provider"),
    )
    op.create_index("ix_platform_connections_user_id", "platform_connections", ["user_id"])

    op.create_table(
        "sync_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("connection_id", sa.String(36), sa.ForeignKey("platform_connections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("imported_count", sa.Integer(), nullable=False),
        sa.Column("total_count", sa.Integer(), nullable=False),
    )
    op.create_index("ix_sync_logs_connection_id", "sync_logs", ["connection_id"])

    op.create_table(
        "game_notes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_game_id", sa.String(36), sa.ForeignKey("user_games.id", ondelete="CASCADE"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_game_notes_user_game_id", "game_notes", ["user_game_id"], unique=True)

    op.create_table(
        "user_settings",
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("theme", sa.String(20), nullable=False),
        sa.Column("weekly_goal_hours", sa.Float(), nullable=False),
        sa.Column("timezone", sa.String(80), nullable=False),
        sa.Column("profile_public", sa.Boolean(), nullable=False),
    )


def downgrade() -> None:
    for table in ("user_settings", "game_notes", "sync_logs", "platform_connections", "goal_games", "goals",
                  "gaming_sessions", "user_games", "games", "steam_openid_nonces", "auth_sessions", "users"):
        op.drop_table(table)
