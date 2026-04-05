"""Permission-function branch coverage tracker.

Provides both *runtime* coverage (using Python's ``coverage`` library) and a
*static predictor* that estimates which branches a test case will hit without
executing it, so the test selector can maximise coverage before any tests run.

Branch IDs (B1-B25) map to specific decision points in the permission
checking code — see the plan for the full branch map.
"""

import logging
import os
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Branch catalogue — the canonical set of branch IDs we track
# ---------------------------------------------------------------------------

BRANCH_CATALOG: Dict[str, str] = {
    # is_action_allowed
    "B1": "system disabled -> True",
    "B2": "OR over attributes, first match -> True",
    "B3": "no match -> denied",
    # _check_single_attribute
    "B4": "needs emptied by a rule -> allowed",
    "B5": "needs remain after all rules -> denied",
    # check_subsumption
    "B6": "rule_value == '?' -> skip attribute",
    "B7": "expiry check (datetime comparison)",
    "B8": "all attributes satisfied -> fully covers",
    "B9": "partial coverage -> still needed",
    "B10": "all have remaining values -> build new needs",
    # validate_attribute
    "B11": "no rule value -> return attribute",
    "B12": "resource_difference callable -> delegate",
    "B13": "tree comparison, sub_result >= 0 -> covers",
    "B14": "tree comparison, sub_result < 0 -> no match",
    # build_tree_from_values
    "B15": "has_special_value path",
    "B16": "non-special path (all wildcards/defaults)",
    "B17": "parent_has_special -> fill with '?'",
    "B18": "node_value is None -> fill with '?'",
    # check_subtree
    "B19": "key mismatch -> recurse into children",
    "B20": "value1 == value2 -> exact match",
    "B21": "value2 == '?' (request wildcard) -> match",
    "B22": "value1 == '?' (rule wildcard) -> match",
    "B23": "value mismatch -> -1",
    "B24": "children comparison (recursive)",
    "B25": "no corresponding child in node2 -> continue",
}

ALL_BRANCH_IDS: List[str] = sorted(BRANCH_CATALOG.keys(), key=lambda b: int(b[1:]))

# ---------------------------------------------------------------------------
# Runtime coverage using Python's `coverage` library
# ---------------------------------------------------------------------------

_POLICY_SYSTEM_FILE = os.path.join("src", "policy_system", "policy_system.py")
_RESOURCE_TREE_FILE = os.path.join("src", "utils", "resource_type_tree.py")

# Line ranges for each branch (approximate — adjusted to the actual source).
# We store sets of line numbers that, when executed, indicate a branch was hit.
# These are derived from reading the source files.
_BRANCH_LINE_MAP: Dict[str, Dict[str, List[int]]] = {
    "B1":  {_POLICY_SYSTEM_FILE: [304, 305, 306]},
    "B2":  {_POLICY_SYSTEM_FILE: [317, 318, 319]},
    "B3":  {_POLICY_SYSTEM_FILE: [321, 322]},
    "B4":  {_POLICY_SYSTEM_FILE: [347, 348, 352]},
    "B5":  {_POLICY_SYSTEM_FILE: [353, 354, 358]},
    "B6":  {_POLICY_SYSTEM_FILE: [380, 381]},
    "B7":  {_POLICY_SYSTEM_FILE: [374, 376, 377]},
    "B8":  {_POLICY_SYSTEM_FILE: [395, 396, 397]},
    "B9":  {_POLICY_SYSTEM_FILE: [398, 399, 400]},
    "B10": {_POLICY_SYSTEM_FILE: [403, 404, 405, 408]},
    "B11": {_POLICY_SYSTEM_FILE: [421, 422, 423]},
    "B12": {_POLICY_SYSTEM_FILE: [427, 428, 429]},
    "B13": {_POLICY_SYSTEM_FILE: [456, 460, 461]},
    "B14": {_POLICY_SYSTEM_FILE: [456, 462]},
    "B15": {_POLICY_SYSTEM_FILE: [481, 483]},
    "B16": {_POLICY_SYSTEM_FILE: [534, 536]},
    "B17": {_POLICY_SYSTEM_FILE: [496, 497, 498]},
    "B18": {_POLICY_SYSTEM_FILE: [514, 515, 516]},
    "B19": {_RESOURCE_TREE_FILE: [49, 50, 52, 53, 54]},
    "B20": {_RESOURCE_TREE_FILE: [59, 60, 61]},
    "B21": {_RESOURCE_TREE_FILE: [63, 64, 65]},
    "B22": {_RESOURCE_TREE_FILE: [67, 68, 69]},
    "B23": {_RESOURCE_TREE_FILE: [72, 73, 74]},
    "B24": {_RESOURCE_TREE_FILE: [77, 78, 82, 83, 86]},
    "B25": {_RESOURCE_TREE_FILE: [88, 89, 90]},
}


class PermissionCoverageTracker:
    """Wraps Python's ``coverage`` library to measure permission-function
    branch coverage on a per-test and cumulative basis."""

    def __init__(self):
        self._cumulative_lines: Dict[str, Set[int]] = {}
        self._cumulative_branches_hit: Set[str] = set()

    def run_with_coverage(
        self, func: Callable, *args: Any, **kwargs: Any
    ) -> Tuple[Any, Dict[str, Any]]:
        """Execute *func* while collecting line-level coverage, then map
        executed lines back to our branch IDs."""
        try:
            import coverage as cov_lib
        except ImportError:
            logger.warning("coverage library not installed — running without instrumentation")
            result = func(*args, **kwargs)
            return result, self._empty_report()

        cov = cov_lib.Coverage(branch=True, include=[
            os.path.abspath(os.path.join(os.getcwd(), _POLICY_SYSTEM_FILE)),
            os.path.abspath(os.path.join(os.getcwd(), _RESOURCE_TREE_FILE)),
        ])
        cov.start()
        try:
            result = func(*args, **kwargs)
        finally:
            cov.stop()
            cov.save()

        report = self._extract(cov)
        return result, report

    # ------------------------------------------------------------------

    def _extract(self, cov) -> Dict[str, Any]:
        """Map raw coverage data to our branch catalogue."""
        executed_per_file: Dict[str, Set[int]] = {}
        line_cov_data: Dict[str, Dict[str, Any]] = {}

        for measured_file in cov.get_data().measured_files():
            try:
                analysis = cov.analysis2(measured_file)
                # analysis2 returns (filename, executed, excluded, missing, formatted_missing)
                executed = set(analysis[1])
                missing = set(analysis[3])
            except Exception:
                continue

            # Normalise path for matching
            for ref_path in [_POLICY_SYSTEM_FILE, _RESOURCE_TREE_FILE]:
                abs_ref = os.path.abspath(os.path.join(os.getcwd(), ref_path))
                if os.path.abspath(measured_file) == abs_ref:
                    executed_per_file[ref_path] = executed
                    total = len(executed) + len(missing)
                    line_cov_data[ref_path] = {
                        "executed_lines": sorted(executed),
                        "missing_lines": sorted(missing),
                        "line_coverage_pct": round(100 * len(executed) / max(total, 1), 1),
                    }

        branches_hit = self._lines_to_branches(executed_per_file)
        self._cumulative_branches_hit |= branches_hit

        for fpath, lines in executed_per_file.items():
            self._cumulative_lines.setdefault(fpath, set())
            self._cumulative_lines[fpath] |= lines

        return {
            "branches_hit": sorted(branches_hit, key=lambda b: int(b[1:])),
            "branch_coverage_pct": round(
                100 * len(branches_hit) / max(len(ALL_BRANCH_IDS), 1), 1
            ),
            "line_data": line_cov_data,
        }

    def _lines_to_branches(
        self, executed_per_file: Dict[str, Set[int]]
    ) -> Set[str]:
        """Determine which branch IDs were hit based on executed lines."""
        hit: Set[str] = set()
        for branch_id, file_lines in _BRANCH_LINE_MAP.items():
            for fpath, lines in file_lines.items():
                executed = executed_per_file.get(fpath, set())
                if any(ln in executed for ln in lines):
                    hit.add(branch_id)
                    break
        return hit

    def get_cumulative_report(self) -> Dict[str, Any]:
        """Return aggregate coverage across all tests run so far."""
        return {
            "branches_hit": sorted(
                self._cumulative_branches_hit, key=lambda b: int(b[1:])
            ),
            "branches_missing": sorted(
                set(ALL_BRANCH_IDS) - self._cumulative_branches_hit,
                key=lambda b: int(b[1:]),
            ),
            "branch_coverage_pct": round(
                100 * len(self._cumulative_branches_hit) / max(len(ALL_BRANCH_IDS), 1),
                1,
            ),
            "total_branches": len(ALL_BRANCH_IDS),
        }

    def reset(self):
        self._cumulative_lines.clear()
        self._cumulative_branches_hit.clear()

    @staticmethod
    def _empty_report() -> Dict[str, Any]:
        return {
            "branches_hit": [],
            "branch_coverage_pct": 0.0,
            "line_data": {},
        }


# ---------------------------------------------------------------------------
# Static branch predictor — estimates coverage *before* running a test
# ---------------------------------------------------------------------------

def predict_branches(test_case: Dict[str, Any]) -> List[str]:
    """Estimate which branch IDs a test case will hit, based on its structure.

    This is intentionally a heuristic — it cannot be exact without execution —
    but it gives the test selector a useful signal for the set-cover algorithm.
    """
    predicted: Set[str] = set()
    grant = test_case.get("grant_permission", {})
    spec = grant.get("resource_value_specification", "")
    action = grant.get("action", "")

    has_wildcard = "(?)" in spec
    depth = spec.count("::")  # 0 = root-only, 1 = two levels, etc.

    # Phase A (with permission) will exercise the "allowed" path
    predicted.update({"B2", "B4", "B8", "B13"})

    # Phase B (without permission) will exercise the "denied" path
    predicted.update({"B3", "B5"})

    # Tree building
    if has_wildcard:
        predicted.add("B16")  # non-special path
        predicted.add("B22")  # rule-wildcard match
    else:
        predicted.add("B15")  # has_special_value path
        predicted.add("B20")  # exact-value match

    if depth >= 1:
        predicted.add("B24")  # children comparison
        predicted.add("B17")  # parent_has_special

    if depth >= 2:
        predicted.add("B18")  # node_value None fill

    # Phase B denial means the tree won't match -> B14
    predicted.add("B14")

    # If there are already predicted_branches from the LLM, merge them
    llm_predicted = test_case.get("predicted_branches", [])
    for b in llm_predicted:
        if b in BRANCH_CATALOG:
            predicted.add(b)

    return sorted(predicted, key=lambda b: int(b[1:]))
