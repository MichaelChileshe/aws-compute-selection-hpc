# ---- the EC2 nodes (placement, bench, Spot worker): SSM, read their code, use the Spot job's prefix ----

resource "aws_iam_role" "node" {
  name = "themba-hpc-node-role"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "ec2.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_role_policy" "node" {
  name = "code-and-spot-job"
  role = aws_iam_role.node.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ReadTheCode"
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = "${aws_s3_bucket.hpc.arn}/code/*"
      },
      {
        Sid      = "SpotJobState"
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject"]
        Resource = "${aws_s3_bucket.hpc.arn}/spot-job/*"
      },
      {
        Sid       = "ListOwnPrefixes"
        Effect    = "Allow"
        Action    = ["s3:ListBucket"]
        Resource  = aws_s3_bucket.hpc.arn
        Condition = { StringLike = { "s3:prefix" = ["code/*", "spot-job/*"] } }
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "node_ssm" {
  role       = aws_iam_role.node.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "node" {
  name = "themba-hpc-node-profile"
  role = aws_iam_role.node.name
}

# ---- AWS Batch container instances: join the ECS cluster Batch manages, write container logs ----

resource "aws_iam_role" "batch_instance" {
  count = var.batch_lab ? 1 : 0
  name  = "themba-batch-instance-role"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "ec2.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_role_policy_attachment" "batch_instance_ecs" {
  count      = var.batch_lab ? 1 : 0
  role       = aws_iam_role.batch_instance[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role"
}

resource "aws_iam_instance_profile" "batch_instance" {
  count = var.batch_lab ? 1 : 0
  name  = "themba-batch-instance-profile"
  role  = aws_iam_role.batch_instance[0].name
}

# ---- AWS FIS: allowed to send a Spot interruption to instances tagged as the Spot worker ----

resource "aws_iam_role" "fis" {
  count = var.spot_lab ? 1 : 0
  name  = "themba-fis-spot-role"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "fis.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_role_policy" "fis" {
  count = var.spot_lab ? 1 : 0
  name  = "interrupt-the-spot-worker"
  role  = aws_iam_role.fis[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "InterruptTaggedSpotWorkerOnly"
        Effect    = "Allow"
        Action    = "ec2:SendSpotInstanceInterruptions"
        Resource  = "arn:aws:ec2:${var.region}:${local.account_id}:instance/*"
        Condition = { StringEquals = { "aws:ResourceTag/Name" = "themba-spot-worker" } }
      },
      {
        Sid      = "FindTargets"
        Effect   = "Allow"
        Action   = ["ec2:DescribeInstances", "tag:GetResources"]
        Resource = "*"
      },
    ]
  })
}
