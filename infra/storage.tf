# One bucket: the tool code (code/app/*.py) and the Spot job's checkpoints, events and result
# (spot-job/). force_destroy: "terraform destroy" empties and removes it.

resource "aws_s3_bucket" "hpc" {
  bucket        = local.bucket
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "hpc" {
  bucket                  = aws_s3_bucket.hpc.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "hpc" {
  bucket = aws_s3_bucket.hpc.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_policy" "tls_only" {
  bucket = aws_s3_bucket.hpc.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "TLSOnly"
      Effect    = "Deny"
      Principal = "*"
      Action    = "s3:*"
      Resource  = [aws_s3_bucket.hpc.arn, "${aws_s3_bucket.hpc.arn}/*"]
      Condition = { Bool = { "aws:SecureTransport" = "false" } }
    }]
  })
  depends_on = [aws_s3_bucket_public_access_block.hpc]
}

resource "aws_s3_bucket_lifecycle_configuration" "hpc" {
  bucket = aws_s3_bucket.hpc.id
  rule {
    id     = "abort-incomplete-uploads"
    status = "Enabled"
    filter {}
    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}

# The tools travel through S3: the nodes copy them at boot (themba-sync). etag = MD5, so an
# edited file is uploaded again.
resource "aws_s3_object" "app" {
  for_each = fileset("${path.module}/../app", "*.py")
  bucket   = aws_s3_bucket.hpc.id
  key      = "code/app/${each.value}"
  source   = "${path.module}/../app/${each.value}"
  etag     = filemd5("${path.module}/../app/${each.value}")
}
