from functools import wraps
from flask import redirect, flash
from typing import TypeVar, Optional, Callable

from src.shared.configs.security.session_manager import SessionManager
from src.shared.data.base.model import BaseModel

T = TypeVar('T', bound=BaseModel)


class SessionAuthDecorators:
    """Authentication and authorization decorators for Flask routes."""

    def __init__(
        self,
        session_manager: SessionManager[T],
        unauthorized_url: str = '/auth/login',
        home_url: str = '/'
    ) -> None:
        """
        Initialize auth decorators with session manager and default redirect URLs.

        Args:
            session_manager: SessionManager instance for user authentication
            unauthorized_url: Default URL for unauthenticated/unauthorized access
            home_url: Default URL for redirecting already authenticated users
        """
        self.session_manager = session_manager
        self.unauthorized_url = unauthorized_url
        self.home_url = home_url

    def login_required(self, f: Optional[Callable] = None, redirect_to: Optional[str] = None):
        """
        Require user authentication.

        Args:
            f: Function to decorate
            redirect_to: Optional URL to redirect to (overrides unauthorized_url)

        Usage:
            @auth.login_required
            def protected_route():
                pass

            @auth.login_required(redirect_to='/custom/login')
            def another_route():
                pass
        """
        def decorator(func):
            @wraps(func)
            def decorated_function(*args, **kwargs):
                if not self.session_manager.is_authenticated():
                    flash('Please log in to access this page', 'error')
                    return redirect(redirect_to or self.unauthorized_url)
                return func(*args, **kwargs)
            return decorated_function

        # Handle both @auth.login_required and @auth.login_required(redirect_to='...')
        if f is None:
            return decorator
        return decorator(f)

    def role_required(self, *allowed_roles: str, redirect_to: Optional[str] = None):
        """
        Require specific role(s).

        Args:
            *allowed_roles: One or more role values that are allowed
            redirect_to: Optional URL to redirect to (overrides unauthorized_url)

        Usage:
            @auth.role_required('admin')
            def admin_route():
                pass

            @auth.role_required('admin', 'moderator')
            def multi_role_route():
                pass
        """

        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if not self.session_manager.is_authenticated():
                    flash('Please log in to access this page', 'error')
                    return redirect(redirect_to or self.unauthorized_url)

                current_role = self.session_manager.get_current_user_role()
                normalized_allowed = [r.lower() for r in allowed_roles]

                if current_role.lower() not in normalized_allowed:
                    flash('You do not have permission to access this page', 'error')
                    return redirect(redirect_to or self.unauthorized_url)

                return f(*args, **kwargs)

            return decorated_function

        return decorator

    def guest_only(self, f: Optional[Callable] = None, redirect_to: Optional[str] = None):
        """
        Allow only non-authenticated users.

        Args:
            f: Function to decorate
            redirect_to: Optional URL to redirect to (overrides home_url)

        Usage:
            @auth.guest_only
            def login():
                pass

            @auth.guest_only(redirect_to='/dashboard')
            def register():
                pass
        """
        def decorator(func):
            @wraps(func)
            def decorated_function(*args, **kwargs):
                if self.session_manager.is_authenticated():
                    flash('You are already logged in', 'info')
                    return redirect(redirect_to or self.home_url)
                return func(*args, **kwargs)
            return decorated_function

        # Handle both @auth.guest_only and @auth.guest_only(redirect_to='...')
        if f is None:
            return decorator
        return decorator(f)