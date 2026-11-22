"""Schema-validated JSON/CSV persistence with atomic writes."""

from __future__ import annotations

import csv
import json
import os
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .errors import InputValidationError
from .models import Exam, Faculty, Room, Student


def atomic_write_json(path: str | Path, payload: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def load_json(path: str | Path) -> dict[str, Any]:
    try:
        with Path(path).open(encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise InputValidationError(f"invalid JSON file: {exc}") from exc
    if not isinstance(data, dict):
        raise InputValidationError("top-level JSON value must be an object")
    required = {"students", "exams", "faculty", "rooms"}
    if set(data) != required:
        raise InputValidationError(f"JSON keys must be exactly {sorted(required)}")
    if any(not isinstance(data[key], list) for key in required):
        raise InputValidationError("students, exams, faculty, and rooms must be arrays")
    return data


def load_csv_rows(path: str | Path, required_columns: set[str]) -> list[dict[str, str]]:
    try:
        with Path(path).open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or not required_columns.issubset(reader.fieldnames):
                raise InputValidationError(f"CSV requires columns {sorted(required_columns)}")
            return [dict(row) for row in reader]
    except OSError as exc:
        raise InputValidationError(f"cannot read CSV: {exc}") from exc


def parse_entities(data: dict[str, Any]) -> tuple[list[Student], list[Exam], list[Faculty], list[Room]]:
    try:
        if not all(isinstance(data[key], list) for key in ("students", "exams", "faculty", "rooms")):
            raise InputValidationError("all entity collections must be arrays")
        if any(not isinstance(row, dict) for collection in data.values() for row in collection):
            raise InputValidationError("every entity must be an object")
        students = [
            Student(row["student_id"], row["name"], tuple(row["subjects"]))
            for row in data["students"]
        ]
        exams = [
            Exam(row["exam_id"], row["subject"], tuple(row["student_ids"]))
            for row in data["exams"]
        ]
        faculty = [
            Faculty(
                row["faculty_id"], row["name"], tuple(row.get("subjects", [])),
                frozenset(row.get("unavailable_blocks", [])),
            )
            for row in data["faculty"]
        ]
        rooms = [Room(row["room_id"], row["capacity"]) for row in data["rooms"]]
    except (KeyError, TypeError, ValueError, InputValidationError) as exc:
        raise InputValidationError(f"invalid entity schema: {exc}") from exc
    student_ids = {student.student_id for student in students}
    if len(student_ids) != len(students):
        raise InputValidationError("student IDs must be unique")
    if len({exam.exam_id for exam in exams}) != len(exams):
        raise InputValidationError("exam IDs must be unique")
    if len({teacher.faculty_id for teacher in faculty}) != len(faculty):
        raise InputValidationError("faculty IDs must be unique")
    if len({room.room_id for room in rooms}) != len(rooms):
        raise InputValidationError("room IDs must be unique")
    if any(student_id not in student_ids for exam in exams for student_id in exam.student_ids):
        raise InputValidationError("every exam student_id must refer to a known student")
    return students, exams, faculty, rooms
