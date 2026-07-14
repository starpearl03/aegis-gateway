# src/modules/analysis/data/repositories/crime_trend_repository.py
from typing import List

from src.modules.crime_analysis.domain.models.crime_trend import CrimeTrend
from src.modules.crime_analysis.domain.models.enums import TrendCategory, SeverityLevel
from src.shared.data.base.repository import BaseRepository


class CrimeTrendRepository(BaseRepository[CrimeTrend]):
    """Repository for CrimeTrend model"""

    def __init__(self):
        super().__init__(CrimeTrend)

    def find_by_analysis(self, analysis_id: str) -> List[CrimeTrend]:
        """Find all trends for a specific analysis"""
        return self.find_many_by({"analysis_id": analysis_id})

    def find_by_hotspot(self, hotspot_id: str) -> List[CrimeTrend]:
        """Find all trends for a specific hotspot"""
        return self.find_many_by({"hotspot_id": hotspot_id})

    def find_by_category(self, category: TrendCategory) -> List[CrimeTrend]:
        """Find all trends by category"""
        return self.find_many_by({"trend_category": category})

    def find_by_severity(self, severity: SeverityLevel) -> List[CrimeTrend]:
        """Find all trends by severity level"""
        return self.find_many_by({"severity": severity})

    def find_high_severity_trends(self) -> List[CrimeTrend]:
        """Find all high severity trends"""
        return self.find_many_by({"severity": SeverityLevel.HIGH})

    def find_by_crime_type(self, crime_type: str) -> List[CrimeTrend]:
        """Find all trends for a specific crime type"""
        return self.find_many_by({"crime_type": crime_type})

    def find_crime_trends(self) -> List[CrimeTrend]:
        """Find all trends related to crimes"""
        return self.find_many_by({"trend_category": TrendCategory.CRIME})

    def find_missing_person_trends(self) -> List[CrimeTrend]:
        """Find all trends related to missing persons"""
        return self.find_many_by({"trend_category": TrendCategory.MISSING_PERSON})