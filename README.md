shellfs
===============================================================================

[shellfs] is a simple, in-performant filesystem that uses shell commands
to implement filesystem operations. [shellfs] is based on [fsspec]
that provides the core functionality for different filesystems.


[shellfs] provides:

* a filesystem abstraction if a shell is provided to run commands
* the shell protocol provides a stable interface to run commands in any shell
* a `ShellProtocol` as extension-point for different kind of shells
  (to execute filesystem operation commands).
* a `FileSystemProtocol` as extension-point to execute filesystem operations via shell commands,
* a `FSOperationCommand` as low-level profile that acts as adapter.
  between different shell command dialects and supports the shell command execution.
* the shell protocol is implemented for the local shell (on Unix platforms).

EXAMPLE:

```python
# -- FILE: example_use_shellfs.py
# SHELL PROVIDES:
#   * run(command, ...) method to execute commands (filesystem operations)
#   * FSOPS_COMMAND_CLASS: Provides low-level functionality for FileSystemProtocol

from shellfs import ShellFileSystem
from shellfs.shell.unix import UnixShell
from pathlib import Path

this_shell = UnixShell()
shellfs = ShellFileSystem(this_shell)
some_dir_path = "/tmp/some_dir"
some_file_path = Path(some_dir_path)/"some_file.txt"
shellfs.touch(some_file_path)
assert shellfs.exists(some_file_path) is True
assert shellfs.isfile(some_file_path) is True
assert shellfs.isdir(some_file_path) is False
assert shellfs.isdir(some_dir_path) is True
```

NOTES:

* The [shellfs] is not very performant.
* The [shellfs] is intended to be used if no better filesystem exists
  and only if a command shell is provided that allows to access the internal filesystem.

RELATED:

* [fsspec]

[shellfs]: https://github.com/jenisys/shellfs
[fsspec]: https://github.com/fsspec/filesystem_spec
[universal_pathlib]: https://github.com/fsspec/universal_pathlib
