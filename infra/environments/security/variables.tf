variable "plan_only" {
  description = "Skip all provider calls so the configuration can be planned without credentials. Never true for apply."
  type        = bool
  default     = false
}

variable "region" {
  description = "Region of the archive bucket (the workload account's home Region)."
  type        = string
  default     = "eu-west-1"
}

variable "security_account_id" {
  description = "The security account, which owns the archive. scripts/01-deploy-security.sh writes it; it is never committed."
  type        = string

  validation {
    condition     = can(regex("^[0-9]{12}$", var.security_account_id))
    error_message = "security_account_id must be 12 digits."
  }
}

variable "workload_account_id" {
  description = "The workload account whose trail delivers here."
  type        = string

  validation {
    condition     = can(regex("^[0-9]{12}$", var.workload_account_id))
    error_message = "workload_account_id must be 12 digits."
  }
}

variable "retention_days" {
  description = "Compliance-mode retention. Nobody can shorten it, so the exercise uses 1."
  type        = number
  default     = 1
}

variable "expire_days" {
  description = "Days after which log files expire and the bucket can be destroyed."
  type        = number
  default     = 2
}
