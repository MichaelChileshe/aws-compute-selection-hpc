# The night run on AWS Batch: Graviton vs x86, all Spot

## The setup

`batch_lab = true` ([`infra/batch.tf`](../infra/batch.tf)):

- **Two managed compute environments**, both `SPOT` with `SPOT_PRICE_CAPACITY_OPTIMIZED`, **min 0** and max 16 vCPUs, over the three public subnets, ECS on Amazon Linux 2023:
  - `themba-cat-graviton`: c7g, m7g, c6g, m6g
  - `themba-cat-x86`: c7i, m7i, c7a, m7a, c6i
- **A queue for each**, so the two can be run and measured separately.
- **One job definition**, `themba-catsim`: the public `amazonlinux:2023` image (multi-architecture, Python 3 included), 2 vCPUs and 3,000 MiB per child, logs to `/aws/batch/themba-cat`, a 30-minute timeout, and a retry strategy that retries a child whose host went away (`Host EC2*`, which covers a Spot reclaim) and fails anything else. The model travels in the job definition itself (gzip + base64 in an environment variable), so there's no image to build or registry to run.
- **The run:** one array job of **40 children × 60,000 years** = the same 2,400,000 years as the Spot job. Child *i* runs years *i* × 60,000 onwards (`AWS_BATCH_JOB_ARRAY_INDEX`) and prints its totals; [`scripts/batch_collect.py`](../scripts/batch_collect.py) merges them from CloudWatch Logs and measures the run.

Both compute environments came up `ENABLED`, `VALID`, min 0, max 16 ([`21`](screenshots/21-batch-compute-environments.png)).

## Results

| | Graviton queue | x86 queue |
|---|---|---|
| Children succeeded / retried | **40 / 0** | **40 / 0** |
| Submit to first child running | 65.8 s | 137.1 s |
| **Wall clock, submit to last child done** | **236.2 s** | **277.1 s** |
| Most children running at once | 13 | 13 |
| Child run time | 36.0–53.3 s | 26.5–43.7 s |
| Years per second per child (average) | 1,466.5 | 1,749.2 |
| Container time in total | 1,690.3 s | 1,436.2 s |
| Instances Batch launched (all Spot) | 1 × c7g.4xlarge, 5 × m6g.large | 3 × c7a.large, 1 × m7i.4xlarge, 1 × m7i.xlarge |
| Instance time in total | 1,489 s | 1,267 s |
| Estimated cost (instance lifetime × Spot price at collection) | **~US$0.0315** | **~US$0.0355** |
| Digest | **`0cb96b0f9d9c5303`** | **`0cb96b0f9d9c5303`** |

Screenshots [`24`](screenshots/24-batch-graviton-run.png)–[`28`](screenshots/28-batch-x86-answer-instances.png); data in [`results/batch-runs.csv`](results/batch-runs.csv), per child and per instance in [`results/raw/`](results/raw/).

## What it shows

- **Under five minutes from submit to the 1-in-200 number,** for a run that took the single Spot worker about 17–19 s per 20,000 years (about 35–38 minutes for the whole 2,400,000 on one c6g.large). Themba's 07:00 deadline stops being a problem; the run could be repeated several times a night.
- **Batch chose its own instances,** including much larger ones than the jobs asked for (a c7g.4xlarge and an m7i.4xlarge, each with room for 8 children), and the instances it launched added up to 26 vCPUs on each run, more than the 16 I set as the maximum. AWS documents that these Spot allocation strategies may go over `maxvCpus` to meet a request.
- **Per container, x86 was faster** (the c7a and m7i are quicker per core than Graviton for this code); **per run, Graviton finished first,** because its Spot capacity arrived 71 s sooner. On a short job, the wait for capacity is as big as the compute.
- **Cost was the same order on both:** about three US cents for 2.4 million simulated years, with nothing running before or after. The compute environments returned to 0 vCPUs on their own.
- **Same digest on both architectures, and the same as the interrupted Spot job's split replayed.** 40 pieces on 6 or 5 instances of different types gave the identical answer.

## The first attempt failed

The first Graviton submission failed all 40 children within about 18 seconds, before any instance started: `Container Overrides length must be at most 8192` ([`22`](screenshots/22-batch-first-run-failed.png), [`23`](screenshots/23-batch-failure-reason.png)). The cause and fix are in [`debugging-journey.md`](debugging-journey.md#1-every-batch-child-failed-container-overrides-length-must-be-at-most-8192).
