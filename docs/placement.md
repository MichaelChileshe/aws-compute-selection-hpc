# Placement groups: cluster vs spread vs another AZ

## The setup

`placement_lab = true` built two placement groups and five identical **c7i.large** nodes ([`infra/placement.tf`](../infra/placement.tf)):

| Node | Group | AZ | Private IP |
|---|---|---|---|
| cluster-a, cluster-b | `themba-hpc-cluster` (strategy `cluster`) | us-east-1a | 10.140.1.86, 10.140.1.195 |
| spread-a, spread-b | `themba-hpc-spread` (strategy `spread`, rack level) | us-east-1a | 10.140.1.248, 10.140.1.224 |
| spread-c | `themba-hpc-spread` | us-east-1b | 10.140.2.254 |

Every node runs an iperf3 server. [`scripts/placement_test.py`](../scripts/placement_test.py) runs [`app/nettest.py`](../app/nettest.py) on the first node of each pair through SSM: 1,000 pings 2 ms apart, then iperf3 for 10 s with one TCP stream (the per-flow limit) and 10 s with eight (the instance limit). Same instance type everywhere, so placement is the only variable.

## Results

| Pair | Placement | Round trip avg (min / max / mdev) ms | 1 stream Gbit/s | 8 streams Gbit/s |
|---|---|---|---|---|
| cluster-a → cluster-b | cluster group, same AZ | **0.235** (0.07 / 1.715 / 0.063) | **9.53** | 12.409 |
| spread-a → spread-b | spread group, same AZ | **0.22** (0.08 / 2.429 / 0.086) | **9.529** | 12.41 |
| spread-a → spread-c | spread group, other AZ | **0.494** (0.36 / 2.264 / 0.092) | **4.965** | 12.409 |

0% packet loss everywhere. Screenshots [`06`](screenshots/06-placement-apply-7.png)–[`09`](screenshots/09-placement-destroyed-7.png); data in [`results/placement.csv`](results/placement.csv).

## What it means

- **Inside one AZ, the cluster group made no measurable difference** for this instance size: the spread pair's average round trip was even 0.015 ms lower, within the noise of a single run, and both pairs pushed 9.53 Gbit/s on one stream.
- **Crossing AZs is what cost:** the round trip doubled (2.1× the cluster pair) and one stream stopped at 4.965 Gbit/s, in line with the 5 Gbit/s single-flow limit AWS documents for traffic outside a cluster placement group. In my test that limit only showed up between AZs.
- **Eight streams hit the same 12.41 Gbit/s on every pair:** the c7i.large's own burst bandwidth ("up to 12.5 Gbit/s"). The instance, not the placement, was the ceiling.
- **The trade-off of a cluster group is resilience:** both nodes sit close together, so one hardware problem can take out both. A spread group guarantees distinct racks (at most 7 running instances per AZ per group).

**For Themba:** catsim's years are independent; the nodes don't talk to each other at all. So the decision is no cluster group ([ADR 0002](adr/0002-no-cluster-placement-group-for-this-workload.md)). If a future model were tightly coupled (MPI exchanging data every step), the right test would be larger network-optimised instances with EFA in a cluster group, which this lab doesn't cover.
