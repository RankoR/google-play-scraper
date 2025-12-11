from datetime import datetime
from typing import Optional, Dict, List, Any

from pydantic import BaseModel, HttpUrl, Field, BeforeValidator
from typing_extensions import Annotated


# -- Helpers for Validators --

def _coerce_int(v: Any) -> int:
    if isinstance(v, int):
        return v
    if isinstance(v, str):
        # Handles "5,000,000+" -> 5000000
        clean = v.replace(",", "").replace("+", "").split(" ")[0]
        if clean.isdigit():
            return int(clean)
    return 0


def _coerce_float(v: Any) -> float:
    if isinstance(v, (float, int)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.replace(",", "."))
        except ValueError:
            pass
    return 0.0


CoercedInt = Annotated[int, BeforeValidator(_coerce_int)]
CoercedFloat = Annotated[float, BeforeValidator(_coerce_float)]


class AppOverview(BaseModel):
    """Minimal app details used in lists/search."""
    app_id: str
    title: str
    icon: Optional[HttpUrl] = None
    developer: Optional[str] = None
    developer_id: Optional[str] = None
    score: Optional[CoercedFloat] = None
    score_text: Optional[str] = None
    price_text: Optional[str] = None
    free: Optional[bool] = None
    summary: Optional[str] = None


class AppDetails(AppOverview):
    """Detailed app information."""
    description: str = ""
    description_html: str = ""
    installs: str = "0"
    min_installs: CoercedInt = 0
    max_installs: CoercedInt = 0
    ratings: CoercedInt = 0
    reviews: CoercedInt = 0
    histogram: Dict[str, int] = Field(default_factory=dict)
    currency: Optional[str] = None
    price: CoercedFloat = 0.0
    available: bool = True
    offers_iap: bool = False
    android_version: str = "VARY"
    developer_email: Optional[str] = None
    developer_website: Optional[HttpUrl] = None
    developer_address: Optional[str] = None
    privacy_policy: Optional[HttpUrl] = None
    genre: Optional[str] = None
    genre_id: Optional[str] = None
    header_image: Optional[HttpUrl] = None
    screenshots: List[HttpUrl] = Field(default_factory=list)
    video: Optional[HttpUrl] = None
    content_rating: Optional[str] = None
    released: Optional[str] = None
    updated: Optional[datetime] = None
    version: Optional[str] = None
    recent_changes: Optional[str] = None
    comments: List[str] = Field(default_factory=list)


class Review(BaseModel):
    id: str
    user_name: str
    user_image: Optional[HttpUrl] = None
    date: Optional[datetime] = None
    score: int
    title: Optional[str] = None
    text: Optional[str] = None
    reply_date: Optional[datetime] = None
    reply_text: Optional[str] = None
    version: Optional[str] = None
    thumbs_up: int = 0
