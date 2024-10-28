import subprocess
import sys
from typing import Optional, ParamSpec

from typing_extensions import Self

from .core import FSOpsCommand, CommandResult, ShellProtocol


# -----------------------------------------------------------------------------
# TYPE SUPPORT
# -----------------------------------------------------------------------------
P = ParamSpec("P")


# -----------------------------------------------------------------------------
# FILESYSTEM COMMAND DIALECTS:
# -----------------------------------------------------------------------------
# class FSCommandDialect4Unix(FSOpsCommand):
#     COMMAND_SCHEMA4LISTDIR = "ls -laF {path}"
#     COMMAND_SCHEMA4STAT = "ls -laF {path}"
#
#
# class FSCommandDialect4Windows(FSOpsCommand):
#     COMMAND_SCHEMA4LISTDIR = "dir {path}"
#     COMMAND_SCHEMA4STAT = "dir {path}"


# -----------------------------------------------------------------------------
# SHELL IMPLEMENTATION:
# -----------------------------------------------------------------------------
class LocalShell(ShellProtocol):
    """
    Runs command(s) in the local shell.
    """
    STRICT_DEFAULT = None

    def __init__(self, check: Optional[bool] = None) -> None:
        super().__init__()
        self.check = check or self.STRICT_DEFAULT

    def run(self, command: str,
            timeout: Optional[float] = None,
            **kwargs: P.kwargs) -> CommandResult:
        check = bool(kwargs.pop("check", self.check))
        return subprocess.run(command,
                              capture_output=True,
                              timeout=timeout,
                              check=check,
                              **kwargs)

