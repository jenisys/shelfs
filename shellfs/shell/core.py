import sys
from abc import abstractmethod
from enum import Enum
from functools import partial
from logging import getLogger
from subprocess import CalledProcessError, CompletedProcess
from typing import (
    Any, Callable, List,
    Optional, ParamSpec,
    Tuple, TypedDict, Union
)

from typing_extensions import Protocol, Self
# -- NOTE ON: Protocol super().__init__() call problem
#   * FIXED FOR: Python >= 3.11
#   * FIXED FOR: typing_extensions >= 4.6.0


# -----------------------------------------------------------------------------
# CONSTANTS
# -----------------------------------------------------------------------------
log4fsop = getLogger("shellfs.fsop")


# -----------------------------------------------------------------------------
# TYPE SUPPORT
# -----------------------------------------------------------------------------
P = ParamSpec("P")
DEFAULT_ENCODING = "UTF-8"

# -----------------------------------------------------------------------------
# UTILITY FUNCTIONS
# -----------------------------------------------------------------------------
def as_string(text: Union[str, bytes], encoding: Optional[str] = None) -> str:
    if isinstance(text, str):
        return text
    if not text:
        return ""

    assert isinstance(text, bytes), "type=%r" % text
    encoding = encoding or DEFAULT_ENCODING
    return text.decode(encoding)


# -----------------------------------------------------------------------------
# SHELL PROTOCOL / INTERFACE
# -----------------------------------------------------------------------------
class CommandResult(CompletedProcess):
    @staticmethod
    def make_output(this: Self, stderr_prefix: str = "") -> str:
        """Combines stdout and stderr and converts them to a string."""
        output = as_string(this.stdout or "")
        if this.stderr:
            output += "\n{prefix}{}".format(as_string(this.stderr),
                                            prefix=stderr_prefix)
        return output.strip()


class ErrorDialect:
    COMMAND_ERROR_CLASS = CalledProcessError
    TIMEOUT_ERROR_CLASS = TimeoutError
    ACCESS_DENIED_ERROR_CLASS = PermissionError



class PathType(Enum):
    NOT_FOUND = 0
    DIRECTORY = 1
    FILE = 2
    SYMLINK = 3

    def __str__(self):
        return self.name.lower()

    def __eq__(self, other):
        # -- SUPPORT: string-comparison
        # HINT: fsspec uses string-comparison with "file", "directory".
        if isinstance(other, PathType):
            return self is other
        elif isinstance(other, str):
            return self.name.lower() == other.lower()
        else:
            message = f"{type(other)} (expected: PathType, string)"
            raise TypeError(message)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        return self.value < other.value

    @classmethod
    def from_name(cls, name: str) -> Self:
        enum_item = getattr(cls, name.upper(), None)
        if enum_item is None:
            return LookupError(name)
        return enum_item


class PathEntry(TypedDict):
    """
            result = {
                "name": path,
                "size": size,
                "type": t,
                "created": out.st_ctime,
                "islink": link,
            }
    """
    name: str
    type: PathType
    size: int = 0
    islink: bool = False
    # MAYBE-LATER: created: str or DateTime

    def exists(self) -> bool:
        return self["type"] is not PathType.NOT_FOUND

    def is_not_found(self) -> bool:
        return self["type"] is PathType.NOT_FOUND

    @classmethod
    def make_not_found(cls, name: str) -> Self:
        return dict(name=name, type=PathType.NOT_FOUND, size=0)

    def __eq__(self, other):
        size_matched = (
            (self["size"] == other["size"]) or
            (self["size"] is None) or (other["size"] is None)
        )
        return (
            self["name"] == other["name"] and
            self["type"] == other["type"] and
            size_matched
        )

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        size_lessthan = (self["size"] < other["size"]) or (self["size"] is None)
        return (
            (self["type"] < other["type"]) or
            ((self["type"] == other["type"]) and (self["name"] < other["name"])) or
            ((self["type"] == other["type"]) and (self["name"] == other["name"]) and size_lessthan)
        )


class FSOperation(Enum):
    UNKNOWN = 0
    INFO = 1
    LISTDIR = 2

    # -- CREATE OPERATION(s):
    MKDIR = 10
    MAKEDIRS = 11
    TOUCH = 12
    COPY_FILE = 13
    # RESERVED: COPY = 14

    # -- DESTRUCTIVE OPERATION(s):
    RMTREE = 20
    RMDIR = 21
    REMOVE_FILE = 22


class FSOpsCommand:
    """
    Provides a mapping for filesystem operations to shell commands.
    """
    COMMAND_SCHEMA4INFO = None
    COMMAND_SCHEMA4LISTDIR = None
    COMMAND_SCHEMA4MKDIR = None
    COMMAND_SCHEMA4MAKEDIRS = None
    COMMAND_SCHEMA4TOUCH = None
    COMMAND_SCHEMA4COPY_FILE = None
    COMMAND_SCHEMA4RMTREE = None
    COMMAND_SCHEMA4RMDIR = None
    COMMAND_SCHEMA4REMOVE_FILE = None

    def _select_command_schema_for(self, operation: FSOperation) -> str:
        schema_name = f"COMMAND_SCHEMA4{operation.name}"
        command_schema = getattr(self, schema_name, None)
        if command_schema is None:
            # -- UNKNOWN-OPERATION:
            raise LookupError(operation)

        # -- NORMAL-CASE:
        return command_schema

    def _make_command_for(self, operation: FSOperation, **kwargs) -> str:
        command_schema = self._select_command_schema_for(operation)
        return command_schema.format(**kwargs)

    # -- MAKE-COMMAND FUNCTIONS:
    def make_command4info(self, path: str) -> str:
        return self._make_command_for(FSOperation.INFO, path=path)

    def make_command4listdir(self, directory: str) -> str:
        return self._make_command_for(FSOperation.LISTDIR, directory=directory)

    def make_command4mkdir(self, directory: str) -> str:
        return self._make_command_for(FSOperation.MKDIR, directory=directory)

    def make_command4makedirs(self, directory: str) -> str:
        return self._make_command_for(FSOperation.MAKEDIRS, directory=directory)

    def make_command4touch(self, path: str) -> str:
        return self._make_command_for(FSOperation.TOUCH, path=path)

    def make_command4copy_file(self, from_path: str, to_path: str) -> str:
        return self._make_command_for(FSOperation.COPY_FILE,
                                      from_path=from_path,
                                      to_path=to_path)

    def make_command4rmtree(self, directory: str) -> str:
        return self._make_command_for(FSOperation.RMTREE, directory=directory)

    def make_command4rmdir(self, directory: str) -> str:
        return self._make_command_for(FSOperation.RMDIR, directory=directory)

    def make_command4remove_file(self, path: str) -> str:
        return self._make_command_for(FSOperation.REMOVE_FILE, path=path)

    # -- MAKE-RESULT FUNCTIONS:
    def make_result4info(self, result: CommandResult, path: str) -> PathEntry:
        return NotImplemented

    def make_result4listdir(self, result: CommandResult, directory: str) -> List[PathEntry]:
        return NotImplemented

    @classmethod
    def make_result4any(cls, operation: FSOperation, result: CommandResult, **kwargs) -> CommandResult:
        # -- NOTE: Indicate if FS operation was successful (or not).
        succeeded = result.returncode == 0
        if succeeded:
            return result

        # -- FILESYSTEM-OPERATION FAILED:
        return_code = result.returncode
        output = CommandResult.make_output(result)
        log4fsop.warning(f"""{operation.name} FAILED: kwargs: {kwargs}
  return_code: {return_code}
  output: {output}
""")
        return result

    @classmethod
    def make_result4mkdir(cls, result: CommandResult, directory: str) -> CommandResult:
        return cls.make_result4any(FSOperation.MKDIR, result,
                                   directory=directory)

    @classmethod
    def make_result4makedirs(cls, result: CommandResult, directory: str) -> CommandResult:
        return cls.make_result4any(FSOperation.MAKEDIRS, result, directory=directory)

    @classmethod
    def make_result4touch(cls, result: CommandResult, path: str) -> CommandResult:
        return cls.make_result4any(FSOperation.TOUCH, result, path=path)

    @classmethod
    def make_result4copy_file(cls, result: CommandResult,
                              from_path: str, to_path: str) -> CommandResult:
        return cls.make_result4any(FSOperation.COPY_FILE, result,
                                   from_path=from_path,
                                   to_path=to_path)

    @classmethod
    def make_result4rmtree(cls, result: CommandResult, directory: str) -> CommandResult:
        return cls.make_result4any(FSOperation.RMTREE, result, directory=directory)

    @classmethod
    def make_result4rmdir(cls, result: CommandResult, directory: str) -> CommandResult:
        return cls.make_result4any(FSOperation.RMDIR, result, directory=directory)

    @classmethod
    def make_result4remove_file(cls, result: CommandResult, path: str) -> CommandResult:
        return cls.make_result4any(FSOperation.REMOVE_FILE, result, path=path)


class ShellProtocol(Protocol):
    """Protocol for shell(s) that run command(s) as filesystem operations."""
    FSOPS_COMMAND_CLASS = None
    ERROR_DIALECT_CLASS = ErrorDialect

    def __init__(self,
                 fsops_command: Optional[FSOpsCommand] = None,
                 error_dialect: Optional[ErrorDialect] = None) -> None:
        # -- NOTE: Works since Python >= 3.11 ot typing_extensions >= 4.6.0
        # BEFORE: Method not called in DerivedClass with: super().__init__()
        if fsops_command is None:
            fsops_command = self.FSOPS_COMMAND_CLASS()
        if error_dialect is None:
            error_dialect = self.ERROR_DIALECT_CLASS

        super().__init__()
        self.fsops_command = fsops_command
        self.error_dialect = error_dialect

    # def _init(self):
    #     self._setup_fsops()
    #     self._setup_error_dialect()
    #
    # def _setup_error_dialect(self, error_dialect: Optional[ErrorDialect] = None):
    #     if error_dialect is None:
    #         error_dialect = self.ERROR_DIALECT_CLASS
    #
    #     self.error_dialect = error_dialect
    #
    # def _setup_fsops(self, fsops_command: Optional[FSOpsCommand] = None):
    #     if fsops_command is None:
    #         fsops_command = self.FSOPS_COMMAND_CLASS()
    #     self.fsops_command = fsops_command

    @abstractmethod
    def run(self, command: str, timeout: Optional[float] = None) -> CommandResult:
        ...


class FileSystemProtocol:
    """
    Provides the core functionality of the shell-based filesystem.

    * It provides a simple, stable API to the :class:`ShellFileSystem`.
    * It coordinates the execution of filesystem operations provided by a shell.
    """
    def __init__(self, shell: ShellProtocol):
        self.shell = shell
        self.fsops_command = shell.fsops_command
        self.error_dialect = shell.error_dialect
        self._fsop_functions_map = {}
        self._setup_fsop_functions_map()

    def _setup_fsop_functions_map(self):
        for operation in iter(FSOperation):
            if operation is FSOperation.UNKNOWN:
                continue

            # -- SCHEMA: make_command_func, make_result_func
            fsop_functions = self._select_fsop_functions(operation)
            self._fsop_functions_map[operation] = fsop_functions

    def _select_fsop_functions(self, operation) -> Tuple[Callable, Callable]:
        operation_name = operation.name.lower()
        func_name1 = f"make_command4{operation_name}"
        func_name2 = f"make_result4{operation_name}"
        make_command_func = getattr(self.fsops_command, func_name1)
        make_result_func = getattr(self.fsops_command, func_name2, None)
        if make_result_func is None:
            make_result_func = partial(FSOpsCommand.make_result4any, operation)
        return make_command_func, make_result_func

    def run_fsop(self, operation, **kwargs) -> Any:
        make_command_func, make_result_func = self._fsop_functions_map[operation]
        command = make_command_func(**kwargs)
        result = self.shell.run(command)
        result.stdout = as_string(result.stdout)
        result.stderr = as_string(result.stderr)
        return make_result_func(result, **kwargs)

    def info(self, path: str) -> PathEntry:
        return self.run_fsop(FSOperation.INFO, path=path)

    def listdir(self, directory: str) -> List[PathEntry]:
        return self.run_fsop(FSOperation.LISTDIR, directory=directory)

    def exists(self, path: str) -> bool:
        path_entry = self.info(path)
        return path_entry["type"] is not PathType.NOT_FOUND

    def isfile(self, path: str) -> bool:
        path_entry = self.info(path)
        return path_entry["type"] is PathType.FILE

    def isdir(self, path: str) -> bool:
        path_entry = self.info(path)
        return path_entry["type"] is PathType.DIRECTORY

    def mkdir(self, directory: str) -> bool:
        return self.run_fsop(FSOperation.MKDIR, directory=directory)

    def makedirs(self, directory: str) -> bool:
        return self.run_fsop(FSOperation.MAKEDIRS, directory=directory)

    def touch(self, path: str) -> bool:
        return self.run_fsop(FSOperation.TOUCH, path=path)

    def copy_file(self, from_path: str, to_path: str) -> bool:
        return self.run_fsop(FSOperation.COPY_FILE,
                             from_path=from_path,
                             to_path=to_path)

    def rmtree(self, directory: str) -> CommandResult:
        return self.run_fsop(FSOperation.RMTREE, directory=directory)

    def rmdir(self, directory: str) -> CommandResult:
        return self.run_fsop(FSOperation.RMDIR, directory=directory)

    def remove_file(self, path: str) -> CommandResult:
        return self.run_fsop(FSOperation.REMOVE_FILE, path=path)


class ShellFactory:
    CLASS_REGISTRY = {}

    @classmethod
    def register_shell(cls, name: str, shell_class) -> Self:
        cls.CLASS_REGISTRY[name] = shell_class

    @classmethod
    def make_shell_by_name(cls, name: str) -> ShellProtocol:
        # -- MAY RAISE: KeyError if name is UNKNOWN.
        shell_class = cls.CLASS_REGISTRY[name]
        return shell_class()

    @classmethod
    def make_local_shell(cls):
        return cls.make_shell_by_name(sys.platform)
