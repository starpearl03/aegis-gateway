# ===== shared/repositories/person_image_repository.py =====
from typing import List, Optional

from src.modules.records.domain.models.person_image import PersonImage
from src.shared.data.base.repository import BaseRepository


class PersonImageRepository(BaseRepository[PersonImage]):
    """Repository for PersonImage model"""

    def __init__(self):
        super().__init__(PersonImage)

    def find_by_person_id(self, person_id: str) -> List[PersonImage]:
        """Find all images for a specific person"""
        return self.find_many_by({"person_id": person_id})

    def find_primary_image(self, person_id: str) -> Optional[PersonImage]:
        """Find the primary image for a person"""
        return self.find_one_by({"person_id": person_id, "is_primary": True})

    def find_images_with_vectors(self, person_id: str) -> List[PersonImage]:
        """Find all images with facial recognition vectors for a person"""
        return self.model.query.filter(
            self.model.is_deleted == False,
            self.model.person_id == person_id,
            self.model.image_vector.isnot(None)
        ).all()

    def set_as_primary(self, image_id: str, person_id: str) -> PersonImage:
        """
        Set an image as primary and unset all other primary images for the person.

        Args:
            image_id: ID of the image to set as primary
            person_id: ID of the person

        Returns:
            The updated primary image
        """
        # Unset all primary images for this person
        images = self.find_by_person_id(person_id)
        for img in images:
            if img.is_primary:
                img.is_primary = False

        # Set the new primary image
        image = self.find_by_id(image_id)
        if image:
            image.is_primary = True
            self.update(image)

        return image