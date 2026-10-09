# 0002 · No cluster placement group for this workload; keep talking nodes in one AZ

**Status:** accepted · 2026-10-09

## Context
Cluster placement groups are the textbook answer for HPC networking. Themba's model is embarrassingly parallel: simulated years are independent, nodes never exchange data, and each worker only reads its code and writes a small result.

## Decision
No cluster placement group for the catastrophe model. Spread capacity across AZs (for Spot availability) and accept cross-AZ latency, because there is no node-to-node traffic. For any future workload where nodes do talk, keep them in one AZ first, and test a cluster group with larger network-optimised instances (and EFA for MPI) before adopting one.

## Alternatives considered
- **Cluster group anyway:** no measured benefit at this size, a single-AZ, close-together failure domain, and a higher chance of `InsufficientInstanceCapacity` when asking for co-located capacity.
- **Spread group:** guarantees distinct racks; useful for a few critical nodes, irrelevant for a batch fleet.

## Consequences
- Measured on c7i.large: same AZ 0.22–0.235 ms and 9.53 Gbit/s per flow with or without the cluster group; other AZ 0.494 ms and 4.965 Gbit/s; 12.41 Gbit/s with 8 streams everywhere.
- The finding is specific to 2-vCPU instances; it is not evidence against cluster groups for network-heavy instance types.
