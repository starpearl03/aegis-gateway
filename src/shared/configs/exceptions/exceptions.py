"""
Universal dynamic exception handler for any domain.
These exceptions are generic and reusable across different entities and services.
"""

from typing import List, Optional, Any, Dict
from flask import flash


class AppException(Exception):
    """
    Base exception for all application errors.
    Automatically flashes messages for web requests.
    """

    def __init__(
            self,
            message: str,
            details: Optional[List[str]] = None,
            status_code: int = 500,
            title: str = "Application Error",
            flash_category: str = 'error',
            field_errors: Optional[Dict[str, List[str]]] = None
    ):
        self.message = message
        self.details = details or [message] if message else []
        self.status_code = status_code
        self.title = title
        self.flash_category = flash_category
        self.field_errors = field_errors or {}

        # Flash messages for web requests
        if self.details:
            for detail in self.details:
                flash(detail, self.flash_category)
        else:
            flash(self.message, self.flash_category)

        super().__init__(self.message)

    def add_field_error(self, field: str, error: str) -> None:
        """
        Add a field-specific error to this exception.

        Args:
            field: Name of the field with the error
            error: Error message for the field

        Usage:
            exception.add_field_error("email", "Invalid email format")
            exception.add_field_error("password", "Too short")
        """
        if field not in self.field_errors:
            self.field_errors[field] = []
        self.field_errors[field].append(error)


class NotFoundException(AppException):
    """
    Raised when a requested resource is not found.

    Usage:
        raise NotFoundException(f"Product with id {product_id} not found")
        raise NotFoundException(f"User with email {email} not found")
        raise NotFoundException(f"Order with id {order_id} not found")
    """

    def __init__(self, message: str, details: Optional[List[str]] = None,
                 field_errors: Optional[Dict[str, List[str]]] = None):
        super().__init__(
            message=message,
            details=details,
            status_code=404,
            title="Resource Not Found",
            field_errors=field_errors
        )


class AlreadyExistsException(AppException):
    """
    Raised when trying to create a resource that already exists.

    Usage:
        raise AlreadyExistsException(f"Product with name '{name}' already exists")
        raise AlreadyExistsException(f"User with email {email} already exists")
        raise AlreadyExistsException(f"Category with slug '{slug}' already exists")
    """

    def __init__(self, message: str, details: Optional[List[str]] = None,
                 field_errors: Optional[Dict[str, List[str]]] = None):
        super().__init__(
            message=message,
            details=details,
            status_code=409,
            title="Resource Already Exists",
            field_errors=field_errors
        )


class ValidationException(AppException):
    """
    Raised when input validation fails.

    Usage:
        raise ValidationException(f"Invalid email format: {email}")
        raise ValidationException(f"Price must be greater than 0, got {price}")
        raise ValidationException("Password must be at least 8 characters",
                                details=["Must contain uppercase", "Must contain number"])

        # With field errors
        exc = ValidationException("Form validation failed")
        exc.add_field_error("email", "Invalid format")
        exc.add_field_error("password", "Too short")
        raise exc
    """

    def __init__(self, message: str, details: Optional[List[str]] = None,
                 field_errors: Optional[Dict[str, List[str]]] = None):
        super().__init__(
            message=message,
            details=details,
            status_code=400,
            title="Validation Failed",
            field_errors=field_errors
        )


class UnauthorizedException(AppException):
    """
    Raised when user is not authenticated or credentials are invalid.

    Usage:
        raise UnauthorizedException("Invalid login credentials")
        raise UnauthorizedException("Session has expired, please login again")
        raise UnauthorizedException(f"Invalid API key: {api_key}")
    """

    def __init__(self, message: str, details: Optional[List[str]] = None,
                 field_errors: Optional[Dict[str, List[str]]] = None):
        super().__init__(
            message=message,
            details=details,
            status_code=401,
            title="Authentication Required",
            field_errors=field_errors
        )


class ForbiddenException(AppException):
    """
    Raised when user doesn't have permission to access a resource.

    Usage:
        raise ForbiddenException(f"You don't have permission to delete product {product_id}")
        raise ForbiddenException("Admin access required for this operation")
        raise ForbiddenException(f"Access denied to {resource_name}")
    """

    def __init__(self, message: str, details: Optional[List[str]] = None,
                 field_errors: Optional[Dict[str, List[str]]] = None):
        super().__init__(
            message=message,
            details=details,
            status_code=403,
            title="Access Forbidden",
            field_errors=field_errors
        )


class ConflictException(AppException):
    """
    Raised when operation conflicts with current state.

    Usage:
        raise ConflictException(f"Cannot delete product {product_id} - it has active orders")
        raise ConflictException(f"User {user_id} is already assigned to this project")
        raise ConflictException("Cannot update order - it has already been shipped")
    """

    def __init__(self, message: str, details: Optional[List[str]] = None,
                 field_errors: Optional[Dict[str, List[str]]] = None):
        super().__init__(
            message=message,
            details=details,
            status_code=409,
            title="Operation Conflict",
            field_errors=field_errors
        )


class BadRequestException(AppException):
    """
    Raised when request is malformed or invalid.

    Usage:
        raise BadRequestException(f"Invalid JSON format in request body")
        raise BadRequestException(f"Missing required parameter: {param_name}")
        raise BadRequestException("Request body cannot be empty")
    """

    def __init__(self, message: str, details: Optional[List[str]] = None,
                 field_errors: Optional[Dict[str, List[str]]] = None):
        super().__init__(
            message=message,
            details=details,
            status_code=400,
            title="Bad Request",
            field_errors=field_errors
        )


class InternalServerException(AppException):
    """
    Raised when an internal server error occurs.

    Usage:
        raise InternalServerException(f"Database connection failed: {error}")
        raise InternalServerException("External API is currently unavailable")
        raise InternalServerException(f"Failed to process {operation}: {error}")
    """

    def __init__(self, message: str, details: Optional[List[str]] = None,
                 field_errors: Optional[Dict[str, List[str]]] = None):
        super().__init__(
            message=message,
            details=details,
            status_code=500,
            title="Internal Server Error",
            field_errors=field_errors
        )


class ServiceUnavailableException(AppException):
    """
    Raised when service is temporarily unavailable.

    Usage:
        raise ServiceUnavailableException("Payment service is currently down")
        raise ServiceUnavailableException(f"Email service unavailable, try again later")
        raise ServiceUnavailableException("System maintenance in progress")
    """

    def __init__(self, message: str, details: Optional[List[str]] = None,
                 field_errors: Optional[Dict[str, List[str]]] = None):
        super().__init__(
            message=message,
            details=details,
            status_code=503,
            title="Service Unavailable",
            field_errors=field_errors
        )


class RateLimitExceededException(AppException):
    """
    Raised when rate limit is exceeded.

    Usage:
        raise RateLimitExceededException(f"Rate limit exceeded for user {user_id}")
        raise RateLimitExceededException("Too many requests, try again in 5 minutes")
        raise RateLimitExceededException(f"API limit reached: {limit} requests per hour")
    """

    def __init__(self, message: str, details: Optional[List[str]] = None,
                 field_errors: Optional[Dict[str, List[str]]] = None):
        super().__init__(
            message=message,
            details=details,
            status_code=429,
            title="Rate Limit Exceeded",
            field_errors=field_errors
        )


class CustomException(AppException):
    """
    Fully customizable exception for specific use cases.

    Usage:
        raise CustomException(
            message=f"Payment failed for order {order_id}",
            status_code=402,
            title="Payment Required",
            details=["Card declined", "Insufficient funds"]
        )
    """

    def __init__(self, message: str, status_code: int = 500, title: str = "Custom Error",
                 details: Optional[List[str]] = None, flash_category: str = 'error',
                 field_errors: Optional[Dict[str, List[str]]] = None):
        super().__init__(
            message=message,
            details=details,
            status_code=status_code,
            title=title,
            flash_category=flash_category,
            field_errors=field_errors
        )


# Utility function to create dynamic exceptions
def create_exception(exception_type: str, message: str, **kwargs) -> AppException:
    """
    Factory function to create exceptions dynamically.

    Args:
        exception_type: Type of exception ('not_found', 'validation', 'unauthorized', etc.)
        message: Custom message for the exception
        **kwargs: Additional parameters (details, status_code, field_errors, etc.)

    Usage:
        raise create_exception('not_found', f"Product with id {product_id} not found")
        raise create_exception('validation', "Invalid input", details=["Email required"],
                             field_errors={"email": ["Invalid format"]})
    """

    exception_map = {
        'not_found': NotFoundException,
        'already_exists': AlreadyExistsException,
        'validation': ValidationException,
        'unauthorized': UnauthorizedException,
        'forbidden': ForbiddenException,
        'conflict': ConflictException,
        'bad_request': BadRequestException,
        'internal_server': InternalServerException,
        'service_unavailable': ServiceUnavailableException,
        'rate_limit': RateLimitExceededException,
        'custom': CustomException
    }

    exception_class = exception_map.get(exception_type, CustomException)

    if exception_type == 'custom':
        return exception_class(message, **kwargs)
    else:
        return exception_class(message, kwargs.get('details'), kwargs.get('field_errors'))


# Context manager for exception handling
class ExceptionHandler:
    """
    Context manager for handling exceptions with custom logic.

    Usage:
        with ExceptionHandler('product') as handler:
            # Some operation that might fail
            product = get_product(product_id)
            handler.not_found_if_none(product, f"Product with id {product_id} not found")
    """

    def __init__(self, context_name: str = "operation"):
        self.context_name = context_name

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Handle any unhandled exceptions here if needed
        return False

    def not_found_if_none(self, obj: Any, message: str):
        """Raise NotFoundException if object is None"""
        if obj is None:
            raise NotFoundException(message)
        return obj

    def validation_check(self, condition: bool, message: str, details: Optional[List[str]] = None,
                         field_errors: Optional[Dict[str, List[str]]] = None):
        """Raise ValidationException if condition is False"""
        if not condition:
            raise ValidationException(message, details, field_errors)

    def already_exists_check(self, obj: Any, message: str):
        """Raise AlreadyExistsException if object exists (is not None)"""
        if obj is not None:
            raise AlreadyExistsException(message)

    def unauthorized_check(self, condition: bool, message: str):
        """Raise UnauthorizedException if condition is False"""
        if not condition:
            raise UnauthorizedException(message)

    def forbidden_check(self, condition: bool, message: str):
        """Raise ForbiddenException if condition is False"""
        if not condition:
            raise ForbiddenException(message)