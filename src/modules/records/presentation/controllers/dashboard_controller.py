from flask import Blueprint, render_template, request, jsonify
from datetime import datetime, timedelta

from src.modules.records.internal.statistics_utils import StatisticsUtils
from src.modules.records.presentation.dtos.record_management import GetStatisticsRequest

from src.modules.authentication.domain.models.user import User
from src.modules.authentication.domain.repositories.user_repository import UserRepository
from src.shared.configs.security.session_decorators import SessionAuthDecorators
from src.shared.configs.security.session_manager import SessionManager
from src.shared.configs.exceptions.exceptions import AppException
from src.shared.response.api_response import ApiResponse
from src.shared.response.error_detail import ErrorDetail

# Create blueprint
dashboard_bp = Blueprint(
    'dashboard',
    __name__,
    template_folder='../templates',
    url_prefix='/dashboard'
)

# Initialize services
statistics_utils = StatisticsUtils()
user_repository = UserRepository()
session_manager = SessionManager[User](user_repository)

# Initialize auth decorators
auth = SessionAuthDecorators(
    session_manager=session_manager,
    unauthorized_url='/',
    home_url='/dashboard'
)


# Context processor to inject current user
@dashboard_bp.app_context_processor
def inject_current_user():
    """Inject current user into all templates"""
    return {
        'current_user': session_manager.get_current_user()
    }


# =============================================================================
# DASHBOARD HOME ROUTE
# =============================================================================
@dashboard_bp.route('/', methods=['GET'])
@auth.login_required
def dashboard_home():
    """Main dashboard page with statistics overview"""
    try:
        # Get optional filters from query params
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', None)
        officer_id = request.args.get('officer_id', None)

        # Create statistics request
        stats_request = GetStatisticsRequest(
            start_date=start_date,
            end_date=end_date,
            officer_id=officer_id
        )

        # Get dashboard statistics
        stats_response = statistics_utils.get_dashboard_statistics(stats_request)

        return render_template(
            'dashboard/home.jinja2',
            statistics=stats_response.to_dict()['statistics'],
            filters={
                'start_date': start_date,
                'end_date': end_date,
                'officer_id': officer_id
            }
        )

    except AppException as e:
        return render_template(
            'dashboard/home.jinja2',
            statistics={},
            filters={}
        ), e.status_code


# =============================================================================
# GET STATISTICS API (AJAX)
# =============================================================================
@dashboard_bp.route('/statistics', methods=['GET'])
@auth.login_required
def get_statistics():
    """Get dashboard statistics - AJAX endpoint"""
    try:
        # Get optional filters from query params
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', None)
        officer_id = request.args.get('officer_id', None)

        # Create statistics request
        stats_request = GetStatisticsRequest(
            start_date=start_date,
            end_date=end_date,
            officer_id=officer_id
        )

        # Get dashboard statistics
        stats_response = statistics_utils.get_dashboard_statistics(stats_request)

        # Create success response
        response = ApiResponse.success(
            value=stats_response,
            message="Statistics retrieved successfully"
        )

        return jsonify(response.to_dict()), response.get_status_code()

    except AppException as e:
        error_detail = ErrorDetail(
            title="Statistics Retrieval Failed",
            details=[str(e)],
            status=e.status_code
        )
        response = ApiResponse.failure(
            error=error_detail,
            message=str(e)
        )
        return jsonify(response.to_dict()), response.get_status_code()

    except Exception as e:
        error_detail = ErrorDetail(
            title="Unexpected Error",
            details=[f"An error occurred: {str(e)}"],
            status=500
        )
        response = ApiResponse.failure(error=error_detail)
        return jsonify(response.to_dict()), response.get_status_code()


# =============================================================================
# GET OFFICER STATISTICS API (AJAX)
# =============================================================================
@dashboard_bp.route('/statistics/officer/<string:officer_id>', methods=['GET'])
@auth.login_required
@auth.role_required('admin', 'officer')
def get_officer_statistics(officer_id):
    """Get statistics for a specific officer - AJAX endpoint"""
    try:
        # Verify user can access these statistics
        current_user_id = session_manager.get_current_user_id()
        current_user = session_manager.get_current_user()

        # Only admins or the officer themselves can view officer statistics
        if current_user.role != 'admin' and current_user_id != officer_id:
            error_detail = ErrorDetail(
                title="Access Denied",
                details=["You don't have permission to view these statistics"],
                status=403
            )
            response = ApiResponse.failure(error=error_detail)
            return jsonify(response.to_dict()), response.get_status_code()

        # Get officer statistics
        stats_response = statistics_utils.get_officer_statistics(officer_id)

        # Create success response
        response = ApiResponse.success(
            value=stats_response,
            message="Officer statistics retrieved successfully"
        )

        return jsonify(response.to_dict()), response.get_status_code()

    except AppException as e:
        error_detail = ErrorDetail(
            title="Statistics Retrieval Failed",
            details=[str(e)],
            status=e.status_code
        )
        response = ApiResponse.failure(
            error=error_detail,
            message=str(e)
        )
        return jsonify(response.to_dict()), response.get_status_code()

    except Exception as e:
        error_detail = ErrorDetail(
            title="Unexpected Error",
            details=[f"An error occurred: {str(e)}"],
            status=500
        )
        response = ApiResponse.failure(error=error_detail)
        return jsonify(response.to_dict()), response.get_status_code()


# =============================================================================
# GET DATE RANGE STATISTICS API (AJAX)
# =============================================================================
@dashboard_bp.route('/statistics/date-range', methods=['GET'])
@auth.login_required
def get_date_range_statistics():
    """Get statistics for a specific date range - AJAX endpoint"""
    try:
        # Get date range from query params
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        if not start_date or not end_date:
            error_detail = ErrorDetail(
                title="Validation Error",
                details=["Both start_date and end_date are required"],
                status=400
            )
            response = ApiResponse.failure(error=error_detail)
            return jsonify(response.to_dict()), response.get_status_code()

        # Validate date format
        try:
            datetime.fromisoformat(start_date)
            datetime.fromisoformat(end_date)
        except ValueError:
            error_detail = ErrorDetail(
                title="Validation Error",
                details=["Invalid date format. Use ISO format (YYYY-MM-DD)"],
                status=400
            )
            response = ApiResponse.failure(error=error_detail)
            return jsonify(response.to_dict()), response.get_status_code()

        # Get statistics for date range
        stats_response = statistics_utils.get_statistics_by_date_range(
            start_date=start_date,
            end_date=end_date
        )

        # Create success response
        response = ApiResponse.success(
            value=stats_response,
            message="Date range statistics retrieved successfully"
        )

        return jsonify(response.to_dict()), response.get_status_code()

    except AppException as e:
        error_detail = ErrorDetail(
            title="Statistics Retrieval Failed",
            details=[str(e)],
            status=e.status_code
        )
        response = ApiResponse.failure(
            error=error_detail,
            message=str(e)
        )
        return jsonify(response.to_dict()), response.get_status_code()

    except Exception as e:
        error_detail = ErrorDetail(
            title="Unexpected Error",
            details=[f"An error occurred: {str(e)}"],
            status=500
        )
        response = ApiResponse.failure(error=error_detail)
        return jsonify(response.to_dict()), response.get_status_code()


# =============================================================================
# QUICK STATS API (AJAX) - For dashboard widgets/cards
# =============================================================================
@dashboard_bp.route('/quick-stats', methods=['GET'])
@auth.login_required
def get_quick_stats():
    """Get quick statistics for dashboard cards - AJAX endpoint"""
    try:
        # Get basic statistics without filters
        stats_request = GetStatisticsRequest()
        stats_response = statistics_utils.get_dashboard_statistics(stats_request)

        # Format for dashboard cards
        quick_stats = {
            'missing_persons': {
                'total': stats_response.total_missing_persons,
                'active': stats_response.active_missing_cases
            },
            'criminals': {
                'total': stats_response.total_criminals,
                'wanted': stats_response.wanted_criminals
            },
            'crimes': {
                'total': stats_response.total_crimes,
                'open': stats_response.open_crimes,
                'solved': stats_response.solved_crimes
            },
            'punishments': {
                'total': stats_response.total_punishments,
                'active': stats_response.active_punishments
            }
        }

        # Create success response
        response = ApiResponse.success(
            value=quick_stats,
            message="Quick statistics retrieved successfully"
        )

        return jsonify(response.to_dict()), response.get_status_code()

    except AppException as e:
        error_detail = ErrorDetail(
            title="Statistics Retrieval Failed",
            details=[str(e)],
            status=e.status_code
        )
        response = ApiResponse.failure(
            error=error_detail,
            message=str(e)
        )
        return jsonify(response.to_dict()), response.get_status_code()

    except Exception as e:
        error_detail = ErrorDetail(
            title="Unexpected Error",
            details=[f"An error occurred: {str(e)}"],
            status=500
        )
        response = ApiResponse.failure(error=error_detail)
        return jsonify(response.to_dict()), response.get_status_code()