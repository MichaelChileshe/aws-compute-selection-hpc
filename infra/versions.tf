terraform {
  required_version = ">= 1.11.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.60"
    }
  }

  # Remote state in the shared bucket (one key per project), passed at init time:
  #   terraform init -backend-config="bucket=nkosi-tfstate-<account id>"
  # use_lockfile = S3-native state locking (no DynamoDB lock table).
  backend "s3" {
    key          = "aws-compute-selection-hpc/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = {
      Project   = "aws-compute-selection-hpc"
      ManagedBy = "terraform"
    }
  }
}
