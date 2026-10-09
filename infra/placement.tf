# The placement group lab. A cluster group packs instances close together in one AZ (lowest
# latency, highest per-flow bandwidth between them); a spread group puts each instance on
# different hardware (racks with their own network and power), and can span AZs. Same instance
# type everywhere, so the only difference between the pairs is where they sit.

resource "aws_placement_group" "cluster" {
  count    = var.placement_lab ? 1 : 0
  name     = "themba-hpc-cluster"
  strategy = "cluster"
}

resource "aws_placement_group" "spread" {
  count        = var.placement_lab ? 1 : 0
  name         = "themba-hpc-spread"
  strategy     = "spread"
  spread_level = "rack"
}

resource "aws_instance" "placement" {
  for_each = var.placement_lab ? local.placement_nodes : {}

  ami                    = data.aws_ssm_parameter.al2023_x86.insecure_value
  instance_type          = var.placement_instance_type
  subnet_id              = aws_subnet.public[each.value.az].id
  vpc_security_group_ids = [aws_security_group.nodes.id]
  iam_instance_profile   = aws_iam_instance_profile.node.name
  placement_group        = each.value.group == "cluster" ? aws_placement_group.cluster[0].id : aws_placement_group.spread[0].id

  metadata_options {
    http_tokens   = "required"
    http_endpoint = "enabled"
  }

  root_block_device {
    volume_type = "gp3"
    encrypted   = true
  }

  user_data = templatefile("${path.module}/templates/userdata.sh.tftpl", {
    region = var.region, bucket = aws_s3_bucket.hpc.bucket, role = "placement"
  })
  user_data_replace_on_change = true

  tags = { Name = "themba-pg-${each.key}", PlacementLab = each.value.group }

  depends_on = [aws_s3_object.app, aws_route.internet, aws_route_table_association.public, aws_vpc_security_group_egress_rule.all, aws_iam_role_policy.node]

  lifecycle {
    ignore_changes = [ami]
  }
}
