"""Top-level package for hashtree."""

from .cli import cli, hashtree
from .version import __author__, __email__, __timestamp__, __version__

__all__ = ["cli", "hashtree", "__version__", "__timestamp__", "__author__", "__email__"]
