variable "bucket_name" {
  description = "Name of the archive bucket, in the security account."
  type        = string
}

variable "workload_account_id" {
  description = "The account whose trail delivers here; only its trail may write."
  type        = string
}

variable "region" {
  description = "Home region of the workload account's trail."
  type        = string
}

variable "trail_name" {
  description = "Name of the workload account's trail; the bucket policy admits that trail only."
  type        = string
}

variable "key_alias_arn" {
  description = "Alias ARN of the key that encrypts the archive."
  type        = string
}

variable "retention_days" {
  description = "Compliance-mode retention. Nobody can shorten it, so the exercise uses 1."
  type        = number
  default     = 1

  validation {
    condition     = var.retention_days >= 1
    error_message = "retention_days must be at least 1."
  }
}

variable "expire_days" {
  description = "Days after which log files expire. Must be longer than retention_days."
  type        = number
  default     = 2
}
