class ServiceError(Exception):
    pass


class InvalidCredentials(ServiceError):
    pass


class AccessDenied(ServiceError):
    pass


class NotFound(ServiceError):
    pass


class Conflict(ServiceError):
    pass
