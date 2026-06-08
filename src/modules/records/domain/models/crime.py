from sqlalchemy import func

from src.modules.records.domain.models.enums import CrimeStatus
from src.shared.data.base.model import BaseModel
from src.shared.data.database import db


class Crime(BaseModel):
    """Model for crimes"""
    __tablename__ = 'crimes'

    case_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    crime_type = db.Column(db.String(100), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    date_committed = db.Column(db.DateTime, nullable=False, index=True)
    date_reported = db.Column(db.DateTime, server_default=func.now())
    status = db.Column(db.Enum(CrimeStatus), default=CrimeStatus.OPEN,
                       nullable=False, index=True)

    # Location relationship
    location_id = db.Column(db.String(36), db.ForeignKey('locations.id'), nullable=False)
    location = db.relationship('Location')

    # Criminal relationship
    criminal_id = db.Column(db.String(36), db.ForeignKey('criminals.id'),
                            nullable=False, index=True)
    criminal = db.relationship('Criminal', back_populates='crimes')

    # Track investigating officer
    assigned_officer_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    assigned_officer = db.relationship('User', foreign_keys=[assigned_officer_id])

    # Track who reported/created this crime record
    reported_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    reported_by_user = db.relationship('User', foreign_keys=[reported_by])

    # Relationships
    victims = db.relationship('CrimeVictim', back_populates='crime', cascade="all, delete-orphan")
    punishments = db.relationship('Punishment', back_populates='crime', lazy='dynamic',
                                  cascade="all, delete-orphan")
    evidence = db.relationship('Evidence', back_populates='crime', lazy='dynamic',
                               cascade="all, delete-orphan")

    __table_args__ = (
        db.Index('idx_crime_status_date', 'status', 'date_committed'),
        db.Index('idx_crime_type_date', 'crime_type', 'date_committed'),
    )