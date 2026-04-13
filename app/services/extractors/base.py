from abc import ABC, abstractmethod
from PIL import Image


class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, text: str, images: list[Image.Image]) -> dict:
        """Return a dict of extracted fields."""
        ...
