from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, code: str, detail: str, status: int = 400):
        self.code = code
        self.detail = detail
        self.status = status
        super().__init__(detail)


def not_found(detail: str = "Not found") -> AppError:
    return AppError("NOT_FOUND", detail, 404)


def forbidden(detail: str = "Forbidden") -> AppError:
    return AppError("FORBIDDEN", detail, 403)


def conflict(code: str, detail: str) -> AppError:
    return AppError(code, detail, 409)


def bad_request(code: str, detail: str) -> AppError:
    return AppError(code, detail, 400)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status, content={"detail": exc.detail, "code": exc.code}
        )
