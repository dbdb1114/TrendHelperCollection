# Minimal Alembic env.py (manual template)
import os
from alembic import context
from sqlalchemy import create_engine
from logging.config import fileConfig

# If you later generate a proper alembic.ini, fileConfig can read it
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import your Base metadata here when ready:
# from core.models import Base
target_metadata = None  # replace with Base.metadata when models are ready

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/trendhelper")

def run_migrations_offline():
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = create_engine(DATABASE_URL, pool_pre_ping=True)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

