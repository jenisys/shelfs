"""
Provides a filesystem abstraction based on shell commands.
"""

from typing import Optional, ParamSpec

from fsspec.spec import AbstractFileSystem

from .shell import PathType
from .shell.core import FileSystemProtocol, ShellProtocol, ShellFactory

# -----------------------------------------------------------------------------
# TYPE SUPPORT
# -----------------------------------------------------------------------------
P = ParamSpec("P")


# -----------------------------------------------------------------------------
# FILESYSTEM SUPPORT
# -----------------------------------------------------------------------------
class ShellFileSystem(AbstractFileSystem):
    def __init__(self, shell: Optional[ShellProtocol] = None, **kwargs: P.kwargs) -> None:
        if shell is None:
            shell = ShellFactory.make_local_shell()

        super().__init__(**kwargs)
        self.shell = shell
        self.fs_protocol = FileSystemProtocol(shell)

    # -- IMPLEMENT INTERFACE FOR: AbstractFileSystem
    @property
    def fsid(self):
        return "shellfs"

    def info(self, path, **kwargs):
        path_entry = self.fs_protocol.info(path)
        path_type = path_entry["type"]
        if path_type is PathType.NOT_FOUND:
            raise FileNotFoundError(path)
        return path_entry

    def ls(self, path, detail=True, **kwargs):
        """List objects at path.

        This should include subdirectories and files at that location. The
        difference between a file and a directory must be clear when details
        are requested.

        The specific keys, or perhaps a FileInfo class, or similar, is TBD,
        but must be consistent across implementations.
        Must include:

        - full path to the entry (without protocol)
        - size of the entry, in bytes. If the value cannot be determined, will
          be ``None``.
        - type of entry, "file", "directory" or other

        Additional information
        may be present, appropriate to the file-system, e.g., generation,
        checksum, etc.

        May use refresh=True|False to allow use of self._ls_from_cache to
        check for a saved listing and avoid calling the backend. This would be
        common where listing may be expensive.

        Parameters
        ----------
        path: str
        detail: bool
            if True, gives a list of dictionaries, where each is the same as
            the result of ``info(path)``. If False, gives a list of paths
            (str).
        kwargs: may have additional backend-specific options, such as version
            information

        Returns
        -------
        List of strings if detail is False, or list of directory information
        dicts if detail is True.
        """
        path = self._strip_protocol(path)
        path_entry = self.info(path)
        if path_entry["type"] is PathType.NOT_FOUND:
            raise FileNotFoundError(path)

        if path_entry["type"] == PathType.DIRECTORY:
            path_entries = self.fs_protocol.listdir(path)
        else:
            assert path_entry["type"] == PathType.FILE
            path_entries = [path_entry]

        if not detail:
            # -- NAME-ONLY:
            return [entry["name"] for entry in path_entries]
        # -- OTHERWISE: Provide complete info for each entry.
        return path_entries

    def mkdir(self, path, create_parents=True, **kwargs):
        """
        Create directory entry at path

        For systems that don't have true directories, may create an for
        this instance only and not touch the real filesystem

        Parameters
        ----------
        path: str
            location
        create_parents: bool
            if True, this is equivalent to ``makedirs``
        kwargs:
            may be permissions, etc.
        """
        path = self._strip_protocol(path)
        if create_parents:
            self.makedirs(path, exist_ok=True)
            return

        # -- OTHERWISE:
        # NOTE: Not 100% correct -- DO NOT CARE IF EXISTS or NOT.
        self.fs_protocol.mkdir(path)

    def makedirs(self, path, exist_ok=False):
        """Recursively make directories

        Creates directory at path and any intervening required directories.
        Raises exception if, for instance, the path already exists but is a
        file.

        Parameters
        ----------
        path: str
            leaf directory name
        exist_ok: bool (False)
            If False, will error if the target already exists
        """
        self.fs_protocol.makedirs(path)

    def rmdir(self, path):
        """Remove a directory, if empty"""
        # -- NOTE: Not 100% correct -- Removes even non-emptry directories.
        self.fs_protocol.rmtree(path)

    # TODO: Check if needed.
    def exists(self, path, **kwargs):
        return self.fs_protocol.exists(path)

    def touch(self, path, truncate=True, **kwargs):
        """Create empty file, or update timestamp

        Parameters
        ----------
        path: str
            file location
        truncate: bool
            If True, always set file size to 0; if False, update timestamp and
            leave file unchanged, if backend allows this
        """
        if truncate and self.isfile(path):
            self.rm_file(path)

        # -- NORMAL-CASE:
        self.fs_protocol.touch(path)

    def cp_file(self, path1, path2, **kwargs):
        self.fs_protocol.copy_file(path1, path2, **kwargs)

    def rm_file(self, path):
        """Delete a file (overridden from base-class)."""
        self.fs_protocol.remove(path)
