# ===== shared/utils/person_image_utils.py =====
from typing import List

import logging

from src.modules.records.domain.models.person_image import PersonImage
from src.modules.records.domain.repositories.person_image_repository import PersonImageRepository
from src.modules.records.domain.repositories.person_repository import PersonRepository
from src.modules.records.presentation.dtos.record_management import CreatePersonImageRequest, PersonImageResponse
from src.shared.configs.exceptions.exceptions import NotFoundException, ValidationException
from src.shared.utils.facial_recongition_service import FacialRecognitionService

logger = logging.getLogger(__name__)


class PersonImageUtils:
    """Utility class for person image management operations with facial recognition."""

    def __init__(self):
        self.image_repo = PersonImageRepository()
        self.person_repo = PersonRepository()
        self.face_recognition = FacialRecognitionService()

    def upload_person_image(self, request: CreatePersonImageRequest) -> PersonImageResponse:
        """
        Upload an image for a person with automatic face vector generation.

        Args:
            request: CreatePersonImageRequest DTO

        Returns:
            PersonImageResponse DTO

        Raises:
            NotFoundException: If person not found
            ValidationException: If image data is invalid or face detection fails
        """
        # Verify person exists
        person = self.person_repo.find_by_id(request.person_id)
        if not person:
            raise NotFoundException(f"Person with ID {request.person_id} not found")

        try:
            # Extract face vector from image
            logger.info(f"Extracting face vector from image: {request.image_path}")
            face_vectors = self.face_recognition.extract_face_vector(request.image_path)

            # Validate that at least one face was detected
            if not face_vectors or len(face_vectors) == 0:
                raise ValidationException(
                    f"No face detected in image: {request.image_path}. "
                    "Please upload a clear image with a visible face."
                )

            # Use the first detected face vector (highest quality)
            face_vector = face_vectors[0]
            logger.info(f"Successfully extracted face vector with {len(face_vector)} dimensions")

            # Check if this is the first image for this person
            existing_images = self.image_repo.find_by_person_id(request.person_id)
            is_first_image = len(existing_images) == 0

            # If request doesn't specify primary status and this is first image, make it primary
            if request.is_primary is None and is_first_image:
                request.is_primary = True

            # If setting as primary, unset other primary images
            if request.is_primary:
                self._unset_primary_images(request.person_id)

            # Create image entity with face vector
            image = PersonImage(
                person_id=request.person_id,
                image_path=request.image_path,
                image_vector=face_vector,  # Store the extracted face vector
                is_primary=request.is_primary if request.is_primary is not None else False,
                quality_score=request.quality_score,
                uploaded_by=request.uploaded_by
            )

            # Save to database
            saved_image = self.image_repo.create(image)

            logger.info(f"Successfully uploaded image with face vector for person {request.person_id}")

            # Return response DTO
            return PersonImageResponse(
                id=saved_image.id,
                person_id=saved_image.person_id,
                image_path=saved_image.image_path,
                is_primary=saved_image.is_primary,
                quality_score=saved_image.quality_score,
                capture_date=saved_image.capture_date.isoformat(),
                created_at=saved_image.created_at.isoformat(),
                updated_at=saved_image.updated_at.isoformat()
            )

        except ValidationException:
            raise
        except Exception as e:
            logger.error(f"Failed to upload image: {str(e)}")
            raise ValidationException(f"Failed to upload image: {str(e)}")

    def upload_multiple_images(
            self,
            person_id: str,
            image_paths: List[str],
            uploaded_by: str = None
    ) -> List[PersonImageResponse]:
        """
        Upload multiple images for a person with automatic face vector generation.

        Args:
            person_id: Person ID
            image_paths: List of image paths
            uploaded_by: User ID who uploaded the images

        Returns:
            List of PersonImageResponse DTOs

        Raises:
            NotFoundException: If person not found
            ValidationException: If no faces detected in any image
        """
        # Verify person exists
        person = self.person_repo.find_by_id(person_id)
        if not person:
            raise NotFoundException(f"Person with ID {person_id} not found")

        uploaded_images = []
        failed_images = []

        for idx, image_path in enumerate(image_paths):
            try:
                # Create request for each image
                request = CreatePersonImageRequest(
                    person_id=person_id,
                    image_path=image_path,
                    is_primary=(idx == 0 and len(self.image_repo.find_by_person_id(person_id)) == 0),
                    uploaded_by=uploaded_by
                )

                # Upload image with face vector
                image_response = self.upload_person_image(request)
                uploaded_images.append(image_response)

            except Exception as e:
                logger.warning(f"Failed to upload image {image_path}: {str(e)}")
                failed_images.append({"path": image_path, "error": str(e)})
                continue

        if not uploaded_images:
            raise ValidationException(
                f"Failed to upload any images. No faces detected in provided images. "
                f"Failed: {len(failed_images)}"
            )

        if failed_images:
            logger.warning(
                f"Successfully uploaded {len(uploaded_images)} images, "
                f"but {len(failed_images)} failed"
            )

        return uploaded_images

    def get_person_images(self, person_id: str) -> List[PersonImageResponse]:
        """
        Get all images for a person.

        Args:
            person_id: Person ID

        Returns:
            List of PersonImageResponse DTOs

        Raises:
            NotFoundException: If person not found
        """
        # Verify person exists
        person = self.person_repo.find_by_id(person_id)
        if not person:
            raise NotFoundException(f"Person with ID {person_id} not found")

        images = self.image_repo.find_by_person_id(person_id)

        return [
            PersonImageResponse(
                id=img.id,
                person_id=img.person_id,
                image_path=img.image_path,
                is_primary=img.is_primary,
                quality_score=img.quality_score,
                capture_date=img.capture_date.isoformat(),
                created_at=img.created_at.isoformat(),
                updated_at=img.updated_at.isoformat()
            )
            for img in images
        ]

    def get_primary_image(self, person_id: str) -> PersonImageResponse:
        """
        Get the primary image for a person.

        Args:
            person_id: Person ID

        Returns:
            PersonImageResponse DTO

        Raises:
            NotFoundException: If person or primary image not found
        """
        # Verify person exists
        person = self.person_repo.find_by_id(person_id)
        if not person:
            raise NotFoundException(f"Person with ID {person_id} not found")

        image = self.image_repo.find_primary_image(person_id)

        if not image:
            raise NotFoundException(f"No primary image found for person {person_id}")

        return PersonImageResponse(
            id=image.id,
            person_id=image.person_id,
            image_path=image.image_path,
            is_primary=image.is_primary,
            quality_score=image.quality_score,
            capture_date=image.capture_date.isoformat(),
            created_at=image.created_at.isoformat(),
            updated_at=image.updated_at.isoformat()
        )

    def set_primary_image(self, image_id: str, person_id: str) -> PersonImageResponse:
        """
        Set an image as primary for a person.
        Automatically unsets all other images as primary for this person.

        Args:
            image_id: Image ID to set as primary
            person_id: Person ID

        Returns:
            PersonImageResponse DTO

        Raises:
            NotFoundException: If image or person not found
            ValidationException: If image doesn't belong to the person
        """
        # Verify person exists
        person = self.person_repo.find_by_id(person_id)
        if not person:
            raise NotFoundException(f"Person with ID {person_id} not found")

        # Verify image exists
        image = self.image_repo.find_by_id(image_id)
        if not image:
            raise NotFoundException(f"Image with ID {image_id} not found")

        # Verify image belongs to this person
        if image.person_id != person_id:
            raise ValidationException(
                f"Image {image_id} does not belong to person {person_id}"
            )

        # Unset all other primary images for this person
        self._unset_primary_images(person_id)

        # Set this image as primary
        image.is_primary = True
        updated_image = self.image_repo.update(image)

        return PersonImageResponse(
            id=updated_image.id,
            person_id=updated_image.person_id,
            image_path=updated_image.image_path,
            is_primary=updated_image.is_primary,
            quality_score=updated_image.quality_score,
            capture_date=updated_image.capture_date.isoformat(),
            created_at=updated_image.created_at.isoformat(),
            updated_at=updated_image.updated_at.isoformat()
        )

    def delete_person_image(self, image_id: str) -> bool:
        """
        Delete a person image.
        If the deleted image was primary, automatically sets another image as primary.

        Args:
            image_id: Image ID

        Returns:
            True if deleted successfully

        Raises:
            NotFoundException: If image not found
        """
        image = self.image_repo.find_by_id(image_id)

        if not image:
            raise NotFoundException(f"Image with ID {image_id} not found")

        was_primary = image.is_primary
        person_id = image.person_id

        # Delete the image
        self.image_repo.delete(image)

        # If deleted image was primary, set another image as primary
        if was_primary:
            remaining_images = self.image_repo.find_by_person_id(person_id)
            if remaining_images:
                # Set the first remaining image as primary
                remaining_images[0].is_primary = True
                self.image_repo.update(remaining_images[0])
                logger.info(
                    f"Deleted primary image {image_id}, "
                    f"set image {remaining_images[0].id} as new primary"
                )

        return True

    def _unset_primary_images(self, person_id: str) -> None:
        """
        Helper method to unset all primary images for a person.

        Args:
            person_id: Person ID
        """
        images = self.image_repo.find_by_person_id(person_id)
        for img in images:
            if img.is_primary:
                img.is_primary = False
                self.image_repo.update(img)