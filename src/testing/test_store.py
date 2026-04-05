"""Persistence layer for test suites and test results.

Test suites are keyed by (app_name, hash) where the hash is derived from
the resource type tree structure **and** the permission function source code.
When either changes the hash changes and cached tests are invalidated.
"""

import hashlib
import inspect
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.utils.resource_type_tree import ResourceTypeTree

logger = logging.getLogger(__name__)

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
_TESTS_DIR = os.path.join(_DATA_DIR, "tests")
_RESULTS_DIR = os.path.join(_DATA_DIR, "test_results")


def _ensure_dirs():
    os.makedirs(_TESTS_DIR, exist_ok=True)
    os.makedirs(_RESULTS_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------

def compute_api_hash(
    resource_trees: List[ResourceTypeTree],
    annotation_cls,
    action_names: List[str],
) -> str:
    """Stable hash of tree structure + annotation source + actions."""
    parts: List[str] = []
    for tree in resource_trees:
        parts.append(tree.get_tree_string())
    try:
        parts.append(inspect.getsource(annotation_cls))
    except (TypeError, OSError):
        parts.append("(source unavailable)")
    parts.extend(sorted(action_names))
    blob = "\n---\n".join(parts).encode()
    return hashlib.sha256(blob).hexdigest()[:12]


def compute_web_hash(mapping: Dict[str, Any]) -> str:
    """Stable hash of a browser.agents.json URL entry."""
    blob = json.dumps(mapping, sort_keys=True).encode()
    return hashlib.sha256(blob).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Test suite persistence
# ---------------------------------------------------------------------------

def _suite_path(app_name: str, tree_hash: str) -> str:
    return os.path.join(_TESTS_DIR, f"{app_name}_{tree_hash}.json")


def save_test_suite(
    app_name: str,
    tree_hash: str,
    tests: List[Dict[str, Any]],
) -> str:
    """Save a test suite and return the file path."""
    _ensure_dirs()
    path = _suite_path(app_name, tree_hash)
    payload = {
        "app": app_name,
        "tree_hash": tree_hash,
        "generated_at": datetime.utcnow().isoformat(),
        "test_count": len(tests),
        "tests": tests,
    }
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    logger.info("Saved %d tests to %s", len(tests), path)
    return path


def load_test_suite(
    app_name: str, tree_hash: str
) -> Optional[Dict[str, Any]]:
    """Load a test suite if it exists and the hash matches."""
    path = _suite_path(app_name, tree_hash)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        data = json.load(f)
    if data.get("tree_hash") != tree_hash:
        logger.info("Hash mismatch for %s — cached tests stale", app_name)
        return None
    return data


def list_test_suites() -> List[Dict[str, Any]]:
    """Return metadata for all stored test suites."""
    _ensure_dirs()
    suites = []
    for fname in os.listdir(_TESTS_DIR):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(_TESTS_DIR, fname)
        try:
            with open(path) as f:
                data = json.load(f)
            suites.append({
                "file": fname,
                "app": data.get("app"),
                "tree_hash": data.get("tree_hash"),
                "generated_at": data.get("generated_at"),
                "test_count": data.get("test_count", 0),
            })
        except Exception as exc:
            logger.warning("Skipping invalid suite file %s: %s", fname, exc)
    return suites


def load_all_suites_for_app(app_name: str) -> List[Dict[str, Any]]:
    """Load full suite data (including tests) for every suite matching *app_name*."""
    _ensure_dirs()
    results: List[Dict[str, Any]] = []
    for fname in sorted(os.listdir(_TESTS_DIR)):
        if not fname.startswith(f"{app_name}_") or not fname.endswith(".json"):
            continue
        path = os.path.join(_TESTS_DIR, fname)
        try:
            with open(path) as f:
                results.append(json.load(f))
        except Exception as exc:
            logger.warning("Skipping invalid suite file %s: %s", fname, exc)
    return results


def load_all_suites() -> List[Dict[str, Any]]:
    """Load full suite data for every stored suite."""
    _ensure_dirs()
    results: List[Dict[str, Any]] = []
    for fname in sorted(os.listdir(_TESTS_DIR)):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(_TESTS_DIR, fname)
        try:
            with open(path) as f:
                results.append(json.load(f))
        except Exception as exc:
            logger.warning("Skipping invalid suite file %s: %s", fname, exc)
    return results


def delete_test_from_suite(
    app_name: str, tree_hash: str, test_id: str
) -> bool:
    """Remove a single test from a saved suite. Returns True if found and removed."""
    path = _suite_path(app_name, tree_hash)
    if not os.path.exists(path):
        return False
    with open(path) as f:
        data = json.load(f)
    original_count = len(data.get("tests", []))
    data["tests"] = [t for t in data.get("tests", []) if t.get("test_id") != test_id]
    if len(data["tests"]) == original_count:
        return False
    data["test_count"] = len(data["tests"])
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    logger.info("Deleted test %s from suite %s/%s", test_id, app_name, tree_hash)
    return True


# ---------------------------------------------------------------------------
# Test results persistence
# ---------------------------------------------------------------------------

def save_test_results(
    app_name: str,
    tree_hash: str,
    results: List[Dict[str, Any]],
    cumulative_coverage: Dict[str, Any],
) -> str:
    """Save a completed test run's results."""
    _ensure_dirs()
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    fname = f"{app_name}_{tree_hash}_{ts}.json"
    path = os.path.join(_RESULTS_DIR, fname)
    payload = {
        "app": app_name,
        "tree_hash": tree_hash,
        "run_at": datetime.utcnow().isoformat(),
        "result_count": len(results),
        "results": results,
        "cumulative_coverage": cumulative_coverage,
    }
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    logger.info("Saved %d results to %s", len(results), path)
    return path


def load_latest_results(app_name: str) -> Optional[Dict[str, Any]]:
    """Load the most recent results file for an app."""
    _ensure_dirs()
    candidates = [
        f for f in os.listdir(_RESULTS_DIR)
        if f.startswith(f"{app_name}_") and f.endswith(".json")
    ]
    if not candidates:
        return None
    candidates.sort(reverse=True)
    path = os.path.join(_RESULTS_DIR, candidates[0])
    with open(path) as f:
        return json.load(f)


def list_test_results() -> List[Dict[str, Any]]:
    """Return metadata for all stored test results."""
    _ensure_dirs()
    results = []
    for fname in os.listdir(_RESULTS_DIR):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(_RESULTS_DIR, fname)
        try:
            with open(path) as f:
                data = json.load(f)
            results.append({
                "file": fname,
                "app": data.get("app"),
                "tree_hash": data.get("tree_hash"),
                "run_at": data.get("run_at"),
                "result_count": data.get("result_count", 0),
            })
        except Exception as exc:
            logger.warning("Skipping invalid result file %s: %s", fname, exc)
    return results
