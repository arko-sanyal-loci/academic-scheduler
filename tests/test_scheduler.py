"""Normal, boundary, and corrupt-input tests for the scheduling engine."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from academic_scheduler.errors import CapacityExceededError, InputValidationError, ScheduleConflictError
from academic_scheduler.models import Exam, Faculty, Room
from academic_scheduler.persistence import atomic_write_json, load_json, parse_entities
from academic_scheduler.solver import ScheduleSolver


class SchedulerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.exams = [
            Exam("math", "Mathematics", ("s1", "s2")),
            Exam("history", "History", ("s2", "s3")),
            Exam("art", "Art", ("s4",)),
        ]
        self.faculty = [
            Faculty("f1", "A", ("Mathematics",), frozenset()),
            Faculty("f2", "B", ("History",), frozenset()),
            Faculty("f3", "C", ("Art",), frozenset()),
        ]

    def test_dsatur_colours_conflicts_and_assigns_resources(self) -> None:
        schedule = ScheduleSolver(self.exams, self.faculty, [Room("r1", 2), Room("r2", 2)], 2).solve()
        by_exam = {a.exam_id: a for a in schedule.assignments}
        self.assertNotEqual(by_exam["math"].block, by_exam["history"].block)
        self.assertEqual(len(schedule.assignments), 3)
        self.assertTrue(all(a.faculty_id != next(e for e in self.exams if e.exam_id == a.exam_id).subject for a in schedule.assignments))

    def test_exact_capacity_is_accepted(self) -> None:
        schedule = ScheduleSolver([Exam("x", "X", ("s1", "s2"))], [Faculty("f", "F", ("Y",))], [Room("r", 2)], 1).solve()
        self.assertEqual(schedule.assignments[0].room_id, "r")

    def test_capacity_overflow_is_reported(self) -> None:
        with self.assertRaises(CapacityExceededError):
            ScheduleSolver([Exam("x", "X", ("s1", "s2", "s3"))], [Faculty("f", "F", ("Y",))], [Room("r", 2)], 1).solve()

    def test_unsatisfiable_graph_is_reported(self) -> None:
        exams = [Exam(str(i), "X", ("s" + str(i), "shared")) for i in range(3)]
        faculty = [Faculty("f", "F", ("Y",))]
        with self.assertRaises(ScheduleConflictError):
            ScheduleSolver(exams, faculty, [Room("r", 10)], 2).color_exams()

    def test_zero_slack_availability_is_reported(self) -> None:
        faculty = [Faculty("f", "F", ("Other",), frozenset({0}))]
        with self.assertRaises(ScheduleConflictError):
            ScheduleSolver([Exam("x", "X", ("s",))], faculty, [Room("r", 1)], 1).solve()

    def test_corrupt_json_and_atomic_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            atomic_write_json(path, {"students": [], "exams": [], "faculty": [], "rooms": []})
            self.assertEqual(set(load_json(path)), {"students", "exams", "faculty", "rooms"})
            path.write_text("{bad", encoding="utf-8")
            with self.assertRaises(InputValidationError):
                load_json(path)
            with self.assertRaises(InputValidationError):
                parse_entities({"students": [], "exams": [], "faculty": [], "rooms": [{"room_id": "r", "capacity": "bad"}]})


if __name__ == "__main__":
    unittest.main()
