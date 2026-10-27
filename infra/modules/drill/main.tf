# The deliberate weakness the incident drill needs, and nothing else. It exists only while the exercise runs: the
# environment creates this module only when enable_drill is true, and `make down` removes it. The drill user's access key
# is NOT created here (it would sit in the state); scripts/03-drill-setup.sh creates it and prints nothing secret.
locals {
  user_arn = "arn:aws:iam::${var.account_id}:user/${var.user_name}"
}

resource "aws_iam_user" "drill" {
  #checkov:skip=CKV_AWS_273:The drill needs a long-lived user key: that is the leaked credential the exercise detects.
  name = var.user_name
  tags = { purpose = "incident-drill" }
}

# The user can do one thing: assume the broad role.
resource "aws_iam_user_policy" "assume_broad_role" {
  #checkov:skip=CKV_AWS_40:The drill user is a deliberate exception; it exists only while the drill runs.
  name = "assume-the-drill-role"
  user = aws_iam_user.drill.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "AssumeOnlyTheDrillRole"
      Effect   = "Allow"
      Action   = "sts:AssumeRole"
      Resource = "arn:aws:iam::${var.account_id}:role/${var.role_name}"
    }]
  })
}

resource "aws_iam_role" "broad" {
  name = var.role_name
  tags = { purpose = "incident-drill" }

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "OnlyTheDrillUserAssumes"
      Effect    = "Allow"
      Principal = { AWS = local.user_arn }
      Action    = "sts:AssumeRole"
    }]
  })

  depends_on = [aws_iam_user.drill]
}

# The weakness: far more than the role needs.
resource "aws_iam_role_policy_attachment" "power_user" {
  role       = aws_iam_role.broad.name
  policy_arn = "arn:aws:iam::aws:policy/PowerUserAccess"
}

# PowerUserAccess leaves out IAM, so the role is also allowed to mint a key for the drill user. That is what lets detection
# D1 fire on a call that succeeds, as in the lesson's timeline.
resource "aws_iam_role_policy" "mint_a_key_for_the_drill_user" {
  name = "create-access-key-for-the-drill-user"
  role = aws_iam_role.broad.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "CreateAKeyForTheDrillUserOnly"
      Effect   = "Allow"
      Action   = "iam:CreateAccessKey"
      Resource = local.user_arn
    }]
  })
}

# The target the attacker makes public. Block Public Access is off and ACLs are on: also deliberate, also temporary.
resource "aws_s3_bucket" "data" {
  #checkov:skip=CKV_AWS_18:Throwaway drill bucket.
  #checkov:skip=CKV_AWS_21:Throwaway drill bucket; versioning adds nothing to the drill.
  #checkov:skip=CKV_AWS_144:Throwaway drill bucket.
  #checkov:skip=CKV_AWS_145:Throwaway drill bucket holding no data.
  #checkov:skip=CKV2_AWS_6:Block Public Access is off on purpose: the drill makes this bucket public.
  #checkov:skip=CKV2_AWS_61:Throwaway drill bucket.
  #checkov:skip=CKV2_AWS_62:Throwaway drill bucket.
  bucket        = "${var.bucket_prefix}-${var.account_id}"
  force_destroy = true
  tags          = { purpose = "incident-drill" }
}

resource "aws_s3_bucket_ownership_controls" "data" {
  #checkov:skip=CKV2_AWS_65:ACLs stay enabled on purpose: the drill makes the bucket public with an ACL.
  bucket = aws_s3_bucket.data.bucket

  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_public_access_block" "data" {
  #checkov:skip=CKV_AWS_53:Deliberate drill weakness.
  #checkov:skip=CKV_AWS_54:Deliberate drill weakness.
  #checkov:skip=CKV_AWS_55:Deliberate drill weakness.
  #checkov:skip=CKV_AWS_56:Deliberate drill weakness.
  bucket                  = aws_s3_bucket.data.bucket
  block_public_acls       = false
  ignore_public_acls      = false
  block_public_policy     = false
  restrict_public_buckets = false
}

# The honeytoken: a user with no permissions at all. Any use of its key, allowed or denied, is an intruder. The key is created
# by scripts/06-honeytoken.sh and its id is passed to the environment so detection D5 can watch for it.
resource "aws_iam_user" "honeytoken" {
  #checkov:skip=CKV_AWS_273:A honeytoken is a user nobody should ever sign in as; its key is bait.
  count = var.enable_honeytoken ? 1 : 0

  name = "honeytoken-svc"
  tags = { purpose = "honeytoken" }
}
