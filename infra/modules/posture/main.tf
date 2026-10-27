# Posture management: Security Hub with the foundational best-practices standard, fed by AWS Config recording.
locals {
  config_bucket = "${var.name}-config-${var.account_id}"
}

resource "aws_s3_bucket" "config" {
  #checkov:skip=CKV_AWS_18:The recorder's own delivery bucket; CloudTrail data events are not enabled for it.
  #checkov:skip=CKV_AWS_144:Single-region sandbox.
  #checkov:skip=CKV_AWS_145:AWS Config delivers with the recorder's role; a customer-managed key needs further grants outside this lesson.
  #checkov:skip=CKV2_AWS_62:Nothing reacts to configuration snapshots here.
  bucket        = local.config_bucket
  force_destroy = var.force_destroy
}

resource "aws_s3_bucket_public_access_block" "config" {
  bucket                  = aws_s3_bucket.config.bucket
  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "config" {
  bucket = aws_s3_bucket.config.bucket

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_versioning" "config" {
  bucket = aws_s3_bucket.config.bucket

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "config" {
  bucket = aws_s3_bucket.config.bucket

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "config" {
  bucket = aws_s3_bucket.config.bucket

  rule {
    id     = "expire-snapshots"
    status = "Enabled"

    filter {}

    expiration {
      days = var.retention_days
    }

    noncurrent_version_expiration {
      noncurrent_days = 7
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  depends_on = [aws_s3_bucket_versioning.config]
}

resource "aws_s3_bucket_policy" "config" {
  bucket = aws_s3_bucket.config.bucket

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyPlainHttp"
        Effect    = "Deny"
        Principal = { AWS = "*" }
        Action    = "s3:*"
        Resource  = ["arn:aws:s3:::${local.config_bucket}", "arn:aws:s3:::${local.config_bucket}/*"]
        Condition = { Bool = { "aws:SecureTransport" = "false" } }
      },
    ]
  })

  depends_on = [aws_s3_bucket_public_access_block.config]
}

resource "aws_iam_role" "config" {
  name = "${var.name}-config-recorder"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "config.amazonaws.com" }
      Action    = "sts:AssumeRole"
      Condition = { StringEquals = { "aws:SourceAccount" = var.account_id } }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "config" {
  role       = aws_iam_role.config.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWS_ConfigRole"
}

resource "aws_iam_role_policy" "deliver" {
  name = "deliver-to-the-config-bucket"
  role = aws_iam_role.config.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "CheckTheBucket"
        Effect   = "Allow"
        Action   = "s3:GetBucketAcl"
        Resource = "arn:aws:s3:::${local.config_bucket}"
      },
      {
        Sid       = "WriteSnapshots"
        Effect    = "Allow"
        Action    = "s3:PutObject"
        Resource  = "arn:aws:s3:::${local.config_bucket}/AWSLogs/${var.account_id}/Config/*"
        Condition = { StringEquals = { "s3:x-amz-acl" = "bucket-owner-full-control" } }
      },
    ]
  })
}

resource "aws_config_configuration_recorder" "this" {
  name     = var.name
  role_arn = aws_iam_role.config.arn

  recording_group {
    all_supported                 = true
    include_global_resource_types = true
  }
}

resource "aws_config_delivery_channel" "this" {
  name           = var.name
  s3_bucket_name = aws_s3_bucket.config.bucket

  depends_on = [aws_config_configuration_recorder.this, aws_s3_bucket_policy.config]
}

resource "aws_config_configuration_recorder_status" "this" {
  name       = aws_config_configuration_recorder.this.name
  is_enabled = true

  depends_on = [aws_config_delivery_channel.this]
}

resource "aws_securityhub_account" "this" {
  depends_on = [aws_config_configuration_recorder_status.this]
}

resource "aws_securityhub_standards_subscription" "foundational" {
  standards_arn = "arn:aws:securityhub:${var.region}::standards/aws-foundational-security-best-practices/v/1.0.0"

  depends_on = [aws_securityhub_account.this]
}
