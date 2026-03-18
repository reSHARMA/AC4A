"""Simplified resource difference utilities as per design.

Only expose the minimal primitives:
    difference_enum(need, have)
    difference_interval(need, have)                     # basic start/end containment using numeric compare
    difference_interval(need, have, compare)            # optional comparator for custom ordering/types
    difference_tree(need, have)                         # uses AttributeTree/ResourceTypeTree style subtree check

Each function returns set() when fully satisfied, else returns `need` unchanged.
They deliberately do NOT attempt to compute partial residual structures; applications
can layer richer domain-specific logic on top if desired.
"""
from __future__ import annotations

from typing import List, Dict, Callable, Optional, Tuple, Set, Any
from src.utils.attribute_tree import AttributeTree


def difference_enum(need: List[Dict[str, str]], have: List[Dict[str, str]]):
    """Enum difference: if identical (single key/value) return empty set else original need.

    Expectation: both lists contain a single dict with same key for equality to hold.
    """
    if not need:
        return set()
    if not have:
        return need
    n = need[0]
    h = have[0]
    return set() if n == h else need


def _extract_interval(lst: List[Dict[str, str]]) -> Tuple[str, str]:
    if not lst:
        return '', ''
    d = lst[0]
    return next(iter(d.items()))


def _parse_bounds(val: str) -> Tuple[Optional[int], Optional[int]]:
    if val == '?':
        return None, None
    if '-' not in val:
        return None, None
    s, e = val.split('-', 1)
    start = int(s) if s and s != '?' else None
    end = int(e) if e and e != '?' else None
    return start, end


def difference_interval(need: List[Dict[str, str]], have: List[Dict[str, str]], compare: Callable[[Any, Any], int] | None = None):
    """Interval difference.

    Rules:
      - Wildcard in have ('?') -> covers need.
      - Need wildcard '?' only covered if have wildcard.
      - Containment (have.start <= need.start AND have.end >= need.end with open bounds allowed) -> covered.
      - Otherwise (partial overlap or disjoint) -> return need.

    If a `compare` callable is supplied it must behave like: compare(a,b)<0 if a<b, 0 if equal, >0 if a>b.
    This is used for element-wise boundary comparisons when custom types are used.
    """
    if not need:
        return set()
    if not have:
        return need
    n_key, n_val = _extract_interval(need)
    h_key, h_val = _extract_interval(have)
    if n_key != h_key:
        return need
    # Wildcards
    if n_val == '?':
        return set() if h_val == '?' else need
    if h_val == '?':
        return set()

    n_start, n_end = _parse_bounds(n_val)
    h_start, h_end = _parse_bounds(h_val)

    def leq(a, b):
        if a is None or b is None:
            return True  # open bound considered universally leq
        if compare:
            return compare(a, b) <= 0
        return a <= b

    def geq(a, b):
        if a is None or b is None:
            return True
        if compare:
            return compare(a, b) >= 0
        return a >= b

    contained = leq(h_start, n_start) and geq(h_end, n_end)
    return set() if contained else need


def difference_tree(need: List[Dict[str, str]], have: List[Dict[str, str]]):
    """Tree difference using AttributeTree.check_subtree.

    We construct linear chains for the sequences of key/value dicts in order.
    If the need chain is a subtree of have chain (per check_subtree semantics) -> set().
    Else return need.
    """
    if not need:
        return set()
    if not have:
        return need

    def build_chain(pairs: List[Dict[str, str]]) -> AttributeTree:
        root = None
        current = None
        for d in pairs:
            key, val = next(iter(d.items()))
            node = AttributeTree(key, data=val)
            if root is None:
                root = node
                current = node
            else:
                current.children.append(node)
                current = node
        return root

    need_tree = build_chain(need)
    have_tree = build_chain(have)
    if need_tree is None or have_tree is None:
        return need
    res = need_tree.check_subtree(have_tree)
    return set() if res >= 0 else need


__all__ = [
    'difference_enum',
    'difference_interval',
    'difference_tree',
]
