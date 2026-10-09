# One VPC, three public subnets (one per AZ). Public so that Batch instances and the nodes can
# reach package repositories, the public ECR gallery, SSM and S3 without a NAT gateway (which
# would cost more than everything else here). Nothing is reachable from outside: the security
# group allows inbound traffic only from itself (node to node, for the network tests).

resource "aws_vpc" "lab" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  tags                 = { Name = "themba-hpc-vpc" }
}

resource "aws_subnet" "public" {
  count                   = 3
  vpc_id                  = aws_vpc.lab.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index + 1)
  availability_zone       = var.azs[count.index]
  map_public_ip_on_launch = true
  tags                    = { Name = "themba-hpc-public-${substr(var.azs[count.index], -1, 1)}" }
}

resource "aws_internet_gateway" "lab" {
  vpc_id = aws_vpc.lab.id
  tags   = { Name = "themba-hpc-igw" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.lab.id
  tags   = { Name = "themba-hpc-public-rt" }
}

resource "aws_route" "internet" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.lab.id
}

resource "aws_route_table_association" "public" {
  count          = 3
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.lab.id
  service_name      = "com.amazonaws.${var.region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.public.id]
  tags              = { Name = "themba-hpc-s3-endpoint" }
}

resource "aws_security_group" "nodes" {
  name        = "themba-hpc-nodes"
  description = "HPC lab nodes - inbound only from each other, no internet inbound"
  vpc_id      = aws_vpc.lab.id
  tags        = { Name = "themba-hpc-nodes" }
}

# Node to node: ping and iperf3 for the placement group tests.
resource "aws_vpc_security_group_ingress_rule" "self" {
  security_group_id            = aws_security_group.nodes.id
  description                  = "All traffic from other lab nodes"
  ip_protocol                  = "-1"
  referenced_security_group_id = aws_security_group.nodes.id
}

resource "aws_vpc_security_group_egress_rule" "all" {
  security_group_id = aws_security_group.nodes.id
  description       = "Outbound: packages, SSM, S3, ECR Public, Batch/ECS"
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}
