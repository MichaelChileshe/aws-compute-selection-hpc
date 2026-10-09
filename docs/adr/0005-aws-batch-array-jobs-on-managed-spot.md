# 0005 · AWS Batch array jobs on managed Spot compute environments that scale to zero

**Status:** accepted · 2026-10-09

## Context
The current model runs on one always-on server and misses the 07:00 deadline on busy nights. The work splits naturally into independent ranges of years.

## Decision
- One array job per run: N children, each a range of years (`AWS_BATCH_JOB_ARRAY_INDEX`), each printing its totals to CloudWatch Logs; a collector merges them.
- Managed compute environments, `SPOT` with `SPOT_PRICE_CAPACITY_OPTIMIZED`, **min 0 vCPUs**, several instance families each.
- Retry a child only when its host went away (`Host EC2*`); fail everything else.
- Ship the model in the job definition (gzip + base64) on the public Amazon Linux image for this lab; in production, build an image in ECR.

## Alternatives considered
- **A bigger always-on server:** faster, but billed 24 hours a day for a few hours of work, and still one point of failure.
- **The Spot worker from ADR 0004 at fleet scale:** possible, but it would rebuild what Batch provides (queueing, placement, retries, scale to zero).
- **AWS ParallelCluster:** the right tool for tightly coupled MPI jobs with a scheduler; more than an embarrassingly parallel model needs.

## Consequences
- Measured: 2,400,000 years in 236.2 s (Graviton) and 277.1 s (x86), 40/40, 0 retries, ~US$0.03 each, compute environments back to 0 vCPUs.
- The submission limit (container overrides ≤ 8,192 characters) bit once; code in the job definition must stay small or move to an image.
- Batch can launch more vCPUs than `maxvCpus` with these strategies (26 vs 16 here); quotas and budgets must allow for it.
