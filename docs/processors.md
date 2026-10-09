# Graviton vs Intel vs AMD: speed and price per simulated year

## The setup

`bench_lab = true`: one on-demand node per type, all 2 vCPUs, same Amazon Linux 2023, same Python (3.9.25), same code (catsim.py's SHA-256 matched on all three, [`11`](screenshots/11-bench-node-cpus.png)):

| Node | Type | CPU (from /proc/cpuinfo) | Architecture |
|---|---|---|---|
| graviton | c7g.large | Graviton3 (`CPU part : 0xd40`) | aarch64 |
| intel | c7i.large | Intel Xeon Platinum 8488C | x86_64 |
| amd | c7a.large | AMD EPYC 9R14 | x86_64 |

[`scripts/bench.py`](../scripts/bench.py) ran `catsim bench --years 60000` on all three at once, with 1 process and with 2, then read the on-demand price (Price List API) and the lowest current Spot price across us-east-1 AZs ([`scripts/prices.py`](../scripts/prices.py)), and divided: US$ per million simulated years at full speed.

## Results

| Type | Years/s, 1 process | Years/s, 2 processes | 2nd vCPU adds | On-demand US$/h | Spot US$/h (lowest AZ) | US$ per million years, on-demand | US$ per million years, Spot |
|---|---|---|---|---|---|---|---|
| c7a.large (AMD) | 1,036.0 | **2,186.8** | 2.11× | 0.10264 | 0.0332 | 0.0130 | **0.0042** |
| c7g.large (Graviton) | 827.1 | 1,658.9 | 2.01× | **0.0725** | **0.0253** | **0.0121** | **0.0042** |
| c7i.large (Intel) | **1,215.1** | 1,249.3 | **1.03×** | 0.08925 | 0.0292 | 0.0198 | 0.0065 |

Every one of the six runs: digest **`07394c4b0c9564a3`**. Screenshots [`10`](screenshots/10-bench-apply-3.png)–[`13`](screenshots/13-bench-destroyed-3.png); data in [`results/bench.csv`](results/bench.csv).

## What it means

- **Per core, Intel is fastest** (1,215 years/s), AMD next, Graviton slowest (827): for pure-Python, single-threaded work, clock speed and core design matter.
- **Per instance, AMD is fastest** and **Intel falls to last**: on c7i.large the 2 vCPUs are one physical core with two hyperthreads, so the second process added 3%. On c7g and c7a each vCPU is a whole core, and the second process doubled the speed.
- **Per dollar on-demand, Graviton wins** (US$0.0121 per million years), AMD 7% behind, Intel about 64% behind. **On Spot, Graviton and AMD tie** at US$0.0042 (to four decimals; unrounded AMD is 0.4% cheaper): Spot discounts were 65–68% on all three types that day.
- So "fastest" (AMD), "cheapest per hour" (Graviton) and "cheapest per unit of work" (Graviton on-demand, Graviton or AMD on Spot) are three different answers. The night run is priced by the last one ([ADR 0003](adr/0003-graviton-first-x86-as-fallback.md)).

**Caveats:** one run per type; Spot prices move hourly; and this is one pure-Python workload. Compiled or vectorised code (NumPy, C) could rank the processors differently. The method carries over: same code, digest check, price per unit of work.
