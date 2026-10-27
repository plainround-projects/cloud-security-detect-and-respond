locals {
  trail_name  = "central-trail"
  bucket_name = "detect-archive-${var.security_account_id}"
  trail_arn   = "arn:aws:cloudtrail:${var.region}:${var.workload_account_id}:trail/${local.trail_name}"
}

# The key that encrypts the archive. The workload account's trail may use it to write; the security account's principals may
# decrypt through the storage service; the account root administers it but cannot decrypt on its own authority.
module "archive_key" {
  source = "../../modules/kms-key"

  alias       = "detect-archive"
  description = "Encrypts the central audit log archive."
  account_id  = var.security_account_id
  region      = var.region

  statements = [
    {
      Sid       = "WorkloadTrailEncryptsLogFiles"
      Effect    = "Allow"
      Principal = { Service = "cloudtrail.amazonaws.com" }
      Action    = "kms:GenerateDataKey*"
      Resource  = "*"
      Condition = {
        StringEquals = { "aws:SourceArn" = local.trail_arn }
        StringLike   = { "kms:EncryptionContext:aws:cloudtrail:arn" = "arn:aws:cloudtrail:*:${var.workload_account_id}:trail/*" }
      }
    },
    {
      Sid       = "WorkloadTrailDescribesTheKey"
      Effect    = "Allow"
      Principal = { Service = "cloudtrail.amazonaws.com" }
      Action    = "kms:DescribeKey"
      Resource  = "*"
    },
    {
      Sid       = "SecurityAccountReadsLogsThroughTheStorageService"
      Effect    = "Allow"
      Principal = { AWS = "arn:aws:iam::${var.security_account_id}:root" }
      Action    = "kms:Decrypt"
      Resource  = "*"
      Condition = { StringEquals = { "kms:ViaService" = "s3.${var.region}.amazonaws.com" } }
    },
  ]
}

module "log_archive" {
  source = "../../modules/log-archive"

  bucket_name         = local.bucket_name
  workload_account_id = var.workload_account_id
  region              = var.region
  trail_name          = local.trail_name
  key_alias_arn       = module.archive_key.alias_arn
  retention_days      = var.retention_days
  expire_days         = var.expire_days

  depends_on = [module.archive_key]
}
