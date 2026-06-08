from src.modules.records.domain.models.enums import PunishmentType, PunishmentStatus
from src.shared.data.base.model import BaseModel
from src.shared.data.database import db


class Punishment(BaseModel):
    """Model for punishments associated with crimes"""
    __tablename__ = 'punishments'

    type = db.Column(db.Enum(PunishmentType), nullable=False, index=True)
    status = db.Column(db.Enum(PunishmentStatus), nullable=False, index=True)
    start_date = db.Column(db.DateTime, nullable=True, index=True)
    end_date = db.Column(db.DateTime, nullable=True, index=True)

    # For fines
    amount = db.Column(db.Numeric(10, 2), nullable=True)
    amount_paid = db.Column(db.Numeric(10, 2), default=0)

    # For jail or community service
    duration = db.Column(db.Integer, nullable=True)  # In days
    location_id = db.Column(db.String(36), db.ForeignKey('locations.id'), nullable=True)
    location = db.relationship('Location')

    details = db.Column(db.Text, nullable=True)

    # Foreign key
    crime_id = db.Column(db.String(36), db.ForeignKey('crimes.id'), nullable=False, index=True)

    # Relationships
    crime = db.relationship('Crime', back_populates='punishments')

    # Track who assigned this punishment
    assigned_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    assigned_by_user = db.relationship('User', foreign_keys=[assigned_by])

    __table_args__ = (
        db.Index('idx_punishment_status_type', 'status', 'type'),
    )
