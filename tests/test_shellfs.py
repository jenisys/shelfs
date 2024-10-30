import os
from contextlib import contextmanager
from operator import itemgetter
from pathlib import Path
from shutil import rmtree
from typing import Optional

import pytest

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
    ensure_that_directory_of_file_exists(path)
    if contents is None:
        path.touch(exist_ok=True)
    else:
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

    # -- OPERATION: listdir (aka: "ls")
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

    # -- OPERATION: makedirs
    def test_makedirs_if_directory_does_not_exist_with_one_level(self, tmp_path: Path) -> None:
        this_directory = tmp_path/"some_directory_401"
        ensure_that_directory_does_not_exist(this_directory)

        shellfs = ShellFileSystem()
        shellfs.makedirs(this_directory)
        assert this_directory.is_dir()
        assert shellfs.isdir(this_directory)

    def test_makedirs_if_directory_does_not_exist_with_many_levels(self, tmp_path: Path) -> None:
        this_base_directory = tmp_path/"some_directory_402"
        this_directory = this_base_directory/"subdir_1/subdir_2"
        ensure_that_directory_does_not_exist(this_base_directory)

        shellfs = ShellFileSystem()
        shellfs.makedirs(this_directory)
        assert this_directory.is_dir()
        assert shellfs.isdir(this_directory)

    def test_makedirs_raises_error_if_directory_exists(self, tmp_path: Path) -> None:
        this_directory = tmp_path/"some_directory_403"
        ensure_that_directory_exists(this_directory)

        shellfs = ShellFileSystem()
        with pytest.raises(FileExistsError):
            shellfs.makedirs(this_directory)

    def test_makedirs_if_directory_exists_with_exist_ok(self, tmp_path: Path) -> None:
        this_directory = tmp_path/"some_directory_403"
        ensure_that_directory_exists(this_directory)

        shellfs = ShellFileSystem()
        shellfs.makedirs(this_directory, exist_ok=True)
        assert this_directory.is_dir()
        assert shellfs.isdir(this_directory)

    def test_makedirs_raises_error_if_directory_exists_as_file(self, tmp_path: Path) -> None:
        this_directory_isa_file = tmp_path/"some_file_404.txt"
        ensure_that_file_exists(this_directory_isa_file)
        shellfs = ShellFileSystem()

        # -- CASE 1: exist_ok = False
        with pytest.raises(FileExistsError):
            shellfs.makedirs(this_directory_isa_file)

        # -- CASE 2:
        with pytest.raises(FileExistsError):
            shellfs.makedirs(this_directory_isa_file, exist_ok=True)

    # -- OPERATION: mkdir
    def test_mkdir_if_directory_does_not_exist(self, tmp_path: Path) -> None:
        this_directory = tmp_path/"some_directory_501"
        ensure_that_directory_does_not_exist(this_directory)

        shellfs = ShellFileSystem()
        shellfs.mkdir(this_directory)
        assert this_directory.is_dir()
        assert shellfs.isdir(this_directory)

    def test_mkdir_with_create_parents(self, tmp_path: Path) -> None:
        this_base_directory = tmp_path/"some_directory_502"
        this_directory = this_base_directory/"subdir_1/subdir_2"
        ensure_that_directory_does_not_exist(this_base_directory)

        shellfs = ShellFileSystem()
        shellfs.mkdir(this_directory, create_parents=True)
        assert this_directory.is_dir()
        assert shellfs.isdir(this_directory)

    def test_mkdir_if_directory_exists(self, tmp_path: Path) -> None:
        this_directory = tmp_path/"some_directory_503"
        ensure_that_directory_exists(this_directory)

        shellfs = ShellFileSystem()
        shellfs.mkdir(this_directory)
        assert this_directory.is_dir()
        assert shellfs.isdir(this_directory)

    def test_mkdir_without_create_parents_raises_error_if_directory_exists(self, tmp_path: Path) -> None:
        this_directory = tmp_path/"some_directory_503"
        ensure_that_directory_exists(this_directory)

        shellfs = ShellFileSystem()
        with pytest.raises(FileExistsError):
            shellfs.mkdir(this_directory, create_parents=False)

    def test_mkdir_raises_error_if_directory_exists_as_file(self, tmp_path: Path) -> None:
        this_directory_as_file = tmp_path/"some_file_504.txt"
        ensure_that_file_exists(this_directory_as_file)

        shellfs = ShellFileSystem()
        with pytest.raises(FileExistsError):
            shellfs.mkdir(this_directory_as_file)

    def test_mkdir_without_create_parents_raises_error_if_directory_exists_as_file(self, tmp_path: Path) -> None:
        this_directory_as_file = tmp_path/"some_file_504.txt"
        ensure_that_file_exists(this_directory_as_file)

        shellfs = ShellFileSystem()
        with pytest.raises(FileExistsError):
            shellfs.mkdir(this_directory_as_file, create_parents=False)

    # -- OPERATION: rmdir
    def test_rmdir_if_empty_directory_exists(self, tmp_path: Path) -> None:
        this_directory = tmp_path/"some_directory_601"
        ensure_that_directory_exists(this_directory)

        shellfs = ShellFileSystem()
        shellfs.rmdir(this_directory)
        assert this_directory.exists() is False
        assert shellfs.exists(this_directory) is False
        assert shellfs.isdir(this_directory) is False

    def test_rmdir_raises_error_if_nonempty_directory_exists(self, tmp_path: Path) -> None:
        this_directory = tmp_path/"some_directory_601"
        this_file = this_directory/".keepme"
        ensure_that_file_exists(this_file)
        assert this_directory.exists() is True
        assert this_directory.is_dir() is True

        shellfs = ShellFileSystem()
        with pytest.raises(PermissionError):
            shellfs.rmdir(this_directory)

        # -- POST-CONDITIONS:
        assert this_directory.exists() is True
        assert shellfs.exists(this_directory) is True
        assert shellfs.isdir(this_directory) is True

    def test_rmdir_if_directory_does_not_exist(self, tmp_path: Path) -> None:
        this_directory = tmp_path/"some_directory_602"
        ensure_that_directory_does_not_exist(this_directory)

        shellfs = ShellFileSystem()
        with pytest.raises(FileNotFoundError):
            shellfs.rmdir(this_directory)

        # -- POST-CONDITIONS:
        assert this_directory.exists() is False
        assert shellfs.exists(this_directory) is False
        assert shellfs.isdir(this_directory) is False

    # -- OPERATION: rmtree
    def test_rmtree_if_directory_exists(self, tmp_path: Path) -> None:
        this_directory = tmp_path/"some_directory_701"
        this_file = this_directory/".keepme"
        ensure_that_file_exists(this_file)
        assert this_directory.is_dir() is True

        shellfs = ShellFileSystem()
        shellfs.rmtree(this_directory)
        assert this_directory.exists() is False
        assert shellfs.exists(this_directory) is False
        assert shellfs.isdir(this_directory) is False

    def test_rmtree_if_directory_does_not_exist(self, tmp_path: Path) -> None:
        this_directory = tmp_path/"MISSING_DIRECTORY"
        ensure_that_directory_does_not_exist(this_directory)

        shellfs = ShellFileSystem()
        shellfs.rmtree(this_directory)
        assert this_directory.exists() is False
        assert shellfs.exists(this_directory) is False
        assert shellfs.isdir(this_directory) is False

    def test_rmtree_raises_error_if_directory_isa_file(self, tmp_path: Path) -> None:
        this_directory_as_file = tmp_path/"some_file_702.txt"
        ensure_that_file_exists(this_directory_as_file)

        shellfs = ShellFileSystem()
        with pytest.raises(NotADirectoryError):
            shellfs.rmtree(this_directory_as_file)

        # -- POST-CONDITIONS:
        assert this_directory_as_file.exists() is True
        assert shellfs.exists(this_directory_as_file) is True
        assert shellfs.isfile(this_directory_as_file) is True

    # -- OPERATION: rm-recursive
    def test_rm_recursive_if_non_empty_directory_exists(self, tmp_path: Path) -> None:
        this_directory = tmp_path/"some_directory_801"
        this_file = this_directory/".keepme"
        ensure_that_file_exists(this_file)
        assert this_directory.is_dir() is True

        shellfs = ShellFileSystem()
        shellfs.rm(this_directory, recursive=True)

        # -- POST-CONDITIONS:
        assert this_directory.exists() is False
        assert shellfs.exists(this_directory) is False
        assert this_file.exists() is False
        assert shellfs.exists(this_file) is False

    def test_rm_recursive_ignores_if_path_does_not_exist(self, tmp_path: Path) -> None:
        this_path = tmp_path/"MISSING_PATH"
        ensure_that_directory_does_not_exist(this_path)
        ensure_that_file_does_not_exist(this_path)

        shellfs = ShellFileSystem()
        shellfs.rm(this_path, recursive=True)

        # -- POST-CONDITIONS:
        assert this_path.exists() is False
        assert shellfs.exists(this_path) is False

    def test_rm_recursive_if__file_exists(self, tmp_path: Path) -> None:
        this_file = tmp_path/"some_file_802.txt"
        ensure_that_file_exists(this_file)

        shellfs = ShellFileSystem()
        shellfs.rm(this_file, recursive=True)

        # -- POST-CONDITIONS:
        assert this_file.exists() is False
        assert shellfs.exists(this_file) is False
        assert shellfs.isfile(this_file) is False

    def test_rm_recursive_with_many_paths(self, tmp_path: Path) -> None:
        # -- TEST REQUIRES: Non-existing paths are ignored.
        this_directory = tmp_path/"some_directory_803"
        this_file = this_directory/".keepme"
        ensure_that_file_exists(this_file)
        assert this_directory.is_dir() is True

        shellfs = ShellFileSystem()
        this_paths = [this_directory, this_file]
        shellfs.rm(this_paths, recursive=True)

        # -- POST-CONDITIONS:
        assert this_directory.exists() is False
        assert shellfs.exists(this_directory) is False
        assert this_file.exists() is False
        assert shellfs.exists(this_file) is False
