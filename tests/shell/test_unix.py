import pytest

from shellfs.shell.core import PathType
from shellfs.shell.unix import FSOpsCommand4Unix, UnixShell


class TestUnixShell:
    pass


class TestFSOpsCommand4Unix:
    """
    EXAMPLES::

        $ ls -ladFL -D "%Y-%m-%dT%H:%M:%S" this_repo_directory
        drwxr-xr-x  10 jens  staff  320 2024-10-27T12:19:03 this_repo_directory/
        # file_mask ?  user  group  size date               name (with type-suffix)

        $ ls -ladL -D "%Y-%m-%dT%H:%M:%S" this_repo_directory
        drwxr-xr-x  10 jens  staff  320 2024-10-27T12:19:03 this_repo_directory

        $ ls -ladL -D "%s" this_path
        drwxr-xr-x  10 jens  staff  320 1730027943 this_repo_directory
        -rw-r--r--  1 jens  staff  2879 1730025034 this_file.py
        -rw-r--r--  1 jens  staff  0 1730063602 __EMPTY_FILE.tag
        # file_mask ?  user  group  size utc-time-seconds  name (with type-suffix)

        $ ls -ladL -D "%s" this_path
        -rw-r--r--  1 alice  users  2879 Oct 27 11:30 this_file.txt
    """

    @pytest.mark.parametrize("text, expected", [
        ("-rw-r--r--", PathType.FILE),
        ("drwxr-xr-x", PathType.DIRECTORY),
        # -- SPECIAL FILES:
        ("brw-r--r--", PathType.FILE),
        ("crw-r--r--", PathType.FILE),
    ])
    def test_get_file_type_from(self, text, expected):
        path_type = FSOpsCommand4Unix.get_file_type_from(text)
        assert path_type is expected

    @pytest.mark.parametrize("path, output", [
        ("some_file.txt",  "-rw-r--r--  1 alice  users  4001 1730054321 some_file.txt"),
        ("dir1/nested_file.txt", "-rw-r--r--  1 bob  users  4002 1730054322 dir1/nested_file.txt"),
        ("iso_timestamp.txt", "-rw-r--r--  1 charly  users  4003 2024-10-27T12:19:03 iso_timestamp.txt"),
        ("many_words_timestamp.txt", "-rw-r--r--  1 doro  users  4004 Oct 27 11:30 many_words_timestamp.txt"),
    ])
    def test_make_result4info__with_file(self, path, output):
        entry = FSOpsCommand4Unix.make_result4info(path, output)
        this_file_size = entry["size"]
        assert entry["name"] == path
        assert entry["type"] == PathType.FILE
        assert 4001 <= this_file_size <= 4004

    @pytest.mark.parametrize("path, output", [
        ("empty_file.txt", "-rw-r--r--  1 emil    users     0 1730054000 empty_file.txt"),
    ])
    def test_make_result4info__with_empty_file(self, path, output):
        entry = FSOpsCommand4Unix.make_result4info(path, output)
        assert entry["name"] == path
        assert entry["type"] == PathType.FILE
        assert entry["size"] == 0

    @pytest.mark.parametrize("path, output", [
        ("some_directory",  "drw-r--r--  1 alice  users  121 1730054321 some_directory"),
        ("dir1/nested_dir", "drw-r--r--  1 bob    users  122 1730054322 dir1/nested_dir"),
        ("iso_timestamp.txt", "drw-r--r--  1 charly  users  123 2024-10-27T12:19:03 iso_timestamp.txt"),
        ("many_words_timestamp.txt", "drw-r--r--  1 doro  users  124 Oct 27 11:30 many_words_timestamp.txt"),
    ])
    def test_make_result4info__with_directory(self, path, output):
        entry = FSOpsCommand4Unix.make_result4info(path, output)
        this_directory_size = entry["size"]
        assert entry["name"] == path
        assert entry["type"] == PathType.DIRECTORY
        assert 121 <= this_directory_size <= 124

    @pytest.mark.parametrize("path, output", [
        ("UNKNOWN_FILE.txt", "ls: UNKNOWN_FILE.txt: No such file or directory"),
        ("UNKNOWN_DIRECTORY", "ls: UNKNOWN_DIRECTORY: No such file or directory"),
    ])
    def test_make_result4info__with_path_not_found(self, path, output):
        entry = FSOpsCommand4Unix.make_result4info(path, output)
        this_size = entry["size"]
        assert entry["name"] == path
        assert entry["type"] == PathType.NOT_FOUND
        assert this_size == 0
