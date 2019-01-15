"""Exception types

Exception hierarchy::

    ApplicationException
        InvalidStateError
"""


class ApplicationException(Exception):
    """Base exception type"""


class InvalidStateError(ApplicationException):
    """The internal state or class invariant is violated"""
