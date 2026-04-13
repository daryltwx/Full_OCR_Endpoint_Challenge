from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ocr_dpi: int = 150
    allowed_mime_types: set[str] = {
        "application/pdf",
        "image/jpeg",
        "image/png",
    }
    # Signature detection thresholds
    sig_min_contour_area: int = 200
    sig_max_contour_area: int = 50000
    sig_min_solidity: float = 0.15
    sig_max_solidity: float = 0.85
    sig_min_qualifying_contours: int = 4


settings = Settings()
