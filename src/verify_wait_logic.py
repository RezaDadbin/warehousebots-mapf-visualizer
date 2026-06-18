# Small smoke checks for WAIT/STAY behavior in MAPF transitions.
#
# Run from the project folder:
#
# python3 src/verify_wait_logic.py

from __future__ import annotations

try:
    from .mapf_problem import MAPFProblem
except ImportError:
    from mapf_problem import MAPFProblem


def build_wait_demo_problem() -> MAPFProblem:
    # Create a tiny two-agent problem with valid mixed WAIT actions.
    return MAPFProblem(
        name="wait_logic_smoke",
        rows=3,
        cols=4,
        grid=[
            "....",
            "....",
            "....",
        ],
        agents=[
            {"id": "A", "start": [1, 0], "goal": [1, 3]},
            {"id": "B", "start": [2, 3], "goal": [0, 3]},
        ],
        max_expansions=100,
    )


def run_wait_logic_checks() -> None:
    # Assert that individual WAIT is allowed and all-WAIT is rejected.
    problem = build_wait_demo_problem()
    state = problem.initial_state()

    all_wait = ("WAIT", "WAIT")
    assert problem._valid_child(state, all_wait, problem.result(state, all_wait)) == "all agents chose WAIT"

    mixed_wait = ("RIGHT", "WAIT")
    mixed_state = problem.result(state, mixed_wait)
    assert problem._valid_child(state, mixed_wait, mixed_state) is None

    valid_children, rejected_children = problem.generate_children(state, include_rejected=True)
    assert any(child.action == mixed_wait for child in valid_children)
    assert not any(
        rejected.action == mixed_wait and "WAIT" in rejected.reason
        for rejected in rejected_children
    )

    print("WAIT logic OK: individual WAIT is allowed, all-WAIT is rejected.")


if __name__ == "__main__":
    run_wait_logic_checks()
