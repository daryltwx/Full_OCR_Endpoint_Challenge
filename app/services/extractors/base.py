from abc import ABC, abstractmethod
from PIL import Image


class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, text: str, images: list[Image.Image]) -> dict:
        """Extract structured fields from the document.

        Args:
            text: OCR-extracted text.
            images: Page images from the document.

        Returns:
            A dict mapping field names to extracted values.
        """
        ...
