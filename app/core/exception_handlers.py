from typing import Dict, Any, List
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi import HTTPException as FastAPIHTTPException

from app.utils.logger import logger_instance as log


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Global handler for Pydantic validation errors - simple and effective.
    """
    errors: List[Dict[str, Any]] = []
    for error in exc.errors():
        field_name: str = " -> ".join(str(loc) for loc in error["loc"])
        errors.append(
            {
                "field": field_name,
                "message": error["msg"],
                "type": error["type"],
            }
        )

    log.error(
        "Pydantic validation error",
        extra={
            "method": request.method,
            "url": str(request.url),
            "errors": errors,
            "error_count": len(errors),
        },
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "detail": "Validation error",
            "errors": errors,
        },
    )


async def fastapi_http_exception_handler(
    request: Request, exc: FastAPIHTTPException
) -> JSONResponse:
    """
    Handler for FastAPI HTTPExceptions (raised by our application code).
    These should pass through without modification.
    """
    log.info(
        f"Application HTTP exception {exc.status_code}",
        extra={
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "status_code": exc.status_code,
            "detail": str(exc.detail),
        },
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """
    Global handler for Starlette HTTP exceptions (like route not found, method not allowed, etc.).
    These are typically infrastructure-level errors.
    """
    if exc.status_code == 404:
        log.warning(
            "Endpoint not found",
            extra={
                "method": request.method,
                "url": str(request.url),
                "path": request.url.path,
                "status_code": 404,
            },
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "detail": f"The requested endpoint '{request.method} {request.url.path}' was not found on this server.",
                "error_type": "endpoint_not_found",
                "suggestion": "Please check the URL and HTTP method, or refer to the API documentation.",
            },
        )
    elif exc.status_code == 405:
        log.warning(
            "Method not allowed",
            extra={
                "method": request.method,
                "url": str(request.url),
                "path": request.url.path,
                "status_code": 405,
            },
        )
        return JSONResponse(
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            content={
                "detail": f"The HTTP method '{request.method}' is not allowed for the endpoint '{request.url.path}'.",
                "error_type": "method_not_allowed",
                "suggestion": "Please check the allowed HTTP methods for this endpoint.",
            },
        )
    else:
        log.error(
            f"HTTP exception {exc.status_code}",
            extra={
                "method": request.method,
                "url": str(request.url),
                "status_code": exc.status_code,
                "detail": str(exc.detail),
            },
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )


def setup_exception_handlers(app: FastAPI) -> None:
    """
    Register all exception handlers with the FastAPI app.
    Call this function from main.py to keep it clean.

    Args:
        app: The FastAPI application instance
    """
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(FastAPIHTTPException, fastapi_http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
