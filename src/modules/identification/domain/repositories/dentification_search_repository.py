from typing import List, Optional
from datetime import datetime, timedelta

from src.modules.identification.domain.models.identification_search import IdentificationSearch
from src.modules.identification.domain.models.enums import SearchType, SearchStatus
from src.shared.data.base.repository import BaseRepository


class IdentificationSearchRepository(BaseRepository[IdentificationSearch]):
    """Repository for IdentificationSearch model"""

    def __init__(self):
        super().__init__(IdentificationSearch)

    def find_by_status(self, status: SearchStatus) -> List[IdentificationSearch]:
        """Find all searches by status"""
        return self.find_many_by({"status": status})

    def find_pending_searches(self) -> List[IdentificationSearch]:
        """Find all pending searches"""
        return self.find_by_status(SearchStatus.PENDING)

    def find_by_search_type(self, search_type: SearchType) -> List[IdentificationSearch]:
        """Find all searches by type (criminal or missing person)"""
        return self.find_many_by({"search_type": search_type})

    def find_recent_searches(self, days: int = 7) -> List[IdentificationSearch]:
        """
        Find searches created within the last N days

        Args:
            days: Number of days to look back (default: 7)

        Returns:
            List of recent searches
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        return self.model.query.filter(
            self.model.is_deleted == False,
            self.model.created_at >= cutoff_date
        ).order_by(self.model.created_at.desc()).all()

    def find_completed_searches(self) -> List[IdentificationSearch]:
        """Find all completed searches"""
        return self.find_by_status(SearchStatus.COMPLETED)

    def find_failed_searches(self) -> List[IdentificationSearch]:
        """Find all failed searches"""
        return self.find_by_status(SearchStatus.FAILED)

    def mark_notification_sent(self, search: IdentificationSearch) -> IdentificationSearch:
        """
        Mark notification as sent for a search

        Args:
            search: The search to mark

        Returns:
            Updated search instance
        """
        search.notification_sent = True
        return self.update(search)
