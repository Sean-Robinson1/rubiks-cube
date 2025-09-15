"""rubiks_cube package: public API and metadata."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("rubiks-cube")
except PackageNotFoundError:
    __version__ = "0.0.0"

from .cube import Cube
from .main import main

__all__ = ["Cube", "main", "__version__"]
