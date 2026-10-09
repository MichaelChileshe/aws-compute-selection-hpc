# 0004 · Spot with checkpoints to S3, notice handling, and diversified pools

**Status:** accepted · 2026-10-09

## Context
Spot was 65–68% cheaper than on-demand for all three benchmarked types that day, but AWS can reclaim an instance with a 2-minute notice. The run must not lose or double-count work.

## Decision
- Work in small chunks (20,000 years, about 17–19 s) and save a checkpoint to S3 after each.
- Watch IMDS for the rebalance recommendation and the interruption notice; on the notice, finish the current chunk, checkpoint and exit.
- Run under an Auto Scaling group with four instance types in three AZs, `price-capacity-optimized`, so a replacement can come from 12 Spot pools (4 types × 3 AZs).
- Keep capacity rebalancing off until the worker takes a lease on the checkpoint (two workers must never write it at once).
- Prove it with AWS FIS rather than waiting for a real reclaim.

## Consequences
- Measured: stopped 14.8 s after the notice at year 620,000; the first replacement failed for lack of Spot capacity, the second (another type, another AZ) launched 9 s after that failure and resumed at year 620,000; 0 years lost or repeated.
- Recovery time is dominated by the notice period and replacement launch (159.7 s from stop to resume).
- For the nightly run, AWS Batch provides the same properties (retries on `Host EC2*`, diversified pools) without a custom worker ([0005](0005-aws-batch-array-jobs-on-managed-spot.md)); the worker pattern remains the answer for long single jobs.
