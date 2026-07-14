# src/modules/analysis/data/repositories/crime_hotspot_repository.py
from typing import List

from src.modules.crime_analysis.domain.models.crime_hotspot import CrimeHotspot
from src.modules.crime_analysis.domain.models.enums import RiskLevel
from src.shared.data.base.repository import BaseRepository


class CrimeHotspotRepository(BaseRepository[CrimeHotspot]):
    """Repository for CrimeHotspot model"""

    def __init__(self):
        super().__init__(CrimeHotspot)

    def find_by_analysis(self, analysis_id: str) -> List[CrimeHotspot]:
        """Find all hotspots for a specific analysis"""
        return self.find_many_by({"analysis_id": analysis_id})

    def find_by_location(self, location_id: str) -> List[CrimeHotspot]:
        """Find all hotspots at a specific location"""
        return self.find_many_by({"location_id": location_id})

    def find_by_risk_level(self, risk_level: RiskLevel) -> List[CrimeHotspot]:
        """Find all hotspots with a specific risk level"""
        return self.find_many_by({"risk_level": risk_level})

    def find_high_risk_hotspots(self) -> List[CrimeHotspot]:
        """Find all high and critical risk hotspots"""
        return self.model.query.filter(
            self.model.is_deleted == False,
            self.model.risk_level.in_([RiskLevel.HIGH, RiskLevel.CRITICAL])
        ).all()

    def find_by_crime_type(self, crime_type: str) -> List[CrimeHotspot]:
        """Find all hotspots for a specific crime type"""
        return self.find_many_by({"crime_type": crime_type})

    def find_missing_person_hotspots(self) -> List[CrimeHotspot]:
        """Find all hotspots related to missing persons"""
        return self.find_many_by({"is_missing_person_hotspot": True})

    def find_crime_hotspots(self) -> List[CrimeHotspot]:
        """Find all hotspots related to crimes (not missing persons)"""
        return self.find_many_by({"is_missing_person_hotspot": False})

    def find_by_location_and_analysis(self, location_id: str, analysis_id: str) -> List[CrimeHotspot]:
        """Find hotspots for a specific location in a specific analysis"""
        return self.find_many_by({
            "location_id": location_id,
            "analysis_id": analysis_id
        })