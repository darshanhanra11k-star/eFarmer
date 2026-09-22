import logging
from typing import cast

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import AppError

logger = logging.getLogger(__name__)


async def app_error_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    app_exc = cast(AppError, exc)
    return JSONResponse(
        status_code=app_exc.status_code,
        content=jsonable_encoder(app_exc.to_dict()),
    )


async def request_validation_error_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    val_exc = cast(RequestValidationError, exc)
    return JSONResponse(
        status_code=422,
        content=jsonable_encoder(
            {
                "code": "validation_error",
                "message": "Enter a valid value.",
                "status_code": 422,
                "details": {
                    "errors": val_exc.errors(),
                },
            }
        ),
    )


async def unexpected_error_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    logger.exception("unhandled_exception", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "code": "internal_error",
            "message": "Something went wrong.",
            "status_code": 500,
            "details": {},
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, request_validation_error_handler)
    app.add_exception_handler(Exception, unexpected_error_handler)
