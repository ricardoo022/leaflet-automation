from enum import StrEnum


class ProgramType(StrEnum):
    WEEKLY = "weekly"
    WEEKEND = "weekend"
    SPECIAL = "special"
    UNKNOWN = "unknown"


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
