variable "plan_only" {
  description = "Skip all provider calls so the configuration can be planned without credentials. Never true for apply."
  type        = bool
  default     = false
}

variable "region" {
  description = "The workload account's home Region."
  type        = string
  default     = "eu-west-1"
}

variable "workload_account_id" {
  description = "The sandbox workload account. scripts/02-deploy-workload.sh writes it; it is never committed."
  type        = string

  validation {
    condition     = can(regex("^[0-9]{12}$", var.workload_account_id))
    error_message = "workload_account_id must be 12 digits."
  }
}

variable "log_bucket_name" {
  description = "Archive bucket in the security account (output log_bucket_name of the security environment)."
  type        = string
}

variable "log_key_arn" {
  description = "Archive key in the security account (output log_key_arn of the security environment)."
  type        = string
}

variable "alert_email" {
  description = "Address that receives the alerts and the budget notices."
  type        = string
}

variable "monthly_budget_usd" {
  description = "Monthly cost limit for the account's budget."
  type        = number
  default     = 20
}

variable "enable_drill" {
  description = "Create the deliberate weakness for the incident drill. True only while the exercise runs."
  type        = bool
  default     = false
}

variable "enable_posture" {
  description = "Turn on Security Hub and AWS Config recording."
  type        = bool
  default     = true
}

variable "honeytoken_access_key_id" {
  description = "Access key id of the honeytoken user. Empty until scripts/06-honeytoken.sh has created it; detection D5 is deployed only when set."
  type        = string
  default     = ""
}

variable "force_destroy" {
  description = "Let destroy delete non-empty buckets. True only for the throwaway sandbox."
  type        = bool
  default     = false
}
