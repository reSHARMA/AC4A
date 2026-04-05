"""Coverage trackers for the permission testing system.

Two distinct coverage models:

1. **BrowserMappingCoverageTracker** — for web/browser tests.
   Tracks which ``(data_type, selector_type)`` entries from
   ``browser.agents.json`` were exercised during tests.  This is a
   *data-coverage* metric (not code-coverage).

2. **AnnotationCoverageTracker** — for API tests.
   Uses Python's ``coverage`` library to measure line-level coverage of
   the annotation class file (the ``generate_attributes`` / ``get_hierarchy``
   / ``get_access_level`` mapping functions).

Both expose the same report shape so the frontend can render them uniformly:
``branches_hit`` / ``branches_missing`` / ``branch_coverage_pct`` /
``total_branches``.  For browser tests, each "branch" is a
``data_type::selector_type`` entry.  For API tests, each "branch" is a
line in the annotation file that was executed.
"""

import json
import logging
import os
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# =========================================================================
# 1. Browser Mapping Coverage
# =========================================================================

class BrowserMappingCoverageTracker:
    """Track which ``(data_type, selector_type)`` entries from
    ``browser.agents.json`` were exercised during browser tests.

    Each entry in the config's ``data`` dict, combined with whether its
    selectors appear in ``read`` / ``write`` / ``create``, produces one
    coverable unit.  The "branch ID" for display is
    ``"data_type::selector_type"`` (e.g. ``"Expedia:Flight(?)::read"``).
    """

    def __init__(self, url_pattern: str = ""):
        self._universe: Set[str] = set()
        self._hits: Set[str] = set()
        self._url_pattern = url_pattern
        self._load_universe()

    def _load_universe(self):
        """Build the set of all coverable entries from browser.agents.json."""
        config_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "web", "agent", "agents",
            "browser.agents.json",
        )
        config_path = os.path.normpath(config_path)
        if not os.path.exists(config_path):
            logger.warning("browser.agents.json not found at %s", config_path)
            return

        try:
            with open(config_path) as f:
                config = json.load(f)
        except Exception as exc:
            logger.warning("Failed to load browser.agents.json: %s", exc)
            return

        import re
        for url, mapping in config.items():
            if self._url_pattern:
                pattern = self._url_pattern.replace("*", ".*")
                if not re.match(pattern, url):
                    continue

            read_sels = set(mapping.get("read", []))
            write_sels = set(mapping.get("write", []))
            create_sels = set(mapping.get("create", []))

            for data_type, selectors in mapping.get("data", {}).items():
                for sel in selectors:
                    if sel in read_sels:
                        self._universe.add(f"{data_type}::read")
                    if sel in write_sels:
                        self._universe.add(f"{data_type}::write")
                    if sel in create_sels:
                        self._universe.add(f"{data_type}::create")

        logger.info("Browser mapping universe: %d entries for pattern '%s'",
                     len(self._universe), self._url_pattern)

    def record_hit(self, data_type: str, selector_type: str):
        """Mark a (data_type, selector_type) pair as exercised."""
        key = f"{data_type}::{selector_type.lower()}"
        self._hits.add(key)

    def get_report(self) -> Dict[str, Any]:
        total = len(self._universe)
        hit = self._hits & self._universe
        missing = self._universe - hit
        return {
            "coverage_type": "browser_mapping",
            "branches_hit": sorted(hit),
            "branches_missing": sorted(missing),
            "branch_coverage_pct": round(
                100 * len(hit) / max(total, 1), 1
            ),
            "total_branches": total,
        }

    def get_cumulative_report(self) -> Dict[str, Any]:
        return self.get_report()

    def reset(self):
        self._hits.clear()

    @staticmethod
    def empty_report() -> Dict[str, Any]:
        return {
            "coverage_type": "browser_mapping",
            "branches_hit": [],
            "branches_missing": [],
            "branch_coverage_pct": 0.0,
            "total_branches": 0,
        }


# =========================================================================
# 2. Annotation (API) Coverage
# =========================================================================

class AnnotationCoverageTracker:
    """Measure line-level coverage of an API annotation class file.

    Instead of the old B1-B25 branch IDs mapped to policy_system.py, this
    instruments the *annotation file* (e.g. ``calendar_agent.py``) which
    contains ``generate_attributes``, ``get_hierarchy``, ``get_access_level``
    — the mapping from API calls to resource specs.

    "Branches" reported are individual source lines in the annotation file
    that were executed, labelled as ``L<line_number>``.
    """

    def __init__(self, annotation_file: str):
        """
        Args:
            annotation_file: relative path to the annotation source file,
                e.g. ``"web/agent/agents/calendar_agent.py"``
        """
        self._annotation_file = annotation_file
        self._abs_path = os.path.abspath(
            os.path.join(os.getcwd(), annotation_file)
        )
        self._cumulative_executed: Set[int] = set()
        self._cumulative_missing: Set[int] = set()
        self._total_lines: int = 0

    def run_with_coverage(
        self, func: Callable, *args: Any, **kwargs: Any
    ) -> Tuple[Any, Dict[str, Any]]:
        """Execute *func* while collecting line coverage of the annotation file."""
        try:
            import coverage as cov_lib
        except ImportError:
            logger.warning("coverage library not installed")
            result = func(*args, **kwargs)
            return result, self._empty_report()

        cov = cov_lib.Coverage(branch=True, include=[self._abs_path])
        cov.start()
        try:
            result = func(*args, **kwargs)
        finally:
            cov.stop()
            cov.save()

        report = self._extract(cov)
        return result, report

    def _extract(self, cov) -> Dict[str, Any]:
        executed: Set[int] = set()
        missing: Set[int] = set()

        for measured_file in cov.get_data().measured_files():
            if os.path.abspath(measured_file) != self._abs_path:
                continue
            try:
                analysis = cov.analysis2(measured_file)
                executed = set(analysis[1])
                missing = set(analysis[3])
            except Exception:
                continue

        self._cumulative_executed |= executed
        self._cumulative_missing = (
            (self._cumulative_missing | missing) - self._cumulative_executed
        )
        total = len(executed) + len(missing)
        if total > self._total_lines:
            self._total_lines = total

        pct = round(100 * len(executed) / max(total, 1), 1)
        return {
            "coverage_type": "annotation",
            "annotation_file": self._annotation_file,
            "branches_hit": [f"L{ln}" for ln in sorted(executed)],
            "branches_missing": [f"L{ln}" for ln in sorted(missing)],
            "branch_coverage_pct": pct,
            "total_branches": total,
            "executed_count": len(executed),
            "missing_count": len(missing),
        }

    def get_cumulative_report(self) -> Dict[str, Any]:
        total = self._total_lines or (
            len(self._cumulative_executed) + len(self._cumulative_missing)
        )
        executed = len(self._cumulative_executed)
        return {
            "coverage_type": "annotation",
            "annotation_file": self._annotation_file,
            "branches_hit": [f"L{ln}" for ln in sorted(self._cumulative_executed)],
            "branches_missing": [f"L{ln}" for ln in sorted(self._cumulative_missing)],
            "branch_coverage_pct": round(
                100 * executed / max(total, 1), 1
            ),
            "total_branches": total,
            "executed_count": executed,
            "missing_count": len(self._cumulative_missing),
        }

    def reset(self):
        self._cumulative_executed.clear()
        self._cumulative_missing.clear()
        self._total_lines = 0

    def _empty_report(self) -> Dict[str, Any]:
        return {
            "coverage_type": "annotation",
            "annotation_file": self._annotation_file,
            "branches_hit": [],
            "branches_missing": [],
            "branch_coverage_pct": 0.0,
            "total_branches": 0,
            "executed_count": 0,
            "missing_count": 0,
        }


# =========================================================================
# Static predictors for test selection
# =========================================================================

def predict_coverage_units(test_case: Dict[str, Any]) -> List[str]:
    """Predict which coverage units a test will hit.

    For web tests: returns ``["data_type::selector_type"]`` entries.
    For API tests: returns a small set of heuristic labels derived from
    the grant structure.
    """
    grant = test_case.get("grant_permission", {})
    if not isinstance(grant, dict):
        grant = {}

    is_web = "data_type" in grant or "selector_type" in grant

    if is_web:
        data_type = grant.get("data_type", "")
        selector_type = grant.get("selector_type", "read").lower()
        if data_type:
            return [f"{data_type}::{selector_type}"]
        return []

    spec = grant.get("resource_value_specification", "")
    action = grant.get("action", "Read")
    units: List[str] = []
    if spec:
        units.append(f"spec::{spec}")
    if action:
        units.append(f"action::{action}")
    depth = spec.count("::")
    units.append(f"depth::{depth}")
    if "(?)" in spec:
        units.append("wildcard::yes")
    else:
        units.append("wildcard::no")

    llm_predicted = test_case.get("predicted_branches", [])
    if isinstance(llm_predicted, list):
        for b in llm_predicted:
            units.append(str(b).strip())

    return units


# Keep old names importable for backward compatibility
def branch_sort_key(branch_id: str) -> int:
    """Sort branch/coverage IDs safely."""
    b = str(branch_id).strip()
    if b.startswith("B") and len(b) >= 2:
        try:
            return int(b[1:])
        except ValueError:
            return 0
    if b.startswith("L") and len(b) >= 2:
        try:
            return int(b[1:])
        except ValueError:
            return 0
    return hash(b) % 10000


# Legacy alias
predict_branches = predict_coverage_units
