"""Validated domain models and serialisation helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .errors import InputValidationError


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InputValidationError(f"{name} must be a non-empty string")
    return value.strip()


def _positive(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise InputValidationError(f"{name} must be a positive integer")
    return value


@dataclass(frozen=True)
class Student:
    student_id: str
    name: str
    subjects: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "student_id", _text(self.student_id, "student_id"))
        object.__setattr__(self, "name", _text(self.name, "name"))
        if not self.subjects or any(not isinstance(s, str) or not s.strip() for s in self.subjects):
            raise InputValidationError("subjects must contain non-empty strings")


@dataclass(frozen=True)
class Exam:
    exam_id: str
    subject: str
    student_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "exam_id", _text(self.exam_id, "exam_id"))
        object.__setattr__(self, "subject", _text(self.subject, "subject"))
        if not self.student_ids or len(set(self.student_ids)) != len(self.student_ids):
            raise InputValidationError("student_ids must be a non-empty unique sequence")


@dataclass(frozen=True)
class Faculty:
    faculty_id: str
    name: str
    subjects: tuple[str, ...]
    unavailable_blocks: frozenset[int] = frozenset()

    def __post_init__(self) -> None:
        object.__setattr__(self, "faculty_id", _text(self.faculty_id, "faculty_id"))
        object.__setattr__(self, "name", _text(self.name, "name"))
        if any(not isinstance(s, str) or not s.strip() for s in self.subjects):
            raise InputValidationError("faculty subjects must be strings")
        if any(isinstance(b, bool) or not isinstance(b, int) or b < 0 for b in self.unavailable_blocks):
            raise InputValidationError("unavailable_blocks must contain non-negative integers")


@dataclass(frozen=True)
class Room:
    room_id: str
    capacity: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "room_id", _text(self.room_id, "room_id"))
        object.__setattr__(self, "capacity", _positive(self.capacity, "capacity"))


@dataclass
class Assignment:
    exam_id: str
    block: int
    room_id: str
    faculty_id: str


@dataclass
class Schedule:
    assignments: list[Assignment] = field(default_factory=list)
    audit: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"assignments": [asdict(a) for a in self.assignments], "audit": self.audit}
