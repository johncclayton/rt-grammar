# Design rationale template

Use this skeleton for feature design packages in rt-grammar. Each section is required; keep call sites concrete and the shape section code-heavy.

## 1. Problem

What user pain exists today? What is in scope for v1 and explicitly out of scope?

## 2. Usage (caller's view)

**Start here for readers.** A short README-style overview, then 2–3 realistic call sites (CLI, library, web) showing the intended public API before any internals.

## 3. Shape

Data structures, module map, and function/class signatures. Python sketches live under the feature package directory. CriteriaGraph (or equivalent core type) should be obvious as the load-bearing abstraction.

## 4. Tradeoffs accepted

Decisions we are deliberately making, including what we are not building yet.

## 5. Alternatives considered

At least one structurally different approach and why it was not chosen.

## 6. Open questions and risks

Unknowns, dependencies on RealTest behavior, and failure modes.

## 7. Next implementation step

One concrete, mergeable first slice — not a multi-month roadmap.
