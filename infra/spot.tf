# The interruptible Spot job. An Auto Scaling group of exactly one Spot instance runs
# catsim-worker, which saves a checkpoint to S3 after every chunk of years and watches the
# instance metadata for the 2-minute interruption notice. When AWS FIS interrupts it, the group
# launches a replacement, which carries on from the last checkpoint.

resource "aws_s3_object" "spot_job" {
  count        = var.spot_lab ? 1 : 0
  bucket       = aws_s3_bucket.hpc.id
  key          = "spot-job/job.json"
  content_type = "application/json"
  content      = jsonencode({ seed = 26, years = var.spot_job_years, chunk = var.spot_job_chunk })
}

resource "aws_launch_template" "spot_worker" {
  count         = var.spot_lab ? 1 : 0
  name          = "themba-spot-worker"
  image_id      = data.aws_ssm_parameter.al2023_arm.insecure_value
  instance_type = var.spot_instance_types[0]

  iam_instance_profile {
    name = aws_iam_instance_profile.node.name
  }

  vpc_security_group_ids = [aws_security_group.nodes.id]

  metadata_options {
    http_tokens   = "required"
    http_endpoint = "enabled"
  }

  block_device_mappings {
    device_name = "/dev/xvda"
    ebs {
      volume_type = "gp3"
      encrypted   = true
    }
  }

  user_data = base64encode(templatefile("${path.module}/templates/userdata.sh.tftpl", {
    region = var.region, bucket = aws_s3_bucket.hpc.bucket, role = "spot"
  }))

  tag_specifications {
    resource_type = "instance"
    tags          = { Name = "themba-spot-worker", Project = "aws-compute-selection-hpc", ManagedBy = "terraform" }
  }

  lifecycle {
    ignore_changes = [image_id]
  }
}

resource "aws_autoscaling_group" "spot_worker" {
  count               = var.spot_lab ? 1 : 0
  name                = "themba-spot-worker"
  min_size            = 1
  max_size            = 1
  desired_capacity    = 1
  vpc_zone_identifier = aws_subnet.public[*].id
  health_check_type   = "EC2"

  # Capacity rebalancing stays off: it would start a second worker before the first one stops,
  # and two workers would write the same checkpoint. (A production version uses a lease.)
  capacity_rebalance = false

  mixed_instances_policy {
    instances_distribution {
      on_demand_base_capacity                  = 0
      on_demand_percentage_above_base_capacity = 0
      spot_allocation_strategy                 = "price-capacity-optimized"
    }

    launch_template {
      launch_template_specification {
        launch_template_id = aws_launch_template.spot_worker[0].id
        version            = aws_launch_template.spot_worker[0].latest_version
      }

      dynamic "override" {
        for_each = var.spot_instance_types
        content {
          instance_type = override.value
        }
      }
    }
  }

  depends_on = [aws_s3_object.spot_job, aws_s3_object.app, aws_route.internet, aws_route_table_association.public, aws_vpc_security_group_egress_rule.all, aws_iam_role_policy.node]
}

# AWS FIS: send ONE running instance named themba-spot-worker the real Spot interruption
# sequence (rebalance recommendation, then the 2-minute notice, then termination).
resource "aws_fis_experiment_template" "spot_interrupt" {
  count       = var.spot_lab ? 1 : 0
  description = "Interrupt the Themba Spot worker with a 2-minute notice"
  role_arn    = aws_iam_role.fis[0].arn

  stop_condition {
    source = "none"
  }

  target {
    name           = "spot-worker"
    resource_type  = "aws:ec2:spot-instance"
    selection_mode = "COUNT(1)"

    resource_tag {
      key   = "Name"
      value = "themba-spot-worker"
    }

    filter {
      path   = "State.Name"
      values = ["running"]
    }
  }

  action {
    name      = "interrupt"
    action_id = "aws:ec2:send-spot-instance-interruptions"

    parameter {
      key   = "durationBeforeInterruption"
      value = "PT2M"
    }

    target {
      key   = "SpotInstances"
      value = "spot-worker"
    }
  }

  tags = { Name = "themba-spot-interrupt" }

  depends_on = [aws_iam_role_policy.fis]
}
