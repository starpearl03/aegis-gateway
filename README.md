# Sentinel - Police Intelligence System

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![Flask](https://img.shields.io/badge/flask-2.3.3-lightgrey.svg)

Sentinel is an advanced police intelligence system for crime analysis, facial recognition, and predictive policing. Built with a modular architecture using Flask, SQLAlchemy, and AI/ML technologies, it provides comprehensive tools for crime tracking, suspect identification, and crime hotspot detection.

---

## Table of Contents

- [Features](#features)
- [Architecture Overview](#architecture-overview)
- [Project Structure](#project-structure)
- [Technology Stack](#technology-stack)
- [Core Algorithms](#core-algorithms)
  - [Facial Recognition Service](#facial-recognition-service)
  - [Hotspot Detection Algorithm](#hotspot-detection-algorithm)
  - [Base Model & Repository Pattern](#base-model--repository-pattern)
- [Database Schema (ERD)](#database-schema-erd)
- [System Diagrams](#system-diagrams)
  - [High-Level Architecture](#high-level-architecture)
  - [Module Architecture](#module-architecture)
  - [Class Diagrams](#class-diagrams)
  - [Sequence Diagrams](#sequence-diagrams)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Documentation](#api-documentation)

---

## Features

- **Criminal Records Management**: Comprehensive tracking of criminals, crimes, victims, and evidence
- **Facial Recognition**: Advanced face detection and matching using InsightFace with support for images and videos
- **Missing Persons Database**: Track and manage missing person reports with status history
- **Crime Analysis**: AI-powered crime analysis with trend detection and risk assessment
- **Hotspot Detection**: DBSCAN-based geographic clustering to identify crime hotspots
- **Alert Broadcasting**: Multi-channel notifications (Email, SMS) for critical alerts
- **User Authentication**: Secure session-based authentication with role-based access control
- **Soft Delete Pattern**: Safe data deletion with recovery capabilities
- **LLM Integration**: Google Gemini AI for generating analysis summaries and recommendations

---

## Architecture Overview

Sentinel follows a **Clean Architecture** pattern with clear separation of concerns across multiple layers:

<p align="left">
  <img src="docs/imgs/Architecture-Overview.png" alt="Architecture Overview" width="800"/>
</p>

### Modular Architecture

The system is organized into **4 core modules**, each following the same architectural pattern:

```
module/
├── domain/                  # Business logic layer
│   ├── models/             # SQLAlchemy ORM models
│   ├── repositories/       # Data access layer (CRUD operations)
│   └── services/           # Domain services (business logic)
├── presentation/           # User interface layer
│   ├── controller/         # Flask blueprints (REST endpoints)
│   ├── dtos/              # Data Transfer Objects (validation)
│   └── templates/         # Jinja2 HTML templates
└── internal/              # Internal utilities (optional)
```

---

## Project Structure

```
Sentinel/
├── main.py                      # Application entry point
├── requirements.txt             # Python dependencies
├── .env.development            # Development configuration
├── broadcast_contacts.json     # Alert broadcast contacts
│
├── src/                        # Main source directory
│   ├── config/                 # Configuration management
│   │   ├── config.yaml         # YAML configuration
│   │   ├── config.py           # Config loader
│   │   └── factory.py          # Flask app factory
│   │
│   ├── shared/                 # Shared utilities
│   │   ├── configs/            # Global configs & security
│   │   │   ├── exceptions.py
│   │   │   ├── session_manager.py
│   │   │   ├── session_decorators.py
│   │   │   └── global_error_handler.py
│   │   ├── data/               # Data access layer
│   │   │   ├── database.py
│   │   │   └── base/
│   │   │       ├── model.py    # BaseModel
│   │   │       └── repository.py  # BaseRepository
│   │   ├── response/           # Response handling
│   │   │   ├── api_response.py
│   │   │   └── error_detail.py
│   │   ├── utils/              # Utilities
│   │   │   ├── facial_recongition_service.py  # Core facial recognition
│   │   │   ├── LLMClient.py    # Google Gemini client
│   │   │   └── notifications/  # Notification services
│   │   └── ui/                 # Shared templates
│   │       └── templates/
│   │           └── base.jinja2
│   │
│   └── modules/                # Feature modules
│       ├── authentication/     # User authentication & management
│       │   ├── domain/
│       │   │   ├── models/     # User model
│       │   │   ├── repositories/
│       │   │   └── services/   # AuthenticationService, UserManagementService
│       │   └── presentation/
│       │       ├── controller/
│       │       ├── dtos/
│       │       └── templates/
│       │
│       ├── records/            # Criminal records & missing persons
│       │   ├── domain/
│       │   │   ├── models/     # Person, Criminal, Crime, Evidence, etc.
│       │   │   ├── repositories/
│       │   │   └── services/
│       │   ├── presentation/
│       │   └── internal/       # LocationUtils, PersonImageUtils
│       │
│       ├── identification/     # Facial recognition search
│       │   ├── domain/
│       │   │   ├── models/     # IdentificationSearch, IdentificationResult
│       │   │   ├── repositories/
│       │   │   └── services/   # IdentificationSearchService
│       │   └── presentation/
│       │
│       └── crime_analysis/     # Crime analytics & hotspots
│           ├── domain/
│           │   ├── models/     # CrimeAnalysis, CrimeHotspot, CrimeTrend
│           │   ├── repositories/
│           │   └── services/   # CrimeAnalysisService
│           ├── presentation/
│           └── internal/       # HotspotDetector, LLMDataFormatter
│
├── uploads/                    # File uploads
│   ├── criminals/
│   ├── missing_persons/
│   └── evidence/
│
├── logs/                       # Application logs
└── venv/                       # Python virtual environment
```

---

## Technology Stack

### Backend Framework
- **Flask 2.3.3** - Lightweight web framework
- **Flask-SQLAlchemy** - ORM integration
- **Flask-Session** - Server-side session management
- **Flask-Bcrypt 1.0.1** - Password hashing

### Database
- **PostgreSQL** - Primary relational database
- **SQLAlchemy 2.0.44** - Object-relational mapping
- **pgvector 0.4.1** - Vector embeddings for similarity search

### Artificial Intelligence & Machine Learning
- **InsightFace 0.7.3** - Facial recognition and detection
- **Google Generative AI** - Gemini LLM for analysis summaries
- **OpenCV 4.12.0.88** - Computer vision operations
- **scikit-learn 1.7.2** - DBSCAN clustering algorithm
- **NumPy 2.2.6** - Numerical computing
- **SciPy 1.16.3** - Scientific computing (distance calculations)

### External Integrations
- **Twilio 9.8.5** - SMS notifications
- **Gmail SMTP** - Email notifications
- **geopy 2.4.1** - Geocoding and location services

### Frontend
- **Jinja2 3.1.6** - Template engine
- **HTML/CSS/JavaScript** - Web interface

---

## Core Algorithms

### Facial Recognition Service

The `FacialRecognitionService` is the core component for face detection, recognition, and matching. It uses **InsightFace** with the Buffalo_L model for high-accuracy facial recognition.

#### Class Diagram

<p align="left">
  <img src="docs/imgs/class_diagram_1.png" alt="Facial Recognition Service Class Diagram" width="700"/>
</p>

#### Key Features

1. **Multi-Stage Face Preprocessing**
   - **Histogram Equalization**: CLAHE (Contrast Limited Adaptive Histogram Equalization) for better contrast
   - **Normalization**: Pixel value normalization for consistent input
   - **Gamma Correction**: Brightness adjustment for varying lighting conditions

2. **Face Quality Assessment**
   - Face size validation (minimum 80x80 pixels)
   - Blur detection using Laplacian variance
   - Face orientation analysis using facial landmarks
   - Brightness and contrast evaluation
   - Combined quality score: `0.4*size + 0.25*blur + 0.25*orientation + 0.1*lighting`

3. **Enhanced Face Alignment**
   - Uses InsightFace's `face_align.norm_crop()` for geometric normalization
   - Combines original and aligned embeddings with weighted averaging
   - Weights: 70% original embedding + 30% aligned embedding

4. **Video Processing**
   - Frame sampling (configurable FPS sampling rate)
   - Optional DeepSORT tracking for face tracking across frames
   - DBSCAN clustering to identify unique individuals
   - Selects best quality frame per detected person

5. **Similarity Calculation**
   - **Multiple Distance Metrics**:
     - Cosine similarity (70% weight): `1 - cosine_distance(v1, v2)`
     - Euclidean distance (30% weight): `1 / (1 + euclidean_distance(v1, v2))`
   - L2 normalization of all vectors before comparison
   - Default similarity threshold: **0.35** (lower = more strict)

#### Algorithm Flow - Image Processing

<p align="left">
  <img src="docs/imgs/sequence_diagram_1.png" alt="Image Processing Sequence Diagram" width="700"/>
</p>

#### Algorithm Flow - Video Processing with Clustering

<p align="left">
  <img src="docs/imgs/sequence_diagram_2.png" alt="Video Processing Sequence Diagram" width="700"/>
</p>

#### Configuration Parameters

```python
config = {
    'similarity_threshold': 0.35,        # Match threshold (0-1)
    'min_face_size': 80,                 # Minimum face width/height
    'blur_threshold': 100,               # Laplacian variance threshold
    'face_quality_threshold': 0.4,       # Minimum quality to use
    'apply_histogram_equalization': True,
    'apply_normalization': True,
    'apply_gamma_correction': True,
    'use_multiple_metrics': True,
    'metric_weights': {'cosine': 0.7, 'euclidean': 0.3},
    'eps_values': [0.25, 0.3, 0.35, 0.4],  # DBSCAN epsilon values
    'dbscan_min_samples': 2,
    'sampling_rate': 3,                  # Frames per second for videos
}
```

---

### Hotspot Detection Algorithm

The `HotspotDetector` uses **DBSCAN (Density-Based Spatial Clustering of Applications with Noise)** to identify geographic crime hotspots.

#### Class Diagram

<p align="left">
  <img src="docs/imgs/class_diagram_2.png" alt="Hotspot Detector Class Diagram" width="700"/>
</p>

#### Algorithm Description

1. **Spatial Clustering with DBSCAN**
   - Groups incidents within a specified radius (default: 2 km)
   - Requires minimum incidents to form a cluster (default: 3)
   - Uses **Haversine metric** for accurate geographic distance on Earth's surface
   - Handles noise points (isolated incidents)

2. **Crime Type Separation**
   - Clusters each crime type separately (robbery, theft, assault, etc.)
   - Prevents mixing different crime types in the same hotspot
   - Missing persons are treated as a separate category

3. **Centroid Calculation**
   - Calculates average latitude/longitude for each cluster
   - Selects most representative location (closest to centroid)

4. **Risk Level Assessment**
   - **Crimes**:
     - Critical: ≥15 incidents
     - High: 10-14 incidents
     - Medium: 5-9 incidents
     - Low: 3-4 incidents
   - **Missing Persons**:
     - Critical: ≥10 incidents
     - High: 7-9 incidents
     - Medium: 5-6 incidents
     - Low: 3-4 incidents

#### Algorithm Flow

<p align="left">
  <img src="docs/imgs/sequence_diagram_3.png" alt="Hotspot Detection Sequence Diagram" width="700"/>
</p>

#### Mathematical Formulas

**Haversine Distance** (used by DBSCAN):
```
a = sin²(Δlat/2) + cos(lat1) × cos(lat2) × sin²(Δlon/2)
c = 2 × atan2(√a, √(1-a))
distance = R × c

where:
  R = Earth's radius (6371 km)
  Δlat = lat2 - lat1 (in radians)
  Δlon = lon2 - lon1 (in radians)
```

**DBSCAN Epsilon** (radius threshold):
```
eps_radians = radius_km / earth_radius_km
eps_radians = 2.0 / 6371.0 ≈ 0.000314 radians
```

#### Usage Example

```python
from src.modules.crime_analysis.internal.hotspot_detector import HotspotDetector

# Initialize detector
detector = HotspotDetector(
    radius_km=2.0,      # 2km radius
    min_incidents=3     # Minimum 3 incidents for a cluster
)

# Detect hotspots
hotspots = detector.detect_hotspots(
    crimes=crime_list,
    missing_persons=missing_person_list
)

# Get statistics
stats = detector.get_cluster_statistics(hotspots)
print(f"Found {stats['total_hotspots']} hotspots")
print(f"By risk level: {stats['by_risk_level']}")
print(f"By crime type: {stats['by_crime_type']}")
```

---

### Base Model & Repository Pattern

Sentinel implements a **Generic Repository Pattern** with a base model providing common functionality for all entities.

#### Class Diagram

<p align="left">
  <img src="docs/imgs/class_diagram_3.png" alt="Base Model and Repository Class Diagram" width="700"/>
</p>

#### BaseModel Features

1. **Automatic UUID Generation**: Every entity gets a unique UUID primary key
2. **Timestamps**: Automatic `created_at` and `updated_at` tracking
3. **Soft Delete**: `is_deleted` flag for logical deletion
4. **Serialization**: `to_dict()` for JSON conversion, `from_dict()` for deserialization
5. **String Representation**: Clean `__repr__()` for debugging

#### BaseRepository Features

1. **Generic CRUD Operations**: Works with any model type through TypeVar
2. **Soft Delete Support**: All queries exclude deleted records by default
3. **Bulk Operations**: `create_many()`, `update_many()`, `delete_many()`
4. **Query Helpers**: `exists()`, `count()`, `paginate()`
5. **Transaction Safety**: Automatic rollback on errors
6. **Hard Delete**: `hard_delete()` for permanent removal
7. **Restore**: `restore()` to recover soft-deleted records

#### Repository Pattern Flow

<p align="left">
  <img src="docs/imgs/sequence_diagram_4.png" alt="Repository Pattern Flow Sequence Diagram" width="700"/>
</p>

#### Benefits

1. **DRY Principle**: No repeated CRUD code across repositories
2. **Type Safety**: Generic typing provides IDE autocomplete and type checking
3. **Consistent Interface**: All repositories have the same methods
4. **Easy Testing**: Mock repositories for unit tests
5. **Data Recovery**: Soft delete allows data restoration
6. **Audit Trail**: Timestamps track creation and modification

---

## Database Schema (ERD)

<p align="left">
  <img src="docs/imgs/erd.png" alt="Entity Relationship Diagram" width="900"/>
</p>

### Key Relationships

1. **Polymorphic Inheritance**: `Person` is the base table for both `Criminal` and `MissingPerson`
2. **Crime Network**: `Crime` connects to `Criminal`, `Location`, `Reporter`, `CrimeVictim`, `Evidence`, and `Punishment`
3. **Identification**: `IdentificationSearch` produces multiple `IdentificationResult` objects matching persons
4. **Analysis Pipeline**: `CrimeAnalysis` generates `CrimeHotspot`, `CrimeTrend`, and `Recommendation`
5. **Alert System**: `CrimeHotspot` can trigger `AlertBroadcast` notifications

---

## System Diagrams

### High-Level Architecture

<p align="left">
  <img src="docs/imgs/High-Level_Architecture_diagram.png" alt="High-Level Architecture" width="800"/>
</p>

### Module Architecture

<p align="left">
  <img src="docs/imgs/Module_Architecture.png" alt="Module Architecture" width="800"/>
</p>

### Class Diagrams

#### Authentication Module

<p align="left">
  <img src="docs/imgs/class_diagram_4.png" alt="Authentication Module Class Diagram" width="700"/>
</p>

#### Crime Records Module

<p align="left">
  <img src="docs/imgs/class_diagram_5.png" alt="Crime Records Module Class Diagram" width="700"/>
</p>

#### Identification Module

<p align="left">
  <img src="docs/imgs/class_diagram_6.png" alt="Identification Module Class Diagram" width="700"/>
</p>

#### Crime Analysis Module

<p align="left">
  <img src="docs/imgs/class_diagram_7.png" alt="Crime Analysis Module Class Diagram" width="700"/>
</p>

### Sequence Diagrams

#### User Authentication Flow

<p align="left">
  <img src="docs/imgs/sequence_diagram_5.png" alt="User Authentication Flow Sequence Diagram" width="700"/>
</p>

#### Facial Recognition Search Flow

<p align="left">
  <img src="docs/imgs/sequence_diagram_6.png" alt="Facial Recognition Search Flow Sequence Diagram" width="700"/>
</p>

#### Crime Analysis & Hotspot Detection Flow

<p align="left">
  <img src="docs/imgs/sequence_diagram_7.png" alt="Crime Analysis Flow Sequence Diagram" width="700"/>
</p>

#### Criminal Record Creation Flow

<p align="left">
  <img src="docs/imgs/sequence_diagram_8.png" alt="Criminal Record Creation Flow Sequence Diagram" width="700"/>
</p>

---

## Installation

### Prerequisites

- Python 3.11+
- PostgreSQL 14+ with pgvector extension
- CUDA-capable GPU (optional, for faster facial recognition)
- Git

### Step 1: Clone the Repository

```bash
git clone https://github.com/kudzaiprichard/sentinel.git
cd sentinel
```

### Step 2: Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Install PostgreSQL pgvector Extension

```sql
-- Connect to your PostgreSQL database
CREATE EXTENSION IF NOT EXISTS vector;
```

### Step 5: Set Up Environment Variables

Create a `.env.development` file:

```bash
# Database
DATABASE_URI=postgresql://username:password@localhost:5432/sentinel_db
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# Security
SESSION_SECRET_KEY=your-secret-key-here
BCRYPT_ROUNDS=10

# Server
SERVER_IP=127.0.0.1
SERVER_PORT=5000
FLASK_DEBUG=true

# Google Gemini AI
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.0-flash-exp

# Email (Gmail SMTP)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# SMS (Twilio)
TWILIO_ACCOUNT_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_PHONE_NUMBER=+1234567890

# File Upload
UPLOAD_FOLDER_ROOT=uploads
MAX_FILE_SIZE_MB=10
```

### Step 6: Initialize Database

```bash
python -c "from src.config.factory import create_app; app = create_app(); app.app_context().push(); from src.shared.data.database import db; db.create_all(); print('Database initialized')"
```

### Step 7: Run the Application

```bash
python main.py
```

The application will be available at `http://127.0.0.1:5000`

---

## Configuration

### config.yaml Structure

```yaml
application:
  name: Sentinel Police Intelligence System
  version: 1.0.0

security:
  session_lifetime_minutes: 30
  bcrypt_rounds: ${BCRYPT_ROUNDS}
  session_secret_key: ${SESSION_SECRET_KEY}

database:
  uri: ${DATABASE_URI}
  pool_size: ${DB_POOL_SIZE}
  max_overflow: ${DB_MAX_OVERFLOW}

integrations:
  ai:
    provider: google
    api_key: ${GEMINI_API_KEY}
    model: ${GEMINI_MODEL}

  email:
    smtp_server: ${SMTP_SERVER}
    smtp_port: ${SMTP_PORT}
    username: ${SMTP_USERNAME}
    password: ${SMTP_PASSWORD}

  sms:
    provider: twilio
    account_sid: ${TWILIO_ACCOUNT_SID}
    auth_token: ${TWILIO_AUTH_TOKEN}
    phone_number: ${TWILIO_PHONE_NUMBER}

uploads:
  folder: ${UPLOAD_FOLDER_ROOT}
  max_size_mb: ${MAX_FILE_SIZE_MB}

logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: logs/sentinel.log
```

---

## Usage

### 1. User Authentication

```python
# Login
POST /login
{
  "email": "admin@example.com",
  "password": "your-password"
}

# Response: 200 OK + Session cookie
```

### 2. Create Criminal Record

```python
POST /criminals
Content-Type: multipart/form-data

{
  "first_name": "John",
  "last_name": "Doe",
  "date_of_birth": "1990-01-01",
  "gender": "male",
  "alias": "JD",
  "is_wanted": true,
  "threat_level": "high",
  "photo": <file>
}
```

### 3. Facial Recognition Search

```python
POST /identification/search
Content-Type: multipart/form-data

{
  "search_type": "image",
  "file": <image_file>
}

# Response: List of matches with similarity scores
```

### 4. Generate Crime Analysis

```python
POST /analysis
{
  "period_start": "2024-01-01",
  "period_end": "2024-12-31"
}

# Response: Analysis with hotspots, trends, and recommendations
```

---

## API Documentation

### Authentication Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/` | Login page and authentication |
| POST | `/logout` | User logout |
| GET/POST | `/register` | User registration |

### Criminal Records Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/criminals` | List/create criminals |
| GET | `/criminals/<id>` | View criminal details |
| POST | `/criminals/<id>/crimes` | Add crime to criminal |
| GET/POST | `/criminals/<id>/images` | Manage criminal photos |

### Missing Persons Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/missing-persons` | List/create missing persons |
| GET | `/missing-persons/<id>` | View missing person details |
| PUT | `/missing-persons/<id>/status` | Update missing person status |

### Identification Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/identification/search` | Create facial recognition search |
| GET | `/identification/results/<id>` | View search results |
| GET | `/identification/history` | View search history |

### Crime Analysis Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/analysis` | List crime analyses |
| POST | `/analysis` | Generate new analysis |
| GET | `/analysis/<id>` | View detailed analysis |
| GET | `/analysis/<id>/export` | Export analysis as PDF/JSON |

---

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -m 'Add new feature'`)
4. Push to the branch (`git push origin feature/new-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## Acknowledgments

- **InsightFace** for facial recognition capabilities
- **Google Gemini** for AI-powered analysis
- **scikit-learn** for clustering algorithms
- **Flask** and **SQLAlchemy** communities

---

## Contact

For questions or support, please contact:
- Email: kudzaiprichard@gmail.com
- GitHub Issues: [https://github.com/kudzaiprichard/sentinel/issues](https://github.com/kudzaiprichard/sentinel/issues)

---

**Built with Python, Flask, AI, and a commitment to public safety.**