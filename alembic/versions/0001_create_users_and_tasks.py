"""Create users and tasks."""

import sqlalchemy as sa

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(254), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(60), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "USER",
                "ADMIN",
                name="user_role",
                native_enum=False,
                create_constraint=True,
                length=5,
            ),
            server_default="USER",
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "in_progress",
                "done",
                name="task_status",
                native_enum=False,
                create_constraint=True,
                length=11,
            ),
            server_default="pending",
            nullable=False,
        ),
        sa.Column(
            "priority",
            sa.Enum(
                "low",
                "medium",
                "high",
                name="task_priority",
                native_enum=False,
                create_constraint=True,
                length=6,
            ),
            server_default="medium",
            nullable=False,
        ),
        sa.Column("deadline", sa.DateTime(timezone=True)),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_tasks_user_id_id", "tasks", ["user_id", "id"])


def downgrade() -> None:
    op.drop_index("ix_tasks_user_id_id", table_name="tasks")
    op.drop_table("tasks")
    op.drop_table("users")
