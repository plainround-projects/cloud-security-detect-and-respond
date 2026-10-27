variable "alias" {
  description = "Alias of the key, without the alias/ prefix."
  type        = string
}

variable "description" {
  description = "What the key protects."
  type        = string
}

variable "account_id" {
  description = "Account that owns the key; its root administers the key."
  type        = string
}

variable "region" {
  description = "Region of the key."
  type        = string
}

variable "statements" {
  description = "Key policy statements that grant use of the key, as policy-document statement objects."
  type        = any
  default     = []
}

variable "deletion_window_in_days" {
  description = "Waiting period before a scheduled deletion takes effect (7 to 30)."
  type        = number
  default     = 7
}
