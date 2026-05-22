from dataclasses import dataclass
from typing import Dict, Any, Optional
import re

from src.shared.configs.exceptions.exceptions import ValidationException


# ============ Registration Feature ============

@dataclass
class RegisterRequest:
    """DTO for user registration."""
    email: str
    password: str
    first_name: str
    last_name: str
    role: Optional[str] = None

    def __post_init__(self):
        """Validate registration data after initialization."""
        self._validate_email(self.email)
        self._validate_password(self.password)
        self._validate_name(self.first_name, "First name")
        self._validate_name(self.last_name, "Last name")

    @staticmethod
    def _validate_email(email: str) -> None:
        """Validate email format."""
        if not email:
            raise ValidationException("Email cannot be empty")

        # Email validation using regex
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise ValidationException("Invalid email format")

        if len(email) > 255:
            raise ValidationException("Email is too long")

    @staticmethod
    def _validate_password(password: str) -> None:
        """Validate password strength."""
        if not password:
            raise ValidationException("Password cannot be empty")

        if len(password) < 8:
            raise ValidationException("Password must be at least 8 characters long")

        if len(password) > 128:
            raise ValidationException("Password is too long")

        if not any(char.isdigit() for char in password):
            raise ValidationException("Password must contain at least one number")

        if not any(char.isupper() for char in password):
            raise ValidationException("Password must contain at least one uppercase letter")

        if not any(char.islower() for char in password):
            raise ValidationException("Password must contain at least one lowercase letter")

    @staticmethod
    def _validate_name(name: str, field_name: str = "Name") -> None:
        """Validate name field (first name or last name)."""
        if not name or not name.strip():
            raise ValidationException(f"{field_name} cannot be empty")

        if len(name.strip()) < 2:
            raise ValidationException(f"{field_name} must be at least 2 characters long")

        if len(name) > 255:
            raise ValidationException(f"{field_name} is too long")

        # Allow letters, spaces, hyphens, apostrophes
        if not re.match(r"^[a-zA-Z\s\-']+$", name):
            raise ValidationException(f"{field_name} contains invalid characters")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'email': self.email,
            'password': self.password,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'role': self.role
        }


@dataclass
class RegisterResponse:
    """DTO for registration response."""
    message: str
    id: str
    email: str
    first_name: str
    last_name: str
    role: str
    is_active: bool
    created_at: str
    updated_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'message': self.message,
            'user': {
                'id': self.id,
                'email': self.email,
                'first_name': self.first_name,
                'last_name': self.last_name,
                'role': self.role,
                'is_active': self.is_active,
                'created_at': self.created_at,
                'updated_at': self.updated_at
            }
        }


# ============ Login Feature ============

@dataclass
class LoginRequest:
    """DTO for user login."""
    email: str
    password: str

    def __post_init__(self):
        """Validate login data after initialization."""
        self._validate_email(self.email)
        self._validate_password(self.password)

    @staticmethod
    def _validate_email(email: str) -> None:
        """Validate email format."""
        if not email:
            raise ValidationException("Email cannot be empty")

        # Email validation using regex
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise ValidationException("Invalid email format")

        if len(email) > 255:
            raise ValidationException("Email is too long")

    @staticmethod
    def _validate_password(password: str) -> None:
        """Validate password is provided."""
        if not password:
            raise ValidationException("Password cannot be empty")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'email': self.email,
            'password': self.password
        }


@dataclass
class LoginResponse:
    """DTO for login response."""
    message: str
    id: str
    email: str
    first_name: str
    last_name: str
    role: str
    is_active: bool
    created_at: str
    updated_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'message': self.message,
            'user': {
                'id': self.id,
                'email': self.email,
                'first_name': self.first_name,
                'last_name': self.last_name,
                'role': self.role,
                'is_active': self.is_active,
                'created_at': self.created_at,
                'updated_at': self.updated_at
            }
        }


# ============ Logout Feature ============

@dataclass
class LogoutRequest:
    """DTO for logout request."""
    user_id: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {'user_id': self.user_id}


@dataclass
class LogoutResponse:
    """DTO for logout response."""
    message: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {'message': self.message}