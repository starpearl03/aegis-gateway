from typing import List, Dict, Optional, Any


class ErrorDetail:
    """
    Represents detailed error information for API responses.
    Supports both general error messages and field-specific errors.

    Usage:
        # Simple usage with string list (backward compatible)
        error = ErrorDetail(
            title="Validation Failed",
            details=["Invalid input data", "Missing required fields"],
            status=400
        )

        # With field-specific errors
        error = ErrorDetail(
            title="Validation Failed",
            details=["Form validation failed"],
            status=400
        )
        error.add_field_error("email", "Invalid email format")
        error.add_field_error("email", "Email already exists")
        error.add_field_error("password", "Must be at least 8 characters")

        # Mixed usage
        error = ErrorDetail(
            title="Registration Failed",
            details=["Account creation failed"],
            status=400,
            field_errors={
                "email": ["Invalid format", "Already in use"],
                "username": ["Contains invalid characters"]
            }
        )
    """

    def __init__(
        self,
        title: str,
        details: Optional[List[str]] = None,
        status: int = 400,
        field_errors: Optional[Dict[str, List[str]]] = None
    ):
        """
        Initialize error detail.

        Args:
            title: Main error title/heading
            details: List of general error messages
            status: HTTP status code (default: 400)
            field_errors: Dictionary of field-specific errors
        """
        self.title = title
        self.details = details if details else []
        self.status = status
        self.field_errors = field_errors if field_errors else {}

    def add_detail(self, detail: str) -> None:
        """
        Add a general error detail.

        Args:
            detail: General error message to add
        """
        self.details.append(detail)

    def add_field_error(self, field: str, error: str) -> None:
        """
        Add a field-specific error.

        Args:
            field: Name of the field with the error
            error: Error message for the field

        Usage:
            error_detail.add_field_error("email", "Invalid email format")
            error_detail.add_field_error("password", "Too short")
        """
        if field not in self.field_errors:
            self.field_errors[field] = []
        self.field_errors[field].append(error)

    def add_field_errors(self, field: str, errors: List[str]) -> None:
        """
        Add multiple errors for a specific field.

        Args:
            field: Name of the field with errors
            errors: List of error messages for the field

        Usage:
            error_detail.add_field_errors("email", [
                "Invalid format",
                "Already exists in system"
            ])
        """
        if field not in self.field_errors:
            self.field_errors[field] = []
        self.field_errors[field].extend(errors)

    def has_details(self) -> bool:
        """Check if error has any general details."""
        return len(self.details) > 0

    def has_field_errors(self) -> bool:
        """Check if error has any field-specific errors."""
        return len(self.field_errors) > 0

    def has_errors(self) -> bool:
        """Check if error has any details or field errors."""
        return self.has_details() or self.has_field_errors()

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert error detail to dictionary.

        Returns:
            Dictionary with title, details, field_errors, and status
        """
        result: Dict[str, Any] = {
            'title': self.title,
            'status': self.status
        }

        # Only include details if present
        if self.details:
            result['details'] = self.details

        # Only include field_errors if present
        if self.field_errors:
            result['field_errors'] = self.field_errors

        return result

    def __str__(self) -> str:
        """String representation of error detail."""
        parts = [f"{self.title} (Status: {self.status})"]

        if self.details:
            parts.append(f"Details: {', '.join(self.details)}")

        if self.field_errors:
            field_error_strs = []
            for field, errors in self.field_errors.items():
                field_error_strs.append(f"{field}: {', '.join(errors)}")
            parts.append(f"Field Errors: {'; '.join(field_error_strs)}")

        return " | ".join(parts)

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return (f"ErrorDetail(title='{self.title}', "
                f"details={self.details}, "
                f"field_errors={self.field_errors}, "
                f"status={self.status})")