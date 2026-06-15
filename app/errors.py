"""Structured error library + FastAPI handlers (S5 / TH-016)."""
from __future__ import annotations
import uuid
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


class APIError(Exception):
    def __init__(self, status_code: int, error_code: str, message: str):
        self.status_code = status_code
        self.error_code = error_code
        self.message = message


def _body(error_code: str, message: str) -> dict:
    return {"error_code": error_code, "message": message, "request_id": uuid.uuid4().hex[:12]}


def register(app):
    @app.exception_handler(APIError)
    async def _api(request: Request, exc: APIError):
        return JSONResponse(status_code=exc.status_code,
                            content=_body(exc.error_code, exc.message))

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException):
        mapping = {400: "INVALID_REQUEST", 401: "UNAUTHORIZED", 402: "QUOTA_EXCEEDED",
                   404: "NOT_FOUND", 422: "UNPROCESSABLE", 429: "RATE_LIMITED",
                   500: "SERVER_ERROR"}
        code = mapping.get(exc.status_code, "ERROR")
        detail = exc.detail
        if isinstance(detail, dict):
            return JSONResponse(status_code=exc.status_code, content=detail)
        return JSONResponse(status_code=exc.status_code, content=_body(code, str(detail)))

    @app.exception_handler(RequestValidationError)
    async def _val(request: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422,
                            content=_body("INVALID_REQUEST", "Malformed or missing fields."))
