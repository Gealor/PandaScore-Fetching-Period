from .base import AppBaseException


class BaseOutboxEventException(AppBaseException):
    pass

class OutboxEventNotFoundException(AppBaseException):
    pass