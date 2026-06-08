from sqlalchemy import func

from src.shared.data.base.model import BaseModel
from src.shared.data.database import db
from pgvector.sqlalchemy import Vector

class PersonImage(BaseModel):
    """Model for storing images with facial recognition vectors"""
    __tablename__ = 'person_images'

    image_path = db.Column(db.String(255), nullable=False)
    image_vector = db.Column(Vector(512), nullable=True)  # 512-dimensional vector

    is_primary = db.Column(db.Boolean, default=False, index=True)
    capture_date = db.Column(db.DateTime, server_default=func.now())
    quality_score = db.Column(db.Float, nullable=True)  # Image quality for recognition

    person_id = db.Column(db.String(36), db.ForeignKey('persons.id'), nullable=False, index=True)
    person = db.relationship('Person', back_populates='images')

    # Track who uploaded this image
    uploaded_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)

    __table_args__ = (
        db.Index('idx_person_primary_image', 'person_id', 'is_primary'),
    )