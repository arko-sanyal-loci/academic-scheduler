# Academic Exam & Invigilator Scheduling Engine

## Criterion C — Development

The engine separates validated domain models (`models.py`), custom abstract data
types (`adts.py`), the solver (`solver.py`), persistence (`persistence.py`), and
the command-line/test runner (`cli.py`). Exam conflicts form an undirected graph:
two exams are adjacent when their student sets intersect. `ScheduleSolver`
colours this graph using DSATUR: the custom binary min-heap selects the uncoloured
vertex with maximum saturation, then maximum degree, with recursive backtracking
when a colour branch reaches a dead end. Saturation is the number of distinct
colours among already-coloured neighbours, not merely degree.

Rooms are assigned per block using capacity-descending exams and the smallest
adequate unused room. Faculty assignment rejects subject conflicts,
unavailability, duplicate block assignments, and runs longer than two consecutive
blocks; the remaining load-balance target is a soft objective and is reported as
`fairness_violations`. JSON and CSV input validation raises `InputValidationError`,
while hard scheduling failures raise `ScheduleConflictError` or
`CapacityExceededError`. JSON writes use a flushed temporary file followed by
`os.replace`, so readers never observe a partially-written target.

The custom `DoublyLinkedList` stores manual override events and exposes cursor
based undo/redo operations. Run the verification matrix with:

```bash
PYTHONPATH=.. python3 -m unittest discover -s tests -v
```

Or solve a JSON state file:

```bash
python3 -m academic_scheduler input.json --blocks 4 --output schedule.json
```

## Criterion E — Evaluation

For `V` exams and `E` conflict edges, the conflict graph construction is
`O(V^2 * S)` for `S` average enrolment size. This reference implementation
rebuilds the custom heap for each selected vertex, giving `O(V^2 log V)`
selection time. An indexed heap with lazy stale-entry deletion would provide
`O((V + E) log V)` priority maintenance; both approaches use `O(V + E)`
graph/state space. Recursive colouring is exponential in the worst case,
`O(K^V)` for `K` blocks, although saturation pruning rejects impossible
partial assignments early. This makes the implementation appropriate for a
school-sized timetable, but a 5,000-student deployment can bottleneck in
pairwise exam comparisons and in dense graphs that cause backtracking. An
inverted student-to-exam index, bitsets, connected-component decomposition,
and bounded parallel solving would reduce those costs.

Greedy DSATUR is fast, explainable, and has predictable memory use, but it can
settle on a locally convenient block arrangement and cannot optimise all
invigilator fairness choices globally. Exact integer linear programming can
optimise fairness, room use, and policy constraints together and provide
optimality certificates, but model construction and solving cost grow rapidly and
require an external solver, which conflicts with this standard-library-only
prototype. Two concrete extensions are: (1) add a simulated-annealing or tabu
search phase that swaps blocks/teachers to reduce fairness penalties after the
hard-feasible solution; and (2) replace the colouring core with a SAT/SMT or ILP
adapter supporting explicit room, availability, accessibility, and multi-room
exam constraints while retaining this domain/persistence API.
