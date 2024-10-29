import os
from contextlib import contextmanager
from operator import itemgetter
from pathlib import Path
from shutil import rmtree
from typing import Optional

# NOT_NEEDED: import pytest

from shellfs.shell import PathEntry, PathType
from shellfs.spec import ShellFileSystem


# -----------------------------------------------------------------------------
# TEST SUPPORT
# -----------------------------------------------------------------------------
DEFAULT_TEXT_PATTERN = "0123456789ABCDEF\n"


# -----------------------------------------------------------------------------
# TEST SUPPORT
# -----------------------------------------------------------------------------
@contextmanager
def chdir(directory):
    # -- PROVIDED-BY: contextlib.chdir() since Python 3.11
    this_directory = Path(directory).absolute()
    if not this_directory.is_dir():
        raise FileNotFoundError(directory)

    initial_directory = Path.cwd()
    try:
        os.chdir(this_directory)
        yield this_directory
    finally:
        os.chdir(initial_directory)


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


def ensure_that_many_files_exist_with_contents(files_with_contents):
    for filename, contents in files_with_contents:
        filename_path = Path(filename)
        ensure_that_directory_of_file_exists(filename_path)
        filename_path.write_text(contents)


def make_text(size, pattern: Optional[str] = None):
    """Generate text of the provided size."""
    pattern = pattern or DEFAULT_TEXT_PATTERN
    factor = 1 + (size // len(pattern))
    text = pattern * factor
    if len(text) > size:
        text = text[:size]
    return text


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

    def test_isfile_returns_true_with_existing_file(self, tmp_path: Path) -> None:
        this_file_path = tmp_path/"some_file_101.txt"
        ensure_that_file_exists(this_file_path)

        shellfs = ShellFileSystem()
        actual_outcome = shellfs.isfile(this_file_path)
        assert actual_outcome is True

    def test_isfile_returns_false_with_nonexisting_file(self, tmp_path: Path) -> None:
        this_file_path = tmp_path/"MISSING_FILE.txt"
        ensure_that_file_does_not_exist(this_file_path)

        shellfs = ShellFileSystem()
        actual_outcome = shellfs.isfile(this_file_path)
        assert actual_outcome is False

    def test_isfile_returns_false_with_existing_directory(self, tmp_path: Path) -> None:
        this_directory_path = tmp_path/"some_directory"
        ensure_that_directory_exists(this_directory_path)

        shellfs = ShellFileSystem()
        actual_outcome = shellfs.isfile(this_directory_path)
        assert actual_outcome is False


    def test_isdir_returns_true_with_existing_directory(self, tmp_path: Path) -> None:
        this_directory_path = tmp_path/"some_directory_102"
        ensure_that_directory_exists(this_directory_path)

        shellfs = ShellFileSystem()
        actual_outcome = shellfs.isdir(this_directory_path)
        assert actual_outcome is True

    def test_isdir_returns_false_with_nonexisting_directory(self, tmp_path: Path) -> None:
        this_directory_path = tmp_path/"MISSING_DIRECTORY"
        ensure_that_directory_does_not_exist(this_directory_path)

        shellfs = ShellFileSystem()
        actual_outcome = shellfs.isdir(this_directory_path)
        assert actual_outcome is False

    def test_isdir_returns_false_with_existing_file(self, tmp_path: Path) -> None:
        this_file_path = tmp_path/"some_file_131.txt"
        ensure_that_file_exists(this_file_path)

        shellfs = ShellFileSystem()
        actual_outcome = shellfs.isdir(this_file_path)
        assert actual_outcome is False

    def test_ls_returns_directory_entries(self, tmp_path: Path) -> None:
        this_directory = tmp_path/"some_directory_401"
        files = [
            (this_directory/"EMPTY_FILE.txt", ""),
            (this_directory/"sub_directory/.keepme", ""),
            (this_directory/"some_file.txt", make_text(size=123)),
        ]
        ensure_that_many_files_exist_with_contents(files)

        shellfs = ShellFileSystem()
        with chdir(tmp_path):
            this_directory_relative_to_root = this_directory.relative_to(tmp_path)
            path_entries = shellfs.ls(this_directory_relative_to_root)

            expected = [
                PathEntry(name="sub_directory", type=PathType.DIRECTORY, size=None),
                PathEntry(name="EMPTY_FILE.txt", type=PathType.FILE, size=0),
                PathEntry(name="some_file.txt", type=PathType.FILE, size=123),
            ]
            path_entries.sort(key=itemgetter("type"))  # -- NORMALIZE ORDERING.
            this_directory_size = path_entries[0]["size"]
            expected[0]["size"] = this_directory_size
            assert path_entries[0]["type"] is PathType.DIRECTORY
            assert path_entries == expected

    def test_ls_without_detail_returns_entry_names(self, tmp_path: Path) -> None:
        this_directory = tmp_path/"some_directory_401"
        files = [
            (this_directory/"EMPTY_FILE.txt", ""),
            (this_directory/"sub_directory/.keepme", ""),
            (this_directory/"some_file.txt", make_text(size=123)),
        ]
        ensure_that_many_files_exist_with_contents(files)

        shellfs = ShellFileSystem()
        with chdir(tmp_path):
            this_directory_relative_to_root = this_directory.relative_to(tmp_path)
            entry_names = shellfs.ls(this_directory_relative_to_root, detail=False)

            expected = [
                "EMPTY_FILE.txt",
                "some_file.txt",
                "sub_directory",
            ]
            entry_names.sort()  # -- NORMALIZE ORDERING.
            assert entry_names == expected
