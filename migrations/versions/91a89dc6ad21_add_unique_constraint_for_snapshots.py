"""add unique constraint for snapshots

Revision ID: 91a89dc6ad21
Revises: fefc8e82a7b3
Create Date: 2025-10-08 16:46:52.495622

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '91a89dc6ad21'
down_revision = 'fefc8e82a7b3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Remove existing duplicates before adding unique constraint
    op.execute("""
        DELETE FROM video_metrics_snapshot
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM video_metrics_snapshot
            GROUP BY video_id, captured_at
        )
    """)

    # Drop existing non-unique index
    op.drop_index('idx_video_metrics_video_captured', table_name='video_metrics_snapshot')

    # Create unique index
    op.create_index('idx_video_metrics_video_captured_unique',
                    'video_metrics_snapshot',
                    ['video_id', 'captured_at'],
                    unique=True)


def downgrade() -> None:
    # Recreate non-unique index
    op.drop_index('idx_video_metrics_video_captured_unique', table_name='video_metrics_snapshot')
    op.create_index('idx_video_metrics_video_captured',
                    'video_metrics_snapshot',
                    ['video_id', 'captured_at'],
                    unique=False)