from alembic import context
from sqlalchemy import engine_from_config, create_engine, pool
from logging.config import fileConfig
import os
import sys

# This is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers defined in the .ini file.
fileConfig(config.config_file_name)

# Optional: Use environment variable instead of hardcoding DB URL
db_url = os.getenv("DB_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

# If you have models, set this to their Base.metadata
target_metadata = None  # Or something like `Base.metadata` if using ORM

def run_migrations_offline():
    """Run migrations in 'offline' mode (SQL script output)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Run migrations in 'online' mode (connect to DB and apply)."""
    connectable = create_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

# Choose offline or online mode based on how Alembic is invoked
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
