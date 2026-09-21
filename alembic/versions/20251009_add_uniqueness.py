from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "make_task_id_unique"
down_revision = "add_updated_at_column"
branch_labels = None
depends_on = None


def upgrade():
    # 1) Deduplicate existing rows: keep the newest per task_id by created_at, then updated_at
    #    We delete by ctid to avoid needing a surrogate key.
    op.execute("""
        WITH ranked AS (
            SELECT
                ctid,
                ROW_NUMBER() OVER (
                    PARTITION BY task_id
                    ORDER BY created_at DESC NULLS LAST,
                             updated_at DESC NULLS LAST,
                             ctid DESC
                ) AS rn
            FROM pii_scanner.task_status
        )
        DELETE FROM pii_scanner.task_status t
        USING ranked r
        WHERE t.ctid = r.ctid
          AND r.rn > 1;
    """)

    # 2) Add a UNIQUE constraint on task_id
    op.create_unique_constraint(
        constraint_name="uq_task_status_task_id",
        table_name="task_status",
        columns=["task_id"],
        schema="pii_scanner",
    )


def downgrade():
    # Drop the UNIQUE constraint
    op.drop_constraint(
        "uq_task_status_task_id",
        "task_status",
        type_="unique",
        schema="pii_scanner",
    )
