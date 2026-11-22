"""Custom abstract data types required by the solver and audit trail."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Iterator, Optional, TypeVar

T = TypeVar("T")


class MinHeap(Generic[T]):
    """Binary min-heap with O(log n) insertion/removal and O(1) peek."""

    def __init__(self) -> None:
        self._items: list[tuple[tuple, T]] = []

    def __len__(self) -> int:
        return len(self._items)

    def push(self, priority: tuple, value: T) -> None:
        self._items.append((priority, value))
        self._sift_up(len(self._items) - 1)

    def pop(self) -> T:
        if not self._items:
            raise IndexError("pop from empty MinHeap")
        self._items[0], self._items[-1] = self._items[-1], self._items[0]
        item = self._items.pop()
        if self._items:
            self._sift_down(0)
        return item[1]

    def peek(self) -> T:
        if not self._items:
            raise IndexError("peek from empty MinHeap")
        return self._items[0][1]

    def _sift_up(self, index: int) -> None:
        while index:
            parent = (index - 1) // 2
            if self._items[parent][0] <= self._items[index][0]:
                return
            self._items[parent], self._items[index] = self._items[index], self._items[parent]
            index = parent

    def _sift_down(self, index: int) -> None:
        size = len(self._items)
        while True:
            left, right = 2 * index + 1, 2 * index + 2
            smallest = index
            if left < size and self._items[left][0] < self._items[smallest][0]:
                smallest = left
            if right < size and self._items[right][0] < self._items[smallest][0]:
                smallest = right
            if smallest == index:
                return
            self._items[index], self._items[smallest] = self._items[smallest], self._items[index]
            index = smallest


@dataclass
class _Node(Generic[T]):
    value: T
    previous: Optional["_Node[T]"] = None
    next: Optional["_Node[T]"] = None


class DoublyLinkedList(Generic[T]):
    """Pointer-based doubly linked list supporting cursor undo/redo operations."""

    def __init__(self) -> None:
        self.head: Optional[_Node[T]] = None
        self.tail: Optional[_Node[T]] = None
        self.cursor: Optional[_Node[T]] = None

    def append(self, value: T) -> None:
        node = _Node(value, self.tail)
        if self.tail:
            self.tail.next = node
        else:
            self.head = node
        self.tail = node
        self.cursor = node

    def undo(self) -> T:
        if not self.cursor:
            raise IndexError("nothing to undo")
        value = self.cursor.value
        self.cursor = self.cursor.previous
        return value

    def redo(self) -> T:
        node = self.head if self.cursor is None else self.cursor.next
        if not node:
            raise IndexError("nothing to redo")
        self.cursor = node
        return node.value

    def __iter__(self) -> Iterator[T]:
        current = self.head
        while current:
            yield current.value
            current = current.next
