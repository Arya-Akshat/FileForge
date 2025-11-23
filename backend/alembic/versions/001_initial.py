"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2025-11-23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # Create files table
    op.create_table('files',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('original_name', sa.String(), nullable=False),
        sa.Column('storage_bucket', sa.String(), nullable=False),
        sa.Column('storage_key', sa.String(), nullable=False),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('mime_type', sa.String(), nullable=True),
        sa.Column('status', sa.Enum('UPLOADING', 'UPLOADED', 'PROCESSING', 'READY', 'FAILED', name='filestatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_processed_output', sa.Boolean(), default=False),
        sa.Column('parent_file_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['parent_file_id'], ['files.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create file_metadata table
    op.create_table('file_metadata',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('file_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('exif_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('video_info', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('ai_tags', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('custom_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['file_id'], ['files.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('file_id')
    )

    # Create pipelines table
    op.create_table('pipelines',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('file_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('steps', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['file_id'], ['files.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create jobs table
    op.create_table('jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('file_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('pipeline_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('type', sa.Enum('THUMBNAIL', 'IMAGE_CONVERT', 'IMAGE_COMPRESS', 'VIDEO_THUMBNAIL', 'VIDEO_PREVIEW', 'VIDEO_CONVERT', 'COMPRESS', 'METADATA', 'ENCRYPT', 'DECRYPT', 'VIRUS_SCAN', 'AI_TAG', name='jobtype'), nullable=False),
        sa.Column('status', sa.Enum('QUEUED', 'RUNNING', 'COMPLETED', 'FAILED', name='jobstatus'), default='QUEUED'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('result_file_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('params', postgresql.JSON(astext_type=sa.Text()), default={}),
        sa.ForeignKeyConstraint(['file_id'], ['files.id'], ),
        sa.ForeignKeyConstraint(['pipeline_id'], ['pipelines.id'], ),
        sa.ForeignKeyConstraint(['result_file_id'], ['files.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('jobs')
    op.drop_table('pipelines')
    op.drop_table('file_metadata')
    op.drop_table('files')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
