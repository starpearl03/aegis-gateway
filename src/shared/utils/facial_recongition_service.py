import os
import cv2
import numpy as np
import logging
import uuid
import time
from typing import List, Dict, Any, Tuple, Optional, Union
from sklearn.cluster import DBSCAN
from scipy.spatial.distance import cosine, euclidean

# Import InsightFace
import insightface
from insightface.app import FaceAnalysis
from insightface.utils import face_align

# Optional: Import Deep SORT for tracking
try:
    from deep_sort_realtime.deepsort_tracker import DeepSort

    DEEPSORT_AVAILABLE = True
except ImportError:
    DEEPSORT_AVAILABLE = False
    logging.warning("DeepSORT not available. Video face tracking will use simpler methods.")

logger = logging.getLogger(__name__)


class FacialRecognitionService:
    """Service for facial recognition using InsightFace with enhanced accuracy"""

    def __init__(self, config=None):
        """
        Initialize the facial recognition service with optional configuration

        Args:
            config: Optional configuration dictionary to override defaults
        """
        # Default configuration
        self.default_config = {
            # Thresholds
            'similarity_threshold': 0.35,  # Lower threshold for better matching (original was 0.4)
            'min_face_size': 80,  # Minimum face size (width/height) to consider
            'blur_threshold': 100,  # Laplacian variance threshold for blur detection
            'face_quality_threshold': 0.4,  # Minimum face quality score to use

            # Preprocessing
            'apply_histogram_equalization': True,
            'apply_normalization': True,
            'apply_gamma_correction': True,
            'gamma_value': 1.0,

            # Similarity calculation
            'use_multiple_metrics': True,
            'metric_weights': {'cosine': 0.7, 'euclidean': 0.3},

            # Face alignment
            'use_enhanced_alignment': True,
            'alignment_methods': ['default'],
            'detection_size': (640, 640),
            'feature_extraction_size': (112, 112),

            # Clustering
            'eps_values': [0.25, 0.3, 0.35, 0.4],
            'dbscan_min_samples': 2,

            # Video processing
            'sampling_rate': 3,  # Frames per second to sample in videos

            # Debug options
            'debug': False,
            'save_processed_faces': False,
            'processed_faces_dir': 'processed_faces',
        }

        # Override defaults with provided config
        self.config = self.default_config.copy()
        if config:
            self.config.update(config)

        # Initialize similarity threshold from config
        self.similarity_threshold = self.config['similarity_threshold']
        self.min_face_size = self.config['min_face_size']
        self.blur_threshold = self.config['blur_threshold']
        self.detection_size = self.config['detection_size']

        # Initialize InsightFace - will download model on first run
        self.face_app = FaceAnalysis(
            name="buffalo_l",  # Use large model for better accuracy
            providers=['CUDAExecutionProvider', 'CPUExecutionProvider']  # Try CUDA first, fall back to CPU
        )
        self.face_app.prepare(ctx_id=0, det_size=self.detection_size)

        # Initialize tracker for videos if DeepSORT is available
        if DEEPSORT_AVAILABLE:
            self.tracker = DeepSort(max_age=30)
            self.use_deepsort = True
        else:
            self.use_deepsort = False

        logger.info("Facial Recognition Service initialized with InsightFace")

        # Create directory for processed faces if enabled
        if self.config['save_processed_faces']:
            os.makedirs(self.config['processed_faces_dir'], exist_ok=True)

    def extract_face_vector(self, image_path: str) -> List[list]:
        """
        Extract face vectors from an image file (compatibility method for existing code)

        Args:
            image_path: Path to the image file

        Returns:
            List of face embedding vectors as lists of floats
        """
        logger.info(f"Extracting face vector from image: {image_path} (compatibility method)")
        return self.extract_face_vectors_from_image(image_path)

    def preprocess_face(self, face_img):
        """
        Apply preprocessing techniques to improve face recognition across different conditions

        Args:
            face_img: Face image to preprocess

        Returns:
            Preprocessed face image
        """
        try:
            # Skip processing if image is empty
            if face_img is None or face_img.size == 0:
                return face_img

            # Create a copy to avoid modifying original
            processed = face_img.copy()

            # Apply histogram equalization for better contrast handling
            if self.config['apply_histogram_equalization']:
                # Convert to LAB color space for better equalization
                if len(processed.shape) == 3:  # Color image
                    lab = cv2.cvtColor(processed, cv2.COLOR_RGB2LAB)
                    l, a, b = cv2.split(lab)

                    # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
                    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                    cl = clahe.apply(l)

                    # Merge and convert back to RGB
                    enhanced_lab = cv2.merge((cl, a, b))
                    processed = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2RGB)
                else:  # Grayscale image
                    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                    processed = clahe.apply(processed)

            # Apply normalization for consistent pixel range
            if self.config['apply_normalization']:
                processed = cv2.normalize(processed, None, 0, 255, cv2.NORM_MINMAX)

            # Apply gamma correction for better brightness handling
            if self.config['apply_gamma_correction']:
                gamma = self.config['gamma_value']
                inv_gamma = 1.0 / gamma
                table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)]).astype(np.uint8)
                processed = cv2.LUT(processed, table)

            # Save processed face for debugging if enabled
            if self.config['save_processed_faces']:
                timestamp = int(time.time() * 1000)
                filename = os.path.join(self.config['processed_faces_dir'], f"processed_face_{timestamp}.jpg")
                cv2.imwrite(filename, cv2.cvtColor(processed, cv2.COLOR_RGB2BGR))

            return processed
        except Exception as e:
            logger.error(f"Error preprocessing face: {str(e)}")
            return face_img  # Return original if preprocessing fails

    def extract_face_vectors_from_file(self, file_path: str, file_type: str) -> List[list]:
        """
        Extract face vectors from an image or video file

        Args:
            file_path: Path to the file
            file_type: Type of file ('image' or 'video')

        Returns:
            List of face embedding vectors as lists of floats (PostgreSQL compatible)
        """
        try:
            logger.info(f"Extracting face vectors from {file_type}: {file_path}")

            if file_type.lower() == 'image':
                vectors = self.extract_face_vectors_from_image(file_path)
                logger.info(f"Extracted {len(vectors)} face vectors from image")
                return vectors

            elif file_type.lower() == 'video':
                vectors = self.extract_face_vectors_from_video(file_path)
                logger.info(f"Extracted {len(vectors)} face vectors from video")
                return vectors

            else:
                raise ValueError(f"Unsupported file type: {file_type}. Supported types are 'image' and 'video'.")

        except Exception as e:
            logger.error(f"Error extracting face vectors from file: {str(e)}", exc_info=True)
            return []

    def assess_face_quality(self, face, img) -> float:
        """
        Improved face quality assessment with better metrics for video frames

        Args:
            face: InsightFace face object
            img: Original image

        Returns:
            Quality score (higher is better)
        """
        try:
            # Extract face bounding box
            x1, y1, x2, y2 = map(int, face.bbox)

            # 1. Face size (more weight on area)
            face_width, face_height = x2 - x1, y2 - y1
            face_area = face_width * face_height
            min_area = self.min_face_size * self.min_face_size

            if face_area < min_area:
                return 0.0  # Too small

            # Scale factor for larger faces (up to 4x minimum size)
            size_score = min(1.0, face_area / (min_area * 4))

            # 2. Face orientation (frontal is better)
            landmarks = face.landmark
            orientation_score = 0.5  # Default

            if landmarks is not None and len(landmarks) >= 5:
                # Left eye, right eye, nose
                left_eye, right_eye = landmarks[0], landmarks[1]
                nose = landmarks[2]

                # Calculate eye line
                eye_distance = np.sqrt((right_eye[0] - left_eye[0]) ** 2 + (right_eye[1] - left_eye[1]) ** 2)
                eye_center_x = (left_eye[0] + right_eye[0]) / 2
                eye_center_y = (left_eye[1] + right_eye[1]) / 2

                # Symmetry: distance from nose to eye line center
                vertical_dist = abs(nose[1] - eye_center_y)
                horizontal_dist = abs(nose[0] - eye_center_x)

                # Eyes should be level and nose should be centered and below eyes
                eye_level = 1.0 - min(1.0, abs(right_eye[1] - left_eye[1]) / eye_distance)
                nose_centered = 1.0 - min(1.0, horizontal_dist / (eye_distance * 0.5))
                nose_below = 1.0 if vertical_dist > 0 and nose[1] > eye_center_y else 0.5

                # Combine orientation metrics
                orientation_score = 0.4 * eye_level + 0.4 * nose_centered + 0.2 * nose_below

            # 3. Blur detection (more sensitive)
            face_img = img[y1:y2, x1:x2]
            if face_img.size == 0:
                return 0.0

            if len(face_img.shape) == 3:  # Color image
                gray = cv2.cvtColor(face_img, cv2.COLOR_RGB2GRAY)
            else:  # Already grayscale
                gray = face_img

            # Laplacian variance (higher = less blurry)
            blur_value = cv2.Laplacian(gray, cv2.CV_64F).var()

            # Scale blur score - more sensitive to blur
            blur_threshold = self.blur_threshold
            blur_score = min(1.0, blur_value / blur_threshold)

            # 4. Face brightness and contrast
            if face_img.size > 0:
                if len(face_img.shape) == 3:
                    face_gray = cv2.cvtColor(face_img, cv2.COLOR_RGB2GRAY)
                else:
                    face_gray = face_img

                # Calculate brightness and contrast
                brightness = np.mean(face_gray)
                contrast = np.std(face_gray)

                # Normalize scores (ideal range)
                brightness_score = 1.0 - abs((brightness - 127.5) / 127.5)
                contrast_score = min(1.0, contrast / 60.0)  # Good contrast is > 60

                # Combine lighting scores
                lighting_score = 0.5 * brightness_score + 0.5 * contrast_score
            else:
                lighting_score = 0.0

            # Combine all scores with adjusted weights
            # More weight on size and blur (most important for recognition)
            quality_score = (
                    0.4 * size_score +
                    0.25 * blur_score +
                    0.25 * orientation_score +
                    0.1 * lighting_score
            )

            return quality_score

        except Exception as e:
            logger.warning(f"Error assessing face quality: {str(e)}")
            return 0.0

    def extract_face_vectors_from_image(self, file_path: str) -> List[list]:
        """
        Extract face vectors from a single image file with enhanced preprocessing
        and multiple alignment methods

        Args:
            file_path: Path to the image file

        Returns:
            List of face embedding vectors as lists of floats (PostgreSQL compatible)
        """
        try:
            # Read image
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            img = cv2.imread(file_path)
            if img is None:
                raise ValueError(f"Failed to read image: {file_path}")

            # BGR to RGB for InsightFace
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            # Detect faces
            faces = self.face_app.get(img)

            if not faces:
                logger.warning(f"No faces detected in image: {file_path}")
                return []

            # Extract quality-filtered face embeddings
            face_vectors = []
            for face in faces:
                quality = self.assess_face_quality(face, img)

                # Only process faces with sufficient quality
                if quality > self.config['face_quality_threshold']:
                    # Get face region
                    x1, y1, x2, y2 = map(int, face.bbox)
                    face_img = img[y1:y2, x1:x2]

                    # Preprocess face image
                    preprocessed_face = self.preprocess_face(face_img)

                    # Multiple embeddings collection
                    embeddings = []
                    embedding_weights = []

                    # 1. Original embedding
                    embeddings.append(face.embedding)
                    embedding_weights.append(1.0)  # Higher weight for original

                    # 2. Enhanced alignment if requested and landmarks available
                    if self.config['use_enhanced_alignment'] and face.landmark is not None:
                        try:
                            # Align face and extract features
                            aligned_face = face_align.norm_crop(img, face.landmark,
                                                                image_size=self.config['feature_extraction_size'][0])

                            # Preprocess aligned face
                            preprocessed_aligned = self.preprocess_face(aligned_face)

                            # Get embedding from aligned face
                            aligned_faces = self.face_app.get(preprocessed_aligned)
                            if aligned_faces and aligned_faces[0].embedding is not None:
                                embeddings.append(aligned_faces[0].embedding)
                                embedding_weights.append(0.9)  # Slightly lower weight for aligned
                        except Exception as align_err:
                            logger.warning(f"Face alignment failed: {str(align_err)}")

                    # 3. Combine embeddings if we have multiple
                    if len(embeddings) > 1:
                        # Normalize each embedding
                        norm_embeddings = []
                        for emb in embeddings:
                            norm_emb = emb / np.linalg.norm(emb)
                            norm_embeddings.append(norm_emb)

                        # Weighted average of embeddings
                        total_weight = sum(embedding_weights)
                        weighted_embedding = np.zeros_like(norm_embeddings[0])

                        for i, emb in enumerate(norm_embeddings):
                            weighted_embedding += emb * (embedding_weights[i] / total_weight)

                        # Normalize final embedding
                        final_embedding = weighted_embedding / np.linalg.norm(weighted_embedding)
                    else:
                        # Just use the original embedding
                        final_embedding = face.embedding / np.linalg.norm(face.embedding)

                    # Convert numpy.float32 to standard Python float for PostgreSQL compatibility
                    embedding = final_embedding.astype(float).tolist()
                    face_vectors.append(embedding)

            return face_vectors

        except Exception as e:
            logger.error(f"Error extracting face vectors from image: {str(e)}")
            return []

    def extract_face_vectors_from_video(self, video_path: str, sampling_rate: int = None) -> List[list]:
        """
        Extract unique face vectors from a video file using tracking and clustering with enhanced preprocessing

        Args:
            video_path: Path to the video file
            sampling_rate: Number of frames to sample per second (default from config)

        Returns:
            List of unique face embedding vectors as lists of floats (PostgreSQL compatible)
        """
        try:
            # Use config sampling rate if not specified
            if sampling_rate is None:
                sampling_rate = self.config['sampling_rate']

            # Check if video file exists
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"Video file not found: {video_path}")

            # Open video file
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"Failed to open video: {video_path}")

            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps

            # Calculate frame sampling interval
            frame_interval = max(1, int(fps / sampling_rate))

            logger.info(
                f"Processing video: {video_path}, fps={fps}, frames={frame_count}, duration={duration}s, interval={frame_interval}")

            # Always use simple video processing to avoid DeepSORT issues
            face_embeddings = self._process_video_simple(cap, fps, frame_count, frame_interval)

            # Release video resource
            cap.release()

            logger.info(f"Extracted {len(face_embeddings)} unique face embeddings from video")

            # If we have multiple embeddings, perform clustering to find unique individuals
            if len(face_embeddings) > 1:
                try:
                    unique_embeddings = self._cluster_embeddings(face_embeddings)
                    logger.info(
                        f"Clustered {len(face_embeddings)} embeddings into {len(unique_embeddings)} unique faces")

                    # Convert numpy arrays to standard Python float lists for PostgreSQL compatibility
                    return [emb.astype(float).tolist() if isinstance(emb, np.ndarray) else emb
                            for emb in unique_embeddings]
                except Exception as cluster_err:
                    logger.warning(f"Clustering failed: {str(cluster_err)}, returning all embeddings")
                    # If clustering fails, return all embeddings
                    return [emb.astype(float).tolist() if isinstance(emb, np.ndarray) else emb
                            for emb in face_embeddings[:5]]  # Limit to 5 to avoid too many comparisons

            # If we only have one embedding, return it as a list of lists
            return [emb.astype(float).tolist() if isinstance(emb, np.ndarray) else emb
                    for emb in face_embeddings]

        except Exception as e:
            logger.error(f"Error extracting face vectors from video: {str(e)}", exc_info=True)
            return []

    def _process_video_with_deepsort(self, cap, fps, frame_count, frame_interval) -> List[np.ndarray]:
        """
        Process video with DeepSORT tracking for face identification with improved alignment

        Args:
            cap: OpenCV video capture object
            fps: Frames per second of the video
            frame_count: Total number of frames
            frame_interval: Interval for frame sampling

        Returns:
            List of unique face embedding vectors as numpy arrays
        """
        # Initialize trackers and storage
        tracked_faces = {}  # track_id -> [embeddings, quality_scores]
        current_frame = 0

        logger.info(
            f"Processing video with DeepSORT ({frame_count / fps:.2f}s, {fps:.2f}fps) with sampling interval {frame_interval}")

        # Process video frames
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Only process frames at the sampling interval
            if current_frame % frame_interval == 0:
                # Convert to RGB for InsightFace
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Detect faces
                faces = self.face_app.get(rgb_frame)

                # Prepare tracking detections
                detections = []
                face_embeddings = []
                qualities = []

                for face in faces:
                    x1, y1, x2, y2 = map(int, face.bbox)

                    # Extract face region for preprocessing
                    face_img = rgb_frame[y1:y2, x1:x2]

                    # Apply preprocessing
                    preprocessed_face = self.preprocess_face(face_img)

                    # Calculate face quality with improved metrics
                    quality = self.assess_face_quality(face, rgb_frame)

                    # Get normalized embedding
                    face_embedding = face.embedding / np.linalg.norm(face.embedding)

                    # Try aligned face if landmarks available
                    if face.landmark is not None:
                        try:
                            aligned_face = face_align.norm_crop(rgb_frame, face.landmark)
                            aligned_preprocessed = self.preprocess_face(aligned_face)
                            aligned_faces = self.face_app.get(aligned_preprocessed)
                            if aligned_faces and aligned_faces[0].embedding is not None:
                                aligned_embedding = aligned_faces[0].embedding
                                # Normalize embedding
                                aligned_embedding = aligned_embedding / np.linalg.norm(aligned_embedding)
                                # Weighted combination
                                face_embedding = 0.7 * face_embedding + 0.3 * aligned_embedding
                                face_embedding = face_embedding / np.linalg.norm(face_embedding)
                        except Exception as align_err:
                            logger.warning(f"Face alignment failed: {str(align_err)}, using original embedding")

                    # Create detection for DeepSORT with proper format (bbox, confidence, embedding)
                    # Note: DeepSORT expects embeddings parameter as a separate list
                    detection = ([x1, y1, x2 - x1, y2 - y1], face.det_score)
                    detections.append(detection)
                    face_embeddings.append(face_embedding)
                    qualities.append(quality)

                # Only update tracker if we have detections
                if detections:
                    try:
                        # Here's the fix - pass embeddings as a separate parameter
                        tracks = self.tracker.update_tracks(detections, embeddings=face_embeddings)

                        # Process tracks
                        for i, track in enumerate(tracks):
                            if not track.is_confirmed():
                                continue

                            track_id = track.track_id
                            if track_id not in tracked_faces:
                                tracked_faces[track_id] = {"embeddings": [], "qualities": [], "frames": []}

                            if i < len(face_embeddings):  # Make sure we have an embedding for this track
                                tracked_faces[track_id]["embeddings"].append(face_embeddings[i])
                                tracked_faces[track_id]["qualities"].append(qualities[i])
                                tracked_faces[track_id]["frames"].append(current_frame)

                    except Exception as e:
                        logger.warning(f"Error updating tracks: {str(e)}")
                        # Fall back to simple storage
                        for i in range(len(face_embeddings)):
                            track_id = f"fallback_{current_frame}_{i}"
                            if track_id not in tracked_faces:
                                tracked_faces[track_id] = {"embeddings": [], "qualities": [], "frames": []}
                            tracked_faces[track_id]["embeddings"].append(face_embeddings[i])
                            tracked_faces[track_id]["qualities"].append(qualities[i])
                            tracked_faces[track_id]["frames"].append(current_frame)

            current_frame += 1

            # Status update for long videos
            if current_frame % 100 == 0:
                logger.debug(f"Processed {current_frame}/{frame_count} frames, {len(tracked_faces)} unique faces")

        # For each tracked face, select the best quality embeddings
        best_face_embeddings = []
        for track_id, data in tracked_faces.items():
            if len(data["embeddings"]) < 1:
                # Skip tracks with no embeddings
                continue

            # Get embedding with highest quality
            best_idx = np.argmax(data["qualities"]) if data["qualities"] else 0
            best_face_embeddings.append(data["embeddings"][best_idx])

        # If we didn't get any embeddings from tracking, try simpler method
        if not best_face_embeddings:
            logger.warning("DeepSORT tracking failed to extract embeddings, falling back to simple processing")
            # Rewind the video and try simple processing
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            best_face_embeddings = self._process_video_simple(cap, fps, frame_count, frame_interval)

        # Return best face embeddings
        return best_face_embeddings


    def _process_video_simple(self, cap, fps, frame_count, frame_interval) -> List[np.ndarray]:
        """
        Process video with simple frame sampling for face identification with enhanced preprocessing
        (Used when DeepSORT is not available)

        Args:
            cap: OpenCV video capture object
            fps: Frames per second of the video
            frame_count: Total number of frames
            frame_interval: Interval for frame sampling

        Returns:
            List of unique face embedding vectors as numpy arrays
        """
        # Initialize storage for all detected face embeddings
        all_embeddings = []
        all_qualities = []
        current_frame = 0

        logger.info(
            f"Processing video with simple tracking ({frame_count / fps:.2f}s, {fps:.2f}fps) with sampling interval {frame_interval}")

        # Process video frames
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Only process frames at the sampling interval
            if current_frame % frame_interval == 0:
                # Convert to RGB for InsightFace
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Detect faces
                faces = self.face_app.get(rgb_frame)

                # Extract face embeddings with improved quality and alignment
                for face in faces:
                    quality = self.assess_face_quality(face, rgb_frame)
                    if quality > self.config['face_quality_threshold']:  # Only use faces with decent quality
                        # Extract face region
                        x1, y1, x2, y2 = map(int, face.bbox)
                        face_img = rgb_frame[y1:y2, x1:x2]

                        # Apply preprocessing
                        preprocessed_face = self.preprocess_face(face_img)

                        # Try different alignment methods
                        if face.landmark is not None:
                            try:
                                aligned_face = face_align.norm_crop(rgb_frame, face.landmark)
                                preprocessed_aligned = self.preprocess_face(aligned_face)
                                aligned_faces = self.face_app.get(preprocessed_aligned)
                                if aligned_faces:
                                    embedding = aligned_faces[0].embedding
                                else:
                                    embedding = face.embedding
                            except Exception as align_err:
                                logger.warning(f"Face alignment failed: {str(align_err)}, using original embedding")
                                embedding = face.embedding
                        else:
                            embedding = face.embedding

                        # Normalize embedding
                        embedding = embedding / np.linalg.norm(embedding)
                        all_embeddings.append(embedding)
                        all_qualities.append(quality)

            current_frame += 1

            # Status update for long videos
            if current_frame % 100 == 0:
                logger.debug(f"Processed {current_frame}/{frame_count} frames, {len(all_embeddings)} faces detected")

        return all_embeddings

    def _cluster_embeddings(self, embeddings: List[np.ndarray]) -> List[np.ndarray]:
        """
        Improved clustering with adaptive epsilon and better center detection

        Args:
            embeddings: List of face embedding vectors (numpy arrays)

        Returns:
            List of unique face embedding vectors (one per cluster) as numpy arrays
        """
        if not embeddings or len(embeddings) <= 1:
            return embeddings

        try:
            # Normalize all embeddings first
            norm_embeddings = []
            for emb in embeddings:
                if isinstance(emb, list):
                    emb = np.array(emb)
                norm_emb = emb / np.linalg.norm(emb)
                norm_embeddings.append(norm_emb)

            embeddings_array = np.vstack(norm_embeddings)

            # Calculate distance matrix with cosine distance
            n = len(embeddings)
            distance_matrix = np.zeros((n, n))
            for i in range(n):
                for j in range(i + 1, n):
                    distance = cosine(norm_embeddings[i], norm_embeddings[j])
                    distance_matrix[i, j] = distance
                    distance_matrix[j, i] = distance

            # Try multiple epsilon values for DBSCAN to find optimal clustering
            eps_values = self.config['eps_values']
            best_clusters = []
            best_silhouette = -1  # For silhouette-based evaluation (higher is better)

            for eps in eps_values:
                clustering = DBSCAN(eps=eps, min_samples=self.config['dbscan_min_samples'], metric='precomputed').fit(
                    distance_matrix)
                labels = clustering.labels_

                # Skip if all points are noise or in one cluster
                unique_labels = np.unique(labels)
                if len(unique_labels) <= 1 or (len(unique_labels) == 2 and -1 in unique_labels):
                    continue

                # Get representative embedding for each cluster
                clusters = []
                for label in unique_labels:
                    if label == -1:  # Skip noise
                        continue

                    indices = np.where(labels == label)[0]
                    if len(indices) == 0:
                        continue

                    # Find representative face (nearest to center)
                    cluster_vectors = embeddings_array[indices]
                    center = np.mean(cluster_vectors, axis=0)
                    center = center / np.linalg.norm(center)

                    # Find closest vector to center
                    distances = [cosine(center, norm_embeddings[i]) for i in indices]
                    closest_idx = indices[np.argmin(distances)]

                    clusters.append(embeddings[closest_idx])

                # If we found good clusters, use them
                if len(clusters) > 0:
                    best_clusters = clusters
                    logger.info(f"Found {len(clusters)} clusters with eps={eps}")
                    break

            # If no good clustering was found, take top embeddings
            if not best_clusters:
                logger.warning("Clustering failed to find good clusters, using top embeddings")
                # Sort by quality if available
                if hasattr(embeddings, 'qualities') and len(embeddings.qualities) == len(embeddings):
                    indices = np.argsort(embeddings.qualities)[-5:]  # Top 5 by quality
                    return [embeddings[i] for i in indices]
                else:
                    return embeddings[:min(5, len(embeddings))]

            return best_clusters

        except Exception as e:
            logger.error(f"Error in clustering: {str(e)}")
            return embeddings[:min(3, len(embeddings))]

    def calculate_similarity(self, vector1: Union[np.ndarray, list], vector2: Union[np.ndarray, list]) -> float:
        """
        Calculate similarity using multiple metrics for more robust matching

        Args:
            vector1: First vector (numpy array or list)
            vector2: Second vector (numpy array or list)

        Returns:
            Similarity score (0-1, higher means more similar)
        """
        try:
            # Ensure we're working with numpy arrays
            if isinstance(vector1, list):
                vector1 = np.array(vector1)
            if isinstance(vector2, list):
                vector2 = np.array(vector2)

            # Ensure vectors are 1-D
            if len(vector1.shape) > 1:
                vector1 = vector1.flatten()
            if len(vector2.shape) > 1:
                vector2 = vector2.flatten()

            # L2 normalize both vectors (critical for consistent comparison)
            vector1 = vector1 / np.linalg.norm(vector1)
            vector2 = vector2 / np.linalg.norm(vector2)

            # Use multiple metrics if configured
            if self.config['use_multiple_metrics']:
                similarities = {}
                weights = self.config['metric_weights']

                # Cosine similarity (higher is better)
                if 'cosine' in weights:
                    similarities['cosine'] = 1.0 - cosine(vector1, vector2)

                # Euclidean distance (convert to similarity)
                if 'euclidean' in weights:
                    euclidean_dist = euclidean(vector1, vector2)
                    similarities['euclidean'] = 1.0 / (1.0 + euclidean_dist)

                # Calculate weighted average
                weighted_sum = sum(sim * weights.get(metric, 0.0) for metric, sim in similarities.items())
                total_weight = sum(weights.get(metric, 0.0) for metric in similarities)

                if total_weight > 0:
                    return weighted_sum / total_weight
                else:
                    # Fallback to cosine similarity if weights are invalid
                    return 1.0 - cosine(vector1, vector2)
            else:
                # Just use cosine similarity if multiple metrics not enabled
                return 1.0 - cosine(vector1, vector2)
        except Exception as e:
            logger.error(f"Error calculating similarity: {str(e)}")
            return 0.0  # Return lowest similarity on error
