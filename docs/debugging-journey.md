# Debugging journey

What didn't go as expected, what it turned out to be, and what changed.

## 1. Every Batch child failed: `Container Overrides length must be at most 8192`

**Symptom.** The first Graviton array job went from submitted to `FAILED=40` in about 18 seconds. No child had an attempt; no instance had started ([`22`](screenshots/22-batch-first-run-failed.png)). Batch's reason for child 0: `Container Overrides length must be at most 8192`; for the parent: `Array Child Job failed` ([`23`](screenshots/23-batch-failure-reason.png), [`results/raw/batch-graviton-failure.json`](results/raw/batch-graviton-failure.json)). Both compute environments were `VALID` and healthy.

**Cause.** I'd shipped the model inside the job definition as a base64 environment variable: 10,732 characters. Batch hands a job's command and environment to ECS as container overrides, and ECS caps those at 8,192 characters. The job definition registered fine; every job built from it was rejected.

**Fix.** Gzip before base64 (Terraform's `base64gzip()`), and unzip in the container (`gzip.decompress`): 4,360 characters. `Plan: 0 to add, 1 to change, 0 to destroy`, applied as `themba-catsim:2`; the resubmitted job went 40/40 ([`24`](screenshots/24-batch-graviton-run.png)).

**Lesson.** A definition that registers isn't a definition that runs; limits can apply at submit time. For anything bigger, the code belongs in an image (ECR) or is fetched from S3 at start.

## 2. My collect script assumed at least one child had started

**Symptom.** After the failed run, `batch_collect.py` crashed with `ValueError: min() iterable argument is empty` ([`22`](screenshots/22-batch-first-run-failed.png)).

**Cause.** It took the first start time from the children's attempts; a job rejected at submit has no attempts.

**Fix.** If no child ever started, it stops with the parent's status and the children's reasons instead.

## 3. A finished array job had no `stoppedAt`

**Symptom.** After the successful rerun, the same script stopped with `KeyError: 'stoppedAt'`.

**Cause.** I'd read the wall clock from the array parent's `stoppedAt`; Batch didn't return one for the parent.

**Fix.** The run ends when its last child stops, so the wall clock is the latest child `stoppedAt` minus the parent's `createdAt`: 236.2 s ([`25`](screenshots/25-batch-graviton-summary.png)).

## 4. The Spot replacement's first launch failed

**Symptom.** After the interruption, the Auto Scaling group logged `Failed  Launching a new EC2 instance. Status Reason: Could not launch Spot Instances. InsufficientInstanceCapacity` ([`15`](screenshots/15-spot-interruption-handled.png)).

**Cause.** No Spot capacity for the request in the AZ it tried first. That's Spot working as designed, not a fault.

**Result.** 9 seconds later the group launched an m6g.large in us-east-1c, a different type in a different AZ, which resumed at year 620,000. This is the reason the group lists four instance types across three AZs ([ADR 0004](adr/0004-spot-with-checkpoints-and-diversified-pools.md)).

## 5. A second FIS experiment failed

**Symptom.** `get-experiment` on the ID I'd saved showed `state: failed`, `action: failed`, started 13:02:53, ended 13:03:05 local ([`18`](screenshots/18-second-fis-failed-and-resume.png)).

**Cause.** I had started the experiment twice. The first (13:00:30, `completed`, [`16`](screenshots/16-fis-experiment-completed.png)) interrupted the only worker; the second, started from another terminal two minutes later while that instance was still serving its notice, failed (most likely because there was no interruptible target left; I didn't capture the experiment's failure reason), and its ID is the one the results file kept. (`targets: null` appears on both, because my query didn't capture targets.)

**Lesson.** An interruption experiment is a one-shot action on a live target: run it from one place, save each experiment's ID under its own name, and record the failure reason (`state.reason`) when one fails.

## 6. The interrupted Spot job's final answer wasn't captured on AWS

**Symptom.** The summary showed the Spot job's result as `None`; Batch's "same as Spot job" as `None`.

**Cause.** I ran the final status right after the resume (26.7%) and switched the Spot lab off, so the resumed worker never finished, and the bucket holding its checkpoint went at teardown.

**Fix.** The model makes the answer reproducible: I replayed the same split on my laptop (years 0–619,999 + 620,000–2,399,999, merged) and got `0cb96b0f9d9c5303`, the digest of both Batch runs. The repo states which part was measured on AWS and which was reproduced ([`spot.md`](spot.md)).

**Lesson.** Collect the final result before switching a lab off: `spot_status.py --watch` until it reports finished is there for that.
