variable "name" {
  description = "Trail name; the archive bucket policy admits this trail only."
  type        = string
}

variable "log_bucket_name" {
  description = "Archive bucket in the security account."
  type        = string
}

variable "log_key_arn" {
  description = "ARN of the archive key in the security account."
  type        = string
}
