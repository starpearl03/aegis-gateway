# src/modules/analysis/domain/models/crime_hotspot.py
from src.modules.crime_analysis.domain.models.enums import RiskLevel
from src.shared.data.base.model import BaseModel
from src.shared.data.database import db


class CrimeHotspot(BaseModel):
    """Model for crime hotspots identified in analysis"""
    __tablename__ = 'crime_hotspots'

    location_id = db.Column(db.String(36), db.ForeignKey('locations.id'),
                            nullable=False, index=True)
    analysis_id = db.Column(db.String(36), db.ForeignKey('crime_analyses.id'),
                            nullable=False, index=True)

    incident_count = db.Column(db.Integer, nullable=False, default=0)
    crime_type = db.Column(db.String(100), nullable=True, index=True)
    is_missing_person_hotspot = db.Column(db.Boolean, nullable=False,
                                          default=False, index=True)
    risk_level = db.Column(db.Enum(RiskLevel), nullable=False, index=True)

    # Relationships
    location = db.relationship('Location', foreign_keys=[location_id])
    analysis = db.relationship('CrimeAnalysis', back_populates='hotspots')
    trends = db.relationship('CrimeTrend', back_populates='hotspot',
                             cascade='all, delete-orphan')
    recommendations = db.relationship('Recommendation', back_populates='hotspot',
                                      cascade='all, delete-orphan')
    alerts = db.relationship('AlertBroadcast', back_populates='hotspot',
                             cascade='all, delete-orphan')

    __table_args__ = (
        db.Index('idx_hotspot_risk_type', 'risk_level', 'crime_type'),
        db.Index('idx_hotspot_location_analysis', 'location_id', 'analysis_id'),
    )