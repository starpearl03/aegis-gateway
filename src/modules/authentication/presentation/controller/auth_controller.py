from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from src.modules.authentication.domain.repositories.user_repository import UserRepository
from src.modules.authentication.domain.services.auth_service import AuthenticationService
from src.modules.authentication.presentation.dtos.authentication import (
    RegisterRequest, LoginRequest, LogoutRequest
)

from src.modules.authentication.domain.models.user import User
from src.shared.configs.blueprint_registry import register_blueprint
from src.shared.configs.security.session_decorators import SessionAuthDecorators
from src.shared.configs.security.session_manager import SessionManager
from src.shared.configs.exceptions.exceptions import AppException

# Create blueprint
auth_bp = Blueprint(
    'auth',
    __name__,
    template_folder='../templates',
    url_prefix='/'
)

# Register blueprint automatically
register_blueprint(auth_bp)

# Initialize services
auth_service = AuthenticationService()
user_repository = UserRepository()
session_manager = SessionManager[User](user_repository)

# Initialize auth decorators
auth = SessionAuthDecorators(
    session_manager=session_manager,
    unauthorized_url='/auth/login',
    home_url='/dashboard'
)


# Context processor to inject current user
@auth_bp.app_context_processor
def inject_current_user():
    """Inject current user into all templates"""
    return {
        'current_user': session_manager.get_current_user()
    }


# =============================================================================
# LOGIN ROUTES
# =============================================================================
@auth_bp.route('/', methods=['GET', 'POST'])
def login():
    """User login page"""
    if request.method == 'GET':
        return render_template('auth/login.jinja2')

    try:
        # POST - Collect form data
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        remember = request.form.get('remember', 'off') == 'on'

        # Create login request
        login_request = LoginRequest(email=email, password=password)

        # Authenticate user
        response = auth_service.login(login_request)

        # Get user and store in session
        user = user_repository.find_by_email(email)
        session_manager.login_user(user)

        # Handle remember me
        if remember:
            session.permanent = True

        # Success message and redirect
        flash(f'Welcome back, {response.first_name}!', 'success')
        return redirect(url_for('dashboard'))

    except AppException as e:
        # AppException already flashed the message in constructor
        # Stay on login page to show toast
        return render_template('auth/login.jinja2'), e.status_code

    # Let other exceptions bubble up to global error handler
    # (no except Exception - so they propagate)


# =============================================================================
# REGISTRATION ROUTES
# =============================================================================
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page"""
    if request.method == 'GET':
        return render_template('auth/register.jinja2')

    try:
        # POST - Collect form data
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        role = request.form.get('role', None)

        # Create registration request
        register_request = RegisterRequest(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=role
        )

        # Register user
        response = auth_service.register(register_request)

        # Auto-login after registration
        user = user_repository.find_by_email(email)
        session_manager.login_user(user)

        # Success message and redirect
        flash(f'Registration successful! Welcome, {response.first_name}!', 'success')
        return redirect(url_for('dashboard'))

    except AppException as e:
        # AppException already flashed the message in constructor
        # Stay on registration page to show toast
        return render_template('auth/register.jinja2'), e.status_code

    # Let other exceptions bubble up to global error handler


# =============================================================================
# LOGOUT ROUTES
# =============================================================================
@auth_bp.route('/logout', methods=['GET', 'POST'])
@auth.login_required
def logout():
    """Logout user and clear session"""
    try:
        # Get current user ID
        user_id = session_manager.get_current_user_id()

        # Create logout request
        logout_request = LogoutRequest(user_id=user_id)

        # Call logout service
        response = auth_service.logout(logout_request)

        # Clear session
        session_manager.logout_user()

        flash(response.message, 'success')
        return redirect(url_for('auth.login'))

    except AppException as e:
        # Always clear session even if error occurs
        session_manager.logout_user()
        return redirect(url_for('auth.login'))

    except Exception:
        # For unexpected errors, still clear session then re-raise
        session_manager.logout_user()
        raise  # Let global handler deal with it