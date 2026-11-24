# pyright: basic
"""Alembic's entry point. It runs migrations on one SQLite file and nothing else.

SQLite can roll back schema changes, but Python's sqlite3 module quietly commits before them.
The two listeners below turn that off and begin each migration's transaction by hand, so a
migration that fails half way leaves nothing behind.
"""

from alembic import context
from sqlalchemy import create_engine, event
from sqlalchemy.pool import NullPool

config = context.config

if context.is_offline_mode():
    raise RuntimeError("Offline (SQL script) mode is not supported; run the migration directly.")

engine = create_engine(config.get_main_option("sqlalchemy.url") or "", poolclass=NullPool)


@event.listens_for(engine, "connect")
def take_over_transactions(dbapi_connection, _record):  # type: ignore[no-untyped-def]
    dbapi_connection.isolation_level = None


@event.listens_for(engine, "begin")
def begin_explicitly(connection):  # type: ignore[no-untyped-def]
    connection.exec_driver_sql("BEGIN")


with engine.connect() as connection:
    context.configure(
        connection=connection,
        target_metadata=None,  # no ORM models; migrations are written by hand
        transactional_ddl=True,
        transaction_per_migration=True,
    )
    with context.begin_transaction():
        context.run_migrations()
