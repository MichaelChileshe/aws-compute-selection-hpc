# The price-performance benchmark: one on-demand node per instance type, same size (2 vCPU),
# same AMI family, same code. Graviton types get the arm64 AMI.

resource "aws_instance" "bench" {
  for_each = var.bench_lab ? var.bench_instance_types : {}

  ami                    = local.is_arm[each.key] ? data.aws_ssm_parameter.al2023_arm.insecure_value : data.aws_ssm_parameter.al2023_x86.insecure_value
  instance_type          = each.value
  subnet_id              = aws_subnet.public[0].id
  vpc_security_group_ids = [aws_security_group.nodes.id]
  iam_instance_profile   = aws_iam_instance_profile.node.name

  metadata_options {
    http_tokens   = "required"
    http_endpoint = "enabled"
  }

  root_block_device {
    volume_type = "gp3"
    encrypted   = true
  }

  user_data = templatefile("${path.module}/templates/userdata.sh.tftpl", {
    region = var.region, bucket = aws_s3_bucket.hpc.bucket, role = "bench"
  })
  user_data_replace_on_change = true

  tags = { Name = "themba-bench-${each.key}" }

  depends_on = [aws_s3_object.app, aws_route.internet, aws_route_table_association.public, aws_vpc_security_group_egress_rule.all, aws_iam_role_policy.node]

  lifecycle {
    ignore_changes = [ami]
  }
}
