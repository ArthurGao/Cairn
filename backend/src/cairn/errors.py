"""Domain errors. The API maps every CairnError to `{error: {code, message}}`."""


class CairnError(Exception):
    """An error with a stable machine-readable code and an HTTP status for the API."""

    code: str = "error"
    status: int = 500

    def __init__(self, message: str, *, code: str | None = None, status: int | None = None):
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if status is not None:
            self.status = status
