import uuid
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional
from enum import Enum

from app.utils.logger import logger_instance as log

TEMP_REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "temp_reports"

REPORT_EXPIRATION_HOURS = 1
MAX_CONCURRENT_REPORTS = 1


class ReportStatus(str, Enum):
    """Report generation status"""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


def ensure_temp_reports_dir() -> Path:
    """
    Ensure the temp_reports directory exists.

    Returns:
        Path to temp_reports directory
    """
    TEMP_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return TEMP_REPORTS_DIR


def generate_task_id() -> str:
    """
    Generate a unique task ID using UUID4.

    Returns:
        Task ID as string (UUID)
    """
    return str(uuid.uuid4())


def get_report_path(task_id: str, status: ReportStatus) -> Path:
    """
    Get the file path for a report based on its task_id and status.

    Args:
        task_id: Unique task identifier
        status: Current status of the report

    Returns:
        Path to the report file
    """
    ensure_temp_reports_dir()

    if status == ReportStatus.PENDING:
        return TEMP_REPORTS_DIR / f"{task_id}.pending"
    elif status == ReportStatus.COMPLETED:
        return TEMP_REPORTS_DIR / f"{task_id}.xlsx"
    elif status == ReportStatus.FAILED:
        return TEMP_REPORTS_DIR / f"{task_id}.failed"
    else:
        raise ValueError(f"Invalid report status: {status}")


def create_pending_report(task_id: str) -> bool:
    """
    Create a pending marker file for a new report task.

    Args:
        task_id: Unique task identifier

    Returns:
        True if created successfully, False otherwise
    """
    try:
        pending_path = get_report_path(task_id, ReportStatus.PENDING)
        pending_path.touch()
        log.info(
            f"Created pending report marker",
            extra={"task_id": task_id, "path": str(pending_path)},
        )
        return True
    except Exception as e:
        log.error(
            f"Failed to create pending report marker",
            extra={"task_id": task_id, "error": str(e)},
            exc_info=True,
        )
        return False


def mark_report_completed(task_id: str, file_content: bytes) -> bool:
    """
    Mark a report as completed by saving the Excel file and removing pending marker.

    Args:
        task_id: Unique task identifier
        file_content: Binary content of the Excel file

    Returns:
        True if marked successfully, False otherwise
    """
    try:
        pending_path = get_report_path(task_id, ReportStatus.PENDING)
        completed_path = get_report_path(task_id, ReportStatus.COMPLETED)

        with open(completed_path, "wb") as f:
            f.write(file_content)

        if pending_path.exists():
            pending_path.unlink()

        log.info(
            f"Marked report as completed",
            extra={
                "task_id": task_id,
                "file_size": len(file_content),
                "path": str(completed_path),
            },
        )
        return True
    except Exception as e:
        log.error(
            f"Failed to mark report as completed",
            extra={"task_id": task_id, "error": str(e)},
            exc_info=True,
        )
        return False


def mark_report_failed(task_id: str, error_message: str = "") -> bool:
    """
    Mark a report as failed by creating a failed marker and removing pending marker.

    Args:
        task_id: Unique task identifier
        error_message: Optional error message to store

    Returns:
        True if marked successfully, False otherwise
    """
    try:
        pending_path = get_report_path(task_id, ReportStatus.PENDING)
        failed_path = get_report_path(task_id, ReportStatus.FAILED)

        with open(failed_path, "w") as f:
            f.write(error_message or "Report generation failed")

        if pending_path.exists():
            pending_path.unlink()

        log.warning(
            f"Marked report as failed",
            extra={"task_id": task_id, "error_message": error_message},
        )
        return True
    except Exception as e:
        log.error(
            f"Failed to mark report as failed",
            extra={"task_id": task_id, "error": str(e)},
            exc_info=True,
        )
        return False


def get_report_status(task_id: str) -> tuple[ReportStatus | None, Optional[str]]:
    """
    Get the current status of a report task.

    Args:
        task_id: Unique task identifier

    Returns:
        Tuple of (status, message)
        - status: ReportStatus enum or None if not found
        - message: Human-readable message
    """
    pending_path = get_report_path(task_id, ReportStatus.PENDING)
    completed_path = get_report_path(task_id, ReportStatus.COMPLETED)
    failed_path = get_report_path(task_id, ReportStatus.FAILED)

    if completed_path.exists():
        return ReportStatus.COMPLETED, "Reporte listo para descargar"
    elif pending_path.exists():
        return ReportStatus.PENDING, "Generando reporte, por favor espere..."
    elif failed_path.exists():
        try:
            with open(failed_path, "r") as f:
                error_msg = f.read()
            return ReportStatus.FAILED, error_msg or "Error al generar el reporte"
        except Exception:
            return ReportStatus.FAILED, "Error al generar el reporte"
    else:
        return None, "Reporte no encontrado o expirado"


def count_pending_reports() -> int:
    """
    Count the number of reports currently being generated (pending status).

    Returns:
        Number of pending reports
    """
    ensure_temp_reports_dir()
    pending_files = list(TEMP_REPORTS_DIR.glob("*.pending"))
    return len(pending_files)


def can_start_new_report() -> tuple[bool, Optional[str]]:
    """
    Check if a new report generation can be started based on concurrency limits.

    Returns:
        Tuple of (can_start, reason)
        - can_start: True if a new report can be started
        - reason: Reason why it cannot start (if can_start is False)
    """
    current_pending = count_pending_reports()

    if current_pending >= MAX_CONCURRENT_REPORTS:
        return (
            False,
            f"Ya hay {current_pending} reporte(s) generándose. Por favor intente en unos minutos.",
        )

    return True, None


def cleanup_old_reports() -> int:
    """
    Remove report files older than REPORT_EXPIRATION_HOURS.

    Returns:
        Number of files deleted
    """
    ensure_temp_reports_dir()

    now = datetime.now(timezone.utc)
    expiration_time = now - timedelta(hours=REPORT_EXPIRATION_HOURS)
    deleted_count = 0

    try:
        for file_path in TEMP_REPORTS_DIR.glob("*"):
            if file_path.is_file():
                file_mtime = datetime.fromtimestamp(
                    file_path.stat().st_mtime, tz=timezone.utc
                )

                if file_mtime < expiration_time:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                        log.info(
                            f"Deleted expired report file",
                            extra={
                                "file": file_path.name,
                                "age_hours": (now - file_mtime).total_seconds() / 3600,
                            },
                        )
                    except Exception as e:
                        log.error(
                            f"Failed to delete expired report file",
                            extra={"file": file_path.name, "error": str(e)},
                        )

        if deleted_count > 0:
            log.info(
                f"Cleanup completed",
                extra={"deleted_files": deleted_count},
            )

    except Exception as e:
        log.error(
            f"Error during cleanup",
            extra={"error": str(e)},
            exc_info=True,
        )

    return deleted_count


def get_report_file_path(task_id: str) -> Optional[Path]:
    """
    Get the path to a completed report file if it exists.

    Args:
        task_id: Unique task identifier

    Returns:
        Path to the Excel file if it exists, None otherwise
    """
    completed_path = get_report_path(task_id, ReportStatus.COMPLETED)
    if completed_path.exists():
        return completed_path
    return None
