from typing import ParamSpec
from .core import (
    FSOpsCommand,
    CommandResult,  # noqa: F401
    ShellProtocol   # noqa: F401
)
from .local import LocalShell

# -----------------------------------------------------------------------------
# TYPE SUPPORT
# -----------------------------------------------------------------------------
P = ParamSpec("P")


# -----------------------------------------------------------------------------
# FILESYSTEM COMMAND DIALECTS:
# -----------------------------------------------------------------------------
class FSOpsCommand4Windows(FSOpsCommand):
    COMMAND_SCHEMA4LISTDIR = "dir {path}"
    COMMAND_SCHEMA4STAT = "dir {path}"


# -----------------------------------------------------------------------------
# SHELL IMPLEMENTATION:
# -----------------------------------------------------------------------------
class WindowsShell(LocalShell):
    FSOPS_COMMAND_CLASS = FSOpsCommand4Windows
