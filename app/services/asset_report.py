from io import BytesIO
from typing import List, Optional, Tuple, Dict, Any
import xlsxwriter
from pathlib import Path
from PIL import Image
import pytz
import zipfile
import re

from app.models.asset import Asset
from app.core.config import ASSET_PHOTOS_DIR
from app.utils.logger import logger_instance as log


PHOTO_MAX_WIDTH = 150  # pixels
PHOTO_MAX_HEIGHT = 150  # pixels
EXCEL_ROW_HEIGHT = 115  # Excel row height in points (roughly 150px)


def _parse_georef(georef: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Parse georeferenciacion string to extract latitude and longitude.

    Args:
        georef: Georeferenciacion string in format "lat, lon, altm"
                (e.g., "-30.002523, -71.329657, 159.60m")

    Returns:
        Tuple of (latitude, longitude) as floats, or (None, None) if invalid
    """
    if not georef:
        return None, None
    try:
        match = re.findall(r"-?\d+\.\d+", georef)
        if len(match) >= 2:
            return float(match[0]), float(match[1])
    except (ValueError, IndexError) as e:
        log.warning(
            "Error parsing georeferenciacion",
            extra={"georef": georef, "error": str(e)},
        )
    return None, None


def _escape_xml(text: str) -> str:
    """
    Escape special characters for XML/KML validity.

    Args:
        text: Text to escape

    Returns:
        Escaped text safe for XML/KML
    """
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _resize_image(
    image_path: Path, max_width: int, max_height: int
) -> Optional[BytesIO]:
    """
    Resize image to fit within max dimensions while maintaining aspect ratio.

    Args:
        image_path: Path to the image file
        max_width: Maximum width in pixels
        max_height: Maximum height in pixels

    Returns:
        BytesIO buffer containing the resized image, or None if error
    """
    try:
        with Image.open(image_path) as img:
            if img.mode in ("RGBA", "LA", "P"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                background.paste(
                    img,
                    mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None,
                )
                img = background
            elif img.mode != "RGB":
                img = img.convert("RGB")

            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=85, optimize=True)
            buffer.seek(0)

            return buffer

    except Exception as e:
        log.error(
            "Error resizing image for Excel report",
            extra={
                "image_path": str(image_path),
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        return None


def generate_excel_report(assets: List[Asset], include_photos: bool = False) -> BytesIO:
    """
    Generate an Excel report from a list of Asset objects.

    Args:
        assets: List of Asset model instances with loaded relationships
        include_photos: Whether to include photos in the report

    Returns:
        BytesIO object containing the Excel file
    """

    output = BytesIO()

    workbook = xlsxwriter.Workbook(output, {"in_memory": True})
    worksheet = workbook.add_worksheet("Assets")

    header_format = workbook.add_format(
        {
            "bold": True,
            "bg_color": "#4472C4",
            "font_color": "white",
            "border": 1,
            "align": "center",
            "valign": "vcenter",
        }
    )

    cell_format = workbook.add_format(
        {
            "border": 1,
            "align": "left",
            "valign": "vcenter",
        }
    )

    date_format = workbook.add_format(
        {
            "border": 1,
            "align": "left",
            "valign": "vcenter",
            "num_format": "yyyy-mm-dd",
        }
    )

    if include_photos:
        description_format = workbook.add_format(
            {
                "border": 1,
                "align": "left",
                "valign": "top",
                "text_wrap": True,
            }
        )
    else:
        description_format = workbook.add_format(
            {
                "border": 1,
                "align": "left",
                "valign": "vcenter",
            }
        )

    headers = [
        "Tag BIM",
        "ID Interno",
        "Fecha Instalación",
        "Proyecto",
        "Elemento",
        "Instalador",
        "Macro Ubicación",
        "Dirección Calzada",
        "Georeferenciación",
        "Descripción",
    ]

    if include_photos:
        headers.append("Foto")

    for col, header in enumerate(headers):
        worksheet.write(0, col, header, header_format)

    worksheet.set_column(0, 0, 20)  # Tag BIM
    worksheet.set_column(1, 1, 15)  # ID Interno
    worksheet.set_column(2, 2, 18)  # Fecha Instalación
    worksheet.set_column(3, 3, 25)  # Proyecto
    worksheet.set_column(4, 4, 50)  # Elemento
    worksheet.set_column(5, 5, 30)  # Instalador
    worksheet.set_column(6, 6, 20)  # Macro Ubicación
    worksheet.set_column(7, 7, 15)  # Dirección Calzada
    worksheet.set_column(8, 8, 30)  # Georeferenciación
    worksheet.set_column(9, 9, 25)  # Descripción
    if include_photos:
        worksheet.set_column(10, 10, 22)  # Foto (width to fit 150px image)

    worksheet.freeze_panes(1, 0)

    photos_dir = Path(ASSET_PHOTOS_DIR) if include_photos else None

    for row_idx, asset in enumerate(assets, start=1):
        if include_photos:
            worksheet.set_row(row_idx, EXCEL_ROW_HEIGHT)

        contract_name = asset.contract_project.nombre if asset.contract_project else ""
        element_type_name = asset.element_type.nombre if asset.element_type else ""
        installer_name = asset.installer.nombre if asset.installer else ""
        macro_location_name = (
            asset.macro_location.nombre if asset.macro_location else ""
        )

        worksheet.write(row_idx, 0, asset.tag_bim or "", cell_format)
        worksheet.write(row_idx, 1, asset.id_interno, cell_format)
        worksheet.write_datetime(row_idx, 2, asset.fecha_instalacion, date_format)
        worksheet.write(row_idx, 3, contract_name, cell_format)
        worksheet.write(row_idx, 4, element_type_name, cell_format)
        worksheet.write(row_idx, 5, installer_name, cell_format)
        worksheet.write(row_idx, 6, macro_location_name, cell_format)
        worksheet.write(row_idx, 7, asset.ubicacion_via.value, cell_format)
        worksheet.write(row_idx, 8, asset.georeferenciacion or "", cell_format)
        worksheet.write(row_idx, 9, asset.descripcion or "", description_format)

        if include_photos and asset.nombre_foto_codigo_barra:
            photo_path = photos_dir / asset.nombre_foto_codigo_barra

            if photo_path.exists() and photo_path.is_file():
                resized_image = _resize_image(
                    photo_path,
                    PHOTO_MAX_WIDTH,
                    PHOTO_MAX_HEIGHT,
                )

                if resized_image:
                    try:
                        worksheet.insert_image(
                            row_idx,
                            10,  # Photo column
                            asset.nombre_foto_codigo_barra,
                            {
                                "image_data": resized_image,
                                "x_offset": 5,
                                "y_offset": 5,
                                "positioning": 1,
                            },
                        )
                    except Exception as e:
                        worksheet.write(row_idx, 10, "Error al cargar", cell_format)
                        log.error(
                            "Error inserting photo in Excel",
                            extra={
                                "asset_id": asset.id,
                                "photo_name": asset.nombre_foto_codigo_barra,
                                "error": str(e),
                            },
                        )
                else:
                    worksheet.write(row_idx, 10, "Error al procesar", cell_format)
            else:
                worksheet.write(row_idx, 10, "Archivo no encontrado", cell_format)
                log.warning(
                    "Photo file not found in filesystem",
                    extra={
                        "asset_id": asset.id,
                        "id_interno": asset.id_interno,
                        "photo_name": asset.nombre_foto_codigo_barra,
                        "expected_path": str(photo_path),
                    },
                )
        elif include_photos:
            worksheet.write(row_idx, 10, "Sin foto", cell_format)

    workbook.close()

    output.seek(0)

    return output


def generate_installers_excel_report(
    assets: List[Asset],
) -> Optional[BytesIO]:
    """
    Generate an Excel report with one sheet per installer.

    Each sheet contains:
    - Total number of assets by that installer
    - Last asset creation date
    - Maximum time delta between consecutive asset creations
    - Table of all assets sorted by created_at (descending)

    Args:
        assets: List of Asset model instances with loaded relationships

    Returns:
        BytesIO object containing the Excel file, or None if no assets
    """
    if not assets:
        return None

    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True})

    # Formats
    header_format = workbook.add_format(
        {
            "bold": True,
            "bg_color": "#4472C4",
            "font_color": "white",
            "border": 1,
            "align": "center",
            "valign": "vcenter",
        }
    )

    stats_label_format = workbook.add_format(
        {
            "bold": True,
            "bg_color": "#D9E1F2",
            "border": 1,
            "align": "left",
            "valign": "vcenter",
        }
    )

    stats_value_format = workbook.add_format(
        {
            "border": 1,
            "align": "left",
            "valign": "vcenter",
        }
    )

    cell_format = workbook.add_format(
        {
            "border": 1,
            "align": "left",
            "valign": "vcenter",
        }
    )

    datetime_format = workbook.add_format(
        {
            "border": 1,
            "align": "left",
            "valign": "vcenter",
        }
    )

    from collections import defaultdict

    assets_by_installer = defaultdict(list)
    for asset in assets:
        if asset.installer:
            assets_by_installer[asset.installer.nombre].append(asset)

    for installer_name, installer_assets in sorted(assets_by_installer.items()):
        sheet_name = installer_name[:31]
        invalid_chars = ["[", "]", "*", "?", ":", "/", "\\"]
        for char in invalid_chars:
            sheet_name = sheet_name.replace(char, "")

        worksheet = workbook.add_worksheet(sheet_name)

        sorted_assets = sorted(
            installer_assets, key=lambda a: a.created_at, reverse=True
        )

        total_assets = len(sorted_assets)
        last_creation = sorted_assets[0].created_at if sorted_assets else None

        max_delta = None
        if len(sorted_assets) >= 2:
            sorted_for_delta = sorted(sorted_assets, key=lambda a: a.created_at)
            deltas = []
            for i in range(1, len(sorted_for_delta)):
                delta = (
                    sorted_for_delta[i].created_at - sorted_for_delta[i - 1].created_at
                )
                deltas.append(delta)
            if deltas:
                max_delta = max(deltas)

        worksheet.write(0, 0, "Instalador:", stats_label_format)
        worksheet.write(0, 1, installer_name, stats_value_format)

        worksheet.write(1, 0, "Estadísticas del Instalador", stats_label_format)
        worksheet.write(1, 1, "", stats_label_format)

        worksheet.write(2, 0, "Total de Activos:", stats_label_format)
        worksheet.write(2, 1, total_assets, stats_value_format)

        worksheet.write(3, 0, "Última Instalación:", stats_label_format)
        if last_creation:
            chile_tz = pytz.timezone("Chile/Continental")
            utc_tz = pytz.UTC
            last_creation_utc = (
                last_creation.replace(tzinfo=utc_tz)
                if last_creation.tzinfo is None
                else last_creation
            )
            last_creation_chile = last_creation_utc.astimezone(chile_tz)

            months_es = [
                "enero",
                "febrero",
                "marzo",
                "abril",
                "mayo",
                "junio",
                "julio",
                "agosto",
                "septiembre",
                "octubre",
                "noviembre",
                "diciembre",
            ]
            formatted_date = (
                f"{last_creation_chile.day} {months_es[last_creation_chile.month - 1]} "
                f"{last_creation_chile.year} {last_creation_chile.strftime('%I:%M%p')}"
            )
            worksheet.write(3, 1, formatted_date, stats_value_format)
        else:
            worksheet.write(3, 1, "N/A", stats_value_format)

        worksheet.write(4, 0, "Delta Máximo Entre Instalaciones:", stats_label_format)
        if max_delta:
            total_hours = int(max_delta.total_seconds() // 3600)
            remaining_minutes = int((max_delta.total_seconds() % 3600) // 60)
            delta_str = f"{total_hours} horas, {remaining_minutes} minutos"
            worksheet.write(4, 1, delta_str, stats_value_format)
        else:
            worksheet.write(4, 1, "N/A", stats_value_format)

        worksheet.set_column(0, 0, 35)
        worksheet.set_column(1, 1, 35)
        table_start_row = 6
        headers = [
            "ID Único",
            "Tipo de Elemento",
            "Dirección Calzada",
            "Georeferenciación",
            "Fecha de Creación",
        ]

        for col, header in enumerate(headers):
            worksheet.write(table_start_row, col, header, header_format)

        worksheet.set_column(0, 0, 15)  # ID Único
        worksheet.set_column(1, 1, 50)  # Tipo de Elemento
        worksheet.set_column(2, 2, 20)  # Dirección Calzada
        worksheet.set_column(3, 3, 30)  # Georeferenciación
        worksheet.set_column(4, 4, 32)  # Fecha de Creación

        worksheet.freeze_panes(table_start_row + 1, 0)

        chile_tz = pytz.timezone("Chile/Continental")
        utc_tz = pytz.UTC
        months_es = [
            "enero",
            "febrero",
            "marzo",
            "abril",
            "mayo",
            "junio",
            "julio",
            "agosto",
            "septiembre",
            "octubre",
            "noviembre",
            "diciembre",
        ]
        for row_idx, asset in enumerate(sorted_assets, start=table_start_row + 1):
            element_type_name = asset.element_type.nombre if asset.element_type else ""

            created_at_utc = (
                asset.created_at.replace(tzinfo=utc_tz)
                if asset.created_at.tzinfo is None
                else asset.created_at
            )
            created_at_chile = created_at_utc.astimezone(chile_tz)

            formatted_date = (
                f"{created_at_chile.day} {months_es[created_at_chile.month - 1]} "
                f"{created_at_chile.year} {created_at_chile.strftime('%I:%M%p')}"
            )

            worksheet.write(row_idx, 0, asset.id_interno, cell_format)
            worksheet.write(row_idx, 1, element_type_name, cell_format)
            worksheet.write(row_idx, 2, asset.ubicacion_via.value, cell_format)
            worksheet.write(row_idx, 3, asset.georeferenciacion or "", cell_format)
            worksheet.write(row_idx, 4, formatted_date, cell_format)

    workbook.close()
    output.seek(0)

    return output


def generate_kmz_report(
    assets: Optional[List[Asset]] = None,
    assets_data: Optional[List[Dict[str, Any]]] = None,
) -> BytesIO:
    if assets is None and assets_data is None:
        raise ValueError("Either assets or assets_data must be provided")

    valid_assets = []
    skipped_count = 0

    if assets is not None:
        for asset in assets:
            lat, lon = _parse_georef(asset.georeferenciacion)
            if lat is not None and lon is not None:
                elemento_name = asset.element_type.nombre
                valid_assets.append(
                    {
                        "id_interno": asset.id_interno,
                        "elemento": elemento_name,
                        "lat": lat,
                        "lon": lon,
                    }
                )
            else:
                skipped_count += 1
                if asset.georeferenciacion:
                    log.warning(
                        "Asset skipped due to invalid georeferenciacion",
                        extra={
                            "asset_id": asset.id,
                            "id_interno": asset.id_interno,
                            "georeferenciacion": asset.georeferenciacion,
                        },
                    )

    if assets_data is not None:
        for asset_dict in assets_data:
            lat, lon = _parse_georef(asset_dict.get("georeferenciacion", ""))
            if lat is not None and lon is not None:
                valid_assets.append(
                    {
                        "id_interno": asset_dict.get("id_interno"),
                        "elemento": asset_dict.get("elemento", ""),
                        "lat": lat,
                        "lon": lon,
                    }
                )
            else:
                skipped_count += 1
                if asset_dict.get("georeferenciacion"):
                    log.warning(
                        "Asset skipped due to invalid georeferenciacion",
                        extra={
                            "id_interno": asset_dict.get("id_interno"),
                            "georeferenciacion": asset_dict.get("georeferenciacion"),
                        },
                    )

    log.info(
        "KMZ report generation",
        extra={
            "total_assets": len(assets or []) + len(assets_data or []),
            "valid_assets": len(valid_assets),
            "skipped_assets": skipped_count,
        },
    )

    placemarks = []
    for asset_data in valid_assets:
        id_interno = _escape_xml(str(asset_data["id_interno"]))
        elemento = _escape_xml(str(asset_data.get("elemento", "")))
        lat = asset_data["lat"]
        lon = asset_data["lon"]

        if elemento:
            name = f"{id_interno} - {elemento}"
        else:
            name = id_interno

        placemark = f"""
        <Placemark>
            <name>{name}</name>
            <Point>
                <coordinates>{lon},{lat},0</coordinates>
            </Point>
        </Placemark>"""
        placemarks.append(placemark)

    kml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Activos Viales</name>
    <description>Activos extraídos desde base de datos</description>
    {''.join(placemarks)}
  </Document>
</kml>
"""

    output = BytesIO()
    try:
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as kmz:
            kmz.writestr("doc.kml", kml_content.encode("utf-8"))
    except Exception as e:
        log.error(
            "Error creating KMZ file",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise

    output.seek(0)

    return output
