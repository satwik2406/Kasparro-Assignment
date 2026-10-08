"""
PDF parser implementation using pypdf.
Robust against corrupt, blank, or partially invalid PDF structures.
"""

from pathlib import Path
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from src.parsers.base import BaseParser


class PDFParser(BaseParser):
    """Extracts text from PDF documents with strict error isolation."""

    def extract_text(self, file_path: Path) -> str:
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if file_path.stat().st_size == 0:
            raise ValueError(f"File is empty (0 bytes): {file_path.name}")

        try:
            reader = PdfReader(str(file_path))
            if reader.is_encrypted:
                try:
                    # Attempt empty password decryption
                    reader.decrypt("")
                except Exception:
                    raise ValueError(f"Encrypted PDF cannot be read without password: {file_path.name}")

            extracted_chunks = []
            for i, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        extracted_chunks.append(page_text)
                except Exception as page_err:
                    # Continue reading other pages if one page has issues
                    continue

            full_text = "\n".join(extracted_chunks).strip()
            if not full_text:
                raise ValueError(f"No extractable text found in PDF (may be scanned image): {file_path.name}")

            return full_text

        except PdfReadError as e:
            raise ValueError(f"Corrupt or invalid PDF format: {file_path.name} ({str(e)})")
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"Failed to parse PDF {file_path.name}: {str(e)}")
