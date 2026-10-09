# The Terraform

## Why

Apart from `aws-terraform-iac-pipeline`, I built my earlier environments from the AWS CLI, chaining commands into long sequences. Most of those chains were the same work every time, and every manual teardown risked one forgotten delete left billing. Since `aws-dynamodb-data-modeling` the infrastructure is code. What I still run by hand are the measurements.

## Layout

| Path | What |
|---|---|
| `bootstrap/main.tf` | The shared state bucket `nkosi-tfstate-<account>` (versioned, encrypted, TLS-only, `prevent_destroy`). Created in `aws-dynamodb-data-modeling`; this project only checks it exists. |
| `infra/versions.tf` | Terraform >= 1.11, AWS provider `~> 6.60` (6.68.0 used), S3 backend with key `aws-compute-selection-hpc/terraform.tfstate` and `use_lockfile = true`, `default_tags` `Project` + `ManagedBy`. |
| `infra/variables.tf` | Region, three AZs (the first must offer every benchmark type), instance types per lab, the Spot job's size and chunk, Batch's max vCPUs, and the **lab switches**: `placement_lab`, `bench_lab`, `spot_lab`, `batch_lab`. |
| `infra/main.tf` | The two Amazon Linux 2023 AMIs (x86_64 and arm64, from SSM parameters), which bench types are Graviton (picks the AMI), the placement nodes. |
| `infra/network.tf` | VPC, three public subnets (no NAT gateway: it would cost more than all the labs), internet gateway, S3 gateway endpoint, one security group: inbound only from itself (node-to-node tests), outbound open. |
| `infra/storage.tf` | The bucket (public access blocked, SSE-S3, TLS-only, abort incomplete uploads) and the tool files as objects (etag = MD5). |
| `infra/iam.tf` | Node role (SSM, read `code/`, read/write `spot-job/`), Batch instance role (ECS), FIS role (interrupt only instances tagged `themba-spot-worker`). |
| `infra/placement.tf` | Cluster and spread placement groups, five c7i.large nodes. |
| `infra/bench.tf` | One on-demand node per benchmark type. |
| `infra/spot.tf` | `job.json`, the launch template, the Auto Scaling group (mixed instances, 100% Spot, 4 types, 3 AZs), the FIS experiment template. |
| `infra/batch.tf` | Log group, two Spot compute environments, two queues, the job definition. |
| `infra/templates/userdata.sh.tftpl` | One boot script for every node: settings, code from S3, the `catsim` command, then per role an iperf3 server (placement) or the worker service (spot). |

## Phases

| Phase | Line | Plan | Result |
|---|---|---|---|
| Base | (none) | `26 to add` | `26 added`; state list 29 (26 + 3 data sources) |
| Placement lab | `placement_lab = true` | `7 to add` | `7 added`, measured, then `7 destroyed` |
| Processor lab | `bench_lab = true` | `3 to add` | `3 added`, measured, then `3 destroyed` |
| Spot lab | `spot_lab = true` | `6 to add` | measured, then `6 destroyed` |
| Batch lab | `batch_lab = true` | `9 to add` | `9 added` |
| Job definition fix | (code change: gzip) | `0 to add, 1 to change` | updated in place: `themba-catsim:2` |
| Batch lab off | line deleted | | `9 destroyed` |
| Destroy | | `26 to destroy` | **`Destroy complete! Resources: 26 destroyed.`** |

Screenshots: [`04`](screenshots/04-base-apply-26.png), [`06`](screenshots/06-placement-apply-7.png), [`09`](screenshots/09-placement-destroyed-7.png), [`10`](screenshots/10-bench-apply-3.png), [`13`](screenshots/13-bench-destroyed-3.png), [`19`](screenshots/19-spot-destroyed-6.png), [`20`](screenshots/20-batch-apply-9.png), [`29`](screenshots/29-batch-destroyed-9.png), [`31`](screenshots/31-destroy-26.png). Plans in [`results/raw/`](results/raw/).

## Things Terraform taught me in this build

- **Labs as `count`/`for_each` behind one variable keep cost honest.** Each lab existed only for its measurement; the plan before each apply showed exactly the 7, 3, 6 or 9 resources it would add, and the apply after showed the same number destroyed.
- **A job definition change is a new revision, not a replacement.** The gzip fix showed as `1 to change` in place; AWS Batch registered `themba-catsim:2` and Terraform tracked it. Old revisions stay in Batch as INACTIVE.
- **Batch makes resources Terraform doesn't own:** the ECS cluster behind each compute environment and the instances it launches. Terraform deletes the compute environment (disabling it first), and Batch removes what it made. The clean check confirmed no `themba-` ECS cluster was left.
- **Verify through AWS, not through Terraform.** cluster-a's three tool files and catsim.py on each bench node were hashed after boot and matched Terraform's `app_sha256` output, and the compute environments were described with the AWS CLI after the apply.

## Quality gates

`terraform fmt -check -recursive` (clean), `terraform validate` (`Success! The configuration is valid.`), `tflint --recursive` with the recommended rules (clean), `checkov --soft-fail`: **74 passed, 19 failed, 0 skipped** ([`02`](screenshots/02-init-fmt-validate.png), [`03`](screenshots/03-tflint-checkov.png), [`results/raw/checkov.txt`](results/raw/checkov.txt)). The scan includes `bootstrap/`, so the state bucket appears in it.

| Check | Resource(s) | Decision for this lab | In production |
|---|---|---|---|
| CKV_AWS_145 S3 KMS by default | state, hpc buckets | accepted: SSE-S3 | KMS on the state bucket |
| CKV_AWS_18 S3 access logging | state, hpc | accepted | access logs on the state bucket |
| CKV_AWS_144 S3 cross-Region replication | state, hpc | accepted | replicate the state bucket |
| CKV2_AWS_62 S3 event notifications | state, hpc | not needed | not needed |
| CKV_AWS_21 S3 versioning | hpc | accepted: code is rebuilt from the repo; checkpoints are rewritten on purpose | versioning if results must be kept |
| CKV_AWS_300 abort incomplete uploads | state bucket's lifecycle | **fix**: add it to the bootstrap (the hpc bucket has it) | fix |
| CKV_AWS_130 subnets assign public IPs | 3 public subnets | accepted: no NAT gateway, outbound only, no inbound rules | private subnets + NAT or VPC endpoints for ECR/ECS/SSM |
| CKV_AWS_126 / CKV_AWS_135 detailed monitoring, EBS-optimised | bench and placement nodes | not needed for short tests (current types are EBS-optimised by default; the check reads the argument) | set explicitly |
| CKV2_AWS_11 VPC flow logs | VPC | accepted for a lab | flow logs on |
| CKV2_AWS_12 default security group | VPC | **fix**: manage the default group with no rules | fix |

19 findings: 4 checks × 2 buckets, 1 versioning, 1 lifecycle, 3 subnets, 2 × 2 on the nodes, 2 on the VPC.
