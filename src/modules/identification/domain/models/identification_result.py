from src.modules.identification.domain.models.enums import PersonType
from src.shared.data.base.model import BaseModel
from src.shared.data.database import db


class IdentificationResult(BaseModel):
    """Model for identification search results - one record per matched image"""
    __tablename__ = 'identification_results'

    search_id = db.Column(db.String(36), db.ForeignKey('identification_searches.id'),
                         nullable=False, index=True)
    person_id = db.Column(db.String(36), db.ForeignKey('persons.id'), nullable=True, index=True)
    person_type = db.Column(db.Enum(PersonType), nullable=True)
    similarity_score = db.Column(db.Float, nullable=False)
    is_match = db.Column(db.Boolean, default=False, nullable=False, index=True)
    matched_image_id = db.Column(db.String(36), db.ForeignKey('person_images.id'), nullable=True)

    # Relationships
    search = db.relationship('IdentificationSearch', back_populates='results')
    person = db.relationship('Person', foreign_keys=[person_id])
    matched_image = db.relationship('PersonImage', foreign_keys=[matched_image_id])

    __table_args__ = (
        db.Index('idx_result_search_match', 'search_id', 'is_match'),
        db.Index('idx_result_person', 'person_id', 'person_type'),
        db.Index('idx_result_score', 'similarity_score'),
    )

    def __repr__(self) -> str:
        return f"<IdentificationResult(id={self.id}, person_id={self.person_id}, score={self.similarity_score:.3f}, match={self.is_match})>"
