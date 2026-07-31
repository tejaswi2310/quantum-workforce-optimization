from typing import Any, Optional

class CustomException(Exception):
    def __init__(self, status_code: int, message: str, detail: Optional[Any] = None):
        self.status_code = status_code
        self.message = message
        self.detail = detail
        super().__init__(message)
