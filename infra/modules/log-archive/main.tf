# The central, tamper-resistant log store. It lives in a separate account (the security account): an administrator of the
# workload account has no rights here. Object Lock in compliance mode means even this account's owner cannot delete or
# shorten the retention of a log file inside the retention period.
locals {
  trail_arn = "arn:aws:cloudtrail:${var.region}:${var.workload_account_id}:trail/${var.trail_name}"
}

resource "aws_s3_bucket" "archive" {
  #checkov:skip=CKV_AWS_18:Access to the archive is itself recorded by the security account's own trail in a real organization; this build keeps one trail.
  #checkov:skip=CKV_AWS_144:Cross-region replication of the archive is a production decision, see ARCHITECTURE.md.
  #checkov:skip=CKV2_AWS_62:Nothing reacts to log delivery here; detection runs from the rules in the workload account and the batch scan.
  bucket              = var.bucket_name
  object_lock_enabled = true
}

resource "aws_s3_bucket_ownership_controls" "archive" {
  bucket = aws_s3_bucket.archive.bucket

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_public_access_block" "archive" {
  bucket                  = aws_s3_bucket.archive.bucket
  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "archive" {
  bucket = aws_s3_bucket.archive.bucket

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "archive" {
  bucket = aws_s3_bucket.archive.bucket

  rule {
    bucket_key_enabled = true

    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = var.key_alias_arn
    }
  }
}

# Compliance mode cannot be shortened or removed by anyone. The exercise uses a one-day retention so teardown is possible.
resource "aws_s3_bucket_object_lock_configuration" "archive" {
  bucket = aws_s3_bucket.archive.bucket

  rule {
    default_retention {
      mode = "COMPLIANCE"
      days = var.retention_days
    }
  }

  depends_on = [aws_s3_bucket_versioning.archive]
}

# Files leave only by expiring after the retention has ended; nobody deletes them by hand.
resource "aws_s3_bucket_lifecycle_configuration" "archive" {
  bucket = aws_s3_bucket.archive.bucket

  rule {
    id     = "expire-after-retention"
    status = "Enabled"

    filter {}

    expiration {
      days = var.expire_days
    }

    noncurrent_version_expiration {
      noncurrent_days = var.expire_days
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  depends_on = [aws_s3_bucket_versioning.archive]
}

resource "aws_s3_bucket_policy" "archive" {
  bucket = aws_s3_bucket.archive.bucket

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "TrailChecksTheBucketAcl"
        Effect    = "Allow"
        Principal = { Service = "cloudtrail.amazonaws.com" }
        Action    = "s3:GetBucketAcl"
        Resource  = "arn:aws:s3:::${var.bucket_name}"
        Condition = { StringEquals = { "aws:SourceArn" = local.trail_arn } }
      },
      {
        Sid       = "TrailWritesLogFilesOfTheWorkloadAccount"
        Effect    = "Allow"
        Principal = { Service = "cloudtrail.amazonaws.com" }
        Action    = "s3:PutObject"
        Resource  = "arn:aws:s3:::${var.bucket_name}/AWSLogs/${var.workload_account_id}/*"
        Condition = {
          StringEquals = { "s3:x-amz-acl" = "bucket-owner-full-control", "aws:SourceArn" = local.trail_arn }
        }
      },
      {
        Sid       = "NobodyDeletesOrRewritesLogFiles"
        Effect    = "Deny"
        Principal = { AWS = "*" }
        Action    = ["s3:DeleteObject", "s3:DeleteObjectVersion", "s3:PutObjectRetention", "s3:BypassGovernanceRetention"]
        Resource  = "arn:aws:s3:::${var.bucket_name}/*"
      },
      {
        Sid       = "DenyPlainHttp"
        Effect    = "Deny"
        Principal = { AWS = "*" }
        Action    = "s3:*"
        Resource  = ["arn:aws:s3:::${var.bucket_name}", "arn:aws:s3:::${var.bucket_name}/*"]
        Condition = { Bool = { "aws:SecureTransport" = "false" } }
      },
    ]
  })

  depends_on = [aws_s3_bucket_public_access_block.archive]
}
