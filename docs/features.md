# Features

This document outlines the main features and capabilities of the Highway Inventory Backend.

## Asset Management

### Core Operations

- **Create Assets**: Single and bulk creation with automatic conflict detection
- **Update Assets**: Modify asset details with version tracking for sync conflict resolution
- **Soft Delete**: Mark assets as "retirado" (retired) instead of hard deletion for audit trail
- **Filtering & Pagination**: Query assets by date range, status, element type, contract, and location
- **Lookup by BIM Tag**: Public endpoint for mobile barcode scanning without authentication

### Bulk Import

- **Batch Processing**: Import up to 200 assets per request
- **Conflict Resolution**: Automatic detection of duplicate `id_interno` values
- **Conflictive Assets Table**: Stores assets with constraint violations separately for manual review
- **Individual Failure Handling**: One failed asset doesn't rollback the entire batch

### Versioning

Each asset maintains a `version` field that increments on updates, enabling:

- Mobile app sync conflict detection
- Offline-first mobile workflows
- Last-write-wins resolution strategy

## Photo Management

### Upload & Processing

- **Single Photo Upload**: Attach photos during asset creation/update
- **Bulk Photo Upload**: Associate photos with multiple existing assets in one request
- **Format Support**: JPEG, PNG with automatic conversion and optimization
- **Validation**: File extension, size, and format checks
- **Filesystem Storage**: Photos saved with naming convention `{id_interno}_{timestamp}.jpg`

### Optimization

- **Automatic Resizing**: Large images resized for efficient storage and transmission
- **JPEG Compression**: 85% quality with LANCZOS resampling for optimal balance
- **RGBA Handling**: Transparent images converted to RGB with white background
- **Mobile Base64 Encoding**: Photos returned as base64 strings for offline mobile apps

### Photo Embedding in Reports

- Photos can be embedded in Excel reports
- Resized to 150x150px maximum for report optimization
- Excel row height automatically adjusted to fit images
- Each photo positioned with proper offsets and alignment

## Mobile Synchronization

### Offline-First Architecture

The API supports mobile apps that collect data offline and sync when connected:

- **Sync Endpoint**: `POST /v1/assets/sync` accepts arrays of assets
- **Version-Based Conflicts**: Compares version numbers to detect concurrent modifications
- **Batch Response**: Returns counts of created, updated, and conflictive assets
- **Master Data Endpoint**: Single endpoint to fetch all reference data (element types, installers, contracts)

### Public Barcode Lookup

- **No Authentication Required**: Field workers can scan barcodes without login
- **Base64 Photo Response**: Photo embedded in response for offline viewing
- **Status Filtering**: Retired assets return 402 status to prevent scanning old inventory

## Excel Report Generation

### Standard Asset Reports

- **Async Processing**: Large reports generated in background to avoid timeouts
- **Task Tracking**: Each report gets a unique task ID for status checking and download
- **Date Range Filtering**: Export assets created within specific date ranges (max 90 days)
- **Element Type Filtering**: Filter by asset categories (signs, barriers, markings)
- **Status Filtering**: Include/exclude retired assets
- **Photo Embedding**: Optional inclusion of asset photos resized to 150x150px
- **Custom Formatting**: Headers with colors, borders, freeze panes, auto-column widths
- **Chilean Timezone**: Timestamps formatted for local timezone

### Installer Analytics Reports

- **Multi-Sheet Workbook**: One sheet per installer
- **Statistics Per Installer**:
  - Total assets installed
  - Date of last installation
  - Maximum time between installations
- **Sorted by Creation**: Assets ordered chronologically
- **Formatted Output**: Professional Excel styling for stakeholders

### Report Lifecycle

1. **Request**: Submit report parameters to `/v1/assets/report/excel`
2. **Background Task**: Report generation starts with task ID returned
3. **Status Check**: Poll `/v1/assets/report/excel/{task_id}/status` for completion
4. **Download**: Retrieve completed report from `/v1/assets/report/excel/{task_id}/download`
5. **Auto-Cleanup**: Reports expire after 1 hour to manage disk space

## KMZ Geospatial Reports

### Google Earth Export

Generate KMZ files for visualization in Google Earth with two modes:

**Mode 1: Database Query**

- Filter by date range and contract project
- Fetch georeferenced assets from database
- Parse coordinates in format: `"lat, lon, altm"` (e.g., `-30.002523, -71.329657, 159.60m`)
- Generate KML placemarks with asset metadata

**Mode 2: Excel Upload**

- Upload `.xlsx` file with columns: `ID Interno`, `Elemento`, `Georeferenciación`
- Parse Excel data using openpyxl
- Validate required columns
- Convert to KML format with placemarks

**Output**:

- KML XML with placemarks for each asset
- ZIP compressed to `.kmz` format
- Downloadable file for Google Earth import

### Use Cases

- Visualize asset distribution across highway segments
- Plan maintenance routes
- Identify gaps in inventory coverage
- Share geospatial data with MOP stakeholders

## User Management

### CRUD Operations

- **Create Users**: Admin-only with email notification containing temporary password
- **Update Users**: Modify user details, roles, verification status
- **Soft Delete**: Deactivate users without losing audit history
- **List Users**: Paginated with filtering by role, verification status

### Authentication & Security

- **JWT Authentication**: Token-based authentication with configurable expiration
- **Argon2 Password Hashing**: More secure than bcrypt for password storage
- **Role-Based Access**: Admin vs Regular user permissions
- **Temporary Passwords**: Flag for forced password change on first login

### Email Notifications

- **User Creation**: HTML email with temporary password and login instructions
- **Password Reset**: Secure password reset flow with email verification
- **Jinja2 Templates**: Professional HTML emails with consistent styling

## Background Task Processing

### Async Report Manager

- **Task Queue**: Manages concurrent report generation
- **Status Tracking**: PENDING → COMPLETED/FAILED states tracked via filesystem markers
- **Concurrent Limit**: Prevents system overload (currently 1 concurrent report)
- **Expiration**: Automatic cleanup of reports older than 1 hour
- **Error Handling**: Failed reports logged with detailed error information

### Benefits

- Non-blocking API responses for large reports
- Better user experience (poll for completion rather than timeout)
- Resource management on server
- Scalable for multiple simultaneous report requests

## Master Data Management

### Reference Data Endpoint

**Single Endpoint**: `GET /v1/master-data/` returns all reference data in one request

**Included Data**:

- Element types (asset categories)
- Installers (companies/personnel)
- Contract projects
- Macro locations (geographic zones)

**Purpose**:

- Populate mobile app dropdowns
- Reduce API calls (one request vs four)
- Ensure data consistency across clients

### CRUD Operations

Each master data type supports:

- Create new entries
- Update existing entries
- Soft delete (maintain referential integrity)
- List with pagination and active/inactive filtering

## Conflict Detection & Resolution

### Unique Constraint Handling

During bulk imports, the system detects conflicts on:

- `id_interno` (internal ID, must be unique)
- `tag_bim` (MOP BIM identifier, optional but unique if present)

**Resolution Strategy**:

- Valid assets inserted into `assets` table
- Conflicting assets stored in `conflictive_assets` table
- Response includes counts of successful and failed insertions
- Admin can review and manually resolve conflicts

### Version Conflicts (Mobile Sync)

When mobile app submits asset updates:

- Server compares submitted version with database version
- If versions match: update proceeds, version increments
- If versions differ: conflict detected, asset marked as conflictive
- Mobile app receives conflict notification for user resolution

This ensures data integrity when multiple users work offline on the same assets.
