# Screenshots

In build order. The account ID is masked in every image.

| # | File | What it shows |
|---|---|---|
| 01 | [`01-state-bucket-azs-quotas.png`](screenshots/01-state-bucket-azs-quotas.png) | State bucket exists; c7a/c7g/c7i.large offered in us-east-1a, b, c, d and f; vCPU quotas: 16 on-demand, 32 Spot |
| 02 | [`02-init-fmt-validate.png`](screenshots/02-init-fmt-validate.png) | `terraform init` (aws 6.68.0), `fmt` clean, `validate` success |
| 03 | [`03-tflint-checkov.png`](screenshots/03-tflint-checkov.png) | `tflint` clean; checkov 74 passed, 19 failed |
| 04 | [`04-base-apply-26.png`](screenshots/04-base-apply-26.png) | Base: `Apply complete! Resources: 26 added`; outputs; state list 29 |
| 05 | [`05-local-split-check-digest.png`](screenshots/05-local-split-check-digest.png) | The model on my laptop: 4,000 years in one run and as two merged halves, same digest `78a9364c876e456c` |
| 06 | [`06-placement-apply-7.png`](screenshots/06-placement-apply-7.png) | Placement lab: `7 added`; the tool files' SHA-256 in the outputs |
| 07 | [`07-placement-nodes-and-first-pair.png`](screenshots/07-placement-nodes-and-first-pair.png) | cluster-a booted, its files' SHA-256 = Terraform's, iperf3 server active; where AWS put the five nodes; the cluster pair's numbers |
| 08 | [`08-placement-results.png`](screenshots/08-placement-results.png) | Placement results: three pairs, round trip and 1 / 8-stream throughput |
| 09 | [`09-placement-destroyed-7.png`](screenshots/09-placement-destroyed-7.png) | Placement lab off: `7 destroyed` |
| 10 | [`10-bench-apply-3.png`](screenshots/10-bench-apply-3.png) | Processor lab: `3 added` (c7a, c7g, c7i .large) |
| 11 | [`11-bench-node-cpus.png`](screenshots/11-bench-node-cpus.png) | Each node: same catsim.py SHA-256; architecture and Python 3.9.25; CPU (AMD EPYC 9R14, Graviton CPU part 0xd40, Intel Xeon 8488C) |
| 12 | [`12-bench-results.png`](screenshots/12-bench-results.png) | Benchmark: years per second with 1 and 2 processes, prices, US$ per million years; identical digest on every node |
| 13 | [`13-bench-destroyed-3.png`](screenshots/13-bench-destroyed-3.png) | Processor lab off: `3 destroyed` |
| 14 | [`14-spot-progress-before-interruption.png`](screenshots/14-spot-progress-before-interruption.png) | Spot job running on a c6g.large: 400,000 then 460,000 of 2,400,000 years |
| 15 | [`15-spot-interruption-handled.png`](screenshots/15-spot-interruption-handled.png) | The interruption: rebalance recommendation, notice, stopped at year 620,000 14.8 s after the notice; instance terminated; first replacement failed (no Spot capacity), second launching |
| 16 | [`16-fis-experiment-completed.png`](screenshots/16-fis-experiment-completed.png) | The FIS experiment that interrupted the worker: completed |
| 17 | [`17-second-fis-start-and-watch.png`](screenshots/17-second-fis-start-and-watch.png) | A second FIS experiment started from another terminal, and the status watch |
| 18 | [`18-second-fis-failed-and-resume.png`](screenshots/18-second-fis-failed-and-resume.png) | The second experiment failed; the replacement m6g.large resumed from year 620,000 |
| 19 | [`19-spot-destroyed-6.png`](screenshots/19-spot-destroyed-6.png) | Spot lab off: `6 destroyed` |
| 20 | [`20-batch-apply-9.png`](screenshots/20-batch-apply-9.png) | Batch lab: `9 added`; queues and job definition in the outputs |
| 21 | [`21-batch-compute-environments.png`](screenshots/21-batch-compute-environments.png) | Both compute environments ENABLED, VALID, SPOT, SPOT_PRICE_CAPACITY_OPTIMIZED, 0-16 vCPUs |
| 22 | [`22-batch-first-run-failed.png`](screenshots/22-batch-first-run-failed.png) | First Batch run: all 40 children FAILED in 18 s; my collect script's crash |
| 23 | [`23-batch-failure-reason.png`](screenshots/23-batch-failure-reason.png) | Batch's reason: `Container Overrides length must be at most 8192`; compute environments healthy |
| 24 | [`24-batch-graviton-run.png`](screenshots/24-batch-graviton-run.png) | Second Graviton run (job definition revision 2): RUNNABLE, RUNNING, SUCCEEDED=40 |
| 25 | [`25-batch-graviton-summary.png`](screenshots/25-batch-graviton-summary.png) | Graviton run summary: 40/40, 0 retries, 236.2 s, first start 65.8 s, instance types |
| 26 | [`26-batch-graviton-answer-instances.png`](screenshots/26-batch-graviton-answer-instances.png) | Graviton run answer (digest `0cb96b0f9d9c5303`) and the six Spot instances Batch used |
| 27 | [`27-batch-x86-run.png`](screenshots/27-batch-x86-run.png) | x86 run: submit, status lines, summary |
| 28 | [`28-batch-x86-answer-instances.png`](screenshots/28-batch-x86-answer-instances.png) | x86 run answer (same digest) and the five Spot instances |
| 29 | [`29-batch-destroyed-9.png`](screenshots/29-batch-destroyed-9.png) | Batch lab off: `9 destroyed` |
| 30 | [`30-results-summary.png`](screenshots/30-results-summary.png) | Results summary: Batch and Terraform sections |
| 31 | [`31-destroy-26.png`](screenshots/31-destroy-26.png) | `Destroy complete! Resources: 26 destroyed.` |
| 32 | [`32-clean-check.png`](screenshots/32-clean-check.png) | Clean check commands (all empty) |
| 33 | [`33-clean-check-state.png`](screenshots/33-clean-check-state.png) | Clean check end: state list 0, 304-byte empty state |
