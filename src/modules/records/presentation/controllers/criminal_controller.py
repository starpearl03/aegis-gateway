from flask import Blueprint, render_template, request, jsonify, flash, current_app
from werkzeug.utils import secure_filename
import os
from datetime import datetime

from src.modules.records.domain.services.criminal_record_service import CriminalRecordService
from src.modules.records.internal.location_utils import LocationUtils
from src.modules.records.presentation.dtos.record_management import (
    CreateCriminalRequest, UpdateCriminalRequest, ListCriminalsRequest,
    CreateCrimeRequest, UpdateCrimeRequest, ListCrimesRequest,
    AddCrimeVictimRequest, CreatePunishmentRequest, UpdatePunishmentRequest,
    ListPunishmentsRequest, CreateEvidenceRequest, UpdateEvidenceRequest,
    ListEvidenceRequest, CreateLocationRequest, CreatePersonImageRequest,
    SearchPersonRequest
)

from src.modules.authentication.domain.models.user import User
from src.modules.authentication.domain.repositories.user_repository import UserRepository
from src.shared.configs.security.session_decorators import SessionAuthDecorators
from src.shared.configs.security.session_manager import SessionManager
from src.shared.configs.exceptions.exceptions import AppException
from src.shared.response.api_response import ApiResponse
from src.shared.response.error_detail import ErrorDetail

# Create blueprint
criminal_bp = Blueprint(
    'criminal',
    __name__,
    template_folder='../templates',
    url_prefix='/criminals'
)

# Initialize services
criminal_service = CriminalRecordService()
location_utils = LocationUtils()
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
@criminal_bp.app_context_processor
def inject_current_user():
    """Inject current user into all templates"""
    return {
        'current_user': session_manager.get_current_user()
    }


# =============================================================================
# CRIMINAL MANAGEMENT ROUTES
# =============================================================================

@criminal_bp.route('/', methods=['GET'])
@auth.login_required
def list_criminals():
    """List all criminals with pagination and filtering"""
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        is_wanted = request.args.get('is_wanted', None, type=str)
        min_priority = request.args.get('min_priority', None, type=int)
        gang_affiliation = request.args.get('gang_affiliation', None, type=str)
        threat_level = request.args.get('threat_level', None, type=str)
        include_deleted = request.args.get('include_deleted', 'false', type=str).lower() == 'true'

        # Convert is_wanted string to boolean if provided
        is_wanted_bool = None
        if is_wanted is not None and is_wanted.lower() in ['true', 'false']:
            is_wanted_bool = is_wanted.lower() == 'true'

        # Create list request
        list_request = ListCriminalsRequest(
            page=page,
            per_page=per_page,
            is_wanted=is_wanted_bool,
            min_priority=min_priority,
            gang_affiliation=gang_affiliation,
            threat_level=threat_level,
            include_deleted=include_deleted
        )

        # Get criminals
        response = criminal_service.list_criminals(list_request)

        return render_template(
            'criminal/list.jinja2',
            criminals=response.criminals,
            pagination={
                'total': response.total,
                'page': response.page,
                'per_page': response.per_page,
                'total_pages': response.total_pages
            },
            filters={
                'is_wanted': is_wanted,
                'min_priority': min_priority,
                'gang_affiliation': gang_affiliation,
                'threat_level': threat_level,
                'include_deleted': include_deleted
            }
        )

    except AppException as e:
        return render_template(
            'criminal/list.jinja2',
            criminals=[],
            pagination={}
        ), e.status_code


@criminal_bp.route('/<string:criminal_id>', methods=['GET'])
@auth.login_required
def view_criminal(criminal_id):
    """View a single criminal's comprehensive profile with all related data"""
    try:
        # Get criminal basic info
        criminal_response = criminal_service.get_criminal_by_id(criminal_id)

        # Get images
        images = criminal_service.image_utils.get_person_images(criminal_id)

        # Get crimes associated with this criminal
        crimes_request = ListCrimesRequest(criminal_id=criminal_id, page=1, per_page=100)
        crimes_response = criminal_service.list_crimes(crimes_request)

        # Enrich each crime with full details (victims, punishments, evidence)
        enriched_crimes = []
        for crime in crimes_response.crimes:
            crime_id = crime['id']

            # Get victims for this crime
            try:
                victims = criminal_service.get_crime_victims(crime_id)
                crime['victims'] = [victim.to_dict() for victim in victims]
            except:
                crime['victims'] = []

            # Get punishments for this crime
            try:
                punishments_request = ListPunishmentsRequest(crime_id=crime_id, page=1, per_page=100)
                punishments_response = criminal_service.list_punishments(punishments_request)
                crime['punishments'] = punishments_response.punishments
            except:
                crime['punishments'] = []

            # Get evidence for this crime
            try:
                evidence_request = ListEvidenceRequest(crime_id=crime_id, page=1, per_page=100)
                evidence_response = criminal_service.list_evidence(evidence_request)
                crime['evidence'] = evidence_response.evidence
            except:
                crime['evidence'] = []

            enriched_crimes.append(crime)

        return render_template(
            'criminal/view.jinja2',
            criminal=criminal_response.to_dict(),
            images=[img.to_dict() for img in images],
            crimes=enriched_crimes
        )

    except AppException as e:
        flash(str(e), 'error')
        return render_template(
            'criminal/view.jinja2',
            criminal={},
            images=[],
            crimes=[]
        ), e.status_code


@criminal_bp.route('/form', methods=['GET', 'POST'])
@criminal_bp.route('/form/<string:criminal_id>', methods=['GET', 'POST'])
@auth.login_required
def criminal_form(criminal_id=None):
    """Unified form for creating or editing criminal (same template for both)"""

    # GET - Show form
    if request.method == 'GET':
        try:
            criminal_data = None
            images = []

            # If criminal_id provided, fetch existing data for editing
            if criminal_id:
                response = criminal_service.get_criminal_by_id(criminal_id)
                criminal_data = response.to_dict()

                # Get images for editing
                images = criminal_service.image_utils.get_person_images(criminal_id)

            return render_template(
                'criminal/form.jinja2',
                criminal=criminal_data,
                images=[img.to_dict() for img in images] if images else [],
                is_edit=criminal_id is not None
            )

        except AppException as e:
            flash(str(e), 'error')
            return render_template(
                'criminal/form.jinja2',
                criminal=None,
                images=[],
                is_edit=False
            ), e.status_code

    # POST - Create or Update
    try:
        current_user_id = session_manager.get_current_user_id()

        # ✅ STEP 1: Create address location if provided
        address_id = None
        latitude = request.form.get('latitude', type=float)
        longitude = request.form.get('longitude', type=float)

        if latitude and longitude:
            try:
                location_request = CreateLocationRequest(
                    latitude=latitude,
                    longitude=longitude,
                    address=request.form.get('address', '').strip() or None,
                    city=request.form.get('city', '').strip() or None,
                    state=request.form.get('state', '').strip() or None,
                    country=request.form.get('country', '').strip() or None,
                    postal_code=request.form.get('postal_code', '').strip() or None,
                    description=request.form.get('location_description', '').strip() or None,
                    created_by=current_user_id
                )
                location_response = location_utils.create_location(location_request)
                address_id = location_response.id
            except Exception as loc_error:
                # Log but continue without address if location creation fails
                current_app.logger.warning(f"Location creation failed: {loc_error}")

        # ✅ STEP 2: Determine if this is create or update
        if criminal_id:
            # UPDATE - Only criminal-specific fields can be updated
            update_request = UpdateCriminalRequest(
                criminal_id=criminal_id,
                alias=request.form.get('alias', '').strip() or None,
                is_wanted=request.form.get('is_wanted', 'off') == 'on',
                priority_level=request.form.get('priority_level', type=int),
                gang_affiliation=request.form.get('gang_affiliation', '').strip() or None,
                threat_level=request.form.get('threat_level', '').strip() or None,
                updated_by=current_user_id
            )

            response = criminal_service.update_criminal(update_request)
            message = f'Criminal {response.first_name} {response.last_name} updated successfully!'
        else:
            # ✅ CREATE - Include ALL fields
            create_request = CreateCriminalRequest(
                # Required fields
                first_name=request.form.get('first_name', '').strip(),
                last_name=request.form.get('last_name', '').strip(),

                # Personal info
                date_of_birth=request.form.get('date_of_birth', '').strip() or None,
                gender=request.form.get('gender', '').strip() or None,
                phone_number=request.form.get('phone_number', '').strip() or None,  # ✅ INCLUDE
                email=request.form.get('email', '').strip() or None,  # ✅ INCLUDE
                national_id=request.form.get('national_id', '').strip() or None,  # ✅ INCLUDE

                # Physical description
                height=request.form.get('height', type=float),
                weight=request.form.get('weight', type=float),
                hair_color=request.form.get('hair_color', '').strip() or None,
                eye_color=request.form.get('eye_color', '').strip() or None,
                skin_tone=request.form.get('skin_tone', '').strip() or None,  # ✅ INCLUDE
                distinctive_features=request.form.get('distinctive_features', '').strip() or None,
                description=request.form.get('description', '').strip() or None,

                # Address - USE THE CREATED LOCATION ID
                address_id=address_id,  # ✅ INCLUDE THE CREATED LOCATION

                # Criminal specific
                alias=request.form.get('alias', '').strip() or None,
                is_wanted=request.form.get('is_wanted', 'off') == 'on',
                priority_level=request.form.get('priority_level', 0, type=int),
                gang_affiliation=request.form.get('gang_affiliation', '').strip() or None,
                threat_level=request.form.get('threat_level', '').strip() or None,

                # Metadata
                created_by=current_user_id
            )

            response = criminal_service.create_criminal(create_request)
            criminal_id = response.id
            message = f'Criminal {response.first_name} {response.last_name} created successfully!'

        # ✅ STEP 3: Handle image uploads
        uploaded_files = request.files.getlist('images')
        if uploaded_files and uploaded_files[0].filename:
            image_paths = []

            for idx, file in enumerate(uploaded_files):
                if file and allowed_file(file.filename, current_app.config['ALLOWED_IMAGE_EXTENSIONS']):
                    if not validate_file_size(file):
                        flash(f'File {file.filename} exceeds maximum file size limit', 'warning')
                        continue

                    # Save file with microseconds and index for uniqueness
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                    filename = f"{criminal_id}_{timestamp}_{idx}_{filename}"
                    filepath = os.path.join(current_app.config['UPLOAD_FOLDER_CRIMINALS'], filename)
                    file.save(filepath)
                    image_paths.append(filepath)

            # Upload images with face vectors
            if image_paths:
                try:
                    criminal_service.image_utils.upload_multiple_images(
                        person_id=criminal_id,
                        image_paths=image_paths,
                        uploaded_by=current_user_id
                    )
                except Exception as img_error:
                    flash(f'Some images failed: {str(img_error)}', 'warning')

        flash(message, 'success')

        # Create success response
        api_response = ApiResponse.success(
            value={
                'id': response.id,
                'redirect_url': f'/criminals/{response.id}'
            },
            message=message
        )

        return jsonify(api_response.to_dict()), api_response.get_status_code()

    except AppException as e:
        error_detail = ErrorDetail(
            title="Failed to Save Criminal",
            details=[str(e)],
            status=e.status_code
        )
        response = ApiResponse.failure(error=error_detail, message=str(e))
        return jsonify(response.to_dict()), response.get_status_code()

    except Exception as e:
        current_app.logger.error(f"Criminal form error: {e}")
        error_detail = ErrorDetail(
            title="Unexpected Error",
            details=[f"An error occurred: {str(e)}"],
            status=500
        )
        response = ApiResponse.failure(error=error_detail)
        return jsonify(response.to_dict()), response.get_status_code()

# @criminal_bp.route('/form', methods=['GET', 'POST'])
# @criminal_bp.route('/form/<string:criminal_id>', methods=['GET', 'POST'])
# @auth.login_required
# def criminal_form(criminal_id=None):
#     """Unified form for creating or editing criminal (same template for both)"""
#
#     # GET - Show form
#     if request.method == 'GET':
#         try:
#             criminal_data = None
#             images = []
#
#             # If criminal_id provided, fetch existing data for editing
#             if criminal_id:
#                 response = criminal_service.get_criminal_by_id(criminal_id)
#                 criminal_data = response.to_dict()
#
#                 # Get images for editing
#                 images = criminal_service.image_utils.get_person_images(criminal_id)
#
#             return render_template(
#                 'criminal/form.jinja2',
#                 criminal=criminal_data,
#                 images=[img.to_dict() for img in images] if images else [],
#                 is_edit=criminal_id is not None
#             )
#
#         except AppException as e:
#             flash(str(e), 'error')
#             return render_template(
#                 'criminal/form.jinja2',
#                 criminal=None,
#                 images=[],
#                 is_edit=False
#             ), e.status_code
#
#     # POST - Create or Update
#     try:
#         current_user_id = session_manager.get_current_user_id()
#
#         # Create address location if provided
#         address_id = None
#         latitude = request.form.get('latitude', type=float)
#         longitude = request.form.get('longitude', type=float)
#
#         if latitude and longitude:
#             location_request = CreateLocationRequest(
#                 latitude=latitude,
#                 longitude=longitude,
#                 address=request.form.get('address', '').strip() or None,
#                 city=request.form.get('city', '').strip() or None,
#                 state=request.form.get('state', '').strip() or None,
#                 country=request.form.get('country', '').strip() or None,
#                 postal_code=request.form.get('postal_code', '').strip() or None,
#                 description=request.form.get('location_description', '').strip() or None,
#                 created_by=current_user_id
#             )
#             location_response = location_utils.create_location(location_request)
#             address_id = location_response.id
#
#         # Determine if this is create or update
#         if criminal_id:
#             # UPDATE
#             update_request = UpdateCriminalRequest(
#                 criminal_id=criminal_id,
#                 alias=request.form.get('alias', '').strip() or None,
#                 is_wanted=request.form.get('is_wanted', 'off') == 'on',
#                 priority_level=request.form.get('priority_level', type=int),
#                 gang_affiliation=request.form.get('gang_affiliation', '').strip() or None,
#                 threat_level=request.form.get('threat_level', '').strip() or None,
#                 updated_by=current_user_id
#             )
#
#             response = criminal_service.update_criminal(update_request)
#             message = f'Criminal {response.first_name} {response.last_name} updated successfully!'
#         else:
#             # CREATE
#             create_request = CreateCriminalRequest(
#                 first_name=request.form.get('first_name', '').strip(),
#                 last_name=request.form.get('last_name', '').strip(),
#                 date_of_birth=request.form.get('date_of_birth', '').strip() or None,
#                 gender=request.form.get('gender', '').strip() or None,
#                 phone_number=request.form.get('phone_number', '').strip() or None,
#                 email=request.form.get('email', '').strip() or None,
#                 national_id=request.form.get('national_id', '').strip() or None,
#                 height=request.form.get('height', type=float),
#                 weight=request.form.get('weight', type=float),
#                 hair_color=request.form.get('hair_color', '').strip() or None,
#                 eye_color=request.form.get('eye_color', '').strip() or None,
#                 skin_tone=request.form.get('skin_tone', '').strip() or None,
#                 distinctive_features=request.form.get('distinctive_features', '').strip() or None,
#                 address_id=address_id,
#                 description=request.form.get('description', '').strip() or None,
#                 alias=request.form.get('alias', '').strip() or None,
#                 is_wanted=request.form.get('is_wanted', 'off') == 'on',
#                 priority_level=request.form.get('priority_level', 0, type=int),
#                 gang_affiliation=request.form.get('gang_affiliation', '').strip() or None,
#                 threat_level=request.form.get('threat_level', '').strip() or None,
#                 created_by=current_user_id
#             )
#
#             response = criminal_service.create_criminal(create_request)
#             criminal_id = response.id
#             message = f'Criminal {response.first_name} {response.last_name} created successfully!'
#
#         # Handle image uploads
#         uploaded_files = request.files.getlist('images')
#         if uploaded_files and uploaded_files[0].filename:
#             image_paths = []
#
#             for idx, file in enumerate(uploaded_files):
#                 if file and allowed_file(file.filename, current_app.config['ALLOWED_IMAGE_EXTENSIONS']):
#                     if not validate_file_size(file):
#                         flash(f'File {file.filename} exceeds maximum file size limit', 'warning')
#                         continue
#
#                     # Save file with microseconds and index for uniqueness
#                     filename = secure_filename(file.filename)
#                     timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
#                     filename = f"{criminal_id}_{timestamp}_{idx}_{filename}"
#                     filepath = os.path.join(current_app.config['UPLOAD_FOLDER_CRIMINALS'], filename)
#                     file.save(filepath)
#                     image_paths.append(filepath)
#
#             # Upload images with face vectors
#             if image_paths:
#                 try:
#                     criminal_service.image_utils.upload_multiple_images(
#                         person_id=criminal_id,
#                         image_paths=image_paths,
#                         uploaded_by=current_user_id
#                     )
#                 except Exception as img_error:
#                     flash(f'Some images failed: {str(img_error)}', 'warning')
#
#         flash(message, 'success')
#
#         # Create success response
#         api_response = ApiResponse.success(
#             value=response,
#             message=message
#         )
#
#         return jsonify(api_response.to_dict()), api_response.get_status_code()
#
#     except AppException as e:
#         error_detail = ErrorDetail(
#             title="Failed to Save Criminal",
#             details=[str(e)],
#             status=e.status_code
#         )
#         response = ApiResponse.failure(error=error_detail, message=str(e))
#         return jsonify(response.to_dict()), response.get_status_code()
#
#     except Exception as e:
#         error_detail = ErrorDetail(
#             title="Unexpected Error",
#             details=[f"An error occurred: {str(e)}"],
#             status=500
#         )
#         response = ApiResponse.failure(error=error_detail)
#         return jsonify(response.to_dict()), response.get_status_code()


@criminal_bp.route('/<string:criminal_id>/delete', methods=['POST'])
@auth.login_required
@auth.role_required('admin')
def delete_criminal(criminal_id):
    """Soft delete a criminal record - AJAX endpoint"""
    try:
        # Delete criminal
        response = criminal_service.delete_criminal(criminal_id)

        flash(response.message, 'success')

        # Create success response
        api_response = ApiResponse.success(
            value=response,
            message=response.message
        )

        return jsonify(api_response.to_dict()), api_response.get_status_code()

    except AppException as e:
        error_detail = ErrorDetail(
            title="Failed to Delete Criminal",
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


@criminal_bp.route('/wanted', methods=['GET'])
@auth.login_required
def get_wanted_criminals():
    """Get all wanted criminals - AJAX endpoint"""
    try:
        # Get wanted criminals
        wanted = criminal_service.get_wanted_criminals()

        # Create success response
        api_response = ApiResponse.success(
            value=[criminal.to_dict() for criminal in wanted],
            message=f"Found {len(wanted)} wanted criminal(s)"
        )

        return jsonify(api_response.to_dict()), api_response.get_status_code()

    except AppException as e:
        error_detail = ErrorDetail(
            title="Failed to Retrieve Wanted Criminals",
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
# CRIME MANAGEMENT ROUTES
# =============================================================================

@criminal_bp.route('/crimes', methods=['GET'])
@auth.login_required
def list_crimes():
    """List all crimes with pagination and filtering"""
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status', None, type=str)
        crime_type = request.args.get('crime_type', None, type=str)
        criminal_id = request.args.get('criminal_id', None, type=str)
        assigned_officer_id = request.args.get('assigned_officer_id', None, type=str)
        include_deleted = request.args.get('include_deleted', 'false', type=str).lower() == 'true'

        # Create list request
        list_request = ListCrimesRequest(
            page=page,
            per_page=per_page,
            status=status,
            crime_type=crime_type,
            criminal_id=criminal_id,
            assigned_officer_id=assigned_officer_id,
            include_deleted=include_deleted
        )

        # Get crimes
        response = criminal_service.list_crimes(list_request)

        return render_template(
            'criminal/crimes/list.jinja2',
            crimes=response.crimes,
            pagination={
                'total': response.total,
                'page': response.page,
                'per_page': response.per_page,
                'total_pages': response.total_pages
            },
            filters={
                'status': status,
                'crime_type': crime_type,
                'criminal_id': criminal_id,
                'assigned_officer_id': assigned_officer_id,
                'include_deleted': include_deleted
            }
        )

    except AppException as e:
        return render_template(
            'criminal/crimes/list.jinja2',
            crimes=[],
            pagination={}
        ), e.status_code


@criminal_bp.route('/crimes/<string:crime_id>', methods=['GET'])
@auth.login_required
def view_crime(crime_id):
    """View a single crime's details"""
    try:
        # Get crime
        crime_response = criminal_service.get_crime_by_id(crime_id)

        # Get victims
        victims = criminal_service.get_crime_victims(crime_id)

        # Get punishments
        punishments_request = ListPunishmentsRequest(crime_id=crime_id, page=1, per_page=100)
        punishments_response = criminal_service.list_punishments(punishments_request)

        # Get evidence
        evidence_request = ListEvidenceRequest(crime_id=crime_id, page=1, per_page=100)
        evidence_response = criminal_service.list_evidence(evidence_request)

        return render_template(
            'criminal/crimes/view.jinja2',
            crime=crime_response.to_dict(),
            victims=[victim.to_dict() for victim in victims],
            punishments=punishments_response.punishments,
            evidence=evidence_response.evidence
        )

    except AppException as e:
        flash(str(e), 'error')
        return render_template(
            'criminal/crimes/view.jinja2',
            crime={},
            victims=[],
            punishments=[],
            evidence=[]
        ), e.status_code


@criminal_bp.route('/<string:criminal_id>/add-crime/form', methods=['GET', 'POST'])
@auth.login_required
def add_crime_to_criminal_form(criminal_id):
    """Add crime form specifically for a criminal (pre-fills criminal_id)"""

    # GET - Show form with criminal pre-selected
    if request.method == 'GET':
        try:
            # Get criminal info for display
            criminal_response = criminal_service.get_criminal_by_id(criminal_id)

            return render_template(
                'criminal/crimes/form.jinja2',
                crime=None,
                criminal=criminal_response.to_dict(),
                is_edit=False,
                from_criminal_view=True
            )

        except AppException as e:
            flash(str(e), 'error')
            return render_template(
                'criminal/crimes/form.jinja2',
                crime=None,
                criminal=None,
                is_edit=False,
                from_criminal_view=True
            ), e.status_code

    # POST - Create crime for this criminal
    try:
        current_user_id = session_manager.get_current_user_id()

        # Create location for crime
        latitude = request.form.get('latitude', type=float)
        longitude = request.form.get('longitude', type=float)

        location_request = CreateLocationRequest(
            latitude=latitude,
            longitude=longitude,
            address=request.form.get('address', '').strip() or None,
            city=request.form.get('city', '').strip() or None,
            state=request.form.get('state', '').strip() or None,
            country=request.form.get('country', '').strip() or None,
            postal_code=request.form.get('postal_code', '').strip() or None,
            description=request.form.get('location_description', '').strip() or None,
            created_by=current_user_id
        )

        location_response = location_utils.create_location(location_request)

        # Create crime with pre-filled criminal_id
        create_request = CreateCrimeRequest(
            case_number=request.form.get('case_number', '').strip(),
            crime_type=request.form.get('crime_type', '').strip(),
            description=request.form.get('description', '').strip(),
            date_committed=request.form.get('date_committed', '').strip(),
            criminal_id=criminal_id,  # Pre-filled from URL
            location_id=location_response.id,
            assigned_officer_id=request.form.get('assigned_officer_id', '').strip() or None,
            reported_by=current_user_id
        )

        response = criminal_service.create_crime(create_request)
        message = f'Crime case {response.case_number} added to criminal successfully!'

        flash(message, 'success')

        # Create success response
        api_response = ApiResponse.success(
            value=response,
            message=message
        )

        return jsonify(api_response.to_dict()), api_response.get_status_code()

    except AppException as e:
        error_detail = ErrorDetail(
            title="Failed to Add Crime",
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


@criminal_bp.route('/crimes/form', methods=['GET', 'POST'])
@criminal_bp.route('/crimes/form/<string:crime_id>', methods=['GET', 'POST'])
@auth.login_required
def crime_form(crime_id=None):
    """Unified form for creating or editing crime (same template for both)"""

    # GET - Show form
    if request.method == 'GET':
        try:
            crime_data = None

            # If crime_id provided, fetch existing data for editing
            if crime_id:
                response = criminal_service.get_crime_by_id(crime_id)
                crime_data = response.to_dict()

            return render_template(
                'criminal/crimes/form.jinja2',
                crime=crime_data,
                criminal=None,
                is_edit=crime_id is not None,
                from_criminal_view=False
            )

        except AppException as e:
            flash(str(e), 'error')
            return render_template(
                'criminal/crimes/form.jinja2',
                crime=None,
                criminal=None,
                is_edit=False,
                from_criminal_view=False
            ), e.status_code

    # POST - Create or Update
    try:
        current_user_id = session_manager.get_current_user_id()

        # Determine if this is create or update
        if crime_id:
            # UPDATE
            update_request = UpdateCrimeRequest(
                crime_id=crime_id,
                status=request.form.get('status', '').strip() or None,
                assigned_officer_id=request.form.get('assigned_officer_id', '').strip() or None,
                description=request.form.get('description', '').strip() or None,
                updated_by=current_user_id
            )

            response = criminal_service.update_crime(update_request)
            message = f'Crime case {response.case_number} updated successfully!'
        else:
            # CREATE - Need location first
            latitude = request.form.get('latitude', type=float)
            longitude = request.form.get('longitude', type=float)

            location_request = CreateLocationRequest(
                latitude=latitude,
                longitude=longitude,
                address=request.form.get('address', '').strip() or None,
                city=request.form.get('city', '').strip() or None,
                state=request.form.get('state', '').strip() or None,
                country=request.form.get('country', '').strip() or None,
                postal_code=request.form.get('postal_code', '').strip() or None,
                description=request.form.get('location_description', '').strip() or None,
                created_by=current_user_id
            )

            location_response = location_utils.create_location(location_request)

            create_request = CreateCrimeRequest(
                case_number=request.form.get('case_number', '').strip(),
                crime_type=request.form.get('crime_type', '').strip(),
                description=request.form.get('description', '').strip(),
                date_committed=request.form.get('date_committed', '').strip(),
                criminal_id=request.form.get('criminal_id', '').strip(),
                location_id=location_response.id,
                assigned_officer_id=request.form.get('assigned_officer_id', '').strip() or None,
                reported_by=current_user_id
            )

            response = criminal_service.create_crime(create_request)
            message = f'Crime case {response.case_number} created successfully!'

        flash(message, 'success')

        # Create success response
        api_response = ApiResponse.success(
            value=response,
            message=message
        )

        return jsonify(api_response.to_dict()), api_response.get_status_code()

    except AppException as e:
        error_detail = ErrorDetail(
            title="Failed to Save Crime",
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


@criminal_bp.route('/crimes/<string:crime_id>/details', methods=['GET'])
@auth.login_required
def get_crime_details(crime_id):
    """Get full crime details with related data for inline/modal display - AJAX endpoint"""
    try:
        # Get crime
        crime_response = criminal_service.get_crime_by_id(crime_id)
        crime_data = crime_response.to_dict()

        # Get victims
        victims = criminal_service.get_crime_victims(crime_id)
        crime_data['victims'] = [victim.to_dict() for victim in victims]

        # Get punishments
        punishments_request = ListPunishmentsRequest(crime_id=crime_id, page=1, per_page=100)
        punishments_response = criminal_service.list_punishments(punishments_request)
        crime_data['punishments'] = punishments_response.punishments

        # Get evidence
        evidence_request = ListEvidenceRequest(crime_id=crime_id, page=1, per_page=100)
        evidence_response = criminal_service.list_evidence(evidence_request)
        crime_data['evidence'] = evidence_response.evidence

        # Create success response
        api_response = ApiResponse.success(
            value=crime_data,
            message="Crime details retrieved successfully"
        )

        return jsonify(api_response.to_dict()), api_response.get_status_code()

    except AppException as e:
        error_detail = ErrorDetail(
            title="Failed to Retrieve Crime Details",
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


@criminal_bp.route('/crimes/<string:crime_id>/delete', methods=['POST'])
@auth.login_required
@auth.role_required('admin')
def delete_crime(crime_id):
    """Soft delete a crime record - AJAX endpoint"""
    try:
        # Delete crime
        response = criminal_service.delete_crime(crime_id)

        flash(response.message, 'success')

        # Create success response
        api_response = ApiResponse.success(
            value=response,
            message=response.message
        )

        return jsonify(api_response.to_dict()), api_response.get_status_code()

    except AppException as e:
        error_detail = ErrorDetail(
            title="Failed to Delete Crime",
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


@criminal_bp.route('/crimes/<string:crime_id>/assign-officer', methods=['POST'])
@auth.login_required
@auth.role_required('admin')
def assign_officer_to_crime(crime_id):
    """Assign an officer to a crime - AJAX endpoint"""
    try:
        officer_id = request.form.get('officer_id', '').strip()

        # Assign officer
        response = criminal_service.assign_officer_to_crime(crime_id, officer_id)

        flash('Officer assigned successfully!', 'success')

        # Create success response
        api_response = ApiResponse.success(
            value=response,
            message='Officer assigned successfully!'
        )

        return jsonify(api_response.to_dict()), api_response.get_status_code()

    except AppException as e:
        error_detail = ErrorDetail(
            title="Failed to Assign Officer",
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


@criminal_bp.route('/crimes/unassigned', methods=['GET'])
@auth.login_required
def get_unassigned_cases():
    """Get all unassigned crime cases - AJAX endpoint"""
    try:
        # Get unassigned cases
        cases = criminal_service.get_unassigned_cases()

        # Create success response
        api_response = ApiResponse.success(
            value=[case.to_dict() for case in cases],
            message=f"Found {len(cases)} unassigned case(s)"
        )

        return jsonify(api_response.to_dict()), api_response.get_status_code()

    except AppException as e:
        error_detail = ErrorDetail(
            title="Failed to Retrieve Unassigned Cases",
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
# CRIME VICTIM MANAGEMENT ROUTES
# =============================================================================

@criminal_bp.route('/crimes/<string:crime_id>/victims/form', methods=['GET', 'POST'])
@auth.login_required
def victim_form(crime_id):
    """Unified form for adding victim to crime"""

    # GET - Show form
    if request.method == 'GET':
        try:
            # Fetch crime data for display
            crime_response = criminal_service.get_crime_by_id(crime_id)
            crime_data = crime_response.to_dict()

            # Get the criminal info to pre-fill as potential victim
            criminal = None
            if crime_data.get('criminal_id'):
                try:
                    criminal_response = criminal_service.get_criminal_by_id(crime_data['criminal_id'])
                    criminal = criminal_response.to_dict()
                except:
                    pass

            return render_template(
                'criminal/crimes/victim_form.jinja2',
                crime=crime_data,
                criminal=criminal,
                crime_id=crime_id
            )

        except AppException as e:
            flash(str(e), 'error')
            return render_template(
                'criminal/crimes/victim_form.jinja2',
                crime=None,
                criminal=None,
                crime_id=crime_id
            ), e.status_code

    # POST - Add victim
    try:
        current_user_id = session_manager.get_current_user_id()

        # Fetch crime data for verification
        crime_response = criminal_service.get_crime_by_id(crime_id)

        # Get full name from form
        full_name = request.form.get('full_name', '').strip()

        if not full_name:
            error_detail = ErrorDetail(
                title="Validation Error",
                details=["Victim full name is required"],
                status=400
            )
            response = ApiResponse.failure(error=error_detail)
            return jsonify(response.to_dict()), response.get_status_code()

        # Create victim request
        victim_request = AddCrimeVictimRequest(
            crime_id=crime_id,
            full_name=full_name,
            injury_description=request.form.get('injury_description', '').strip() or None,
            medical_report_path=None,
            recorded_by=current_user_id
        )

        # Handle medical report upload if provided
        filepath = None
        if 'medical_report' in request.files:
            file = request.files['medical_report']
            if file and file.filename and allowed_file(file.filename,
                                                       current_app.config['ALLOWED_EVIDENCE_EXTENSIONS']):
                if validate_file_size(file):
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"medical_report_{crime_id}_{timestamp}_{filename}"
                    filepath = os.path.join(current_app.config['UPLOAD_FOLDER_EVIDENCE'], filename)
                    file.save(filepath)
                    victim_request.medical_report_path = filepath
                else:
                    error_detail = ErrorDetail(
                        title="Validation Error",
                        details=["Medical report exceeds maximum file size limit"],
                        status=400
                    )
                    response = ApiResponse.failure(error=error_detail)
                    return jsonify(response.to_dict()), response.get_status_code()

        # Add victim
        response = criminal_service.add_victim_to_crime(victim_request)
        message = 'Victim added to crime successfully!'

        flash(message, 'success')

        # Convert response to dict if it has to_dict method
        response_data = response.to_dict() if hasattr(response, 'to_dict') else response

        # Create success response
        api_response = ApiResponse.success(
            value=response_data,
            message=message
        )

        return jsonify(api_response.to_dict()), api_response.get_status_code()

    except AppException as e:
        # Clean up uploaded file if error occurred
        if 'filepath' in locals() and filepath and os.path.exists(filepath):
            try:
                os.remove(filepath)
            except:
                pass

        error_detail = ErrorDetail(
            title="Failed to Add Victim",
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

        error_detail = ErrorDetail(
            title="Unexpected Error",
            details=[f"An error occurred: {str(e)}"],
            status=500
        )
        response = ApiResponse.failure(error=error_detail)
        return jsonify(response.to_dict()), response.get_status_code()


@criminal_bp.route('/crimes/<string:crime_id>/victims', methods=['GET'])
@auth.login_required
def get_crime_victims(crime_id):
    """Get all victims of a crime - AJAX endpoint"""
    try:
        # Get victims
        victims = criminal_service.get_crime_victims(crime_id)

        # Create success response
        api_response = ApiResponse.success(
            value=[victim.to_dict() for victim in victims],
            message=f"Found {len(victims)} victim(s)"
        )

        return jsonify(api_response.to_dict()), api_response.get_status_code()

    except AppException as e:
        error_detail = ErrorDetail(
            title="Failed to Retrieve Victims",
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
# PUNISHMENT MANAGEMENT ROUTES
# =============================================================================

@criminal_bp.route('/crimes/<string:crime_id>/punishments/form', methods=['GET', 'POST'])
@criminal_bp.route('/crimes/<string:crime_id>/punishments/form/<string:punishment_id>', methods=['GET', 'POST'])
@auth.login_required
def punishment_form(crime_id, punishment_id=None):
    """Unified form for creating or editing punishment (same template for both)"""

    # GET - Show form
    if request.method == 'GET':
        try:
            punishment_data = None
            crime_data = None

            # Fetch crime data for display (required for both create and edit)
            if crime_id:
                crime_response = criminal_service.get_crime_by_id(crime_id)
                crime_data = crime_response.to_dict()
            else:
                raise AppException("Crime ID is required", 400)

            # If punishment_id provided, fetch existing data for editing
            if punishment_id:
                # Get punishment by fetching from list and filtering (since we don't have get_by_id)
                punishments_request = ListPunishmentsRequest(page=1, per_page=1000)
                punishments_response = criminal_service.list_punishments(punishments_request)

                # Find the specific punishment
                punishment_data = next(
                    (p for p in punishments_response.punishments if p['id'] == punishment_id),
                    None
                )

                if not punishment_data:
                    raise AppException("Punishment not found", 404)

                # Verify punishment belongs to this crime
                if punishment_data['crime_id'] != crime_id:
                    raise AppException("Punishment does not belong to this crime", 403)

            return render_template(
                'criminal/crimes/punishment_form.jinja2',
                punishment=punishment_data,
                crime=crime_data,
                is_edit=punishment_id is not None
            )

        except AppException as e:
            flash(str(e), 'error')
            # Try to fetch crime data even on error for proper breadcrumb display
            try:
                if crime_id:
                    crime_response = criminal_service.get_crime_by_id(crime_id)
                    crime_data = crime_response.to_dict()
                else:
                    crime_data = None
            except:
                crime_data = None

            return render_template(
                'criminal/crimes/punishment_form.jinja2',
                punishment=None,
                crime=crime_data,
                is_edit=False
            ), e.status_code

    # POST - Create or Update
    try:
        current_user_id = session_manager.get_current_user_id()

        # Fetch crime data for verification
        crime_response = criminal_service.get_crime_by_id(crime_id)

        # Determine if this is create or update
        if punishment_id:
            # UPDATE
            update_request = UpdatePunishmentRequest(
                punishment_id=punishment_id,
                status=request.form.get('status', '').strip() or None,
                amount_paid=request.form.get('amount_paid', type=float),
                end_date=request.form.get('end_date', '').strip() or None,
                details=request.form.get('details', '').strip() or None,
                updated_by=current_user_id
            )

            response = criminal_service.update_punishment(update_request)
            message = 'Punishment updated successfully!'
        else:
            # CREATE
            # Get form data
            punishment_type = request.form.get('type', '').strip()
            status = request.form.get('status', '').strip()
            start_date = request.form.get('start_date', '').strip() or None
            end_date = request.form.get('end_date', '').strip() or None
            details = request.form.get('details', '').strip() or None

            # Validate punishment type
            valid_types = ['jail', 'prison', 'fine', 'probation', 'community_service',
                          'suspended_sentence', 'acquitted', 'death_penalty']
            if punishment_type not in valid_types:
                raise AppException(f"Invalid punishment type: {punishment_type}", 400)

            # Validate status
            valid_statuses = ['pending', 'active', 'completed', 'suspended',
                            'revoked', 'overdue', 'partially_paid']
            if status not in valid_statuses:
                raise AppException(f"Invalid status: {status}", 400)

            # Get conditional fields based on punishment type
            amount = None
            duration = None

            if punishment_type == 'fine':
                amount = request.form.get('amount', type=float)
                if not amount or amount <= 0:
                    raise AppException("Fine requires a valid amount greater than 0", 400)

            if punishment_type in ['jail', 'prison', 'community_service', 'probation']:
                duration = request.form.get('duration', type=int)
                if not duration or duration <= 0:
                    raise AppException(f"{punishment_type.replace('_', ' ').title()} requires a valid duration greater than 0", 400)

            # No location needed for punishments (remove location logic)
            create_request = CreatePunishmentRequest(
                crime_id=crime_id,
                type=punishment_type,
                status=status,
                start_date=start_date,
                end_date=end_date,
                amount=amount,
                duration=duration,
                location_id=None,  # Set to None
                details=details,
                assigned_by=current_user_id
            )

            response = criminal_service.create_punishment(create_request)
            message = 'Punishment created successfully!'

        flash(message, 'success')

        # Create success response
        api_response = ApiResponse.success(
            value=response,
            message=message
        )

        return jsonify(api_response.to_dict()), api_response.get_status_code()

    except AppException as e:
        error_detail = ErrorDetail(
            title="Failed to Save Punishment",
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


@criminal_bp.route('/punishments', methods=['GET'])
@auth.login_required
def list_punishments():
    """List punishments with filters - AJAX endpoint"""
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        crime_id = request.args.get('crime_id', None, type=str)
        punishment_type = request.args.get('type', None, type=str)
        status = request.args.get('status', None, type=str)
        include_deleted = request.args.get('include_deleted', 'false', type=str).lower() == 'true'

        # Create list request
        list_request = ListPunishmentsRequest(
            page=page,
            per_page=per_page,
            crime_id=crime_id,
            type=punishment_type,
            status=status,
            include_deleted=include_deleted
        )

        # Get punishments
        response = criminal_service.list_punishments(list_request)

        # Create success response
        api_response = ApiResponse.success(
            value=response,
            message=response.message
        )

        return jsonify(api_response.to_dict()), api_response.get_status_code()

    except AppException as e:
        error_detail = ErrorDetail(
            title="Failed to List Punishments",
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


@criminal_bp.route('/punishments/<string:punishment_id>/record-payment', methods=['POST'])
@auth.login_required
def record_fine_payment(punishment_id):
    """Record a fine payment - AJAX endpoint"""
    try:
        amount = request.form.get('amount', type=float)

        if not amount or amount <= 0:
            error_detail = ErrorDetail(
                title="Validation Error",
                details=["Payment amount must be greater than 0"],
                status=400
            )
            response = ApiResponse.failure(error=error_detail)
            return jsonify(response.to_dict()), response.get_status_code()

        # Record payment
        response = criminal_service.record_fine_payment(punishment_id, amount)

        flash(f'Payment of ${amount} recorded successfully!', 'success')

        # Create success response
        api_response = ApiResponse.success(
            value=response,
            message=f'Payment of ${amount} recorded successfully!'
        )

        return jsonify(api_response.to_dict()), api_response.get_status_code()

    except AppException as e:
        error_detail = ErrorDetail(
            title="Failed to Record Payment",
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
# EVIDENCE MANAGEMENT ROUTES
# =============================================================================

@criminal_bp.route('/crimes/<string:crime_id>/evidence/form', methods=['GET', 'POST'])
@criminal_bp.route('/crimes/<string:crime_id>/evidence/form/<string:evidence_id>', methods=['GET', 'POST'])
@auth.login_required
def evidence_form(crime_id, evidence_id=None):
    """Unified form for creating or editing evidence (same template for both)"""

    # GET - Show form
    if request.method == 'GET':
        try:
            evidence_data = None
            crime_data = None

            # Fetch crime data for display (required for both create and edit)
            if crime_id:
                crime_response = criminal_service.get_crime_by_id(crime_id)
                crime_data = crime_response.to_dict()
            else:
                raise AppException("Crime ID is required", 400)

            # If evidence_id provided, fetch existing data for editing
            if evidence_id:
                # Get evidence by fetching from list and filtering
                evidence_request = ListEvidenceRequest(page=1, per_page=1000)
                evidence_response = criminal_service.list_evidence(evidence_request)

                # Find the specific evidence
                evidence_data = next(
                    (e for e in evidence_response.evidence if e['id'] == evidence_id),
                    None
                )

                if not evidence_data:
                    raise AppException("Evidence not found", 404)

                # Verify evidence belongs to this crime
                if evidence_data['crime_id'] != crime_id:
                    raise AppException("Evidence does not belong to this crime", 403)

            return render_template(
                'criminal/crimes/evidence_form.jinja2',
                evidence=evidence_data,
                crime=crime_data,
                is_edit=evidence_id is not None
            )

        except AppException as e:
            flash(str(e), 'error')
            # Try to fetch crime data even on error for proper breadcrumb display
            try:
                if crime_id:
                    crime_response = criminal_service.get_crime_by_id(crime_id)
                    crime_data = crime_response.to_dict()
                else:
                    crime_data = None
            except:
                crime_data = None

            return render_template(
                'criminal/crimes/evidence_form.jinja2',
                evidence=None,
                crime=crime_data,
                is_edit=False
            ), e.status_code

    # POST - Create or Update
    try:
        current_user_id = session_manager.get_current_user_id()

        # Fetch crime data for verification
        crime_response = criminal_service.get_crime_by_id(crime_id)

        # Determine if this is create or update
        if evidence_id:
            # UPDATE
            update_request = UpdateEvidenceRequest(
                evidence_id=evidence_id,
                description=request.form.get('description', '').strip() or None,
                storage_location=request.form.get('storage_location', '').strip() or None,
                updated_by=current_user_id
            )

            response = criminal_service.update_evidence(update_request)
            message = 'Evidence updated successfully!'
        else:
            # CREATE
            # Get the type and convert to uppercase to match database enum
            evidence_type = request.form.get('type', '').strip().upper()

            evidence_request = CreateEvidenceRequest(
                crime_id=crime_id,
                description=request.form.get('description', '').strip(),
                type=evidence_type,  # Now uppercase
                file_path=None,
                collected_by=current_user_id,  # Use current user ID
                collected_date=request.form.get('collected_date', '').strip() or None,
                storage_location=request.form.get('storage_location', '').strip() or None
            )

            # Handle evidence file upload if provided
            if 'evidence_file' in request.files:
                file = request.files['evidence_file']
                if file and file.filename and allowed_file(file.filename,
                                                           current_app.config['ALLOWED_EVIDENCE_EXTENSIONS']):
                    if validate_file_size(file):
                        filename = secure_filename(file.filename)
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename = f"evidence_{crime_id}_{timestamp}_{filename}"
                        filepath = os.path.join(current_app.config['UPLOAD_FOLDER_EVIDENCE'], filename)
                        file.save(filepath)
                        evidence_request.file_path = filepath
                    else:
                        error_detail = ErrorDetail(
                            title="Validation Error",
                            details=["Evidence file exceeds maximum file size limit"],
                            status=400
                        )
                        response = ApiResponse.failure(error=error_detail)
                        return jsonify(response.to_dict()), response.get_status_code()

            response = criminal_service.create_evidence(evidence_request)
            message = 'Evidence created successfully!'

        flash(message, 'success')

        # Convert response to dict if it has to_dict method
        response_data = response.to_dict() if hasattr(response, 'to_dict') else response

        # Create success response
        api_response = ApiResponse.success(
            value=response_data,
            message=message
        )

        return jsonify(api_response.to_dict()), api_response.get_status_code()

    except AppException as e:
        # Clean up uploaded file if error occurred
        if 'filepath' in locals() and filepath and os.path.exists(filepath):
            try:
                os.remove(filepath)
            except:
                pass

        error_detail = ErrorDetail(
            title="Failed to Save Evidence",
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

        error_detail = ErrorDetail(
            title="Unexpected Error",
            details=[f"An error occurred: {str(e)}"],
            status=500
        )
        response = ApiResponse.failure(error=error_detail)
        return jsonify(response.to_dict()), response.get_status_code()


@criminal_bp.route('/evidence', methods=['GET'])
@auth.login_required
def list_evidence():
    """List evidence with filters - AJAX endpoint"""
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        crime_id = request.args.get('crime_id', None, type=str)
        evidence_type = request.args.get('type', None, type=str)
        collected_by = request.args.get('collected_by', None, type=str)
        include_deleted = request.args.get('include_deleted', 'false', type=str).lower() == 'true'

        # Create list request
        list_request = ListEvidenceRequest(
            page=page,
            per_page=per_page,
            crime_id=crime_id,
            type=evidence_type,
            collected_by=collected_by,
            include_deleted=include_deleted
        )

        # Get evidence
        response = criminal_service.list_evidence(list_request)

        # Create success response
        api_response = ApiResponse.success(
            value=response,
            message=response.message
        )

        return jsonify(api_response.to_dict()), api_response.get_status_code()

    except AppException as e:
        error_detail = ErrorDetail(
            title="Failed to List Evidence",
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
# IMAGE MANAGEMENT ROUTES (for criminals)
# =============================================================================

@criminal_bp.route('/<string:criminal_id>/upload-image', methods=['POST'])
@auth.login_required
def upload_criminal_image(criminal_id):
    """Upload an image for a criminal - AJAX endpoint"""
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

        if not allowed_file(file.filename, current_app.config['ALLOWED_IMAGE_EXTENSIONS']):
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
        filename = f"{criminal_id}_{timestamp}_{filename}"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER_CRIMINALS'], filename)
        file.save(filepath)

        # Get primary flag
        is_primary = request.form.get('is_primary', 'false').lower() == 'true'

        # Create image request
        image_request = CreatePersonImageRequest(
            person_id=criminal_id,
            image_path=filepath,
            is_primary=is_primary,
            uploaded_by=current_user_id
        )

        # Upload image with face vector
        image_response = criminal_service.image_utils.upload_person_image(image_request)

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


@criminal_bp.route('/images/<string:image_id>/delete', methods=['POST'])
@auth.login_required
def delete_criminal_image(image_id):
    """Delete a criminal image - AJAX endpoint"""
    try:
        # Delete image
        success = criminal_service.image_utils.delete_person_image(image_id)

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


@criminal_bp.route('/<string:criminal_id>/images/<string:image_id>/set-primary', methods=['POST'])
@auth.login_required
def set_criminal_primary_image(criminal_id, image_id):
    """Set an image as primary for criminal - AJAX endpoint"""
    try:
        # Set primary image
        image_response = criminal_service.image_utils.set_primary_image(
            image_id=image_id,
            person_id=criminal_id
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
        response = ApiResponse.failure(error=error_detail)
        return jsonify(response.to_dict()), response.get_status_code()


# =============================================================================
# STATISTICS ROUTE
# =============================================================================

@criminal_bp.route('/statistics', methods=['GET'])
@auth.login_required
def get_criminal_statistics():
    """Get criminal-related statistics - AJAX endpoint"""
    try:
        # Get statistics
        stats = criminal_service.get_criminal_statistics()

        # Create success response
        api_response = ApiResponse.success(
            value=stats,
            message="Criminal statistics retrieved successfully"
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