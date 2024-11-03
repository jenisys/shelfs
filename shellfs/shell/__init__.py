from .factory import ShellFactory
from .unix import UnixShell as _UnixShell
from .windows import WindowsShell as _WindowsShell


# -----------------------------------------------------------------------------
# MODULE SETUP
# -----------------------------------------------------------------------------
def _register_local_shells_by_platform():
    ShellFactory.register_shell("win32", _WindowsShell)
    for platform_name in _UnixShell.SUPPORTED_PLATFORMS:
        ShellFactory.register_shell(platform_name, _UnixShell)


def _setup_module():
    _register_local_shells_by_platform()


# -----------------------------------------------------------------------------
# AUTO MODULE SETUP
# -----------------------------------------------------------------------------
_setup_module()
