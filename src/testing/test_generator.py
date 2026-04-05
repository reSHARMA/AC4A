"""LLM-driven test generation for the permission system.

Uses minimal-grant design: each test grants exactly the permission being tested,
then removes it and verifies the agent is blocked.  This avoids the combinatorial
explosion of carving exceptions out of broad wildcards.
"""

import inspect
import json
import logging
import re
from typing import Any, Dict, List, Optional

from src.utils.dummy_data import call_openai_api
from src.utils.resource_type_tree import ResourceTypeTree

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tree_to_text(tree: ResourceTypeTree, indent: int = 0) -> str:
    """Serialise a ResourceTypeTree to a human-readable indented string."""
    lines: List[str] = []
    key, value = list(tree.value.items())[0]
    desc = f" -- {tree.description}" if tree.description else ""
    exs = f" (examples: {tree.examples})" if tree.examples else ""
    lines.append(f"{'  ' * indent}{key}: {value}{desc}{exs}")
    for child in tree.children:
        lines.append(_tree_to_text(child, indent + 1))
    return "\n".join(lines)


def _get_annotation_source(annotation_cls) -> str:
    """Return the source code of the APIAnnotation class for LLM context."""
    try:
        return inspect.getsource(annotation_cls)
    except (TypeError, OSError):
        return "(source unavailable)"


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a permission-system test designer.  You will receive:
1. A resource type tree (hierarchical schema of resources and their metadata).
2. The source code of the permission annotation class that maps API calls to
   resource_value_specification strings and action types.
3. A list of action types (e.g. Read, Write, Create).

=== PERMISSION SYNTAX AND SEMANTICS ===

Each policy has two keys: `resource_value_specification` and `action`.

**resource_value_specification** identifies the specific data being accessed.
It follows this grammar:

  data = Namespace:Key(value)
  spec = data ( "::" data )*

- Every segment MUST be Namespace:Key(value).  Bare names without parentheses
  are INVALID.  "Calendar" alone is INVALID.  "Calendar:Year" alone is INVALID.
- `value` is either a concrete value or `?` (wildcard meaning any).
- There must ALWAYS be a value: Calendar:Month(December) is valid,
  Calendar:Month is NOT valid.
- `?` can be used as a wildcard value: Calendar:Month(?) allows all months.
- Segments are separated by :: and MUST follow the parent→child hierarchy of
  the resource tree.  A child can only follow its parent.
  Calendar:Year(2025)::Calendar:Month(July)::Calendar:Day(14) is valid.
  Calendar:Day(14)::Calendar:Year(2025) is INVALID (wrong order).

**action** is one of: Read, Write, Create.
- Read: viewing, checking, searching, or retrieving existing data.
- Write: modifying, updating, editing existing data.
- Create: adding new data or creating new resources.

**Valid examples:**
  "Calendar:Year(2025)" — access to all of year 2025
  "Calendar:Year(2025)::Calendar:Month(December)::Calendar:Day(15)" — one day
  "Calendar:Year(?)::Calendar:Month(?)" — all months of all years
  "Wallet:CreditCard(Alaska Airline)" — one specific credit card
  "Expedia:Destination(Japan)::Expedia:Flight(?)" — all flights to Japan

=== YOUR TASK ===

Produce a JSON array of test cases.  Each test case follows the
**minimal-grant** pattern:
  - grant_permission: a JSON object with exactly two keys:
      "resource_value_specification": a VALID spec string per the rules above
      "action": one of the action types
  - task_with_permission: a natural-language task that exercises that permission
    (should succeed when the permission is present).
  - task_without_permission: a natural-language task that should be blocked when
    the permission is removed.
  - expected_behavior: human-readable description of what should happen.
  - predicted_branches: list of branch IDs (B1-B25) this test is likely to hit.

Rules:
- Use concrete example values from the tree metadata.
- Cover all action types and tree depths.  Aim for diversity:
  * Root-level grants vs leaf-level grants
  * Each action type (Read, Write, Create)
  * Boundary values from the examples
- For predicted_branches, reason about which code paths will fire:
  * B1: system disabled  B2: OR-match  B3: no-match/denied
  * B4: needs-emptied  B5: needs-remain
  * B6: rule wildcard skip  B7: expiry  B8: fully-covers  B9: partial  B10: build-needs
  * B11: no-rule-value  B12: resource-difference  B13: tree-covers  B14: tree-no-match
  * B15: has-special-value  B16: non-special  B17: parent-has-special  B18: node-value-none
  * B19: key-mismatch  B20: exact-value-match  B21: request-wildcard  B22: rule-wildcard
  * B23: value-mismatch  B24: children-compare  B25: no-corresponding-child
- Return ONLY a JSON array (no markdown fences, no explanation).

Generate exactly {num_tests} test cases.
"""

_USER_PROMPT = """\
=== RESOURCE TYPE TREE ===
{tree_text}

=== ANNOTATION CLASS SOURCE ===
{annotation_source}

=== ACTION TYPES ===
{actions}

=== REMINDER ===
resource_value_specification MUST follow the Namespace:Key(value) grammar.
Every :: segment needs parentheses with a value.
Valid: "Calendar:Year(2025)::Calendar:Month(December)::Calendar:Day(31)"
Valid: "Calendar:Year(?)" (wildcard)
INVALID: "Calendar", "Calendar::Calendar:Year(2025)", "Calendar:Month"

Generate {num_tests} test cases as a JSON array.
"""


# ---------------------------------------------------------------------------
# Web-page prompt (for browser.agents.json entries)
# ---------------------------------------------------------------------------

_WEB_SYSTEM_PROMPT = """\
You are a permission-system test designer for web-page access control.
You will receive a URL and its permission mapping (read/write/create selectors
and resource-data associations from browser.agents.json).

=== PERMISSION SYNTAX ===

The grant_permission for web tests has two keys:
  "data_type": a resource string following the Namespace:Key(value) grammar.
    Every segment is Namespace:Key(value) separated by ::
    value is either a concrete string or ? (wildcard).
    Examples: "Expedia:Flight(?)", "Calendar:Year(2025)::Calendar:Month(June)"
    INVALID: bare names without (value) like "Expedia" or "Calendar:Month"
  "selector_type": one of "read", "write", or "create".

=== YOUR TASK ===

Produce a JSON array of test cases using minimal-grant design.
Each test case has:
  - grant_permission: a dict with "data_type" and "selector_type" per above.
  - task_with_permission: a browser instruction that exercises that permission.
  - task_without_permission: same instruction, expected to be blocked.
  - expected_behavior: description of both phases.
  - predicted_branches: branch IDs from B1-B25.

Return ONLY a JSON array.  Generate exactly {num_tests} test cases.
"""

_WEB_USER_PROMPT = """\
=== URL ===
{url}

=== PERMISSION MAPPING ===
{mapping_json}

Generate {num_tests} test cases as a JSON array.
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_api_tests(
    app_name: str,
    resource_trees: List[ResourceTypeTree],
    annotation_cls,
    action_names: List[str],
    num_tests: int = 20,
) -> List[Dict[str, Any]]:
    """Generate test cases for an API-based application.

    Args:
        app_name: e.g. "calendar", "wallet"
        resource_trees: root ResourceTypeTree nodes registered for the app
        annotation_cls: the APIAnnotation class (used to extract source)
        action_names: e.g. ["Read", "Write", "Create"]
        num_tests: how many tests to generate
    Returns:
        List of test-case dicts.
    """
    tree_text = "\n\n".join(_tree_to_text(t) for t in resource_trees)
    annotation_source = _get_annotation_source(annotation_cls)

    system = _SYSTEM_PROMPT.format(num_tests=num_tests)
    user = _USER_PROMPT.format(
        tree_text=tree_text,
        annotation_source=annotation_source,
        actions=", ".join(action_names),
        num_tests=num_tests,
    )

    raw = call_openai_api(system, user, "perm")
    tests = _parse_json_array(raw, app_name)

    for i, t in enumerate(tests):
        t.setdefault("test_id", f"{app_name}-{i}")
        t["app"] = app_name

    logger.info("Generated %d API tests for %s", len(tests), app_name)
    return tests


def generate_web_tests(
    url: str,
    mapping: Dict[str, Any],
    num_tests: int = 10,
) -> List[Dict[str, Any]]:
    """Generate test cases for a web-page permission mapping.

    Args:
        url: the page URL key from browser.agents.json
        mapping: the dict value for that URL (read, write, create, data, etc.)
        num_tests: how many tests to generate
    Returns:
        List of test-case dicts.
    """
    system = _WEB_SYSTEM_PROMPT.format(num_tests=num_tests)
    user = _WEB_USER_PROMPT.format(
        url=url,
        mapping_json=json.dumps(mapping, indent=2),
        num_tests=num_tests,
    )

    raw = call_openai_api(system, user, "perm")
    domain = url.split("/")[2] if "/" in url else url
    tests = _parse_json_array(raw, domain)

    for i, t in enumerate(tests):
        t.setdefault("test_id", f"web-{domain}-{i}")
        t["app"] = domain
        t["url"] = url

    logger.info("Generated %d web tests for %s", len(tests), url)
    return tests


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _parse_json_array(raw: str, context: str) -> List[Dict[str, Any]]:
    """Best-effort parse of an LLM JSON array response."""
    raw = raw.strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
        raw = raw.strip()

    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return parsed
        logger.warning("LLM returned non-array JSON for %s, wrapping", context)
        return [parsed]
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse LLM response for %s: %s", context, exc)
        logger.debug("Raw response: %s", raw[:500])
        return []
