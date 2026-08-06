# src/modules/analysis/application/services/crime_analysis_service.py
import json
from typing import Type
from datetime import datetime
import logging
import inspect

from src.modules.crime_analysis.domain.models import AlertBroadcast
from src.modules.crime_analysis.domain.repositories.crime_analysis_repository import CrimeAnalysisRepository
from src.modules.crime_analysis.domain.repositories.crime_hotspot_repository import CrimeHotspotRepository
from src.modules.crime_analysis.domain.repositories.crime_trend_repository import CrimeTrendRepository
from src.modules.crime_analysis.domain.repositories.recommendation_repository import RecommendationRepository
from src.modules.crime_analysis.domain.services.alert_broadcast_service import AlertBroadcastService
from src.modules.crime_analysis.internal.llm_data_formatter import LLMDataFormatter
from src.modules.crime_analysis.internal.hotspot_detector import HotspotDetector, HotspotData
from src.modules.crime_analysis.presentation.dtos.analysis_dtos import *
from src.modules.crime_analysis.domain.models.crime_analysis import CrimeAnalysis
from src.modules.crime_analysis.domain.models.crime_hotspot import CrimeHotspot
from src.modules.crime_analysis.domain.models.crime_trend import CrimeTrend
from src.modules.crime_analysis.domain.models.recommendation import Recommendation
from src.modules.crime_analysis.domain.models.enums import (
    RiskLevel,
    TrendCategory,
    SeverityLevel,
    PriorityLevel
)
from src.modules.records.domain.models.location import Location
from src.modules.records.domain.repositories.crime_repository import CrimeRepository
from src.modules.records.domain.repositories.missing_person_repository import MissingPersonRepository
from src.modules.records.domain.repositories.location_repository import LocationRepository
from src.modules.records.domain.repositories.criminal_repository import CriminalRepository
from src.shared.configs.exceptions.exceptions import (
    NotFoundException,
    ValidationException,
    InternalServerException
)
from src.shared.utils.LLMClient import LLMClient

logger = logging.getLogger(__name__)


class CrimeAnalysisService:
    """Service for managing crime analysis, hotspots, trends, and recommendations."""

    def __init__(self):
        # Analysis repositories
        self.analysis_repos = {
            'analysis': CrimeAnalysisRepository(),
            'hotspot': CrimeHotspotRepository(),
            'trend': CrimeTrendRepository(),
            'recommendation': RecommendationRepository()
        }

        # Records repositories for data collection
        self.record_repos = {
            'crime': CrimeRepository(),
            'missing_person': MissingPersonRepository(),
            'location': LocationRepository(),
            'criminal': CriminalRepository()
        }

        # LLM Client
        self.llm_client = LLMClient()

    # ========================================================================
    # CRIME ANALYSIS GENERATION AND PREVIEW
    # ========================================================================

    def preview_crime_analysis(self, request: GenerateAnalysisReportRequest) -> AnalysisReportResponse:
        """
        Generate a crime analysis preview WITHOUT saving to database.
        Useful for reviewing LLM output before committing to permanent storage.
        Includes full location data for map visualization.

        Args:
            request: GenerateAnalysisReportRequest DTO

        Returns:
            AnalysisReportResponse DTO with analysis data (not saved, no IDs)

        Raises:
            InternalServerException: If preview generation fails
        """
        try:
            # Step 1: Collect crime and missing person data
            start_date = datetime.fromisoformat(request.start_date)
            end_date = datetime.fromisoformat(request.end_date)

            crimes = self.record_repos['crime'].find_by_date_range(start_date, end_date)
            missing_persons = self.record_repos['missing_person'].find_by_date_range(start_date, end_date)

            logger.info(f"Preview analysis: {len(crimes)} crimes, {len(missing_persons)} missing persons")

            # Step 2: Detect hotspots programmatically using DBSCAN clustering
            hotspot_detector = HotspotDetector(
                radius_km=request.radius_km,
                min_incidents=request.min_incidents
            )
            detected_hotspots = hotspot_detector.detect_hotspots(crimes, missing_persons)

            # Log hotspot detection statistics
            stats = hotspot_detector.get_cluster_statistics(detected_hotspots)
            logger.info(f"Hotspot detection stats: {stats}")

            # Step 3: Prepare data for LLM (with pre-calculated hotspots)
            formatter = LLMDataFormatter()
            formatted_prompt = formatter.prepare_analysis_prompt(
                crimes,
                missing_persons,
                detected_hotspots,
                start_date,
                end_date
            )

            # Step 4: Send to LLM for analysis (summary, trends, recommendations only)
            logger.info("Sending preview analysis request to LLM...")
            llm_response = self.llm_client.generate(formatted_prompt)
            logger.info("LLM preview analysis completed successfully")

            # Step 5: Build preview analysis object (no database save)
            preview_analysis = {
                'id': 'preview',
                'analysis_period_start': start_date.isoformat(),
                'analysis_period_end': end_date.isoformat(),
                'total_crimes': len(crimes),
                'total_missing_persons': len(missing_persons),
                'summary': llm_response.get('summary', 'No summary provided'),
                'generated_by': request.generated_by,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }

            # Step 6: Convert detected hotspots to preview format WITH FULL LOCATION DATA
            hotspots_data = []
            if request.include_hotspots:
                logger.info(f"Processing {len(detected_hotspots)} hotspots for preview")

                for idx, detected_hotspot in enumerate(detected_hotspots):
                    # Fetch location details for map visualization
                    location_data = None
                    if detected_hotspot.location_id:
                        location = self.record_repos['location'].find_by_id(detected_hotspot.location_id)
                        if location:
                            location_data = {
                                'id': location.id,
                                'latitude': float(location.latitude),
                                'longitude': float(location.longitude),
                                'address': location.address,
                                'city': location.city,
                                'state': location.state,
                                'country': location.country
                            }

                    # Create temporary CrimeHotspot for color calculation
                    temp_hotspot = CrimeHotspot(
                        location_id=detected_hotspot.location_id,
                        analysis_id='preview',
                        incident_count=detected_hotspot.incident_count,
                        crime_type=detected_hotspot.crime_type,
                        is_missing_person_hotspot=detected_hotspot.is_missing_person_hotspot,
                        risk_level=self._get_enum_by_value(RiskLevel, detected_hotspot.risk_level)
                    )

                    # Build hotspot dictionary
                    hotspot_dict = {
                        'id': f"preview-hotspot-{idx + 1}",
                        'location_id': detected_hotspot.location_id,
                        'analysis_id': 'preview',
                        'incident_count': detected_hotspot.incident_count,
                        'crime_type': detected_hotspot.crime_type,
                        'is_missing_person_hotspot': detected_hotspot.is_missing_person_hotspot,
                        'risk_level': detected_hotspot.risk_level,
                        'location': location_data,
                        'color': self._get_hotspot_color(temp_hotspot),
                        'created_at': datetime.now().isoformat(),
                        'updated_at': datetime.now().isoformat()
                    }
                    hotspots_data.append(hotspot_dict)

                logger.info(f"Preview hotspots processed: {len(hotspots_data)}")

            # Step 7: Process trends from LLM response
            trends_data = []
            if request.include_trends:
                for trend in llm_response.get('trends', []):
                    trend_dict = {
                        'id': f"preview-trend-{len(trends_data) + 1}",
                        'analysis_id': 'preview',
                        'hotspot_id': trend.get('hotspot_id'),
                        'trend_category': trend.get('trend_category', 'crime'),
                        'crime_type': trend.get('crime_type'),
                        'description': trend.get('description', ''),
                        'affected_demographic': trend.get('affected_demographic'),
                        'time_pattern': trend.get('time_pattern'),
                        'severity': trend.get('severity', 'low'),
                        'created_at': datetime.now().isoformat(),
                        'updated_at': datetime.now().isoformat()
                    }
                    trends_data.append(trend_dict)

            # Step 8: Process recommendations from LLM response
            recommendations_data = []
            if request.include_recommendations:
                for recommendation in llm_response.get('recommendations', []):
                    recommendation_dict = {
                        'id': f"preview-recommendation-{len(recommendations_data) + 1}",
                        'analysis_id': 'preview',
                        'hotspot_id': recommendation.get('hotspot_id'),
                        'recommendation_text': recommendation.get('recommendation_text', ''),
                        'priority': recommendation.get('priority', 'low'),
                        'created_at': datetime.now().isoformat(),
                        'updated_at': datetime.now().isoformat()
                    }
                    recommendations_data.append(recommendation_dict)

            # Step 9: Return preview response
            return AnalysisReportResponse(
                message="Crime analysis preview generated successfully (not saved to database)",
                analysis=preview_analysis,
                hotspots=hotspots_data,
                trends=trends_data,
                recommendations=recommendations_data
            )

        except Exception as e:
            logger.error(f"Failed to generate preview analysis: {str(e)}", exc_info=True)
            raise InternalServerException(f"Failed to generate preview analysis: {str(e)}")

    def generate_crime_analysis(self, request: GenerateAnalysisReportRequest) -> AnalysisReportResponse:
        """
        Generate a complete crime analysis report with hotspots, trends, and recommendations.
        Uses programmatic hotspot detection (DBSCAN) + LLM analysis.

        Args:
            request: GenerateAnalysisReportRequest DTO

        Returns:
            AnalysisReportResponse DTO with complete analysis

        Raises:
            ValidationException: If data collection or analysis fails
        """
        try:
            # Step 1: Collect crime and missing person data
            start_date = datetime.fromisoformat(request.start_date)
            end_date = datetime.fromisoformat(request.end_date)

            crimes = self.record_repos['crime'].find_by_date_range(start_date, end_date)
            missing_persons = self.record_repos['missing_person'].find_by_date_range(start_date, end_date)

            logger.info(f"Analysis generation: {len(crimes)} crimes, {len(missing_persons)} missing persons")

            # Step 2: Detect hotspots programmatically using DBSCAN clustering
            hotspot_detector = HotspotDetector(
                radius_km=request.radius_km,
                min_incidents=request.min_incidents
            )
            detected_hotspots = hotspot_detector.detect_hotspots(crimes, missing_persons)

            # Log hotspot detection statistics
            stats = hotspot_detector.get_cluster_statistics(detected_hotspots)
            logger.info(f"Hotspot detection stats: {stats}")

            # Step 3: Prepare data for LLM (with pre-calculated hotspots)
            formatter = LLMDataFormatter()
            formatted_prompt = formatter.prepare_analysis_prompt(
                crimes,
                missing_persons,
                detected_hotspots,
                start_date,
                end_date
            )

            # Step 4: Send to LLM for analysis (summary, trends, recommendations only)
            logger.info("Sending analysis request to LLM...")
            llm_response = self.llm_client.generate(formatted_prompt)
            logger.info("LLM analysis completed successfully")

            # Step 5: Create analysis record
            analysis = CrimeAnalysis(
                analysis_period_start=start_date,
                analysis_period_end=end_date,
                total_crimes=len(crimes),
                total_missing_persons=len(missing_persons),
                summary=llm_response.get('summary', 'No summary provided'),
                generated_by=request.generated_by
            )
            saved_analysis = self.analysis_repos['analysis'].create(analysis)

            # Step 6: Save programmatically detected hotspots to database
            hotspots = []
            if request.include_hotspots:
                hotspots = self._create_hotspots_from_detection(
                    saved_analysis.id,
                    detected_hotspots
                )
                logger.info(f"Saved {len(hotspots)} hotspots to database")

            # Step 7: Create trends from LLM response
            trends = []
            if request.include_trends:
                trends = self._create_entities_from_llm(
                    saved_analysis.id,
                    CrimeTrend,
                    llm_response.get('trends', []),
                    self.analysis_repos['trend'],
                    'trend'
                )

            # Step 8: Create recommendations from LLM response
            recommendations = []
            if request.include_recommendations:
                recommendations = self._create_entities_from_llm(
                    saved_analysis.id,
                    Recommendation,
                    llm_response.get('recommendations', []),
                    self.analysis_repos['recommendation'],
                    'recommendation'
                )

            # Step 9: Create alert broadcasts for critical hotspots
            alerts = []
            if request.include_hotspots and hotspots:
                alerts = self._create_alert_broadcasts_for_critical_hotspots(
                    saved_analysis.id,
                    hotspots
                )
                logger.info(f"Created {len(alerts)} alert broadcasts for critical hotspots")

            # Step 10: Build and return response
            return AnalysisReportResponse(
                message="Crime analysis generated successfully",
                analysis=self._build_response(saved_analysis, CrimeAnalysisResponse).to_dict(),
                hotspots=[self._build_response(h, CrimeHotspotResponse).to_dict() for h in hotspots],
                trends=[self._build_response(t, CrimeTrendResponse).to_dict() for t in trends],
                recommendations=[self._build_response(r, RecommendationResponse).to_dict() for r in recommendations]
            )

        except Exception as e:
            logger.error(f"Failed to generate crime analysis: {str(e)}", exc_info=True)
            raise InternalServerException(f"Failed to generate crime analysis: {str(e)}")

    def _create_hotspots_from_detection(
            self,
            analysis_id: str,
            detected_hotspots: List[HotspotData]
    ) -> List[CrimeHotspot]:
        """
        Create CrimeHotspot entities from programmatically detected hotspots.

        Args:
            analysis_id: Analysis ID
            detected_hotspots: List of HotspotData from hotspot detector

        Returns:
            List of saved CrimeHotspot entities
        """
        hotspots = []

        for hotspot_data in detected_hotspots:
            try:
                # Convert risk_level string to RiskLevel enum
                risk_level = self._get_enum_by_value(RiskLevel, hotspot_data.risk_level)

                # Create CrimeHotspot entity
                hotspot = CrimeHotspot(
                    location_id=hotspot_data.location_id,
                    analysis_id=analysis_id,
                    incident_count=hotspot_data.incident_count,
                    crime_type=hotspot_data.crime_type,
                    is_missing_person_hotspot=hotspot_data.is_missing_person_hotspot,
                    risk_level=risk_level
                )

                saved = self.analysis_repos['hotspot'].create(hotspot)
                hotspots.append(saved)

            except Exception as e:
                logger.warning(f"Failed to create hotspot from detection: {e}")
                continue

        logger.info(f"Created {len(hotspots)} hotspots from detection")
        return hotspots

    def _create_entities_from_llm(
            self,
            analysis_id: str,
            entity_class: Type,
            data_list: List[Dict[str, Any]],
            repository,
            entity_type: str
    ) -> List:
        """
        Generic entity creator from LLM data.

        Args:
            analysis_id: Analysis ID
            entity_class: Entity class to instantiate
            data_list: List of entity data dictionaries from LLM
            repository: Repository to use for creation
            entity_type: Type name for logging ('trend', 'recommendation')

        Returns:
            List of created entities
        """
        entities = []
        enum_map = {
            'severity': SeverityLevel,
            'priority': PriorityLevel,
            'trend_category': TrendCategory
        }

        for data in data_list:
            try:
                # Convert enum string values to enums
                for key, value in list(data.items()):
                    if key in enum_map and isinstance(value, str):
                        data[key] = self._get_enum_by_value(enum_map[key], value)

                # Add analysis_id
                data['analysis_id'] = analysis_id

                # Create entity
                entity = entity_class(**data)
                saved = repository.create(entity)
                entities.append(saved)

            except Exception as e:
                logger.warning(f"Failed to create {entity_type} from LLM data: {e}")
                continue

        logger.info(f"Created {len(entities)} {entity_type}(s) from LLM data")
        return entities

    # ========================================================================
    # GENERIC CRUD OPERATIONS
    # ========================================================================

    def create_crime_analysis(self, request: CreateCrimeAnalysisRequest) -> CrimeAnalysisResponse:
        """Create a new crime analysis record manually."""
        try:
            analysis = CrimeAnalysis(
                analysis_period_start=datetime.fromisoformat(request.analysis_period_start),
                analysis_period_end=datetime.fromisoformat(request.analysis_period_end),
                generated_by=request.generated_by
            )
            saved = self.analysis_repos['analysis'].create(analysis)
            return self._build_response(saved, CrimeAnalysisResponse)
        except Exception as e:
            raise ValidationException(f"Failed to create crime analysis: {str(e)}")

    def get_crime_analysis_by_id(self, analysis_id: str) -> CrimeAnalysisResponse:
        """Get crime analysis by ID."""
        analysis = self._verify_entity_exists(analysis_id, self.analysis_repos['analysis'], "Crime analysis")
        return self._build_response(analysis, CrimeAnalysisResponse)

    def list_crime_analyses(self, request: ListCrimeAnalysesRequest) -> ListCrimeAnalysesResponse:
        """List crime analyses with filters and pagination."""
        return self._list_entities(  # type: ignore[arg-type]
            self.analysis_repos['analysis'],
            request,
            CrimeAnalysisResponse,
            ListCrimeAnalysesResponse,
            'analysis',
            'analyses'
        )

    def delete_crime_analysis(self, analysis_id: str) -> DeleteResponse:
        """Soft delete a crime analysis."""
        return self._delete_entity(analysis_id, self.analysis_repos['analysis'], "Crime analysis")

    # ========================================================================
    # CRIME HOTSPOT MANAGEMENT
    # ========================================================================

    def create_crime_hotspot(self, request: CreateCrimeHotspotRequest) -> CrimeHotspotResponse:
        """Create a new crime hotspot."""
        # Verify dependencies
        self._verify_entity_exists(request.analysis_id, self.analysis_repos['analysis'], "Crime analysis")
        self._verify_entity_exists(request.location_id, self.record_repos['location'], "Location")

        try:
            hotspot = CrimeHotspot(
                location_id=request.location_id,
                analysis_id=request.analysis_id,
                incident_count=request.incident_count,
                crime_type=request.crime_type,
                is_missing_person_hotspot=request.is_missing_person_hotspot,
                risk_level=self._get_enum_by_value(RiskLevel, request.risk_level)
            )
            saved = self.analysis_repos['hotspot'].create(hotspot)
            return self._build_response(saved, CrimeHotspotResponse)
        except Exception as e:
            raise ValidationException(f"Failed to create crime hotspot: {str(e)}")

    def get_crime_hotspot_by_id(self, hotspot_id: str) -> CrimeHotspotResponse:
        """Get crime hotspot by ID."""
        hotspot = self._verify_entity_exists(hotspot_id, self.analysis_repos['hotspot'], "Crime hotspot")
        return self._build_response(hotspot, CrimeHotspotResponse)

    def list_crime_hotspots(self, request: ListCrimeHotspotsRequest) -> ListCrimeHotspotsResponse:
        """List crime hotspots with filters and pagination."""
        return self._list_entities(  # type: ignore[arg-type]
            self.analysis_repos['hotspot'],
            request,
            CrimeHotspotResponse,
            ListCrimeHotspotsResponse,
            'hotspot',
            'hotspots'
        )

    def get_high_risk_hotspots(self) -> List[CrimeHotspotResponse]:
        """Get all high and critical risk hotspots."""
        hotspots = self.analysis_repos['hotspot'].find_high_risk_hotspots()
        return [self._build_response(h, CrimeHotspotResponse) for h in hotspots]  # type: ignore[arg-type]

    def delete_crime_hotspot(self, hotspot_id: str) -> DeleteResponse:
        """Soft delete a crime hotspot."""
        return self._delete_entity(hotspot_id, self.analysis_repos['hotspot'], "Crime hotspot")

    # ========================================================================
    # CRIME TREND MANAGEMENT
    # ========================================================================

    def create_crime_trend(self, request: CreateCrimeTrendRequest) -> CrimeTrendResponse:
        """Create a new crime trend."""
        # Verify dependencies
        self._verify_entity_exists(request.analysis_id, self.analysis_repos['analysis'], "Crime analysis")
        if request.hotspot_id:
            self._verify_entity_exists(request.hotspot_id, self.analysis_repos['hotspot'], "Crime hotspot")

        try:
            trend = CrimeTrend(
                analysis_id=request.analysis_id,
                hotspot_id=request.hotspot_id,
                trend_category=self._get_enum_by_value(TrendCategory, request.trend_category),
                crime_type=request.crime_type,
                description=request.description,
                affected_demographic=request.affected_demographic,
                time_pattern=request.time_pattern,
                severity=self._get_enum_by_value(SeverityLevel, request.severity)
            )
            saved = self.analysis_repos['trend'].create(trend)
            return self._build_response(saved, CrimeTrendResponse)
        except Exception as e:
            raise ValidationException(f"Failed to create crime trend: {str(e)}")

    def get_crime_trend_by_id(self, trend_id: str) -> CrimeTrendResponse:
        """Get crime trend by ID."""
        trend = self._verify_entity_exists(trend_id, self.analysis_repos['trend'], "Crime trend")
        return self._build_response(trend, CrimeTrendResponse)

    def list_crime_trends(self, request: ListCrimeTrendsRequest) -> ListCrimeTrendsResponse:
        """List crime trends with filters and pagination."""
        return self._list_entities(  # type: ignore[arg-type]
            self.analysis_repos['trend'],
            request,
            CrimeTrendResponse,
            ListCrimeTrendsResponse,
            'trend',
            'trends'
        )

    def delete_crime_trend(self, trend_id: str) -> DeleteResponse:
        """Soft delete a crime trend."""
        return self._delete_entity(trend_id, self.analysis_repos['trend'], "Crime trend")

    # ========================================================================
    # RECOMMENDATION MANAGEMENT
    # ========================================================================

    def create_recommendation(self, request: CreateRecommendationRequest) -> RecommendationResponse:
        """Create a new recommendation."""
        # Verify dependencies
        self._verify_entity_exists(request.analysis_id, self.analysis_repos['analysis'], "Crime analysis")
        if request.hotspot_id:
            self._verify_entity_exists(request.hotspot_id, self.analysis_repos['hotspot'], "Crime hotspot")

        try:
            recommendation = Recommendation(
                analysis_id=request.analysis_id,
                hotspot_id=request.hotspot_id,
                recommendation_text=request.recommendation_text,
                priority=self._get_enum_by_value(PriorityLevel, request.priority)
            )
            saved = self.analysis_repos['recommendation'].create(recommendation)
            return self._build_response(saved, RecommendationResponse)
        except Exception as e:
            raise ValidationException(f"Failed to create recommendation: {str(e)}")

    def get_recommendation_by_id(self, recommendation_id: str) -> RecommendationResponse:
        """Get recommendation by ID."""
        rec = self._verify_entity_exists(recommendation_id, self.analysis_repos['recommendation'], "Recommendation")
        return self._build_response(rec, RecommendationResponse)

    def list_recommendations(self, request: ListRecommendationsRequest) -> ListRecommendationsResponse:
        """List recommendations with filters and pagination."""
        return self._list_entities(  # type: ignore[arg-type]
            self.analysis_repos['recommendation'],
            request,
            RecommendationResponse,
            ListRecommendationsResponse,
            'recommendation',
            'recommendations'
        )

    def get_urgent_recommendations(self) -> List[RecommendationResponse]:
        """Get all urgent recommendations."""
        recommendations = self.analysis_repos['recommendation'].find_urgent_recommendations()
        return [self._build_response(r, RecommendationResponse) for r in recommendations]  # type: ignore[arg-type]

    def delete_recommendation(self, recommendation_id: str) -> DeleteResponse:
        """Soft delete a recommendation."""
        return self._delete_entity(recommendation_id, self.analysis_repos['recommendation'], "Recommendation")

    # ========================================================================
    # ALERT BROADCASTS
    # ========================================================================

    def _create_alert_broadcasts_for_critical_hotspots(
            self,
            analysis_id: str,
            hotspots: List[CrimeHotspot]
    ) -> List[AlertBroadcast]:
        """Automatically create alert broadcasts for critical and high-risk hotspots."""
        alert_service = AlertBroadcastService()
        created_alerts = []

        for hotspot in hotspots:
            # Only create alerts for high and critical risk hotspots
            if hotspot.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]: # can add RiskLevel.MEDIUM
                try:
                    location = self.record_repos['location'].find_by_id(hotspot.location_id)
                    if not location:
                        continue

                    alert_message = self._generate_alert_message(hotspot, location)
                    alert_request = CreateAlertBroadcastRequest(
                        hotspot_id=hotspot.id,
                        message=alert_message
                    )

                    alert_response = alert_service.create_alert_broadcast(alert_request)
                    created_alerts.append(alert_response)
                    logger.info(f"Alert broadcast created for hotspot {hotspot.id}")

                except Exception as e:
                    logger.error(f"Failed to create alert for hotspot {hotspot.id}: {e}")
                    continue

        return created_alerts

    def _generate_alert_message(self, hotspot: CrimeHotspot, location: Location) -> str:
        """
        Generate alert message for a hotspot (without "POLICE ALERT" prefix).
        The prefix will be added by NotificationService's SMS_TEMPLATE.

        Args:
            hotspot: CrimeHotspot entity
            location: Location entity (from Location model)

        Returns:
            Alert message content (without POLICE ALERT prefix)
        """
        # Safely extract area name with fallbacks
        area = location.city or location.address or "your area"

        if hotspot.is_missing_person_hotspot:
            message = (
                f"High number of missing person cases reported in {area}. "
                f"{hotspot.incident_count} incidents recorded. "
                f"Residents are urged to be vigilant, report suspicious activities, "
                f"and ensure safety of vulnerable persons. Contact Police: (040)2717860"
            )
        else:
            crime_type = hotspot.crime_type or "criminal activity"
            message = (
                f"Increased {crime_type} incidents in {area}. "
                f"{hotspot.incident_count} cases reported. "
                f"Residents should take precautions, secure properties, and report "
                f"any suspicious behavior immediately. Contact Police: (040)2717860"
            )

        return message

    # ========================================================================
    # MAP VISUALIZATION - STRATEGIC LAYER (Hotspots)
    # ========================================================================

    def get_map_data(self, request: GetMapDataRequest) -> MapDataResponse:
        """
        Get strategic map visualization data (hotspots with aggregated data).
        This is the default view showing high-level overview for decision makers.

        Args:
            request: GetMapDataRequest DTO

        Returns:
            MapDataResponse with hotspot locations and risk-based coloring
        """
        analysis = self._verify_entity_exists(request.analysis_id, self.analysis_repos['analysis'], "Crime analysis")

        # Get hotspots with filters
        hotspots = self.analysis_repos['hotspot'].find_by_analysis(request.analysis_id)

        # Apply type filters
        if not request.include_crime_hotspots:
            hotspots = [h for h in hotspots if h.is_missing_person_hotspot]
        if not request.include_missing_person_hotspots:
            hotspots = [h for h in hotspots if not h.is_missing_person_hotspot]

        # Filter by minimum risk level
        if request.min_risk_level:
            min_risk = self._get_enum_by_value(RiskLevel, request.min_risk_level)
            risk_hierarchy = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 1, RiskLevel.HIGH: 2, RiskLevel.CRITICAL: 3}
            hotspots = [h for h in hotspots if risk_hierarchy.get(h.risk_level, 0) >= risk_hierarchy.get(min_risk, 0)]

        # Build hotspot data
        hotspot_data = []
        for hotspot in hotspots:
            location = self.record_repos['location'].find_by_id(hotspot.location_id)
            if location:
                hotspot_data.append({
                    'id': hotspot.id,
                    'latitude': float(location.latitude),
                    'longitude': float(location.longitude),
                    'address': location.address,
                    'city': location.city,
                    'incident_count': hotspot.incident_count,
                    'crime_type': hotspot.crime_type,
                    'is_missing_person_hotspot': hotspot.is_missing_person_hotspot,
                    'risk_level': hotspot.risk_level.value,
                    'color': self._get_hotspot_color(hotspot)
                })

        return MapDataResponse(
            message=f"Found {len(hotspot_data)} hotspot(s) for map visualization",
            hotspots=hotspot_data,
            analysis_period_start=analysis.analysis_period_start.isoformat(),
            analysis_period_end=analysis.analysis_period_end.isoformat()
        )

    def _get_hotspot_color(self, hotspot: CrimeHotspot) -> str:
        """Get color code for hotspot based on risk level and type."""
        # Color coding for crime hotspots
        color_map = {
            RiskLevel.LOW: '#4CAF50',  # Green
            RiskLevel.MEDIUM: '#FFC107',  # Amber
            RiskLevel.HIGH: '#FF5722',  # Deep Orange
            RiskLevel.CRITICAL: '#F44336'  # Red
        }

        # Different shade for missing person hotspots
        if hotspot.is_missing_person_hotspot:
            color_map = {
                RiskLevel.LOW: '#2196F3',  # Blue
                RiskLevel.MEDIUM: '#9C27B0',  # Purple
                RiskLevel.HIGH: '#E91E63',  # Pink
                RiskLevel.CRITICAL: '#880E4F'  # Dark Pink
            }

        return color_map.get(hotspot.risk_level, '#9E9E9E')  # Grey as default

    # ========================================================================
    # MAP VISUALIZATION - TACTICAL LAYER (Individual Crimes)
    # ========================================================================

    def get_individual_crime_map_data(
            self,
            request: GetIndividualCrimeMapDataRequest
    ) -> IndividualCrimeMapDataResponse:
        """
        Get tactical map visualization data (individual crime locations).
        """
        try:
            # Parse dates
            start_date = datetime.fromisoformat(request.start_date)
            end_date = datetime.fromisoformat(request.end_date)

            # Fetch crimes and missing persons from database
            crimes = self.record_repos['crime'].find_by_date_range(start_date, end_date)
            missing_persons = self.record_repos['missing_person'].find_by_date_range(start_date, end_date)

            # ✅ NEW: Get all unique crime types and generate color mapping
            unique_crime_types = set()
            for crime in crimes:
                if crime.crime_type:
                    unique_crime_types.add(crime.crime_type.lower().strip())

            # Generate color mapping for unique crime types
            crime_type_colors = self._generate_color_palette(list(unique_crime_types))

            # Always include missing person color
            crime_type_colors['missing_person'] = '#FF69B4'

            # Filter by crime type if specified
            if request.crime_types:
                crimes = [c for c in crimes if c.crime_type in request.crime_types]

            # Apply limit for performance
            total_incidents = len(crimes) + len(missing_persons)
            limited = False
            if request.limit and total_incidents > request.limit:
                crime_ratio = len(crimes) / total_incidents
                missing_ratio = len(missing_persons) / total_incidents
                crimes_limit = max(1, int(request.limit * crime_ratio))
                missing_limit = max(1, int(request.limit * missing_ratio))
                crimes = crimes[:crimes_limit]
                missing_persons = missing_persons[:missing_limit]
                limited = True

            # Build crime markers
            crime_markers = []
            for crime in crimes:
                if crime.location:
                    lat_valid = crime.location.latitude is not None
                    lng_valid = crime.location.longitude is not None

                    if lat_valid and lng_valid:
                        try:
                            normalized_type = crime.crime_type.lower().strip() if crime.crime_type else 'unknown'
                            marker_data = {
                                'id': crime.id,
                                'latitude': float(crime.location.latitude),
                                'longitude': float(crime.location.longitude),
                                'crime_type': crime.crime_type,
                                'date_committed': crime.date_committed.isoformat() if crime.date_committed else None,
                                'status': crime.status.value,
                                'severity': crime.severity.value if hasattr(crime, 'severity') else 'unknown',
                                'description': crime.description[:100] if crime.description else '',
                                'address': crime.location.address,
                                'city': crime.location.city,
                                'color': crime_type_colors.get(normalized_type, '#808080'),  # ✅ Use generated color
                                'type': 'crime'
                            }
                            crime_markers.append(marker_data)
                        except (ValueError, TypeError):
                            continue

            # Build missing person markers
            for mp in missing_persons:
                if mp.last_seen_location:
                    lat_valid = mp.last_seen_location.latitude is not None
                    lng_valid = mp.last_seen_location.longitude is not None

                    if lat_valid and lng_valid:
                        try:
                            first_name = getattr(mp, 'first_name', 'Unknown')
                            last_name = getattr(mp, 'last_name', '')
                            full_name = f"{first_name} {last_name}".strip()

                            marker_data = {
                                'id': mp.id,
                                'latitude': float(mp.last_seen_location.latitude),
                                'longitude': float(mp.last_seen_location.longitude),
                                'crime_type': 'missing_person',
                                'date_committed': mp.last_seen_date.isoformat() if mp.last_seen_date else None,
                                'status': mp.status.value,
                                'severity': 'high',
                                'description': f"Missing: {full_name}",
                                'address': mp.last_seen_location.address,
                                'city': mp.last_seen_location.city,
                                'color': crime_type_colors['missing_person'],  # ✅ Use generated color
                                'type': 'missing_person'
                            }
                            crime_markers.append(marker_data)
                        except (ValueError, TypeError):
                            continue

            crimes_count = len([m for m in crime_markers if m.get('type') == 'crime'])
            missing_count = len([m for m in crime_markers if m.get('type') == 'missing_person'])

            logger.info(f"Retrieved {len(crime_markers)} markers for tactical map view")

            return IndividualCrimeMapDataResponse(
                message=f'Found {len(crime_markers)} incident(s) for tactical map view',
                crimes=crime_markers,
                total=len(crime_markers),
                limited=limited,
                period_start=start_date.isoformat(),
                period_end=end_date.isoformat()
            )

        except Exception as e:
            logger.error(f"Failed to get individual crime map data: {str(e)}", exc_info=True)
            raise InternalServerException(f"Failed to get individual crime map data: {str(e)}")

    def _generate_color_palette(self, crime_types: List[str]) -> Dict[str, str]:
        """
        Generate a color palette for unique crime types.
        Each crime type gets a distinct color.

        Args:
            crime_types: List of unique crime types (already normalized to lowercase)

        Returns:
            Dictionary mapping crime type to hex color
        """
        # Predefined color palette (vibrant, distinguishable colors)
        color_palette = [
            '#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#FF00FF', '#00FFFF',
            '#FF8C00', '#8B0000', '#006400', '#00008B', '#FFD700', '#8B008B',
            '#DC143C', '#00CED1', '#FF1493', '#1E90FF', '#32CD32', '#FF4500',
            '#9370DB', '#00FA9A', '#FF6347', '#4169E1', '#ADFF2F', '#FF69B4',
            '#87CEEB', '#FFA500', '#BA55D3', '#20B2AA', '#F08080', '#7B68EE',
            '#98FB98', '#DDA0DD', '#B0E0E6', '#FFDAB9', '#EE82EE', '#F0E68C',
            '#E6E6FA', '#FFF0F5', '#FAEBD7', '#FFE4E1'
        ]

        if not crime_types:
            return {}

        # Sort crime types for consistency
        sorted_types = sorted(crime_types)

        # Map each crime type to a color
        color_mapping = {}
        for i, crime_type in enumerate(sorted_types):
            # Use modulo to cycle through colors if we have more crime types than colors
            color_mapping[crime_type] = color_palette[i % len(color_palette)]

        return color_mapping

    # ========================================================================
    # GENERIC HELPER METHODS
    # ========================================================================

    def _verify_entity_exists(self, entity_id: str, repository, entity_name: str):
        """Generic existence validator."""
        entity = repository.find_by_id(entity_id)
        if not entity:
            raise NotFoundException(f"{entity_name} with ID {entity_id} not found")
        return entity

    def _delete_entity(self, entity_id: str, repository, entity_name: str) -> DeleteResponse:
        """Generic delete handler."""
        entity = self._verify_entity_exists(entity_id, repository, entity_name)
        repository.delete(entity)
        return DeleteResponse(
            message=f"{entity_name} deleted successfully",
            id=entity_id
        )

    def _list_entities(self, repository, request, response_class: Type,
                       list_response_class: Type, entity_name: str, plural_name: str):
        """Generic list handler with filters and pagination."""
        # Apply filters
        entities = self._apply_filters(repository, request)

        # Pagination
        total = len(entities)
        start = (request.page - 1) * request.per_page
        end = start + request.per_page
        paginated = entities[start:end]

        # Build responses
        entity_dicts = [
            self._build_response(entity, response_class).to_dict()
            for entity in paginated
        ]

        return list_response_class(
            message=f"Found {total} {entity_name}(s)",
            **{plural_name: entity_dicts},
            total=total,
            page=request.page,
            per_page=request.per_page,
            total_pages=(total + request.per_page - 1) // request.per_page
        )

    def _apply_filters(self, repository, request):
        """Apply filters dynamically based on request attributes."""
        # Check for specific filters in order of priority
        # Only check attributes that actually exist on the request object

        if hasattr(request, 'generated_by') and getattr(request, 'generated_by', None):
            return repository.find_by_generated_by(request.generated_by)

        if (hasattr(request, 'start_date') and hasattr(request, 'end_date') and
                getattr(request, 'start_date', None) and getattr(request, 'end_date', None)):
            start = datetime.fromisoformat(request.start_date)
            end = datetime.fromisoformat(request.end_date)
            return repository.find_by_date_range(start, end)

        if hasattr(request, 'analysis_id') and getattr(request, 'analysis_id', None):
            return repository.find_by_analysis(request.analysis_id)

        if hasattr(request, 'hotspot_id') and getattr(request, 'hotspot_id', None):
            return repository.find_by_hotspot(request.hotspot_id)

        if hasattr(request, 'location_id') and getattr(request, 'location_id', None):
            return repository.find_by_location(request.location_id)

        if hasattr(request, 'risk_level') and getattr(request, 'risk_level', None):
            risk_level = self._get_enum_by_value(RiskLevel, request.risk_level)
            return repository.find_by_risk_level(risk_level)

        if hasattr(request, 'crime_type') and getattr(request, 'crime_type', None):
            return repository.find_by_crime_type(request.crime_type)

        if hasattr(request, 'is_missing_person_hotspot') and getattr(request, 'is_missing_person_hotspot',
                                                                     None) is not None:
            is_missing = getattr(request, 'is_missing_person_hotspot')
            if is_missing:
                return repository.find_missing_person_hotspots()
            else:
                return repository.find_crime_hotspots()

        if hasattr(request, 'trend_category') and getattr(request, 'trend_category', None):
            category = self._get_enum_by_value(TrendCategory, request.trend_category)
            return repository.find_by_category(category)

        if hasattr(request, 'severity') and getattr(request, 'severity', None):
            severity = self._get_enum_by_value(SeverityLevel, request.severity)
            return repository.find_by_severity(severity)

        if hasattr(request, 'priority') and getattr(request, 'priority', None):
            priority = self._get_enum_by_value(PriorityLevel, request.priority)
            return repository.find_by_priority(priority)

        if hasattr(request, 'status') and getattr(request, 'status', None):
            from src.modules.crime_analysis.domain.models.enums import BroadcastStatus
            status = self._get_enum_by_value(BroadcastStatus, request.status)
            return repository.find_by_status(status)

        # Default: return all non-deleted records
        return repository.find_all(include_deleted=getattr(request, 'include_deleted', False))

    def _build_response(self, entity, response_class: Type):
        """Generic response builder for all entities."""
        # Get expected fields for the response class FIRST
        response_fields = set(inspect.signature(response_class.__init__).parameters.keys()) - {'self'}

        # Base fields common to all entities
        data = {
            'id': entity.id,
            'created_at': entity.created_at.isoformat(),
            'updated_at': entity.updated_at.isoformat()
        }

        # Add datetime fields (only if BOTH entity has them AND response expects them)
        if 'analysis_period_start' in response_fields:
            if hasattr(entity, 'analysis_period_start') and entity.analysis_period_start:
                data['analysis_period_start'] = entity.analysis_period_start.isoformat()

        if 'analysis_period_end' in response_fields:
            if hasattr(entity, 'analysis_period_end') and entity.analysis_period_end:
                data['analysis_period_end'] = entity.analysis_period_end.isoformat()

        # Add enum fields (only if both entity has them AND response expects them)
        enum_fields = ['risk_level', 'severity', 'priority', 'status', 'trend_category']
        for field in enum_fields:
            if field in response_fields and hasattr(entity, field):
                enum_value = getattr(entity, field)
                data[field] = enum_value.value if enum_value else None

        # Add scalar fields (only if BOTH entity has them AND response expects them)
        scalar_fields = [
            'location_id', 'analysis_id', 'hotspot_id', 'incident_count', 'crime_type',
            'is_missing_person_hotspot', 'description', 'affected_demographic', 'time_pattern',
            'recommendation_text', 'total_crimes', 'total_missing_persons', 'summary',
            'generated_by', 'message', 'sent_at', 'recipient_count'
        ]

        for field in scalar_fields:
            if field in response_fields and hasattr(entity, field):
                value = getattr(entity, field)
                if isinstance(value, datetime):
                    data[field] = value.isoformat() if value else None
                else:
                    data[field] = value

        # Add location data ONLY for CrimeHotspotResponse
        if response_class == CrimeHotspotResponse and 'location' in response_fields:
            if hasattr(entity, 'location_id') and entity.location_id:
                location = self.record_repos['location'].find_by_id(entity.location_id)
                if location:
                    data['location'] = {
                        'id': location.id,
                        'latitude': float(location.latitude),
                        'longitude': float(location.longitude),
                        'address': location.address,
                        'city': location.city,
                        'state': location.state,
                        'country': location.country
                    }
                else:
                    data['location'] = None
            else:
                data['location'] = None

            # ✅ ADD COLOR FOR HOTSPOTS
            if 'color' in response_fields:
                data['color'] = self._get_hotspot_color(entity)

        return response_class(**data)

    @staticmethod
    def _get_enum_by_value(enum_class, value: str):
        """Get enum member by its value (case-insensitive)."""
        if not value:
            raise ValidationException(f"Value cannot be empty for {enum_class.__name__}")

        value_lower = value.lower().strip()
        for member in enum_class:
            if member.value.lower() == value_lower:
                return member

        valid_values = [member.value for member in enum_class]
        raise ValidationException(
            f"Invalid {enum_class.__name__} value: '{value}'. "
            f"Valid options are: {', '.join(valid_values)}"
        )