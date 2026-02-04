# Highway Inventory Backend

A production FastAPI backend for highway asset inventory management, developed as a freelance project for an organization modernizing their highway catalog infrastructure in collaboration with MOP (Ministerio de Obras Públicas de Chile). This system is currently deployed and actively serving field operations across various highway networks.

## Project Overview

This backend API manages the complete lifecycle of highway infrastructure assets (traffic signs, barriers, road markings, etc.) with support for field mobile applications, photo documentation, geolocation tracking, and comprehensive reporting capabilities. The architecture enables offline-first mobile data collection that synchronizes with the central database, bridging the gap between field workers and administrative personnel.

## Architecture

The application follows a **domain-bounded layered architecture** with clear separation of concerns:

- **API Layer** (`app/api/`) - REST endpoints with public and authenticated (v1) routes
- **CRUD Layer** (`app/crud/`) - Database operation abstractions
- **Services Layer** (`app/services/`) - Business logic, report generation, background tasks
- **Models Layer** (`app/models/`) - SQLAlchemy ORM models with domain entities
- **Schemas Layer** (`app/schemas/`) - Pydantic validation models for API contracts
- **Core Layer** (`app/core/`) - Configuration, security, exception handling

**Domain Contexts**: Assets, Users, Contract Projects, Element Types, Installers, Macro Locations, Conflictive Assets

For detailed architecture information, see [docs/architecture.md](docs/architecture.md).

## Technology Stack

- **Framework**: FastAPI 0.119.0 with async support
- **Database**: PostgreSQL 15 with asyncpg driver
- **ORM**: SQLAlchemy 2.0.36 (async)
- **Migrations**: Alembic 1.13.3
- **Validation**: Pydantic 2.12.3
- **Authentication**: JWT with Argon2 password hashing
- **Excel Processing**: xlsxwriter (write optimization), openpyxl (read operations)
- **Image Processing**: Pillow for photo optimization and embedding
- **Email**: Resend with Jinja2 templates
- **Monitoring**: Sentry for error tracking, Graylog integration
- **Deployment**: Docker + Docker Compose

See [docs/technologies.md](docs/technologies.md) for technology justifications and use cases.

## Key Features

- **Asset Management**: CRUD operations with versioning, bulk imports, conflict resolution
- **Photo Management**: Optimized upload, validation, resizing, and embedding in Excel reports
- **Mobile Synchronization**: Offline-first mobile app support with version-based conflict detection
- **Excel Reports**: Async generation with optional photo embedding, date filtering, multi-sheet analytics
- **KMZ Geospatial Reports**: Generate Google Earth files from database queries or uploaded Excel files
- **User Management**: Role-based access control (Admin/Regular), email notifications
- **Background Tasks**: Async report processing with task tracking and automatic cleanup

For detailed feature descriptions, see [docs/features.md](docs/features.md).

## API Documentation

The API includes auto-generated interactive documentation:

- **Swagger UI**: Available at `/docs` when running locally
- **ReDoc**: Available at `/redoc` when running locally

**Endpoints Structure**:

- `POST /public/v1/login` - JWT authentication
- `GET /public/v1/assets/tag-bim/{tag}` - Public asset lookup for mobile barcode scanning
- `GET /v1/assets/` - Paginated asset listing with filters (authenticated)
- `POST /v1/assets/bulk/` - Bulk asset creation with conflict handling
- `POST /v1/assets/photos/bulk/` - Bulk photo upload
- `POST /v1/assets/report/excel` - Generate Excel report (async)
- `POST /v1/assets/report/kmz` - Generate KMZ geospatial report
- `GET /v1/master-data/` - Reference data for mobile apps

## Related Projects

This backend serves multiple client applications:

- **React Frontend** (Web Dashboard): [GitHub Repository](https://github.com) _(link pending)_
- **Mobile Application** (Field Data Collection): [GitHub Repository](https://github.com) _(link pending)_

## Development Setup

```bash
# Clone repository
git clone <repository-url>
cd highway-inventory-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.local.txt

# Configure environment
cp .env.example .env  # Edit with your settings

# Run migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload
```

**Docker Setup**:

```bash
# Build and run containers
docker-compose up -d

# Check logs
docker-compose logs -f api
```

## Production Status

**This project is currently in production** and actively used for highway infrastructure management. It is **not intended for public use or distribution**.

## License

Copyright © 2026. All rights reserved.

This software is proprietary and confidential. Unauthorized copying, modification, distribution, or use of this code is strictly prohibited without explicit written authorization.

---

**Author**: Daniel Bassano
