"""
Provides a filesystem abstraction based on shell commands.
"""

import os
from typing import Optional, ParamSpec

from fsspec.spec import AbstractFileSystem

from .shell import PathType
from .shell.core import FileSystemProtocol, ShellProtocol, ShellFactory


P = ParamSpec("P")


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

    # def info_example(self, path, **kwargs):
    #     if isinstance(path, os.DirEntry):
    #         # scandir DirEntry
    #         out = path.stat(follow_symlinks=False)
    #         link = path.is_symlink()
    #         if path.is_dir(follow_symlinks=False):
    #             t = "directory"
    #         elif path.is_file(follow_symlinks=False):
    #             t = "file"
    #         else:
    #             t = "other"
    #
    #         size = out.st_size
    #         if link:
    #             try:
    #                 out2 = path.stat(follow_symlinks=True)
    #                 size = out2.st_size
    #             except OSError:
    #                 size = 0
    #         path = self._strip_protocol(path.path)
    #     else:
    #         # str or path-like
    #         path = self._strip_protocol(path)
    #         out = os.stat(path, follow_symlinks=False)
    #         link = stat.S_ISLNK(out.st_mode)
    #         if link:
    #             out = os.stat(path, follow_symlinks=True)
    #         size = out.st_size
    #         if stat.S_ISDIR(out.st_mode):
    #             t = "directory"
    #         elif stat.S_ISREG(out.st_mode):
    #             t = "file"
    #         else:
    #             t = "other"
    #     result = {
    #         "name": path,
    #         "size": size,
    #         "type": t,
    #         "created": out.st_ctime,
    #         "islink": link,
    #     }
    #     for field in ["mode", "uid", "gid", "mtime", "ino", "nlink"]:
    #         result[field] = getattr(out, f"st_{field}")
    #     if link:
    #         result["destination"] = os.readlink(path)
    #     return result

    # def ls_example(self, path, detail=False, **kwargs):
    #     path = self._strip_protocol(path)
    #     info = self.info(path)
    #     if info["type"] == "directory":
    #         with os.scandir(path) as it:
    #             infos = [self.info(f) for f in it]
    #     else:
    #         infos = [info]
    #
    #     if not detail:
    #         return [i["name"] for i in infos]
    #     return infos

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
        pass  # not necessary to implement, may not have directories

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
        pass  # not necessary to implement, may not have directories

    def rmdir(self, path):
        """Remove a directory, if empty"""
        pass  # not necessary to implement, may not have directories

    def exists(self, path, **kwargs):
        return self.fs_protocol.exists(path)
