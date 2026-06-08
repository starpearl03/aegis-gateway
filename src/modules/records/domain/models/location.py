from src.shared.data.base.model import BaseModel
from src.shared.data.database import db


class Location(BaseModel):
    """Reusable location model with GPS coordinates"""
    __tablename__ = 'locations'

    latitude = db.Column(db.Numeric(10, 8), nullable=False)  # -90 to 90
    longitude = db.Column(db.Numeric(11, 8), nullable=False)  # -180 to 180
    address = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(100), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    postal_code = db.Column(db.String(20), nullable=True)
    description = db.Column(db.Text, nullable=True)  # e.g., "Near the old church"

    # Track who created/modified this location
    created_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    updated_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)

    __table_args__ = (
        db.Index('idx_location_coordinates', 'latitude', 'longitude'),
    )