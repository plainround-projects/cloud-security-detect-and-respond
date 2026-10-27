output "bucket_name" {
  description = "Name of the archive bucket."
  value       = aws_s3_bucket.archive.bucket
}
