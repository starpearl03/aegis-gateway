# src/modules/analysis/domain/models/alert_broadcast.py
from src.modules.crime_analysis.domain.models.enums import BroadcastStatus
from src.shared.data.base.model import BaseModel
from src.shared.data.database import db


class AlertBroadcast(BaseModel):
    """Model for SMS alert broadcasts to locals"""
    __tablename__ = 'alert_broadcasts'

    hotspot_id = db.Column(db.String(36), db.ForeignKey('crime_hotspots.id'),
                           nullable=False, index=True)

    message = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, nullable=True, index=True)
    recipient_count = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.Enum(BroadcastStatus), nullable=False,
                       default=BroadcastStatus.PENDING, index=True)

    # Relationships
    hotspot = db.relationship('CrimeHotspot', back_populates='alerts')

    __table_args__ = (
        db.Index('idx_alert_status_sent', 'status', 'sent_at'),
    )