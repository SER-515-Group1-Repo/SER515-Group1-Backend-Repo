from models import Base
import os
import sys
from os.path import abspath, dirname
from logging.config import fileConfig
from dotenv import load_dotenv
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
from database import Base

sys.path.append(os.getcwd())

load_dotenv()   # reads .env

target_metadata = Base.metadata
# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    SQLALCHEMY_DATABASE_URL = DATABASE_URL
else:
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")  # Default to localhost if not set
    DB_DATABASE = os.getenv("DB_DATABASE")
    SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://root:@{DB_HOST}/{DB_DATABASE}"

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
# Add the project root to the Python path
sys.path.insert(0, dirname(dirname(abspath(__file__))))

# Import your models' Base
target_metadata = Base.metadata

# Set the SQLAlchemy URL dynamically
# configparser does interpolation with '%' which breaks when passwords are
# URL-encoded and contain percent-escapes. Escape percent signs so config
# receives a literal percent (%%) and avoids ValueError: invalid interpolation.
safe_url = SQLALCHEMY_DATABASE_URL.replace('%', '%%') if SQLALCHEMY_DATABASE_URL else SQLALCHEMY_DATABASE_URL
config.set_main_option("sqlalchemy.url", safe_url)

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
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
