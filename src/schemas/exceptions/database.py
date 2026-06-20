from .base import AppBaseException


class BaseDatabaseException(AppBaseException):
    pass

class DatabaseException(BaseDatabaseException):
    pass

class DatabaseStartupException(BaseDatabaseException):
    pass