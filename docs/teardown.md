# Teardown

Every lab was switched off after its measurement (`7`, `3`, `6` and `9 destroyed`), so the teardown is the base.

```bash
# from the repo folder
cat infra/phases.auto.tfvars 2>/dev/null   # empty: every lab is off
terraform -chdir=infra destroy -no-color 2>&1 | tee build/results/tf-destroy.txt
```

`Plan: 0 to add, 0 to change, 26 to destroy.` and **`Destroy complete! Resources: 26 destroyed.`** The bucket is emptied first (`force_destroy`), which also removes the Spot job's checkpoint and events, so collect results before this ([`31`](screenshots/31-destroy-26.png)).

## Clean check

Every line must print nothing, except the first (`0`) and the last (the empty state file). The filters use `themba-` with the hyphen.

```bash
terraform -chdir=infra state list | wc -l
aws ec2 describe-instances --filters Name=tag:Project,Values=aws-compute-selection-hpc Name=instance-state-name,Values=pending,running,stopping,stopped --query 'Reservations[].Instances[].InstanceId' --output text
aws ec2 describe-vpcs --filters Name=tag:Name,Values=themba-hpc-vpc --query 'Vpcs[].VpcId' --output text
aws ec2 describe-placement-groups --query 'PlacementGroups[?starts_with(GroupName, `themba-`)].GroupName' --output text
aws ec2 describe-launch-templates --query 'LaunchTemplates[?starts_with(LaunchTemplateName, `themba-`)].LaunchTemplateName' --output text
aws autoscaling describe-auto-scaling-groups --query 'AutoScalingGroups[?starts_with(AutoScalingGroupName, `themba-`)].AutoScalingGroupName' --output text
aws fis list-experiment-templates --query 'experimentTemplates[?tags.Name==`themba-spot-interrupt`].id' --output text
aws batch describe-compute-environments --query 'computeEnvironments[?starts_with(computeEnvironmentName, `themba-`)].computeEnvironmentName' --output text
aws batch describe-job-queues --query 'jobQueues[?starts_with(jobQueueName, `themba-`)].jobQueueName' --output text
aws batch describe-job-definitions --status ACTIVE --query 'jobDefinitions[?starts_with(jobDefinitionName, `themba-`)].jobDefinitionName' --output text
aws ecs list-clusters --query 'clusterArns[?contains(@, `themba-`)]' --output text
aws s3api list-buckets --query 'Buckets[?starts_with(Name, `themba-`)].Name' --output text
aws iam list-roles --query 'Roles[?starts_with(RoleName, `themba-`)].RoleName' --output text
aws iam list-instance-profiles --query 'InstanceProfiles[?starts_with(InstanceProfileName, `themba-`)].InstanceProfileName' --output text
aws logs describe-log-groups --log-group-name-prefix /aws/batch/themba --query 'logGroups[].logGroupName' --output text
aws s3 ls "s3://$STATE_BUCKET/aws-compute-selection-hpc/"
```

Result in this build: state list `0`, every AWS line empty, and a **304-byte** `terraform.tfstate` in the state bucket ([`32`](screenshots/32-clean-check.png), [`33`](screenshots/33-clean-check-state.png)).

**What stays, on purpose or by design:** the shared state bucket (`bootstrap/`, `prevent_destroy`); the job definition's revisions, which Batch keeps as INACTIVE (they can't be deleted by hand; AWS documents removing INACTIVE revisions after 180 days; free); the FIS experiment history (free).
