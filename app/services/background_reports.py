from datetime import datetime
from typing import Optional

from app.db.database import SessionLocal
from app.crud.asset import get_assets_by_datetime_range
from app.crud.contract_project import get_contract_project_by_id_or_nombre
from app.crud.element_type import get_element_type_by_id_or_nombre
from app.services.asset_report import generate_excel_report
from app.utils.async_report_manager import (
    mark_report_completed,
    mark_report_failed,
    cleanup_old_reports,
)
from app.utils.logger import logger_instance as log
from app.enums.enums import AssetStatus


async def generate_excel_report_background(
    task_id: str,
    contract_name: str,
    fecha_desde: datetime,
    fecha_hasta: datetime,
    include_photos: bool,
    element_type: Optional[str] = None,
    asset_status: Optional[AssetStatus] = None,
):
    """
    Background task to generate Excel report asynchronously.

    This function runs outside the main HTTP request cycle, using a new database session.
    It updates the task status files as it progresses.

    Args:
        task_id: Unique task identifier
        contract_name: Name of the contract to filter assets
        fecha_desde: Start datetime (already validated and converted to UTC)
        fecha_hasta: End datetime (already validated and converted to UTC)
        include_photos: Whether to include photos in the report
        element_type: Optional element type name to filter assets
        asset_status: Optional asset status to filter assets
    """
    log.info(
        f"Starting background Excel report generation",
        extra={
            "task_id": task_id,
            "contract_name": contract_name,
            "fecha_desde": fecha_desde.isoformat(),
            "fecha_hasta": fecha_hasta.isoformat(),
            "include_photos": include_photos,
            "element_type": element_type,
            "asset_status": asset_status.value if asset_status else None,
        },
    )

    cleanup_old_reports()

    async with SessionLocal() as db:
        try:
            contract_project = await get_contract_project_by_id_or_nombre(
                db=db,
                nombre=contract_name,
            )

            if not contract_project:
                error_msg = f"Proyecto de contrato '{contract_name}' no encontrado"
                log.error(
                    f"Contract project not found",
                    extra={"task_id": task_id, "contract_name": contract_name},
                )
                mark_report_failed(task_id, error_msg)
                return

            element_type_obj = None
            if element_type is not None:
                element_type_obj = await get_element_type_by_id_or_nombre(
                    db=db,
                    nombre=element_type,
                )
                if not element_type_obj:
                    error_msg = f"Tipo de elemento '{element_type}' no encontrado"
                    log.error(
                        f"Element type not found",
                        extra={"task_id": task_id, "element_type": element_type},
                    )
                    mark_report_failed(task_id, error_msg)
                    return

            log.info(
                f"Fetching assets for report",
                extra={
                    "task_id": task_id,
                    "contract_project_id": contract_project.id,
                },
            )

            assets = await get_assets_by_datetime_range(
                db=db,
                contract_project_id=contract_project.id,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                element_type_id=element_type_obj.id if element_type_obj else None,
                asset_status=asset_status,
            )

            log.info(
                f"Assets fetched, generating Excel file",
                extra={
                    "task_id": task_id,
                    "asset_count": len(assets),
                },
            )

            excel_buffer = generate_excel_report(
                assets=assets,
                include_photos=include_photos,
            )

            file_content = excel_buffer.getvalue()
            success = mark_report_completed(task_id, file_content)

            if success:
                log.info(
                    f"Excel report generated successfully",
                    extra={
                        "task_id": task_id,
                        "file_size_bytes": len(file_content),
                        "asset_count": len(assets),
                    },
                )
            else:
                error_msg = "Error al guardar el archivo del reporte"
                log.error(
                    f"Failed to save report file",
                    extra={"task_id": task_id},
                )
                mark_report_failed(task_id, error_msg)

        except Exception as e:
            error_msg = f"Error interno al generar el reporte: {str(e)}"
            log.error(
                f"Exception during Excel report generation",
                extra={
                    "task_id": task_id,
                    "error_type": type(e).__name__,
                    "error": str(e),
                },
                exc_info=True,
            )
            mark_report_failed(task_id, error_msg)


async def generate_installers_excel_report_background(
    task_id: str,
    contract_name: str,
    fecha_desde: datetime,
    fecha_hasta: datetime,
    element_type: Optional[str] = None,
    asset_status: Optional[AssetStatus] = None,
):
    """
    Background task to generate installers Excel report asynchronously.

    Args:
        task_id: Unique task identifier
        contract_name: Name of the contract to filter assets
        fecha_desde: Start datetime (already validated and converted to UTC)
        fecha_hasta: End datetime (already validated and converted to UTC)
        element_type: Optional element type name to filter assets
    """
    log.info(
        f"Starting background installers Excel report generation",
        extra={
            "task_id": task_id,
            "contract_name": contract_name,
            "fecha_desde": fecha_desde.isoformat(),
            "fecha_hasta": fecha_hasta.isoformat(),
            "element_type": element_type,
        },
    )

    cleanup_old_reports()

    from app.services.asset_report import generate_installers_excel_report

    async with SessionLocal() as db:
        try:
            contract_project = await get_contract_project_by_id_or_nombre(
                db=db,
                nombre=contract_name,
            )

            if not contract_project:
                error_msg = f"Proyecto de contrato '{contract_name}' no encontrado"
                log.error(
                    f"Contract project not found",
                    extra={"task_id": task_id, "contract_name": contract_name},
                )
                mark_report_failed(task_id, error_msg)
                return

            element_type_obj = None
            if element_type is not None:
                element_type_obj = await get_element_type_by_id_or_nombre(
                    db=db,
                    nombre=element_type,
                )
                if not element_type_obj:
                    error_msg = f"Tipo de elemento '{element_type}' no encontrado"
                    log.error(
                        f"Element type not found",
                        extra={"task_id": task_id, "element_type": element_type},
                    )
                    mark_report_failed(task_id, error_msg)
                    return

            assets = await get_assets_by_datetime_range(
                db=db,
                contract_project_id=contract_project.id,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                element_type_id=element_type_obj.id if element_type_obj else None,
                asset_status=asset_status,
            )

            log.info(
                f"Assets fetched, generating installers Excel file",
                extra={
                    "task_id": task_id,
                    "asset_count": len(assets),
                },
            )

            excel_buffer = generate_installers_excel_report(assets=assets)

            file_content = excel_buffer.getvalue()
            success = mark_report_completed(task_id, file_content)

            if success:
                log.info(
                    f"Installers Excel report generated successfully",
                    extra={
                        "task_id": task_id,
                        "file_size_bytes": len(file_content),
                        "asset_count": len(assets),
                    },
                )
            else:
                error_msg = "Error al guardar el archivo del reporte"
                log.error(
                    f"Failed to save installers report file",
                    extra={"task_id": task_id},
                )
                mark_report_failed(task_id, error_msg)

        except Exception as e:
            error_msg = f"Error interno al generar el reporte: {str(e)}"
            log.error(
                f"Exception during installers Excel report generation",
                extra={
                    "task_id": task_id,
                    "error_type": type(e).__name__,
                    "error": str(e),
                },
                exc_info=True,
            )
            mark_report_failed(task_id, error_msg)
