# Architecture Overview

This document describes the layered architecture and design patterns used in the Highway Inventory Backend.

## Layered Architecture

The application follows a **domain-bounded layered architecture** that separates concerns and promotes maintainability. Each layer has a specific responsibility and communicates through well-defined interfaces.

### API Layer (`app/api/`)

**Purpose**: HTTP request handling and response formatting

**Structure**:

- `app/api/public/v1/` - Public endpoints (no authentication required)
  - Login endpoint for JWT token issuance
  - Asset lookup by BIM tag for mobile barcode scanning
- `app/api/v1/` - Protected endpoints (JWT authentication required)
  - Asset CRUD operations
  - Report generation
  - User management
  - Master data endpoints
- `app/api/deps.py` - Dependency injection for database sessions and authentication

**Responsibilities**:

- Route definition and HTTP method handling
- Request validation using Pydantic schemas
- Authentication and authorization checks
- Response serialization
- Error handling and HTTP status codes

### CRUD Layer (`app/crud/`)

**Purpose**: Database operation abstractions

**Modules**:

- `asset.py` - Asset entity operations (create, read, update, soft delete, bulk operations)
- `conflictive_asset.py` - Duplicate asset handling
- `user.py` - User management operations
- `contract_project.py` - Contract/project operations
- `element_type.py` - Asset type catalog operations
- `installer.py` - Installer entity operations
- `macro_location.py` - Geographic zone operations

**Responsibilities**:

- SQLAlchemy query construction
- Transaction management
- Bulk insert/update operations with conflict resolution
- Pagination logic
- Database-level filtering and sorting

**Pattern**: Each CRUD module follows a consistent interface with methods like `create()`, `get()`, `get_multi()`, `update()`, `delete()`.

### Services Layer (`app/services/`)

**Purpose**: Business logic and complex operations

**Modules**:

- `asset_report.py` - Excel and KMZ report generation
- `background_reports.py` - Async report task management
- `photo_upload.py` - Photo processing and optimization
- `email.py` - Email notification orchestration

**Responsibilities**:

- Multi-step business processes
- File generation (Excel, KMZ)
- Image processing and optimization
- Email composition and delivery
- Background task coordination
- External API integration

**Pattern**: Services orchestrate multiple CRUD operations and apply domain-specific business rules.

### Models Layer (`app/models/`)

**Purpose**: Database schema definition using SQLAlchemy ORM

**Entities**:

- `Asset` - Highway infrastructure assets (signs, barriers, markings)
- `ConflictiveAsset` - Assets with unique constraint violations during bulk imports
- `User` - System users with role-based access
- `ContractProject` - Projects and contracts grouping assets
- `ElementType` - Asset categorization (catalog)
- `Installer` - Personnel or companies who installed assets
- `MacroLocation` - Geographic zones with kilometer ranges

**Features**:

- UTC timestamp mixin for `created_at` and `updated_at` fields
- Soft delete support with `activo` boolean flag
- Relationships and foreign keys
- Indexes on frequently queried fields
- Enums for status, roles, and categories

### Schemas Layer (`app/schemas/`)

**Purpose**: Request/response validation and API contracts using Pydantic

**Categories**:

- Request schemas (e.g., `AssetCreate`, `UserCreate`) - Validate incoming data
- Response schemas (e.g., `AssetResponse`, `UserResponse`) - Define API responses
- Shared schemas (e.g., `PaginatedResponse`) - Reusable pagination structure

**Features**:

- Type validation and coercion
- Custom validators for business rules (e.g., RUT validation, date ranges)
- Field aliases for snake_case/camelCase conversion
- Computed fields
- ORM mode for SQLAlchemy model serialization

### Core Layer (`app/core/`)

**Purpose**: Cross-cutting concerns and infrastructure

**Modules**:

- `config.py` - Environment configuration using Pydantic Settings
- `security.py` - JWT generation/validation, Argon2 password hashing, role verification
- `exception_handlers.py` - Global exception handling and HTTP error responses
- `email.py` - Email client configuration (Resend API)

**Responsibilities**:

- Application configuration management
- Authentication and authorization logic
- Security utilities (token management, password hashing)
- Global error handling
- Logging configuration

### Database Layer (`app/db/`)

**Purpose**: Database connection and session management

**Modules**:

- `database.py` - Async SQLAlchemy engine and session factory
- `base_class.py` - Base model class with common fields
- `base.py` - Import all models for Alembic migration detection

**Features**:

- Async connection pooling with pre-ping for connection health checks
- Session lifecycle management
- Database URL configuration
- Migration support through Alembic

## Domain-Bounded Contexts

The application is organized around these business domains:

- **Assets Domain** - Core inventory management (primary functionality)
- **Users Domain** - Authentication, authorization, user lifecycle
- **Contracts Domain** - Project and contract organization
- **Catalog Domain** - Element types, installers (reference data)
- **Locations Domain** - Geographic segmentation (macro locations)
- **Reports Domain** - Excel and geospatial report generation

Each domain has its own model, schema, CRUD operations, and endpoints, promoting modularity and independent evolution.

## Design Patterns

- **Dependency Injection** - Database sessions and auth dependencies injected into endpoints
- **Repository Pattern** - CRUD layer abstracts database operations
- **Service Layer Pattern** - Complex business logic separated from API and data access
- **DTO Pattern** - Pydantic schemas act as Data Transfer Objects
- **Factory Pattern** - Session factory for database connections
- **Decorator Pattern** - SQLAlchemy error handler decorator for consistent error handling

## Data Flow Example

**Creating an Asset with Photo**:

1. **API Layer** receives POST request at `/v1/assets/`
2. **Dependency** validates JWT token and injects database session
3. **Schema** validates request body (Pydantic `AssetCreate`)
4. **Service** processes photo upload (resize, optimize, save to filesystem)
5. **CRUD** inserts asset record into database with photo filename
6. **Model** defines table structure and relationships
7. **API Layer** returns response (Pydantic `AssetResponse` with HTTP 201)

This layered approach ensures each component has a single responsibility and can be tested independently.
