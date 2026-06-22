from aiohttp import ClientError

from .base import AppBaseException


class BaseIntegrationException(AppBaseException):
    pass


class InvalidFormatResponse(BaseIntegrationException):
    pass


class FailedResponseCodeException(BaseIntegrationException):
    def __init__(self, status_code, detail):
        self.status_code=status_code
        self.detail=detail

    def __str__(self):
        return f"status_code={self.status_code}, detail={self.detail}"


class UnexpectedResponseException(BaseIntegrationException):
    def __init__(self, exc: ClientError):
        self.orig_exc = exc

    def __str__(self):
        return str(self.orig_exc)
