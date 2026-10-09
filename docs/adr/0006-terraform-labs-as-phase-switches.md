# 0006 · Terraform with the shared state bucket, each lab a phase switch

**Status:** accepted · 2026-10-09

## Context
Built entirely with Terraform, like the two projects before it. Four labs with very different resources (on-demand nodes, an Auto Scaling group with FIS, Batch) each needed to exist only while being measured.

## Decision
- One base (26 resources) for the day; each lab behind one boolean (`placement_lab`, `bench_lab`, `spot_lab`, `batch_lab`) in `infra/phases.auto.tfvars`, switched on, measured, switched off.
- Remote state in the shared bucket with `use_lockfile = true`; provider pinned by the committed lock file (aws 6.68.0).
- Quality gates before apply (fmt, validate, tflint, checkov), tags `Project` and `ManagedBy` on everything: `default_tags` for what Terraform creates, and explicit tags in the launch template and the compute environments for the instances the Auto Scaling group and Batch launch.

## Consequences
- Measured: 26 + 7 + 3 + 6 + 9 resources added across the day, each lab destroyed after its measurement, one in-place job definition update, `Destroy complete! Resources: 26 destroyed.`, clean check empty.
- Only one lab billed at a time, which kept the build to about US$0.35–0.45.
- The `Project` tag on every resource is what a project-agnostic teardown tool can use instead of name prefixes.
