"""
Plain text resume parser (.txt, .md).
"""

from pathlib import Path
from src.parsers.base import BaseParser


class TXTParser(BaseParser):
    """Extracts text from plain text files."""

    def extract_text(self, file_path: Path) -> str:
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if file_path.stat().st_size == 0:
            raise ValueError(f"File is empty (0 bytes): {file_path.name}")

        for encoding in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    content = f.read().strip()
                if not content:
                    raise ValueError(f"File is empty: {file_path.name}")
                return content
            except UnicodeDecodeError:
                continue
            except Exception as e:
                if isinstance(e, ValueError):
                    raise
                raise ValueError(f"Failed to read TXT {file_path.name}: {str(e)}")

        raise ValueError(f"Unable to decode text file with standard encodings: {file_path.name}")
