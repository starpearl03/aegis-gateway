from src.modules.identification.domain.models.enums import SearchType, FileType, SearchStatus
from src.shared.data.base.model import BaseModel
from src.shared.data.database import db


class IdentificationSearch(BaseModel):
    """Model for identification search requests"""
    __tablename__ = 'identification_searches'

    search_type = db.Column(db.Enum(SearchType), nullable=False, index=True)
    file_path = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.Enum(FileType), nullable=False)
    status = db.Column(db.Enum(SearchStatus), default=SearchStatus.PENDING,
                       nullable=False, index=True)

    # Relationships
    results = db.relationship('IdentificationResult', back_populates='search',
                             lazy='dynamic', cascade="all, delete-orphan")

    __table_args__ = (
        db.Index('idx_search_status_type', 'status', 'search_type'),
        db.Index('idx_search_created', 'created_at'),
    )

    def __repr__(self) -> str:
        return f"<IdentificationSearch(id={self.id}, type={self.search_type.value}, status={self.status.value})>"
