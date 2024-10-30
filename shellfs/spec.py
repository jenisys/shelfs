"""
Provides a filesystem abstraction based on shell commands.

MISSING SUPPORT FOR FILESYSTEM:

* open()
* read_bytes()
* read_text()
* write_bytes()
* write_text()
* ... (like: cat(), ...)
"""

from typing import Optional, ParamSpec

from fsspec.spec import AbstractFileSystem

from .shell.core import (
    CommandResult,
    FileSystemProtocol,
    PathType,
    ShellProtocol,
    ShellFactory,
    # PREPARED: as_string,
)


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

    @staticmethod
    def _raise_error_on_command_failed(result: CommandResult,
                                       error_class: Exception,
                                       *args: P.args,
                                       **kwargs: P.kwargs):
        if result.returncode == 0:
            return

        # -- CASE: Command failed
        if issubclass(error_class, OSError):
            output = CommandResult.make_output(result)
            message = ""
            if output:
                message = output.splitlines()[0]
            errno = result.returncode
            raise OSError(errno, message, *args, **kwargs)

        if not (args or kwargs):
            output = CommandResult.make_output(result)
            args = (output, )
        raise error_class(*args, **kwargs)


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

    # TODO: Check if needed.
    def exists(self, path, **kwargs):
        return self.fs_protocol.exists(path)

    def mkdir(self, path, create_parents=True, **kwargs):
        """
        Create directory entry at path

        For systems that don't have true directories, may create one for
        this instance only and not touch the real filesystem

        Parameters
        ----------
        path: str
            location
        create_parents: bool
            If True, this is equivalent to :func:`makedirs`
        kwargs:
            May be permissions, etc.
        """
        path = self._strip_protocol(path)
        if create_parents:
            self.makedirs(path, exist_ok=True)
            return

        # -- NORMAL-CASE: Same behaviour as os.mkdir()
        path_type = self.fs_protocol.info(path)["type"]
        if path_type is not PathType.NOT_FOUND:
            # -- WORSE IF: PathType.FILE
            assert path_type in (PathType.DIRECTORY, PathType.FILE)
            raise FileExistsError(path)
        self.fs_protocol.mkdir(path)

    def makedirs(self, path, exist_ok: bool = False):
        """Recursively make directories

        Creates directory at path and any intervening required directories.
        Raises exception if, for instance, the path already exists but is a
        file.

        Parameters
        ----------
        path: str
            leaf directory name
        exist_ok: bool (False; like: :func:`os.makedirs()`)
            If False, will error if the target already exists
        """
        path = self._strip_protocol(path)
        path_type = self.fs_protocol.info(path)["type"]
        if path_type is PathType.NOT_FOUND:
            self.fs_protocol.makedirs(path)
            return

            # -- CASE: Directory or File exists already:
        if path_type is PathType.FILE:
            raise FileExistsError(path)
        elif not exist_ok:
            assert path_type is PathType.DIRECTORY
            raise FileExistsError(path)

    def rmdir(self, path):
        """Remove a directory, if empty"""
        # -- SAME BEHAVIOUR AS: os.rmdir()
        path = self._strip_protocol(path)
        path_type = self.fs_protocol.info(path)["type"]
        if path_type is PathType.NOT_FOUND:
            raise FileNotFoundError(path)

        command_result = self.fs_protocol.rmdir(path)
        self._raise_error_on_command_failed(command_result, OSError, path)
        # if command_result.returncode != 0:
        #     errno = command_result.returncode
        #     message = as_string(command_result.stderr.splitlines()[0])
        #     raise OSError(errno, message, path)

    def touch(self, path, truncate=False, **kwargs):
        """Create empty file, or update timestamp

        Parameters
        ----------
        path: str
            file location to use.
        truncate: bool
            If true, truncates the file size to zero (0);
            if false, update timestamp and leave file unchanged, if backend allows this.

        NOTE:
        * ``truncate=False`` differs from base-class default value (is true).
        """
        if truncate and self.isfile(path):
            self.rm_file(path)

        # -- NORMAL-CASE:
        command_result = self.fs_protocol.touch(path)
        self._raise_error_on_command_failed(command_result, PermissionError, path)

    def cp_file(self, path1, path2, **kwargs):
        command_result = self.fs_protocol.copy_file(path1, path2, **kwargs)
        self._raise_error_on_command_failed(command_result, OSError)

    def rm_file(self, path):
        """Delete a file (overridden from base-class)."""
        command_result = self.fs_protocol.remove_file(path)
        self._raise_error_on_command_failed(command_result, OSError)

    def rm(self, path, recursive=False, maxdepth=None):
        """Override to provide sane remove/remove-recursive implementation.
        The original base-class implementation deletes only files and
        is stumbles over its own feet when directory(s) should be removed in the for-loop.

        Parameters
        ----------
        path: str or list of str
            Directory(s) or file(s) to delete.
        recursive: bool
            If true and path is a directory, remove the directory subtree with its contents.
        maxdepth: int or None
            Depth to pass to walk for finding files to delete, if recursive.
            If None, there will be no limit and infinite recursion may be possible.
        """
        if maxdepth is not None:
            raise ValueError("NOT-SUPPORTED: maxdepth as int")

        paths = path
        if not isinstance(paths, list):
            paths = [path]

        for this_path in paths:
            this_path = self._strip_protocol(this_path)
            path_type = self.fs_protocol.info(this_path)["type"]
            if path_type is PathType.NOT_FOUND:
                # -- GRACEFULLY-IGNORED
                continue

            if path_type is PathType.DIRECTORY:
                if not recursive:
                    raise ValueError(f"DIRECTORY REQUIRES: recursive=True: {this_path}")
                self.rmtree(this_path)
            else:
                assert path_type is PathType.FILE
                self.rm_file(this_path)

    # -- FSSPEC-API EXTENSION(s):
    def rmtree(self, directory, ignore_errors=False, onexc=None):
        """Remove entire directory tree."""
        # --  SAME BEHAVIOUR AS: shutil.rmtree()
        path_type = self.fs_protocol.info(directory)["type"]
        if path_type is PathType.NOT_FOUND:
            return

        if path_type is PathType.FILE:
            if not ignore_errors:
                if onexc:
                    this_exception = NotADirectoryError(directory)
                    exc_info = NotADirectoryError, this_exception, None
                    return onexc(self.rmtree, directory, exc_info)
                # -- RAISE EXCEPTION:
                raise NotADirectoryError(directory)
            # -- BAIL-OUT HERE:
            return

        # -- NORMAL-CASE: DIRECTORY
        result = self.fs_protocol.rmtree(directory)
        if ignore_errors or result.returncode == 0:
            return

        # -- CASE: HAS FAILED
        assert not ignore_errors and result.returncode != 0
        if onexc:
            # -- HINT: May not be available for remote-node(s).
            # MAYBE: exc_info = sys.exc_info()
            exc_info = None
            onexc(self.fs_protocol.rmtree, directory, exc_info)
            return

        # -- OTHERWISE:
        errno = result.returncode
        output = CommandResult.make_output(result)
        raise OSError(errno, output, directory)
