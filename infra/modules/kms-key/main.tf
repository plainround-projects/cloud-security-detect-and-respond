locals {
  # Management only. The account root is deliberately not given kms:Decrypt or kms:Encrypt, so an IAM policy cannot
  # reach the data; only the principals in `statements` can use the key.
  administration_actions = [
    "kms:Create*", "kms:Describe*", "kms:Enable*", "kms:List*", "kms:Put*", "kms:Update*", "kms:Revoke*",
    "kms:Disable*", "kms:Get*", "kms:Delete*", "kms:TagResource", "kms:UntagResource",
    "kms:ScheduleKeyDeletion", "kms:CancelKeyDeletion",
  ]

  administration = {
    Sid       = "AccountAdministersKey"
    Effect    = "Allow"
    Principal = { AWS = "arn:aws:iam::${var.account_id}:root" }
    Action    = local.administration_actions
    Resource  = "*"
  }
}

resource "aws_kms_key" "this" {
  description             = var.description
  enable_key_rotation     = true
  deletion_window_in_days = var.deletion_window_in_days
  policy                  = jsonencode({ Version = "2012-10-17", Statement = concat([local.administration], var.statements) })
}

resource "aws_kms_alias" "this" {
  name          = "alias/${var.alias}"
  target_key_id = aws_kms_key.this.key_id
}
