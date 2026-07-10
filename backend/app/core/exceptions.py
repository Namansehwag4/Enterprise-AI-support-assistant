class DomainException(Exception):
    """Base domain exception"""
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

class EntityNotFoundError(DomainException):
    """Raised when a requested resource is not found"""
    pass

class EntityAlreadyExistsError(DomainException):
    """Raised when trying to create a resource that already exists"""
    pass

class AuthenticationError(DomainException):
    """Raised when authentication fails"""
    pass

class AuthorizationError(DomainException):
    """Raised when a user lacks required permissions"""
    pass

class InvalidOperationError(DomainException):
    """Raised when an operation is invalid in the current state"""
    pass
