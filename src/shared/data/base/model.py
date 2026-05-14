import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from src.shared.data.database import db


class BaseModel(db.Model):
    """
    Abstract base model for all database models.
    Provides common fields and utility methods.
    """
    __abstract__ = True

    # Primary key as UUID string
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now())
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now(), onupdate=datetime.now)

    # Soft delete flag
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)

    def to_dict(self, exclude: Optional[list] = None) -> Dict[str, Any]:
        """
        Convert model instance to dictionary.

        Args:
            exclude: List of column names to exclude from the result

        Returns:
            Dictionary representation of the model
        """
        exclude = exclude or []
        result = {}

        for column in self.__table__.columns:
            if column.name not in exclude and not column.name.startswith('_'):
                value = getattr(self, column.name)

                # Handle datetime serialization
                if isinstance(value, datetime):
                    value = value.isoformat()

                result[column.name] = value

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseModel':
        """
        Create model instance from dictionary.
        Filters out invalid attributes and protected fields.

        Args:
            data: Dictionary of data to create instance from

        Returns:
            New instance of the model
        """
        filtered_data = {
            k: v for k, v in data.items()
            if hasattr(cls, k) and not k.startswith('_')
        }
        return cls(**filtered_data)

    def __repr__(self) -> str:
        """String representation of the model."""
        return f"<{self.__class__.__name__}(id={self.id})>"