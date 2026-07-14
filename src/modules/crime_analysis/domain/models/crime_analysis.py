# src/modules/analysis/domain/models/crime_analysis.py
from src.shared.data.base.model import BaseModel
from src.shared.data.database import db


class CrimeAnalysis(BaseModel):
    """Model for crime analysis reports"""
    __tablename__ = 'crime_analyses'

    analysis_period_start = db.Column(db.DateTime, nullable=False, index=True)
    analysis_period_end = db.Column(db.DateTime, nullable=False, index=True)
    total_crimes = db.Column(db.Integer, nullable=False, default=0)
    total_missing_persons = db.Column(db.Integer, nullable=False, default=0)
    summary = db.Column(db.Text, nullable=False)

    # Track who generated this analysis
    generated_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    generated_by_user = db.relationship('User', foreign_keys=[generated_by])

    # Relationships
    hotspots = db.relationship('CrimeHotspot', back_populates='analysis',
                               cascade='all, delete-orphan')
    trends = db.relationship('CrimeTrend', back_populates='analysis',
                            cascade='all, delete-orphan')
    recommendations = db.relationship('Recommendation', back_populates='analysis',
                                     cascade='all, delete-orphan')

    __table_args__ = (
        db.Index('idx_analysis_period', 'analysis_period_start', 'analysis_period_end'),
    )