# 0001 · A deterministic model, split by year, checked by one digest on every run

**Status:** accepted · 2026-10-09

## Context
The point of the project is to move the catastrophe model freely between processors, Spot pools, process counts and Batch splits. Each move raises the same question from the actuaries: is the capital number still the same? Checking that by hand every time isn't practical.

## Decision
- Every simulated year gets its own seed (`seed × 1,000,003 + year`), so the result depends only on which years are run.
- Results are integer totals, counts and a histogram, which merge exactly in any order.
- Only operations IEEE 754 defines exactly at run time (`+ − × ÷`, comparisons); constants that need `exp` are literals.
- Every run prints a digest: the first 16 hex characters of the SHA-256 of the full aggregate.

## Consequences
- Measured: the same digest on Graviton, Intel and AMD (1 and 2 processes), on my laptop under a different Python version, from two Batch runs of 40 children on different instance types, and from the Spot job's interruption split replayed.
- The model can't use library functions whose results may differ by a bit between platforms (`math.exp`, `math.log`) inside the simulation, which constrains how it's written. Distributions are built from tables and arithmetic instead.
- The digest proves sameness, not correctness: the model's actuarial validity is a separate review.
