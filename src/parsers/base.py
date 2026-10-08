"""
Base resume parser interface.
"""

from abc import ABC, abstractmethod
from pathlib import Path


class BaseParser(ABC):
    """Abstract interface for file text extractors."""

    @abstractmethod
    def extract_text(self, file_path: Path) -> str:
        """Extract text from the given file path.
        Raises an exception if the file is completely unreadable.
        """
        pass
