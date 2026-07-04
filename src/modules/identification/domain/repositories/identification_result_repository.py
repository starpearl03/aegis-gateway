from typing import List, Optional

from src.modules.identification.domain.models.identification_result import IdentificationResult
from src.modules.identification.domain.models.enums import PersonType
from src.shared.data.base.repository import BaseRepository


class IdentificationResultRepository(BaseRepository[IdentificationResult]):
    """Repository for IdentificationResult model"""

    def __init__(self):
        super().__init__(IdentificationResult)

    def find_by_search(self, search_id: str) -> List[IdentificationResult]:
        """Find all results for a specific search"""
        return self.find_many_by({"search_id": search_id})

    def find_matches_by_search(self, search_id: str) -> List[IdentificationResult]:
        """
        Find only matched results for a specific search

        Args:
            search_id: ID of the search

        Returns:
            List of results where is_match=True
        """
        return self.model.query.filter(
            self.model.is_deleted == False,
            self.model.search_id == search_id,
            self.model.is_match == True
        ).order_by(self.model.similarity_score.desc()).all()

    def find_by_person(self, person_id: str) -> List[IdentificationResult]:
        """Find all results that matched a specific person"""
        return self.find_many_by({"person_id": person_id})

    def find_top_matches_by_search(self, search_id: str, limit: int = 10) -> List[IdentificationResult]:
        """
        Find top N matches for a search ordered by similarity score

        Args:
            search_id: ID of the search
            limit: Maximum number of results to return (default: 10)

        Returns:
            List of top matched results
        """
        return self.model.query.filter(
            self.model.is_deleted == False,
            self.model.search_id == search_id,
            self.model.is_match == True
        ).order_by(self.model.similarity_score.desc()).limit(limit).all()

    def find_by_person_type(self, search_id: str, person_type: PersonType) -> List[IdentificationResult]:
        """
        Find results for a search filtered by person type

        Args:
            search_id: ID of the search
            person_type: Type of person (criminal or missing_person)

        Returns:
            List of results matching the person type
        """
        return self.model.query.filter(
            self.model.is_deleted == False,
            self.model.search_id == search_id,
            self.model.person_type == person_type
        ).all()

    def get_best_match_per_person(self, search_id: str) -> List[IdentificationResult]:
        """
        Get the best match (highest similarity) for each unique person in a search

        Args:
            search_id: ID of the search

        Returns:
            List of results with best match per person
        """
        from sqlalchemy import func

        # Subquery to get max similarity score per person
        subquery = self.model.query.filter(
            self.model.is_deleted == False,
            self.model.search_id == search_id,
            self.model.is_match == True
        ).with_entities(
            self.model.person_id,
            func.max(self.model.similarity_score).label('max_score')
        ).group_by(self.model.person_id).subquery()

        # Join to get full result records
        return self.model.query.join(
            subquery,
            (self.model.person_id == subquery.c.person_id) &
            (self.model.similarity_score == subquery.c.max_score)
        ).filter(
            self.model.is_deleted == False,
            self.model.search_id == search_id
        ).order_by(self.model.similarity_score.desc()).all()

    def count_matches_by_search(self, search_id: str) -> int:
        """Count total matches for a search"""
        return self.count({"search_id": search_id, "is_match": True})