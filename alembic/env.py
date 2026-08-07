# Minimal Alembic env placeholder. Configure DB connection and target_metadata when ready.
from logging.config import fileConfig

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
fileConfig(config.config_file_name)

# TODO: import your SQLAlchemy models' metadata as target_metadata
target_metadata = None

def run_migrations_offline():
    context.configure(url=config.get_main_option("sqlalchemy.url"))
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    # Implement when ready
    pass

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
