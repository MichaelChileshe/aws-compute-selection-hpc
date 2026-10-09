variable "region" {
  description = "Region for everything."
  type        = string
  default     = "us-east-1"
}

variable "azs" {
  description = "Three Availability Zones for the public subnets. The first one must offer every instance type the labs use (checked before the first apply)."
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]

  validation {
    condition     = length(var.azs) == 3
    error_message = "azs must list exactly three Availability Zones."
  }
}

variable "vpc_cidr" {
  description = "CIDR block of the lab VPC."
  type        = string
  default     = "10.140.0.0/16"
}

variable "placement_instance_type" {
  description = "Instance type for the placement group lab (all five nodes)."
  type        = string
  default     = "c7i.large"
}

variable "bench_instance_types" {
  description = "One node per type for the price-performance benchmark: name => instance type. Graviton types get the arm64 AMI automatically."
  type        = map(string)
  default = {
    graviton = "c7g.large"
    intel    = "c7i.large"
    amd      = "c7a.large"
  }
}

variable "spot_instance_types" {
  description = "Graviton types the Spot worker's Auto Scaling group may use (more types = more Spot pools to choose from)."
  type        = list(string)
  default     = ["c7g.large", "m7g.large", "c6g.large", "m6g.large"]
}

variable "spot_job_years" {
  description = "Years the interruptible Spot job simulates (the Batch run uses the same total, so the two answers can be compared)."
  type        = number
  default     = 2400000
}

variable "spot_job_chunk" {
  description = "Years per checkpoint: small enough to finish well inside a 2-minute interruption notice."
  type        = number
  default     = 20000
}

variable "batch_max_vcpus" {
  description = "Most vCPUs each Batch compute environment may run at once (keep within the account's Spot vCPU quota)."
  type        = number
  default     = 16
}

# ---- phase switches: set in phases.auto.tfvars as the build goes on ----

variable "placement_lab" {
  description = "Five c7i nodes: two in a cluster placement group, three in a spread group (two in the first AZ, one in the second)."
  type        = bool
  default     = false
}

variable "bench_lab" {
  description = "One on-demand node per bench_instance_types entry, for the Graviton / Intel / AMD benchmark."
  type        = bool
  default     = false
}

variable "spot_lab" {
  description = "The checkpointing Spot worker (an Auto Scaling group of one) and the FIS experiment that interrupts it."
  type        = bool
  default     = false
}

variable "batch_lab" {
  description = "AWS Batch: Graviton and x86 Spot compute environments, a queue for each, the job definition."
  type        = bool
  default     = false
}
