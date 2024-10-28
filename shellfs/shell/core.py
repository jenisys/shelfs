import sys
from abc import abstractmethod
from enum import Enum
from subprocess import CalledProcessError, CompletedProcess
from typing import (
    Any, Callable, List,
    Optional, ParamSpec, Protocol,
    Tuple, TypedDict
)

from typing_extensions import Self


# -----------------------------------------------------------------------------
# TYPE SUPPORT
# -----------------------------------------------------------------------------
P = ParamSpec("P")


# -----------------------------------------------------------------------------
# SHELL PROTOCOL / INTERFACE
# -----------------------------------------------------------------------------
class CommandResult(CompletedProcess):
    pass


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


class FSOperation(Enum):
    UNKNOWN = 0
    INFO = 1
    LISTDIR = 2
    # -- CREATE OPERATION(s):
    MKDIR = 10
    MAKEDIRS = 11
    TOUCH = 12
    # -- DESTRUCTIVE OPERATION(s):
    RMTREE = 20
    REMOVE = 21


class FSOpsCommand:
    """
    Provides a mapping for filesystem operations to shell commands.
    """
    COMMAND_SCHEMA4INFO = None
    COMMAND_SCHEMA4LISTDIR = None
    COMMAND_SCHEMA4MKDIR = None
    COMMAND_SCHEMA4MAKEDIRS = None
    COMMAND_SCHEMA4TOUCH = None
    COMMAND_SCHEMA4RMTREE = None
    COMMAND_SCHEMA4REMOVE = None

    def _select_command_schema_for(self, operation: FSOperation) -> str:
        schema_name = f"COMMAND_SCHEMA4{operation.name}"
        command_schema = getattr(self, schema_name, None)
        if command_schema is None:
            # -- UNKNOWN-OPERATION:
            raise LookupError(operation)

        # -- NORMAL-CASE:
        return command_schema

    def _make_command_for(self, operation: FSOperation, path: str, **kwargs) -> str:
        command_schema = self._select_command_schema_for(operation)
        return command_schema.format(path=path, **kwargs)

    # -- MAKE-COMMAND FUNCTIONS:
    def make_command4info(self, path: str) -> str:
        return self._make_command_for(FSOperation.INFO, path=path)

    def make_command4listdir(self, path: str) -> str:
        return self._make_command_for(FSOperation.LISTDIR, path=path)

    def make_command4mkdir(self, path: str) -> str:
        return self._make_command_for(FSOperation.MKDIR, path=path)

    def make_command4makedirs(self, path: str) -> str:
        return self._make_command_for(FSOperation.MAKEDIRS, path=path)

    def make_command4touch(self, path: str) -> str:
        return self._make_command_for(FSOperation.TOUCH, path=path)

    def make_command4rmtree(self, path: str) -> str:
        return self._make_command_for(FSOperation.RMTREE, path=path)

    def make_command4remove(self, path: str) -> str:
        return self._make_command_for(FSOperation.REMOVE, path=path)

    # -- MAKE-RESULT FUNCTIONS:
    def make_result4info(self, path: str, output: str):
        return NotImplemented

    def make_result4listdir(self, path: str, output: str) -> List[PathEntry]:
        return NotImplemented

    @classmethod
    def make_result4any(cls, path: str, output: str):
        pass

    @classmethod
    def make_result4mkdir(cls, path: str, output: str):
        pass

    @classmethod
    def make_result4makedirs(cls, path: str, output: str):
        pass

    @classmethod
    def make_result4touch(cls, path: str, output: str):
        pass

    @classmethod
    def make_result4rmtree(cls, path: str, output: str):
        pass

    @classmethod
    def make_result4remove(cls, path: str, output: str):
        pass



class ShellProtocol(Protocol):
    """Protocol for shell(s) that run command(s)."""
    FSOPS_COMMAND_CLASS = None
    ERROR_DIALECT_CLASS = ErrorDialect

    def __init__(self, fsops_command: Optional[FSOpsCommand] = None,
                 error_dialect: Optional[ErrorDialect] = None):
        if fsops_command is None:
            fsops_command = self.FSOPS_COMMAND_CLASS()
        if error_dialect is None:
            error_dialect = self.ERROR_DIALECT_CLASS

        self.fsops_command = fsops_command
        self.error_dialect = error_dialect

    @abstractmethod
    def run(self, command: str, timeout: Optional[float] = None) -> CommandResult:
        ...


class FileSystemProtocol(Protocol):
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
        make_result_func = getattr(self.fsops_command, func_name2)
        return make_command_func, make_result_func

    def run_fsop(self, operation, path: str, **kwargs) -> Any:
        make_command_func, make_result_func = self._fsop_functions_map[operation]
        command = make_command_func(path, **kwargs)
        result = self.shell.run(command)
        output = result.stdout.decode()
        return make_result_func(path, output)

    def listdir(self, path: str) -> List[PathEntry]:
        return self.run_fsop(FSOperation.LISTDIR, path)

    def info(self, path: str) -> PathEntry:
        return self.run_fsop(FSOperation.INFO, path)

    def exists(self, path: str) -> bool:
        path_entry = self.info(path)
        return path_entry["type"] is not PathType.NOT_FOUND

    def isfile(self, path: str) -> bool:
        path_entry = self.info(path)
        return path_entry["type"] is PathType.FILE

    def isdir(self, path: str) -> bool:
        path_entry = self.info(path)
        return path_entry["type"] is PathType.DIRECTORY



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
