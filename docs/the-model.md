# The model: catsim, and why every run can be checked with one digest

## What it simulates

`app/catsim.py` is a small property catastrophe model, written for this project in standard-library Python (no packages, so it runs unchanged on the nodes and in the stock Amazon Linux container):

- **The book:** 2,000 insured zones around nine provincial hubs, each with a sum insured; about R104 billion in total. Generated once from a fixed seed, so every run uses the same book.
- **The perils:** hail (2.2 events a year on average, 25 km footprint), flood (0.8, 60 km) and windstorm (1.1, 120 km). Event counts follow a Poisson distribution; each event's damage ratio at its centre comes from a severity curve and falls off with distance.
- **Reinsurance:** a catastrophe excess-of-loss cover per event, R1 billion in excess of R250 million, so the model reports gross and net losses.
- **Outputs per run:** gross and net average annual loss, the largest year, how many years exceed R250m / R500m / R1bn / R2bn, and the **1-in-200-year gross loss** (the 99.5th percentile, read from a histogram of annual losses in R10 million bins).

For 2,400,000 years: gross AAL **R219,218,281**, net AAL **R174,728,049**, 1-in-200 **R1.92 billion**, largest year **R7.62 billion** ([`results/raw/batch-graviton.json`](results/raw/batch-graviton.json)).

## Why the answer can't depend on the machine

Two design rules:

1. **Every simulated year has its own seed:** `Random(seed × 1,000,003 + year)`. Year 620,000 is the same year whether it runs first or last, in one process or in a Batch child on another instance. Results are kept as integer totals, counts and a histogram, which merge exactly in any order.
2. **Only arithmetic IEEE 754 defines exactly.** At run time the model uses `+ − × ÷` and comparisons, no `exp`, `log` or `pow`, whose last bit can differ between CPU architectures and maths libraries. The few constants that need `exp` (Poisson probabilities) are written into the code as literals. Python's random number generator is defined bit for bit too.

So the full aggregate is identical for the same years, and `summary()` prints a **digest**: the first 16 hex characters of the SHA-256 of the aggregate. Two runs with the same digest produced the same answer, to the rand.

## The checks

| Years | Where | How | Digest |
|---|---|---|---|
| 4,000 | my laptop (Python 3.14) | one run | `78a9364c876e456c` |
| 4,000 | my laptop | two halves of 2,000, merged | `78a9364c876e456c` |
| 60,000 | c7g.large (Graviton, arm64), c7i.large (Intel), c7a.large (AMD), Python 3.9 | 1 process and 2 processes each | `07394c4b0c9564a3` (all six) |
| 60,000 | my laptop | 8 processes | `07394c4b0c9564a3` |
| 2,400,000 | AWS Batch, Graviton Spot | 40 children × 60,000, merged | `0cb96b0f9d9c5303` |
| 2,400,000 | AWS Batch, x86 Spot | 40 children × 60,000, merged | `0cb96b0f9d9c5303` |
| 2,400,000 | my laptop | years 0–619,999 + 620,000–2,399,999, merged: the Spot job's interruption point | `0cb96b0f9d9c5303` |

Screenshots [`05`](screenshots/05-local-split-check-digest.png), [`12`](screenshots/12-bench-results.png), [`26`](screenshots/26-batch-graviton-answer-instances.png), [`28`](screenshots/28-batch-x86-answer-instances.png); data in [`results/digests.csv`](results/digests.csv).

**Why it matters for the business.** Once the answer can't depend on the machine, choosing compute is purely a question of time and money: the cheapest Spot pool, Graviton or x86, 1 instance or 40, interrupted or not. Without the check, "is the cheaper option giving us the same capital number?" would need an actuarial review every time the infrastructure changed.
