# Algorithm

This document describes the algorithm implemented by **3D-BinPacking-CPSAT**.

The solver handles the following problem:

- all bins are identical and axis-aligned,
- bin and item dimensions are positive integers,
- item coordinates are integer-valued,
- every item must be packed,
- each item has its own rotation policy,
- the objective is to minimize the number of bins.

The implementation uses Google OR-Tools CP-SAT. The geometric non-overlap model does **not** use Big-M constraints.

---

## 1. Problem definition

Let the bin dimensions be

$$
(W, L, H).
$$

For each item $i$, the original dimensions are

$$
(w_i, l_i, h_i).
$$

A placement consists of:

- a bin index $b_i$,
- an integer origin $(x_i,y_i,z_i)$,
- an allowed orientation with effective dimensions $(d_i^x,d_i^y,d_i^z)$.

A solution is feasible if every item is inside its assigned bin and no two items assigned to the same bin overlap in all three axes.

The optimization objective is

$$
\min K,
$$

where $K$ is the number of bins used.

---

## 2. Rotation policies

Each item has one of three rotation policies.

### \`none\`

No rotation is allowed:

$$
O_i = \{(w_i,l_i,h_i)\}.
$$

### \`fixed_bottom\`

The vertical axis is fixed and only a 90-degree rotation in the base plane is allowed:

$$
O_i =
\{
(w_i,l_i,h_i),
(l_i,w_i,h_i)
\}.
$$

This does **not** mean the item must lie on the floor of the bin. It may still be stacked at $z_i > 0$.

### \`all\`

All six axis-aligned permutations are allowed:

$$
O_i =
\{
(w_i,l_i,h_i),
(w_i,h_i,l_i),
(l_i,w_i,h_i),
(l_i,h_i,w_i),
(h_i,w_i,l_i),
(h_i,l_i,w_i)
\}.
$$

Duplicate orientations are removed when two or more dimensions are equal.

Before model construction, orientations that cannot fit in a single bin are discarded:

$$
d_i^x \le W,\qquad
d_i^y \le L,\qquad
d_i^z \le H.
$$

If an item has no remaining orientation, the instance is immediately infeasible.

Implementation: \`orientations.py\`.

---

## 3. Overall optimization strategy

The solver does not build one large optimization model with the number of bins as the objective.

Instead, it solves a sequence of **fixed-$K$ feasibility problems**.

Let

$$
LB \le K^\star \le UB
$$

be a lower and upper bound on the optimal number of bins. The solver checks

$$
K = LB, LB+1, \ldots, UB
$$

in ascending order.

For each $K$, CP-SAT answers:

> Can all items be packed using bin indices $0,\ldots,K-1$?

The first feasible $K$ is optimal because feasibility is monotone:

$$
\operatorname{feasible}(K)
\Rightarrow
\operatorname{feasible}(K+1).
$$

This architecture has several advantages:

- the CP-SAT model is a pure feasibility model,
- lower- and upper-bound improvements immediately reduce the search range,
- each $K$ can be benchmarked independently,
- the same fixed-$K$ model can be reused for alternative search strategies.

Implementation: \`solver.py\`.

---

## 4. Upper bound: constructive greedy packing

A valid packing gives a mathematically valid upper bound.

The theoretical fallback is

$$
UB = N,
$$

because preprocessing guarantees that every item can fit in a bin individually.

The implementation computes a tighter upper bound with a deterministic constructive heuristic.

Three item orders are tried:

1. decreasing volume,
2. decreasing maximum dimension,
3. decreasing base area.

For each order, items are inserted with a bottom-back-left style first-fit procedure.

Candidate points are explored in $(z,y,x)$ order, so lower placements are preferred first, followed by smaller $y$, then smaller $x$.

After an item with origin $(x,y,z)$ and size $(d_x,d_y,d_z)$ is placed, three new candidate points are generated:

$$
(x+d_x,y,z),
$$

$$
(x,y+d_y,z),
$$

$$
(x,y,z+d_z).
$$

The best greedy packing is used as the upper bound:

$$
UB = \min_r K_r.
$$

The same packing is also used as a CP-SAT solution hint.

Implementation: \`heuristic.py\`.

---

## 5. Lower bounds

The solver currently combines two valid lower bounds.

### 5.1 Volume lower bound

Let

$$
V_i = w_i l_i h_i
$$

and

$$
V_B = WLH.
$$

Then

$$
LB_{\mathrm{vol}}
=
\left\lceil
\frac{\sum_i V_i}{V_B}
\right\rceil.
$$

This is inexpensive but does not account for shape incompatibility.

### 5.2 Incompatibility-graph clique lower bound

Two items are pairwise incompatible if they cannot coexist in the same bin under **any** allowed orientation pair.

For orientations $p \in O_i$ and $q \in O_j$, the pair can coexist only if at least one axis can separate them:

$$
d_{ip}^x+d_{jq}^x \le W
$$

or

$$
d_{ip}^y+d_{jq}^y \le L
$$

or

$$
d_{ip}^z+d_{jq}^z \le H.
$$

If no orientation pair satisfies any of these conditions, items $i$ and $j$ must use different bins.

This defines an incompatibility graph

$$
G=(V,E).
$$

Every clique of size $q$ requires at least $q$ bins:

$$
K^\star \ge q.
$$

The implementation uses a greedy clique heuristic rather than solving maximum clique exactly.

The final lower bound is

$$
LB
=
\max
\left(
LB_{\mathrm{vol}},
LB_{\mathrm{clique}}
\right).
$$

Implementation: \`preprocess.py\`.

---

## 6. Pairwise preprocessing

Before creating geometric Boolean variables, the solver computes pair compatibility information.

For item $i$, define its componentwise minimum feasible extent:

$$
m_i^x = \min_{p\in O_i} d_{ip}^x,
$$

$$
m_i^y = \min_{p\in O_i} d_{ip}^y,
$$

$$
m_i^z = \min_{p\in O_i} d_{ip}^z.
$$

For a pair $i,j$, X separation is impossible for every orientation if

$$
m_i^x + m_j^x > W.
$$

In that case, the model does not create either X-direction separation literal.

The same preprocessing is applied to Y and Z.

If no axis can separate the pair, the model directly adds

$$
b_i \ne b_j.
$$

This reduces the number of Boolean variables and strengthens propagation before search begins.

The solver also precomputes an orientation-pair compatibility matrix for each item pair.

Implementation: \`preprocess.py\`.

---

## 7. Fixed-$K$ variables

For a fixed number of bins $K$, item $i$ receives the following CP-SAT variables.

### Bin assignment

$$
b_i \in \{0,\ldots,K-1\}.
$$

### Orientation index

$$
o_i \in \{0,\ldots,|O_i|-1\}.
$$

### Effective dimensions

$$
d_i^x,\ d_i^y,\ d_i^z.
$$

The orientation index and dimensions are linked by an allowed-assignment table:

$$
(o_i,d_i^x,d_i^y,d_i^z) \in T_i.
$$

This avoids writing separate rotation-specific model logic for \`none\`, \`fixed_bottom\`, and \`all\`.

### Integer coordinates

$$
x_i,y_i,z_i \in \mathbb{Z}_{\ge 0}.
$$

Implementation: \`cp_model.py\`.

---

## 8. Bin-boundary constraints

Every selected orientation must fit at its chosen coordinate:

$$
x_i+d_i^x \le W,
$$

$$
y_i+d_i^y \le L,
$$

$$
z_i+d_i^z \le H.
$$

The model therefore represents every item as an axis-aligned half-open box

$$
[x_i,x_i+d_i^x)
\times
[y_i,y_i+d_i^y)
\times
[z_i,z_i+d_i^z).
$$

Touching faces, edges, or corners are allowed because non-overlap uses $\le$, not $<$.

---

## 9. Pairwise 3D non-overlap

For every item pair $i<j$, define

$$
S_{ij} \iff b_i=b_j.
$$

If the items use different bins, their local coordinates are independent and may overlap.

If they use the same bin, at least one of six separating relations must hold:

$$
x_i+d_i^x \le x_j,
$$

$$
x_j+d_j^x \le x_i,
$$

$$
y_i+d_i^y \le y_j,
$$

$$
y_j+d_j^y \le y_i,
$$

$$
z_i+d_i^z \le z_j,
$$

$$
z_j+d_j^z \le z_i.
$$

The logical constraint is therefore

$$
\neg S_{ij}
\lor X_{ij}
\lor X_{ji}
\lor Y_{ij}
\lor Y_{ji}
\lor Z_{ij}
\lor Z_{ji}.
$$

Only directions proven possible by preprocessing are created.

Each directional literal uses CP-SAT reification, for example

$$
X_{ij}
\Rightarrow
x_i+d_i^x \le x_j.
$$

The default model uses **half reification**. It does not require the converse implication.

No Big-M constant is used.

Implementation: \`cp_model.py\`.

---

## 10. Why half reification is the default

A full equivalence would also add

$$
\neg X_{ij}
\Rightarrow
x_i+d_i^x > x_j.
$$

That makes the Boolean literal exactly represent the truth value of the geometric inequality.

However, for this model the literal only needs to act as a witness that one valid separation exists. Requiring every literal to match the underlying inequality creates additional constraints without changing feasibility.

The repository keeps full reification as an optional benchmark switch, but the default is half reification because benchmark results found it consistently slower on the tested instances.

---

## 11. Orientation-pair compatibility constraints

Axis-level preprocessing can only remove a direction if it is impossible for **all** orientation combinations.

The solver adds a stronger table constraint for orientation pairs.

For each pair $i,j$, precompute $C_{ijpq}$ for every orientation pair $p \in O_i$, $q \in O_j$.

The pair is compatible in the same bin if

$$
C_{ijpq}=1
$$

whenever at least one axis can separate the two selected orientations.

The CP-SAT table over

$$
(S_{ij},o_i,o_j)
$$

allows every orientation pair when

$$
S_{ij}=0,
$$

but only compatible orientation pairs when

$$
S_{ij}=1.
$$

This propagates rotation and bin-assignment decisions before coordinates are fully fixed.

Implementation: \`cp_model.py\`.

---

## 12. Opposite-direction exclusion

For one axis, the two directions are mutually exclusive for positive-sized items.

For example, $X_{ij}$ and $X_{ji}$ cannot both be true.

The model therefore optionally posts

$$
\operatorname{AtMostOne}(X_{ij},X_{ji}),
$$

and similarly for Y and Z.

This is redundant with the geometric constraints but provides an explicit Boolean-level relation for the SAT engine.

It is enabled by default.

---

## 13. Bin-index symmetry breaking

All bins are identical, so permutations of bin labels create equivalent solutions.

Without symmetry breaking, a packing using bins $(0,1,2)$ has many equivalent representations such as $(2,0,1)$.

Items are first ordered deterministically by decreasing volume, then item ID.

The model fixes

$$
b_0=0
$$

and uses restricted-growth numbering:

$$
b_i
\le
1+\max_{j<i} b_j.
$$

Therefore a new bin label may only be introduced after all smaller labels are already reachable.

Used bin indices become consecutive from zero, removing a large class of equivalent search states.

Implementation: \`cp_model.py\`.

---

## 14. CP-SAT hints

The greedy solution is converted into hints for:

- bin index,
- orientation index,
- x coordinate,
- y coordinate,
- z coordinate.

Because symmetry breaking may relabel bins, the greedy bin indices are first normalized in order of first appearance.

Hints do not affect correctness. They only provide CP-SAT with a promising initial assignment.

Implementation: \`solver.py\`.

---

## 15. Search and optimality

The complete search pipeline is:

1. run the constructive greedy heuristic,
2. generate and filter orientations,
3. compute pair compatibility,
4. compute $LB$,
5. take greedy bin count as $UB$,
6. for $K=LB,\ldots,UB$:
   - build the fixed-$K$ model,
   - add hints,
   - solve the feasibility problem,
   - stop at the first feasible $K$.

If every smaller $K$ has been proven infeasible and $K$ is feasible, then

$$
K = K^\star.
$$

The returned solution has \`optimal=True\`.

If the global time budget expires, or CP-SAT returns \`UNKNOWN\` for some $K$, smaller bin counts have not all been ruled out. In that case the solver returns the valid greedy packing with \`optimal=False\`.

This distinction is important:

- \`optimal=True\`: minimum bin count is proven,
- \`optimal=False\`: returned packing is valid, but may use more bins than the unknown optimum.

---

## 16. Time limits

\`SolverOptions.time_limit\` applies to the **entire** search over

$$
[LB,UB],
$$

not independently to every fixed-$K$ model.

This prevents total runtime from growing proportionally with the width of the bound interval.

An optional \`per_k_time_limit\` can additionally cap each individual fixed-$K$ solve.

---

## 17. Independent validation

Every returned solution is independently checked by \`validate\` unless verification is disabled.

The validator checks:

- every item appears exactly once,
- each selected shape is allowed by that item's rotation policy,
- each placement lies inside the bin,
- items in the same bin do not overlap,
- bin indices and reported bin count are consistent.

Keeping validation outside the CP-SAT model is useful for detecting modeling or extraction bugs.

Implementation: \`validate.py\`.

---

## 18. Complexity

For $N$ items, the geometric model considers

$$
\binom{N}{2}
$$

item pairs.

In the worst case, each pair creates six separation literals, so the Boolean part is $O(N^2)$.

Rotation adds at most six orientations per item, and the orientation-pair compatibility table for a pair has at most

$$
6\times6=36
$$

orientation combinations.

The main practical performance techniques are therefore:

- reduce the range $[LB,UB]$,
- remove impossible orientations,
- remove impossible separation axes,
- force incompatible pairs into different bins,
- break bin-label symmetry,
- provide a good initial packing as a hint.

---

## 19. Strengthening constraints not currently implemented

The current implementation intentionally leaves some global-constraint strengthenings for future work.

### Per-axis Cumulative relaxations

For one bin, an X-axis cumulative relaxation would use interval

$$
[x_i,x_i+d_i^x)
$$

with cross-sectional demand

$$
d_i^y d_i^z
$$

and capacity

$$
LH.
$$

Analogous relaxations exist for Y and Z.

With rotations, interval lengths and cross-sectional areas are variable, so an efficient implementation should use orientation-indexed precomputed values rather than unnecessary multiplication constraints.

### Conditional NoOverlap2D

If preprocessing proves a set of items cannot separate along Z, then their XY projections must not overlap.

Such subsets can be strengthened with \`NoOverlap2D\`.

### Conditional NoOverlap

If a set of items cannot separate along two axes, they must be ordered along the remaining axis and can be strengthened with one-dimensional \`NoOverlap\`.

These constraints do not change feasibility; they are intended only to improve propagation.

---

## 20. Source map

| Module | Responsibility |
| --- | --- |
| \`models.py\` | Domain objects and geometry primitives |
| \`orientations.py\` | Rotation generation, deduplication, fit filtering |
| \`preprocess.py\` | Lower bounds, compatibility data, incompatibility graph |
| \`heuristic.py\` | Constructive upper bound and hint generation source |
| \`cp_model.py\` | Fixed-$K$ CP-SAT feasibility model |
| \`solver.py\` | Minimum-bin search over $K$ |
| \`validate.py\` | Independent solution validation |

---

## 21. Summary

The solver combines a constructive heuristic with exact CP-SAT feasibility search:

$$
\boxed{
\text{preprocess}
\rightarrow
(LB,UB)
\rightarrow
\text{fixed-}K\text{ CP-SAT}
\rightarrow
\text{first feasible }K
}
$$

The core geometric constraint is:

$$
\boxed{
b_i \ne b_j
\;\lor\;
X_{ij}
\;\lor\;
X_{ji}
\;\lor\;
Y_{ij}
\;\lor\;
Y_{ji}
\;\lor\;
Z_{ij}
\;\lor\;
Z_{ji}
}
$$

with orientation-dependent integer dimensions and no Big-M formulation.

The result is a compact exact model that supports per-item rotation policies while retaining a clear separation between:

- heuristic upper bounding,
- preprocessing,
- fixed-$K$ feasibility,
- optimality proof,
- independent validation.
