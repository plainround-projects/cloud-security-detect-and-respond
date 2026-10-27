output "role_arn" {
  description = "ARN of the over-privileged role."
  value       = aws_iam_role.broad.arn
}

output "bucket_name" {
  description = "The drill bucket."
  value       = aws_s3_bucket.data.bucket
}
