# ===== src/modules/identification/presentation/controllers/identification_controller.py =====
from flask import Blueprint, render_template, request, jsonify, flash, current_app
from werkzeug.utils import secure_filename
import os
from datetime import datetime

from src.modules.authentication.domain.models.user import User
from src.modules.authentication.domain.repositories.user_repository import UserRepository
from src.modules.identification.domain.services.identification_history_service import IdentificationHistoryService
from src.modules.identification.domain.services.identification_notification_service import \
    IdentificationNotificationService
from src.modules.identification.domain.services.identification_search_service import IdentificationSearchService
from src.modules.identification.presentation.dtos.identification_dtos import CreateIdentificationSearchRequest, \
    ListIdentificationSearchesRequest, SendMissingPersonNotificationRequest
from src.shared.configs.security.session_decorators import SessionAuthDecorators
from src.shared.configs.security.session_manager import SessionManager
from src.shared.configs.exceptions.exceptions import AppException
from src.shared.response.api_response import ApiResponse
from src.shared.response.error_detail import ErrorDetail

# Create blueprint
identification_bp = Blueprint(
    'identification',
    __name__,
    template_folder='../templates',
    url_prefix='/identification'
)

# Initialize services
search_service = IdentificationSearchService()
history_service = IdentificationHistoryService()
notification_service = IdentificationNotificationService()
user_repository = UserRepository()
session_manager = SessionManager[User](user_repository)

# Initialize auth decorators
auth = SessionAuthDecorators(
    session_manager=session_manager,
    unauthorized_url='/',
    home_url='/dashboard'
)


def allowed_file(filename: str, allowed_extensions: set) -> bool:
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


def validate_file_size(file) -> bool:
    """Validate file size"""
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    return file_size <= current_app.config['MAX_FILE_SIZE']


# Context processor to inject current user
@identification_bp.app_context_processor
def inject_current_user():
    """Inject current user into all templates"""
    return {
        'current_user': session_manager.get_current_user()
    }


# =============================================================================
# MAIN SEARCH PAGE WITH HISTORY SIDEBAR
# =============================================================================

@identification_bp.route('/', methods=['GET'])
@auth.login_required
def search_page():
    """
    Main identification search page with left sidebar showing search history
    and main area for new search form
    """
    try:
        # Get recent searches for sidebar (last 10)
        recent_searches = history_service.get_recent_searches(days=30)

        # Limit to 10 most recent for sidebar
        sidebar_searches = recent_searches[:10]

        return render_template(
            'identification/search.jinja2',
            recent_searches=[search.to_dict() for search in sidebar_searches]
        )

    except AppException as e:
        flash(str(e), 'error')
        return render_template(
            'identification/search.jinja2',
            recent_searches=[]
        ), e.status_code


@identification_bp.route('/search', methods=['POST'])
@auth.login_required
def create_search():
    """
    Create a new identification search with uploaded image or video
    """
    try:
        # Validate file upload
        if 'file' not in request.files:
            error_detail = ErrorDetail(
                title="Validation Error",
                details=["No file provided"],
                status=400
            )
            response = ApiResponse.failure(error=error_detail)
            return jsonify(response.to_dict()), response.get_status_code()

        file = request.files['file']
        if file.filename == '':
            error_detail = ErrorDetail(
                title="Validation Error",
                details=["No file selected"],
                status=400
            )
            response = ApiResponse.failure(error=error_detail)
            return jsonify(response.to_dict()), response.get_status_code()

        # Get search parameters
        search_type = request.form.get('search_type', '').strip().lower()

        # Validate search type
        if search_type not in ['criminal', 'missing_person']:
            error_detail = ErrorDetail(
                title="Validation Error",
                details=["Invalid search type. Must be 'criminal' or 'missing_person'"],
                status=400
            )
            response = ApiResponse.failure(error=error_detail)
            return jsonify(response.to_dict()), response.get_status_code()

        # Determine file type
        filename = secure_filename(file.filename)
        file_extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

        image_extensions = current_app.config['ALLOWED_IMAGE_EXTENSIONS']
        video_extensions = {'mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv'}

        if file_extension in image_extensions:
            file_type = 'image'
        elif file_extension in video_extensions:
            file_type = 'video'
        else:
            error_detail = ErrorDetail(
                title="Validation Error",
                details=["Invalid file type. Allowed: images (jpg, png, gif) and videos (mp4, avi, mov)"],
                status=400
            )
            response = ApiResponse.failure(error=error_detail)
            return jsonify(response.to_dict()), response.get_status_code()

        # Validate file size
        if not validate_file_size(file):
            error_detail = ErrorDetail(
                title="Validation Error",
                details=["File size exceeds maximum limit"],
                status=400
            )
            response = ApiResponse.failure(error=error_detail)
            return jsonify(response.to_dict()), response.get_status_code()

        # Save file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        filename = f"search_{timestamp}_{filename}"

        # Save to evidence folder (reuse for identification searches)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER_EVIDENCE'], filename)
        file.save(filepath)

        # Create search request
        search_request = CreateIdentificationSearchRequest(
            search_type=search_type,
            file_path=filepath,
            file_type=file_type
        )

        # Create and process search
        search_response = search_service.create_and_process_search(search_request)

        flash('Search created and processing completed!', 'success')

        # Return success with redirect URL
        api_response = ApiResponse.success(
            value={
                'id': search_response.id,
                'redirect_url': f'/identification/searches/{search_response.id}'
            },
            message='Search created successfully!'
        )

        return jsonify(api_response.to_dict()), api_response.get_status_code()

    except AppException as e:
        # Clean up uploaded file if search creation failed
        if 'filepath' in locals() and filepath and os.path.exists(filepath):
            try:
                os.remove(filepath)
            except:
                pass

        error_detail = ErrorDetail(
            title="Search Creation Failed",
            details=[str(e)],
            status=e.status_code
        )
        response = ApiResponse.failure(error=error_detail, message=str(e))
        return jsonify(response.to_dict()), response.get_status_code()

    except Exception as e:
        # Clean up uploaded file if error occurred
        if 'filepath' in locals() and filepath and os.path.exists(filepath):
            try:
                os.remove(filepath)
            except:
                pass

        current_app.logger.error(f"Search creation error: {e}")
        error_detail = ErrorDetail(
            title="Unexpected Error",
            details=[f"An error occurred: {str(e)}"],
            status=500
        )
        response = ApiResponse.failure(error=error_detail)
        return jsonify(response.to_dict()), response.get_status_code()


# =============================================================================
# VIEW SEARCH RESULTS
# =============================================================================

@identification_bp.route('/searches/<string:search_id>', methods=['GET'])
@auth.login_required
def view_search_results(search_id):
    """
    View detailed results for a specific search with person details
    """
    try:
        # Get search details
        search_response = search_service.get_search_by_id(search_id)

        # Get search results
        results_response = search_service.get_search_results(search_id, matches_only=True)

        # Build view URLs for each result
        for result in results_response.grouped_results:
            person_id = result.get('person_id')
            person_type = result.get('person_type')

            # Generate view URL based on person type
            if person_type == 'criminal':
                result['view_url'] = f"/criminals/{person_id}"
            elif person_type == 'missing_person':
                result['view_url'] = f"/missing-persons/{person_id}"
            else:
                result['view_url'] = None

        return render_template(
            'identification/results.jinja2',
            search=search_response.to_dict(),
            results=results_response.to_dict(),
            search_id=search_id
        )

    except AppException as e:
        flash(str(e), 'error')
        return render_template(
            'identification/results.jinja2',
            search={},
            results={},
            search_id=search_id
        ), e.status_code


# =============================================================================
# SEARCH HISTORY LIST
# =============================================================================

@identification_bp.route('/history', methods=['GET'])
@auth.login_required
def list_search_history():
    """
    List all identification searches with pagination and filters
    """
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search_type = request.args.get('search_type', None, type=str)
        status = request.args.get('status', None, type=str)
        include_deleted = request.args.get('include_deleted', 'false', type=str).lower() == 'true'

        # Create list request
        list_request = ListIdentificationSearchesRequest(
            page=page,
            per_page=per_page,
            search_type=search_type,
            status=status,
            include_deleted=include_deleted
        )

        # Get searches
        response = history_service.list_searches(list_request)

        return render_template(
            'identification/history.jinja2',
            searches=response.searches,
            pagination={
                'total': response.total,
                'page': response.page,
                'per_page': response.per_page,
                'total_pages': response.total_pages
            },
            filters={
                'search_type': search_type,
                'status': status,
                'include_deleted': include_deleted
            }
        )

    except AppException as e:
        flash(str(e), 'error')
        return render_template(
            'identification/history.jinja2',
            searches=[],
            pagination={}
        ), e.status_code


# =============================================================================
# DELETE SEARCH
# =============================================================================

@identification_bp.route('/searches/<string:search_id>/delete', methods=['POST'])
@auth.login_required
@auth.role_required('admin')
def delete_search(search_id):
    """
    Soft delete a search and its results - AJAX endpoint
    """
    try:
        response = history_service.delete_search(search_id)

        flash(response.message, 'success')

        api_response = ApiResponse.success(
            value=response.to_dict(),
            message=response.message
        )

        return jsonify(api_response.to_dict()), api_response.get_status_code()

    except AppException as e:
        error_detail = ErrorDetail(
            title="Failed to Delete Search",
            details=[str(e)],
            status=e.status_code
        )
        response = ApiResponse.failure(error=error_detail, message=str(e))
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
# SEND NOTIFICATION FOR MISSING PERSON
# =============================================================================

@identification_bp.route('/notify', methods=['POST'])
@auth.login_required
def send_notification():
    """
    Send notification to reporter when missing person is found - AJAX endpoint
    """
    try:
        # Get request data
        data = request.get_json()

        if not data:
            error_detail = ErrorDetail(
                title="Validation Error",
                details=["No data provided"],
                status=400
            )
            response = ApiResponse.failure(error=error_detail)
            return jsonify(response.to_dict()), response.get_status_code()

        search_id = data.get('search_id')
        person_id = data.get('person_id')

        if not search_id or not person_id:
            error_detail = ErrorDetail(
                title="Validation Error",
                details=["Search ID and Person ID are required"],
                status=400
            )
            response = ApiResponse.failure(error=error_detail)
            return jsonify(response.to_dict()), response.get_status_code()

        # Create notification request
        notification_request = SendMissingPersonNotificationRequest(
            search_id=search_id,
            person_id=person_id
        )

        # Send notification
        notification_response = notification_service.send_missing_person_found_notification(
            notification_request
        )

        flash(notification_response.message, 'success')

        api_response = ApiResponse.success(
            value=notification_response.to_dict(),
            message=notification_response.message
        )

        return jsonify(api_response.to_dict()), api_response.get_status_code()

    except AppException as e:
        error_detail = ErrorDetail(
            title="Notification Failed",
            details=[str(e)],
            status=e.status_code
        )
        response = ApiResponse.failure(error=error_detail, message=str(e))
        return jsonify(response.to_dict()), response.get_status_code()

    except Exception as e:
        current_app.logger.error(f"Notification error: {e}")
        error_detail = ErrorDetail(
            title="Unexpected Error",
            details=[f"An error occurred: {str(e)}"],
            status=500
        )
        response = ApiResponse.failure(error=error_detail)
        return jsonify(response.to_dict()), response.get_status_code()


# =============================================================================
# STATISTICS
# =============================================================================

@identification_bp.route('/statistics', methods=['GET'])
@auth.login_required
def get_statistics():
    """
    Get identification search statistics - AJAX endpoint
    """
    try:
        stats = history_service.get_search_statistics()

        api_response = ApiResponse.success(
            value=stats,
            message="Statistics retrieved successfully"
        )

        return jsonify(api_response.to_dict()), api_response.get_status_code()

    except AppException as e:
        error_detail = ErrorDetail(
            title="Failed to Retrieve Statistics",
            details=[str(e)],
            status=e.status_code
        )
        response = ApiResponse.failure(error=error_detail, message=str(e))
        return jsonify(response.to_dict()), response.get_status_code()

    except Exception as e:
        error_detail = ErrorDetail(
            title="Unexpected Error",
            details=[f"An error occurred: {str(e)}"],
            status=500
        )
        response = ApiResponse.failure(error=error_detail)
        return jsonify(response.to_dict()), response.get_status_code()