from datetime import datetime

from flask import Blueprint, render_template, request, jsonify, flash, current_app

from src.modules.crime_analysis.domain.services.alert_broadcast_service import AlertBroadcastService
from src.modules.crime_analysis.domain.services.crime_analysis_service import CrimeAnalysisService
from src.modules.crime_analysis.presentation.dtos.analysis_dtos import (
    GenerateAnalysisReportRequest,
    GetMapDataRequest,
    GetIndividualCrimeMapDataRequest,
    ListCrimeAnalysesRequest,
    ListAlertBroadcastsRequest
)

from src.modules.authentication.domain.models.user import User
from src.modules.authentication.domain.repositories.user_repository import UserRepository
from src.shared.configs.security.session_decorators import SessionAuthDecorators
from src.shared.configs.security.session_manager import SessionManager
from src.shared.configs.exceptions.exceptions import AppException
from src.shared.response.api_response import ApiResponse
from src.shared.response.error_detail import ErrorDetail

# Create blueprint
analysis_bp = Blueprint(
    'analysis',
    __name__,
    template_folder='../templates',
    url_prefix='/analysis'
)

# Initialize services
analysis_service = CrimeAnalysisService()
alert_service = AlertBroadcastService()
user_repository = UserRepository()
session_manager = SessionManager[User](user_repository)

# Initialize auth decorators
auth = SessionAuthDecorators(
    session_manager=session_manager,
    unauthorized_url='/',
    home_url='/dashboard'
)


# Context processor to inject current user
@analysis_bp.app_context_processor
def inject_current_user():
    """Inject current user into all templates"""
    return {
        'current_user': session_manager.get_current_user()
    }


# =============================================================================
# ANALYSIS PREVIEW & GENERATION ROUTES
# =============================================================================

@analysis_bp.route('/preview', methods=['GET', 'POST'])
@auth.login_required
def preview_analysis():
    """
    Preview crime analysis WITHOUT saving to database.
    Shows map with crimes/hotspots, analysis summary, recommendations, and alerts.
    """

    # GET - Show preview form
    if request.method == 'GET':
        try:
            # Calculate default date range: 6 months before today
            from datetime import timedelta
            today = datetime.now()
            six_months_ago = today - timedelta(days=180)

            # Format dates for input fields (YYYY-MM-DD)
            default_start_date = six_months_ago.strftime('%Y-%m-%d')
            default_end_date = today.strftime('%Y-%m-%d')

            return render_template(
                'analysis/preview.jinja2',
                default_start_date=default_start_date,
                default_end_date=default_end_date
            )

        except AppException as e:
            flash(str(e), 'error')
            return render_template(
                'analysis/preview.jinja2',
                default_start_date=None,
                default_end_date=None
            ), e.status_code

    # POST - Generate preview
    try:
        current_user_id = session_manager.get_current_user_id()

        # Get form data (user can override defaults)
        start_date = request.form.get('start_date', '').strip()
        end_date = request.form.get('end_date', '').strip()

        # ✅ NEW: Get clustering parameters with defaults
        radius_km = float(request.form.get('radius_km', '2.0'))
        min_incidents = int(request.form.get('min_incidents', '3'))

        include_hotspots = request.form.get('include_hotspots', 'false').lower() == 'true'
        include_trends = request.form.get('include_trends', 'false').lower() == 'true'
        include_recommendations = request.form.get('include_recommendations', 'false').lower() == 'true'

        if not start_date or not end_date:
            error_detail = ErrorDetail(
                title="Validation Error",
                details=["Start date and end date are required"],
                status=400
            )
            response = ApiResponse.failure(error=error_detail)
            return jsonify(response.to_dict()), response.get_status_code()

        # ✅ Create preview request with NEW parameters
        preview_request = GenerateAnalysisReportRequest(
            start_date=start_date,
            end_date=end_date,
            generated_by=current_user_id,
            radius_km=radius_km,  # ✅ NEW
            min_incidents=min_incidents,  # ✅ NEW
            include_hotspots=include_hotspots,
            include_trends=include_trends,
            include_recommendations=include_recommendations
        )

        # Generate preview (not saved to database)
        preview_response = analysis_service.preview_crime_analysis(preview_request)

        # Get individual crimes for tactical map view
        crime_map_request = GetIndividualCrimeMapDataRequest(
            start_date=start_date,
            end_date=end_date,
            limit=1000
        )
        crime_map_response = analysis_service.get_individual_crime_map_data(crime_map_request)

        # Build preview data
        preview_data = {
            'analysis': preview_response.analysis,
            'hotspots': preview_response.hotspots,
            'trends': preview_response.trends,
            'recommendations': preview_response.recommendations,
            'individual_crimes': crime_map_response.crimes,
            'preview_alerts': []  # Preview of alerts that would be sent
        }

        current_app.logger.info(f"current hotspots : {preview_response.hotspots}")
        current_app.logger.info(f"current individual_crimes : {crime_map_response.crimes}")

        # Generate preview alerts for high/critical hotspots (not saved or sent)
        for hotspot in preview_response.hotspots:
            risk_level = hotspot.get('risk_level', '').lower()
            if risk_level in ['high', 'critical']:
                location = hotspot.get('location', {})
                area = location.get('city') or location.get('address') or 'area'
                incident_count = hotspot.get('incident_count', 0)
                is_missing = hotspot.get('is_missing_person_hotspot', False)

                if is_missing:
                    alert_message = (
                        f"High number of missing person cases reported in {area}. "
                        f"{incident_count} incidents recorded. "
                        f"Residents are urged to be vigilant, report suspicious activities, "
                        f"and ensure safety of vulnerable persons. Contact Police: (040)2717860"
                    )
                else:
                    crime_type = hotspot.get('crime_type') or 'criminal activity'
                    alert_message = (
                        f"Increased {crime_type} incidents in {area}. "
                        f"{incident_count} cases reported. "
                        f"Residents should take precautions, secure properties, and report "
                        f"any suspicious behavior immediately. Contact Police: (040)2717860"
                    )

                preview_data['preview_alerts'].append({
                    'hotspot_id': hotspot.get('id'),
                    'location': area,
                    'message': alert_message,
                    'recipient_count': alert_service.get_recipient_count(hotspot.get('location_id')),
                    'status': 'pending',
                    'risk_level': risk_level
                })

        # Create success response
        api_response = ApiResponse.success(
            value=preview_data,
            message="Analysis preview generated successfully (not saved to database)"
        )

        return jsonify(api_response.to_dict()), api_response.get_status_code()

    except AppException as e:
        error_detail = ErrorDetail(
            title="Preview Generation Failed",
            details=[str(e)],
            status=e.status_code
        )
        response = ApiResponse.failure(error=error_detail, message=str(e))
        return jsonify(response.to_dict()), response.get_status_code()

    except Exception as e:
        current_app.logger.error(f"Analysis preview error: {e}")
        error_detail = ErrorDetail(
            title="Unexpected Error",
            details=[f"An error occurred: {str(e)}"],
            status=500
        )
        response = ApiResponse.failure(error=error_detail)
        return jsonify(response.to_dict()), response.get_status_code()


@analysis_bp.route('/generate', methods=['POST'])
@auth.login_required
def generate_analysis():
    """
    Generate and SAVE crime analysis to database.
    Creates analysis, hotspots, trends, recommendations, and alert broadcasts.
    """
    try:
        current_user_id = session_manager.get_current_user_id()

        # Get form data
        start_date = request.form.get('start_date', '').strip()
        end_date = request.form.get('end_date', '').strip()

        # NEW: Get clustering parameters with defaults
        radius_km = float(request.form.get('radius_km', '2.0'))
        min_incidents = int(request.form.get('min_incidents', '3'))

        include_hotspots = request.form.get('include_hotspots', 'true').lower() == 'true'
        include_trends = request.form.get('include_trends', 'true').lower() == 'true'
        include_recommendations = request.form.get('include_recommendations', 'true').lower() == 'true'

        if not start_date or not end_date:
            error_detail = ErrorDetail(
                title="Validation Error",
                details=["Start date and end date are required"],
                status=400
            )
            response = ApiResponse.failure(error=error_detail)
            return jsonify(response.to_dict()), response.get_status_code()

        # Create generation request with NEW parameters
        generate_request = GenerateAnalysisReportRequest(
            start_date=start_date,
            end_date=end_date,
            generated_by=current_user_id,
            radius_km=radius_km,  # NEW
            min_incidents=min_incidents,  # NEW
            include_hotspots=include_hotspots,
            include_trends=include_trends,
            include_recommendations=include_recommendations
        )

        # Generate and save analysis
        analysis_response = analysis_service.generate_crime_analysis(generate_request)

        flash('Crime analysis report generated successfully!', 'success')

        # Create success response with redirect
        api_response = ApiResponse.success(
            value={
                'analysis_id': analysis_response.analysis['id'],
                'redirect_url': f"/analysis/{analysis_response.analysis['id']}"
            },
            message='Crime analysis report generated successfully!'
        )

        return jsonify(api_response.to_dict()), api_response.get_status_code()

    except AppException as e:
        error_detail = ErrorDetail(
            title="Analysis Generation Failed",
            details=[str(e)],
            status=e.status_code
        )
        response = ApiResponse.failure(error=error_detail, message=str(e))
        return jsonify(response.to_dict()), response.get_status_code()

    except Exception as e:
        current_app.logger.error(f"Analysis generation error: {e}")
        error_detail = ErrorDetail(
            title="Unexpected Error",
            details=[f"An error occurred: {str(e)}"],
            status=500
        )
        response = ApiResponse.failure(error=error_detail)
        return jsonify(response.to_dict()), response.get_status_code()


# =============================================================================
# SAVED ANALYSIS REPORTS MANAGEMENT
# =============================================================================

@analysis_bp.route('/', methods=['GET'])
@auth.login_required
def list_analyses():
    """List all saved crime analysis reports with pagination and filtering"""
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        generated_by = request.args.get('generated_by', None, type=str)
        start_date = request.args.get('start_date', None, type=str)
        end_date = request.args.get('end_date', None, type=str)
        include_deleted = request.args.get('include_deleted', 'false', type=str).lower() == 'true'

        # Create list request
        list_request = ListCrimeAnalysesRequest(
            page=page,
            per_page=per_page,
            generated_by=generated_by,
            start_date=start_date,
            end_date=end_date,
            include_deleted=include_deleted
        )

        # Get analyses
        response = analysis_service.list_crime_analyses(list_request)

        return render_template(
            'analysis/list.jinja2',
            analyses=response.analyses,
            pagination={
                'total': response.total,
                'page': response.page,
                'per_page': response.per_page,
                'total_pages': response.total_pages
            },
            filters={
                'generated_by': generated_by,
                'start_date': start_date,
                'end_date': end_date,
                'include_deleted': include_deleted
            }
        )

    except AppException as e:
        return render_template(
            'analysis/list.jinja2',
            analyses=[],
            pagination={}
        ), e.status_code


@analysis_bp.route('/<string:analysis_id>', methods=['GET'])
@auth.login_required
def view_analysis(analysis_id):
    """
    View a saved crime analysis report with all related data.
    Shows hotspots, trends, recommendations, and alert broadcasts.
    """
    try:
        # Get analysis
        analysis_response = analysis_service.get_crime_analysis_by_id(analysis_id)
        analysis_data = analysis_response.to_dict()

        # Get hotspots for this analysis
        from src.modules.crime_analysis.presentation.dtos.analysis_dtos import ListCrimeHotspotsRequest
        hotspots_request = ListCrimeHotspotsRequest(
            analysis_id=analysis_id,
            page=1,
            per_page=100
        )
        hotspots_response = analysis_service.list_crime_hotspots(hotspots_request)

        # Get trends for this analysis
        from src.modules.crime_analysis.presentation.dtos.analysis_dtos import ListCrimeTrendsRequest
        trends_request = ListCrimeTrendsRequest(
            analysis_id=analysis_id,
            page=1,
            per_page=100
        )
        trends_response = analysis_service.list_crime_trends(trends_request)

        # Get recommendations for this analysis
        from src.modules.crime_analysis.presentation.dtos.analysis_dtos import ListRecommendationsRequest
        recommendations_request = ListRecommendationsRequest(
            analysis_id=analysis_id,
            page=1,
            per_page=100
        )
        recommendations_response = analysis_service.list_recommendations(recommendations_request)

        # Get alerts for hotspots in this analysis
        all_alerts = []
        for hotspot in hotspots_response.hotspots:
            try:
                alerts_request = ListAlertBroadcastsRequest(
                    hotspot_id=hotspot['id'],
                    page=1,
                    per_page=100
                )
                alerts_response = alert_service.list_alert_broadcasts(alerts_request)
                all_alerts.extend(alerts_response.alerts)
            except:
                continue

        # Get individual crimes for tactical map view
        crime_map_request = GetIndividualCrimeMapDataRequest(
            start_date=analysis_data['analysis_period_start'],
            end_date=analysis_data['analysis_period_end'],
            limit=1000
        )
        crime_map_response = analysis_service.get_individual_crime_map_data(crime_map_request)

        return render_template(
            'analysis/view.jinja2',
            analysis=analysis_data,
            hotspots=hotspots_response.hotspots,
            trends=trends_response.trends,
            recommendations=recommendations_response.recommendations,
            alerts=all_alerts,
            individual_crimes=crime_map_response.crimes
        )

    except AppException as e:
        flash(str(e), 'error')
        return render_template(
            'analysis/view.jinja2',
            analysis={},
            hotspots=[],
            trends=[],
            recommendations=[],
            alerts=[],
            individual_crimes=[]
        ), e.status_code


@analysis_bp.route('/<string:analysis_id>/delete', methods=['POST'])
@auth.login_required
@auth.role_required('admin')
def delete_analysis(analysis_id):
    """Soft delete a crime analysis report - AJAX endpoint"""
    try:
        # Delete analysis
        response = analysis_service.delete_crime_analysis(analysis_id)

        flash(response.message, 'success')

        # Create success response
        api_response = ApiResponse.success(
            value=response,
            message=response.message
        )

        return jsonify(api_response.to_dict()), api_response.get_status_code()

    except AppException as e:
        error_detail = ErrorDetail(
            title="Failed to Delete Analysis",
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
# ALERT BROADCAST MANAGEMENT
# =============================================================================

@analysis_bp.route('/alerts/<string:alert_id>/send', methods=['POST'])
@auth.login_required
@auth.role_required('admin')
def send_alert(alert_id):
    """Send an alert broadcast - AJAX endpoint"""
    try:
        # Send alert
        response = alert_service.send_alert_broadcast(alert_id)

        flash('Alert broadcast sent successfully!', 'success')

        # Create success response
        api_response = ApiResponse.success(
            value=response.to_dict(),
            message='Alert broadcast sent successfully!'
        )

        return jsonify(api_response.to_dict()), api_response.get_status_code()

    except AppException as e:
        error_detail = ErrorDetail(
            title="Failed to Send Alert",
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

@analysis_bp.route('/alerts/<string:alert_id>/resend', methods=['POST'])
@auth.login_required
@auth.role_required('admin')
def resend_alert(alert_id):
    """Resend an alert broadcast - AJAX endpoint"""
    try:
        # Resend alert
        response = alert_service.resend_alert_broadcast(alert_id)

        flash('Alert broadcast resent successfully!', 'success')

        # Create success response
        api_response = ApiResponse.success(
            value=response.to_dict(),
            message='Alert broadcast resent successfully!'
        )

        return jsonify(api_response.to_dict()), api_response.get_status_code()

    except AppException as e:
        error_detail = ErrorDetail(
            title="Failed to Resend Alert",
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

@analysis_bp.route('/alerts/pending', methods=['GET'])
@auth.login_required
def get_pending_alerts():
    """Get all pending alert broadcasts - AJAX endpoint"""
    try:
        # Get pending alerts
        alerts = alert_service.get_pending_alerts()

        # Create success response
        api_response = ApiResponse.success(
            value=[alert.to_dict() for alert in alerts],
            message=f"Found {len(alerts)} pending alert(s)"
        )

        return jsonify(api_response.to_dict()), api_response.get_status_code()

    except AppException as e:
        error_detail = ErrorDetail(
            title="Failed to Retrieve Pending Alerts",
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
# MAP DATA ENDPOINTS (for AJAX)
# =============================================================================

@analysis_bp.route('/<string:analysis_id>/map-data', methods=['GET'])
@auth.login_required
def get_analysis_map_data(analysis_id):
    """Get hotspot map data for a saved analysis - AJAX endpoint"""
    try:
        # Get query parameters for filters
        include_crime_hotspots = request.args.get('include_crime_hotspots', 'true', type=str).lower() == 'true'
        include_missing_person_hotspots = request.args.get('include_missing_person_hotspots', 'true',
                                                           type=str).lower() == 'true'
        min_risk_level = request.args.get('min_risk_level', None, type=str)

        # Create map data request
        map_request = GetMapDataRequest(
            analysis_id=analysis_id,
            include_crime_hotspots=include_crime_hotspots,
            include_missing_person_hotspots=include_missing_person_hotspots,
            min_risk_level=min_risk_level
        )

        # Get map data
        map_response = analysis_service.get_map_data(map_request)

        # Create success response
        api_response = ApiResponse.success(
            value=map_response.to_dict(),
            message=map_response.message
        )

        return jsonify(api_response.to_dict()), api_response.get_status_code()

    except AppException as e:
        error_detail = ErrorDetail(
            title="Failed to Retrieve Map Data",
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


@analysis_bp.route('/crime-map-data', methods=['GET'])
@auth.login_required
def get_crime_map_data():
    """Get individual crime locations for tactical map view - AJAX endpoint"""
    try:
        # Get query parameters
        start_date = request.args.get('start_date', type=str)
        end_date = request.args.get('end_date', type=str)
        crime_types = request.args.getlist('crime_types')
        limit = request.args.get('limit', 1000, type=int)

        if not start_date or not end_date:
            error_detail = ErrorDetail(
                title="Validation Error",
                details=["Start date and end date are required"],
                status=400
            )
            response = ApiResponse.failure(error=error_detail)
            return jsonify(response.to_dict()), response.get_status_code()

        # Create request
        crime_map_request = GetIndividualCrimeMapDataRequest(
            start_date=start_date,
            end_date=end_date,
            crime_types=crime_types if crime_types else None,
            limit=limit
        )

        # Get crime map data
        crime_map_response = analysis_service.get_individual_crime_map_data(crime_map_request)

        # Create success response
        api_response = ApiResponse.success(
            value=crime_map_response.to_dict(),
            message=crime_map_response.message
        )

        return jsonify(api_response.to_dict()), api_response.get_status_code()

    except AppException as e:
        error_detail = ErrorDetail(
            title="Failed to Retrieve Crime Map Data",
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