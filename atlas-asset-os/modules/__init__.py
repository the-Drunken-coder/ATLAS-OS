"""Module infrastructure for BasePlate OS.

This package provides the base class and loader for all modules.
"""

from modules.module_base import ModuleBase
from modules.module_loader import ModuleLoader, ModuleLoadError, DependencyError

__all__ = [
    "ModuleBase",
    "ModuleLoader",
    "ModuleLoadError",
    "DependencyError",
]
