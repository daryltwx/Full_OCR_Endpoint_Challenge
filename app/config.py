from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ocr_dpi: int = 300
    allowed_mime_types: set[str] = {
        "application/pdf",
        "image/jpeg",
        "image/png",
    }
    # Preprocessing settings
    preprocess_enabled: bool = True
    preprocess_block_size: int = 15       # adaptive threshold block size (odd)
    preprocess_constant: int = 10         # adaptive threshold C value
    preprocess_line_scale: int = 30       # kernel length = width/this for horiz lines

    # Signature detection thresholds
    sig_min_contour_area: int = 200
    sig_max_contour_area: int = 50000
    sig_min_solidity: float = 0.15
    sig_max_solidity: float = 0.85
    sig_min_qualifying_contours: int = 5


settings = Settings()
