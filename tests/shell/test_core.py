from typing import Any

import pytest

from shellfs.shell.core import PathType


class TestPathType:
    @pytest.mark.parametrize("path_type, other", [
        (PathType.FILE, PathType.FILE),
        (PathType.FILE, "file"),
        (PathType.FILE, "FILE"),
        (PathType.DIRECTORY, PathType.DIRECTORY),
        (PathType.DIRECTORY, "directory"),
        (PathType.DIRECTORY, "DIRECTORY"),
    ])
    def test_equal_returns_true_for_matching_other(self, path_type: PathType, other: Any):
        assert path_type == other

    @pytest.mark.parametrize("path_type, other", [
        (PathType.FILE, PathType.DIRECTORY),
        (PathType.FILE, "other"),
        (PathType.FILE, "directory"),
        (PathType.DIRECTORY, PathType.FILE),
        (PathType.DIRECTORY, "other"),
        (PathType.DIRECTORY, "file"),
    ])
    def test_equal_returns_false_for_mismatched_other(self, path_type: PathType, other: Any):
        assert (path_type == other) is False


