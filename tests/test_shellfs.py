from pathlib import Path
from shutil import rmtree
from typing import Optional

import pytest

from shellfs.spec import ShellFileSystem


# -----------------------------------------------------------------------------
# TEST SUPPORT
# -----------------------------------------------------------------------------
def ensure_that_directory_exists(directory: Path) -> Path:
    if not directory.is_dir():
        directory.mkdir(parents=True)
    assert directory.is_dir()
    return directory


def ensure_that_directory_does_not_exist(directory: Path) -> Path:
    if directory.is_dir():
        rmtree(directory, ignore_errors=True)
    assert not directory.exists()
    return directory


def ensure_that_directory_of_file_exists(file_path: Path) -> Path:
    this_directory = file_path.parent
    return ensure_that_directory_exists(this_directory)


def ensure_that_file_exists(path: Path, contents: Optional[str] = None) -> Path:
    if contents is None:
        path.touch(exist_ok=True)
    else:
        ensure_that_directory_of_file_exists(path)
        path.write_text(contents)
    assert path.is_file()
    return path


def ensure_that_file_does_not_exist(path: Path) -> Path:
    if path.is_file():
        path.unlink()
    assert not path.exists()
    return path


# -----------------------------------------------------------------------------
# TESTSUITE
# -----------------------------------------------------------------------------
class TestShellFileSystem:
    """Testing shellfs filesystem with local filesystem."""

    def test_exists_returns_true_with_existing_file(self, tmp_path: Path) -> None:
        this_file_path = tmp_path/"some_file_101.txt"
        ensure_that_file_exists(this_file_path)

        shellfs = ShellFileSystem()
        actual_outcome = shellfs.exists(this_file_path)
        assert actual_outcome is True

    def test_exists_returns_false_with_nonexisting_file(self, tmp_path: Path) -> None:
        this_file_path = tmp_path/"MISSING_FILE.txt"
        ensure_that_file_does_not_exist(this_file_path)

        shellfs = ShellFileSystem()
        actual_outcome = shellfs.exists(this_file_path)
        assert actual_outcome is False

    def test_exists_returns_true_with_existing_directory(self, tmp_path: Path) -> None:
        this_directory_path = tmp_path/"some_directory_102"
        ensure_that_directory_exists(this_directory_path)

        shellfs = ShellFileSystem()
        actual_outcome = shellfs.exists(this_directory_path)
        assert actual_outcome is True

    def test_exists_returns_false_with_nonexisting_directory(self, tmp_path: Path) -> None:
        this_directory_path = tmp_path/"MISSING_DIRECTORY"
        ensure_that_directory_does_not_exist(this_directory_path)

        shellfs = ShellFileSystem()
        actual_outcome = shellfs.exists(this_directory_path)
        assert actual_outcome is False
