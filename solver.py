"""Graph-colouring and resource-assignment solver."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from .adts import DoublyLinkedList, MinHeap
from .errors import CapacityExceededError, ScheduleConflictError
from .models import Assignment, Exam, Faculty, Room, Schedule


@dataclass
class _SearchState:
    colors: dict[str, int]
    saturation: dict[str, set[int]]


class ScheduleSolver:
    """Solve exam blocks, rooms, and invigilators using deterministic search."""

    def __init__(
        self,
        exams: Iterable[Exam],
        faculty: Iterable[Faculty],
        rooms: Iterable[Room],
        block_count: int,
    ) -> None:
        self.exams = list(exams)
        self.faculty = list(faculty)
        self.rooms = list(rooms)
        if block_count <= 0:
            raise ValueError("block_count must be positive")
        self.block_count = block_count
        self.exam_by_id = {e.exam_id: e for e in self.exams}
        if len(self.exam_by_id) != len(self.exams):
            raise ValueError("exam IDs must be unique")
        self.graph = self._build_conflict_graph()

    def _build_conflict_graph(self) -> dict[str, set[str]]:
        graph = {exam.exam_id: set() for exam in self.exams}
        for index, left in enumerate(self.exams):
            left_students = set(left.student_ids)
            for right in self.exams[index + 1:]:
                if left_students.intersection(right.student_ids):
                    graph[left.exam_id].add(right.exam_id)
                    graph[right.exam_id].add(left.exam_id)
        return graph

    def color_exams(self) -> dict[str, int]:
        """Colour the conflict graph with DSATUR plus recursive backtracking.

        This reference implementation rebuilds the heap for each selected
        vertex, so selection is O(V log V) per step and O(V^2 log V) overall;
        an indexed heap with lazy priority updates reduces this to
        O((V + E) log V). Graph construction is O(V^2 * S).
        Backtracking is O(K^V) in the worst case, but pruning rejects a branch
        as soon as a vertex has no legal color. State uses O(V + E) space.
        """
        state = _SearchState({}, {exam.exam_id: set() for exam in self.exams})
        if self._color_recursive(state):
            return state.colors
        raise ScheduleConflictError(
            f"unable to place {len(self.exams)} exams in {self.block_count} conflict-free blocks"
        )

    def _select_vertex(self, state: _SearchState) -> str:
        heap: MinHeap[str] = MinHeap()
        for exam_id, neighbours in self.graph.items():
            if exam_id not in state.colors:
                priority = (-len(state.saturation[exam_id]), -len(neighbours), exam_id)
                heap.push(priority, exam_id)
        return heap.pop()

    def _color_recursive(self, state: _SearchState) -> bool:
        if len(state.colors) == len(self.exams):
            return True
        vertex = self._select_vertex(state)
        forbidden = {state.colors[n] for n in self.graph[vertex] if n in state.colors}
        for color in range(self.block_count):
            if color in forbidden:
                continue
            state.colors[vertex] = color
            changed: list[tuple[str, bool]] = []
            for neighbour in self.graph[vertex]:
                if neighbour not in state.colors and color not in state.saturation[neighbour]:
                    state.saturation[neighbour].add(color)
                    changed.append((neighbour, True))
            if self._color_recursive(state):
                return True
            for neighbour, _ in changed:
                state.saturation[neighbour].discard(color)
            del state.colors[vertex]
        return False

    def solve(self) -> Schedule:
        colors = self.color_exams()
        assignments = self._assign_resources(colors)
        return Schedule(assignments)

    def _assign_resources(self, colors: dict[str, int]) -> list[Assignment]:
        by_block: dict[int, list[Exam]] = defaultdict(list)
        for exam in self.exams:
            by_block[colors[exam.exam_id]].append(exam)
        room_for: dict[str, str] = {}
        for block, exams in by_block.items():
            used_rooms: set[str] = set()
            for exam in sorted(exams, key=lambda e: len(e.student_ids), reverse=True):
                choices = [
                    room for room in self.rooms
                    if room.room_id not in used_rooms and room.capacity >= len(exam.student_ids)
                ]
                if not choices:
                    if not any(room.capacity >= len(exam.student_ids) for room in self.rooms):
                        raise CapacityExceededError(
                            f"exam {exam.exam_id} needs {len(exam.student_ids)} seats"
                        )
                    raise ScheduleConflictError(f"not enough rooms in block {block}")
                room = min(choices, key=lambda r: (r.capacity, r.room_id))
                used_rooms.add(room.room_id)
                room_for[exam.exam_id] = room.room_id

        faculty_for = self._assign_faculty(colors)
        return [
            Assignment(exam.exam_id, colors[exam.exam_id], room_for[exam.exam_id], faculty_for[exam.exam_id])
            for exam in self.exams
        ]

    def _assign_faculty(self, colors: dict[str, int]) -> dict[str, str]:
        ordered = sorted(self.exams, key=lambda e: (colors[e.exam_id], e.exam_id))
        loads = {teacher.faculty_id: 0 for teacher in self.faculty}
        assigned: dict[str, str] = {}
        by_block: dict[int, set[str]] = defaultdict(set)
        for exam in ordered:
            candidates = [
                teacher for teacher in self.faculty
                if exam.subject not in teacher.subjects
                and colors[exam.exam_id] not in teacher.unavailable_blocks
                and teacher.faculty_id not in by_block[colors[exam.exam_id]]
                and self._consecutive_ok(teacher.faculty_id, colors[exam.exam_id], assigned, colors)
            ]
            if not candidates:
                raise ScheduleConflictError(f"no eligible invigilator for exam {exam.exam_id}")
            teacher = min(candidates, key=lambda t: (loads[t.faculty_id], t.faculty_id))
            assigned[exam.exam_id] = teacher.faculty_id
            loads[teacher.faculty_id] += 1
            by_block[colors[exam.exam_id]].add(teacher.faculty_id)
        mean = sum(loads.values()) / len(self.faculty) if self.faculty else 0
        if mean:
            lower, upper = mean * 0.85, mean * 1.15
            # Fairness is soft: retain the feasible schedule and expose the score.
            self.fairness_violations = sum(not lower <= load <= upper for load in loads.values())
        else:
            self.fairness_violations = 0
        return assigned

    @staticmethod
    def _consecutive_ok(
        faculty_id: str, block: int, assigned: dict[str, str], colors: dict[str, int]
    ) -> bool:
        blocks = sorted(colors[eid] for eid, fid in assigned.items() if fid == faculty_id)
        run = 1
        for previous in reversed(blocks):
            if previous == block - run:
                run += 1
            else:
                break
        return run <= 2

    def apply_override(self, schedule: Schedule, assignment: Assignment) -> None:
        """Append a manual override to a doubly linked audit trail."""
        trail = getattr(schedule, "_trail", None)
        if trail is None:
            trail = DoublyLinkedList[dict]()
            for event in schedule.audit:
                trail.append(event)
            schedule._trail = trail
        event = {"action": "override", "assignment": assignment.__dict__.copy()}
        trail.append(event)
        schedule.audit.append(event)
