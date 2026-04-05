"""Coverage-aware strategic test selection.

Given a pool of generated tests and a user-requested budget (N), pick the N
tests that maximise predicted coverage using a greedy set-cover heuristic,
breaking ties with the LLM-assigned priority score.

For **browser/web** tests coverage units are ``data_type::selector_type``
entries from the mapping config.  For **API** tests they are heuristic
labels derived from the grant structure (spec depth, action, wildcard usage).
"""

import logging
from typing import Any, Dict, List, Optional, Set

from src.testing.coverage_tracker import predict_coverage_units, branch_sort_key

logger = logging.getLogger(__name__)


def select_tests(
    tests: List[Dict[str, Any]],
    num_to_select: int,
    action_types: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Select *num_to_select* tests from *tests* to maximise coverage.

    Returns a dict with:
        selected: list of chosen test dicts (augmented with predicted_branches)
        predicted_coverage: summary of which units the selection covers
    """
    if action_types is None:
        action_types = ["Read", "Write", "Create"]

    if num_to_select >= len(tests):
        selected = list(tests)
        _augment_predictions(selected)
        return _build_result(selected)

    predictions: List[Set[str]] = []
    for t in tests:
        units = set(predict_coverage_units(t))
        predictions.append(units)

    selected_indices: List[int] = []
    covered: Set[str] = set()

    for action in action_types:
        if len(selected_indices) >= num_to_select:
            break
        best_idx = _best_for_action(tests, predictions, action, covered, set(selected_indices))
        if best_idx is not None:
            selected_indices.append(best_idx)
            covered |= predictions[best_idx]

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
        "Selected %d/%d tests covering %d units",
        len(selected), len(tests), len(covered),
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
    best_idx = None
    best_new = -1
    best_priority = -1.0

    for i, t in enumerate(tests):
        if i in excluded:
            continue
        grant = t.get("grant_permission", {})
        test_action = (grant.get("action", "") or
                       grant.get("selector_type", "")).lower()
        if test_action != action.lower():
            continue
        new_units = len(predictions[i] - already_covered)
        priority = float(t.get("priority", 0.5))
        if new_units > best_new or (new_units == best_new and priority > best_priority):
            best_idx = i
            best_new = new_units
            best_priority = priority

    return best_idx


def _best_remaining(
    tests: List[Dict],
    predictions: List[Set[str]],
    already_covered: Set[str],
    excluded: Set[int],
) -> Optional[int]:
    best_idx = None
    best_new = -1
    best_priority = -1.0

    for i in range(len(tests)):
        if i in excluded:
            continue
        new_units = len(predictions[i] - already_covered)
        priority = float(tests[i].get("priority", 0.5))
        if new_units > best_new or (new_units == best_new and priority > best_priority):
            best_idx = i
            best_new = new_units
            best_priority = priority

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
    for t in tests:
        if "predicted_branches" not in t or not t["predicted_branches"]:
            t["predicted_branches"] = predict_coverage_units(t)


def _build_result(selected: List[Dict[str, Any]]) -> Dict[str, Any]:
    all_predicted: Set[str] = set()
    for t in selected:
        all_predicted.update(t.get("predicted_branches", []))

    is_web = any(
        "data_type" in t.get("grant_permission", {})
        for t in selected
    )

    coverage_type = "browser_mapping" if is_web else "annotation"

    return {
        "selected": selected,
        "predicted_coverage": {
            "coverage_type": coverage_type,
            "branches_hit": sorted(all_predicted, key=branch_sort_key),
            "branches_missing": [],
            "branch_coverage_pct": 0.0,
            "total_branches": len(all_predicted),
        },
    }
