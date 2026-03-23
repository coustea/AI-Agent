"""Custom API exceptions."""

from fastapi import status


class APIError(Exception):
    """Base API exception."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    message: str = "Internal server error"
    error_code: str = "INTERNAL_ERROR"

    def __init__(
        self,
        message: str = None,
        status_code: int = None,
        error_code: str = None,
    ):
        super().__init__(message or self.message)
        if message:
            self.message = message
        if status_code:
            self.status_code = status_code
        if error_code:
            self.error_code = error_code

    def to_dict(self) -> dict:
        return {
            "code": self.status_code,
            "message": self.message,
            "error_code": self.error_code,
        }


class BadRequestError(APIError):
    """400 Bad Request."""

    status_code = status.HTTP_400_BAD_REQUEST
    message = "Bad Request"
    error_code = "BAD_REQUEST"


class UnauthorizedError(APIError):
    """401 Unauthorized."""

    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Unauthorized"
    error_code = "UNAUTHORIZED"


class ForbiddenError(APIError):
    """403 Forbidden."""

    status_code = status.HTTP_403_FORBIDDEN
    message = "Forbidden"
    error_code = "FORBIDDEN"


class NotFoundError(APIError):
    """404 Not Found."""

    status_code = status.HTTP_404_NOT_FOUND
    message = "Resource not found"
    error_code = "NOT_FOUND"


class ConflictError(APIError):
    """409 Conflict."""

    status_code = status.HTTP_409_CONFLICT
    message = "Resource conflict"
    error_code = "CONFLICT"


class ValidationError(APIError):
    """422 Validation Error."""

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    message = "Validation failed"
    error_code = "VALIDATION_ERROR"


class InternalServerError(APIError):
    """500 Internal Server Error."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    message = "Internal server error"
    error_code = "INTERNAL_SERVER_ERROR"


# ========== User Exceptions ==========


class UserNotFoundError(NotFoundError):
    """User not found."""

    status_code = status.HTTP_404_NOT_FOUND
    message = "User not found"
    error_code = "USER_NOT_FOUND"


class DuplicateUsernameError(ConflictError):
    """Username already exists."""

    status_code = status.HTTP_409_CONFLICT
    message = "Username already exists"
    error_code = "DUPLICATE_USERNAME"


class DuplicateEmailError(ConflictError):
    """Email already exists."""

    status_code = status.HTTP_409_CONFLICT
    message = "Email already exists"
    error_code = "DUPLICATE_EMAIL"


class InvalidCredentialsError(UnauthorizedError):
    """Invalid username or password."""

    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Invalid username or password"
    error_code = "INVALID_CREDENTIALS"


class WrongPasswordError(UnauthorizedError):
    """Wrong old password."""

    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Wrong old password"
    error_code = "WRONG_PASSWORD"


class UserInactiveError(ForbiddenError):
    """User account is inactive."""

    status_code = status.HTTP_403_FORBIDDEN
    message = "User account is inactive"
    error_code = "USER_INACTIVE"
