"""
errors.py - one custom error type used by all services.
Services raise ServiceError("friendly message", status_code=502).
main.py turns it into a clean JSON response, so the user never sees a stack trace.
"""


class ServiceError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
