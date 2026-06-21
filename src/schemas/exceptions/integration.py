from .base import AppBaseException


class BaseIntegrationException(AppBaseException):
    pass


class InvalidFormatResponse(BaseIntegrationException):
    pass


class FailedResponseCodeException(BaseIntegrationException):
    pass
