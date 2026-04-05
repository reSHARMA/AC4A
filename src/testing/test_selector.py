"""Coverage-aware strategic test selection.

Given a pool of generated tests and a user-requested budget (N), pick the N
tests that maximise predicted branch coverage using a greedy set-cover
heuristic, breaking ties with the LLM-assigned priority score.
"""

import logging
from typing import Any, Dict, List, Optional, Set

from src.testing.coverage_tracker import ALL_BRANCH_IDS, predict_branches

logger = logging.getLogger(__name__)


def select_tests(
    tests: List[Dict[str, Any]],
    num_to_select: int,
    action_types: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Select *num_to_select* tests from *tests* to maximise coverage.

    Returns a dict with:
        selected: list of chosen test dicts (augmented with predicted_branches)
        predicted_coverage: summary of which branches the selection covers
    """
    if action_types is None:
        action_types = ["Read", "Write", "Create"]

    if num_to_select >= len(tests):
        selected = list(tests)
        _augment_predictions(selected)
        return _build_result(selected)

    # Pre-compute predicted branches for every test
    predictions: List[Set[str]] = []
    for t in tests:
        branches = set(predict_branches(t))
        predictions.append(branches)

    selected_indices: List[int] = []
    covered: Set[str] = set()

    # Ensure at least one test per action type when possible
    action_covered: Set[str] = set()
    for action in action_types:
        if action in action_covered:
            continue
        best_idx = _best_for_action(tests, predictions, action, covered, set(selected_indices))
        if best_idx is not None:
            selected_indices.append(best_idx)
            covered |= predictions[best_idx]
            action_covered.add(action)
        if len(selected_indices) >= num_to_select:
            break

    # Greedy set-cover for remaining budget
    while len(selected_indices) < num_to_select:
        best_idx = _best_remaining(tests, predictions, covered, set(selected_indices))
        if best_idx is None:
            break
        selected_indices.append(best_idx)
        covered |= predictions[best_idx]

    selected = [tests[i] for i in selected_indices]
    _augment_predictions(selected)

    result = _build_result(selected)
    logger.info(
        "Selected %d/%d tests covering %d/%d branches",
        len(selected), len(tests),
        len(covered), len(ALL_BRANCH_IDS),
    )
    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _best_for_action(
    tests: List[Dict],
    predictions: List[Set[str]],
    action: str,
    already_covered: Set[str],
    excluded: Set[int],
) -> Optional[int]:
    """Find the best test for a specific action type."""
    best_idx = None
    best_new = -1
    best_priority = -1.0

    for i, t in enumerate(tests):
        if i in excluded:
            continue
        grant = t.get("grant_permission", {})
        if grant.get("action", "").lower() != action.lower():
            # For web tests, check selector_type
            if t.get("grant_permission", {}).get("selector_type", "").lower() != action.lower():
                continue
        new_branches = len(predictions[i] - already_covered)
        priority = float(t.get("priority", 0.5))
        if new_branches > best_new or (new_branches == best_new and priority > best_priority):
            best_idx = i
            best_new = new_branches
            best_priority = priority

    return best_idx


def _best_remaining(
    tests: List[Dict],
    predictions: List[Set[str]],
    already_covered: Set[str],
    excluded: Set[int],
) -> Optional[int]:
    """Greedy pick: the test adding the most new branches."""
    best_idx = None
    best_new = -1
    best_priority = -1.0

    for i in range(len(tests)):
        if i in excluded:
            continue
        new_branches = len(predictions[i] - already_covered)
        priority = float(tests[i].get("priority", 0.5))
        if new_branches > best_new or (new_branches == best_new and priority > best_priority):
            best_idx = i
            best_new = new_branches
            best_priority = priority

    # If nothing adds new branches, pick highest-priority unused test
    if best_idx is not None and best_new == 0:
        for i in range(len(tests)):
            if i in excluded:
                continue
            priority = float(tests[i].get("priority", 0.5))
            if priority > best_priority:
                best_idx = i
                best_priority = priority

    return best_idx


def _augment_predictions(tests: List[Dict[str, Any]]) -> None:
    """Ensure each test carries its predicted_branches list."""
    for t in tests:
        if "predicted_branches" not in t or not t["predicted_branches"]:
            t["predicted_branches"] = predict_branches(t)


def _build_result(selected: List[Dict[str, Any]]) -> Dict[str, Any]:
    all_predicted: Set[str] = set()
    for t in selected:
        all_predicted.update(t.get("predicted_branches", []))

    return {
        "selected": selected,
        "predicted_coverage": {
            "branches_covered": sorted(all_predicted, key=lambda b: int(b[1:])),
            "branches_missing": sorted(
                set(ALL_BRANCH_IDS) - all_predicted, key=lambda b: int(b[1:])
            ),
            "branch_coverage_pct": round(
                100 * len(all_predicted) / max(len(ALL_BRANCH_IDS), 1), 1
            ),
            "total_branches": len(ALL_BRANCH_IDS),
        },
    }
