# Spot: a job that survives a real interruption

## How the worker is built

[`app/worker.py`](../app/worker.py) runs as a systemd service on a Spot instance and keeps all its state in S3 under `spot-job/`:

- **`job.json`** (written by Terraform): seed 26, 2,400,000 years, a checkpoint every **20,000** years.
- **`checkpoint.json`**: the next year to run and the merged totals so far, rewritten after every chunk.
- **`events/`**: one small file per event (started, rebalance recommendation, interruption notice, stopped, resumed, finished).

A background thread asks the instance metadata service (IMDSv2) every 2 seconds for `events/recommendations/rebalance` and `spot/instance-action`. When the notice arrives, the worker finishes the chunk it's in, saves the checkpoint and exits. At boot it looks for a checkpoint and carries on from it.

The instance belongs to an **Auto Scaling group of exactly one** ([`infra/spot.tf`](../infra/spot.tf)): 100% Spot, `price-capacity-optimized`, four Graviton types (c7g, m7g, c6g, m6g .large) in three AZs, so a replacement can come from any of 12 Spot pools. Capacity rebalancing is off on purpose: it would start a second worker while the first is still writing the same checkpoint.

**AWS FIS** delivers the real thing on demand: the experiment template targets one running instance tagged `Name = themba-spot-worker` with `aws:ec2:send-spot-instance-interruptions`, `durationBeforeInterruption = PT2M`. Its role can send interruptions only to instances with that tag.

## The run, in UTC

| Time | What |
|---|---|
| 10:51:19 | Group launches i-0807d30feba58a351, a **c6g.large** in us-east-1a (price-capacity-optimized picked c6g, not the first-listed c7g) |
| 10:51:34 | Worker starts: 2,400,000 years in chunks of 20,000 (about 17–19 s each) |
| 11:00:30 | FIS experiment starts (it completed at 11:00:52) |
| 11:00:55 | Worker sees the **rebalance recommendation** (noticeTime 11:00:52) |
| 11:00:56 | Worker sees the **interruption notice**: terminate at 11:02:52, **1.0 s** after the rebalance recommendation |
| 11:01:10 | Worker finishes its chunk, saves the checkpoint and stops: **14.8 s after the notice**, next year **620,000**, 31 chunks done |
| 11:03:21 | Group finds the instance terminated and takes it out of service |
| 11:03:24 | First replacement **fails**: `InsufficientInstanceCapacity - There is no Spot capacity available that matches your request` |
| 11:03:33 | Second attempt succeeds: i-0e16b338327dd8d18, an **m6g.large** in **us-east-1c** |
| 11:03:50 | New worker **resumes from year 620,000** (checkpoint saved by the old instance at 11:01:10) |

**Years lost or repeated: 0.** Stop to resume: 159.7 s, most of it the old instance waiting out its notice (terminate at 11:02:52) and the group noticing it was gone (11:03:21); from the group noticing to the new worker resuming took 29 s. Screenshots [`14`](screenshots/14-spot-progress-before-interruption.png)–[`19`](screenshots/19-spot-destroyed-6.png); data in [`results/spot-interruption.csv`](results/spot-interruption.csv) and [`results/raw/spot.json`](results/raw/spot.json).

## What it shows

- **The 2-minute notice is plenty if the unit of work is small.** With a 17–19 s chunk, the worker used 15 s of its 2 minutes. A chunk of 10 minutes would usually have lost the chunk in progress.
- **The rebalance recommendation came only 1 s earlier here.** In a FIS experiment both arrive together; in real reclaims the recommendation can come well before the notice, and a worker can use it to checkpoint early.
- **Diversification isn't optional.** The first replacement found no Spot capacity for the request in the AZ it tried. With one type in one AZ, the job would have waited; with 12 pools the next attempt worked 9 s later, on a different type in a different AZ.
- **A second, failed experiment:** I started FIS again from another terminal at 11:02:53, after the first had already interrupted the only worker; that experiment failed 12 s later (most likely no interruptible target left; I didn't capture its reason). The completed experiment is the one in the timeline.

## What wasn't measured on AWS

I switched the Spot lab off a few minutes after the resume, with the new worker still running, so the interrupted job's final digest was never written to S3 (and the bucket went with the base at teardown). To close the gap I replayed the same split on my laptop: years 0–619,999 and 620,000–2,399,999, merged the way the worker merges its checkpoint. Digest **`0cb96b0f9d9c5303`**, the same as both Batch runs over the same 2,400,000 years ([`results/raw/local-spot-replay.txt`](results/raw/local-spot-replay.txt)). The resume point is measured on AWS; the final answer for that split is reproduced, not observed.
