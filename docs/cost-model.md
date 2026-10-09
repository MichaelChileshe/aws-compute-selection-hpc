# Cost model

## The build

Built on 9 October 2026, base applied at about 12:25 and destroyed at 13:49 South African time; each lab existed only for its own measurement. The figures are my estimate from the prices the build measured (on-demand from the Price List API, Spot from the price history) and AWS's list prices; Cost Explorer hadn't posted the day when I packaged the repo, and the actual figure replaces this once it has.

| Item | Usage | Estimate (US$) |
|---|---|---|
| Placement lab | 5 × c7i.large on-demand (US$0.08925/h) for about 12 minutes | ~0.09 |
| Processor lab | c7g + c7i + c7a .large on-demand (US$0.0725 + 0.08925 + 0.10264/h) for about 8 minutes | ~0.04 |
| Spot worker | c6g.large then m6g.large Spot (about US$0.03–0.04/h) for about 15 minutes | ~0.01 |
| AWS FIS | the completed experiment (US$0.10 per action-minute) and possibly the failed second one | 0.10–0.20 |
| AWS Batch | instance time × Spot price at collection: 0.0315 (Graviton) + 0.0355 (x86) | ~0.07 |
| Public IPv4, EBS, S3, CloudWatch Logs, SSM | minutes of each; a few hundred requests | ~0.03 |
| **Total** | | **≈ 0.35–0.45** |

**What keeps costing after the destroy:** nothing from this project. The shared state bucket holds a 304-byte empty state file for it.

## The business case: the night run at these rates

From the measured US$ per million simulated years ([`processors.md`](processors.md)):

| Option | US$ per million years | 2,400,000 years (one night) |
|---|---|---|
| c7i.large on-demand | 0.0198 | ~US$0.048 |
| c7g.large on-demand | 0.0121 | ~US$0.029 |
| c7g.large Spot | 0.0042 | ~US$0.010 |
| AWS Batch on Graviton Spot (measured, including instance start-up and idle time) | | ~US$0.032 |

The compute itself is cents a night whichever way it runs. The real saving is the server that's on 24 hours to work for a few: an always-on instance is billed for every hour, whereas Batch with min 0 vCPUs bills only the minutes of the run. And the time saved matters more than the money: the same years finish in about 4 minutes on Batch, against about 35–38 minutes on one 2-vCPU Spot worker.

**Cost lessons from the build:**

- **Price the unit of work.** Intel was fastest per core and about 64% dearer per simulated year than Graviton; AMD was fastest per instance and 7% dearer.
- **Spot changes the ranking:** Graviton and AMD tied on Spot (US$0.0042), so the queue that gets capacity first wins on wall clock.
- **Short jobs pay a large share for start-up:** on the Graviton run Batch paid for about 6,300 vCPU-seconds of instances (26 vCPUs for about 240 s) and used about 3,400 (1,690 container-seconds × 2 vCPUs), roughly 54%; the rest was boot and the tail as the last children finished. Larger runs amortise it.
- **FIS was one of the biggest lines.** Testing resilience on purpose cost about as much as the compute it tested, and was worth it.
