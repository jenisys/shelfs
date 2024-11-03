"""
Provides a :class:`ShellFactory` to register shells and create them.
"""

import sys

from typing_extensions import Self

from shellfs import ShellProtocol


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
