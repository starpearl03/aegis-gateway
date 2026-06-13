# src/config/sql_alchemy.py
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, cast
from sqlalchemy.types import UserDefinedType


class Vector(UserDefinedType):
    def __init__(self, dim):
        self.dim = dim

    def get_col_spec(self, **kw):
        return f"vector({self.dim})"

    def bind_processor(self, dialect):
        def process(value):
            if value is None:
                return None
            # Convert Python list to PostgreSQL array
            return value if isinstance(value, list) else value.tolist()

        return process

    def result_processor(self, dialect, coltype):
        def process(value):
            return value

        return process

    # This is critical for adapter compatibility
    def __str__(self):
        return f"vector({self.dim})"

    # Add SQL Alchemy comparison methods
    def bind_expression(self, bindvalue):
        return cast(bindvalue, self)


# Add cosine similarity function
def cosine_similarity(vector1, vector2):
    """
    Calculate cosine similarity between two vectors

    Args:
        vector1: First vector (db.Vector)
        vector2: Second vector (db.Vector)

    Returns:
        Similarity score (0-1, higher means more similar)
    """
    return func.cosine_similarity(vector1, vector2)

# Initialize SQLAlchemy
db = SQLAlchemy()

# Add vector type to SQLAlchemy
db.Vector = Vector

# Add to SQLAlchemy
db.cosine_similarity = cosine_similarity