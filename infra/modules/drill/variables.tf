variable "account_id" {
  description = "The sandbox account."
  type        = string
}

variable "user_name" {
  description = "The drill user that holds the leaked key."
  type        = string
  default     = "drill-user"
}

variable "role_name" {
  description = "The over-privileged role the drill user can assume."
  type        = string
  default     = "drill-broad-role"
}

variable "bucket_prefix" {
  description = "Prefix of the drill bucket the attacker makes public."
  type        = string
  default     = "drill-data"
}

variable "enable_honeytoken" {
  description = "Also create the honeytoken user (the lesson's second stretch goal)."
  type        = bool
  default     = false
}
