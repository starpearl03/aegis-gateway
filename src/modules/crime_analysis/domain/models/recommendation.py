# src/modules/analysis/domain/models/recommendation.py
from src.modules.crime_analysis.domain.models.enums import PriorityLevel
from src.shared.data.base.model import BaseModel
from src.shared.data.database import db


class Recommendation(BaseModel):
    """Model for crime analysis recommendations"""
    __tablename__ = 'recommendations'

    analysis_id = db.Column(db.String(36), db.ForeignKey('crime_analyses.id'),
                            nullable=False, index=True)
    hotspot_id = db.Column(db.String(36), db.ForeignKey('crime_hotspots.id'),
                           nullable=True, index=True)

    recommendation_text = db.Column(db.Text, nullable=False)
    priority = db.Column(db.Enum(PriorityLevel), nullable=False, index=True)

    # Relationships
    analysis = db.relationship('CrimeAnalysis', back_populates='recommendations')
    hotspot = db.relationship('CrimeHotspot', back_populates='recommendations')

    __table_args__ = (
        db.Index('idx_recommendation_priority', 'priority'),
    )