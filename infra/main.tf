data "aws_caller_identity" "current" {}

# Latest Amazon Linux 2023 AMIs, one per CPU architecture.
data "aws_ssm_parameter" "al2023_x86" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

data "aws_ssm_parameter" "al2023_arm" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-arm64"
}

locals {
  account_id = data.aws_caller_identity.current.account_id
  bucket     = "themba-hpc-${local.account_id}-${var.region}"

  # Graviton instance families end their generation digit with "g" (c7g, m6g, r8g, c7gn ...).
  is_arm = { for k, t in var.bench_instance_types : k => can(regex("^[a-z]+[0-9]+g", t)) }

  # The placement lab: node name => placement group and AZ index.
  placement_nodes = {
    "cluster-a" = { group = "cluster", az = 0 }
    "cluster-b" = { group = "cluster", az = 0 }
    "spread-a"  = { group = "spread", az = 0 }
    "spread-b"  = { group = "spread", az = 0 }
    "spread-c"  = { group = "spread", az = 1 }
  }
}
