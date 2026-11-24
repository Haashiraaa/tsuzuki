"""Schema versions, handled by Alembic.

The migrations are the files in ``migrations/versions/``. They are plain Python that run SQL,
written by hand (there are no ORM models to generate them from). Each runs in its own
transaction, so a failure leaves the database at the last good version. Never edit a migration
that has been released: add a new one.

To add one while developing, from the repository root::

    alembic revision --rev-id 0002 -m "add notes to episodes"

then fill in ``upgrade()`` in the new file. Alembic keeps the current version in a table named
``alembic_version``.
"""

from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from alembic.util.exc import CommandError
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool

from tsuzuki.core.errors import StorageError

SCRIPTS = Path(__file__).resolve().parent / "migrations"


def make_config(database: Path, scripts: Path = SCRIPTS) -> Config:
    config = Config()
    config.set_main_option("script_location", str(scripts))
    # The ini format treats % as special, so a path containing one has to be escaped.
    url = f"sqlite:///{database}".replace("%", "%%")
    config.set_main_option("sqlalchemy.url", url)
    return config


def head_revision(scripts: Path = SCRIPTS) -> str | None:
    """The newest version this copy of Tsuzuki knows."""
    return ScriptDirectory(str(scripts)).get_current_head()


def current_revision(database: Path) -> str | None:
    """The version the database file is at (None for a new, empty one)."""
    engine = create_engine(f"sqlite:///{database}", poolclass=NullPool)
    try:
        with engine.connect() as connection:
            return MigrationContext.configure(connection).get_current_revision()
    except SQLAlchemyError as exc:
        raise StorageError(f"Cannot read the database version of {database}: {exc}") from exc
    finally:
        engine.dispose()


def migrate(database: Path, scripts: Path = SCRIPTS) -> str | None:
    """Bring the database file up to the newest version. Returns the version it ends at."""
    try:
        command.upgrade(make_config(database, scripts), "head")
    except CommandError as exc:
        if "Can't locate revision" in str(exc):
            raise StorageError(
                f"{database} was made by a newer version of Tsuzuki. Update Tsuzuki, or use "
                "a different folder."
            ) from exc
        raise StorageError(f"Cannot upgrade the database {database}: {exc}") from exc
    except SQLAlchemyError as exc:
        raise StorageError(f"Cannot upgrade the database {database}: {exc}") from exc
    return current_revision(database)
