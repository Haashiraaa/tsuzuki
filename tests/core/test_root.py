from pathlib import Path

from tsuzuki.core.root import find_project_root, quiet_file_handler, resolve_root


def make_project(base: Path) -> Path:
    """A repo-like layout: <base>/tsuzuki/pyproject.toml and a same-named package folder."""
    project = base / "tsuzuki"
    package = project / "backend" / "src" / "tsuzuki" / "core"
    package.mkdir(parents=True)
    (project / "pyproject.toml").write_text("[project]\nname='tsuzuki'\n")
    return package


class TestResolveRoot:
    def test_explicit_folder_wins_over_everything(self, tmp_path: Path) -> None:
        start = make_project(tmp_path)
        root = resolve_root(
            tmp_path / "chosen", env={"TSUZUKI_HOME": str(tmp_path / "env")}, start=start
        )
        assert (root.path, root.source) == ((tmp_path / "chosen").resolve(), "--output")

    def test_environment_variable_comes_second(self, tmp_path: Path) -> None:
        start = make_project(tmp_path)
        root = resolve_root(None, env={"TSUZUKI_HOME": str(tmp_path / "env")}, start=start)
        assert (root.path, root.source) == ((tmp_path / "env").resolve(), "$TSUZUKI_HOME")

    def test_project_folder_comes_third(self, tmp_path: Path) -> None:
        start = make_project(tmp_path)
        root = resolve_root(None, env={}, start=start)
        assert (root.path, root.source) == (tmp_path / "tsuzuki", "project folder")

    def test_home_folder_is_the_last_resort(self, tmp_path: Path) -> None:
        nowhere = tmp_path / "elsewhere"
        nowhere.mkdir()
        root = resolve_root(None, env={}, start=nowhere, home=tmp_path / "home")
        assert (root.path, root.source) == (tmp_path / "home" / "tsuzuki", "home folder")

    def test_an_empty_environment_variable_is_ignored(self, tmp_path: Path) -> None:
        nowhere = tmp_path / "elsewhere"
        nowhere.mkdir()
        root = resolve_root(None, env={"TSUZUKI_HOME": ""}, start=nowhere, home=tmp_path)
        assert root.source == "home folder"


class TestRootPaths:
    def test_subfolders_and_database(self, tmp_path: Path) -> None:
        root = resolve_root(tmp_path, env={})
        assert root.downloads == tmp_path.resolve() / "Downloads"
        assert root.logs == tmp_path.resolve() / "logs"
        assert root.database == tmp_path.resolve() / "tsuzuki.db"


class TestFindProjectRoot:
    def test_skips_the_package_folder_with_the_same_name(self, tmp_path: Path) -> None:
        start = make_project(tmp_path)
        assert find_project_root(quiet_file_handler(), start) == tmp_path / "tsuzuki"

    def test_a_same_named_folder_without_the_marker_is_not_a_project(self, tmp_path: Path) -> None:
        lonely = tmp_path / "tsuzuki" / "sub"
        lonely.mkdir(parents=True)
        assert find_project_root(quiet_file_handler(), lonely) is None
