### resource_difference: core semantic properties (calendar examples)

### Identity

Description: If `have` fully covers `need`, nothing remains. With no `have`, the entire `need` remains. If nothing is needed, nothing remains regardless of `have`.

- resource_difference(N, N) = ∅
- resource_difference(N, ∅) = N
- resource_difference(∅, H) = ∅

Examples:
- Unix: Need [{"Calendar:UnixTimestamp": "1704067200"}], Have [{"Calendar:UnixTimestamp": "1704067200"}] → Difference ∅
- Event Types: Need [{"Calendar:Reminder": "Pay_Bills"}], Have [{"Calendar:Reminder": "Pay_Bills"}] → Difference ∅
- YMD: Need [{"Calendar:Year": "2025", "Calendar:Month": "January"}], Have [{"Calendar:Year": "2025", "Calendar:Month": "January"}] → Difference ∅
- Quarters: Need [{"Calendar:Year": "2025", "Calendar:Quarter": "Q2"}], Have [{"Calendar:Year": "2025", "Calendar:Quarter": "Q2"}] → Difference ∅

### Monotonicity in Have

Description: If H covers H′, having H cannot increase what remains; it can only keep it the same or reduce it.

Formal: H covers H′ ⇒ resource_difference(N, H) ⊆ resource_difference(N, H′)

Examples:
- Unix: Need [{"Calendar:UnixTimestamp": "1704067200"}]
  - Have H′ [{"Calendar:UnixTimestamp": "1704067201"}] → Difference = Need
  - Have H  [{"Calendar:UnixTimestamp": "?"}]         → Difference ∅  (∅ ⊆ Need)
- Event Types: Need [{"Calendar:Meeting": "Team_Standup"}]
  - Have H′ [{"Calendar:Event": "Other"}] → Difference = Need
  - Have H  [{"Calendar:Event": "?"}]     → Difference ∅  (∅ ⊆ Need)
- YMD: Need [{"Calendar:Year": "2025", "Calendar:Month": "January"}]
  - Have H′ [{"Calendar:Year": "2025", "Calendar:Month": "February"}] → Difference = Need
  - Have H  [{"Calendar:Year": "2025", "Calendar:Month": "?"}]        → Difference ∅
- Quarters: Need [{"Calendar:Year": "2025", "Calendar:Quarter": "?"}]
  - Have H′ [{"Calendar:Year": "2025", "Calendar:Quarter": "Q2"}] → Difference {Q1, Q3, Q4}
  - Have H  [{"Calendar:Year": "2025", "Calendar:Quarter": "?"}]  → Difference ∅

### Conservativeness

Description: The function never under-reports unmet access. Any portion of `need` not covered by `have` appears in the difference—either as the exact descriptor or a sound, possibly coarser wildcard still enclosing that unmet portion.

Examples:
- Unix: Need [{"Calendar:UnixTimestamp": "1704067200"}], Have [{"Calendar:UnixTimestamp": "1704067201"}] → Difference = Need
- Event Types: Need [{"Calendar:Reminder": "Pay_Bills"}], Have [{"Calendar:Reminder": "Submit_Taxes"}] → Difference = Need
- YMD: Need [{"Calendar:Year": "2025", "Calendar:Event": "?"}], Have [{"Calendar:Year": "2025", "Calendar:Event": "Project_Kickoff"}] → Difference = Need
- Quarters (precise missing set): Need [{"Calendar:Year": "2025", "Calendar:Quarter": "?"}], Have [{"Calendar:Year": "2025", "Calendar:Quarter": "Q2"}] → Difference {Q1, Q3, Q4}

### Order Independence of Iterative Reduction

Description: Iterating over multiple granted permissions ("haves") in any order yields the same semantic remainder of unmet `need`.

Why it holds: Identity + Monotonicity in Have + Conservativeness ensure each step can only maintain or reduce the remaining `need` without under-reporting; reordering cannot change what stays unmet (only transient representation precision).

Examples:
- Quarters:
  - Need N = [{"Calendar:Year": "2025", "Calendar:Quarter": "?"}]
  - Have A = [{"Calendar:Year": "2025", "Calendar:Quarter": "Q2"}]
  - Have B = [{"Calendar:Year": "2025", "Calendar:Quarter": "Q3"}]
  - Order A then B: Difference after A = {Q1, Q3, Q4} → after B = {Q1, Q4}
  - Order B then A: Difference after B = {Q1, Q2, Q4} → after A = {Q1, Q4}
  - Final Difference is {Q1, Q4} in both orders.
- Event Types:
  - Need N = [{"Calendar:Meeting": "Team_Standup"}]
  - Have A = [{"Calendar:Event": "?"}], Have B = [{"Calendar:Meeting": "Team_Standup"}]
  - Applying either first yields Difference ∅ after both; order does not matter.


### Iterative Reduction Algorithm

Conceptual loop to progressively reduce unmet `need` given a list of granted `haves`.

Pseudo-code (avoids in-loop mutation):

```
remaining = list(initial_need)  # each element is a need descriptor (possibly coarse)
for have in haves:               # order does not matter (commutativity property)
   next_remaining = []
   for n in remaining:
      diff_list = resource_difference(n, have)
      # diff_list may:
      #   - be empty (need fully satisfied by have)
      #   - contain the original n (unsatisfied)
      #   - contain several more specific descriptors that partition the unmet portion
      next_remaining.extend(diff_list)
   remaining = normalize(next_remaining)  # optional: merge, deduplicate, canonicalize
   if not remaining:
      break
```

Stopping: Exit early if `remaining` becomes empty or after all `haves` are applied.

normalize(x): merge equivalent descriptors, deduplicate, optionally coalesce adjacent fragments for performance; does not change semantic extent.

### Need Expansion vs Semantic Monotonic Decrease

Even though the count of items in `remaining` can increase after applying a `have`, the *semantic* unmet region monotonically decreases (never expands). This happens because a coarse need can be refined into multiple more specific unmet fragments. Cardinality growth is a refinement, not an increase in total unmet access.

Example (Year → Months):
- Initial Need: `{ Year: 2025 }` (interpreted as all months in 2025)
- Have: `{ Year: 2025, Month: October }`
- resource_difference produces 11 month-specific descriptors for Jan–Sep, Nov–Dec 2025.

Set size grew (1 → 11) but the union of those 11 descriptors equals the original need minus the covered month. The uncovered scope strictly shrank.

We can view each descriptor as an element in a lattice ordered by specificity. Refinement moves downward in the lattice while shrinking the covered semantic extent.

### Soundness vs Precision

- Soundness: No unmet access is omitted. If something is still needed, it appears—either exactly or via a broader wildcard over-approximation.
- Precision: How narrowly the remaining set describes the unmet portion. Lower precision is acceptable if we remain sound.

Two outcomes for the same input can both be sound:
1. Need `{Year:2025}` with Have `{Year:2025, Month:October}` → Remaining represented coarsely as `{Year:2025}` (sound but imprecise; includes already-covered October inside broad descriptor)
2. Need `{Year:2025}` with same Have → Remaining expanded to 11 specific month descriptors excluding October (sound and more precise)

Preference: Higher precision accelerates exhaustion because subsequent `haves` match smaller units directly. Coarse but sound descriptors still preserve correctness; later applications refine away already-covered fragments.

### Ordering Independence (Union Equivalence)

For a set of `haves` H1, H2, ..., Hk, iterative application in any order yields a final `remaining` equivalent (modulo precision differences) to computing:

```
remaining_final ≈ resource_difference(Need, H1 ∪ H2 ∪ ... ∪ Hk)
```

Because each step only removes (or refines) unmet access and never reintroduces covered pieces (Monotonicity + Conservativeness), permutation of application order cannot change which semantic portions remain uncovered—only representation granularity may differ transiently.

Formally (semantic set difference):
```
Need - (H1 ∪ H2) = (Need - H1) - H2 = (Need - H2) - H1
```
By induction this generalizes to any finite sequence.

### Formal Induction Proof (Ordering Independence)

Goal: Show that for any finite multiset of haves H = {H1, H2, ..., Hk} and any permutation π of {1..k}, iterative application of `resource_difference` in the order H_{π(1)}, H_{π(2)}, ..., H_{π(k)} yields a final semantic remainder equal to N − (⋃_{i=1..k} H_i). Representation may differ (precision) but covers exactly the same unmet region.

Definitions:
- Let Diff(N, H) denote the semantic set difference (ideal precise result) that `resource_difference` over-approximates soundly.
- Let RD_seq(N; H1,...,Hm) be the semantic remainder after sequentially applying `resource_difference` with H1 through Hm, using precise refinement (conceptual ideal).

We use the following axioms:
1. Soundness: Each step removes only covered portion; unmet portion persists.
2. Monotonicity: If H covers H′ then Diff(N, H) ⊆ Diff(N, H′).
3. Full Coverage: Diff(N, N) = ∅.
4. Set Semantics: Diff(N, H) = N − H (ideal precise coverage interpretation).

Claim: RD_seq(N; H1,...,Hk) = N − (⋃_{i=1..k} H_i) regardless of order.

Proof: By induction on k ≥ 1.

Base (k = 1): RD_seq(N; H1) = Diff(N, H1) = N − H1 = N − (⋃ H_i). Holds.

Inductive Step: Assume for k = m (m ≥ 1) and any ordering of {H1,...,Hm} we have RD_seq(N; H_{σ(1)},...,H_{σ(m)}) = N − (⋃_{i=1..m} H_i).

Consider k = m + 1. Let the sequence order be an arbitrary permutation τ of {1..m+1}. Split τ into first element H_{τ(1)} and the rest R = {H_{τ(2)},...,H_{τ(m+1)}}.

Define N1 = Diff(N, H_{τ(1)}) = N − H_{τ(1)} (semantic removal of covered portion). Apply the inductive hypothesis to N1 and the multiset R (size m). Hypothesis requires that sequential application to N1 over R yields N1 − (⋃ R) = (N − H_{τ(1)}) − (⋃ R).

Set algebra:
```
(N − H_{τ(1)}) − (⋃ R) = N − (H_{τ(1)} ∪ (⋃ R)) = N − (⋃_{i=1..m+1} H_i).
```
Thus RD_seq(N; H_{τ(1)}, R) = N − (⋃_{i=1..m+1} H_i).

Since τ was arbitrary, holds for all permutations. Therefore by induction the claim is true for all finite k.

Precision Note: If implementation produces a sound over-approximation S such that (N − (⋃ H_i)) ⊆ S ⊆ N − (⋃ H_i) ∪ P (where P are already-covered fragments), subsequent applications either remove or refine P away. Thus terminal sound representation converges to the same semantic set (possibly coarse). Ordering independence pertains to semantic equivalence, not necessarily identical descriptor lists.

QED.

### Additional Worked Examples

1. Year → Months (Single Have)
  - Need: `{Year:2025}`
  - Have: `{Year:2025, Month:October}`
  - Precise Difference: `{Year:2025, Month:Jan}`, `{Year:2025, Month:Feb}`, ..., `{Year:2025, Month:Dec}` excluding October.
  - Coarse Sound Difference (permissible): `{Year:2025}`

2. Year → Months (Multiple Haves)
  - Need: `{Year:2025}`
  - Haves: `{Year:2025, Month:October}`, `{Year:2025, Month:January}`
  - Precise Difference after both: 10 remaining months (Feb–Sep, Nov–Dec)
  - Any order leads to same 10-month set (commutativity).

3. Quarters Refinement
  - Need: `{Year:2025, Quarter:*}`
  - Have: `{Year:2025, Quarter:Q2}`
  - Difference: `{Q1, Q3, Q4}` (precise) or `{Year:2025, Quarter:*}` (coarse sound)

4. Event Category Wildcards
  - Need: `{Event:*, Reminder:Pay_Bills}` (structure allows combined specificity)
  - Have: `{Event:*}`
  - Precise Difference: none (wildcard covers subordinated reminder)
  - Coarse representation would also be empty—soundness forces removal here; no over-approximation remains because coverage is total.

5. Unix Timestamp Exact Match
  - Need: `{UnixTimestamp:1704067200}`
  - Have: `{UnixTimestamp:*}`
  - Difference: ∅ (cannot remain coarse since wildcard fully covers the singleton need)

### Formal Property Summary

Let N be a (possibly hierarchical) set of resource descriptors; H a descriptor or set of descriptors; `⊑` denote coverage (H ⊑ N means H provides all access N describes).

Properties:
1. Identity: resource_difference(N, N) = ∅
2. Null Have: resource_difference(N, ∅) = N
3. Null Need: resource_difference(∅, H) = ∅
4. Monotonicity (Have): H covers H′ ⇒ diff(N,H) ⊆ diff(N,H′)
5. Conservativeness (Soundness): diff(N,H) over-approximates the exact unmet portion; no unmet portion is omitted.
6. Order Independence: Sequentially applying diff with each Hi yields representation whose union equals N − (⋃ Hi).
7. Refinement Possibility: |diff(N,H)| may be > |N|; semantic extent strictly decreases.

### Glossary
- Descriptor: A structured token representing a slice of resource space (e.g., Year=2025, Month=January).
- Coverage: H covers N if every concrete element matched by N is also matched by H.
- Refinement: Replacing a descriptor by a set of more specific descriptors whose union equals the original minus covered parts.
- Soundness: Never missing an unmet portion (no false negatives).
- Precision: Avoiding unnecessary over-approximation (minimizing false positives within remaining set).
- Wildcard (`*`): Matches any value for the attribute and fully covers all specific instances of that attribute.

