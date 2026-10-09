# 0003 · Graviton first for the night run, x86 as a fallback queue

**Status:** accepted · 2026-10-09

## Context
The same 60,000 years on 2-vCPU instances: AMD c7a fastest per instance (2,187 years/s), Graviton c7g 1,659, Intel c7i 1,249 (its 2 vCPUs are one core). Per million simulated years on-demand: c7g US$0.0121, c7a 0.0130, c7i 0.0198; on Spot c7g and c7a both 0.0042, c7i 0.0065. All produced the same digest.

## Decision
- The night run's primary queue uses Graviton Spot (c7g, m7g, c6g, m6g).
- An x86 queue (c7i, m7i, c7a, m7a, c6i) exists beside it; in production it would be the second compute environment in the same queue's order, so Batch falls back when Graviton Spot is short.
- The container image is multi-architecture, so one job definition serves both.

## Alternatives considered
- **AMD only:** fastest per instance and tied on Spot price, but one processor family is fewer Spot pools.
- **Intel:** fastest per core, but hyperthreaded vCPUs halve the useful cores for this compute-bound code; 64% dearer per year on-demand.

## Consequences
- Measured in Batch: Graviton capacity arrived in 66 s vs 137 s for x86, and the run finished first (236 s vs 277 s), although x86 containers were faster.
- The ranking is for this pure-Python model; a compiled or vectorised model must be benchmarked again with the same script.
