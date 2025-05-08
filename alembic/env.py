# alembic/env.py

import sys
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# --- Project Specific Imports ---

# Add the project root directory to the Python path
# This allows Alembic to find your 'app' module when run from the root directory
project_root = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import your SQLAlchemy Base object and all models associated with it
# This ensures Base.metadata is populated before being assigned to target_metadata
try:
    from app.core.database import Base # Adjust path if your Base is elsewhere
    from app.models import * # Imports all models from app/models/__init__.py
except ImportError as e:
    print(f"Error importing application modules in alembic/env.py: {e}")
    print("Please ensure the project structure is correct and dependencies are installed.")
    sys.exit(1) # Exit if core components can't be imported

# --- End Project Specific Imports ---


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    try:
        fileConfig(config.config_file_name)
    except Exception as e:
        print(f"Warning: Could not configure logging from {config.config_file_name}: {e}")


# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata

# Assign your application's Base metadata to target_metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # Get database URL from alembic.ini configuration section
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata, # Pass the metadata object for offline checks
        literal_binds=True, # Render SQL types literally for offline mode
        dialect_opts={"paramstyle": "named"}, # Standard dialect options
        # You might need to specify the schema for the version table if not 'public'
        # version_table_schema='your_schema',
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Create engine from configuration in alembic.ini
    # Pass the section name from the ini file
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.", # Prefix for sqlalchemy settings in ini file
        poolclass=pool.NullPool, # Use NullPool for migrations - avoids leaving connections open
    )

    # Use the engine to connect
    with connectable.connect() as connection:
        # Configure the context with the connection and metadata
        context.configure(
            connection=connection,
            target_metadata=target_metadata, # Pass the metadata object for online comparison
            # You might need to specify the schema for the version table if not 'public'
            # version_table_schema='your_schema',
            # If using multiple schemas, you might need:
            # include_schemas=True,
        )

        # Run migrations within a transaction
        with context.begin_transaction():
            context.run_migrations()


# Determine if running in offline or online mode and execute
if context.is_offline_mode():
    print("Running migrations in offline mode...")
    run_migrations_offline()
else:
    print("Running migrations in online mode...")
    run_migrations_online()

print("Migrations run complete.")