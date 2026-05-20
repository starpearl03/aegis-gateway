from flask import session
from typing import Optional, TypeVar, Generic, runtime_checkable

from src.shared.configs.security.user_auth_protocol import AuthUserProtocol
from src.shared.data.base.repository import BaseRepository


# Type variable constrained to BaseModel and SessionUserProtocol
T = TypeVar('T', bound='BaseModel')


class SessionManager(Generic[T]):
    """
    Generic session manager for handling user authentication sessions.

    Stores and retrieves logged-in user data from Flask session.
    Works with any model that implements SessionUserProtocol.

    Type Parameters:
        T: The model type that extends BaseModel and implements SessionUserProtocol

    Example:
        # In your application setup
        user_session_manager = SessionManager[User](UserRepository())

        # Usage
        user_session_manager.login_user(user)
        current_user = user_session_manager.get_current_user()  # Returns Optional[User]
    """

    def __init__(self, repository: BaseRepository[T]) -> None:
        """
        Initialize the session manager with a repository.

        Args:
            repository: Repository instance for the model type T
        """
        self.repository = repository
        self.SESSION_USER_KEY = 'user_id'
        self.SESSION_USER_ROLE_KEY = 'user_role'
        self.SESSION_USER_EMAIL_KEY = 'user_email'
        self.SESSION_USER_NAME_KEY = 'user_name'

    def login_user(self, user: T) -> None:
        """
        Store user data in session after successful login.

        The user must implement SessionUserProtocol to ensure
        it has the required attributes.

        Args:
            user: User object to store in session

        Raises:
            AttributeError: If user doesn't implement SessionUserProtocol
        """
        # Runtime check to ensure user has required attributes
        if not isinstance(user, AuthUserProtocol):
            raise AttributeError(
                f"User model must implement SessionUserProtocol. "
                f"Missing required attributes: email, first_name, last_name, or role"
            )

        session[self.SESSION_USER_KEY] = user.id
        session[self.SESSION_USER_ROLE_KEY] = user.role.value
        session[self.SESSION_USER_EMAIL_KEY] = user.email
        session[self.SESSION_USER_NAME_KEY] = f"{user.first_name} {user.last_name}"
        session.permanent = True

    def logout_user(self) -> None:
        """
        Clear user data from session (logout).
        """
        session.pop(self.SESSION_USER_KEY, None)
        session.pop(self.SESSION_USER_ROLE_KEY, None)
        session.pop(self.SESSION_USER_EMAIL_KEY, None)
        session.pop(self.SESSION_USER_NAME_KEY, None)
        session.clear()

    def is_authenticated(self) -> bool:
        """
        Check if user is authenticated (logged in).

        Returns:
            bool: True if user is logged in, False otherwise
        """
        return self.SESSION_USER_KEY in session and session[self.SESSION_USER_KEY] is not None

    def get_current_user(self) -> Optional[T]:
        """
        Get current logged-in user object.

        Returns fresh data from the database using the injected repository.

        Returns:
            User object of type T if logged in, None otherwise
        """
        if not self.is_authenticated():
            return None

        user_id = session.get(self.SESSION_USER_KEY)
        if not user_id:
            return None

        # Get fresh user data from database using injected repository
        return self.repository.find_by_id(user_id)

    def get_current_user_id(self) -> Optional[str]:
        """
        Get current user ID from session (lightweight).

        Returns:
            User ID string if logged in, None otherwise
        """
        return session.get(self.SESSION_USER_KEY)

    def get_current_user_role(self) -> Optional[str]:
        """
        Get current user role from session (lightweight).

        Returns:
            User role string if logged in, None otherwise
        """
        return session.get(self.SESSION_USER_ROLE_KEY)

    def get_current_user_email(self) -> Optional[str]:
        """
        Get current user email from session (lightweight).

        Returns:
            User email string if logged in, None otherwise
        """
        return session.get(self.SESSION_USER_EMAIL_KEY)

    def get_current_user_name(self) -> Optional[str]:
        """
        Get current user full name from session (lightweight).

        Returns:
            User full name string if logged in, None otherwise
        """
        return session.get(self.SESSION_USER_NAME_KEY)

    def has_role(self, role_value: str) -> bool:
        """
        Check if current user has a specific role.

        Generic role checking method that works with any role value
        defined by the application.

        Args:
            role_value: The role value to check against

        Returns:
            bool: True if current user has the specified role, False otherwise

        Example:
            if session_manager.has_role('admin'):
                # User is admin

            if session_manager.has_role('customer'):
                # User is customer
        """
        current_role = self.get_current_user_role()
        if not current_role:
            return False
        return current_role.lower() == role_value.lower()

    def refresh_session(self) -> None:
        """
        Refresh session data with latest user information from database.

        Useful when user data is updated and you want to sync the session
        with the current database state.
        """
        if not self.is_authenticated():
            return

        user = self.get_current_user()
        if user:
            # Update session with fresh data
            self.login_user(user)