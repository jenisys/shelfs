import subprocess
from typing import Optional, ParamSpec

from .core import CommandResult, ShellProtocol


# -----------------------------------------------------------------------------
# TYPE SUPPORT
# -----------------------------------------------------------------------------
P = ParamSpec("P")


# -----------------------------------------------------------------------------
# SHELL IMPLEMENTATION:
# -----------------------------------------------------------------------------
class LocalShell(ShellProtocol):
    """
    Runs command(s) in the local shell.
    """
    CHECK_DEFAULT = None

    def __init__(self, check: Optional[bool] = None) -> None:
        super().__init__()
        self.check = check or self.CHECK_DEFAULT

    def run(self, command: str,
            timeout: Optional[float] = None,
            **kwargs: P.kwargs) -> CommandResult:
        check = bool(kwargs.pop("check", self.check))
        return subprocess.run(command,
                              capture_output=True,
                              timeout=timeout,
                              check=check,
                              shell=True,
                              **kwargs)

