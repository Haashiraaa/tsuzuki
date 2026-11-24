import shutil
import sqlite3
from pathlib import Path

import pytest

from tsuzuki.core.errors import StorageError
from tsuzuki.storage.database import open_database, prepare_database
from tsuzuki.storage.migrate import SCRIPTS, current_revision, head_revision, migrate


def tables(path: Path) -> set[str]:
    conn = sqlite3.connect(path)
    try:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    finally:
        conn.close()
    return {row[0] for row in rows}


def scripts_with(tmp_path: Path, *revisions: tuple[str, str | None, list[str]]) -> Path:
    """A throwaway migrations folder: Tsuzuki's own env.py plus the given revisions, each as
    ``(id, previous id, SQL statements)``."""
    folder = tmp_path / "scripts"
    (folder / "versions").mkdir(parents=True)
    shutil.copy(SCRIPTS / "env.py", folder / "env.py")
    for rev, previous, statements in revisions:
        body = "\n".join(f"    op.execute({sql!r})" for sql in statements)
        (folder / "versions" / f"{rev}_step.py").write_text(
            f"from alembic import op\nrevision = {rev!r}\ndown_revision = {previous!r}\n"
            f"branch_labels = None\ndepends_on = None\n\n"
            f"def upgrade() -> None:\n{body}\n\ndef downgrade() -> None:\n    pass\n"
        )
    return folder


def test_a_new_database_is_built_up_to_the_newest_version(tmp_path: Path) -> None:
    path = tmp_path / "new.db"
    assert migrate(path) == head_revision()
    assert {"series", "episodes", "alembic_version"} <= tables(path)


def test_migrating_twice_changes_nothing(tmp_path: Path) -> None:
    path = tmp_path / "twice.db"
    first = migrate(path)
    assert migrate(path) == first
    assert current_revision(path) == head_revision()


def test_a_database_from_a_newer_tsuzuki_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "future.db"
    migrate(path)
    conn = sqlite3.connect(path)
    conn.execute("UPDATE alembic_version SET version_num = '9999'")
    conn.commit()
    conn.close()
    with pytest.raises(StorageError, match="newer version"):
        migrate(path)


def test_each_step_is_applied_in_order(tmp_path: Path) -> None:
    scripts = scripts_with(
        tmp_path,
        ("0001", None, ["CREATE TABLE a (id INTEGER)"]),
        ("0002", "0001", ["CREATE TABLE b (id INTEGER)"]),
    )
    path = tmp_path / "steps.db"
    assert migrate(path, scripts) == "0002"
    assert {"a", "b"} <= tables(path)


def test_a_failing_step_leaves_nothing_half_done(tmp_path: Path) -> None:
    scripts = scripts_with(
        tmp_path,
        ("0001", None, ["CREATE TABLE a (id INTEGER)"]),
        ("0002", "0001", ["CREATE TABLE b (id INTEGER)", "THIS IS NOT SQL"]),
    )
    path = tmp_path / "broken.db"
    with pytest.raises(StorageError):
        migrate(path, scripts)
    assert current_revision(path) == "0001"
    assert "a" in tables(path)
    assert "b" not in tables(path)


def test_a_fixed_step_is_applied_on_the_next_start(tmp_path: Path) -> None:
    path = tmp_path / "retry.db"
    broken = scripts_with(
        tmp_path / "x",
        ("0001", None, ["CREATE TABLE a (id INTEGER)"]),
        ("0002", "0001", ["NOT SQL"]),
    )
    with pytest.raises(StorageError):
        migrate(path, broken)
    fixed = scripts_with(
        tmp_path / "y",
        ("0001", None, ["CREATE TABLE a (id INTEGER)"]),
        ("0002", "0001", ["CREATE TABLE b (id INTEGER)"]),
    )
    assert migrate(path, fixed) == "0002"


def test_paths_with_odd_characters_work(tmp_path: Path) -> None:
    folder = tmp_path / "my 100% anime"
    path = folder / "t.db"
    prepare_database(path)
    assert "series" in tables(path)


def test_open_database_creates_the_folder_and_connects(tmp_path: Path) -> None:
    path = tmp_path / "deep" / "er" / "t.db"
    conn = open_database(path)
    try:
        assert conn.execute("SELECT COUNT(*) FROM series").fetchone()[0] == 0
    finally:
        conn.close()


def test_an_in_memory_database_is_refused_with_a_clear_message() -> None:
    with pytest.raises(StorageError, match="in-memory"):
        prepare_database(":memory:")
