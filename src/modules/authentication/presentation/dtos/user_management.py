from dataclasses import dataclass
from typing import Dict, Any, Optional, List
import re

from src.shared.configs.exceptions.exceptions import ValidationException


# ============ Create User Feature ============

@dataclass
class CreateUserRequest:
    """DTO for admin creating a new user."""
    email: str
    password: str
    first_name: str
    last_name: str
    role: str
    is_active: Optional[bool] = True

    def __post_init__(self):
        """Validate user data after initialization."""
        self._validate_email(self.email)
        self._validate_password(self.password)
        self._validate_name(self.first_name, "First name")
        self._validate_name(self.last_name, "Last name")

    @staticmethod
    def _validate_email(email: str) -> None:
        """Validate email format."""
        if not email:
            raise ValidationException("Email cannot be empty")
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
        """Validate name field."""
        if not name or not name.strip():
            raise ValidationException(f"{field_name} cannot be empty")
        if len(name.strip()) < 2:
            raise ValidationException(f"{field_name} must be at least 2 characters long")
        if len(name) > 255:
            raise ValidationException(f"{field_name} is too long")
        if not re.match(r"^[a-zA-Z\s\-']+$", name):
            raise ValidationException(f"{field_name} contains invalid characters")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'email': self.email,
            'password': self.password,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'role': self.role,
            'is_active': self.is_active
        }


@dataclass
class CreateUserResponse:
    """DTO for create user response."""
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


# ============ Update User Feature ============

@dataclass
class UpdateUserRequest:
    """DTO for updating user details."""
    user_id: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None  # Optional password update

    def __post_init__(self):
        """Validate update data after initialization."""
        if not self.user_id:
            raise ValidationException("User ID is required")

        # Validate only provided fields
        if self.email is not None:
            self._validate_email(self.email)
        if self.first_name is not None:
            self._validate_name(self.first_name, "First name")
        if self.last_name is not None:
            self._validate_name(self.last_name, "Last name")
        if self.password is not None:
            self._validate_password(self.password)

    @staticmethod
    def _validate_email(email: str) -> None:
        """Validate email format."""
        if not email:
            raise ValidationException("Email cannot be empty")
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
        """Validate name field."""
        if not name or not name.strip():
            raise ValidationException(f"{field_name} cannot be empty")
        if len(name.strip()) < 2:
            raise ValidationException(f"{field_name} must be at least 2 characters long")
        if len(name) > 255:
            raise ValidationException(f"{field_name} is too long")
        if not re.match(r"^[a-zA-Z\s\-']+$", name):
            raise ValidationException(f"{field_name} contains invalid characters")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        data = {
            'user_id': self.user_id
        }
        if self.email is not None:
            data['email'] = self.email
        if self.first_name is not None:
            data['first_name'] = self.first_name
        if self.last_name is not None:
            data['last_name'] = self.last_name
        if self.role is not None:
            data['role'] = self.role
        if self.is_active is not None:
            data['is_active'] = self.is_active
        if self.password is not None:
            data['password'] = self.password
        return data


@dataclass
class UpdateUserResponse:
    """DTO for update user response."""
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


# ============ Delete User Feature ============

@dataclass
class DeleteUserRequest:
    """DTO for deleting a user."""
    user_id: str

    def __post_init__(self):
        """Validate request data."""
        if not self.user_id:
            raise ValidationException("User ID is required")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {'user_id': self.user_id}


@dataclass
class DeleteUserResponse:
    """DTO for delete user response."""
    message: str
    user_id: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'message': self.message,
            'user_id': self.user_id
        }


# ============ List Users Feature ============

@dataclass
class ListUsersRequest:
    """DTO for listing users with pagination."""
    page: int = 1
    per_page: int = 20
    role: Optional[str] = None
    is_active: Optional[bool] = None
    include_deleted: bool = False

    def __post_init__(self):
        """Validate pagination parameters."""
        if self.page < 1:
            raise ValidationException("Page must be at least 1")
        if self.per_page < 1 or self.per_page > 100:
            raise ValidationException("Per page must be between 1 and 100")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = {
            'page': self.page,
            'per_page': self.per_page,
            'include_deleted': self.include_deleted
        }
        if self.role is not None:
            data['role'] = self.role
        if self.is_active is not None:
            data['is_active'] = self.is_active
        return data


@dataclass
class UserData:
    """DTO for individual user data in list."""
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
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


@dataclass
class ListUsersResponse:
    """DTO for list users response with pagination."""
    message: str
    users: List[UserData]
    total: int
    page: int
    per_page: int
    total_pages: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'message': self.message,
            'users': [user.to_dict() for user in self.users],
            'pagination': {
                'total': self.total,
                'page': self.page,
                'per_page': self.per_page,
                'total_pages': self.total_pages
            }
        }


# ============ Get Single User Feature ============

@dataclass
class GetUserRequest:
    """DTO for getting a single user."""
    user_id: str

    def __post_init__(self):
        """Validate request data."""
        if not self.user_id:
            raise ValidationException("User ID is required")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {'user_id': self.user_id}


@dataclass
class GetUserResponse:
    """DTO for get user response."""
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