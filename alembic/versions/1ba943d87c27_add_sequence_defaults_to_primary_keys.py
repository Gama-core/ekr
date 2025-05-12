"""add_sequence_defaults_to_primary_keys

Revision ID: 1ba943d87c27
Revises: cd9e56a363dd
Create Date: 2025-05-12 17:23:37.466245

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1ba943d87c27'
down_revision: Union[str, None] = 'cd9e56a363dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# List of tables whose 'id' primary key needs an auto-incrementing default
TABLES_TO_UPDATE = [
    'app_user',
    'document_type',
    'note_type',
    'document',
    'communication',
    'link',
    'note',
]

def upgrade() -> None:
    """Applies the sequence-based defaults to ID columns."""
    print("Applying sequence defaults to primary key columns...")
    for table_name in TABLES_TO_UPDATE:
        sequence_name = f"{table_name}_id_seq"
        print(f"  Processing table: {table_name}")

        # 1. Create the sequence if it doesn't already exist
        print(f"    Creating sequence (if not exists): {sequence_name}")
        op.execute(f"CREATE SEQUENCE IF NOT EXISTS {sequence_name}")

        # 2. Alter the 'id' column to use the sequence for its default value
        print(f"    Setting default for {table_name}.id to nextval('{sequence_name}')")
        op.alter_column(
            table_name=table_name,
            column_name='id',
            server_default=sa.text(f"nextval('{sequence_name}'::regclass)"),
            existing_type=sa.BigInteger(), # Specify existing type for safety
            existing_nullable=False       # Specify existing nullability for safety
        )

        # 3. Make the sequence owned by the column (best practice)
        print(f"    Associating sequence {sequence_name} with {table_name}.id")
        op.execute(f"ALTER SEQUENCE {sequence_name} OWNED BY {table_name}.id")

    print("Sequence defaults applied successfully.")


def downgrade() -> None:
    """Removes the sequence-based defaults from ID columns."""
    print("Removing sequence defaults from primary key columns...")
    for table_name in TABLES_TO_UPDATE:
        sequence_name = f"{table_name}_id_seq"
        print(f"  Processing table: {table_name}")

        # 1. Remove the server default from the 'id' column
        print(f"    Removing default from {table_name}.id")
        op.alter_column(
            table_name=table_name,
            column_name='id',
            server_default=None, # Set default back to None
            existing_type=sa.BigInteger(),
            existing_nullable=False
        )

        # 2. Drop the sequence (it might have been created by this migration)
        # Note: If the sequence existed before this migration, this might be undesired.
        # However, 'OWNED BY' should handle dropping if the table/column is dropped later.
        print(f"    Dropping sequence (if exists): {sequence_name}")
        op.execute(f"DROP SEQUENCE IF EXISTS {sequence_name}")

    print("Sequence defaults removed successfully.")