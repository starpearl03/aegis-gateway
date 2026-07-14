# src/modules/analysis/data/repositories/recommendation_repository.py
from typing import List

from src.modules.crime_analysis.domain.models.recommendation import Recommendation
from src.modules.crime_analysis.domain.models.enums import PriorityLevel
from src.shared.data.base.repository import BaseRepository


class RecommendationRepository(BaseRepository[Recommendation]):
    """Repository for Recommendation model"""

    def __init__(self):
        super().__init__(Recommendation)

    def find_by_analysis(self, analysis_id: str) -> List[Recommendation]:
        """Find all recommendations for a specific analysis"""
        return self.find_many_by({"analysis_id": analysis_id})

    def find_by_hotspot(self, hotspot_id: str) -> List[Recommendation]:
        """Find all recommendations for a specific hotspot"""
        return self.find_many_by({"hotspot_id": hotspot_id})

    def find_by_priority(self, priority: PriorityLevel) -> List[Recommendation]:
        """Find all recommendations by priority level"""
        return self.find_many_by({"priority": priority})

    def find_urgent_recommendations(self) -> List[Recommendation]:
        """Find all urgent recommendations"""
        return self.find_many_by({"priority": PriorityLevel.URGENT})

    def find_high_priority_recommendations(self) -> List[Recommendation]:
        """Find all high and urgent priority recommendations"""
        return self.model.query.filter(
            self.model.is_deleted == False,
            self.model.priority.in_([PriorityLevel.HIGH, PriorityLevel.URGENT])
        ).all()

    def find_general_recommendations(self, analysis_id: str) -> List[Recommendation]:
        """Find general recommendations (not tied to specific hotspot)"""
        return self.model.query.filter(
            self.model.is_deleted == False,
            self.model.analysis_id == analysis_id,
            self.model.hotspot_id.is_(None)
        ).all()