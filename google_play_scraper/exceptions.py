class GooglePlayError(Exception):
    """Base exception for the library."""
    pass


class AppNotFound(GooglePlayError):
    """Raised when the App ID cannot be found (404)."""
    pass


class QuotaExceeded(GooglePlayError):
    """Raised when Google blocks the request (429/503)."""
    pass


class ParsingError(GooglePlayError):
    """Raised when the scraper fails to parse the Google Play response."""
    pass
