shellfs
===============================================================================

xxx

.. |badge.CI_status| image:: https://github.com/jenisys/parse_type/actions/workflows/test.yml/badge.svg
    :target: https://github.com/jenisys/parse_type/actions/workflows/test.yml
    :alt: CI Build Status

.. |badge.latest_version| image:: https://img.shields.io/pypi/v/parse_type.svg
    :target: https://pypi.python.org/pypi/parse_type
    :alt: Latest Version

.. |badge.downloads| image:: https://img.shields.io/pypi/dm/parse_type.svg
    :target: https://pypi.python.org/pypi/parse_type
    :alt: Downloads

.. |badge.license| image:: https://img.shields.io/pypi/l/parse_type.svg
    :target: https://pypi.python.org/pypi/parse_type/
    :alt: License

|badge.CI_status| |badge.latest_version| |badge.license| |badge.downloads|

[shellfs] is a simple, in-performant filesystem that uses shell commands
to implement filesystem operations. [shellfs] is based on [fsspec]
that provides the core functionality for different filesystems.


[shellfs] provides:

* a filesystem abstraction if a shell is provided to run commands
* a shell protocol as extension-point for different kind of shells
* the shell protocol provides a stable interface to run commands in shell
* the shell protocol is implemented for the local shell (on Unix platforms)

EXAMPLE:

```python
# -- FILE: example_use_shellfs.py
from shellfs.shell.local import LocalUnixShell
from shellfs import ShellFileSystem
from pathlib import Path

the_shell = LocalUnixShell()
shellfs = ShellFileSystem(the_shell)
some_dir_path = "/tmp/some_dir"
some_file_path = Path(some_dir_path) / "/some_file.txt"
shellfs.touch(some_file_path)
assert shellfs.exists(some_file_path) is True
assert shellfs.isfile(some_file_path) is True
assert shellfs.isdir(some_file_path) is False
assert shellfs.isdir(some_dir_path) is True
```

NOTES:

* The [shellfs] is not very performant.
* The [shellfs] is intended to be used if no better filesystem exists
  and when only a command shell is provided that can access the internal filesystem.

RELATED:

[shellfs]: https://github.com/jenisys/shellfs
[fsspec]: https://github.com/fsspec/filesystem_spec
[universal_pathlib]: https://github.com/fsspec/universal_pathlib
