from datetime import datetime

from flask import Blueprint, render_template, request, jsonify, flash, current_app
from werkzeug.utils import secure_filename
import os
from typing import List

from src.modules.records.domain.services.missing_person_service import MissingPersonService
from src.modules.records.internal.location_utils import LocationUtils
from src.modules.records.presentation.dtos.record_management import (
    CreateMissingPersonRequest, UpdateMissingPersonRequest,
    UpdateMissingPersonStatusRequest, ListMissingPersonsRequest,
    SearchPersonRequest, CreateLocationRequest, CreatePersonImageRequest
)

from src.modules.authentication.domain.models.user import User
from src.modules.authentication.domain.repositories.user_repository import UserRepository
from src.shared.configs.security.session_decorators import SessionAuthDecorators
from src.shared.configs.security.session_manager import SessionManager
from src.shared.configs.exceptions.exceptions import AppException
from src.shared.response.api_response import ApiResponse
from src.shared.response.error_detail import ErrorDetail

# Create blueprint
missing_person_bp = Blueprint(
    'missing_person',
    __name__,
    template_folder='../templates',
    url_prefix='/missing-persons'
)

# Initialize services
missing_person_service = MissingPersonService()
location_utils = LocationUtils()
user_repository = UserRepository()
session_manager = SessionManager[User](user_repository)

# Initialize auth decorators
auth = SessionAuthDecorators(
    session_manager=session_manager,
    unauthorized_url='/',
    home_url='/dashboard'
)


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_IMAGE_EXTENSIONS']


def validate_file_size(file) -> bool:
    """Validate file size"""
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    return file_size <= current_app.config['MAX_FILE_SIZE']


# Context processor to inject current user
@missing_person_bp.app_context_processor
def inject_current_user():
    """Inject current user into all templates"""
    return {
        'current_user': session_manager.get_current_user()
    }


# =============================================================================
# LIST MISSING PERSONS ROUTE (Main Page)
# =============================================================================
@missing_person_bp.route('/', methods=['GET'])
@auth.login_required
def list_missing_persons():
    """List all missing persons with pagination and filtering"""
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status', None, type=str)
        assigned_officer_id = request.args.get('assigned_officer_id', None, type=str)
        include_deleted = request.args.get('include_deleted', 'false', type=str).lower() == 'true'

        # Create list request
        list_request = ListMissingPersonsRequest(
            page=page,
            per_page=per_page,
            status=status,
            assigned_officer_id=assigned_officer_id,
            include_deleted=include_deleted
        )

        # Get missing persons
        response = missing_person_service.list_missing_persons(list_request)

        return render_template(
            'missing_person/list.jinja2',
            missing_persons=response.missing_persons,
            pagination={
                'total': response.total,
                'page': response.page,
                'per_page': response.per_page,
                'total_pages': response.total_pages
            },
            filters={
                'status': status,
                'assigned_officer_id': assigned_officer_id,
                'include_deleted': include_deleted
            }
        )

    except AppException as e:
        return render_template(
            'missing_person/list.jinja2',
            missing_persons=[],
            pagination={}
        ), e.status_code


# =============================================================================
# VIEW MISSING PERSON ROUTE (Details Page)
# =============================================================================
@missing_person_bp.route('/<string:missing_person_id>', methods=['GET'])
@auth.login_required
def view_missing_person(missing_person_id):
    """View a single missing person's details"""
    try:
        # Get missing person
        response = missing_person_service.get_missing_person_by_id(missing_person_id)

        # Get images for missing person
        images = missing_person_service.image_utils.get_person_images(missing_person_id)

        return render_template(
            'missing_person/view.jinja2',
            missing_person=response.to_dict(),
            images=[img.to_dict() for img in images]
        )

    except AppException as e:
        flash(str(e), 'error')
        return render_template(
            'missing_person/view.jinja2',
            missing_person={},
            images=[]
        ), e.status_code


# =============================================================================
# CREATE/EDIT MISSING PERSON FORM ROUTE
# =============================================================================
@missing_person_bp.route('/form', methods=['GET'])
@missing_person_bp.route('/form/<string:missing_person_id>', methods=['GET'])
@auth.login_required
def missing_person_form(missing_person_id=None):
    """Show form for creating or editing missing person (same template for both)"""
    try:
        missing_person_data = None
        images = []

        # If missing_person_id provided, fetch existing data for editing
        if missing_person_id:
            response = missing_person_service.get_missing_person_by_id(missing_person_id)
            missing_person_data = response.to_dict()

            # Get images for editing
            images = missing_person_service.image_utils.get_person_images(missing_person_id)

        return render_template(
            'missing_person/form.jinja2',
            missing_person=missing_person_data,
            images=[img.to_dict() for img in images] if images else [],
            is_edit=missing_person_id is not None
        )

    except AppException as e:
        flash(str(e), 'error')
        return render_template(
            'missing_person/form.jinja2',
            missing_person=None,
            images=[],
            is_edit=False
        ), e.status_code


# =============================================================================
# CREATE MISSING PERSON ROUTE
# =============================================================================
@missing_person_bp.route('/create', methods=['POST'])
@auth.login_required
def create_missing_person():
    """Report a new missing person"""
    try:
        current_user_id = session_manager.get_current_user_id()

        # ✅ STEP 1: Create location for last seen
        latitude = request.form.get('last_seen_latitude', type=float)
        longitude = request.form.get('last_seen_longitude', type=float)

        if not latitude or not longitude:
            error_detail = ErrorDetail(
                title="Validation Error",
                details=["Last seen location coordinates are required"],
                status=400
            )
            response = ApiResponse.failure(error=error_detail)
            return jsonify(response.to_dict()), response.get_status_code()

        location_request = CreateLocationRequest(
            latitude=latitude,
            longitude=longitude,
            address=request.form.get('last_seen_address', '').strip() or None,
            city=request.form.get('last_seen_city', '').strip() or None,
            state=request.form.get('last_seen_state', '').strip() or None,
            country=request.form.get('last_seen_country', '').strip() or None,
            postal_code=request.form.get('last_seen_postal_code', '').strip() or None,
            description=request.form.get('last_seen_location_description', '').strip() or None,
            created_by=current_user_id
        )

        location_response = location_utils.create_location(location_request)

        # ✅ STEP 2: Create reporter location if provided
        reporter_address_id = None
        reporter_latitude = request.form.get('reporter_latitude', type=float)
        reporter_longitude = request.form.get('reporter_longitude', type=float)

        if reporter_latitude and reporter_longitude:
            try:
                reporter_location_request = CreateLocationRequest(
                    latitude=reporter_latitude,
                    longitude=reporter_longitude,
                    address=request.form.get('reporter_address', '').strip() or None,
                    city=request.form.get('reporter_city', '').strip() or None,
                    state=request.form.get('reporter_state', '').strip() or None,
                    country=request.form.get('reporter_country', '').strip() or None,
                    postal_code=request.form.get('reporter_postal_code', '').strip() or None,
                    created_by=current_user_id
                )
                reporter_location_response = location_utils.create_location(reporter_location_request)
                reporter_address_id = reporter_location_response.id
            except Exception as loc_error:
                current_app.logger.warning(f"Reporter location creation failed: {loc_error}")

        # ✅ STEP 3: Create missing person request with ALL fields
        create_request = CreateMissingPersonRequest(
            # Required fields
            first_name=request.form.get('first_name', '').strip(),
            last_name=request.form.get('last_name', '').strip(),
            last_seen_date=request.form.get('last_seen_date', '').strip(),
            last_seen_location_id=location_response.id,
            reporter_first_name=request.form.get('reporter_first_name', '').strip(),
            reporter_last_name=request.form.get('reporter_last_name', '').strip(),
            reporter_relationship=request.form.get('reporter_relationship', '').strip(),
            reporter_phone=request.form.get('reporter_phone', '').strip(),

            # Optional person fields - ✅ INCLUDE ALL
            date_of_birth=request.form.get('date_of_birth', '').strip() or None,
            gender=request.form.get('gender', '').strip() or None,
            phone_number=request.form.get('phone_number', '').strip() or None,
            email=request.form.get('email', '').strip() or None,
            national_id=request.form.get('national_id', '').strip() or None,  # ✅ INCLUDE
            height=request.form.get('height', type=float),
            weight=request.form.get('weight', type=float),
            hair_color=request.form.get('hair_color', '').strip() or None,
            eye_color=request.form.get('eye_color', '').strip() or None,
            skin_tone=request.form.get('skin_tone', '').strip() or None,  # ✅ INCLUDE
            distinctive_features=request.form.get('distinctive_features', '').strip() or None,
            description=request.form.get('description', '').strip() or None,
            circumstances=request.form.get('circumstances', '').strip() or None,
            assigned_officer_id=request.form.get('assigned_officer_id', '').strip() or None,

            # Reporter optional fields
            reporter_email=request.form.get('reporter_email', '').strip() or None,
            reporter_address_id=reporter_address_id,  # ✅ USE CREATED LOCATION

            # Metadata
            created_by=current_user_id
        )

        # Create missing person
        response = missing_person_service.report_missing_person(create_request)

        # ✅ STEP 4: Handle image uploads
        uploaded_files = request.files.getlist('images')
        if uploaded_files and uploaded_files[0].filename:
            image_paths = []

            for idx, file in enumerate(uploaded_files):
                if file and allowed_file(file.filename):
                    if not validate_file_size(file):
                        flash(f'File {file.filename} exceeds maximum file size limit', 'warning')
                        continue

                    # Save file
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                    filename = f"{response.id}_{timestamp}_{idx}_{filename}"
                    filepath = os.path.join(current_app.config['UPLOAD_FOLDER_MISSING_PERSONS'], filename)
                    file.save(filepath)
                    image_paths.append(filepath)

            # Upload images with face vectors
            if image_paths:
                try:
                    missing_person_service.image_utils.upload_multiple_images(
                        person_id=response.id,
                        image_paths=image_paths,
                        uploaded_by=current_user_id
                    )
                except Exception as img_error:
                    flash(f'Missing person created but some images failed: {str(img_error)}', 'warning')

        flash(f'Missing person {response.first_name} {response.last_name} reported successfully!', 'success')

        # Create success response
        api_response = ApiResponse.success(
            value={
                'id': response.id,
                'redirect_url': f'/missing-persons/{response.id}'
            },
            message=f'Missing person {response.first_name} {response.last_name} reported successfully!'
        )

        return jsonify(api_response.to_dict()), api_response.get_status_code()

    except AppException as e:
        error_detail = ErrorDetail(
            title="Failed to Report Missing Person",
            details=[str(e)],
            status=e.status_code
        )
        response = ApiResponse.failure(error=error_detail, message=str(e))
        return jsonify(response.to_dict()), response.get_status_code()

    except Exception as e:
        current_app.logger.error(f"Create missing person error: {e}")
        error_detail = ErrorDetail(
            title="Unexpected Error",
            details=[f"An error occurred: {str(e)}"],
            status=500
        )
        response = ApiResponse.failure(error=error_detail)
        return jsonify(response.to_dict()), response.get_status_code()

# =============================================================================
# UPDATE MISSING PERSON ROUTE
# =============================================================================
@missing_person_bp.route('/<string:missing_person_id>/update', methods=['POST'])
@auth.login_required
def update_missing_person(missing_person_id):
    """Update missing person details"""
    try:
        current_user_id = session_manager.get_current_user_id()

        # Handle found location if provided
        found_location_id = None
        found_latitude = request.form.get('found_latitude', type=float)
        found_longitude = request.form.get('found_longitude', type=float)

        if found_latitude and found_longitude:
            found_location_request = CreateLocationRequest(
                latitude=found_latitude,
                longitude=found_longitude,
                address=request.form.get('found_address', '').strip() or None,
                city=request.form.get('found_city', '').strip() or None,
                state=request.form.get('found_state', '').strip() or None,
                country=request.form.get('found_country', '').strip() or None,
                postal_code=request.form.get('found_postal_code', '').strip() or None,
                description=request.form.get('found_location_description', '').strip() or None,
                created_by=current_user_id
            )
            found_location_response = location_utils.create_location(found_location_request)
            found_location_id = found_location_response.id

        # Create update request
        update_request = UpdateMissingPersonRequest(
            missing_person_id=missing_person_id,
            status=request.form.get('status', '').strip() or None,
            circumstances=request.form.get('circumstances', '').strip() or None,
            found_date=request.form.get('found_date', '').strip() or None,
            found_location_id=found_location_id,
            found_condition=request.form.get('found_condition', '').strip() or None,
            assigned_officer_id=request.form.get('assigned_officer_id', '').strip() or None,
            updated_by=current_user_id
        )

        # Update missing person
        response = missing_person_service.update_missing_person(update_request)

        # Handle additional image uploads
        uploaded_files = request.files.getlist('images')
        if uploaded_files and uploaded_files[0].filename:
            image_paths = []

            for file in uploaded_files:
                if file and allowed_file(file.filename):
                    if not validate_file_size(file):
                        flash(f'File {file.filename} exceeds maximum file size limit', 'warning')
                        continue

                    # Save file
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"{missing_person_id}_{timestamp}_{filename}"
                    filepath = os.path.join(current_app.config['UPLOAD_FOLDER_MISSING_PERSONS'], filename)
                    file.save(filepath)
                    image_paths.append(filepath)

            # Upload images with face vectors
            if image_paths:
                try:
                    missing_person_service.image_utils.upload_multiple_images(
                        person_id=missing_person_id,
                        image_paths=image_paths,
                        uploaded_by=current_user_id
                    )
                except Exception as img_error:
                    flash(f'Updated but some images failed: {str(img_error)}', 'warning')

        flash(f'Missing person {response.first_name} {response.last_name} updated successfully!', 'success')

        # Create success response
        api_response = ApiResponse.success(
            value=response,
            message=f'Missing person {response.first_name} {response.last_name} updated successfully!'
        )

        return jsonify(api_response.to_dict()), api_response.get_status_code()

    except AppException as e:
        error_detail = ErrorDetail(
            title="Failed to Update Missing Person",
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
# UPDATE STATUS ROUTE (AJAX)
# =============================================================================
@missing_person_bp.route('/<string:missing_person_id>/update-status', methods=['POST'])
@auth.login_required
def update_status(missing_person_id):
    """Update missing person status - AJAX endpoint"""
    try:
        current_user_id = session_manager.get_current_user_id()

        # Get status data from request
        new_status = request.form.get('status', '').strip()
        notes = request.form.get('notes', '').strip() or None

        # Create status update request
        status_request = UpdateMissingPersonStatusRequest(
            missing_person_id=missing_person_id,
            new_status=new_status,
            changed_by=current_user_id,
            notes=notes
        )

        # Update status
        response = missing_person_service.update_missing_person_status(status_request)

        flash(f'Status updated to {new_status} successfully!', 'success')

        # Create success response
        api_response = ApiResponse.success(
            value=response,
            message=f'Status updated to {new_status} successfully!'
        )

        return jsonify(api_response.to_dict()), api_response.get_status_code()

    except AppException as e:
        error_detail = ErrorDetail(
            title="Failed to Update Status",
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
# DELETE MISSING PERSON ROUTE (AJAX)
# =============================================================================
@missing_person_bp.route('/<string:missing_person_id>/delete', methods=['POST'])
@auth.login_required
@auth.role_required('admin')
def delete_missing_person(missing_person_id):
    """Soft delete a missing person record - AJAX endpoint"""
    try:
        # Delete missing person
        response = missing_person_service.delete_missing_person(missing_person_id)

        flash(response.message, 'success')

        # Create success response
        api_response = ApiResponse.success(
            value=response,
            message=response.message
        )

        return jsonify(api_response.to_dict()), api_response.get_status_code()

    except AppException as e:
        error_detail = ErrorDetail(
            title="Failed to Delete Missing Person",
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
# SEARCH MISSING PERSONS ROUTE (AJAX)
# =============================================================================
@missing_person_bp.route('/search', methods=['GET'])
@auth.login_required
def search_missing_persons():
    """Search missing persons - AJAX endpoint"""
    try:
        # Get search parameters
        query = request.args.get('query', '').strip()
        search_type = request.args.get('search_type', 'name')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        # Create search request
        search_request = SearchPersonRequest(
            query=query,
            search_type=search_type,
            page=page,
            per_page=per_page
        )

        # Search missing persons
        response = missing_person_service.search_missing_persons(search_request)

        # Create success response
        api_response = ApiResponse.success(
            value=response,
            message=response.message
        )

        return jsonify(api_response.to_dict()), api_response.get_status_code()

    except AppException as e:
        error_detail = ErrorDetail(
            title="Search Failed",
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
# GET ACTIVE CASES ROUTE (AJAX)
# =============================================================================
@missing_person_bp.route('/active', methods=['GET'])
@auth.login_required
def get_active_cases():
    """Get all active missing person cases - AJAX endpoint"""
    try:
        # Get active cases
        cases = missing_person_service.get_active_cases()

        # Create success response
        api_response = ApiResponse.success(
            value=[case.to_dict() for case in cases],
            message=f"Found {len(cases)} active case(s)"
        )

        return jsonify(api_response.to_dict()), api_response.get_status_code()

    except AppException as e:
        error_detail = ErrorDetail(
            title="Failed to Retrieve Active Cases",
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
# UPLOAD IMAGE ROUTE (AJAX)
# =============================================================================
@missing_person_bp.route('/<string:missing_person_id>/upload-image', methods=['POST'])
@auth.login_required
def upload_image(missing_person_id):
    """Upload an image for a missing person - AJAX endpoint"""
    try:
        current_user_id = session_manager.get_current_user_id()

        # Check if image file is provided
        if 'image' not in request.files:
            error_detail = ErrorDetail(
                title="Validation Error",
                details=["No image file provided"],
                status=400
            )
            response = ApiResponse.failure(error=error_detail)
            return jsonify(response.to_dict()), response.get_status_code()

        file = request.files['image']

        if file.filename == '':
            error_detail = ErrorDetail(
                title="Validation Error",
                details=["No image file selected"],
                status=400
            )
            response = ApiResponse.failure(error=error_detail)
            return jsonify(response.to_dict()), response.get_status_code()

        if not allowed_file(file.filename):
            error_detail = ErrorDetail(
                title="Validation Error",
                details=["Invalid file type. Allowed types: png, jpg, jpeg, gif"],
                status=400
            )
            response = ApiResponse.failure(error=error_detail)
            return jsonify(response.to_dict()), response.get_status_code()

        if not validate_file_size(file):
            error_detail = ErrorDetail(
                title="Validation Error",
                details=["File size exceeds maximum file size limit"],
                status=400
            )
            response = ApiResponse.failure(error=error_detail)
            return jsonify(response.to_dict()), response.get_status_code()

        # Save file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{missing_person_id}_{timestamp}_{filename}"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER_MISSING_PERSONS'], filename)
        file.save(filepath)

        # Get primary flag
        is_primary = request.form.get('is_primary', 'false').lower() == 'true'

        # Create image request
        image_request = CreatePersonImageRequest(
            person_id=missing_person_id,
            image_path=filepath,
            is_primary=is_primary,
            uploaded_by=current_user_id
        )

        # Upload image with face vector
        image_response = missing_person_service.upload_missing_person_image(
            missing_person_id=missing_person_id,
            request=image_request
        )

        flash('Image uploaded successfully!', 'success')

        # Create success response
        api_response = ApiResponse.success(
            value=image_response,
            message='Image uploaded successfully!'
        )

        return jsonify(api_response.to_dict()), api_response.get_status_code()

    except AppException as e:
        # Clean up file if upload failed
        if 'filepath' in locals() and os.path.exists(filepath):
            os.remove(filepath)

        error_detail = ErrorDetail(
            title="Image Upload Failed",
            details=[str(e)],
            status=e.status_code
        )
        response = ApiResponse.failure(error=error_detail, message=str(e))
        return jsonify(response.to_dict()), response.get_status_code()

    except Exception as e:
        # Clean up file if upload failed
        if 'filepath' in locals() and os.path.exists(filepath):
            os.remove(filepath)

        error_detail = ErrorDetail(
            title="Unexpected Error",
            details=[f"An error occurred: {str(e)}"],
            status=500
        )
        response = ApiResponse.failure(error=error_detail)
        return jsonify(response.to_dict()), response.get_status_code()


# =============================================================================
# DELETE IMAGE ROUTE (AJAX)
# =============================================================================
@missing_person_bp.route('/images/<string:image_id>/delete', methods=['POST'])
@auth.login_required
def delete_image(image_id):
    """Delete a person image - AJAX endpoint"""
    try:
        # Delete image
        success = missing_person_service.image_utils.delete_person_image(image_id)

        flash('Image deleted successfully!', 'success')

        # Create success response
        api_response = ApiResponse.success(
            value={'deleted': success},
            message='Image deleted successfully!'
        )

        return jsonify(api_response.to_dict()), api_response.get_status_code()

    except AppException as e:
        error_detail = ErrorDetail(
            title="Image Deletion Failed",
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
# SET PRIMARY IMAGE ROUTE (AJAX)
# =============================================================================
@missing_person_bp.route('/<string:missing_person_id>/images/<string:image_id>/set-primary', methods=['POST'])
@auth.login_required
def set_primary_image(missing_person_id, image_id):
    """Set an image as primary - AJAX endpoint"""
    try:
        # Set primary image
        image_response = missing_person_service.image_utils.set_primary_image(
            image_id=image_id,
            person_id=missing_person_id
        )

        flash('Primary image updated successfully!', 'success')

        # Create success response
        api_response = ApiResponse.success(
            value=image_response,
            message='Primary image updated successfully!'
        )

        return jsonify(api_response.to_dict()), api_response.get_status_code()

    except AppException as e:
        error_detail = ErrorDetail(
            title="Failed to Set Primary Image",
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
        response = ApiResponse