"""Domain-specific exceptions."""


class SchedulerError(Exception):
    """Base class for expected scheduler failures."""


class ScheduleConflictError(SchedulerError):
    """Raised when hard scheduling constraints cannot all be satisfied."""


class CapacityExceededError(ScheduleConflictError):
    """Raised when no available room can seat an exam."""


class InputValidationError(SchedulerError):
    """Raised when JSON or CSV data does not match the input schema."""
