output "bucket" {
  description = "Code and Spot job state."
  value       = aws_s3_bucket.hpc.bucket
}

output "placement_nodes" {
  description = "Placement lab: node name => instance id, private IP, AZ, placement group."
  value = { for k, i in aws_instance.placement : k => {
    id = i.id, ip = i.private_ip, az = i.availability_zone, group = i.placement_group
  } }
}

output "bench_nodes" {
  description = "Benchmark nodes: name => instance id and type."
  value       = { for k, i in aws_instance.bench : k => { id = i.id, type = i.instance_type } }
}

output "spot_asg" {
  description = "The Spot worker's Auto Scaling group."
  value       = var.spot_lab ? aws_autoscaling_group.spot_worker[0].name : ""
}

output "fis_template_id" {
  description = "The FIS experiment template that interrupts the Spot worker."
  value       = var.spot_lab ? aws_fis_experiment_template.spot_interrupt[0].id : ""
}

output "batch_queues" {
  description = "Batch job queues by architecture."
  value       = { for k, q in aws_batch_job_queue.cat : k => q.name }
}

output "batch_job_definition" {
  description = "The catsim job definition (name:revision)."
  value       = var.batch_lab ? "${aws_batch_job_definition.catsim[0].name}:${aws_batch_job_definition.catsim[0].revision}" : ""
}

output "app_sha256" {
  description = "SHA-256 of each tool file: compare with themba-sync's output on a node."
  value       = { for f in fileset("${path.module}/../app", "*.py") : f => filesha256("${path.module}/../app/${f}") }
}
