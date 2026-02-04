# Technology Choices

This document explains the key technology decisions and library selections for the Highway Inventory Backend.

## Core Framework

### FastAPI

**Why**: Modern async Python framework with excellent performance and developer experience

**Key Benefits**:

- Automatic API documentation generation (Swagger UI, ReDoc)
- Native async/await support for I/O-bound operations
- Pydantic integration for request/response validation
- Type hints enable better IDE support and fewer runtime errors
- High performance comparable to Node.js and Go frameworks

**Use Cases in Project**:

- REST API endpoints with automatic validation
- Dependency injection for database sessions and authentication
- Background task support for async report generation
- WebSocket support (future feature for real-time updates)

## Database Stack

### PostgreSQL 15

**Why**: Robust relational database with excellent support for complex queries and data integrity

**Key Features Used**:

- ACID compliance for transactional integrity
- Advanced indexing for fast lookups on `tag_bim`, `id_interno`, `rut`
- JSON/JSONB support for flexible metadata (if needed in future)
- Geospatial extensions available (PostGIS) for future location features

### SQLAlchemy 2.0 (Async)

**Why**: Industry-standard ORM with async support for non-blocking database operations

**Benefits**:

- Async queries prevent blocking on database I/O
- Relationship management between entities
- Migration support through Alembic
- Protection against SQL injection
- Query optimization with lazy loading and eager loading strategies

**Pattern**: Using async session factory with context managers ensures proper connection cleanup

### Alembic

**Why**: Database migration management for version-controlled schema evolution

**Key Features**:

- Auto-generate migrations from SQLAlchemy models
- Rollback capability for safe deployments
- Migration history tracking
- Support for PostgreSQL enums and custom types

**Use Cases**:

- Tracked schema changes from development through production
- Safe deployment of database updates
- Team collaboration on schema modifications

## Data Validation

### Pydantic

**Why**: Data validation using Python type annotations with excellent error messages

**Benefits**:

- Request validation prevents invalid data from reaching business logic
- Response serialization ensures consistent API contracts
- Settings management with environment variable support
- Custom validators for business rules (RUT validation, date ranges)

**Pattern**: Separate request and response schemas ensure clear API boundaries

## Excel Processing

### xlsxwriter

**Why**: Write-optimized library for generating Excel files with advanced formatting

**Advantages Over Alternatives**:

- **Performance**: Significantly faster than openpyxl for write operations
- **Memory Efficiency**: Streams data without loading entire workbook in memory
- **Rich Formatting**: Support for colors, borders, fonts, merged cells, freeze panes
- **Image Embedding**: Insert photos directly into cells with precise positioning
- **Chart Support**: Generate charts and graphs (not currently used but available)

**Trade-off**: Write-only (cannot read Excel files)

**Use Cases in Project**:

- Asset inventory reports with optional photo embedding
- Multi-sheet installer analytics reports
- Custom formatted headers and column widths
- Professional reports for stakeholders

### openpyxl

**Why**: Read-optimized library for parsing uploaded Excel files

**Advantages**:

- **Read Excel Files**: Can load and parse existing `.xlsx` files
- **Read-Only Mode**: Optimized for reading large files without modification
- **Dynamic Column Detection**: Read headers and map to data dynamically

**Trade-off**: Slower write operations, higher memory usage

**Use Cases in Project**:

- KMZ report generation from uploaded Excel files
- Parsing user-submitted inventory data
- Validating required columns before processing

### Why Both Libraries?

**Strategic Decision**: Use the right tool for each operation

- **xlsxwriter** for all report generation (write operations)
- **openpyxl** for all Excel uploads (read operations)
- **Performance**: Each library optimized for its specific use case
- **Maintainability**: Clear separation of concerns

**Note**: Pandas is available in dependencies but not actively used. Direct Excel library usage provides better control over formatting and lower memory footprint for large reports.

## Image Processing

### Pillow (PIL)

**Why**: Comprehensive image manipulation library for photo optimization

**Features Used**:

- **Format Conversion**: RGBA/PNG to RGB/JPEG for consistency
- **Resizing**: Thumbnail generation with aspect ratio preservation
- **Optimization**: JPEG quality control (85%) and LANCZOS resampling
- **EXIF Data**: Extract GPS coordinates from photo metadata
- **Memory Buffers**: Process images without filesystem writes for Excel embedding

**User Impact**:

- Smaller file sizes reduce bandwidth for mobile apps
- Consistent image formats simplify client-side handling
- Embedded photos in Excel reports provide visual inventory verification
- Optimized images load faster in web dashboard

## Authentication & Security

### JWT (PyJWT)

**Why**: Stateless authentication for API scalability

**Benefits**:

- No server-side session storage required
- Token includes user metadata (role, email, RUT)
- Configurable expiration for security
- Easy to scale horizontally (no shared session state)

**Payload Structure**:

```json
{
  "user_name": "Juan Pérez",
  "user_rut": "12345678-9",
  "user_email": "juan@example.com",
  "user_role": "admin",
  "has_temporary_password": false,
  "exp": 1234567890
}
```

### Argon2

**Why**: Modern password hashing algorithm more secure than bcrypt

**Advantages**:

- Winner of Password Hashing Competition (2015)
- Memory-hard algorithm resists GPU/ASIC attacks
- Configurable time and memory costs
- Industry best practice for new applications

**Use Case**: All user passwords hashed with Argon2 before storage

## Email Services

### Resend

**Why**: Modern transactional email API with excellent deliverability

**Benefits**:

- Simple API for sending emails
- High deliverability rates
- Detailed logs and analytics
- Domain verification for professional emails

**Use Cases**:

- New user creation with temporary password
- Password reset flows
- System notifications

### Jinja2

**Why**: Powerful templating engine for HTML emails

**Features**:

- Template inheritance for consistent styling
- Variable interpolation for personalization
- Conditional rendering
- CSS inlining for email client compatibility

**Templates**:

- `email_on_create_user.html` - Welcome email with credentials
- `email_on_reset_password.html` - Password reset instructions

## Monitoring & Logging

### Sentry

**Why**: Real-time error tracking and performance monitoring

**Benefits**:

- Automatic exception capture with stack traces
- User context for debugging (which user encountered error)
- Performance monitoring for slow endpoints
- Release tracking for correlating errors with deployments

### Graylog Integration (graypy)

**Why**: Centralized log aggregation for production troubleshooting

**Benefits**:

- Structured logging with JSON format
- Search and filter logs across multiple services
- Retention policies for compliance
- Real-time log streaming

## Deployment

### Docker

**Why**: Containerization for consistent environments from development to production

**Benefits**:

- Eliminates "works on my machine" issues
- Simplified deployment process
- Easy local development setup
- Resource isolation

**Services**:

- PostgreSQL container with persistent volumes
- API container with health checks
- Nginx reverse proxy (production)

### Docker Compose

**Why**: Multi-container orchestration for local development and simple deployments

**Features**:

- Define all services in one configuration file
- Automatic network creation between containers
- Volume management for data persistence
- Environment variable management

## Bridging the Gap

### User-Friendly Features

The technology choices specifically address the needs of both field workers and office administrators:

**For Field Workers**:

- **Photo Optimization**: Reduced bandwidth for mobile uploads in remote areas
- **Base64 Encoding**: Photos embedded in API responses for offline access
- **Bulk Operations**: Sync large datasets efficiently when back online
- **Barcode Lookup**: Fast asset identification without authentication overhead

**For Office Staff**:

- **Excel Reports**: Familiar format for non-technical users
- **Photo Embedding**: Visual verification without separate image files
- **KMZ Export**: Google Earth integration for geospatial analysis
- **Email Notifications**: Automated communication for user management

**Technical Bridge**:

- **Async Processing**: Large reports don't block system for other users
- **Task Tracking**: Transparent progress for long-running operations
- **Error Handling**: Clear error messages in Spanish for local teams
- **Soft Deletes**: Preserve audit trail while allowing data cleanup

These technology choices enable a system that serves both mobile field workers with limited connectivity and office administrators who need comprehensive reporting and analysis capabilities.
