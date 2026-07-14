# src/modules/analysis/domain/models/crime_trend.py
from src.modules.crime_analysis.domain.models.enums import TrendCategory, SeverityLevel
from src.shared.data.base.model import BaseModel
from src.shared.data.database import db


class CrimeTrend(BaseModel):
    """Model for identified crime trends"""
    __tablename__ = 'crime_trends'

    analysis_id = db.Column(db.String(36), db.ForeignKey('crime_analyses.id'),
                            nullable=False, index=True)
    hotspot_id = db.Column(db.String(36), db.ForeignKey('crime_hotspots.id'),
                           nullable=True, index=True)

    trend_category = db.Column(db.Enum(TrendCategory), nullable=False, index=True)
    crime_type = db.Column(db.String(100), nullable=True, index=True)
    description = db.Column(db.Text, nullable=False)
    affected_demographic = db.Column(db.String(255), nullable=True)
    time_pattern = db.Column(db.String(255), nullable=True)
    severity = db.Column(db.Enum(SeverityLevel), nullable=False, index=True)

    # Relationships
    analysis = db.relationship('CrimeAnalysis', back_populates='trends')
    hotspot = db.relationship('CrimeHotspot', back_populates='trends')

    __table_args__ = (
        db.Index('idx_trend_category_severity', 'trend_category', 'severity'),
    )