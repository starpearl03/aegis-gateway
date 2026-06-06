from flask import Blueprint, render_template, request, flash, jsonify

from src.modules.authentication.domain.repositories.user_repository import UserRepository
from src.modules.authentication.domain.services.user_management_service import UserManagementService
from src.modules.authentication.presentation.dtos.user_management import (
    CreateUserRequest, UpdateUserRequest, DeleteUserRequest,
    ListUsersRequest, GetUserRequest
)

from src.modules.authentication.domain.models.user import User
from src.shared.configs.security.session_decorators import SessionAuthDecorators
from src.shared.configs.security.session_manager import SessionManager
from src.shared.configs.exceptions.exceptions import AppException

# Create blueprint
user_management_bp = Blueprint(
    'user_management',
    __name__,
    template_folder='../templates',
    url_prefix='/users'
)


# Initialize services
user_management_service = UserManagementService()
user_repository = UserRepository()
session_manager = SessionManager[User](user_repository)

# Initialize auth decorators
auth = SessionAuthDecorators(
    session_manager=session_manager,
    unauthorized_url='/',
    home_url='/dashboard'
)


# Context processor to inject current user
@user_management_bp.app_context_processor
def inject_current_user():
    """Inject current user into all templates"""
    return {
        'current_user': session_manager.get_current_user()
    }


# =============================================================================
# LIST USERS ROUTE (Main Page)
# =============================================================================
@user_management_bp.route('/', methods=['GET'])
@auth.login_required
@auth.role_required('admin')
def list_users():
    """List all users with pagination and filtering"""
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        role = request.args.get('role', None, type=str)
        is_active = request.args.get('is_active', None, type=str)
        include_deleted = request.args.get('include_deleted', 'false', type=str).lower() == 'true'

        # Convert is_active string to boolean if provided
        is_active_bool = None
        if is_active is not None and is_active.lower() in ['true', 'false']:
            is_active_bool = is_active.lower() == 'true'

        # Create list request
        list_request = ListUsersRequest(
            page=page,
            per_page=per_page,
            role=role,
            is_active=is_active_bool,
            include_deleted=include_deleted
        )

        # Get users
        response = user_management_service.list_users(list_request)

        return render_template(
            'user_management/list.jinja2',
            users=response.users,
            pagination={
                'total': response.total,
                'page': response.page,
                'per_page': response.per_page,
                'total_pages': response.total_pages
            },
            filters={
                'role': role,
                'is_active': is_active,
                'include_deleted': include_deleted
            }
        )

    except AppException as e:
        # AppException already flashed the message in constructor
        return render_template('user_management/list.jinja2', users=[], pagination={}), e.status_code

    # Let other exceptions bubble up to global error handler


# =============================================================================
# CREATE USER ROUTE (AJAX - for modal)
# =============================================================================
@user_management_bp.route('/create', methods=['POST'])
@auth.login_required
@auth.role_required('admin')
def create_user():
    """Create a new user (AJAX endpoint for modal)"""
    try:
        # POST - Collect form data
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        role = request.form.get('role', '').strip()
        is_active = request.form.get('is_active', 'on') == 'on'

        # Create user request
        create_request = CreateUserRequest(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=role,
            is_active=is_active
        )

        # Create user
        response = user_management_service.create_user(create_request)

        # Success message and return JSON
        flash(f'User {response.email} created successfully!', 'success')

        return jsonify({
            'success': True,
            'message': f'User {response.email} created successfully!',
            'user': response.to_dict()['user']
        }), 201

    except AppException as e:
        # AppException already flashed the message in constructor
        return jsonify({
            'success': False,
            'message': str(e)
        }), e.status_code

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }), 500


# =============================================================================
# VIEW USER ROUTE (AJAX - for modal)
# =============================================================================
@user_management_bp.route('/<string:user_id>', methods=['GET'])
@auth.login_required
@auth.role_required('admin')
def view_user(user_id):
    """View a single user's details (AJAX endpoint for modal)"""
    try:
        # Create get user request
        get_request = GetUserRequest(user_id=user_id)

        # Get user
        response = user_management_service.get_user(get_request)

        return jsonify({
            'success': True,
            'user': response.to_dict()['user']
        }), 200

    except AppException as e:
        # AppException already flashed the message in constructor
        return jsonify({
            'success': False,
            'message': str(e)
        }), e.status_code

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }), 500


# =============================================================================
# EDIT USER ROUTE (AJAX - for modal)
# =============================================================================
@user_management_bp.route('/<string:user_id>/edit', methods=['GET', 'POST'])
@auth.login_required
@auth.role_required('admin')
def edit_user(user_id):
    """Edit an existing user (AJAX endpoint for modal)"""

    # GET - Return user data for the form
    if request.method == 'GET':
        try:
            # Get user data for the form
            get_request = GetUserRequest(user_id=user_id)
            response = user_management_service.get_user(get_request)

            return jsonify({
                'success': True,
                'user': response.to_dict()['user']
            }), 200

        except AppException as e:
            # AppException already flashed the message in constructor
            return jsonify({
                'success': False,
                'message': str(e)
            }), e.status_code

        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'An error occurred: {str(e)}'
            }), 500

    # POST - Update user
    try:
        # POST - Collect form data
        email = request.form.get('email', '').strip()
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        role = request.form.get('role', '').strip()
        is_active = request.form.get('is_active', 'off') == 'on'
        password = request.form.get('password', '').strip()

        # Create update request (only include fields that were provided)
        update_request = UpdateUserRequest(
            user_id=user_id,
            email=email if email else None,
            first_name=first_name if first_name else None,
            last_name=last_name if last_name else None,
            role=role if role else None,
            is_active=is_active,
            password=password if password else None
        )

        # Update user
        response = user_management_service.update_user(update_request)

        # Success message and return JSON
        flash(f'User {response.email} updated successfully!', 'success')

        return jsonify({
            'success': True,
            'message': f'User {response.email} updated successfully!',
            'user': response.to_dict()['user']
        }), 200

    except AppException as e:
        # AppException already flashed the message in constructor
        return jsonify({
            'success': False,
            'message': str(e)
        }), e.status_code

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }), 500


# =============================================================================
# DELETE USER ROUTE (AJAX)
# =============================================================================
@user_management_bp.route('/<string:user_id>/delete', methods=['POST'])
@auth.login_required
@auth.role_required('admin')
def delete_user(user_id):
    """Delete a user (soft delete) - AJAX endpoint"""
    try:
        # Prevent self-deletion
        current_user_id = session_manager.get_current_user_id()
        if user_id == current_user_id:
            flash('You cannot delete your own account', 'error')
            return jsonify({
                'success': False,
                'message': 'You cannot delete your own account'
            }), 400

        # Create delete request
        delete_request = DeleteUserRequest(user_id=user_id)

        # Delete user
        response = user_management_service.delete_user(delete_request)

        # Success message and return JSON
        flash(response.message, 'success')

        return jsonify({
            'success': True,
            'message': response.message
        }), 200

    except AppException as e:
        # AppException already flashed the message in constructor
        return jsonify({
            'success': False,
            'message': str(e)
        }), e.status_code

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }), 500


# =============================================================================
# TOGGLE USER STATUS ROUTE (AJAX)
# =============================================================================
@user_management_bp.route('/<string:user_id>/toggle-status', methods=['POST'])
@auth.login_required
@auth.role_required('admin')
def toggle_user_status(user_id):
    """Toggle user active status (activate/deactivate) - AJAX endpoint"""
    try:
        # Prevent self-deactivation
        current_user_id = session_manager.get_current_user_id()
        if user_id == current_user_id:
            flash('You cannot deactivate your own account', 'error')
            return jsonify({
                'success': False,
                'message': 'You cannot deactivate your own account'
            }), 400

        # Get current user
        get_request = GetUserRequest(user_id=user_id)
        user_response = user_management_service.get_user(get_request)
        user_data = user_response.to_dict()['user']

        # Toggle status
        new_status = not user_data['is_active']

        # Update user
        update_request = UpdateUserRequest(
            user_id=user_id,
            is_active=new_status
        )

        response = user_management_service.update_user(update_request)

        # Success message
        status_text = 'activated' if new_status else 'deactivated'
        flash(f'User {response.email} {status_text} successfully!', 'success')

        return jsonify({
            'success': True,
            'message': f'User {response.email} {status_text} successfully!',
            'user': response.to_dict()['user']
        }), 200

    except AppException as e:
        # AppException already flashed the message in constructor
        return jsonify({
            'success': False,
            'message': str(e)
        }), e.status_code

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }), 500