from typing import Optional, List

from src.modules.authentication.domain.models.user import User, UserRole
from src.shared.data.base.repository import BaseRepository


class UserRepository(BaseRepository[User]):
    """
    Repository for User model operations.
    Extends BaseRepository with user-specific queries only.
    """

    def __init__(self):
        super().__init__(User)

    def find_by_email(self, email: str) -> Optional[User]:
        """
        Find a user by email address.

        Args:
            email: Email address to search for

        Returns:
            User if found, None otherwise
        """
        return self.find_one_by({"email": email})

    def find_by_role(self, role: UserRole) -> List[User]:
        """
        Find all users with a specific role.

        Args:
            role: UserRole to filter by

        Returns:
            List of users with the specified role
        """
        return self.find_many_by({"role": role})

    def authenticate(self, email: str, password: str) -> Optional[User]:
        """
        Authenticate a user with email and password.

        Args:
            email: Email address of the user
            password: Password to verify

        Returns:
            User if authentication successful, None otherwise
        """
        user = self.find_by_email(email)

        if user and user.check_password(password):
            return user

        return None

    def email_exists(self, email: str) -> bool:
        """
        Check if an email address is already registered.

        Args:
            email: Email address to check

        Returns:
            True if email exists, False otherwise
        """
        return self.exists({"email": email})

    def get_active_users(self) -> List[User]:
        """
        Get all active users.

        Returns:
            List of active users
        """
        return self.find_many_by({"is_active": True})

    def get_inactive_users(self) -> List[User]:
        """
        Get all inactive users.

        Returns:
            List of inactive users
        """
        return self.find_many_by({"is_active": False})