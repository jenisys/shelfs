from typing import List, Optional, ParamSpec

import parse
from parse_type.cfparse import Parser as CFParser

from .core import PathEntry, FSOpsCommand, PathType, CommandResult
from .local import LocalShell

# -----------------------------------------------------------------------------
# TYPE SUPPORT
# -----------------------------------------------------------------------------
P = ParamSpec("P")


# -----------------------------------------------------------------------------
# SUPPORT:
# -----------------------------------------------------------------------------
# @parse.with_pattern(r"\s*[A-Za-z0-9_:,\-]+")
@parse.with_pattern(r"\s*([^\s]+)", regex_group_count=1)
def parse_word(text: str) -> str:
    return text.strip()

@parse.with_pattern(r"\s+")
def parse_spacer(text: str) -> str:
    """One or more whitespace chars."""
    return text


# -----------------------------------------------------------------------------
# FILESYSTEM COMMAND DIALECTS:
# -----------------------------------------------------------------------------
class FSOpsCommand4Unix(FSOpsCommand):
    """

    CANDIDATES:

    - ``ls -ladFL -D "%s" {path}``
    - "-l": Show long-format
    - "-a": Do not ignore entries starting with "."
    - "-A": Do not show entries: ".", ".."
    - "-F": Add name-suffixes: "/" for directory, "@" for symlink, ...
    - "-d": Show directory only, not its contents
    - "-L": Follow symbolic link to show the file-type directly
    - "-D %s": Show modified-time in seconds since epoch (1970-01-01T00:00:00Z) -- macOS/BSD only

    EXAMPLES:

    .. code-block:: bash

        $ ls -ladFL -D "%Y-%m-%dT%H:%M:%S" this_repo_directory
        drwxr-xr-x  10 alice users  320 2024-10-27T12:19:03 this_repo_directory/
        # file_mask ?  user  group  size date               name (with type-suffix)

        $ ls -ladL -D "%Y-%m-%dT%H:%M:%S" this_repo_directory
        drwxr-xr-x  10 alice  users   320 2024-10-27T12:19:03 this_repo_directory

        $ ls -ladL -D "%s" this_path
        drwxr-xr-x  10 alice  users   320 1730027943 this_repo_directory
        -rw-r--r--  1  alice  users  2879 1730025034 this_file.py
        -rw-r--r--  1  alice  users     0 1730063602 __EMPTY_FILE.tag
        # file_mask ?  user   group  size utc-time-seconds  name (with type-suffix)

        $ ls -ladL -D "%s" this_path
        -rw-r--r--  1 alice  users  2879 Oct 27 11:30 this_file.txt
    FILE_TYPE CHARS::

           -     Regular file.
           b     Block special file.
           c     Character special file.
           d     Directory.
           l     Symbolic link.
           p     FIFO.
           s     Socket.
           w     Whiteout.

    SEE ALSO:

    * https://www.man7.org/linux/man-pages/man1/ls.1.html
    *
    """
    COMMAND_SCHEMA4INFO = "ls -ldAL {path}"         # -- NOTE: Show info on a file or directory (follows symlinks).
    COMMAND_SCHEMA4LISTDIR = "ls -lAL {directory}"  # -- NOTE: List the contents of a directory.
    COMMAND_SCHEMA4MAKEDIRS = "mkdir -p {directory}"  # -- NOTE: Creates any missing directories.
    COMMAND_SCHEMA4MKDIR = "mkdir {directory}"      # -- NOTE: May fail if directory exists.
    COMMAND_SCHEMA4TOUCH = "touch {path}"           # -- NOTE: Creates an empty file (or update timestamps).
    COMMAND_SCHEMA4COPY_FILE = "cp {from_path} {to_path}"
    COMMAND_SCHEMA4RMTREE = "rm -rf {directory}"    # -- NOTE: Remove directory-tree recursively.
    COMMAND_SCHEMA4RMDIR = "rmdir {directory}"      # -- NOTE: May fail if non-empty.
    COMMAND_SCHEMA4REMOVE_FILE = "rm -f {path}"     # -- NOTE: Remove file.
    RESULT_SCHEMA4INFO = "{file_type:Word}{_s0:Spacer}{link_number:d}{_s1:Spacer}{user:w}{_s2:Spacer}{group:w}{_s3:Spacer}{size:d}{_s4:Spacer}{timestamp}{_s5:Spacer}{name:Word}"
    PATH_NOT_FOUND_MARKER = "No such file or directory"
    # NOT_NEEDED: FILE_TYPE_NORMAL_CHARS = "-dl"  # Regular-file, directory, symlink
    # COMMAND_SCHEMA4STAT1A = "ls -ladL -D '%s' {path}"  -- macOS
    # COMMAND_SCHEMA4STAT2A = "ls -ladL --time-style='+%s' {path}"  -- Linux
    # COMMAND_SCHEMA4STAT1B = "ls -ladL -D '%Y-%m-%dT%H:%M:%S' {path}"  -- macOS
    # COMMAND_SCHEMA4STAT2B = "ls -ladL --time-style='+%Y-%m-%dT%H:%M:%S' {path}"  -- Linux

    @classmethod
    def get_file_type_from(cls, file_type_and_access: str) -> str:
        if not file_type_and_access:
            return PathType.NOT_FOUND

        first_char = file_type_and_access[0]
        path_type = PathType.FILE  # Regular-file or special-file(s)
        if first_char == "d":
            path_type = PathType.DIRECTORY
        elif first_char == "l":
            path_type = PathType.SYMLINK
        return path_type

    @classmethod
    def parse_info(cls, text: str, path: Optional[str] = None) -> PathEntry:
        if cls.PATH_NOT_FOUND_MARKER in text:
            return PathEntry.make_not_found(name=path)

        schema = cls.RESULT_SCHEMA4INFO
        more_types = dict(Word=parse_word, Spacer=parse_spacer)
        parser = CFParser(schema, extra_types=more_types)
        matched = parser.parse(text)
        if matched:
            file_type_and_access = matched.named["file_type"]
            path_type = cls.get_file_type_from(file_type_and_access)
            name = matched.named["name"]
            size = matched.named["size"]
            return PathEntry(name=name, type=path_type, size=size)

        # -- OTHERWISE: Mismatched, unexpected output.
        return PathEntry.make_not_found(name=path)

    # -- IMPLEMENT INTERFACE FOR: FSOpsCommand
    @classmethod
    def make_result4info(cls, result: CommandResult, path: str) -> PathEntry:
        if result.returncode != 0:
            return PathEntry.make_not_found(name=path)

        output = result.stdout.strip()
        if isinstance(output, bytes):
            output = output.decode("utf-8")
        return cls.parse_info(output, path=path)

    @classmethod
    def make_result4listdir(cls, result: CommandResult, directory: str) -> List[PathEntry]:
        output = result.stdout.strip()
        if isinstance(output, bytes):
            output = output.decode("utf-8")

        if cls.PATH_NOT_FOUND_MARKER in output:
            # -- SPECIAL CASE: path is NOT-FOUND (use case: is not really used).
            # MAYBE: return [PathEntry.make_not_found(path)]
            return []

        selected = []
        for index, line in enumerate(output.splitlines()):
            if index == 0 and line.startswith("total "):
                # -- FIRST LINE: If path is a directory.
                continue

            path_entry = cls.parse_info(line, path=directory)
            assert path_entry["type"] is not PathType.NOT_FOUND
            selected.append(path_entry)
        return selected


class UnixShell(LocalShell):
    """
    Filesystem shell for UNIX-like shells (Bourne shell, bash, ...).

    SUPPORTED PLATFORMS:

    * "darwin"
    * "linux"
    * "aix"
    * "cygwin"
    * "freebsd"
    """
    # -- BASED-ON: sys.platform names
    SUPPORTED_PLATFORMS = ["darwin", "linux", "aix", "cygwin", "freebsd"]
    FSOPS_COMMAND_CLASS = FSOpsCommand4Unix
