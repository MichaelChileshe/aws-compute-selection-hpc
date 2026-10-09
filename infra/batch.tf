# AWS Batch: the nightly run as an array job. Two managed Spot compute environments, one
# Graviton and one x86, each behind its own queue so the two can be measured separately. Batch
# starts instances when jobs are queued and terminates them when the queue is empty (min 0).
# The container is the public Amazon Linux 2023 image (multi-architecture, Python 3 included);
# the model travels in the job definition (gzip + base64, because Batch passes the environment
# to ECS as container overrides, limited to 8,192 characters), so there is no image to build.

resource "aws_cloudwatch_log_group" "batch" {
  count             = var.batch_lab ? 1 : 0
  name              = "/aws/batch/themba-cat"
  retention_in_days = 7
}

locals {
  batch_envs = var.batch_lab ? {
    graviton = ["c7g", "m7g", "c6g", "m6g"]
    x86      = ["c7i", "m7i", "c7a", "m7a", "c6i"]
  } : {}
}

resource "aws_batch_compute_environment" "spot" {
  for_each = local.batch_envs
  name     = "themba-cat-${each.key}"
  type     = "MANAGED"
  state    = "ENABLED"

  compute_resources {
    type                = "SPOT"
    allocation_strategy = "SPOT_PRICE_CAPACITY_OPTIMIZED"
    min_vcpus           = 0
    max_vcpus           = var.batch_max_vcpus
    instance_type       = each.value
    subnets             = aws_subnet.public[*].id
    security_group_ids  = [aws_security_group.nodes.id]
    instance_role       = aws_iam_instance_profile.batch_instance[0].arn

    ec2_configuration {
      image_type = "ECS_AL2023"
    }

    tags = { Name = "themba-batch-${each.key}", Project = "aws-compute-selection-hpc", ManagedBy = "terraform" }
  }

  depends_on = [aws_iam_role_policy_attachment.batch_instance_ecs, aws_route.internet, aws_route_table_association.public]
}

resource "aws_batch_job_queue" "cat" {
  for_each = local.batch_envs
  name     = "themba-cat-${each.key}"
  state    = "ENABLED"
  priority = 1

  compute_environment_order {
    order               = 1
    compute_environment = aws_batch_compute_environment.spot[each.key].arn
  }
}

resource "aws_batch_job_definition" "catsim" {
  count                 = var.batch_lab ? 1 : 0
  name                  = "themba-catsim"
  type                  = "container"
  platform_capabilities = ["EC2"]

  # A child whose instance is reclaimed (Spot) or fails to start is retried; a model error isn't.
  retry_strategy {
    attempts = 3
    evaluate_on_exit {
      on_status_reason = "Host EC2*"
      action           = "RETRY"
    }
    evaluate_on_exit {
      on_reason = "*"
      action    = "EXIT"
    }
  }

  timeout {
    attempt_duration_seconds = 1800
  }

  container_properties = jsonencode({
    image   = "public.ecr.aws/amazonlinux/amazonlinux:2023"
    command = ["python3", "-c", "import base64,gzip,os;exec(gzip.decompress(base64.b64decode(os.environ['CATSIM'])).decode())", "run", "--array", "--years", "Ref::years", "--procs", "2", "--raw"]
    resourceRequirements = [
      { type = "VCPU", value = "2" },
      { type = "MEMORY", value = "3000" },
    ]
    environment = [{ name = "CATSIM", value = base64gzip(file("${path.module}/../app/catsim.py")) }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.batch[0].name
        "awslogs-region"        = var.region
        "awslogs-stream-prefix" = "catsim"
      }
    }
  })

  parameters = { years = "60000" }
}
